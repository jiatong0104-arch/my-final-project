"""私密檔案的回應：權限檢查由各個 View 自己做，這裡只負責把檔案送出去。"""

import mimetypes
from pathlib import Path

from django.http import FileResponse


def private_file_response(field_file):
    content_type = mimetypes.guess_type(field_file.name)[0] or "application/octet-stream"
    response = FileResponse(field_file.open("rb"), content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{Path(field_file.name).name}"'
    # 不讓瀏覽器或中間的伺服器快取私密檔案，也不讓瀏覽器猜測檔案類型
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
