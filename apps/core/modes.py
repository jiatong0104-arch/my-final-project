"""學生／老師模式：存在 session 裡，決定左上角顯示「學」或「師」，以及導覽列的內容。

模式只影響「畫面怎麼排」，不影響權限：老師模式也能找老師，學生模式也能進自己的老師檔案。
"""

STUDENT = "student"
TEACHER = "teacher"
SESSION_KEY = "ui_mode"


def get_mode(request):
    mode = request.session.get(SESSION_KEY)
    if mode in (STUDENT, TEACHER):
        return mode
    # 還沒選過：有老師檔案的人預設老師模式，其他人預設學生模式
    user = request.user
    if user.is_authenticated and hasattr(user, "tutor_profile"):
        return TEACHER
    return STUDENT


def set_mode(request, mode):
    if mode in (STUDENT, TEACHER):
        request.session[SESSION_KEY] = mode


def ui_mode(request):
    """context processor：每個模板都能用 {{ ui_mode }}、{{ is_teacher_mode }}"""
    mode = get_mode(request)
    return {"ui_mode": mode, "is_teacher_mode": mode == TEACHER}
