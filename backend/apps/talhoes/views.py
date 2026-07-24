from rest_framework import viewsets
from .models import Talhao
from .serializers import TalhaoSerializer


class TalhaoViewSet(viewsets.ModelViewSet):

    queryset = Talhao.objects.all()
    serializer_class = TalhaoSerializer