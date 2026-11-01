from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


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

    class Degree(models.TextChoices):
        BACHELOR_STUDENT = "bachelor_student", "大學在學"
        BACHELOR = "bachelor", "學士"
        MASTER_STUDENT = "master_student", "碩士在學"
        MASTER = "master", "碩士"
        DOCTOR = "doctor", "博士"

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
    department = models.CharField(max_length=100, verbose_name="系所")
    degree = models.CharField(
        max_length=20,
        choices=Degree.choices,
        default=Degree.BACHELOR,
        verbose_name="學位",
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
        """例如：國立臺灣大學 數學系（學士）"""
        return f"{self.school} {self.department}（{self.get_degree_display()}）"

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
