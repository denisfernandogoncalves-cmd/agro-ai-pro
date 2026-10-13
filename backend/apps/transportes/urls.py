from rest_framework.routers import DefaultRouter
from .views import CaminhaoViewSet, LancamentoViewSet, RemuneracaoViewSet

router = DefaultRouter()
router.register("caminhoes", CaminhaoViewSet, basename="transportes-caminhoes")
router.register("lancamentos", LancamentoViewSet, basename="transportes-lancamentos")
router.register("remuneracoes", RemuneracaoViewSet, basename="transportes-remuneracoes")
urlpatterns = router.urls
