from django.conf import settings
from django.contrib.staticfiles import finders
from django.template.loader import get_template
from django.test import TestCase


class ProjectStructureTests(TestCase):
    """確認模板與靜態檔放在課堂教的位置。"""

    def test_root_templates_only_override_allauth(self):
        # 專案根目錄的 templates/ 只放 allauth 的覆寫；各 app 的頁面放在 apps/<app>/templates/<app>/
        root = settings.BASE_DIR / "templates"
        leftovers = sorted(p.name for p in root.iterdir() if p.name != "account")
        self.assertEqual(
            leftovers, [],
            f"templates/ 裡還有舊檔案：{leftovers}，請刪除（它們會蓋過 app 裡的新模板）",
        )

    def test_templates_load_from_app_folders(self):
        for name in ("core/base.html", "core/home.html", "tutors/tutor_list.html", "matching/chat.html"):
            origin = get_template(name).origin.name
            self.assertIn("apps", origin, name)

    def test_static_files_found(self):
        for path in (
            "core/css/site.css",
            "core/js/site.js",
            "core/js/tailwind-config.js",
            "tutors/js/tutor_form.js",
            "matching/js/chat.js",
        ):
            self.assertIsNotNone(finders.find(path), path)

    def test_home_page_uses_static_files(self):
        response = self.client.get("/")
        self.assertContains(response, "/static/core/css/site.css")
        self.assertContains(response, "/static/core/js/site.js")
