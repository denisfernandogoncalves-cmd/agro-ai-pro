from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .grain_enterprise_reports import (
    dashboard_data_enterprise,
    export_csv,
    export_pdf,
    export_xlsx,
    report_data,
)


class ProducaoDashboardEnterpriseView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(dashboard_data_enterprise(request.user, request.query_params))


class RelatorioProducaoEnterpriseView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            report_type, columns, rows = report_data(request.user, request.query_params)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        output_format = request.query_params.get("formato", "json").lower()
        if output_format == "csv":
            response = HttpResponse(
                export_csv(columns, rows),
                content_type="text/csv; charset=utf-8",
            )
            response["Content-Disposition"] = f'attachment; filename="producao-{report_type}.csv"'
            return response
        if output_format == "xlsx":
            response = HttpResponse(
                export_xlsx(columns, rows),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="producao-{report_type}.xlsx"'
            return response
        if output_format == "pdf":
            response = HttpResponse(
                export_pdf(columns, rows, f"Relatório de {report_type}"),
                content_type="application/pdf",
            )
            response["Content-Disposition"] = f'attachment; filename="producao-{report_type}.pdf"'
            return response
        if output_format != "json":
            return Response(
                {"formato": ["Use json, csv, xlsx ou pdf."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "tipo": report_type,
                "columns": [{"key": key, "label": label} for key, label in columns],
                "count": len(rows),
                "results": rows,
            }
        )
