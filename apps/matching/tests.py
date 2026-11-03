from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import UserProfile
from apps.core.testing import TempMediaMixin, make_image
from apps.tutors.models import Subject, TutorProfile

from .models import MatchRequest, Message, Review

User = get_user_model()


def make_tutor(username, subject, **extra):
    user = User.objects.create_user(username=username, password="pass12345")
    UserProfile.objects.create(user=user, display_name=f"{username} 老師")
    data = {
        "headline": "好老師",
        "bio": "介紹",
        "school": "國立臺灣大學",
        "department": "數學系",
        "hourly_rate_min": 800,
        "hourly_rate_max": 800,
        "city": "taipei",
        "contact_info": f"LINE：{username}",
    }
    data.update(extra)
    tutor = TutorProfile.objects.create(user=user, **data)
    tutor.subjects.add(subject)
    return tutor


class MatchingFlowTests(TestCase):
    def setUp(self):
        self.math = Subject.objects.create(name="數學", level=Subject.Level.JUNIOR)
        self.english = Subject.objects.create(name="英文", level=Subject.Level.JUNIOR)
        self.tutor = make_tutor("teacher", self.math)
        self.student = User.objects.create_user(username="student", password="pass12345")
        self.request_data = {
            "subject": self.math.id,
            "preferred_schedule": "週六下午",
            "message": "想加強函數",
            "student_contact": "LINE：student",
        }

    def send_request(self):
        self.client.login(username="student", password="pass12345")
        return self.client.post(reverse("matching:create", args=[self.tutor.id]), self.request_data)

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(reverse("matching:create", args=[self.tutor.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_login"), response["Location"])

    def test_student_can_send_request(self):
        response = self.send_request()
        self.assertRedirects(response, reverse("matching:list"))
        match = MatchRequest.objects.get()
        self.assertEqual(match.student, self.student)
        self.assertEqual(match.status, MatchRequest.Status.PENDING)

    def test_cannot_request_subject_tutor_does_not_teach(self):
        self.client.login(username="student", password="pass12345")
        data = {**self.request_data, "subject": self.english.id}
        response = self.client.post(reverse("matching:create", args=[self.tutor.id]), data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(MatchRequest.objects.exists())

    def test_cannot_send_duplicate_pending_request(self):
        self.send_request()
        self.send_request()
        self.assertEqual(MatchRequest.objects.count(), 1)

    def test_tutor_cannot_invite_self(self):
        self.client.login(username="teacher", password="pass12345")
        self.client.post(reverse("matching:create", args=[self.tutor.id]), self.request_data)
        self.assertFalse(MatchRequest.objects.exists())

    def test_contact_hidden_until_accepted(self):
        self.send_request()
        response = self.client.get(reverse("matching:list"))
        self.assertNotContains(response, "LINE：teacher")

        self.client.login(username="teacher", password="pass12345")
        response = self.client.get(reverse("matching:list") + "?tab=received")
        self.assertNotContains(response, "LINE：student")

    def test_tutor_accepts_and_both_see_contact(self):
        self.send_request()
        match = MatchRequest.objects.get()

        self.client.login(username="teacher", password="pass12345")
        self.client.post(reverse("matching:accept", args=[match.id]), {"tutor_reply": "好的"})
        match.refresh_from_db()
        self.assertEqual(match.status, MatchRequest.Status.ACCEPTED)
        self.assertEqual(match.tutor_reply, "好的")
        response = self.client.get(reverse("matching:list") + "?tab=received")
        self.assertContains(response, "LINE：student")

        self.client.login(username="student", password="pass12345")
        response = self.client.get(reverse("matching:list"))
        self.assertContains(response, "LINE：teacher")

    def test_other_user_cannot_accept(self):
        self.send_request()
        match = MatchRequest.objects.get()
        User.objects.create_user(username="stranger", password="pass12345")
        self.client.login(username="stranger", password="pass12345")
        response = self.client.post(reverse("matching:accept", args=[match.id]))
        self.assertEqual(response.status_code, 404)
        match.refresh_from_db()
        self.assertEqual(match.status, MatchRequest.Status.PENDING)

    def test_student_can_cancel_pending_request(self):
        self.send_request()
        match = MatchRequest.objects.get()
        self.client.post(reverse("matching:cancel", args=[match.id]))
        match.refresh_from_db()
        self.assertEqual(match.status, MatchRequest.Status.CANCELLED)

    def test_review_only_after_accept_and_only_once(self):
        self.send_request()
        match = MatchRequest.objects.get()
        review_url = reverse("matching:review", args=[match.id])

        response = self.client.post(review_url, {"rating": 5, "comment": "很棒"})
        self.assertEqual(response.status_code, 404)

        match.status = MatchRequest.Status.ACCEPTED
        match.save()
        self.client.post(review_url, {"rating": 5, "comment": "很棒"})
        self.client.post(review_url, {"rating": 1, "comment": "第二次"})
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.get().rating, 5)


class TutorProfileTests(TestCase):
    def setUp(self):
        self.math = Subject.objects.create(name="數學", level=Subject.Level.SENIOR)
        self.user = User.objects.create_user(username="newbie", password="pass12345")
        self.form_data = {
            "headline": "物理系學長",
            "subjects": [self.math.id],
            "bio": "我會用例子教你",
            "school": "清大",
            "department_choice": "物理學系",
            "education_level": "master",
            "education_status": "graduated",
            "years_of_experience": 2,
            "hourly_rate_min": 700,
            "hourly_rate_max": 900,
            "city": "taipei",
            "teaching_mode": "online",
            "contact_info": "LINE：newbie",
            "is_accepting": "on",
        }

    def test_create_profile_sets_owner_to_current_user(self):
        self.client.login(username="newbie", password="pass12345")
        response = self.client.post(reverse("tutors:profile-create"), self.form_data)
        tutor = TutorProfile.objects.get()
        self.assertEqual(tutor.user, self.user)
        self.assertRedirects(response, reverse("tutors:detail", args=[tutor.id]))
        self.assertEqual(list(tutor.subjects.all()), [self.math])

    def test_profile_requires_subject_and_valid_rate(self):
        self.client.login(username="newbie", password="pass12345")
        data = {**self.form_data, "subjects": [], "hourly_rate_min": 10}
        response = self.client.post(reverse("tutors:profile-create"), data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(TutorProfile.objects.exists())

    def test_edit_only_changes_own_profile(self):
        other = make_tutor("other", self.math)
        self.client.login(username="newbie", password="pass12345")
        self.client.post(reverse("tutors:profile-create"), self.form_data)
        self.client.post(reverse("tutors:profile-edit"), {**self.form_data, "hourly_rate_max": 999})
        other.refresh_from_db()
        self.assertEqual(other.hourly_rate_max, 800)
        self.assertEqual(TutorProfile.objects.get(user=self.user).hourly_rate_max, 999)

    def test_list_filters(self):
        make_tutor("cheap", self.math, hourly_rate_min=500, hourly_rate_max=900, teaching_mode="online")
        make_tutor("pricey", self.math, hourly_rate_min=1500, hourly_rate_max=2000, teaching_mode="in_person", city="tainan")
        make_tutor("paused", self.math, is_accepting=False)
        url = reverse("tutors:list")

        names = lambda r: {t.user.username for t in r.context["page"].object_list}
        self.assertEqual(names(self.client.get(url)), {"cheap", "pricey"})
        self.assertEqual(names(self.client.get(url, {"max_rate": 800})), {"cheap"})
        self.assertEqual(names(self.client.get(url, {"mode": "online"})), {"cheap"})
        self.assertEqual(names(self.client.get(url, {"city": "tainan"})), {"pricey"})
        self.assertEqual(names(self.client.get(url, {"q": "cheap 老師"})), {"cheap"})

    def test_signup_creates_profile_and_redirects_to_tutor_form(self):
        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "fresh@example.com",
                "phone": "0912-345-678",
                "password1": "Strong-pass-123",
                "password2": "Strong-pass-123",
                "display_name": "新老師",
                "next": reverse("tutors:profile-create"),
            },
        )
        self.assertRedirects(response, reverse("tutors:profile-create"))
        user = User.objects.get(email="fresh@example.com")
        self.assertEqual(user.profile.display_name, "新老師")
        self.assertEqual(user.profile.phone, "+886912345678")

    def test_school_other_and_custom_subjects(self):
        self.client.login(username="newbie", password="pass12345")
        data = {
            **self.form_data,
            "school": "加州大學柏克萊分校",
            "subjects": [],
            "other_subjects_1": "作文、閱讀理解",
        }
        response = self.client.post(reverse("tutors:profile-create"), data)
        tutor = TutorProfile.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(tutor.school, "加州大學柏克萊分校")
        names = sorted(tutor.subjects.values_list("name", flat=True))
        self.assertEqual(names, ["作文", "閱讀理解"])
        self.assertTrue(all(tutor.subjects.values_list("is_custom", flat=True)))

    def test_school_required(self):
        self.client.login(username="newbie", password="pass12345")
        response = self.client.post(reverse("tutors:profile-create"), {**self.form_data, "school": "  "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("school", response.context["form"].errors)

    def test_school_alias_saved_as_full_name(self):
        self.client.login(username="newbie", password="pass12345")
        self.client.post(reverse("tutors:profile-create"), {**self.form_data, "school": "國立台灣 大學"})
        self.assertEqual(TutorProfile.objects.get().school, "國立臺灣大學")

    def test_rate_range_must_be_ordered(self):
        self.client.login(username="newbie", password="pass12345")
        data = {**self.form_data, "hourly_rate_min": 1200, "hourly_rate_max": 800}
        response = self.client.post(reverse("tutors:profile-create"), data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("hourly_rate_max", response.context["form"].errors)

    def test_bio_limited_to_5000_characters(self):
        self.client.login(username="newbie", password="pass12345")
        data = {**self.form_data, "bio": "字" * 5001}
        response = self.client.post(reverse("tutors:profile-create"), data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("bio", response.context["form"].errors)

    def test_max_rate_filter_uses_lowest_rate(self):
        make_tutor("ranged", self.math, hourly_rate_min=600, hourly_rate_max=1200)
        response = self.client.get(reverse("tutors:list"), {"max_rate": 700})
        self.assertEqual([t.user.username for t in response.context["page"].object_list], ["ranged"])


class DeleteProfileTests(TestCase):
    def setUp(self):
        self.math = Subject.objects.create(name="數學", level=Subject.Level.JUNIOR)
        self.tutor = make_tutor("teacher", self.math)
        self.other = make_tutor("other", self.math)
        student = User.objects.create_user(username="student", password="pass12345")
        MatchRequest.objects.create(
            student=student, tutor=self.tutor, subject=self.math,
            message="hi", preferred_schedule="週六", student_contact="LINE",
        )
        self.url = reverse("tutors:profile-delete")

    def test_get_shows_confirmation_without_deleting(self):
        self.client.login(username="teacher", password="pass12345")
        response = self.client.get(self.url)
        self.assertContains(response, "等待回覆 1 筆")
        self.assertTrue(TutorProfile.objects.filter(id=self.tutor.id).exists())

    def test_post_deletes_only_own_profile(self):
        self.client.login(username="teacher", password="pass12345")
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("core:home"))
        self.assertFalse(TutorProfile.objects.filter(id=self.tutor.id).exists())
        self.assertTrue(TutorProfile.objects.filter(id=self.other.id).exists())
        self.assertTrue(User.objects.filter(username="teacher").exists())
        self.assertFalse(MatchRequest.objects.exists())

    def test_anonymous_cannot_delete(self):
        self.client.post(self.url)
        self.assertEqual(TutorProfile.objects.count(), 2)


class ErrorPageTests(TestCase):
    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_custom_404_page(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "找不到這個頁面", status_code=404)


class LoginTests(TestCase):
    def setUp(self):
        from allauth.account.models import EmailAddress

        self.user = User.objects.create_user(username="amy", email="amy@example.com", password="pass12345")
        EmailAddress.objects.create(user=self.user, email="amy@example.com", primary=True, verified=True)
        UserProfile.objects.create(user=self.user, display_name="Amy", phone="+886912000111")

    def login(self, login):
        return self.client.post(reverse("account_login"), {"login": login, "password": "pass12345"})

    def test_login_with_email(self):
        self.login("amy@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_login_with_taiwan_phone_format(self):
        self.login("0912-000-111")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_username_no_longer_works(self):
        self.login("amy")
        self.assertNotIn("_auth_user_id", self.client.session)


class ChatTests(TestCase):
    def setUp(self):
        math = Subject.objects.create(name="數學", level=Subject.Level.JUNIOR)
        self.tutor = make_tutor("teacher", math)
        self.student = User.objects.create_user(username="student", password="pass12345")
        User.objects.create_user(username="stranger", password="pass12345")
        self.match = MatchRequest.objects.create(
            student=self.student, tutor=self.tutor, subject=math,
            message="hi", preferred_schedule="週六", student_contact="LINE",
            status=MatchRequest.Status.ACCEPTED,
        )
        self.chat_url = reverse("matching:chat", args=[self.match.id])
        self.poll_url = reverse("matching:chat-messages", args=[self.match.id])

    def test_participants_can_chat(self):
        self.client.login(username="student", password="pass12345")
        response = self.client.post(self.chat_url, {"body": "老師好"}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["message"]["mine"])

        self.client.login(username="teacher", password="pass12345")
        self.assertContains(self.client.get(reverse("matching:list") + "?tab=received"), "1 則新訊息")
        data = self.client.get(self.poll_url, {"after": 0}).json()
        self.assertEqual([m["body"] for m in data["messages"]], ["老師好"])
        self.assertFalse(data["messages"][0]["mine"])

        # GET 只讀取：打開聊天室、查詢新訊息都不會把訊息標成已讀
        self.client.get(self.chat_url)
        self.assertFalse(Message.objects.get().is_read)

        # 標記已讀要用 POST
        read_url = reverse("matching:chat-read", args=[self.match.id])
        self.assertEqual(self.client.get(read_url).status_code, 405)
        self.assertEqual(self.client.post(read_url).json(), {"marked": 1})
        self.assertTrue(Message.objects.get().is_read)

    def test_poll_only_returns_newer_messages(self):
        first = Message.objects.create(match_request=self.match, sender=self.student, body="一")
        Message.objects.create(match_request=self.match, sender=self.student, body="二")
        self.client.login(username="teacher", password="pass12345")
        data = self.client.get(self.poll_url, {"after": first.id}).json()
        self.assertEqual([m["body"] for m in data["messages"]], ["二"])

    def test_sender_cannot_mark_own_messages_read(self):
        Message.objects.create(match_request=self.match, sender=self.student, body="一")
        self.client.login(username="student", password="pass12345")
        self.client.post(reverse("matching:chat-read", args=[self.match.id]))
        self.assertFalse(Message.objects.get().is_read)

    def test_outsider_cannot_read_or_post(self):
        Message.objects.create(match_request=self.match, sender=self.student, body="秘密")
        self.client.login(username="stranger", password="pass12345")
        self.assertEqual(self.client.post(reverse("matching:chat-read", args=[self.match.id])).status_code, 404)
        self.assertEqual(self.client.get(self.chat_url).status_code, 404)
        self.assertEqual(self.client.get(self.poll_url).status_code, 404)
        self.assertEqual(self.client.post(self.chat_url, {"body": "嗨"}).status_code, 404)
        self.assertEqual(Message.objects.count(), 1)

    def test_no_chat_before_accepted(self):
        self.match.status = MatchRequest.Status.PENDING
        self.match.save()
        self.client.login(username="student", password="pass12345")
        self.assertEqual(self.client.get(self.chat_url).status_code, 404)

    def test_blank_message_rejected(self):
        self.client.login(username="student", password="pass12345")
        response = self.client.post(self.chat_url, {"body": "   "}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Message.objects.exists())


class ChatImageTests(TempMediaMixin, TestCase):
    def setUp(self):
        super().setUp()
        math = Subject.objects.create(name="數學", level=Subject.Level.JUNIOR)
        self.tutor = make_tutor("teacher", math)
        self.student = User.objects.create_user(username="student", password="pass12345")
        User.objects.create_user(username="stranger", password="pass12345")
        self.match = MatchRequest.objects.create(
            student=self.student, tutor=self.tutor, subject=math,
            message="hi", preferred_schedule="週六", student_contact="LINE",
            status=MatchRequest.Status.ACCEPTED,
        )
        self.chat_url = reverse("matching:chat", args=[self.match.id])

    def send_image(self, body=""):
        self.client.login(username="student", password="pass12345")
        return self.client.post(self.chat_url, {"body": body, "image": make_image("我的作業.jpg")}, HTTP_ACCEPT="application/json")

    def test_send_image_only(self):
        response = self.send_image()
        self.assertEqual(response.status_code, 201)
        message = Message.objects.get()
        self.assertEqual(message.body, "")
        self.assertEqual(response.json()["message"]["image_url"], reverse("matching:chat-image", args=[self.match.id, message.id]))
        # 圖片存在私密資料夾，沒有公開網址
        self.assertTrue(message.image.path.startswith(self._private))
        with self.assertRaises(ValueError):
            message.image.url

    def test_only_the_two_participants_can_see_image(self):
        self.send_image("這題不會")
        image_url = reverse("matching:chat-image", args=[self.match.id, Message.objects.get().id])

        self.assertEqual(self.client.get(image_url).status_code, 200)  # 學生（傳送者）
        self.client.login(username="teacher", password="pass12345")
        response = self.client.get(image_url)
        self.assertEqual(response.status_code, 200)  # 老師
        self.assertEqual(response["Content-Type"], "image/jpeg")

        self.client.login(username="stranger", password="pass12345")
        self.assertEqual(self.client.get(image_url).status_code, 404)  # 其他人
        self.client.logout()
        self.assertEqual(self.client.get(image_url).status_code, 302)  # 沒登入 → 登入頁

    def test_image_url_must_match_chat(self):
        """用自己聊天室的網址，換別人訊息的編號，也拿不到圖片。"""
        self.send_image()
        other_match = MatchRequest.objects.create(
            student=User.objects.get(username="stranger"), tutor=self.tutor, subject=self.match.subject,
            message="hi", preferred_schedule="週日", student_contact="LINE", status=MatchRequest.Status.ACCEPTED,
        )
        self.client.login(username="stranger", password="pass12345")
        url = reverse("matching:chat-image", args=[other_match.id, Message.objects.get().id])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_non_image_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.login(username="student", password="pass12345")
        fake = SimpleUploadedFile("a.jpg", b"not an image", content_type="image/jpeg")
        response = self.client.post(self.chat_url, {"image": fake}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Message.objects.exists())
