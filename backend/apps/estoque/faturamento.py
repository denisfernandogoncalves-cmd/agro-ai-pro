"""Prévia e confirmação atômica do faturamento por fornecedor."""
import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cadpro.models import CADProPropriedade
from apps.financeiro.models import ParceiroFinanceiro
from apps.propriedades.models import Propriedade
from .models import BaixaFaturamentoInsumo, FaturamentoInsumo, LoteEstoque, MovimentacaoEstoque, ProdutoEstoque
from .services import saldo_lote


class FaturamentoConflitante(APIException):
    status_code = 409
    default_detail = "Esta confirmação já foi usada com outros dados. Consulte o histórico."


class ItemFaturamentoEntrada(serializers.Serializer):
    propriedade = serializers.PrimaryKeyRelatedField(queryset=Propriedade.objects.all())
    cad_pro = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    bep = serializers.RegexField(r"^[0-9]+$", max_length=40, required=False, allow_blank=True, default="",
                                error_messages={"invalid": "Informe somente os dígitos do BEP."})
    area_alqueires = serializers.DecimalField(max_digits=14, decimal_places=6, min_value=Decimal("0.000001"))
    quantidade_embalagens = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"), required=False)


class FaturamentoEntrada(serializers.Serializer):
    id = serializers.UUIDField()
    fornecedor = serializers.PrimaryKeyRelatedField(queryset=ParceiroFinanceiro.objects.filter(ativo=True, tipo__in=("fornecedor", "ambos")))
    produto = serializers.PrimaryKeyRelatedField(queryset=ProdutoEstoque.objects.filter(ativo=True))
    data_envio = serializers.DateField()
    embalagem = serializers.CharField(max_length=40)
    conteudo_embalagem = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"))
    dosagem_alqueire = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0"))
    observacoes = serializers.CharField(max_length=1000, allow_blank=True, default="")
    itens = ItemFaturamentoEntrada(many=True, allow_empty=False, max_length=200)

    def validate(self, attrs):
        if not fornecedor_usa_bep(attrs["fornecedor"].nome) and any(i["bep"] for i in attrs["itens"]):
            raise serializers.ValidationError({"itens": "BEP é utilizado somente no faturamento da C.Vale."})
        ids = [i["propriedade"].pk for i in attrs["itens"]]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Selecione cada propriedade uma única vez.")
        for item in attrs["itens"]:
            if "quantidade_embalagens" not in item:
                quantidade = (item["area_alqueires"] * attrs["dosagem_alqueire"] / attrs["conteudo_embalagem"]).quantize(Decimal("1"), rounding=ROUND_CEILING)
                if quantidade <= 0 or quantidade > Decimal("9999999.999"):
                    raise serializers.ValidationError({"itens": "Informe uma quantidade válida de embalagens a enviar."})
                item["quantidade_embalagens"] = quantidade
        total = sum(i["quantidade_embalagens"] * attrs["conteudo_embalagem"] for i in attrs["itens"])
        if total > Decimal("99999999999.999"):
            raise serializers.ValidationError("Quantidade total acima do limite do estoque.")
        for item in attrs["itens"]:
            quantidade = item["quantidade_embalagens"] * attrs["conteudo_embalagem"]
            if quantidade != quantidade.quantize(Decimal("0.001")):
                raise serializers.ValidationError("A quantidade convertida deve ter no máximo três casas decimais.")
        return attrs


def fornecedor_usa_bep(nome):
    return bool(re.match(r"^c[\s.\-]*vale(?:\b|$)", nome.strip(), re.IGNORECASE))


def assinatura(dados):
    def normalizar(valor):
        if hasattr(valor, "pk"):
            return str(valor.pk)
        return str(valor)
    # Campo vazio omitido para preservar a assinatura dos envios anteriores ao BEP.
    itens = [{k: v for k, v in i.items() if k != "bep" or v} for i in dados["itens"]]
    conteudo = {**dados, "itens": sorted(itens, key=lambda i: i["propriedade"].pk)}
    return hashlib.sha256(json.dumps(conteudo, default=normalizar, sort_keys=True).encode()).hexdigest()


def preparar_resumo(dados):
    produto, fornecedor = dados["produto"], dados["fornecedor"]
    itens = []
    for item in dados["itens"]:
        propriedade = item["propriedade"]
        codigos = list(CADProPropriedade.objects.filter(propriedade=propriedade, ativo=True, cad_pro__ativo=True).values_list("cad_pro__codigo", flat=True))
        codigo = item["cad_pro"]
        if (codigos and codigo not in codigos) or (not codigos and codigo):
            raise serializers.ValidationError({"itens": f"Confira o CAD/PRO da propriedade {propriedade.nome}."})
        quantidade = item["quantidade_embalagens"] * dados["conteudo_embalagem"]
        itens.append({
            "propriedade": propriedade.pk, "propriedade_nome": propriedade.nome,
            "produtor": propriedade.proprietario, "cad_pro": codigo,
            "bep": (item["bep"] or propriedade.bp_cvale) if fornecedor_usa_bep(fornecedor.nome) else "",
            "area_alqueires": str(item["area_alqueires"]),
            "quantidade_sugerida": str((item["area_alqueires"] * dados["dosagem_alqueire"]).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)),
            "quantidade_embalagens": str(item["quantidade_embalagens"]), "quantidade": str(quantidade.quantize(Decimal("0.001"))),
        })
    lotes = LoteEstoque.objects.filter(produto=produto, fornecedor=fornecedor)
    saldo = sum((saldo_lote(lote) for lote in lotes), Decimal(0))
    total = sum((Decimal(i["quantidade"]) for i in itens), Decimal(0))
    return {
        "fornecedor_nome": fornecedor.nome, "produto_nome": produto.nome, "unidade": produto.unidade,
        "usa_bep": fornecedor_usa_bep(fornecedor.nome),
        "data_envio": str(dados["data_envio"]), "embalagem": dados["embalagem"],
        "conteudo_embalagem": str(dados["conteudo_embalagem"]), "dosagem_alqueire": str(dados["dosagem_alqueire"]),
        "observacoes": dados["observacoes"], "itens": itens,
        "total_embalagens": str(sum((Decimal(i["quantidade_embalagens"]) for i in itens), Decimal(0))),
        "quantidade_total": str(total), "saldo_anterior": str(saldo), "saldo_posterior": str(saldo - total),
    }


@transaction.atomic
def confirmar_faturamento(dados, usuario):
    # Serializa confirmações do mesmo produto, inclusive quando não há lote ainda.
    ProdutoEstoque.objects.select_for_update().get(pk=dados["produto"].pk)
    hash_dados = assinatura(dados)
    existente = FaturamentoInsumo.objects.filter(pk=dados["id"]).first()
    if existente:
        if existente.excluido_em:
            raise FaturamentoConflitante("Este lançamento foi excluído. Inicie um novo faturamento.")
        if existente.assinatura != hash_dados or existente.criado_por_id != usuario.pk:
            raise FaturamentoConflitante()
        return existente, True
    lotes = list(LoteEstoque.objects.select_for_update().filter(
        produto=dados["produto"], fornecedor=dados["fornecedor"], ativo=True,
    ).order_by("id"))
    resumo = preparar_resumo(dados)
    faturamento = FaturamentoInsumo.objects.create(
        id=dados["id"], assinatura=hash_dados, fornecedor=dados["fornecedor"], produto=dados["produto"],
        data_envio=dados["data_envio"], criado_por=usuario, resumo=resumo,
    )
    restante = Decimal(resumo["quantidade_total"])
    baixas = []
    for lote in lotes:
        quantidade = min(max(saldo_lote(lote), Decimal(0)), restante)
        if quantidade:
            baixas.append((lote, quantidade))
            restante -= quantidade
        if not restante:
            break
    if restante:
        # Um lote próprio representa a parcela sem cobertura, sem inventar entrada.
        lote, _ = LoteEstoque.objects.get_or_create(
            produto=dados["produto"], fornecedor=dados["fornecedor"], local=None,
            codigo="FATURAMENTO-SEM-COBERTURA",
            defaults={"observacoes": "Saldo sem cobertura de faturamentos confirmados."},
        )
        baixas.append((lote, restante))
    for lote, quantidade in baixas:
        movimento = MovimentacaoEstoque(
            lote=lote, tipo="saida", quantidade=quantidade, criado_por=usuario,
            data_movimento=dados["data_envio"], observacoes=f"Faturamento de insumos {faturamento.pk}",
        )
        # Exceção de saldo negativo exclusiva desta operação; saída comum segue bloqueada.
        movimento.full_clean()
        movimento.save()
        BaixaFaturamentoInsumo.objects.create(faturamento=faturamento, movimento=movimento)
    return faturamento, False


@transaction.atomic
def excluir_faturamento(faturamento, usuario):
    # Mesma ordem da confirmação: produto, lotes, movimentos; exclusões repetidas não estornam duas vezes.
    ProdutoEstoque.objects.select_for_update().get(pk=faturamento.produto_id)
    faturamento = FaturamentoInsumo.objects.select_for_update().get(pk=faturamento.pk)
    if faturamento.excluido_em:
        return
    baixas = list(faturamento.baixas.select_related("movimento").order_by("movimento__lote_id"))
    lotes = sorted({b.movimento.lote_id for b in baixas})
    list(LoteEstoque.objects.select_for_update().filter(pk__in=lotes).order_by("id"))
    movimentos = [b.movimento_id for b in baixas]
    list(MovimentacaoEstoque.objects.select_for_update().filter(pk__in=movimentos).order_by("id"))
    faturamento.resumo = {**faturamento.resumo, "baixas_excluidas": [
        {"movimento": b.movimento_id, "lote": b.movimento.lote_id, "quantidade": str(b.movimento.quantidade)}
        for b in baixas
    ]}
    faturamento.baixas.all().delete()
    # Remover apenas as saídas deste envio recompõe exatamente os lotes, inclusive o saldo negativo.
    # Um vínculo protegido inesperado aborta a transação inteira.
    MovimentacaoEstoque.objects.filter(pk__in=movimentos).delete()
    faturamento.excluido_em = timezone.now()
    faturamento.excluido_por = usuario
    faturamento.save(update_fields=("resumo", "excluido_em", "excluido_por"))


class FaturamentoSaida(serializers.ModelSerializer):
    responsavel = serializers.CharField(source="criado_por.username", read_only=True)

    class Meta:
        model = FaturamentoInsumo
        fields = ("id", "fornecedor", "produto", "data_envio", "criado_em", "responsavel", "resumo")
        read_only_fields = fields


class FaturamentoInsumoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = FaturamentoSaida
    queryset = FaturamentoInsumo.objects.select_related("criado_por").filter(excluido_em__isnull=True)

    def destroy(self, request, *args, **kwargs):
        faturamento = get_object_or_404(FaturamentoInsumo, pk=kwargs["pk"])
        self.check_object_permissions(request, faturamento)
        try:
            excluir_faturamento(faturamento, request.user)
        except ProtectedError:
            raise FaturamentoConflitante("Este lançamento possui vínculos que impedem a exclusão.")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def pdf(self, request, *args, **kwargs):
        from .faturamento_pdf import gerar_pdf_faturamento
        faturamento = self.get_object()
        response = HttpResponse(gerar_pdf_faturamento(faturamento), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="faturamento-insumos-{faturamento.id}.pdf"'
        response["Cache-Control"] = "private, no-store"
        return response

    @action(detail=False, methods=["post"])
    def previa(self, request):
        entrada = FaturamentoEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        return Response(preparar_resumo(entrada.validated_data))

    @action(detail=False, methods=["post"])
    def confirmar(self, request):
        entrada = FaturamentoEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            faturamento, repetido = confirmar_faturamento(entrada.validated_data, request.user)
        except IntegrityError:
            # Colisão da mesma chave com outro produto também precisa retornar 409.
            if FaturamentoInsumo.objects.filter(pk=entrada.validated_data["id"]).exists():
                raise FaturamentoConflitante()
            raise
        return Response(self.get_serializer(faturamento).data, status=status.HTTP_200_OK if repetido else status.HTTP_201_CREATED)
