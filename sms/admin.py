from django.contrib import admin

from .models import SmsLog


@admin.register(SmsLog)
class SmsLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "phone", "kind", "status")
    list_filter = ("status", "kind")
