from django.contrib import admin

from .models import CashEntry


@admin.register(CashEntry)
class CashEntryAdmin(admin.ModelAdmin):
    list_display = ("date", "entry_type", "amount", "branch", "recorded_by")
    list_filter = ("entry_type", "branch")
