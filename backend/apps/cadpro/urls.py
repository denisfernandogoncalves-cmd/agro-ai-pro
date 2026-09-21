from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CADProViewSet


router = DefaultRouter()
router.register("", CADProViewSet, basename="cadpro")

urlpatterns = [path("", include(router.urls))]
