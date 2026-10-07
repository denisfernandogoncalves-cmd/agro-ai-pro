from contextvars import ContextVar
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from .models import RegistroAlteracao

requisicao_atual = ContextVar("requisicao_auditoria", default=None)
APPS = {"propriedades", "talhoes", "graos", "vendas", "estoque", "financeiro", "producao", "maquinas", "cadpro", "accounts", "auth"}
# Lista permitida: nunca copiar credenciais, arquivos, dados bancários ou observações livres.
CAMPOS = set("nome username first_name last_name is_active is_staff modulos permissoes proprietario municipio uf area_hectares cultura cultura_atual safra status ativo ativa tipo descricao codigo capacidade_kg peso_bruto_kg peso_liquido_kg umidade_percentual impureza_percentual avariados_percentual placa motorista local_colheita quantidade_kg quantidade_entregue_kg quantidade_devolvida_kg quantidade_cancelada_kg saldo_fisico_kg saldo_comprometido_kg quantidade quantidade_planejada quantidade_utilizada valor valor_liquidado custo_estimado custo_realizado estoque_minimo unidade categoria fabricante data data_colheita data_emissao data_vencimento data_liquidacao data_validade data_planejada data_inicio data_conclusao conteudo_embalagem quantidade_embalagens custo_embalagem valor_total excluido_em excluida_em".split())


def contexto(sender):
    request = requisicao_atual.get()
    if request is None or sender._meta.app_label not in APPS:
        return None
    user = getattr(request, "user", None)
    return request if user and user.is_authenticated else None


def valores(instance):
    resultado = {}
    for campo in instance._meta.concrete_fields:
        if campo.name not in CAMPOS and not campo.is_relation:
            continue
        valor = getattr(instance, campo.attname)
        if isinstance(valor, (Decimal, date, datetime, UUID)):
            valor = str(valor)
        if isinstance(valor, (dict, list)) and campo.name not in {"modulos", "permissoes"}:
            continue
        resultado[str(campo.verbose_name)] = valor
    return resultado


@receiver(pre_delete, dispatch_uid="core_auditoria_antes_excluir")
@receiver(pre_save, dispatch_uid="core_auditoria_antes")
def antes(sender, instance, raw=False, **kwargs):
    if raw or not contexto(sender):
        return
    anterior = sender._default_manager.filter(pk=instance.pk).first() if instance.pk else None
    instance._auditoria_anterior = valores(anterior) if anterior else {}


def registrar(sender, instance, acao):
    request = contexto(sender)
    if not request:
        return
    anterior = getattr(instance, "_auditoria_anterior", {})
    atual = {} if acao == "excluir" else valores(sender._default_manager.get(pk=instance.pk))
    if acao == "excluir":
        anterior = getattr(instance, "_auditoria_anterior", valores(instance))
    alteracoes = {campo: {"antes": anterior.get(campo), "depois": atual.get(campo)} for campo in anterior.keys() | atual.keys() if anterior.get(campo) != atual.get(campo)}
    if not alteracoes:
        return
    RegistroAlteracao.objects.create(usuario=request.user, usuario_nome=request.user.username, modulo=modulo_da_requisicao(request, sender._meta.app_label), entidade=str(sender._meta.verbose_name), registro_id=str(instance.pk), acao=acao, alteracoes=alteracoes)


@receiver(post_save, dispatch_uid="core_auditoria_depois")
def depois(sender, instance, created, raw=False, **kwargs):
    if not raw:
        registrar(sender, instance, "cadastrar" if created else "editar")


@receiver(post_delete, dispatch_uid="core_auditoria_excluir")
def removido(sender, instance, **kwargs):
    registrar(sender, instance, "excluir")


class AuditoriaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/") or request.path.startswith("/api/auth/token") or request.method in {"GET", "HEAD", "OPTIONS"}:
            return self.get_response(request)
        token = requisicao_atual.set(request)
        try:
            return self.get_response(request)
        finally:
            requisicao_atual.reset(token)


def modulo_da_requisicao(request, app):
    caminho = getattr(request, "path", "").removeprefix("/api/")
    if caminho.startswith("estoque/faturamentos/"):
        return "faturamento-insumos"
    if caminho.startswith(("graos/cargas-colhidas/", "graos/terceiros/")):
        return "cargas"
    if caminho.startswith("graos/transferencias/") or caminho.endswith("/transferir/"):
        return "transferencias"
    return {"auth": "usuarios", "accounts": "usuarios", "graos": "producao-saldos", "cadpro": "propriedades", "producao": "operacoes"}.get(app, app)
