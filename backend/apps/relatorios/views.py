from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import dashboard_gerencial


class DashboardGerencialView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        propriedade = request.query_params.get("propriedade", "").strip()
        return Response(
            dashboard_gerencial(
                propriedade=int(propriedade) if propriedade else None,
                safra=request.query_params.get("safra", "").strip(),
            )
        )
