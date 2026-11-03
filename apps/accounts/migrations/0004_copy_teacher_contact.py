from django.db import migrations


def copy_teacher_contact(apps, schema_editor):
    """把老師檔案裡的聯絡方式複製到帳號的基本資料（一個帳號一個聯絡方式）。

    老師檔案的 contact_info 先保留不刪，邀請流程改完後再移除。
    """
    UserProfile = apps.get_model("accounts", "UserProfile")
    TeacherProfile = apps.get_model("tutors", "TeacherProfile")
    for teacher in TeacherProfile.objects.exclude(contact_info=""):
        profile, _ = UserProfile.objects.get_or_create(user_id=teacher.user_id)
        if not profile.contact_info:
            profile.contact_info = teacher.contact_info
            profile.save(update_fields=["contact_info"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_student_profile_and_contact"),
        ("tutors", "0005_rename_tutorprofile_teacherprofile"),
    ]

    operations = [
        migrations.RunPython(copy_teacher_contact, migrations.RunPython.noop),
    ]
