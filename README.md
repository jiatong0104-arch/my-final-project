# 良師配：家教媒合平台

學生可以搜尋、篩選老師並送出家教邀請；老師建立檔案、接受或婉拒邀請；媒合成功後雙方才看得到彼此的聯絡方式，可以在網站上聊天、傳圖片，學生上完課可以留下評價。老師可以上傳證件申請「已認證」標章，也能在自己的主頁發文、分享照片和教學影片。

（起點是 Python 全端開發的期中專案。）

## 啟動方式

在專案根目錄（有 `manage.py` 的資料夾）依序執行：

```bash
uv sync
uv add pillow          # 第一次才需要：圖片上傳要用 Pillow
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
| `teacher@demo.tw` | 0911000001 | 老師（林思妤） | 有一筆待回覆的邀請、和 Amy 的聊天紀錄；**尚未認證**，可以示範申請認證 |
| `student@demo.tw` | 0911000010 | 學生（陳小明） | 示範搜尋老師、送出邀請 |
| `student_amy@demo.tw` | 0911000011 | 學生（Amy 張） | 示範聊天室 |

執行測試：`uv run manage.py test apps`

## 網站功能

| 網址 | 功能 |
|---|---|
| `/` | 首頁：選擇身分（學生／老師），往下看說明與註冊入口 |
| `/mode/` | POST：切換學生／老師模式（左上角顯示「學」或「師」，導覽列跟著換） |
| `/tutors/` | 老師列表：關鍵字、年級、科目、縣市、上課方式、時薪上限篩選與排序 |
| `/tutors/<id>/` | 老師主頁：介紹、科目、教學動態、評價 |
| `/tutors/me/create/`、`/tutors/me/edit/`、`/tutors/me/delete/` | 建立、編輯、刪除自己的老師檔案（刪除前有確認頁） |
| `/tutors/me/verify/` | 申請身分認證：上傳學生證或畢業證書 |
| `/tutors/me/posts/`、`/tutors/me/posts/<id>/delete/` | 發布、刪除自己的動態（只接受 POST） |
| `/tutors/verifications/<id>/document/` | 證件檔案，只有有權限的管理員看得到 |
| `/matches/new/<老師id>/` | 送出家教邀請 |
| `/matches/` | 我的媒合：送出的邀請、收到的邀請（老師） |
| `/matches/<id>/accept/`、`reject/`、`cancel/` | 接受、婉拒、取消邀請（只接受 POST） |
| `/matches/<id>/review/` | 評價老師 |
| `/matches/<id>/chat/` | 聊天室（媒合成功的學生與老師） |
| `/matches/<id>/chat/messages/?after=<訊息id>` | GET：回傳新訊息的 JSON，聊天室每 3 秒查詢一次（只讀取，不改資料） |
| `/matches/<id>/chat/read/` | POST：把對方的訊息標記為已讀 |
| `/matches/<id>/chat/images/<訊息id>/` | 聊天室圖片，只有聊天的兩人看得到 |
| `/accounts/...` | django-allauth 註冊、登入（信箱或手機號碼）、登出 |
| `/admin/` | Django Admin 後台 |

## 資料表設計

```
User ─1:1─ UserProfile            （顯示名稱，註冊時建立）
User ─1:1─ TutorProfile           （有老師檔案的人就是老師）
TutorProfile ─M:N─ Subject        （老師可教的科目）
User(學生) ─1:N─ MatchRequest ─N:1─ TutorProfile
MatchRequest ─1:1─ Review         （已接受的媒合才能評價一次）
MatchRequest ─1:N─ Message        （聊天室訊息，可以附圖片）
TutorProfile ─1:N─ VerificationRequest （身分認證申請）
TutorProfile ─1:N─ TutorPost      （老師動態：文字＋照片或影片）
```

| Model | App | 課堂概念 |
|---|---|---|
| `UserProfile` | accounts | 一對一延伸 User、allauth 註冊表單、手機號碼（唯一） |
| `Subject` | tutors | Admin 管理資料、`IntegerChoices` |
| `TutorProfile` | tutors | 一對一、多對多、資料擁有權、`CheckConstraint`（最低時薪 ≤ 最高時薪） |
| `MatchRequest` | matching | 多對一、狀態流程、`UniqueConstraint`（同一對師生只能有一筆待回覆邀請） |
| `Review` | matching | 一對一、`Avg` 計算平均評分 |
| `Message` | matching | 多對一、`JsonResponse`、已讀狀態、私密圖片 |
| `VerificationRequest` | tutors | 上傳檔案、Admin actions、有條件的 `UniqueConstraint`（同時只能有一筆審核中） |
| `TutorPost` | tutors | 上傳照片／影片、刪除時一起刪檔案（`post_delete` signal） |

## 設計重點

- **登入方式**：用信箱或手機號碼登入（`ACCOUNT_LOGIN_METHODS = {"email", "phone"}`），手機可輸入 0912-345-678 等格式，統一存成 +886912345678。
- **老師檔案**：學校、系所用下拉選單，清單沒有的選「其他」自行輸入；每個年級都能用「其他」新增科目；時薪是區間；自我介紹上限 5000 字。
- **聊天室**：媒合成功後雙方可以在網站上對話；用 `fetch` 每 3 秒向 JSON 網址查詢新訊息，導覽列會顯示未讀數。

- **不分身分、兩種模式**：每個帳號都能找老師，建立老師檔案後就同時是老師。模式存在 session，只影響畫面（左上角「學」／「師」、導覽列），不影響權限。
- **最高學歷**：高中職、專科、大學、碩士、博士，加上在學／畢業；選高中職只需要填校名。
- **身分認證**：未認證的老師一樣會出現在列表，只是沒有「已認證」標章；學生可以勾選「只看已認證」。管理員在後台 `身分認證申請` 開啟證件、執行「通過」或「退回」。修改學歷會自動拿掉標章。
- **上傳檔案**：分成公開（`media/`：老師動態的照片、影片）和私密（`private_media/`：證件、聊天圖片）。私密檔案沒有網址，只能經過檢查權限的 View 讀取；證件在審核完成後立刻刪除。上傳的圖片會重新存檔，縮小尺寸並清掉 EXIF（例如手機照片裡的 GPS 位置），檔名換成隨機字串。
- **隱私**：老師接受邀請前，雙方都看不到對方的聯絡方式。
- **HTTP 方法**：會改變資料的動作（送出邀請、接受、刪除、標記已讀、登出）一律用 POST；GET 只負責讀取。
- **錯誤頁**：`apps/core/templates/404.html`、`500.html`。開發模式（`DEBUG = True`）仍會顯示 Django 的除錯頁，正式環境才會看到自訂錯誤頁。
- **擁有權**：只能編輯自己的老師檔案；只能回覆寄給自己的邀請、取消自己送出的邀請，其他人操作會得到 404。
- **網址參數**：列表用查詢參數做篩選（`?city=taipei&max_rate=800`），詳細頁用路徑參數（`/tutors/3/`）。
- **查詢效能**：`select_related`、`prefetch_related` 避免 N+1 查詢；篩選用子查詢，不會因為 JOIN 造成重複資料。

## 正式上線前要處理的事

- **上傳檔案的存放位置**：`media/`、`private_media/` 目前存在主機的硬碟。很多雲端主機（例如 Render、Heroku）重新部署時會清空硬碟，所以正式上線要改用雲端儲存（例如 S3、Cloudflare R2），私密檔案要用「有時效的簽名網址」或繼續由 View 轉送。
- **影片**：現在是直接存原始檔。iPhone 拍的 `.mov`（HEVC）在部分電腦瀏覽器播不出來；使用者變多時，建議改接影片服務（Cloudflare Stream、Bunny Stream、Mux），自動轉檔、壓縮與串流。
- **上傳大小**：網頁伺服器（Nginx 等）也要設定上限（例如 `client_max_body_size 200m`），不然大影片會被擋下。
- **收費**：媒合費或會員方案要串金流（綠界、藍新、Stripe），金流的測試與正式金鑰都放在環境變數。

## 專案結構

照課堂的分工：每個 app 的模板放在 `apps/<app>/templates/<app>/`，CSS、JS 放在 `apps/<app>/static/<app>/`；專案根目錄的 `templates/` 只放 allauth 的覆寫。

```
config/settings/                base.py / dev.py / prod.py
apps/core/                      首頁、共用版型、404／500 錯誤頁、學生／老師模式
  modes.py                      模式存在 session；context processor 提供 {{ is_teacher_mode }}
  uploads.py                    上傳檔案：私密儲存、隨機檔名、檢查圖片／證件／影片
  files.py                      把私密檔案送給已通過權限檢查的人
  templates/core/base.html      共用版型（導覽列、頁尾），其他頁面用 {% extends "core/base.html" %}
  templates/core/includes/      表單欄位、錯誤訊息的共用片段
  static/core/css/site.css      格線紙背景、田字格、表單樣式
  static/core/js/               Tailwind 設定、導覽列選單
apps/accounts/                  UserProfile、註冊表單、信箱／手機登入
apps/tutors/                    Subject、TutorProfile、VerificationRequest、TutorPost、seed_demo 指令
  static/tutors/js/             老師檔案表單（「其他」、高中職、字數）、發動態（預覽、大小檢查）
apps/matching/                  MatchRequest、Review、Message、媒合流程、聊天室
  static/matching/js/chat.js    聊天室（送出文字和圖片、每 3 秒查詢、標記已讀）
templates/account/              覆寫 allauth 的登入、註冊、登出頁
```
