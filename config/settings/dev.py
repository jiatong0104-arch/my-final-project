from .base import *

DEBUG = True

ALLOWED_HOSTS = []
 #ALLOWED_HOSTS 用來限制哪些網址可連到 Django，避免 HTTP Host header 攻擊

#開發環境中，DEBUG = True 且 ALLOWED_HOSTS = [] 時，Django 會自動允許 localhost、127.0.0.1 與 [::1]，因此使用 http://127.0.0.1:8000/ 練習時不需要填入任何值。
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}