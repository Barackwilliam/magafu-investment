from django.urls import path

from . import views

urlpatterns = [
    path("", views.loan_list, name="loan_list"),
    path("omba/", views.loan_apply, name="loan_apply"),
    path("<int:pk>/", views.loan_detail, name="loan_detail"),
    path("<int:pk>/thibitisha/", views.loan_approve, name="loan_approve"),
    path("<int:pk>/kataa/", views.loan_reject, name="loan_reject"),
    path("<int:pk>/toa/", views.loan_disburse, name="loan_disburse"),
    path("<int:pk>/lipa/", views.loan_pay, name="loan_pay"),
    path("<int:pk>/faini/", views.loan_penalty, name="loan_penalty"),
    path("<int:pk>/futa/", views.loan_write_off, name="loan_write_off"),
    path("<int:pk>/kumbusha/", views.loan_remind, name="loan_remind"),
    path("<int:pk>/statement/", views.loan_statement, name="loan_statement"),
    path("aina/", views.product_list, name="product_list"),
    path("aina/mpya/", views.product_form, name="product_create"),
    path("aina/<int:pk>/", views.product_form, name="product_edit"),
]
