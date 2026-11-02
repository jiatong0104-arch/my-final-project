from django.db.models import Avg, Count
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from apps.matching.models import MatchRequest
from apps.tutors.models import Subject, TutorProfile

from . import modes


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = {
            "tutors": TutorProfile.objects.filter(is_accepting=True).count(),
            "subjects": Subject.objects.count(),
            "matches": MatchRequest.objects.filter(status=MatchRequest.Status.ACCEPTED).count(),
        }
        context["featured_tutors"] = (
            TutorProfile.objects.filter(is_accepting=True)
            .select_related("user__profile")
            .prefetch_related("subjects")
            .annotate(
                avg_rating=Avg("received_requests__review__rating"),
                review_count=Count("received_requests__review", distinct=True),
            )
            .order_by("-avg_rating", "-review_count")[:3]
        )
        return context


class SwitchModeView(View):
    """切換學生／老師模式。會改變 session 的資料，所以只接受 POST。"""

    def post(self, request):
        mode = request.POST.get("mode")
        modes.set_mode(request, mode)

        next_url = request.POST.get("next", "")
        # 只允許跳回本站的網址，避免被利用來導向其他網站（open redirect）
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            next_url = ""
        if not next_url:
            if mode == modes.TEACHER:
                tutor = getattr(request.user, "tutor_profile", None) if request.user.is_authenticated else None
                return redirect("tutors:detail", tutor_id=tutor.id) if tutor else redirect("tutors:profile-create")
            return redirect("tutors:list")
        return redirect(next_url)
