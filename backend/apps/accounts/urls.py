from django.urls import path

from .views import LogoutView
from .users import CurrentUserView, UsersView


urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("users/", UsersView.as_view(), name="users"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
