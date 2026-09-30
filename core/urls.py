from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tafuta/", views.search, name="search"),
    path("matawi/", views.branch_list, name="branch_list"),
    path("matawi/mpya/", views.branch_form, name="branch_create"),
    path("matawi/<int:pk>/", views.branch_form, name="branch_edit"),
    path("matawi/<int:pk>/hali/", views.branch_toggle, name="branch_toggle"),
    path("matawi/<int:pk>/futa/", views.branch_delete, name="branch_delete"),
]
