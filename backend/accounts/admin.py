from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Django Admin: a free CRUD UI for every model. Handy for inspecting data while debugging."""

    list_display = ("username", "email", "role", "is_active", "is_staff", "is_sample_data")
    list_filter = ("role", "is_active", "is_staff", "is_sample_data")
    fieldsets = DjangoUserAdmin.fieldsets + (("Helpdesk", {"fields": ("role", "is_sample_data")}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (("Helpdesk", {"fields": ("email", "role")}),)
