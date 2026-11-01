import os
import dj_database_url
from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

DATABASES = {
    "default": dj_database_url.parse(
        os.environ["DATABASE_URL"],
        conn_max_age=600,
    )
}

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

#DJANGO_ALLOWED_HOSTS 以逗號分隔多個可接受的網站網域，例如 example.com,www.example.com。
#正式環境的 SECRET_KEY 與 DJANGO_ALLOWED_HOSTS 都不應寫死在 GitHub repository 中；
#後續部署時由部署平台的環境變數設定功能提供。現在的 prod.py 只是先建立清楚的設定位置，不能直接視為完整的上線設定。