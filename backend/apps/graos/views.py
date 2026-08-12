from django.db.models.deletion import ProtectedError
from django.db.models import Exists, OuterRef
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .cargas_services import (
    CargaColhidaDuplicadaError,
    CargaColhidaError,
)
from .models import (
    ArmazemGraos,
    CargaColhida,
    GrupoColheita,
    LoteGraos,
    MovimentacaoGraos,
)
from .grupos_services import inativar_grupo_colheita
from .selectors import selecionar_origens, selecionar_reservas
from .serializers import (
    AjusteSaldoSerializer,
    ArmazemGraosSerializer,
    CargaColhidaSerializer,
    EstornoMovimentacaoSerializer,
    FiltrosGraosSerializer,
    FiltrosPosicaoSaldoSerializer,
    GrupoColheitaSerializer,
    LiberarReservaSerializer,
    LoteGraosSerializer,
    MovimentacaoGraosSerializer,
    OperacaoLoteSerializer,
    OperacaoReservaSerializer,
    OrigemSaldoGraosSerializer,
    PosicaoSaldoGraosSerializer,
    ReconciliarPosicaoSerializer,
    ReservaSaldoGraosSerializer,
    ReservarSaldoSerializer,
    TransferirSaldoFisicoSerializer,
    TransferenciaGraosSerializer,
    serializar_painel_saldos,
    serializar_resultado,
)
from .services import (
    SaldoGraosError,
    confirmar_entrega,
    consultar_posicao,
    creditar_producao,
    estornar_movimentacao,
    liberar_reserva,
    posicao_graos,
    painel_saldos_cadpro,
    reconciliar_posicao,
    registrar_ajuste,
    registrar_devolucao,
    reservar_saldo,
    resumo_graos,
    transferir_graos,
    transferir_saldo_fisico,
)


def _filtros_posicao(query_params):
    serializer = FiltrosGraosSerializer(data=query_params)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def _executar_operacao(request, serializer_class, servico, *, dados=None):
    serializer = serializer_class(data=request.data if dados is None else dados)
    serializer.is_valid(raise_exception=True)
    try:
        resultado = servico(
            usuario=request.user,
            **serializer.validated_data,
        )
    except SaldoGraosError as exc:
        return Response(
            {
                "sucesso": False,
                "codigo": exc.codigo,
                "mensagem": str(exc),
            },
            status=status.HTTP_409_CONFLICT,
        )
    codigo_http = (
        status.HTTP_200_OK
        if resultado.idempotente or resultado.codigo == "posicao_reconciliada"
        else status.HTTP_201_CREATED
    )
    return Response(serializar_resultado(resultado), status=codigo_http)


class CadastroGraosMixin:
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Este cadastro possui movimentações ou vínculos protegidos."},
                status=status.HTTP_409_CONFLICT,
            )


class ArmazemGraosViewSet(CadastroGraosMixin, viewsets.ModelViewSet):
    queryset = ArmazemGraos.objects.select_related("propriedade")
    serializer_class = ArmazemGraosSerializer
    search_fields = ("nome", "propriedade__nome")
    ordering_fields = ("nome", "capacidade_kg", "criado_em")
    ordering = ("nome", "id")

    def get_queryset(self):
        queryset = super().get_queryset()
        propriedade = self.request.query_params.get("propriedade", "").strip()
        ativo = self.request.query_params.get("ativo", "").strip().lower()
        if propriedade:
            queryset = queryset.filter(propriedade_id=propriedade)
        if ativo in {"true", "false"}:
            queryset = queryset.filter(ativo=ativo == "true")
        return queryset


class GrupoColheitaViewSet(CadastroGraosMixin, viewsets.ModelViewSet):
    queryset = GrupoColheita.objects.select_related(
        "propriedade",
        "cad_pro",
        "armazem_padrao",
        "criado_por",
    ).annotate(
        contexto_congelado_db=Exists(
            CargaColhida.objects.filter(grupo_colheita_id=OuterRef("pk"))
        )
    )
    serializer_class = GrupoColheitaSerializer
    search_fields = ("nome", "cultura", "safra", "propriedade__nome", "cad_pro__codigo")
    ordering_fields = ("nome", "cultura", "safra", "ativo", "criado_em")
    ordering = ("-safra", "cultura", "nome", "id")
    http_method_names = ("get", "post", "patch", "head", "options")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (
            ("propriedade", "propriedade_id"),
            ("cad_pro", "cad_pro_id"),
            ("armazem_padrao", "armazem_padrao_id"),
            ("safra", "safra"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        cultura = self.request.query_params.get("cultura", "").strip()
        ativo = self.request.query_params.get("ativo", "").strip().lower()
        if cultura:
            queryset = queryset.filter(cultura__iexact=cultura)
        if ativo in {"true", "false"}:
            queryset = queryset.filter(ativo=ativo == "true")
        return queryset

    @action(detail=True, methods=("post",))
    def inativar(self, request, pk=None):
        self.get_object()
        grupo = inativar_grupo_colheita(pk)
        return Response(self.get_serializer(grupo).data)


class CargaColhidaViewSet(
    viewsets.mixins.CreateModelMixin,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = CargaColhida.objects.select_related(
        "grupo_colheita",
        "grupo_colheita__propriedade",
        "grupo_colheita__cad_pro",
        "armazem",
        "lote",
        "movimentacao",
        "criado_por",
    )
    serializer_class = CargaColhidaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = (
        "placa",
        "local_colheita",
        "grupo_colheita__nome",
        "grupo_colheita__propriedade__nome",
        "grupo_colheita__cad_pro__codigo",
    )
    ordering_fields = ("data_colheita", "peso_bruto_kg", "peso_liquido_kg", "criado_em")
    ordering = ("-data_colheita", "-id")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (
            ("grupo_colheita", "grupo_colheita_id"),
            ("propriedade", "grupo_colheita__propriedade_id"),
            ("cad_pro", "grupo_colheita__cad_pro_id"),
            ("armazem", "armazem_id"),
            ("data_colheita", "data_colheita"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            carga = serializer.save()
        except CargaColhidaDuplicadaError as exc:
            return Response(
                {"codigo": exc.codigo, "detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        except SaldoGraosError as exc:
            return Response(
                {"codigo": exc.codigo, "detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        except CargaColhidaError as exc:
            return Response(
                {"codigo": exc.codigo, "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            self.get_serializer(carga).data,
            status=status.HTTP_201_CREATED,
        )


class LoteGraosViewSet(CadastroGraosMixin, viewsets.ModelViewSet):
    queryset = LoteGraos.objects.select_related(
        "armazem",
        "armazem__propriedade",
        "talhao",
    )
    serializer_class = LoteGraosSerializer
    search_fields = (
        "codigo",
        "cultura",
        "safra",
        "armazem__nome",
        "armazem__propriedade__nome",
        "talhao__nome",
    )
    ordering_fields = ("codigo", "cultura", "safra", "criado_em")
    ordering = ("safra", "cultura", "codigo", "id")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (
            ("armazem", "armazem_id"),
            ("propriedade", "armazem__propriedade_id"),
            ("talhao", "talhao_id"),
            ("safra", "safra"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        cultura = self.request.query_params.get("cultura", "").strip()
        ativo = self.request.query_params.get("ativo", "").strip().lower()
        if cultura:
            queryset = queryset.filter(cultura__iexact=cultura)
        if ativo in {"true", "false"}:
            queryset = queryset.filter(ativo=ativo == "true")
        return queryset

    @action(detail=False, methods=["get"])
    def posicao(self, request):
        return Response(posicao_graos(**_filtros_posicao(request.query_params)))

    @action(detail=False, methods=["get"])
    def resumo(self, request):
        return Response(resumo_graos(**_filtros_posicao(request.query_params)))

    @action(detail=True, methods=["post"])
    def transferir(self, request, pk=None):
        serializer = TransferenciaGraosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            saida, entrada = transferir_graos(
                usuario=request.user,
                lote_origem=self.get_object(),
                **serializer.validated_data,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        movimento_serializer = MovimentacaoGraosSerializer(
            (saida, entrada),
            many=True,
        )
        return Response(
            {
                "saida": movimento_serializer.data[0],
                "entrada": movimento_serializer.data[1],
            },
            status=status.HTTP_201_CREATED,
        )


class MovimentacaoGraosViewSet(
    viewsets.mixins.CreateModelMixin,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = MovimentacaoGraos.objects.select_related(
        "lote",
        "lote__armazem",
        "lote__armazem__propriedade",
        "posicao",
        "posicao__cad_pro",
        "posicao__armazem",
        "origem",
        "criado_por",
    )
    serializer_class = MovimentacaoGraosSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = (
        "lote__codigo",
        "lote__cultura",
        "lote__safra",
        "posicao__cad_pro__codigo",
        "posicao__classificacao_codigo",
        "origem__chave_idempotencia",
        "referencia_externa",
        "observacoes",
    )
    ordering_fields = ("data_movimento", "quantidade_kg", "tipo", "criado_em")
    ordering = ("-data_movimento", "-id")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (
            ("tipo", "tipo"),
            ("operacao", "operacao"),
            ("lote", "lote_id"),
            ("posicao", "posicao_id"),
            ("cad_pro", "posicao__cad_pro_id"),
            ("armazem", "posicao__armazem_id"),
            ("propriedade", "posicao__armazem__propriedade_id"),
            ("safra", "posicao__safra"),
            ("classificacao_codigo", "posicao__classificacao_codigo"),
            ("origem", "origem_id"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        cultura = self.request.query_params.get("cultura", "").strip()
        if cultura:
            queryset = queryset.filter(posicao__cultura__iexact=cultura)
        return queryset

    @action(detail=True, methods=["post"], url_path="estornar")
    def estornar(self, request, pk=None):
        dados = request.data.copy()
        dados["movimentacao"] = pk
        return _executar_operacao(
            request,
            EstornoMovimentacaoSerializer,
            estornar_movimentacao,
            dados=dados,
        )


class SaldoGraosViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        filtros = FiltrosPosicaoSaldoSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        queryset = consultar_posicao(**filtros.validated_data)
        return Response(PosicaoSaldoGraosSerializer(queryset, many=True).data)

    def retrieve(self, request, pk=None):
        posicao = consultar_posicao().filter(pk=pk).first()
        if not posicao:
            return Response(
                {"detail": "Posição de saldo não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(PosicaoSaldoGraosSerializer(posicao).data)

    @action(detail=False, methods=["get"], url_path="painel")
    def painel(self, request):
        filtros = FiltrosPosicaoSaldoSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        resultado = painel_saldos_cadpro(**filtros.validated_data)
        return Response(serializar_painel_saldos(resultado))

    def _executar(self, request, serializer_class, servico):
        return _executar_operacao(request, serializer_class, servico)

    @action(detail=False, methods=["post"], url_path="creditar-producao")
    def creditar_producao(self, request):
        return self._executar(request, OperacaoLoteSerializer, creditar_producao)

    @action(detail=False, methods=["post"], url_path="reservar")
    def reservar(self, request):
        return self._executar(request, ReservarSaldoSerializer, reservar_saldo)

    @action(detail=False, methods=["post"], url_path="liberar-reserva")
    def liberar_reserva(self, request):
        return self._executar(request, LiberarReservaSerializer, liberar_reserva)

    @action(detail=False, methods=["post"], url_path="confirmar-entrega")
    def confirmar_entrega(self, request):
        return self._executar(request, OperacaoReservaSerializer, confirmar_entrega)

    @action(detail=False, methods=["post"], url_path="registrar-devolucao")
    def registrar_devolucao(self, request):
        return self._executar(request, OperacaoLoteSerializer, registrar_devolucao)

    @action(detail=False, methods=["post"], url_path="registrar-ajuste")
    def registrar_ajuste(self, request):
        return self._executar(request, AjusteSaldoSerializer, registrar_ajuste)

    @action(detail=False, methods=["post"], url_path="estornar-movimentacao")
    def estornar_movimentacao(self, request):
        return self._executar(
            request,
            EstornoMovimentacaoSerializer,
            estornar_movimentacao,
        )

    @action(detail=False, methods=["post"], url_path="transferir")
    def transferir(self, request):
        return self._executar(
            request,
            TransferirSaldoFisicoSerializer,
            transferir_saldo_fisico,
        )

    @action(detail=False, methods=["post"], url_path="reconciliar")
    def reconciliar(self, request):
        return self._executar(
            request,
            ReconciliarPosicaoSerializer,
            reconciliar_posicao,
        )


class OrigemSaldoGraosViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = selecionar_origens()
    serializer_class = OrigemSaldoGraosSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("chave_idempotencia", "referencia_externa")
    ordering_fields = ("tipo", "criado_em")

    def get_queryset(self):
        queryset = super().get_queryset()
        tipo = self.request.query_params.get("tipo", "").strip()
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return queryset


class ReservaSaldoGraosViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = selecionar_reservas()
    serializer_class = ReservaSaldoGraosSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ("status", "criado_em", "saldo_reservado_kg")

    def get_queryset(self):
        return selecionar_reservas(
            posicao=self.request.query_params.get("posicao", "").strip(),
            status=self.request.query_params.get("status", "").strip(),
        )
