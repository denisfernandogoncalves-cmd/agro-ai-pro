from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import gerar_insights


class InsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        propriedade = request.query_params.get("propriedade", "").strip()
        return Response(
            gerar_insights(propriedade=int(propriedade) if propriedade else None)
        )
