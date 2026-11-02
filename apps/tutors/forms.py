import re

from django import forms

from apps.core.uploads import clean_document, clean_image, clean_video, limit_mb

from . import choices
from .models import Subject, TutorPost, TutorProfile


def grouped_choices(groups, placeholder):
    """把分組的清單轉成 <optgroup> 用的 choices，最後加上「其他」。"""
    return (
        [("", placeholder)]
        + [(group, [(item, item) for item in items]) for group, items in groups]
        + [(choices.OTHER, "其他（自行輸入）")]
    )


def split_subject_names(text):
    """「作文、閱讀理解, 自然」→ ["作文", "閱讀理解", "自然"]"""
    names = re.split(r"[、,，;；\n]+", text or "")
    return [name.strip()[:50] for name in names if name.strip()]


class TutorProfileForm(forms.ModelForm):
    # 學校、系所是否必填，要看最高學歷（高中職只填學校），所以在 clean() 裡檢查
    school_choice = forms.ChoiceField(
        label="學校", required=False, choices=grouped_choices(choices.SCHOOLS, "請選擇學校"),
    )
    school_other = forms.CharField(
        label="學校名稱", required=False, max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "請輸入學校名稱"}),
    )
    department_choice = forms.ChoiceField(
        label="系所", required=False, choices=grouped_choices(choices.DEPARTMENTS, "請選擇系所"),
    )
    department_other = forms.CharField(
        label="系所名稱", required=False, max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "請輸入系所名稱"}),
    )
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="可教科目",
    )

    class Meta:
        model = TutorProfile
        fields = (
            "headline",
            "education_level",
            "education_status",
            "bio",
            "subjects",
            "hourly_rate_min",
            "hourly_rate_max",
            "years_of_experience",
            "city",
            "teaching_mode",
            "contact_info",
            "is_accepting",
        )
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 8, "maxlength": 5000}),
            "education_level": forms.RadioSelect,
            "education_status": forms.RadioSelect,
            "hourly_rate_min": forms.NumberInput(attrs={"step": 50, "placeholder": "例如 600"}),
            "hourly_rate_max": forms.NumberInput(attrs={"step": 50, "placeholder": "例如 1000"}),
        }
        labels = {"hourly_rate_min": "最低", "hourly_rate_max": "最高"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 科目清單：官方科目 + 這位老師自己新增過的科目
        own = self.instance.subjects.all() if self.instance.pk else Subject.objects.none()
        self.fields["subjects"].queryset = (
            Subject.objects.filter(is_custom=False) | Subject.objects.filter(id__in=own.values("id"))
        ).distinct()

        # 每個年級一個「其他」輸入框
        for value, label in Subject.Level.choices:
            self.fields[f"other_subjects_{value}"] = forms.CharField(
                required=False,
                max_length=200,
                label=f"{label}其他科目",
                widget=forms.TextInput(attrs={"placeholder": "例如：作文、閱讀理解（多個用頓號分隔）"}),
            )

        # 編輯時，把已存的學校／系所放回下拉選單；不在清單裡的就放進「其他」
        if self.instance.pk:
            for name, options in (("school", choices.SCHOOLS), ("department", choices.DEPARTMENTS)):
                saved = getattr(self.instance, name)
                if saved in choices.flat(options):
                    self.initial[f"{name}_choice"] = saved
                elif saved:
                    self.initial[f"{name}_choice"] = choices.OTHER
                    self.initial[f"{name}_other"] = saved

    # ── 讓模板可以依年級分組顯示科目 ──
    def subjects_by_level(self):
        selected = {str(value) for value in (self["subjects"].value() or [])}
        groups = {value: {"label": label, "items": [], "other": self[f"other_subjects_{value}"]}
                  for value, label in Subject.Level.choices}
        for subject in self.fields["subjects"].queryset:
            groups[subject.level]["items"].append({"subject": subject, "checked": str(subject.pk) in selected})
        return groups.values()

    def _resolve(self, name, label):
        choice = self.cleaned_data.get(f"{name}_choice")
        if choice == choices.OTHER:
            text = (self.cleaned_data.get(f"{name}_other") or "").strip()
            if not text:
                self.add_error(f"{name}_other", "選擇「其他」時，請輸入名稱。")
            return text
        if not choice:
            self.add_error(f"{name}_choice", f"請選擇{label}。")
        return choice or ""

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("education_level") == TutorProfile.EducationLevel.HIGH_SCHOOL:
            # 高中職：清單裡都是大學，所以直接輸入校名，不用填系所
            self.school_value = (cleaned.get("school_other") or "").strip()
            if not self.school_value:
                self.add_error("school_other", "請輸入學校名稱。")
            self.department_value = ""
        else:
            self.school_value = self._resolve("school", "學校")
            self.department_value = self._resolve("department", "系所")

        low, high = cleaned.get("hourly_rate_min"), cleaned.get("hourly_rate_max")
        if low is not None and high is not None and low > high:
            self.add_error("hourly_rate_max", "最高時薪不能低於最低時薪。")

        self.custom_subjects = [
            (level, name)
            for level, _ in Subject.Level.choices
            for name in split_subject_names(cleaned.get(f"other_subjects_{level}"))
        ]
        if not cleaned.get("subjects") and not self.custom_subjects:
            self.add_error("subjects", "請至少選擇或輸入一個可教科目。")
        return cleaned

    def save(self, commit=True):
        tutor = super().save(commit=False)
        tutor.school = self.school_value
        tutor.department = self.department_value
        if commit:
            tutor.save()
            self.save_m2m()
        return tutor

    def _save_m2m(self):
        super()._save_m2m()
        for level, name in self.custom_subjects:
            subject = Subject.objects.filter(name__iexact=name, level=level).first()
            if subject is None:
                subject = Subject.objects.create(name=name, level=level, is_custom=True)
            self.instance.subjects.add(subject)


class VerificationForm(forms.Form):
    document = forms.FileField(
        label="證件照片或 PDF",
        widget=forms.ClearableFileInput(attrs={"accept": "image/*,application/pdf"}),
    )

    def clean_document(self):
        return clean_document(self.cleaned_data["document"])


class TutorPostForm(forms.ModelForm):
    """老師發動態：文字，加上一張照片或一部影片（都可以不加，但不能全部空白）。"""

    class Meta:
        model = TutorPost
        fields = ("body", "image", "video")
        widgets = {
            "body": forms.Textarea(attrs={"rows": 3, "maxlength": 3000, "placeholder": "分享教學心得、上課花絮，或錄一段試教影片…"}),
            "image": forms.FileInput(attrs={"accept": "image/*"}),
            "video": forms.FileInput(attrs={"accept": "video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm"}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        return clean_image(image) if image else image

    def clean_video(self):
        video = self.cleaned_data.get("video")
        return clean_video(video) if video else video

    def clean(self):
        cleaned = super().clean()
        cleaned["body"] = (cleaned.get("body") or "").strip()
        if cleaned.get("image") and cleaned.get("video"):
            raise forms.ValidationError("一則動態只能放一張照片或一部影片，請擇一。")
        if not (cleaned["body"] or cleaned.get("image") or cleaned.get("video")) and not self.errors:
            raise forms.ValidationError("寫點文字，或加一張照片、一部影片再發布。")
        return cleaned

    @staticmethod
    def limits():
        return {"image": limit_mb("image"), "video": limit_mb("video")}
