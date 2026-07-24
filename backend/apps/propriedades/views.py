from rest_framework import viewsets

from .models import Propriedade
from .serializers import PropriedadeSerializer


class PropriedadeViewSet(viewsets.ModelViewSet):

    queryset = Propriedade.objects.all()
    serializer_class = PropriedadeSerializer