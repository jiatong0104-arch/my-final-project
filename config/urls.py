from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("apps.core.urls")),
    path("tutors/", include("apps.tutors.urls")),
    path("matches/", include("apps.matching.urls")),
]

# 開發時由 Django 提供公開上傳檔案（media/）；正式上線改由雲端儲存或網頁伺服器提供。
# 私密檔案（private_media/）不在這裡，只能透過檢查權限的 View 讀取。
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
