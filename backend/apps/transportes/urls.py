from rest_framework.routers import DefaultRouter
from .views import CaminhaoViewSet, LancamentoViewSet, RemuneracaoViewSet

from .fretes import FreteViewSet

router = DefaultRouter()
router.register("caminhoes", CaminhaoViewSet, basename="transportes-caminhoes")
router.register("lancamentos", LancamentoViewSet, basename="transportes-lancamentos")
router.register("remuneracoes", RemuneracaoViewSet, basename="transportes-remuneracoes")
router.register("fretes", FreteViewSet, basename="transportes-fretes")
urlpatterns = router.urls
