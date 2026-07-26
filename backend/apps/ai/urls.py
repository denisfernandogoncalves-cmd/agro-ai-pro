from django.urls import path

from .views import InsightsView

urlpatterns = [path("insights/", InsightsView.as_view(), name="insights")]
