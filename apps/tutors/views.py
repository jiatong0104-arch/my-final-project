from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.matching.models import MatchRequest, Review

from .forms import TutorProfileForm
from .models import Subject, TutorProfile

SORT_OPTIONS = {
    "rating": ("評價最高", ("-avg_rating", "-review_count", "-created_at")),
    "price_low": ("時薪由低到高", ("hourly_rate_min", "hourly_rate_max", "-created_at")),
    "price_high": ("時薪由高到低", ("-hourly_rate_max", "-hourly_rate_min", "-created_at")),
    "experience": ("年資最多", ("-years_of_experience", "-created_at")),
    "newest": ("最新加入", ("-created_at",)),
}


def with_rating(queryset):
    """替老師加上平均評分與評價數（透過 媒合邀請 → 評價 的關聯計算）。"""
    return queryset.annotate(
        avg_rating=Avg("received_requests__review__rating"),
        review_count=Count("received_requests__review", distinct=True),
    )


class TutorListView(View):
    """老師列表：用查詢參數搜尋、篩選與排序。"""

    def get(self, request):
        params = {
            "q": request.GET.get("q", "").strip(),
            "subject": request.GET.get("subject", ""),
            "level": request.GET.get("level", ""),
            "city": request.GET.get("city", ""),
            "mode": request.GET.get("mode", ""),
            "max_rate": request.GET.get("max_rate", "").strip(),
            "sort": request.GET.get("sort", "rating"),
        }

        tutors = with_rating(
            TutorProfile.objects.filter(is_accepting=True)
            .select_related("user", "user__profile")
            .prefetch_related("subjects")
        )

        if params["q"]:
            keyword = params["q"]
            matched_ids = TutorProfile.objects.filter(
                Q(headline__icontains=keyword)
                | Q(bio__icontains=keyword)
                | Q(school__icontains=keyword)
                | Q(department__icontains=keyword)
                | Q(user__profile__display_name__icontains=keyword)
                | Q(subjects__name__icontains=keyword)
            ).values("id")
            tutors = tutors.filter(id__in=matched_ids)
        if params["subject"].isdigit():
            tutors = tutors.filter(id__in=Subject.objects.filter(id=params["subject"]).values("tutors"))
        if params["level"].isdigit():
            tutors = tutors.filter(id__in=Subject.objects.filter(level=params["level"]).values("tutors"))
        if params["city"] in TutorProfile.City.values:
            tutors = tutors.filter(city=params["city"])
        if params["mode"] == TutorProfile.TeachingMode.ONLINE:
            tutors = tutors.exclude(teaching_mode=TutorProfile.TeachingMode.IN_PERSON)
        elif params["mode"] == TutorProfile.TeachingMode.IN_PERSON:
            tutors = tutors.exclude(teaching_mode=TutorProfile.TeachingMode.ONLINE)
        if params["max_rate"].isdigit():
            # 預算內：老師的最低時薪不超過預算
            tutors = tutors.filter(hourly_rate_min__lte=int(params["max_rate"]))

        if params["sort"] not in SORT_OPTIONS:
            params["sort"] = "rating"
        tutors = tutors.order_by(*SORT_OPTIONS[params["sort"]][1])

        page = Paginator(tutors, 9).get_page(request.GET.get("page"))

        # 換頁時保留目前的篩選條件
        query = request.GET.copy()
        query.pop("page", None)

        active_filters = any(params[key] for key in ("q", "subject", "level", "city", "mode", "max_rate"))

        context = {
            "page": page,
            "params": params,
            "querystring": query.urlencode(),
            "active_filters": active_filters,
            # 篩選選單：官方科目，加上至少有一位老師在教的自訂科目
            "subjects": Subject.objects.filter(Q(is_custom=False) | Q(tutors__isnull=False)).distinct(),
            "levels": Subject.Level.choices,
            "cities": TutorProfile.City.choices,
            "sort_options": [(key, label) for key, (label, _) in SORT_OPTIONS.items()],
        }
        return render(request, "tutors/tutor_list.html", context)


class TutorDetailView(View):
    """老師詳細頁：用路徑參數找到一位老師。"""

    def get(self, request, tutor_id):
        tutor = get_object_or_404(
            with_rating(
                TutorProfile.objects.select_related("user", "user__profile").prefetch_related("subjects")
            ),
            id=tutor_id,
        )
        reviews = (
            Review.objects.filter(match_request__tutor=tutor)
            .select_related("match_request__student__profile", "match_request__subject")
        )

        is_owner = request.user.is_authenticated and tutor.user_id == request.user.id
        pending_request = None
        accepted_request = None
        if request.user.is_authenticated and not is_owner:
            my_requests = MatchRequest.objects.filter(student=request.user, tutor=tutor)
            pending_request = my_requests.filter(status=MatchRequest.Status.PENDING).first()
            accepted_request = my_requests.filter(status=MatchRequest.Status.ACCEPTED).first()

        context = {
            "tutor": tutor,
            "reviews": reviews,
            "is_owner": is_owner,
            "pending_request": pending_request,
            "accepted_request": accepted_request,
        }
        return render(request, "tutors/tutor_detail.html", context)


class TutorProfileCreateView(LoginRequiredMixin, View):
    """成為老師：替目前登入的使用者建立老師檔案。"""

    template_name = "tutors/tutor_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, "tutor_profile"):
            messages.info(request, "你已經有老師檔案了，可以在這裡修改。")
            return redirect("tutors:profile-edit")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {"form": TutorProfileForm(), "is_create": True})

    def post(self, request):
        form = TutorProfileForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "is_create": True}, status=400)

        tutor = form.save(commit=False)
        tutor.user = request.user  # 擁有者一律是目前登入的人，不從表單接收
        tutor.save()
        form.save_m2m()
        messages.success(request, "老師檔案建立完成！學生現在可以找到你了。")
        return redirect("tutors:detail", tutor_id=tutor.id)


class TutorProfileUpdateView(LoginRequiredMixin, View):
    """編輯自己的老師檔案：只會拿到 request.user 自己的那一份。"""

    template_name = "tutors/tutor_form.html"

    def get_tutor(self, request):
        return TutorProfile.objects.filter(user=request.user).first()

    def get(self, request):
        tutor = self.get_tutor(request)
        if tutor is None:
            return redirect("tutors:profile-create")
        return render(request, self.template_name, {"form": TutorProfileForm(instance=tutor), "tutor": tutor})

    def post(self, request):
        tutor = self.get_tutor(request)
        if tutor is None:
            return redirect("tutors:profile-create")

        form = TutorProfileForm(request.POST, instance=tutor)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "tutor": tutor}, status=400)

        form.save()
        messages.success(request, "老師檔案已更新。")
        return redirect("tutors:detail", tutor_id=tutor.id)


class TutorProfileDeleteView(LoginRequiredMixin, View):
    """刪除自己的老師檔案：GET 顯示確認頁，POST 才真的刪除。"""

    template_name = "tutors/tutor_confirm_delete.html"

    def get_tutor(self, request):
        return TutorProfile.objects.filter(user=request.user).first()

    def get(self, request):
        tutor = self.get_tutor(request)
        if tutor is None:
            return redirect("tutors:profile-create")
        requests = MatchRequest.objects.filter(tutor=tutor)
        context = {
            "tutor": tutor,
            # 讓老師知道刪除後會一起消失的資料（on_delete=CASCADE）
            "pending_count": requests.filter(status=MatchRequest.Status.PENDING).count(),
            "accepted_count": requests.filter(status=MatchRequest.Status.ACCEPTED).count(),
            "review_count": Review.objects.filter(match_request__tutor=tutor).count(),
            "message_count": tutor.received_requests.aggregate(total=Count("messages"))["total"],
        }
        return render(request, self.template_name, context)

    def post(self, request):
        tutor = self.get_tutor(request)
        if tutor is None:
            return redirect("tutors:profile-create")
        tutor.delete()
        messages.success(request, "老師檔案已刪除。你的帳號還在，之後想教學可以重新建立。")
        return redirect("core:home")
