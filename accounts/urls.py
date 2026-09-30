from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("ingia/", views.LoginView.as_view(), name="login"),
    path("toka/", LogoutView.as_view(), name="logout"),
    path("nenosiri/", views.PasswordChangeView.as_view(), name="password_change"),
    path("watumiaji/", views.user_list, name="user_list"),
    path("watumiaji/mpya/", views.user_form, name="user_create"),
    path("watumiaji/<int:pk>/", views.user_form, name="user_edit"),
]
