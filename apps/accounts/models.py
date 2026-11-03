from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="使用者",
    )
    display_name = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="顯示名稱",
    )
    # 以國際格式儲存（+886912345678），畫面上顯示為 0912-345-678
    phone = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="手機號碼",
    )
    # 一個帳號一個聯絡方式，當學生、當老師都用這個（媒合成功後對方才看得到）
    contact_info = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="聯絡方式",
        help_text="例如 LINE ID 或 Email。只有媒合成功的對象看得到。",
    )

    class Meta:
        verbose_name = "基本資料"
        verbose_name_plural = "基本資料"

    def __str__(self):
        return self.display_name or self.user.username

    @property
    def phone_display(self):
        if self.phone and self.phone.startswith("+886") and len(self.phone) == 13:
            local = "0" + self.phone[4:]
            return f"{local[:4]}-{local[4:7]}-{local[7:]}"
        return self.phone or ""


class StudentProfile(models.Model):
    """學生檔案：一位 User 最多一份（一對一）。學生第一次送邀請時自動建立。

    只用來存學生資料、帶入表單預設值，不是權限門檻：沒有這份檔案的人一樣能找老師。
    """

    class LearningStage(models.TextChoices):
        ELEMENTARY = "elementary", "國小"
        JUNIOR = "junior", "國中"
        SENIOR = "senior", "高中"
        COLLEGE = "college", "大學"
        ADULT = "adult", "社會人士"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        verbose_name="使用者",
    )
    # 自動建立時還不知道，所以可以空白
    learning_stage = models.CharField(
        max_length=20,
        choices=LearningStage.choices,
        blank=True,
        verbose_name="學習階段",
    )
    subjects = models.ManyToManyField(
        "tutors.Subject",
        blank=True,
        related_name="interested_students",
        verbose_name="想學的科目",
    )
    learning_goal = models.TextField(
        max_length=1000,
        blank=True,
        verbose_name="學習目標",
        help_text="例如：會考數學拿到 A、準備多益 800 分",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "學生檔案"
        verbose_name_plural = "學生檔案"
        ordering = ("-created_at",)

    def __str__(self):
        profile = getattr(self.user, "profile", None)
        name = profile.display_name if profile and profile.display_name else self.user.username
        return f"#{self.user_id} {name}"
