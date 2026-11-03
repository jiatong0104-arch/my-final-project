from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.tutors.models import TutorProfile

from .models import StudentProfile, UserProfile

User = get_user_model()


# ── 同一頁顯示一個人的所有資料：基本資料 / 學生檔案 / 老師檔案 ──────────────
# inline = 「嵌在使用者頁裡的表單」。沒有那份檔案時會顯示空白表單，不填就不會建立。

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "基本資料"
    fields = ("display_name", "phone", "contact_info")


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    verbose_name_plural = "學生檔案"
    fields = ("learning_stage", "subjects", "learning_goal", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("subjects",)


class TutorProfileInline(admin.StackedInline):
    model = TutorProfile
    verbose_name_plural = "老師檔案"
    filter_horizontal = ("subjects",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("headline", "bio", "is_accepting")}),
        ("學歷與認證", {"fields": ("school", "department", "education_level", "education_status", "is_verified")}),
        ("教學", {"fields": ("subjects", "years_of_experience", "hourly_rate_min", "hourly_rate_max", "city", "teaching_mode")}),
        ("其他", {"fields": ("contact_info", "created_at", "updated_at")}),
    )


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "name", "email", "phone", "is_student", "is_tutor", "is_staff")
    list_display_links = ("id", "username")
    list_select_related = ("profile", "student_profile", "tutor_profile")
    search_fields = ("username", "email", "profile__display_name", "profile__phone")
    ordering = ("id",)
    inlines = (UserProfileInline, StudentProfileInline, TutorProfileInline)

    def get_inlines(self, request, obj):
        # 「新增使用者」那一步只設定帳號密碼，存檔後再填各份檔案
        return self.inlines if obj else ()

    @admin.display(description="名稱", ordering="profile__display_name")
    def name(self, user):
        profile = getattr(user, "profile", None)
        return profile.display_name if profile and profile.display_name else "—"

    @admin.display(description="手機")
    def phone(self, user):
        profile = getattr(user, "profile", None)
        return profile.phone_display if profile else ""

    @admin.display(boolean=True, description="學生檔案")
    def is_student(self, user):
        return hasattr(user, "student_profile")

    @admin.display(boolean=True, description="老師檔案")
    def is_tutor(self, user):
        return hasattr(user, "tutor_profile")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """所有學生檔案的總覽；要編輯建議從「使用者」頁進去，一次看到全部資料。"""

    list_display = ("id", "user_number", "name", "learning_stage", "created_at")
    list_display_links = ("id", "name")
    list_filter = ("learning_stage", "subjects")
    list_select_related = ("user__profile",)
    search_fields = ("user__id", "user__username", "user__profile__display_name", "learning_goal")
    filter_horizontal = ("subjects",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="使用者 ID", ordering="user_id")
    def user_number(self, student):
        return student.user_id

    @admin.display(description="名稱")
    def name(self, student):
        profile = getattr(student.user, "profile", None)
        return profile.display_name if profile and profile.display_name else student.user.username
