"""測試用的小工具：產生圖片、把上傳檔案放到暫存資料夾。"""

import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from PIL import Image


def make_image(name="photo.jpg", size=(64, 48), fmt="JPEG", with_exif=False):
    buffer = io.BytesIO()
    image = Image.new("RGB", size, "red")
    kwargs = {}
    if with_exif:
        exif = Image.Exif()
        exif[0x010F] = "PhoneMaker"  # Make
        kwargs["exif"] = exif
    image.save(buffer, format=fmt, **kwargs)
    content_type = {"JPEG": "image/jpeg", "PNG": "image/png"}[fmt]
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


def make_video(name="lesson.mp4"):
    # MP4 檔頭：前 4 個位元組是長度，接著是 "ftyp"
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 100, content_type="video/mp4")


class TempMediaMixin:
    """每個測試都用新的暫存資料夾存上傳檔案，測完刪掉，不會弄髒專案的 media/。"""

    def setUp(self):
        super().setUp()
        self._media = tempfile.mkdtemp()
        self._private = tempfile.mkdtemp()
        self._override = override_settings(MEDIA_ROOT=self._media, PRIVATE_MEDIA_ROOT=self._private)
        self._override.enable()
        # private_storage 第一次使用時才建立；清掉它，才會套用新的暫存資料夾
        from django.utils.functional import empty
        from apps.core.uploads import private_storage
        private_storage._wrapped = empty

    def tearDown(self):
        self._override.disable()
        from django.utils.functional import empty
        from apps.core.uploads import private_storage
        private_storage._wrapped = empty
        shutil.rmtree(self._media, ignore_errors=True)
        shutil.rmtree(self._private, ignore_errors=True)
        super().tearDown()
