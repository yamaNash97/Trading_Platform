from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Admin list configuration for user profiles."""

    list_display = ('user', 'display_name', 'created_at')
    search_fields = ('user__username', 'user__email', 'display_name')
