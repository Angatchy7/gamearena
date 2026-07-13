from django.contrib import admin

from .models import Game, Tournament


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "game",
        "organizer",
        "tournament_type",
        "participation_type",
        "status",
        "visibility",
        "start_date",
    )

    list_filter = (
        "game",
        "tournament_type",
        "participation_type",
        "status",
        "visibility",
    )

    search_fields = (
        "name",
        "organizer__username",
    )

    autocomplete_fields = (
        "game",
        "organizer",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }