from django.urls import path

from .views import (
    TutorDetailView,
    TutorPostCreateView,
    TutorPostDeleteView,
    TutorVerificationView,
    VerificationDocumentView,
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
    path("me/verify/", TutorVerificationView.as_view(), name="verify"),
    path("me/posts/", TutorPostCreateView.as_view(), name="post-create"),
    path("me/posts/<int:post_id>/delete/", TutorPostDeleteView.as_view(), name="post-delete"),
    path("verifications/<int:verification_id>/document/", VerificationDocumentView.as_view(), name="verification-document"),
    path("<int:tutor_id>/", TutorDetailView.as_view(), name="detail"),
]
