from django.urls import path

from .views import InsightsView
from .chat_local import ChatLocalView

urlpatterns = [path("conversar/", ChatLocalView.as_view(), name="chat-local"), path("insights/", InsightsView.as_view(), name="insights")]
