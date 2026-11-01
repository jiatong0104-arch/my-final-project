from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.tutors.models import Subject, TutorProfile


class MatchRequest(models.Model):
    """學生送給老師的家教邀請。一位老師可以收到很多筆（多對一）。"""

    class Status(models.TextChoices):
        PENDING = "pending", "等待回覆"
        ACCEPTED = "accepted", "已接受"
        REJECTED = "rejected", "已婉拒"
        CANCELLED = "cancelled", "已取消"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_requests",
        verbose_name="學生",
    )
    tutor = models.ForeignKey(
        TutorProfile,
        on_delete=models.CASCADE,
        related_name="received_requests",
        verbose_name="老師",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="match_requests",
        verbose_name="想上的科目",
    )
    message = models.TextField(
        verbose_name="給老師的話",
        help_text="簡單說明你的程度、目標，或想加強的地方。",
    )
    preferred_schedule = models.CharField(
        max_length=100,
        verbose_name="希望上課時段",
        help_text="例如：每週二、四晚上 7 點後",
    )
    student_contact = models.CharField(
        max_length=100,
        verbose_name="你的聯絡方式",
        help_text="LINE ID 或 Email。老師接受邀請後才看得到。",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="狀態",
    )
    tutor_reply = models.TextField(blank=True, verbose_name="老師回覆")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="送出時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "媒合邀請"
        verbose_name_plural = "媒合邀請"
        ordering = ("-created_at",)
        constraints = [
            # 同一位學生對同一位老師，同時間只能有一筆「等待回覆」的邀請
            models.UniqueConstraint(
                fields=("student", "tutor"),
                condition=models.Q(status="pending"),
                name="one_pending_request_per_pair",
            ),
        ]

    def __str__(self):
        return f"{self.student} → {self.tutor}｜{self.subject}"

    @property
    def student_name(self):
        profile = getattr(self.student, "profile", None)
        if profile and profile.display_name:
            return profile.display_name
        return self.student.username

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_accepted(self):
        return self.status == self.Status.ACCEPTED

    def is_participant(self, user):
        return user.id in (self.student_id, self.tutor.user_id)

    def other_party_name(self, user):
        """聊天室標題：對學生顯示老師名字，對老師顯示學生名字。"""
        return self.tutor.display_name if user.id == self.student_id else self.student_name


class Review(models.Model):
    """評價：只有「已接受」的媒合可以評價一次（一對一）。"""

    match_request = models.OneToOneField(
        MatchRequest,
        on_delete=models.CASCADE,
        related_name="review",
        verbose_name="媒合邀請",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="評分",
    )
    comment = models.TextField(verbose_name="評語")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="評價時間")

    class Meta:
        verbose_name = "評價"
        verbose_name_plural = "評價"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.match_request.tutor}｜{self.rating} 星"


class Message(models.Model):
    """聊天室訊息：媒合成功後，學生與老師在網站上對話。一筆媒合有很多則訊息（多對一）。"""

    match_request = models.ForeignKey(
        MatchRequest,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="媒合邀請",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name="傳送者",
    )
    body = models.TextField(max_length=2000, verbose_name="內容")
    is_read = models.BooleanField(default=False, verbose_name="已讀")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="傳送時間")

    class Meta:
        verbose_name = "聊天訊息"
        verbose_name_plural = "聊天訊息"
        ordering = ("created_at", "id")

    def __str__(self):
        return f"{self.sender}：{self.body[:20]}"

    def to_dict(self, viewer):
        """轉成 JSON 給聊天室的 JavaScript 使用。"""
        from django.utils import timezone

        local = timezone.localtime(self.created_at)
        return {
            "id": self.id,
            "body": self.body,
            "mine": self.sender_id == viewer.id,
            "time": local.strftime("%H:%M"),
            "date": local.strftime("%Y-%m-%d"),
        }
