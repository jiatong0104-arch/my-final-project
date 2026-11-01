from django import template

register = template.Library()

AVATAR_COLORS = [
    "bg-emerald-100 text-emerald-800",
    "bg-amber-100 text-amber-800",
    "bg-sky-100 text-sky-800",
    "bg-rose-100 text-rose-800",
    "bg-violet-100 text-violet-800",
    "bg-teal-100 text-teal-800",
]


@register.filter
def avatar_color(value):
    """依 id 給頭像固定的顏色。"""
    try:
        return AVATAR_COLORS[int(value) % len(AVATAR_COLORS)]
    except (TypeError, ValueError):
        return AVATAR_COLORS[0]


@register.filter
def stars(value):
    """把平均分數轉成 ★★★★☆ 字串。"""
    if value is None:
        return ""
    full = int(round(float(value)))
    return "★" * full + "☆" * (5 - full)


@register.filter
def user_display(user):
    profile = getattr(user, "profile", None)
    if profile and profile.display_name:
        return profile.display_name
    return user.get_username()
