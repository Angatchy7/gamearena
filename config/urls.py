"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os
from django.contrib import admin
from django.urls import include, path

admin_path = os.getenv("ADMIN_URL", "admin/").strip("/")
admin_path = f"{admin_path}/" if admin_path else "admin/"

urlpatterns = [
    path('', include('apps.core.urls')),
    path(admin_path, admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path("dashboard/", include("apps.dashboard.urls")),
    path("teams/", include("apps.teams.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("tournaments/", include("apps.tournaments.urls")),
]

from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from django.views.static import serve

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)





