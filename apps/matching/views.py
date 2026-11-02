from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.core import modes
from apps.core.files import private_file_response
from apps.core.uploads import limit_mb
from apps.tutors.models import TutorProfile

from .forms import MatchRequestForm, MessageForm, ReviewForm, TutorReplyForm
from .models import MatchRequest, Message


class MatchRequestCreateView(LoginRequiredMixin, View):
    """學生向某位老師送出家教邀請。"""

    template_name = "matching/request_form.html"

    def get_tutor(self, tutor_id):
        return get_object_or_404(
            TutorProfile.objects.select_related("user", "user__profile").prefetch_related("subjects"),
            id=tutor_id,
        )

    def check_allowed(self, request, tutor):
        """回傳 None 表示可以送出；否則回傳要導向的 response。"""
        if tutor.user_id == request.user.id:
            messages.error(request, "不能邀請自己喔。")
            return redirect("tutors:detail", tutor_id=tutor.id)
        if not tutor.is_accepting:
            messages.error(request, "這位老師目前暫停接案。")
            return redirect("tutors:detail", tutor_id=tutor.id)
        if MatchRequest.objects.filter(
            student=request.user, tutor=tutor, status=MatchRequest.Status.PENDING
        ).exists():
            messages.info(request, "你已經邀請過這位老師，請等待回覆。")
            return redirect("matching:list")
        return None

    def get(self, request, tutor_id):
        tutor = self.get_tutor(tutor_id)
        blocked = self.check_allowed(request, tutor)
        if blocked:
            return blocked

        initial = {}
        subject_id = request.GET.get("subject")
        if subject_id and tutor.subjects.filter(id=subject_id).exists():
            initial["subject"] = subject_id
        form = MatchRequestForm(tutor=tutor, initial=initial)
        return render(request, self.template_name, {"form": form, "tutor": tutor})

    def post(self, request, tutor_id):
        tutor = self.get_tutor(tutor_id)
        blocked = self.check_allowed(request, tutor)
        if blocked:
            return blocked

        form = MatchRequestForm(request.POST, tutor=tutor)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "tutor": tutor}, status=400)

        match = form.save(commit=False)
        match.student = request.user
        match.tutor = tutor
        match.save()
        messages.success(request, f"邀請已送出！{tutor.display_name} 回覆後，你會在這裡看到結果。")
        return redirect("matching:list")


class MyMatchesView(LoginRequiredMixin, View):
    """我的媒合：學生看「我送出的」，老師多一個「我收到的」。"""

    def get(self, request):
        tutor = TutorProfile.objects.filter(user=request.user).first()

        # 每筆媒合附上「對方傳來、我還沒讀」的訊息數
        unread = Count(
            "messages",
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user),
        )
        sent = (
            MatchRequest.objects.filter(student=request.user)
            .select_related("tutor__user__profile", "subject", "review")
            .annotate(unread_count=unread)
        )
        received = MatchRequest.objects.none()
        if tutor:
            received = (
                MatchRequest.objects.filter(tutor=tutor)
                .select_related("student__profile", "subject", "review")
                .annotate(unread_count=unread)
            )

        tab = request.GET.get("tab")
        if tab not in ("sent", "received") or (tab == "received" and not tutor):
            # 老師模式，或老師有待回覆邀請時，預設先看「我收到的」
            has_pending = tutor and received.filter(status=MatchRequest.Status.PENDING).exists()
            teacher_mode = tutor and modes.get_mode(request) == modes.TEACHER
            tab = "received" if (has_pending or teacher_mode) else "sent"

        context = {
            "tab": tab,
            "tutor": tutor,
            "sent": sent,
            "received": received,
            "received_pending": received.filter(status=MatchRequest.Status.PENDING).count() if tutor else 0,
            "reply_form": TutorReplyForm(),
        }
        return render(request, "matching/match_list.html", context)


class MatchRespondView(LoginRequiredMixin, View):
    """老師接受或婉拒邀請。只查得到「寄給自己」的邀請，別人的一律 404。"""

    def post(self, request, match_id, action):
        match = get_object_or_404(
            MatchRequest,
            id=match_id,
            tutor__user=request.user,
            status=MatchRequest.Status.PENDING,
        )
        form = TutorReplyForm(request.POST)
        reply = form.cleaned_data["tutor_reply"] if form.is_valid() else ""

        if action == "accept":
            match.status = MatchRequest.Status.ACCEPTED
            messages.success(request, f"已接受 {match.student_name} 的邀請，現在可以看到對方的聯絡方式了。")
        else:
            match.status = MatchRequest.Status.REJECTED
            messages.info(request, f"已婉拒 {match.student_name} 的邀請。")
        match.tutor_reply = reply
        match.save(update_fields=["status", "tutor_reply", "updated_at"])
        return redirect(f"{reverse('matching:list')}?tab=received")


class MatchCancelView(LoginRequiredMixin, View):
    """學生取消自己送出、尚未回覆的邀請。"""

    def post(self, request, match_id):
        match = get_object_or_404(
            MatchRequest,
            id=match_id,
            student=request.user,
            status=MatchRequest.Status.PENDING,
        )
        match.status = MatchRequest.Status.CANCELLED
        match.save(update_fields=["status", "updated_at"])
        messages.info(request, "邀請已取消。")
        return redirect("matching:list")


class ReviewCreateView(LoginRequiredMixin, View):
    """學生替「已接受」的媒合留下評價，每筆只能評一次。"""

    template_name = "matching/review_form.html"

    def get_match(self, request, match_id):
        return get_object_or_404(
            MatchRequest.objects.select_related("tutor__user__profile", "subject"),
            id=match_id,
            student=request.user,
            status=MatchRequest.Status.ACCEPTED,
        )

    def get(self, request, match_id):
        match = self.get_match(request, match_id)
        if hasattr(match, "review"):
            messages.info(request, "你已經評價過這位老師了。")
            return redirect("tutors:detail", tutor_id=match.tutor_id)
        return render(request, self.template_name, {"form": ReviewForm(), "match": match})

    def post(self, request, match_id):
        match = self.get_match(request, match_id)
        if hasattr(match, "review"):
            return redirect("tutors:detail", tutor_id=match.tutor_id)

        form = ReviewForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "match": match}, status=400)

        review = form.save(commit=False)
        review.match_request = match
        review.save()
        messages.success(request, "感謝你的評價！")
        return redirect("tutors:detail", tutor_id=match.tutor_id)


def get_chat_match(request, match_id):
    """只有媒合成功的兩個人（學生和老師）能進入聊天室，其他人一律 404。"""
    return get_object_or_404(
        MatchRequest.objects.select_related("tutor__user__profile", "student__profile", "subject"),
        Q(student=request.user) | Q(tutor__user=request.user),
        id=match_id,
        status=MatchRequest.Status.ACCEPTED,
    )


def mark_read(match, user):
    """回傳這次標記為已讀的訊息數。"""
    return match.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)


class ChatView(LoginRequiredMixin, View):
    """聊天室頁面；POST 送出訊息。"""

    template_name = "matching/chat.html"

    def get(self, request, match_id):
        # GET 只讀取，不改資料；「標記已讀」交給 ChatReadView（POST）
        match = get_chat_match(request, match_id)
        context = {
            "match": match,
            "chat_messages": match.messages.all(),
            "form": MessageForm(),
            "other_name": match.other_party_name(request.user),
            "is_student": request.user.id == match.student_id,
            "image_limit": limit_mb("image"),
        }
        return render(request, self.template_name, context)

    def post(self, request, match_id):
        match = get_chat_match(request, match_id)
        form = MessageForm(request.POST, request.FILES)
        wants_json = request.headers.get("Accept", "").startswith("application/json")

        if not form.is_valid():
            error = form.first_error()
            if wants_json:
                return JsonResponse({"error": error}, status=400)
            messages.error(request, error)
            return redirect("matching:chat", match_id=match.id)

        message = Message.objects.create(
            match_request=match,
            sender=request.user,
            body=form.cleaned_data["body"],
            image=form.cleaned_data["image"],
        )
        if wants_json:
            return JsonResponse({"message": message.to_dict(request.user)}, status=201)
        return redirect("matching:chat", match_id=match.id)


class ChatReadView(LoginRequiredMixin, View):
    """把對方傳來的訊息標記為已讀。會改變資料，所以只接受 POST。"""

    def post(self, request, match_id):
        match = get_chat_match(request, match_id)
        updated = mark_read(match, request.user)
        return JsonResponse({"marked": updated})


class ChatMessagesView(LoginRequiredMixin, View):
    """回傳 JSON：聊天室每隔幾秒來問「after 這則之後有沒有新訊息」。"""

    def get(self, request, match_id):
        match = get_chat_match(request, match_id)
        after = request.GET.get("after", "0")
        new_messages = match.messages.filter(id__gt=int(after) if after.isdigit() else 0)
        return JsonResponse({"messages": [m.to_dict(request.user) for m in new_messages]})


class ChatImageView(LoginRequiredMixin, View):
    """聊天室的圖片：先用 get_chat_match 確認是聊天的兩人，再從這個聊天室裡找圖片。

    圖片存在 private_media/，沒有公開網址；就算有人拿到這個網址，
    不是聊天的兩人（或沒登入）一律 404，看不到圖片。
    """

    def get(self, request, match_id, message_id):
        match = get_chat_match(request, match_id)
        message = get_object_or_404(match.messages.exclude(image=""), id=message_id)
        return private_file_response(message.image)
