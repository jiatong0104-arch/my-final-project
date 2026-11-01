import logging

from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import UserProfile
from .phone import TaiwanPhoneField, normalize_phone

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    """讓 allauth 知道手機號碼存在哪裡（UserProfile.phone），並接受台灣手機格式。"""

    def phone_form_field(self, **kwargs):
        return TaiwanPhoneField(**kwargs)

    def get_phone(self, user):
        profile = UserProfile.objects.filter(user=user).first()
        if profile and profile.phone:
            return profile.phone, True
        return None

    def set_phone(self, user, phone, verified):
        UserProfile.objects.update_or_create(user=user, defaults={"phone": phone})

    def set_phone_verified(self, user, phone):
        # 本專案不寄送簡訊驗證碼（ACCOUNT_PHONE_VERIFICATION_ENABLED = False）
        pass

    def get_user_by_phone(self, phone):
        try:
            phone = normalize_phone(phone)
        except ValidationError:
            return None
        return get_user_model().objects.filter(profile__phone=phone).first()

    def send_verification_code_sms(self, user, phone, code, **kwargs):
        # 沒有串接簡訊服務；開發時把驗證碼印在終端機
        logger.warning("簡訊驗證碼（開發用）：%s → %s", phone, code)
