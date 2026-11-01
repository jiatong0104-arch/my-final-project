from django import forms

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
    body = forms.CharField(
        max_length=2000,
        label="訊息",
        widget=forms.Textarea(attrs={"rows": 1, "placeholder": "輸入訊息…（Enter 送出，Shift + Enter 換行）"}),
    )

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("訊息不能是空白。")
        return body
