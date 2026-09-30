from django.urls import path

from . import views

urlpatterns = [
    path("", views.sms_log, name="sms_log"),
    path("kumbusha-sugu/", views.remind_overdue, name="sms_remind_overdue"),
]
