from rest_framework.routers import DefaultRouter
from .views import CaminhaoViewSet, LancamentoViewSet, RemuneracaoViewSet

from .fretes import FreteViewSet
from .motoristas import MotoristaViewSet

router = DefaultRouter()
from apps.maquinas.diesel import CompraDieselViewSet
router.register("compras-diesel", CompraDieselViewSet, basename="compras-diesel")
router.register("motoristas", MotoristaViewSet, basename="transportes-motoristas")
router.register("caminhoes", CaminhaoViewSet, basename="transportes-caminhoes")
router.register("lancamentos", LancamentoViewSet, basename="transportes-lancamentos")
router.register("remuneracoes", RemuneracaoViewSet, basename="transportes-remuneracoes")
router.register("fretes", FreteViewSet, basename="transportes-fretes")
from .emprestimos import EmprestimoViewSet
router.register("emprestimos", EmprestimoViewSet, basename="transportes-emprestimos")
urlpatterns = router.urls
