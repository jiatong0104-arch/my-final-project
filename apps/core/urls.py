from django.urls import path

from .views import HomeView, SwitchModeView

app_name = "core"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("mode/", SwitchModeView.as_view(), name="switch-mode"),
]
