from rest_framework import viewsets
from .models import PrevisaoClima
from .serializers import PrevisaoClimaSerializer


class PrevisaoClimaViewSet(viewsets.ModelViewSet):

    queryset = PrevisaoClima.objects.all().order_by("-data")

    serializer_class = PrevisaoClimaSerializer