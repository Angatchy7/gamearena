from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path(
        "",
        views.home,
        name="home",
    ),

    path(
        "search/",
        views.SearchView.as_view(),
        name="search",
    ),

    path(
        "search/ajax/",
        views.SearchAjaxView.as_view(),
        name="search_ajax",
    ),
]