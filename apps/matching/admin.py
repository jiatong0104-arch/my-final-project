from django.contrib import admin

from .models import MatchRequest, Review


class ReviewInline(admin.StackedInline):
    model = Review
    extra = 0


@admin.register(MatchRequest)
class MatchRequestAdmin(admin.ModelAdmin):
    list_display = ("student", "tutor", "subject", "status", "created_at")
    list_filter = ("status", "subject")
    search_fields = ("student__username", "tutor__user__username")
    readonly_fields = ("created_at", "updated_at")
    inlines = (ReviewInline,)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("match_request", "rating", "created_at")
    list_filter = ("rating",)
