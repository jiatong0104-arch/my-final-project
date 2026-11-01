from django.db.models import Avg, Count
from django.views.generic import TemplateView

from apps.matching.models import MatchRequest
from apps.tutors.models import Subject, TutorProfile


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
