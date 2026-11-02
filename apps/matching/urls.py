from django.urls import path

from .views import (
    ChatImageView,
    ChatMessagesView,
    ChatReadView,
    ChatView,
    MatchCancelView,
    MatchRequestCreateView,
    MatchRespondView,
    MyMatchesView,
    ReviewCreateView,
)

app_name = "matching"

urlpatterns = [
    path("", MyMatchesView.as_view(), name="list"),
    path("new/<int:tutor_id>/", MatchRequestCreateView.as_view(), name="create"),
    path("<int:match_id>/accept/", MatchRespondView.as_view(), {"action": "accept"}, name="accept"),
    path("<int:match_id>/reject/", MatchRespondView.as_view(), {"action": "reject"}, name="reject"),
    path("<int:match_id>/cancel/", MatchCancelView.as_view(), name="cancel"),
    path("<int:match_id>/review/", ReviewCreateView.as_view(), name="review"),
    path("<int:match_id>/chat/", ChatView.as_view(), name="chat"),
    path("<int:match_id>/chat/messages/", ChatMessagesView.as_view(), name="chat-messages"),
    path("<int:match_id>/chat/read/", ChatReadView.as_view(), name="chat-read"),
    path("<int:match_id>/chat/images/<int:message_id>/", ChatImageView.as_view(), name="chat-image"),
]
