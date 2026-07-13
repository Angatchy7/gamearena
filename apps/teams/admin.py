from django.contrib import admin

from .models import Team, TeamMember, TeamInvitation


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "manager",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = (
        "team",
        "user",
        "team_role",
        "is_active",
    )

    list_filter = (
        "team_role",
        "is_active",
    )

    search_fields = (
        "team__name",
        "user__username",
    )


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "team",
        "sender",
        "receiver",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "team__name",
        "receiver__username",
    )