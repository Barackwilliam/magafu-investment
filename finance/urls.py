from django.urls import path

from . import views

urlpatterns = [
    path("", views.cash_list, name="cash_list"),
    path("mpya/", views.cash_create, name="cash_create"),
    path("<int:pk>/futa/", views.cash_delete, name="cash_delete"),
]
