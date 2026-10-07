import hashlib
import re
from io import BytesIO
from django.apps import apps
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from .models import AnexoLancamento, RegistroAlteracao

ALVOS = {
    "carga": ("cargas", "graos.CargaColhida"),
    "venda": ("vendas", "vendas.VendaGraos"),
    "transferencia": ("transferencias", "graos.MovimentacaoGraos"),
    "financeiro": ("financeiro", "financeiro.LancamentoFinanceiro"),
    "compra": ("estoque", "estoque.CompraEstoque"),
    "faturamento": ("faturamento-insumos", "estoque.FaturamentoInsumo"),
}


def autorizar(user, entidade, registro_id, acao="consultar"):
    if entidade not in ALVOS:
        raise serializers.ValidationError("Tipo de lançamento inválido.")
    modulo, rotulo = ALVOS[entidade]
    if not pode(user, modulo, acao):
        raise PermissionDenied("Seu usuário não tem acesso a documentos deste lançamento.")
    modelo = apps.get_model(rotulo)
    try:
        pk = modelo._meta.pk.to_python(registro_id)
    except (DjangoValidationError, TypeError, ValueError):
        raise serializers.ValidationError("Identificador de lançamento inválido.")
    alvo = get_object_or_404(modelo, pk=pk)
    if entidade == "transferencia" and alvo.operacao not in {"transferencia_entrada", "transferencia_saida"}:
        raise serializers.ValidationError("Selecione um movimento de transferência.")
    return alvo


def metadados(item):
    return {campo: getattr(item, campo) for campo in ("id", "entidade", "registro_id", "nome", "tipo", "tamanho", "sha256", "criado_em")}


def auditar_documento(request, item, acao):
    RegistroAlteracao.objects.create(usuario=request.user, usuario_nome=request.user.username, modulo=ALVOS[item.entidade][0], entidade="documento do lançamento", registro_id=str(item.pk), acao=acao, alteracoes={"documento":{"antes":None if acao=="cadastrar" else item.nome,"depois":item.nome if acao=="cadastrar" else None},"sha256":{"antes":None,"depois":item.sha256},"lançamento":{"antes":None,"depois":f"{item.entidade}:{item.registro_id}"}})


def validar_arquivo(arquivo):
    if not arquivo or not arquivo.size or arquivo.size > 5 * 1024 * 1024:
        raise serializers.ValidationError("Selecione um PDF, PNG ou JPEG de até 5 MB.")
    conteudo = arquivo.read(5 * 1024 * 1024 + 1)
    if len(conteudo) > 5 * 1024 * 1024:
        raise serializers.ValidationError("O limite por arquivo é 5 MB.")
    nome = re.split(r"[/\\]", arquivo.name)[-1]
    nome = re.sub(r"[\x00-\x1f\x7f]", "", nome)[:160]
    extensao = nome.rsplit(".", 1)[-1].lower()
    if extensao == "pdf" and conteudo.startswith(b"%PDF-") and b"%%EOF" in conteudo[-2048:]:
        tipo = "application/pdf"
    elif extensao == "png" and conteudo.startswith(b"\x89PNG\r\n\x1a\n") and b"IEND" in conteudo[-12:]:
        tipo = "image/png"
    elif extensao in ("jpg", "jpeg") and conteudo.startswith(b"\xff\xd8\xff") and conteudo.endswith(b"\xff\xd9"):
        tipo = "image/jpeg"
    else:
        raise serializers.ValidationError("O conteúdo não corresponde a um PDF, PNG ou JPEG permitido.")
    return nome, tipo, conteudo


class AnexosView(NoStoreResponseMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request, entidade, registro_id):
        registro_id = str(autorizar(request.user, entidade, registro_id).pk)
        itens = AnexoLancamento.objects.filter(entidade=entidade, registro_id=registro_id, excluido_em__isnull=True).defer("conteudo")
        return Response([metadados(item) for item in itens])

    def post(self, request, entidade, registro_id):
        registro_id = str(autorizar(request.user, entidade, registro_id, "cadastrar").pk)
        nome, tipo, conteudo = validar_arquivo(request.FILES.get("arquivo"))
        sha = hashlib.sha256(conteudo).hexdigest()
        with transaction.atomic():
            # Mesmo alvo serializa uploads inclusive de usuários diferentes.
            alvo = autorizar(request.user, entidade, registro_id, "cadastrar")
            type(alvo).objects.select_for_update().get(pk=alvo.pk)
            qs = AnexoLancamento.objects.filter(entidade=entidade, registro_id=registro_id, excluido_em__isnull=True)
            existente = qs.filter(sha256=sha).first()
            if existente:
                return Response(metadados(existente))
            if qs.count() >= 20:
                raise serializers.ValidationError("O limite é 20 documentos por lançamento.")
            item = AnexoLancamento.objects.create(entidade=entidade, registro_id=registro_id, nome=nome, tipo=tipo, tamanho=len(conteudo), sha256=sha, conteudo=conteudo, criado_por=request.user)
            auditar_documento(request, item, "cadastrar")
        return Response(metadados(item), status=201)


class AnexoDetailView(NoStoreResponseMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        item = get_object_or_404(AnexoLancamento, pk=pk, excluido_em__isnull=True)
        autorizar(request.user, item.entidade, item.registro_id)
        resposta = FileResponse(BytesIO(bytes(item.conteudo)), as_attachment=True, filename=item.nome, content_type=item.tipo)
        resposta["X-Content-Type-Options"] = "nosniff"
        return resposta

    def delete(self, request, pk):
        with transaction.atomic():
            item = get_object_or_404(AnexoLancamento.objects.select_for_update(), pk=pk, excluido_em__isnull=True)
            autorizar(request.user, item.entidade, item.registro_id, "excluir")
            item.excluido_em = timezone.now()
            item.save(update_fields=("excluido_em",))
            auditar_documento(request, item, "excluir")
        return Response(status=204)
