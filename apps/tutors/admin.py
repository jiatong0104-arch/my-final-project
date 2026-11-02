from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from .models import Subject, TutorPost, TutorProfile, VerificationRequest


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("__str__", "name", "level", "is_custom")
    list_filter = ("level", "is_custom")
    search_fields = ("name",)


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "headline", "education_label", "is_verified", "city", "hourly_rate_min", "hourly_rate_max", "is_accepting")
    list_filter = ("is_verified", "is_accepting", "education_level", "city", "teaching_mode", "subjects")
    search_fields = ("user__username", "user__profile__display_name", "headline", "school", "department")
    filter_horizontal = ("subjects",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="學歷")
    def education_label(self, tutor):
        return tutor.education_label


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    """審核流程：打開證件 → 對照「申請時填寫的學歷」→ 勾選後執行「通過」或「退回」。

    退回前先在列表的「審核說明」欄填寫原因並儲存，老師會在認證頁看到。
    """

    list_display = ("tutor", "education_snapshot", "document_link", "status", "admin_note", "submitted_at")
    list_editable = ("admin_note",)
    list_filter = ("status",)
    search_fields = ("tutor__user__profile__display_name", "education_snapshot")
    readonly_fields = ("tutor", "education_snapshot", "document_link", "status", "submitted_at", "reviewed_at", "reviewed_by")
    fields = ("tutor", "education_snapshot", "document_link", "status", "admin_note", "submitted_at", "reviewed_at", "reviewed_by")
    actions = ("approve", "reject")

    def has_add_permission(self, request):
        return False  # 申請只能由老師自己送出

    @admin.display(description="證件")
    def document_link(self, obj):
        if not obj.document:
            return "（審核完成，已刪除）"
        url = reverse("tutors:verification-document", args=[obj.id])
        return format_html('<a href="{}" target="_blank" rel="noopener">開啟證件</a>', url)

    def _finish(self, request, queryset, status):
        done = 0
        for verification in queryset.filter(status=VerificationRequest.Status.PENDING).select_related("tutor"):
            verification.finish(status, request.user, verification.admin_note)
            done += 1
        return done

    @admin.action(description="通過：給老師「已認證」標章，並刪除證件檔案")
    def approve(self, request, queryset):
        done = self._finish(request, queryset, VerificationRequest.Status.APPROVED)
        self.message_user(request, f"已通過 {done} 筆申請。", messages.SUCCESS)

    @admin.action(description="退回：不給標章，並刪除證件檔案（請先填寫審核說明）")
    def reject(self, request, queryset):
        if queryset.filter(status=VerificationRequest.Status.PENDING, admin_note="").exists():
            self.message_user(request, "請先在「審核說明」寫下退回原因並儲存，老師才知道要怎麼補件。", messages.ERROR)
            return
        done = self._finish(request, queryset, VerificationRequest.Status.REJECTED)
        self.message_user(request, f"已退回 {done} 筆申請。", messages.WARNING)


@admin.register(TutorPost)
class TutorPostAdmin(admin.ModelAdmin):
    """動態是公開內容，管理員可以下架不當貼文。"""

    list_display = ("tutor", "short_body", "has_image", "has_video", "created_at")
    search_fields = ("tutor__user__profile__display_name", "body")
    readonly_fields = ("tutor", "created_at")

    @admin.display(description="內容")
    def short_body(self, post):
        return post.body[:40]

    @admin.display(boolean=True, description="照片")
    def has_image(self, post):
        return bool(post.image)

    @admin.display(boolean=True, description="影片")
    def has_video(self, post):
        return bool(post.video)
