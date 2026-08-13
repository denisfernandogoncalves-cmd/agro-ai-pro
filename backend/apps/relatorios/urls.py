from django.urls import path

from .views import DashboardGerencialView

urlpatterns = [path("dashboard/", DashboardGerencialView.as_view(), name="dashboard")]
