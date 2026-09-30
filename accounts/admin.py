from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (("Magafu", {"fields": ("role", "branch", "phone")}),)
    list_display = ("username", "first_name", "last_name", "role", "branch", "is_active")
