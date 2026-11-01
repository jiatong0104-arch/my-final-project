from django.contrib import admin

from .models import Subject, TutorProfile


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("__str__", "name", "level", "is_custom")
    list_filter = ("level", "is_custom")
    search_fields = ("name",)


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "headline", "city", "teaching_mode", "hourly_rate_min", "hourly_rate_max", "is_accepting")
    list_filter = ("is_accepting", "city", "teaching_mode", "subjects")
    search_fields = ("user__username", "user__profile__display_name", "headline", "school", "department")
    filter_horizontal = ("subjects",)
    readonly_fields = ("created_at", "updated_at")
