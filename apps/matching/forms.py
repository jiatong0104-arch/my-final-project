from django import forms

from apps.core.uploads import clean_image

from .models import MatchRequest, Review


class MatchRequestForm(forms.ModelForm):
    class Meta:
        model = MatchRequest
        fields = ("subject", "preferred_schedule", "message", "student_contact")
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, tutor, **kwargs):
        super().__init__(*args, **kwargs)
        # 只能選這位老師有教的科目
        self.fields["subject"].queryset = tutor.subjects.all()
        self.fields["subject"].empty_label = "請選擇科目"


class TutorReplyForm(forms.Form):
    tutor_reply = forms.CharField(
        required=False,
        max_length=500,
        label="給學生的回覆（選填）",
        widget=forms.Textarea(attrs={"rows": 2}),
    )


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(i, f"{i} 星") for i in range(5, 0, -1)],
        coerce=int,
        widget=forms.RadioSelect,
        label="評分",
    )

    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 4}),
        }


class MessageForm(forms.Form):
    """一則訊息可以是文字、圖片，或兩者都有。"""

    body = forms.CharField(
        required=False,
        max_length=2000,
        label="訊息",
        widget=forms.Textarea(attrs={"rows": 1, "placeholder": "輸入訊息…（Enter 送出，Shift + Enter 換行）"}),
    )

    image = forms.ImageField(required=False, label="圖片")

    def clean_body(self):
        return self.cleaned_data["body"].strip()

    def clean_image(self):
        image = self.cleaned_data.get("image")
        return clean_image(image, max_side=1600) if image else None

    def clean(self):
        cleaned = super().clean()
        if not self.errors and not cleaned.get("body") and not cleaned.get("image"):
            raise forms.ValidationError("訊息不能是空白。")
        return cleaned

    def first_error(self):
        for errors in self.errors.values():
            return errors[0]
        return "訊息沒有送出，請再試一次。"
