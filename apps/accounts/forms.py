from django import forms

from .models import UserProfile


class ProfileSignupForm(forms.Form):
    display_name = forms.CharField(
        max_length=50,
        label="顯示名稱",
        help_text="老師和學生會看到這個名字，例如「王小明」。",
    )

    field_order = ["display_name", "email", "phone", "password1", "password2"]

    def signup(self, request, user):
        UserProfile.objects.update_or_create(
            user=user,
            defaults={"display_name": self.cleaned_data["display_name"]},
        )

