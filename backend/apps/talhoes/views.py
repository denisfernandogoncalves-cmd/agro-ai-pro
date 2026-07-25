from rest_framework import viewsets
from .models import Talhao
from .serializers import TalhaoSerializer


class TalhaoViewSet(viewsets.ModelViewSet):

    queryset = Talhao.objects.select_related("propriedade").all()
    serializer_class = TalhaoSerializer
