from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)

from .forms import TournamentCreateForm as TournamentForm
from .models import Tournament


class TournamentListView(ListView):

    model = Tournament

    template_name = "tournaments/list.html"

    context_object_name = "tournaments"

    paginate_by = 12

    def get_queryset(self):
        qs = (
            Tournament.objects
            .select_related("organizer", "game")
            .annotate(total_registrations=Count("registrations"))
            .order_by("-created_at")
        )
        game_slug = self.request.GET.get("game", "").strip()
        if game_slug:
            qs = qs.filter(game__slug=game_slug)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_game_slug"] = self.request.GET.get("game", "").strip()
        return ctx


class MyTournamentListView(LoginRequiredMixin, ListView):

    model = Tournament

    template_name = "tournaments/my_list.html"

    context_object_name = "tournaments"

    paginate_by = 12

    def get_queryset(self):

        return (
            Tournament.objects
            .filter(
                organizer=self.request.user
            )
            .annotate(
                total_registrations=Count("registrations")
            )
            .order_by("-created_at")
        )


class TournamentDetailView(DetailView):

    model = Tournament

    slug_field = "slug"

    slug_url_kwarg = "slug"

    context_object_name = "tournament"

    template_name = "tournaments/detail.html"

    def get_queryset(self):

        return (
            Tournament.objects
            .select_related(
                "organizer",
                "game",
                "champion",
            )
            .prefetch_related(
                "registrations__team",
                "registrations__team__manager",
                "rounds__matches__team_one",
                "rounds__matches__team_two",
                "rounds__matches__winner",
            )
        )



class TournamentCreateView(LoginRequiredMixin, CreateView):

    model = Tournament

    form_class = TournamentForm

    template_name = "tournaments/create.html"

    def form_valid(self, form):

        tournament = form.save(commit=False)

        tournament.organizer = self.request.user

        tournament.save()

        messages.success(
            self.request,
            "Tournament created successfully.",
        )

        return redirect(
            "tournaments:dashboard",
            slug=tournament.slug,
        )


class TournamentUpdateView(LoginRequiredMixin, UpdateView):

    model = Tournament

    form_class = TournamentForm

    slug_field = "slug"

    slug_url_kwarg = "slug"

    template_name = "tournaments/edit.html"

    def get_queryset(self):

        return Tournament.objects.filter(
            organizer=self.request.user,
        )

    def form_valid(self, form):

        messages.success(
            self.request,
            "Tournament updated successfully.",
        )

        return super().form_valid(form)

    def get_success_url(self):

        return reverse_lazy(
            "tournaments:dashboard",
            kwargs={
                "slug": self.object.slug,
            },
        )


class TournamentDeleteView(LoginRequiredMixin, DeleteView):

    model = Tournament

    slug_field = "slug"

    slug_url_kwarg = "slug"

    template_name = "tournaments/delete.html"

    success_url = reverse_lazy(
        "tournaments:my_list",
    )

    def get_queryset(self):

        return Tournament.objects.filter(
            organizer=self.request.user,
        )

    def delete(self, request, *args, **kwargs):

        messages.success(
            request,
            "Tournament deleted successfully.",
        )

        return super().delete(
            request,
            *args,
            **kwargs,
        )