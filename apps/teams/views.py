from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from .forms import TeamCreateForm
from .services import create_team


class CreateTeamView(LoginRequiredMixin, View):
    template_name = "teams/create_team.html"

    def get(self, request):
        form = TeamCreateForm()
        return render(
            request,
            self.template_name,
            {
                "form": form,
            },
        )

    def post(self, request):
        form = TeamCreateForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            try:
                create_team(
                    captain=request.user,
                    form=form,
                )

                return redirect("dashboard:captain_dashboard")

            except ValueError as e:
                form.add_error(
                    None,
                    str(e),
                )

        return render(
            request,
            self.template_name,
            {
                "form": form,
            },
        )