import csv
import io

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from openpyxl import Workbook
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.access import PAPEIS_ADMINISTRACAO, PAPEIS_GESTAO, PAPEIS_OPERACAO
from apps.estoque.models import LocalEstoque

from .grain_models import CadPro
from .grain_reports import export_pdf
from .grain_services import ProducaoError
from .joint_models import (
    CargaLoteConjunto,
    LoteConjuntoProducao,
    MovimentacaoLoteConjunto,
    ParticipanteLoteConjunto,
    SaidaLoteConjunto,
    SaldoLoteConjunto,
)
from .joint_serializers import (
    CargaLoteConjuntoSerializer,
    LoteConjuntoProducaoSerializer,
    MovimentacaoLoteConjuntoSerializer,
    SaidaLoteConjuntoSerializer,
    SaldoLoteConjuntoSerializer,
)
from .joint_services import (
    ajustar_saldo_conjunto,
    colocar_em_conferencia,
    confirmar_lote,
    confirmar_saida_conjunta,
    encerrar_lote,
    estornar_lote,
    estornar_saida_conjunta,
    exigir_acesso_lote,
    lotes_conjuntos_visiveis,
    ratear_manual,
    ratear_por_area,
    recalcular_lote,
    resumo_transportes,
    transferir_saldo_conjunto,
)


def resposta_erro(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def lote_visivel_ou_404(usuario, lote_id):
    return get_object_or_404(
        lotes_conjuntos_visiveis(usuario).select_related(
            "cultura", "safra", "local_armazenagem", "cadpro_responsavel"
        ),
        pk=lote_id,
    )


class LoteConjuntoProducaoViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = LoteConjuntoProducaoSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        "codigo",
        "descricao",
        "cultura__nome",
        "safra__nome",
        "participantes__propriedade__nome",
        "participantes__propriedade__municipio",
        "participantes__propriedade__proprietario",
        "participantes__cadpro__codigo",
    )
    ordering_fields = (
        "data_inicio_colheita",
        "data_final_colheita",
        "peso_liquido_total_kg",
        "area_total_colhida_ha",
        "status",
        "criado_em",
    )

    def get_queryset(self):
        queryset = lotes_conjuntos_visiveis(self.request.user).select_related(
            "cultura", "safra", "local_armazenagem", "cadpro_responsavel"
        ).prefetch_related(
            "participantes__propriedade",
            "participantes__cadpro",
            "participantes__talhoes__talhao",
            "cargas__motorista",
            "cargas__veiculo_cavalo",
            "cargas__veiculo_carreta",
            "cargas__transportadora",
            "cadpros_participantes__cadpro__propriedade",
            "saldos_conjuntos__local_armazenagem",
        )
        for parametro, campo in (
            ("cultura", "cultura_id"),
            ("safra", "safra_id"),
            ("status", "status"),
            ("local", "local_armazenagem_id"),
            ("propriedade", "participantes__propriedade_id"),
            ("cadpro", "participantes__cadpro_id"),
            ("municipio", "participantes__propriedade__municipio__icontains"),
            ("produtor", "participantes__propriedade__proprietario__icontains"),
        ):
            valor = self.request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        data_inicio = self.request.query_params.get("data_inicio", "").strip()
        data_fim = self.request.query_params.get("data_fim", "").strip()
        if data_inicio:
            queryset = queryset.filter(data_inicio_colheita__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data_inicio_colheita__lte=data_fim)
        return queryset.distinct()

    def perform_destroy(self, instance):
        exigir_acesso_lote(self.request.user, instance, papeis=PAPEIS_ADMINISTRACAO)
        if instance.status != LoteConjuntoProducao.Status.RASCUNHO:
            raise ProducaoError("Somente lotes em rascunho podem ser excluídos.")
        instance.delete()

    @action(detail=True, methods=("post",))
    def recalcular(self, request, pk=None):
        lote = self.get_object()
        exigir_acesso_lote(request.user, lote, papeis=PAPEIS_GESTAO)
        return Response(self.get_serializer(recalcular_lote(lote)).data)

    @action(detail=True, methods=("post",), url_path="colocar-em-conferencia")
    def conferencia(self, request, pk=None):
        try:
            return Response(self.get_serializer(colocar_em_conferencia(self.get_object(), usuario=request.user)).data)
        except ProducaoError as exc:
            return resposta_erro(exc)

    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        try:
            return Response(self.get_serializer(confirmar_lote(self.get_object(), usuario=request.user)).data)
        except ProducaoError as exc:
            return resposta_erro(exc)

    @action(detail=True, methods=("post",), url_path="ratear-area")
    def ratear_area(self, request, pk=None):
        try:
            ratear_por_area(self.get_object(), usuario=request.user)
            return Response(self.get_serializer(self.get_object()).data)
        except ProducaoError as exc:
            return resposta_erro(exc)

    @action(detail=True, methods=("post",), url_path="ratear-manual")
    def ratear_manual_action(self, request, pk=None):
        try:
            ratear_manual(
                self.get_object(),
                usuario=request.user,
                itens=request.data.get("itens", []),
                justificativa=request.data.get("justificativa", ""),
                exigir_total=bool(request.data.get("distribuir_todo_saldo", True)),
            )
            return Response(self.get_serializer(self.get_object()).data)
        except (ProducaoError, ValueError, TypeError) as exc:
            return resposta_erro(exc)

    @action(detail=True, methods=("post",))
    def transferir(self, request, pk=None):
        lote = self.get_object()
        origem = get_object_or_404(LocalEstoque, pk=request.data.get("local_origem"))
        destino = get_object_or_404(LocalEstoque, pk=request.data.get("local_destino"))
        try:
            movimento = transferir_saldo_conjunto(
                lote,
                usuario=request.user,
                local_origem=origem,
                local_destino=destino,
                quantidade_kg=request.data.get("quantidade_kg", 0),
            )
            return Response(MovimentacaoLoteConjuntoSerializer(movimento).data)
        except ProducaoError as exc:
            return resposta_erro(exc)

    @action(detail=True, methods=("post",), url_path="ajustar-saldo")
    def ajustar_saldo(self, request, pk=None):
        lote = self.get_object()
        local = get_object_or_404(LocalEstoque, pk=request.data.get("local"))
        try:
            movimento = ajustar_saldo_conjunto(
                lote,
                usuario=request.user,
                local=local,
                quantidade_kg=request.data.get("quantidade_kg", 0),
                justificativa=request.data.get("justificativa", ""),
            )
            return Response(MovimentacaoLoteConjuntoSerializer(movimento).data)
        except ProducaoError as exc:
            return resposta_erro(exc)

    @action(detail=True, methods=("post",))
    def encerrar(self, request, pk=None):
        try:
            return Response(self.get_serializer(encerrar_lote(self.get_object(), usuario=request.user)).data)
        except ProducaoError as exc:
            return resposta_erro(exc)

    @action(detail=True, methods=("post",))
    def estornar(self, request, pk=None):
        try:
            return Response(
                self.get_serializer(
                    estornar_lote(
                        self.get_object(),
                        usuario=request.user,
                        motivo=request.data.get("motivo", ""),
                    )
                ).data
            )
        except ProducaoError as exc:
            return resposta_erro(exc)

    @action(detail=True, methods=("get",), url_path="resumo-transportes")
    def transportes(self, request, pk=None):
        lote = self.get_object()
        exigir_acesso_lote(request.user, lote)
        return Response(resumo_transportes(lote))


class CargaLoteConjuntoViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = CargaLoteConjuntoSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        "lote__codigo",
        "motorista__nome",
        "veiculo_cavalo__placa",
        "placa_cavalo_informada",
        "romaneio",
        "destino",
    )
    ordering_fields = ("data_hora", "peso_liquido_kg", "motorista__nome")

    def get_queryset(self):
        lotes = lotes_conjuntos_visiveis(self.request.user).values_list("id", flat=True)
        queryset = CargaLoteConjunto.objects.filter(lote_id__in=lotes).select_related(
            "lote__cultura",
            "motorista",
            "veiculo_cavalo",
            "veiculo_carreta",
            "transportadora",
            "local_armazenagem",
        )
        lote = self.request.query_params.get("lote", "").strip()
        return queryset.filter(lote_id=lote) if lote else queryset

    def perform_create(self, serializer):
        lote = serializer.validated_data["lote"]
        exigir_acesso_lote(self.request.user, lote, papeis=PAPEIS_OPERACAO)
        if lote.status not in {LoteConjuntoProducao.Status.RASCUNHO, LoteConjuntoProducao.Status.CONFERENCIA}:
            raise ProducaoError("Não é possível incluir carga em lote confirmado.")
        serializer.save()

    def perform_update(self, serializer):
        exigir_acesso_lote(self.request.user, serializer.instance.lote, papeis=PAPEIS_OPERACAO)
        serializer.save()

    def perform_destroy(self, instance):
        exigir_acesso_lote(self.request.user, instance.lote, papeis=PAPEIS_GESTAO)
        if instance.lote.status not in {LoteConjuntoProducao.Status.RASCUNHO, LoteConjuntoProducao.Status.CONFERENCIA}:
            raise ProducaoError("Não é possível excluir carga de lote confirmado.")
        lote = instance.lote
        instance.delete()
        recalcular_lote(lote)


class SaidaLoteConjuntoViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = SaidaLoteConjuntoSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("lote__codigo", "romaneio", "motorista__nome", "destino")
    ordering_fields = ("data_hora", "quantidade_kg", "status")

    def get_queryset(self):
        lotes = lotes_conjuntos_visiveis(self.request.user).values_list("id", flat=True)
        queryset = SaidaLoteConjunto.objects.filter(lote_id__in=lotes).select_related(
            "lote", "local_armazenagem", "comprador", "contrato", "motorista", "veiculo_cavalo", "veiculo_carreta"
        )
        lote = self.request.query_params.get("lote", "").strip()
        return queryset.filter(lote_id=lote) if lote else queryset

    def perform_create(self, serializer):
        lote = serializer.validated_data["lote"]
        exigir_acesso_lote(self.request.user, lote, papeis=PAPEIS_OPERACAO)
        serializer.save()

    @action(detail=True, methods=("post",))
    def confirmar(self, request, pk=None):
        try:
            return Response(self.get_serializer(confirmar_saida_conjunta(self.get_object(), usuario=request.user)).data)
        except ProducaoError as exc:
            return resposta_erro(exc)

    @action(detail=True, methods=("post",))
    def estornar(self, request, pk=None):
        try:
            return Response(
                self.get_serializer(
                    estornar_saida_conjunta(
                        self.get_object(),
                        usuario=request.user,
                        motivo=request.data.get("motivo", ""),
                    )
                ).data
            )
        except ProducaoError as exc:
            return resposta_erro(exc)


class SaldoLoteConjuntoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = SaldoLoteConjuntoSerializer

    def get_queryset(self):
        lotes = lotes_conjuntos_visiveis(self.request.user).values_list("id", flat=True)
        queryset = SaldoLoteConjunto.objects.filter(lote_id__in=lotes).select_related("lote", "local_armazenagem")
        lote = self.request.query_params.get("lote", "").strip()
        return queryset.filter(lote_id=lote) if lote else queryset


class MovimentacaoLoteConjuntoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = MovimentacaoLoteConjuntoSerializer

    def get_queryset(self):
        lotes = lotes_conjuntos_visiveis(self.request.user).values_list("id", flat=True)
        queryset = MovimentacaoLoteConjunto.objects.filter(lote_id__in=lotes).select_related(
            "lote", "local_origem", "local_destino", "participante", "cadpro", "criado_por"
        )
        lote = self.request.query_params.get("lote", "").strip()
        return queryset.filter(lote_id=lote) if lote else queryset


class RelatorioLoteConjuntoView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        queryset = lotes_conjuntos_visiveis(request.user).select_related("cultura", "safra", "local_armazenagem").prefetch_related("participantes__propriedade", "cargas__motorista", "cargas__veiculo_cavalo")
        for parametro, campo in (
            ("cultura", "cultura_id"),
            ("safra", "safra_id"),
            ("status", "status"),
            ("propriedade", "participantes__propriedade_id"),
        ):
            valor = request.query_params.get(parametro, "").strip()
            if valor:
                queryset = queryset.filter(**{campo: valor})
        inicio = request.query_params.get("data_inicio", "").strip()
        fim = request.query_params.get("data_fim", "").strip()
        if inicio:
            queryset = queryset.filter(data_inicio_colheita__gte=inicio)
        if fim:
            queryset = queryset.filter(data_inicio_colheita__lte=fim)
        queryset = queryset.distinct()
        linhas = []
        for lote in queryset:
            linhas.append({
                "codigo": lote.codigo,
                "periodo": f"{lote.data_inicio_colheita} a {lote.data_final_colheita or lote.data_inicio_colheita}",
                "cultura": lote.cultura.nome,
                "safra": lote.safra.nome,
                "propriedades": ", ".join(item.propriedade.nome for item in lote.participantes.all()),
                "area_colhida": lote.area_total_colhida_ha,
                "peso_liquido": lote.peso_liquido_total_kg,
                "produtividade": lote.produtividade_kg_ha,
                "saldo_conjunto": sum((item.quantidade_kg for item in lote.saldos_conjuntos.all()), 0),
                "cargas": lote.cargas.count(),
                "status": lote.status,
            })
        formato = request.query_params.get("formato", "csv").lower()
        if formato == "xlsx":
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Lotes conjuntos"
            cabecalhos = list(linhas[0].keys()) if linhas else ["codigo", "periodo", "cultura", "safra", "propriedades", "area_colhida", "peso_liquido", "produtividade", "saldo_conjunto", "cargas", "status"]
            sheet.append(cabecalhos)
            for linha in linhas:
                sheet.append([str(linha[campo]) for campo in cabecalhos])
            output = io.BytesIO()
            workbook.save(output)
            response = HttpResponse(output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response["Content-Disposition"] = 'attachment; filename="lotes-conjuntos.xlsx"'
            return response
        if formato == "pdf":
            pdf_rows = [
                {
                    "data": linha["periodo"],
                    "propriedade": linha["propriedades"],
                    "cadpro": "Conjunto",
                    "cultura": linha["cultura"],
                    "safra": linha["safra"],
                    "peso_liquido_kg": linha["peso_liquido"],
                    "sacas": "Conjunto",
                }
                for linha in linhas
            ]
            response = HttpResponse(export_pdf(pdf_rows), content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="lotes-conjuntos.pdf"'
            return response
        output = io.StringIO()
        cabecalhos = list(linhas[0].keys()) if linhas else ["codigo", "periodo", "cultura", "safra", "propriedades", "area_colhida", "peso_liquido", "produtividade", "saldo_conjunto", "cargas", "status"]
        writer = csv.DictWriter(output, fieldnames=cabecalhos)
        writer.writeheader()
        writer.writerows(linhas)
        response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="lotes-conjuntos.csv"'
        return response
