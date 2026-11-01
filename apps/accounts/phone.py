import re

from django import forms
from django.core.exceptions import ValidationError

TAIWAN_MOBILE = re.compile(r"^09\d{8}$")
INTERNATIONAL = re.compile(r"^\+[1-9]\d{6,14}$")


def normalize_phone(value):
    """把 0912-345-678、0912 345 678、+886912345678 統一成 +886912345678。"""
    cleaned = re.sub(r"[\s\-()]", "", value or "")
    if TAIWAN_MOBILE.match(cleaned):
        return "+886" + cleaned[1:]
    if cleaned.startswith("+8860"):
        cleaned = "+886" + cleaned[5:]
    if INTERNATIONAL.match(cleaned):
        return cleaned
    raise ValidationError("請輸入正確的手機號碼，例如 0912345678。", code="invalid_phone")


class TaiwanPhoneField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", "手機號碼")
        kwargs.setdefault(
            "widget",
            forms.TextInput(attrs={"placeholder": "0912345678", "autocomplete": "tel", "type": "tel"}),
        )
        kwargs.pop("validators", None)
        super().__init__(*args, **kwargs)

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return value
        return normalize_phone(value)
