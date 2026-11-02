"""把舊的「學位」欄位（degree）拆成「最高學歷」和「在學／畢業」兩個欄位。

舊資料會自動轉換，例如 master_student（碩士在學）→ 碩士 + 在學。
"""
from django.db import migrations, models

DEGREE_TO_EDUCATION = {
    "bachelor_student": ("bachelor", "studying"),
    "bachelor": ("bachelor", "graduated"),
    "master_student": ("master", "studying"),
    "master": ("master", "graduated"),
    "doctor": ("doctor", "graduated"),
}


def degree_to_education(apps, schema_editor):
    TutorProfile = apps.get_model("tutors", "TutorProfile")
    for tutor in TutorProfile.objects.all():
        level, status = DEGREE_TO_EDUCATION.get(tutor.degree, ("bachelor", "graduated"))
        tutor.education_level = level
        tutor.education_status = status
        tutor.save(update_fields=["education_level", "education_status"])


def education_to_degree(apps, schema_editor):
    TutorProfile = apps.get_model("tutors", "TutorProfile")
    reverse = {value: key for key, value in DEGREE_TO_EDUCATION.items()}
    for tutor in TutorProfile.objects.all():
        tutor.degree = reverse.get((tutor.education_level, tutor.education_status), "bachelor")
        tutor.save(update_fields=["degree"])


class Migration(migrations.Migration):

    dependencies = [
        ("tutors", "0002_education_rate_range_custom_subjects"),
    ]

    operations = [
        migrations.AddField(
            model_name="tutorprofile",
            name="education_level",
            field=models.CharField(
                choices=[("high_school", "高中職"), ("associate", "專科"), ("bachelor", "大學"), ("master", "碩士"), ("doctor", "博士")],
                default="bachelor", max_length=20, verbose_name="最高學歷",
            ),
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="education_status",
            field=models.CharField(
                choices=[("studying", "在學"), ("graduated", "畢業")],
                default="graduated", max_length=20, verbose_name="在學／畢業",
            ),
        ),
        migrations.RunPython(degree_to_education, education_to_degree),
        migrations.RemoveField(model_name="tutorprofile", name="degree"),
        migrations.AlterField(
            model_name="tutorprofile",
            name="department",
            field=models.CharField(blank=True, max_length=100, verbose_name="系所"),
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="is_verified",
            field=models.BooleanField(
                default=False, verbose_name="已認證",
                help_text="管理員審核學生證或畢業證書後打勾。修改學歷時會自動取消，需要重新審核。",
            ),
        ),
    ]
