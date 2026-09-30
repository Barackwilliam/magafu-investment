from django.urls import path

from . import views

urlpatterns = [
    path("", views.customer_list, name="customer_list"),
    path("mpya/", views.customer_form, name="customer_create"),
    path("<int:pk>/", views.customer_detail, name="customer_detail"),
    path("<int:pk>/hariri/", views.customer_form, name="customer_edit"),
]
