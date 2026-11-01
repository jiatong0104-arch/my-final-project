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

    class Meta:
        verbose_name = "使用者個人資料"
        verbose_name_plural = "使用者個人資料"

    def __str__(self):
        return self.display_name or self.user.username

    @property
    def phone_display(self):
        if self.phone and self.phone.startswith("+886") and len(self.phone) == 13:
            local = "0" + self.phone[4:]
            return f"{local[:4]}-{local[4:7]}-{local[7:]}"
        return self.phone or ""
