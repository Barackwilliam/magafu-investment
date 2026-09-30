from django.urls import path

from . import views

urlpatterns = [
    path("siku/", views.daily_report, name="report_daily"),
    path("makusanyo/", views.collections_report, name="report_collections"),
    path("mikopo-iliyotolewa/", views.disbursements_report, name="report_disbursements"),
    path("madeni-sugu/", views.overdue_report, name="report_overdue"),
    path("matawi/", views.branches_report, name="report_branches"),
]
