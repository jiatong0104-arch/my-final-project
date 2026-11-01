from django.db.models import Q

from .models import MatchRequest, Message


def pending_requests(request):
    """導覽列的提醒數字：老師待回覆的邀請 + 聊天室未讀訊息。"""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    pending = MatchRequest.objects.filter(
        tutor__user=user,
        status=MatchRequest.Status.PENDING,
    ).count()
    unread = (
        Message.objects.filter(is_read=False)
        .filter(Q(match_request__student=user) | Q(match_request__tutor__user=user))
        .exclude(sender=user)
        .count()
    )
    return {
        "pending_request_count": pending,
        "unread_message_count": unread,
        "nav_badge_count": pending + unread,
    }
