from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from PIL import Image

from apps.accounts.models import UserProfile
from apps.core.testing import TempMediaMixin, make_image, make_video
from apps.core.uploads import clean_image

from .models import Subject, TutorPost, TutorProfile, VerificationRequest

User = get_user_model()
PASSWORD = "pass12345"


def make_tutor(username, **extra):
    user = User.objects.create_user(username=username, password=PASSWORD)
    UserProfile.objects.create(user=user, display_name=f"{username} 老師")
    data = {
        "headline": "好老師", "bio": "介紹", "school": "國立臺灣大學", "department": "數學系",
        "hourly_rate_min": 800, "hourly_rate_max": 800, "city": "taipei", "contact_info": "LINE",
    }
    data.update(extra)
    tutor = TutorProfile.objects.create(user=user, **data)
    tutor.subjects.add(Subject.objects.get_or_create(name="數學", level=Subject.Level.JUNIOR)[0])
    return tutor


class EducationTests(TestCase):
    def setUp(self):
        self.math = Subject.objects.create(name="數學", level=Subject.Level.SENIOR)
        User.objects.create_user(username="newbie", password=PASSWORD)
        self.client.login(username="newbie", password=PASSWORD)
        self.data = {
            "headline": "學長", "subjects": [self.math.id], "bio": "介紹",
            "education_level": "bachelor", "education_status": "studying",
            "school": "國立清華大學", "department_choice": "物理學系",
            "years_of_experience": 1, "hourly_rate_min": 500, "hourly_rate_max": 600,
            "city": "taipei", "teaching_mode": "online", "contact_info": "LINE", "is_accepting": "on",
        }

    def test_education_label(self):
        self.client.post(reverse("tutors:profile-create"), self.data)
        self.assertEqual(TutorProfile.objects.get().education, "國立清華大學 物理學系（大學在學）")

    def test_high_school_only_needs_school_name(self):
        data = {**self.data, "education_level": "high_school", "department_choice": "",
                "school": "臺北市立建國高級中學"}
        response = self.client.post(reverse("tutors:profile-create"), data)
        self.assertEqual(response.status_code, 302)
        tutor = TutorProfile.objects.get()
        self.assertEqual(tutor.department, "")
        self.assertEqual(tutor.education, "臺北市立建國高級中學（高中職在學）")

    def test_high_school_requires_school_name(self):
        data = {**self.data, "education_level": "high_school", "school": ""}
        response = self.client.post(reverse("tutors:profile-create"), data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("school", response.context["form"].errors)

    def test_university_requires_department(self):
        response = self.client.post(reverse("tutors:profile-create"), {**self.data, "department_choice": ""})
        self.assertEqual(response.status_code, 400)
        self.assertIn("department_choice", response.context["form"].errors)

    def test_changing_education_removes_verified_badge(self):
        self.client.post(reverse("tutors:profile-create"), self.data)
        TutorProfile.objects.update(is_verified=True)

        # 只改時薪：標章還在
        self.client.post(reverse("tutors:profile-edit"), {**self.data, "hourly_rate_max": 700})
        self.assertTrue(TutorProfile.objects.get().is_verified)

        # 改成畢業：標章拿掉
        self.client.post(reverse("tutors:profile-edit"), {**self.data, "education_status": "graduated"})
        self.assertFalse(TutorProfile.objects.get().is_verified)


class VerificationTests(TempMediaMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tutor = make_tutor("teacher")
        self.client.login(username="teacher", password=PASSWORD)
        self.url = reverse("tutors:verify")

    def submit(self, file=None):
        return self.client.post(self.url, {"document": file or make_image("學生證.jpg")})

    def make_admin(self, staff=True, permission=True):
        admin = User.objects.create_user(username="admin", password=PASSWORD, is_staff=staff)
        if permission:
            admin.user_permissions.add(Permission.objects.get(codename="view_verificationrequest"))
        return admin

    def test_submit_creates_pending_request_with_private_random_name(self):
        self.assertRedirects(self.submit(), self.url)
        verification = VerificationRequest.objects.get()
        self.assertEqual(verification.status, "pending")
        self.assertEqual(verification.education_snapshot, self.tutor.education)
        # 檔名換成隨機字串，不會留下「學生證」之類的原始檔名
        self.assertNotIn("學生證", verification.document.name)
        self.assertTrue(verification.document.path.startswith(self._private))
        # 私密檔案沒有公開網址
        with self.assertRaises(ValueError):
            verification.document.url

    def test_pdf_allowed_other_files_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        pdf = SimpleUploadedFile("diploma.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        self.assertEqual(self.submit(pdf).status_code, 302)
        VerificationRequest.objects.all().delete()

        exe = SimpleUploadedFile("virus.jpg", b"MZ not an image", content_type="image/jpeg")
        self.assertEqual(self.submit(exe).status_code, 400)
        self.assertFalse(VerificationRequest.objects.exists())

    def test_only_one_pending_request(self):
        self.submit()
        self.submit()
        self.assertEqual(VerificationRequest.objects.count(), 1)

    def test_document_only_visible_to_admin(self):
        self.submit()
        url = reverse("tutors:verification-document", args=[VerificationRequest.objects.get().id])

        # 老師本人也看不到（證件只給審核的人看）
        self.assertEqual(self.client.get(url).status_code, 404)
        # 只是 staff、沒有權限：也看不到
        self.make_admin(permission=False)
        self.client.login(username="admin", password=PASSWORD)
        self.assertEqual(self.client.get(url).status_code, 404)

        admin = User.objects.get(username="admin")
        admin.user_permissions.add(Permission.objects.get(codename="view_verificationrequest"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_approve_gives_badge_and_deletes_document(self):
        self.submit()
        verification = VerificationRequest.objects.get()
        path = verification.document.path
        verification.finish(VerificationRequest.Status.APPROVED, self.make_admin())

        self.tutor.refresh_from_db()
        verification.refresh_from_db()
        self.assertTrue(self.tutor.is_verified)
        self.assertFalse(verification.document)
        import os
        self.assertFalse(os.path.exists(path))

    def test_admin_reject_requires_note(self):
        self.submit()
        admin = self.make_admin()
        admin.is_superuser = True
        admin.save()
        self.client.login(username="admin", password=PASSWORD)
        changelist = reverse("admin:tutors_verificationrequest_changelist")
        ids = [VerificationRequest.objects.get().id]

        self.client.post(changelist, {"action": "reject", "_selected_action": ids})
        self.assertEqual(VerificationRequest.objects.get().status, "pending")

        VerificationRequest.objects.update(admin_note="照片模糊")
        self.client.post(changelist, {"action": "reject", "_selected_action": ids})
        self.assertEqual(VerificationRequest.objects.get().status, "rejected")
        self.tutor.refresh_from_db()
        self.assertFalse(self.tutor.is_verified)

    def test_list_badge_and_filter(self):
        make_tutor("verified", is_verified=True)
        response = self.client.get(reverse("tutors:list"), {"verified": "1"})
        self.assertEqual([t.user.username for t in response.context["page"].object_list], ["verified"])
        # 未認證的老師仍然會出現在一般列表
        response = self.client.get(reverse("tutors:list"))
        self.assertEqual(response.context["page"].paginator.count, 2)
        self.assertContains(response, "學歷已認證", count=1)  # 只有一位老師有標章
        self.assertContains(response, "只看「已認證學歷」的老師")

    def test_experience_filter(self):
        make_tutor("new", years_of_experience=0)
        make_tutor("mid", years_of_experience=4)
        make_tutor("senior", years_of_experience=12)
        names = lambda exp: {t.user.username for t in self.client.get(reverse("tutors:list"), {"exp": exp}).context["page"].object_list}
        self.assertEqual(names("0"), {"new", "teacher"})  # teacher 的年資預設 0
        self.assertEqual(names("3-5"), {"mid"})
        self.assertEqual(names("11-"), {"senior"})
        self.assertEqual(len(names("亂打")), 4)  # 不認得的值就不篩選


class TutorPostTests(TempMediaMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tutor = make_tutor("teacher")
        self.url = reverse("tutors:post-create")
        self.client.login(username="teacher", password=PASSWORD)

    def test_text_post(self):
        response = self.client.post(self.url, {"body": "今天教了二次函數"})
        post = TutorPost.objects.get()
        self.assertRedirects(response, reverse("tutors:detail", args=[self.tutor.id]) + f"#post-{post.id}", fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse("tutors:detail", args=[self.tutor.id])), "今天教了二次函數")

    def test_photo_post_is_public(self):
        self.client.post(self.url, {"body": "", "image": make_image()})
        post = TutorPost.objects.get()
        self.assertTrue(post.image.url.startswith("/media/posts/images/"))

    def test_video_post(self):
        self.client.post(self.url, {"video": make_video()})
        self.assertTrue(TutorPost.objects.get().video.name.endswith(".mp4"))

    def test_fake_video_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake = SimpleUploadedFile("lesson.mp4", b"hello world, not a video", content_type="video/mp4")
        response = self.client.post(self.url, {"body": "影片", "video": fake})
        self.assertEqual(response.status_code, 400)
        # 打的文字還留在表單裡
        self.assertContains(response, "影片", status_code=400)
        self.assertFalse(TutorPost.objects.exists())

    def test_empty_post_and_both_files_rejected(self):
        self.assertEqual(self.client.post(self.url, {"body": "  "}).status_code, 400)
        response = self.client.post(self.url, {"image": make_image(), "video": make_video()})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(TutorPost.objects.exists())

    def test_only_owner_can_delete_and_file_is_removed(self):
        import os

        self.client.post(self.url, {"image": make_image()})
        post = TutorPost.objects.get()
        path = post.image.path
        delete_url = reverse("tutors:post-delete", args=[post.id])

        make_tutor("other")
        self.client.login(username="other", password=PASSWORD)
        self.assertEqual(self.client.post(delete_url).status_code, 404)

        self.client.login(username="teacher", password=PASSWORD)
        self.client.post(delete_url)
        self.assertFalse(TutorPost.objects.exists())
        self.assertFalse(os.path.exists(path))

    def test_student_without_profile_cannot_post(self):
        User.objects.create_user(username="student", password=PASSWORD)
        self.client.login(username="student", password=PASSWORD)
        self.client.post(self.url, {"body": "hi"})
        self.assertFalse(TutorPost.objects.exists())


class ImageCleaningTests(TestCase):
    def test_strips_exif_and_shrinks(self):
        cleaned = clean_image(make_image(size=(4000, 1000), with_exif=True), max_side=2000)
        image = Image.open(cleaned)
        self.assertEqual(image.size, (2000, 500))
        self.assertEqual(len(image.getexif()), 0)


class ModeTests(TestCase):
    def test_switch_mode_changes_logo(self):
        list_url = reverse("tutors:list")
        self.assertContains(self.client.get(list_url), "學生模式")

        response = self.client.post(reverse("core:switch-mode"), {"mode": "teacher", "next": "/#teacher"})
        self.assertRedirects(response, "/#teacher", fetch_redirect_response=False)
        self.assertContains(self.client.get(list_url), "老師模式")

    def test_home_shows_split_logo(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "logo-split")
        self.assertNotContains(response, "學生模式")

    def test_switch_mode_requires_post(self):
        self.assertEqual(self.client.get(reverse("core:switch-mode")).status_code, 405)

    def test_no_redirect_to_other_sites(self):
        response = self.client.post(reverse("core:switch-mode"), {"mode": "student", "next": "https://evil.example/"})
        self.assertRedirects(response, reverse("tutors:list"))

    def test_tutor_defaults_to_teacher_mode(self):
        make_tutor("teacher")
        self.client.login(username="teacher", password=PASSWORD)
        self.assertContains(self.client.get(reverse("tutors:list")), "老師模式")
