from django.contrib import admin
from .models import Team, TeamMembership


class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_by",
        "is_active",
        "created_at",
    )

    search_fields = ("name",)

    list_filter = ("is_active",)

    prepopulated_fields = {
        "slug": ("name",),
    }


class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "team",
        "user",
        "management_role",
        "game_role",
        "is_active",
    )

    list_filter = (
        "management_role",
        "game_role",
        "is_active",
    )

    search_fields = (
        "team__name",
        "user__username",
    )


admin.site.register(Team, TeamAdmin)
admin.site.register(TeamMembership, TeamMembershipAdmin)