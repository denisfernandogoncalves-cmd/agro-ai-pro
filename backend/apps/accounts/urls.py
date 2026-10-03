from django.urls import path

from .views import LogoutView
from .users import CurrentUserView, UserDetailView, UsersView


urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("users/", UsersView.as_view(), name="users"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
