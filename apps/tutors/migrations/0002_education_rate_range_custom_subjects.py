from django.db import migrations, models
import django.core.validators


def copy_rate_and_education(apps, schema_editor):
    """把舊資料搬到新欄位：最高時薪先等於原本的時薪；舊的「學歷」文字放進學校欄位。"""
    TutorProfile = apps.get_model("tutors", "TutorProfile")
    for tutor in TutorProfile.objects.all():
        tutor.hourly_rate_max = tutor.hourly_rate_min
        if not tutor.school:
            tutor.school = tutor.education
        tutor.save(update_fields=["hourly_rate_max", "school"])


def add_elementary_social(apps, schema_editor):
    Subject = apps.get_model("tutors", "Subject")
    Subject.objects.get_or_create(name="社會", level=1)


class Migration(migrations.Migration):

    dependencies = [
        ("tutors", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="subject",
            name="is_custom",
            field=models.BooleanField(default=False, help_text="老師在「其他」欄位自行輸入的科目。", verbose_name="老師自行新增"),
        ),
        migrations.RenameField(
            model_name="tutorprofile",
            old_name="hourly_rate",
            new_name="hourly_rate_min",
        ),
        migrations.AlterField(
            model_name="tutorprofile",
            name="hourly_rate_min",
            field=models.PositiveIntegerField(
                validators=[django.core.validators.MinValueValidator(100), django.core.validators.MaxValueValidator(5000)],
                verbose_name="最低時薪",
            ),
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="hourly_rate_max",
            field=models.PositiveIntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(100), django.core.validators.MaxValueValidator(5000)],
                verbose_name="最高時薪",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="school",
            field=models.CharField(default="", max_length=100, verbose_name="學校"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="department",
            field=models.CharField(default="", max_length=100, verbose_name="系所"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="degree",
            field=models.CharField(
                choices=[
                    ("bachelor_student", "大學在學"),
                    ("bachelor", "學士"),
                    ("master_student", "碩士在學"),
                    ("master", "碩士"),
                    ("doctor", "博士"),
                ],
                default="bachelor",
                max_length=20,
                verbose_name="學位",
            ),
        ),
        migrations.RunPython(copy_rate_and_education, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="tutorprofile",
            name="education",
        ),
        migrations.AlterField(
            model_name="tutorprofile",
            name="bio",
            field=models.TextField(max_length=5000, verbose_name="自我介紹與教學方式"),
        ),
        migrations.AddConstraint(
            model_name="tutorprofile",
            constraint=models.CheckConstraint(
                condition=models.Q(("hourly_rate_min__lte", models.F("hourly_rate_max"))),
                name="rate_min_not_above_max",
                violation_error_message="最高時薪不能低於最低時薪。",
            ),
        ),
        migrations.RunPython(add_elementary_social, migrations.RunPython.noop),
    ]
