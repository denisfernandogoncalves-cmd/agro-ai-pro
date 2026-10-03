from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

MODULOS = {
    "propriedades": "Propriedades", "talhoes": "Talhões",
    "cadastros-agricolas": "Cadastros agrícolas", "cargas": "Cargas colhidas",
    "producao-saldos": "Produção e saldos", "transferencias": "Transferência de saldo",
    "vendas": "Vendas", "clima": "Clima", "mercado": "Mercado",
    "financeiro": "Financeiro", "estoque": "Estoque", "operacoes": "Operações",
    "maquinas": "Máquinas", "faturamento-insumos": "Faturamento de insumos",
    "relatorios": "Relatórios", "importacoes": "Importações", "insights": "Assistente",
}


def modulos_do_usuario(user):
    if user.is_staff or user.is_superuser:
        return list(MODULOS)
    from .models import AcessoUsuario
    acesso = AcessoUsuario.objects.filter(usuario=user).first()
    if acesso and acesso.excluido_em:
        return []
    return list(MODULOS) if acesso is None or acesso.modulos is None else acesso.modulos


# Catálogos de consulta são compartilhados pelos módulos que dependem deles.
# A permissão de consultar um catálogo nunca autoriza sua alteração.
REGRAS = (
    ("estoque/faturamentos/", {"faturamento-insumos"}, {"faturamento-insumos"}),
    ("estoque/produtos/", {"estoque", "cadastros-agricolas", "faturamento-insumos", "operacoes"}, {"cadastros-agricolas", "estoque"}),
    ("estoque/locais/", {"estoque", "cadastros-agricolas", "faturamento-insumos"}, {"cadastros-agricolas", "estoque"}),
    ("estoque/lotes/", {"estoque", "operacoes"}, {"estoque"}),
    ("estoque/", {"estoque"}, {"estoque"}),
    ("financeiro/parceiros/", {"financeiro", "cadastros-agricolas", "estoque", "faturamento-insumos", "vendas"}, {"financeiro", "cadastros-agricolas"}),
    ("financeiro/categorias/", {"financeiro", "cadastros-agricolas"}, {"financeiro", "cadastros-agricolas"}),
    ("financeiro/centros-custo/", {"financeiro", "cadastros-agricolas"}, {"financeiro", "cadastros-agricolas"}),
    ("financeiro/", {"financeiro"}, {"financeiro"}),
    ("graos/armazens/", {"cadastros-agricolas", "cargas", "producao-saldos", "transferencias", "vendas"}, {"cadastros-agricolas"}),
    ("graos/cargas-colhidas/", {"cargas"}, {"cargas"}),
    ("graos/saldos/transferir/", {"transferencias"}, {"transferencias"}),
    ("graos/transferencias/", {"transferencias"}, {"transferencias"}),
    ("graos/lotes/", {"producao-saldos", "vendas", "transferencias"}, {"producao-saldos", "cadastros-agricolas"}),
    ("graos/", {"producao-saldos", "transferencias", "vendas"}, {"producao-saldos"}),
    ("comercial/contratos/", {"cadastros-agricolas", "vendas"}, {"cadastros-agricolas", "vendas"}),
    ("comercial/", {"vendas"}, {"vendas"}),
    ("propriedades/", set(MODULOS) - {"mercado"}, {"propriedades"}),
    ("cadpros/", {"propriedades", "talhoes", "cadastros-agricolas", "cargas", "producao-saldos", "transferencias", "vendas", "faturamento-insumos", "importacoes"}, {"propriedades", "cadastros-agricolas"}),
    ("talhoes/grupos-colheita/", {"talhoes", "cargas"}, {"talhoes"}),
    ("talhoes/", {"talhoes", "cargas", "operacoes", "maquinas", "clima", "relatorios", "insights"}, {"talhoes"}),
    ("producao/operacoes/", {"operacoes", "maquinas"}, {"operacoes"}),
    ("producao/", {"operacoes"}, {"operacoes"}),
    ("maquinas/", {"maquinas"}, {"maquinas"}),
    ("clima/", {"clima"}, {"clima"}),
    ("mercado/", {"mercado"}, {"mercado"}),
    ("relatorios/", {"relatorios"}, {"relatorios"}),
    ("importacoes/", {"importacoes"}, {"importacoes"}),
    ("ai/", {"insights"}, {"insights"}),
)


ACOES = ("consultar", "cadastrar", "editar", "excluir", "imprimir")


def permissoes_do_usuario(user):
    from .models import AcessoUsuario
    modulos = modulos_do_usuario(user)
    if user.is_staff or user.is_superuser:
        return {modulo: list(ACOES) for modulo in modulos}
    acesso = AcessoUsuario.objects.filter(usuario=user).first()
    configuradas = acesso.permissoes if acesso and acesso.permissoes is not None else {}
    return {modulo: configuradas.get(modulo, list(ACOES)) for modulo in modulos}


def pode(user, modulo, acao="consultar"):
    return acao in permissoes_do_usuario(user).get(modulo, [])


def acao_da_requisicao(path, method):
    recurso = path.rstrip("/")
    if method in {"GET", "HEAD", "OPTIONS"}:
        return "imprimir" if recurso.endswith(("/pdf", "/imprimir", "/exportar")) else "consultar"
    if method == "DELETE" or recurso.endswith(("/cancelar", "/excluir", "/estornar")):
        return "excluir"
    if method in {"PATCH", "PUT"}:
        return "editar"
    ultimo = recurso.rsplit("/", 1)[-1]
    if ultimo in {"ler-codigo", "previa-particular", "simular", "previa"}:
        return "consultar"
    if ultimo in {"cancelar", "estornar", "estornar-movimentacao", "excluir"}:
        return "excluir"
    if recurso.endswith("/estoque/faturamentos/confirmar"):
        return "cadastrar"
    if ultimo in {"confirmar", "liquidar", "iniciar", "concluir", "reativar", "reconciliar", "confirmar-entrega", "liberar-reserva"}:
        return "editar"
    if ultimo in {"entregar", "devolver", "reservar", "registrar-saida", "registrar-boleto", "parcelar", "creditar-producao", "registrar-devolucao", "registrar-ajuste", "transferir", "particular", "venda-particular", "confirmar-importacao"}:
        return "cadastrar"
    return "editar" if any(parte.isdigit() for parte in recurso.split("/")) else "cadastrar"


def verificar_acesso(user, path, method):
    if user.is_staff or user.is_superuser or not path.startswith("/api/"):
        return
    recurso = path.removeprefix("/api/")
    if recurso.startswith("auth/") or recurso == "health/":
        return
    if recurso.startswith("core/"):
        # As views de core verificam o setor e o dono da consulta separadamente.
        return
    permissoes = permissoes_do_usuario(user)
    acao = acao_da_requisicao(path, method)
    if recurso.startswith("graos/lotes/") and recurso.endswith("/transferir/"):
        if acao in permissoes.get("transferencias", []):
            return
        raise PermissionDenied("Seu usuário não pode realizar transferências.")
    for prefixo, leitura, escrita in REGRAS:
        if recurso.startswith(prefixo):
            permitidos = leitura if acao in {"consultar", "imprimir"} else escrita
            if any(acao in permissoes.get(modulo, []) for modulo in permitidos):
                return
            break
    raise PermissionDenied("Seu usuário não tem permissão para esta ação. Solicite ao administrador.")


class AcessoJWTAuthentication(JWTAuthentication):
    """Verifica módulos mesmo em views que declaram permissões próprias."""
    def authenticate(self, request):
        resultado = super().authenticate(request)
        if resultado:
            verificar_acesso(resultado[0], request.path, request.method)
        return resultado
