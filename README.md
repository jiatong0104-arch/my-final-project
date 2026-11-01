# 良師配：家教媒合平台

Python 全端開發期中專案。學生可以搜尋、篩選老師並送出家教邀請；老師建立檔案、接受或婉拒邀請；媒合成功後雙方才看得到彼此的聯絡方式，學生上完課可以留下評價。

## 啟動方式

在專案根目錄（有 `manage.py` 的資料夾）依序執行：

```bash
uv sync
uv run manage.py migrate
uv run manage.py seed_demo
uv run manage.py createsuperuser
uv run manage.py runserver
```

開啟 http://127.0.0.1:8000/

> `createsuperuser` 時**一定要填 email**：前台改用信箱或手機號碼登入，沒有 email 的管理員只能登入 `/admin/` 後台。

`seed_demo` 會建立展示資料，密碼都是 `demo1234`。登入時輸入**信箱或手機號碼**：

| 信箱 | 手機 | 身分 | 用途 |
|---|---|---|---|
| `teacher@demo.tw` | 0911000001 | 老師（林思妤） | 有一筆待回覆的邀請、和 Amy 的聊天紀錄 |
| `student@demo.tw` | 0911000010 | 學生（陳小明） | 示範搜尋老師、送出邀請 |
| `student_amy@demo.tw` | 0911000011 | 學生（Amy 張） | 示範聊天室 |

執行測試：`uv run manage.py test apps`

## 網站功能

| 網址 | 功能 |
|---|---|
| `/` | 首頁：選擇身分（學生／老師），往下看說明與註冊入口 |
| `/tutors/` | 老師列表：關鍵字、年級、科目、縣市、上課方式、時薪上限篩選與排序 |
| `/tutors/<id>/` | 老師詳細頁：介紹、科目、評價 |
| `/tutors/me/create/`、`/tutors/me/edit/`、`/tutors/me/delete/` | 建立、編輯、刪除自己的老師檔案（刪除前有確認頁） |
| `/matches/new/<老師id>/` | 送出家教邀請 |
| `/matches/` | 我的媒合：送出的邀請、收到的邀請（老師） |
| `/matches/<id>/accept/`、`reject/`、`cancel/` | 接受、婉拒、取消邀請（只接受 POST） |
| `/matches/<id>/review/` | 評價老師 |
| `/matches/<id>/chat/` | 聊天室（媒合成功的學生與老師） |
| `/matches/<id>/chat/messages/?after=<訊息id>` | GET：回傳新訊息的 JSON，聊天室每 3 秒查詢一次（只讀取，不改資料） |
| `/matches/<id>/chat/read/` | POST：把對方的訊息標記為已讀 |
| `/accounts/...` | django-allauth 註冊、登入（信箱或手機號碼）、登出 |
| `/admin/` | Django Admin 後台 |

## 資料表設計

```
User ─1:1─ UserProfile            （顯示名稱，註冊時建立）
User ─1:1─ TutorProfile           （有老師檔案的人就是老師）
TutorProfile ─M:N─ Subject        （老師可教的科目）
User(學生) ─1:N─ MatchRequest ─N:1─ TutorProfile
MatchRequest ─1:1─ Review         （已接受的媒合才能評價一次）
MatchRequest ─1:N─ Message        （聊天室訊息）
```

| Model | App | 課堂概念 |
|---|---|---|
| `UserProfile` | accounts | 一對一延伸 User、allauth 註冊表單、手機號碼（唯一） |
| `Subject` | tutors | Admin 管理資料、`IntegerChoices` |
| `TutorProfile` | tutors | 一對一、多對多、資料擁有權、`CheckConstraint`（最低時薪 ≤ 最高時薪） |
| `MatchRequest` | matching | 多對一、狀態流程、`UniqueConstraint`（同一對師生只能有一筆待回覆邀請） |
| `Review` | matching | 一對一、`Avg` 計算平均評分 |
| `Message` | matching | 多對一、`JsonResponse`、已讀狀態 |

## 設計重點

- **登入方式**：用信箱或手機號碼登入（`ACCOUNT_LOGIN_METHODS = {"email", "phone"}`），手機可輸入 0912-345-678 等格式，統一存成 +886912345678。
- **老師檔案**：學校、系所用下拉選單，清單沒有的選「其他」自行輸入；每個年級都能用「其他」新增科目；時薪是區間；自我介紹上限 5000 字。
- **聊天室**：媒合成功後雙方可以在網站上對話；用 `fetch` 每 3 秒向 JSON 網址查詢新訊息，導覽列會顯示未讀數。

- **不分身分**：每個帳號都能找老師；建立老師檔案後就同時是老師。
- **隱私**：老師接受邀請前，雙方都看不到對方的聯絡方式。
- **HTTP 方法**：會改變資料的動作（送出邀請、接受、刪除、標記已讀、登出）一律用 POST；GET 只負責讀取。
- **錯誤頁**：`apps/core/templates/404.html`、`500.html`。開發模式（`DEBUG = True`）仍會顯示 Django 的除錯頁，正式環境才會看到自訂錯誤頁。
- **擁有權**：只能編輯自己的老師檔案；只能回覆寄給自己的邀請、取消自己送出的邀請，其他人操作會得到 404。
- **網址參數**：列表用查詢參數做篩選（`?city=taipei&max_rate=800`），詳細頁用路徑參數（`/tutors/3/`）。
- **查詢效能**：`select_related`、`prefetch_related` 避免 N+1 查詢；篩選用子查詢，不會因為 JOIN 造成重複資料。

## 專案結構

照課堂的分工：每個 app 的模板放在 `apps/<app>/templates/<app>/`，CSS、JS 放在 `apps/<app>/static/<app>/`；專案根目錄的 `templates/` 只放 allauth 的覆寫。

```
config/settings/                base.py / dev.py / prod.py
apps/core/                      首頁、共用版型、404／500 錯誤頁
  templates/core/base.html      共用版型（導覽列、頁尾），其他頁面用 {% extends "core/base.html" %}
  templates/core/includes/      表單欄位、錯誤訊息的共用片段
  static/core/css/site.css      格線紙背景、田字格、表單樣式
  static/core/js/               Tailwind 設定、導覽列選單
apps/accounts/                  UserProfile、註冊表單、信箱／手機登入
apps/tutors/                    Subject、TutorProfile、老師列表與檔案、seed_demo 指令
  static/tutors/js/             老師檔案表單（「其他」輸入框、字數）
apps/matching/                  MatchRequest、Review、Message、媒合流程、聊天室
  static/matching/js/chat.js    聊天室（送出、每 3 秒查詢、標記已讀）
templates/account/              覆寫 allauth 的登入、註冊、登出頁
```
