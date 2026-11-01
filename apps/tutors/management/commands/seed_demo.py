"""建立展示用的假資料：uv run manage.py seed_demo

會建立科目、9 位老師、3 位學生，以及一些媒合邀請與評價。
可以重複執行，已存在的資料不會重複建立。
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from allauth.account.models import EmailAddress

from apps.accounts.models import UserProfile
from apps.matching.models import MatchRequest, Message, Review
from apps.tutors.models import Subject, TutorProfile

DEMO_PASSWORD = "demo1234"

L = Subject.Level
SUBJECTS = [
    ("數學", L.ELEMENTARY), ("國語", L.ELEMENTARY), ("英文", L.ELEMENTARY), ("社會", L.ELEMENTARY),
    ("數學", L.JUNIOR), ("英文", L.JUNIOR), ("理化", L.JUNIOR), ("國文", L.JUNIOR),
    ("數學", L.SENIOR), ("英文", L.SENIOR), ("物理", L.SENIOR), ("化學", L.SENIOR), ("國文", L.SENIOR),
    ("微積分", L.COLLEGE), ("統計學", L.COLLEGE), ("經濟學", L.COLLEGE), ("Python 程式設計", L.COLLEGE),
    ("多益 TOEIC", L.GENERAL), ("日文", L.GENERAL), ("鋼琴", L.GENERAL),
]

TUTORS = [
    {
        "username": "teacher", "name": "林思妤",
        "headline": "讓數學變成你最有把握的一科",
        "school": "國立臺灣大學", "department": "數學系", "degree": "bachelor",
        "years": 4, "rate": (700, 1000),
        "city": "taipei", "mode": "both",
        "subjects": [("數學", L.JUNIOR), ("數學", L.SENIOR), ("微積分", L.COLLEGE)],
        "bio": "我相信每個人都學得會數學，只是需要對的切入點。上課會先診斷觀念哪裡卡住，再用生活例子把抽象概念講清楚。\n\n每堂課結束會給 3～5 題剛好的練習，下次上課先檢討，確保真的懂了才往下走。帶過的學生會考數學平均進步 2 個等級。",
    },
    {
        "username": "tutor_chen", "name": "陳柏翰",
        "headline": "物理化學不靠死背，靠理解",
        "school": "國立清華大學", "department": "物理學系", "degree": "master",
        "years": 6, "rate": (900, 1300),
        "city": "new_taipei", "mode": "in_person",
        "subjects": [("理化", L.JUNIOR), ("物理", L.SENIOR), ("化學", L.SENIOR)],
        "bio": "專攻國高中自然科。我會用簡單實驗和動畫幫你建立物理直覺，公式自然記得住。\n\n擅長帶學測、分科衝刺，也很歡迎基礎比較弱、想重新打底的同學。",
    },
    {
        "username": "tutor_wang", "name": "王語涵",
        "headline": "多益 900+，帶你用對方法學英文",
        "school": "國立政治大學", "department": "英國語文學系", "degree": "bachelor",
        "years": 5, "rate": (800, 1200),
        "city": "taipei", "mode": "online",
        "subjects": [("英文", L.JUNIOR), ("英文", L.SENIOR), ("多益 TOEIC", L.GENERAL)],
        "bio": "多益 965 分，曾在美國交換一年。課程以「聽說讀寫平衡」為主，依照你的目標（會考、學測、多益、出國）客製教材。\n\n上課全程線上，會提供共享筆記與單字卡，課後也能傳訊息問問題。",
    },
    {
        "username": "tutor_huang", "name": "黃冠宇",
        "headline": "統計系學長，期中期末救火隊",
        "school": "國立臺北大學", "department": "統計學系", "degree": "bachelor_student",
        "years": 2, "rate": (500, 700),
        "city": "new_taipei", "mode": "both",
        "subjects": [("統計學", L.COLLEGE), ("微積分", L.COLLEGE), ("經濟學", L.COLLEGE)],
        "bio": "大學必修卡關嗎？我修過也教過這些科目，知道老師出題的重點在哪裡。\n\n可以針對考古題逐題講解，也可以從頭幫你把章節觀念整理成一張圖。價格對學生友善。",
    },
    {
        "username": "tutor_lee", "name": "李承恩",
        "headline": "零基礎也能寫出第一個 Python 程式",
        "school": "國立陽明交通大學", "department": "資訊工程學系", "degree": "master",
        "years": 3, "rate": (1000, 1500),
        "city": "taoyuan", "mode": "online",
        "subjects": [("Python 程式設計", L.COLLEGE), ("數學", L.SENIOR)],
        "bio": "現職軟體工程師。教學以「做出東西」為目標：從爬蟲、資料分析到網站，每堂課都會完成一個小專案。\n\n也可以協助大學程式作業的除錯與觀念釐清。",
    },
    {
        "username": "tutor_tsai", "name": "蔡佳穎",
        "headline": "溫柔有耐心，國小孩子的學習夥伴",
        "school": "國立臺北教育大學", "department": "教育學系", "degree": "bachelor",
        "years": 7, "rate": (600, 800),
        "city": "taichung", "mode": "in_person",
        "subjects": [("數學", L.ELEMENTARY), ("國語", L.ELEMENTARY), ("英文", L.ELEMENTARY), ("社會", L.ELEMENTARY)],
        "bio": "擁有國小教師證，擅長陪伴孩子建立讀書習慣。會和家長定期回報學習狀況，一起找出最適合孩子的節奏。\n\n課程包含作業陪寫、閱讀理解與數學基礎加強。",
    },
    {
        "username": "tutor_chang", "name": "張雅婷",
        "headline": "國文作文從 B 到 A+ 的關鍵",
        "school": "國立臺灣師範大學", "department": "國文學系", "degree": "master",
        "years": 8, "rate": (900, 1200),
        "city": "taipei", "mode": "both",
        "subjects": [("國文", L.JUNIOR), ("國文", L.SENIOR)],
        "bio": "專注國文與寫作。會用拆解範文的方式帶你看懂「好文章為什麼好」，再一步步練出自己的寫作架構。\n\n文言文也會整理成好記的脈絡，不用死背翻譯。",
    },
    {
        "username": "tutor_liu", "name": "劉宇辰",
        "headline": "日文檢定 N1，日劇也能變教材",
        "school": "東吳大學", "department": "日本語文學系", "degree": "bachelor",
        "years": 3, "rate": (600, 800),
        "city": "tainan", "mode": "online",
        "subjects": [("日文", L.GENERAL)],
        "bio": "從五十音到 JLPT 檢定都可以教。喜歡用動漫、日劇片段練聽力，讓學日文不無聊。",
    },
    {
        "username": "tutor_wu", "name": "吳品萱",
        "headline": "古典鋼琴與樂理，成人初學也歡迎",
        "school": "國立臺灣藝術大學", "department": "音樂學系", "degree": "bachelor",
        "years": 10, "rate": (1000, 1400),
        "city": "kaohsiung", "mode": "in_person",
        "subjects": [("鋼琴", L.GENERAL)],
        "bio": "教學十年，學生年齡從 5 歲到 60 歲都有。可準備檢定與比賽，也可以單純學喜歡的流行歌。",
    },
]

STUDENTS = [
    ("student", "陳小明"),
    ("student_amy", "Amy 張"),
    ("student_kai", "許凱"),
]

# (學生, 老師, 科目, 狀態, 評分, 評語)
MATCHES = [
    ("student_amy", "teacher", ("數學", L.SENIOR), "accepted", 5, "思妤老師講解非常清楚，三角函數終於懂了！每次上課都有剛好的練習量。"),
    ("student_kai", "teacher", ("微積分", L.COLLEGE), "accepted", 5, "期中前臨時找老師救火，觀念整理超有條理，最後拿了 85 分。"),
    ("student_amy", "tutor_wang", ("多益 TOEIC", L.GENERAL), "accepted", 5, "兩個月從 650 進步到 820，老師的聽力技巧很實用。"),
    ("student_kai", "tutor_chen", ("物理", L.SENIOR), "accepted", 4, "很會用實驗舉例，只是進度有點快，跟老師說之後有調整。"),
    ("student_amy", "tutor_huang", ("統計學", L.COLLEGE), "accepted", 5, "學長很懂考試重點，價格也很實在。"),
    ("student_kai", "tutor_lee", ("Python 程式設計", L.COLLEGE), "accepted", 4, "做中學的方式很有成就感，第三週就寫出自己的爬蟲。"),
    ("student_amy", "tutor_chang", ("國文", L.SENIOR), "accepted", 5, "作文分數真的提升了，老師批改得很仔細。"),
    ("student", "teacher", ("數學", L.JUNIOR), "pending", None, ""),
    ("student_kai", "tutor_tsai", ("數學", L.ELEMENTARY), "rejected", None, ""),
]

PENDING_MESSAGES = {
    ("student", "teacher"): ("國二，函數和幾何比較弱，希望會考數學可以拿到 A。", "每週六下午"),
}


# 已接受的媒合裡，預先放幾則聊天訊息（True = 學生說的）
CHATS = {
    ("student_amy", "teacher"): [
        (True, "老師好！我是 Amy，高二，三角函數一直卡住。"),
        (False, "Amy 你好～我們第一堂先做個小診斷，看是哪個觀念沒接上。"),
        (True, "好的！這週六下午兩點可以嗎？"),
        (False, "可以，我們約在大安捷運站附近的咖啡廳，記得帶課本和最近的考卷。"),
    ],
}


class Command(BaseCommand):
    help = "建立家教媒合平台的展示資料"

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        subjects = {}
        for name, level in SUBJECTS:
            subject, _ = Subject.objects.get_or_create(name=name, level=level)
            subjects[(name, level)] = subject

        phone_numbers = iter(range(1, 100))

        def make_user(username, display_name):
            email = f"{username}@demo.tw"
            phone = f"+88691100{next(phone_numbers):04d}"
            user, created = User.objects.get_or_create(username=username, defaults={"email": email})
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            elif not user.email:
                user.email = email
                user.save(update_fields=["email"])
            EmailAddress.objects.update_or_create(
                user=user, email=user.email, defaults={"primary": True, "verified": True}
            )
            UserProfile.objects.update_or_create(
                user=user, defaults={"display_name": display_name, "phone": phone}
            )
            return user

        users = {}
        for data in TUTORS:
            user = make_user(data["username"], data["name"])
            users[data["username"]] = user
            tutor, _ = TutorProfile.objects.update_or_create(
                user=user,
                defaults={
                    "headline": data["headline"],
                    "bio": data["bio"],
                    "school": data["school"],
                    "department": data["department"],
                    "degree": data["degree"],
                    "years_of_experience": data["years"],
                    "hourly_rate_min": data["rate"][0],
                    "hourly_rate_max": data["rate"][1],
                    "city": data["city"],
                    "teaching_mode": data["mode"],
                    "contact_info": f"LINE ID：{data['username']}_line",
                    "is_accepting": True,
                },
            )
            tutor.subjects.set([subjects[key] for key in data["subjects"]])

        for username, name in STUDENTS:
            users[username] = make_user(username, name)

        for student, tutor, subject_key, status, rating, comment in MATCHES:
            tutor_profile = users[tutor].tutor_profile
            match = MatchRequest.objects.filter(student=users[student], tutor=tutor_profile).first()
            if match is None:
                message, schedule = PENDING_MESSAGES.get(
                    (student, tutor),
                    ("想加強這一科的觀念，也希望能多練習題目。", "平日晚上"),
                )
                match = MatchRequest.objects.create(
                    student=users[student],
                    tutor=tutor_profile,
                    subject=subjects[subject_key],
                    message=message,
                    preferred_schedule=schedule,
                    student_contact=f"LINE ID：{student}_line",
                    status=status,
                    tutor_reply="很高興認識你，我們在聊天室約時間！" if status == "accepted" else "",
                )
                if rating:
                    Review.objects.create(match_request=match, rating=rating, comment=comment)

            if (student, tutor) in CHATS and not match.messages.exists():
                for from_student, body in CHATS[(student, tutor)]:
                    Message.objects.create(
                        match_request=match,
                        sender=users[student] if from_student else users[tutor],
                        body=body,
                        is_read=True,
                    )

        self.stdout.write(self.style.SUCCESS("展示資料建立完成！"))
        self.stdout.write(f"  老師：teacher@demo.tw 或 0911000001，密碼 {DEMO_PASSWORD}（有一筆待回覆邀請）")
        self.stdout.write(f"  學生：student@demo.tw 或 0911000010，密碼 {DEMO_PASSWORD}")
        self.stdout.write(f"  學生 Amy：student_amy@demo.tw，密碼 {DEMO_PASSWORD}（和 teacher 有聊天紀錄）")
