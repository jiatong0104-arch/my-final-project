# 獨立成一個檔案：ACCOUNT_SIGNUP_FORM_CLASS 所在的模組不能匯入 allauth 的表單，否則會循環匯入。
from allauth.account.forms import LoginForm, SignupForm


class EmailOrPhoneLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].label = "信箱或手機號碼"
        self.fields["login"].widget.attrs["placeholder"] = "you@example.com 或 0912345678"
        self.fields["password"].label = "密碼"
        self.fields["password"].help_text = ""  # 本專案沒有寄信功能，先不顯示「忘記密碼」連結

    def user_credentials(self):
        # 只接受信箱或手機號碼；輸入使用者名稱一律不登入
        credentials = super().user_credentials()
        credentials.pop("username", None)
        return credentials


class ZhSignupForm(SignupForm):
    """allauth 註冊表單，把欄位名稱改成中文。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        labels = {
            "email": ("電子信箱", "you@example.com", "登入時使用。"),
            "phone": ("手機號碼", "0912345678", "填寫後，也可以用手機號碼登入。"),
            "password1": ("密碼", "至少 8 個字元", None),
            "password2": ("確認密碼", "再輸入一次密碼", None),
        }
        for name, (label, placeholder, help_text) in labels.items():
            if name in self.fields:
                self.fields[name].label = label
                self.fields[name].widget.attrs["placeholder"] = placeholder
                if help_text:
                    self.fields[name].help_text = help_text
