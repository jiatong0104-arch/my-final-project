from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("apps.core.urls")),
    path("tutors/", include("apps.tutors.urls")),
    path("matches/", include("apps.matching.urls")),
]
