"""上傳檔案的共用工具：存放位置、檔名、檢查格式與大小。

兩種存放位置：
- 公開（default_storage → media/）：老師動態的照片、影片，任何人都能看。
- 私密（private_storage → private_media/）：身分證件、聊天室圖片。
  url() 會直接報錯，所以不會產生公開網址，只能透過檢查權限的 View 讀取。
"""

import io
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible
from django.utils.functional import LazyObject

from PIL import Image, ImageOps, UnidentifiedImageError


class PrivateFileSystemStorage(FileSystemStorage):
    """存在 PRIVATE_MEDIA_ROOT，而且故意不提供網址：要看檔案只能經過檢查權限的 View。"""

    def url(self, name):
        raise ValueError("私密檔案沒有公開網址，請透過檢查權限的 View 讀取。")


class _PrivateStorage(LazyObject):
    def _setup(self):
        self._wrapped = PrivateFileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


private_storage = _PrivateStorage()


def get_private_storage():
    """給 FileField(storage=...) 用；寫成函式，migration 才不會把路徑寫死。"""
    return private_storage


@deconstructible
class RandomName:
    """把上傳的檔名換成隨機字串：避免檔名洩漏個資（例如「王小明_學生證.jpg」），也不會撞名。"""

    def __init__(self, folder):
        self.folder = folder

    def __call__(self, instance, filename):
        ext = Path(filename).suffix.lower()[:10]
        return f"{self.folder}/{uuid.uuid4().hex}{ext}"

    def __eq__(self, other):
        return isinstance(other, RandomName) and other.folder == self.folder


def limit_mb(kind):
    return settings.UPLOAD_LIMITS_MB[kind]


def check_size(file, kind):
    limit = limit_mb(kind)
    if file.size > limit * 1024 * 1024:
        raise ValidationError(f"檔案太大了，上限是 {limit} MB。")


IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}


def clean_image(file, max_side=2000):
    """確認是真的圖片，並重新存一份：
    - 縮小到最長邊 max_side 像素，節省空間；
    - 依照 EXIF 轉正手機拍的照片；
    - 重新存檔時不保留 EXIF，順便清掉照片裡的 GPS 位置等個資。
    回傳新的 ContentFile。
    """
    check_size(file, "image")
    try:
        image = Image.open(file)
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValidationError("無法讀取這張圖片，請上傳 JPG、PNG 或 WEBP。")
    if image.format not in IMAGE_FORMATS:
        raise ValidationError("只能上傳 JPG、PNG、WEBP 或 GIF 圖片。")

    image = ImageOps.exif_transpose(image)
    image.thumbnail((max_side, max_side))
    output = io.BytesIO()
    if image.format == "PNG" or image.mode in ("RGBA", "LA", "P"):
        image.save(output, format="PNG", optimize=True)
        ext = ".png"
    else:
        image.convert("RGB").save(output, format="JPEG", quality=85, optimize=True)
        ext = ".jpg"
    return ContentFile(output.getvalue(), name=f"image{ext}")


def clean_document(file):
    """身分證件：可以是照片（JPG、PNG）或 PDF。"""
    check_size(file, "document")
    head = file.read(5)
    file.seek(0)
    if head == b"%PDF-":
        return file
    try:
        return clean_image(file)
    except ValidationError:
        raise ValidationError("請上傳證件的照片（JPG、PNG）或 PDF 檔。")


VIDEO_TYPES = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm", ".m4v": "video/mp4"}


def clean_video(file):
    """影片：只檢查副檔名、檔頭與大小。轉檔交給正式上線時的影片服務。"""
    check_size(file, "video")
    ext = Path(file.name).suffix.lower()
    if ext not in VIDEO_TYPES:
        raise ValidationError("只能上傳 MP4、MOV 或 WEBM 影片。")
    head = file.read(12)
    file.seek(0)
    # MP4／MOV 的第 4–8 個位元組是 "ftyp"；WEBM 開頭是 1A 45 DF A3
    if head[4:8] != b"ftyp" and not head.startswith(b"\x1a\x45\xdf\xa3"):
        raise ValidationError("這個檔案看起來不是影片，請重新選擇。")
    return file
