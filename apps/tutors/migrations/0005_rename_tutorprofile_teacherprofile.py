from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    """TutorProfile 改名為 TeacherProfile。

    手寫 RenameModel：資料表直接改名、資料全部保留，指向它的關聯（邀請、認證、動態）也會跟著更新。
    """

    dependencies = [
        ("tutors", "0004_verification_and_posts"),
        # 邀請表（matching）連到老師檔案，要讓它先建好再改名，全新資料庫（例如跑測試）才不會出錯
        ("matching", "0003_message_image"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(old_name="TutorProfile", new_name="TeacherProfile"),
    ]
