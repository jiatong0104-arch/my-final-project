from django.urls import path

from .views import (
    TutorDetailView,
    TutorListView,
    TutorProfileCreateView,
    TutorProfileDeleteView,
    TutorProfileUpdateView,
)

app_name = "tutors"

urlpatterns = [
    path("", TutorListView.as_view(), name="list"),
    path("me/create/", TutorProfileCreateView.as_view(), name="profile-create"),
    path("me/edit/", TutorProfileUpdateView.as_view(), name="profile-edit"),
    path("me/delete/", TutorProfileDeleteView.as_view(), name="profile-delete"),
    path("<int:tutor_id>/", TutorDetailView.as_view(), name="detail"),
]
