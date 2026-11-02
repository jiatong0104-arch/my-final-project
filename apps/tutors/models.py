from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.core.uploads import RandomName, get_private_storage


class Subject(models.Model):
    """可教授的科目，例如「國中數學」。由管理員在 Admin 維護。"""

    class Level(models.IntegerChoices):
        ELEMENTARY = 1, "國小"
        JUNIOR = 2, "國中"
        SENIOR = 3, "高中"
        COLLEGE = 4, "大學"
        GENERAL = 5, "不分年級"

    name = models.CharField(max_length=50, verbose_name="科目名稱")
    level = models.PositiveSmallIntegerField(
        choices=Level.choices,
        default=Level.GENERAL,
        verbose_name="年級",
    )
    is_custom = models.BooleanField(
        default=False,
        verbose_name="老師自行新增",
        help_text="老師在「其他」欄位自行輸入的科目。",
    )

    class Meta:
        verbose_name = "科目"
        verbose_name_plural = "科目"
        ordering = ("level", "name")
        constraints = [
            models.UniqueConstraint(fields=("name", "level"), name="unique_subject_per_level"),
        ]

    def __str__(self):
        if self.level == self.Level.GENERAL:
            return self.name
        return f"{self.get_level_display()}{self.name}"


class TutorProfile(models.Model):
    """老師檔案：一位 User 最多一份（一對一）。有這份檔案的人就是老師。"""

    class City(models.TextChoices):
        TAIPEI = "taipei", "台北市"
        NEW_TAIPEI = "new_taipei", "新北市"
        TAOYUAN = "taoyuan", "桃園市"
        TAICHUNG = "taichung", "台中市"
        TAINAN = "tainan", "台南市"
        KAOHSIUNG = "kaohsiung", "高雄市"
        OTHER = "other", "其他縣市"

    class EducationLevel(models.TextChoices):
        HIGH_SCHOOL = "high_school", "高中職"
        ASSOCIATE = "associate", "專科"
        BACHELOR = "bachelor", "大學"
        MASTER = "master", "碩士"
        DOCTOR = "doctor", "博士"

    class EducationStatus(models.TextChoices):
        STUDYING = "studying", "在學"
        GRADUATED = "graduated", "畢業"

    class TeachingMode(models.TextChoices):
        ONLINE = "online", "線上"
        IN_PERSON = "in_person", "面授"
        BOTH = "both", "線上、面授皆可"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tutor_profile",
        verbose_name="使用者",
    )
    headline = models.CharField(
        max_length=60,
        verbose_name="一句話介紹",
        help_text="例如：讓數學不再可怕的台大電機學長",
    )
    bio = models.TextField(max_length=5000, verbose_name="自我介紹與教學方式")
    school = models.CharField(max_length=100, verbose_name="學校")
    # 高中職不用填系所，所以可以空白
    department = models.CharField(max_length=100, blank=True, verbose_name="系所")
    education_level = models.CharField(
        max_length=20,
        choices=EducationLevel.choices,
        default=EducationLevel.BACHELOR,
        verbose_name="最高學歷",
    )
    education_status = models.CharField(
        max_length=20,
        choices=EducationStatus.choices,
        default=EducationStatus.GRADUATED,
        verbose_name="在學／畢業",
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="已認證",
        help_text="管理員審核學生證或畢業證書後打勾。修改學歷時會自動取消，需要重新審核。",
    )
    years_of_experience = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(50)],
        verbose_name="教學年資（年）",
    )
    # 時薪是一個區間：不同科目、年級的收費可能不同
    hourly_rate_min = models.PositiveIntegerField(
        validators=[MinValueValidator(100), MaxValueValidator(5000)],
        verbose_name="最低時薪",
    )
    hourly_rate_max = models.PositiveIntegerField(
        validators=[MinValueValidator(100), MaxValueValidator(5000)],
        verbose_name="最高時薪",
    )
    city = models.CharField(max_length=20, choices=City.choices, verbose_name="所在縣市")
    teaching_mode = models.CharField(
        max_length=20,
        choices=TeachingMode.choices,
        default=TeachingMode.BOTH,
        verbose_name="上課方式",
    )
    subjects = models.ManyToManyField(
        Subject,
        related_name="tutors",
        verbose_name="可教科目",
    )
    contact_info = models.CharField(
        max_length=100,
        verbose_name="聯絡方式",
        help_text="例如 LINE ID 或 Email。只有你接受邀請的學生看得到。",
    )
    is_accepting = models.BooleanField(default=True, verbose_name="開放接案")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "老師檔案"
        verbose_name_plural = "老師檔案"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hourly_rate_min__lte=models.F("hourly_rate_max")),
                name="rate_min_not_above_max",
                violation_error_message="最高時薪不能低於最低時薪。",
            ),
        ]

    def __str__(self):
        return self.display_name

    @property
    def education(self):
        """例如：國立臺灣大學 數學系（大學畢業）、建國高中（高中職在學）"""
        place = f"{self.school} {self.department}".strip()
        return f"{place}（{self.education_label}）"

    @property
    def education_label(self):
        return f"{self.get_education_level_display()}{self.get_education_status_display()}"

    @property
    def rate_display(self):
        if self.hourly_rate_min == self.hourly_rate_max:
            return f"${self.hourly_rate_min:,}"
        return f"${self.hourly_rate_min:,}–{self.hourly_rate_max:,}"

    @property
    def display_name(self):
        profile = getattr(self.user, "profile", None)
        if profile and profile.display_name:
            return profile.display_name
        return self.user.username

    @property
    def initial(self):
        return self.display_name[:1].upper()


class VerificationRequest(models.Model):
    """老師身分認證：上傳學生證（在學）或畢業證書（畢業），由管理員在後台審核。

    證件是敏感個資：存在 private_media/，沒有公開網址，只有管理員能透過 View 看；
    審核完成（通過或退回）就刪除檔案，只留下審核紀錄。
    """

    class Status(models.TextChoices):
        PENDING = "pending", "審核中"
        APPROVED = "approved", "已通過"
        REJECTED = "rejected", "未通過"

    tutor = models.ForeignKey(
        TutorProfile,
        on_delete=models.CASCADE,
        related_name="verifications",
        verbose_name="老師",
    )
    document = models.FileField(
        upload_to=RandomName("verification"),
        storage=get_private_storage,
        blank=True,
        verbose_name="證件檔案",
    )
    education_snapshot = models.CharField(
        max_length=200,
        verbose_name="申請時填寫的學歷",
        help_text="審核時對照證件上的學校、系所是否相符。",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="狀態",
    )
    admin_note = models.CharField(
        max_length=200, blank=True, verbose_name="審核說明",
        help_text="未通過時寫給老師看的原因，例如「照片模糊，看不清楚學校名稱」。",
    )
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="申請時間")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="審核時間")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="審核者",
    )

    class Meta:
        verbose_name = "身分認證申請"
        verbose_name_plural = "身分認證申請"
        ordering = ("-submitted_at",)
        constraints = [
            # 同一位老師同時只能有一筆審核中的申請
            models.UniqueConstraint(
                fields=("tutor",),
                condition=models.Q(status="pending"),
                name="one_pending_verification_per_tutor",
            ),
        ]

    def __str__(self):
        return f"{self.tutor.display_name}（{self.get_status_display()}）"

    def finish(self, status, reviewer, note=""):
        """審核完成：更新狀態、老師的標章，並刪除證件檔案。"""
        from django.utils import timezone

        self.status = status
        self.admin_note = note
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        if self.document:
            self.document.delete(save=False)
        self.save()
        if status == self.Status.APPROVED:
            TutorProfile.objects.filter(pk=self.tutor_id).update(is_verified=True)


class TutorPost(models.Model):
    """老師主頁的動態：一段文字，可以附一張照片或一部影片（二選一）。"""

    tutor = models.ForeignKey(
        TutorProfile,
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name="老師",
    )
    body = models.TextField(max_length=3000, blank=True, verbose_name="內容")
    image = models.ImageField(upload_to=RandomName("posts/images"), blank=True, verbose_name="照片")
    video = models.FileField(upload_to=RandomName("posts/videos"), blank=True, verbose_name="影片")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="發布時間")

    class Meta:
        verbose_name = "老師動態"
        verbose_name_plural = "老師動態"
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"{self.tutor.display_name}：{self.body[:20] or '（照片／影片）'}"


@receiver(post_delete, sender=TutorPost)
@receiver(post_delete, sender=VerificationRequest)
def delete_uploaded_files(sender, instance, **kwargs):
    """資料刪除後，一起刪掉硬碟上的檔案（包含刪除老師檔案時連帶刪除的貼文）。"""
    for name in ("image", "video", "document"):
        file = getattr(instance, name, None)
        if file:
            file.delete(save=False)
