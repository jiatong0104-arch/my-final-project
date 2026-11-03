# 良師配 PROJECT.md

> 給 Claude（和自己）看的精簡專案說明。開新對話時先讀這份，再只讀要改的檔案。
> 功能清單、網址、資料表、啟動方式的完整說明在 `README.md`，這裡不重複。
> 最後更新：2026-11-03

## 一句話

家教媒合平台：學生搜尋老師、送邀請；老師接受後雙方才看得到聯絡方式，可以聊天、評價。起點是 Python 全端開發（Django）期中作業，期中已報告完，現在考慮正式上線並收費。

## 技術

- Django 6.1、Python 3.13、套件用 `uv` 管理（`uv run manage.py ...`）
- django-allauth：信箱或手機號碼登入
- 前端：Django template + Tailwind（CDN 設定在 `apps/core/static/core/js/tailwind-config.js`）+ 少量原生 JS
- 資料庫：開發用 SQLite；`dj-database-url` 已裝，正式環境走環境變數
- 設定分 `config/settings/base.py / dev.py / prod.py`，金鑰放 `.env`（範本 `.env.example`）

## App 分工

| App | 負責 | 主要 Model |
|---|---|---|
| core | 首頁、共用版型、錯誤頁、學生／老師模式、上傳檔案工具 | （無） |
| accounts | 註冊、登入、手機號碼 | UserProfile、StudentProfile |
| tutors | 老師檔案、搜尋列表、身分認證、老師動態、`seed_demo` | Subject、TutorProfile、VerificationRequest、TutorPost |
| matching | 邀請流程、評價、聊天室 | MatchRequest、Review、Message |

## 已定案的設計決定（改之前先想清楚）

- 不分身分：每個帳號都能找老師，建立老師檔案就同時是老師；模式存在 session，只影響畫面不影響權限
- 老師接受邀請前，雙方看不到彼此聯絡方式
- 會改資料的動作一律 POST；GET 只讀
- 只能動自己的資料，別人操作一律回 404
- 上傳分公開 `media/` 與私密 `private_media/`；私密檔只能經權限檢查的 View 讀取，證件審核完即刪
- 聊天室用 fetch 每 3 秒輪詢（沒用 WebSocket）
- 程式結構照課堂範例：模板在 `apps/<app>/templates/<app>/`，靜態檔在 `apps/<app>/static/<app>/`

### 命名規則（2026-11-03 定案）

- **資料與後端一律用 `tutor`**：App、Model、Form、View、Admin、欄位、`related_name`、網址、模板、測試、`seed_demo`
  - 例：`TutorProfile`、`TutorProfileForm`、`TutorProfileCreateView`、`match.tutor`、`user.tutor_profile`
- **只有「學生模式／老師模式」這組畫面名稱用 `teacher`**，和 `student` 成對：
  - `apps/core/modes.py` 的 `TEACHER`、`is_teacher_mode`、`to_teacher` 等
  - Tailwind 主題色 `text-teacher`、`bg-teacher-light`（對應 `text-student`）
- 規則一句話：**資料用 tutor，畫面模式用 student / teacher**
- 其他：App 小寫複數；Model 單數大寫駝峰；欄位與 `related_name` 小寫底線；同一個概念只用一個英文字
- 中文顯示文字（`verbose_name`、畫面上的「老師」）不受影響

### 個人資料結構（2026-11-03 定案，尚未實作）

```
User（自訂 User model，吸收原本 UserProfile 的欄位）
 │  email、密碼、顯示名稱、手機、聯絡方式
 ├─ TutorProfile（當老師才有，一對一）
 └─ StudentProfile（送過邀請才有，一對一）
```

- 自訂 User model 取代內建 User，`UserProfile` 的欄位併入 User，之後刪除 `UserProfile`（上線前做，資料可用 `seed_demo` 重建）
- 兩個身分檔案都掛在 User 底下；每個帳號註冊時就有完整的基本資料，不會有「有帳號沒資料」的情況
- 聯絡方式只存一份（User 上）：刪除 `TutorProfile.contact_info` 與 `MatchRequest.student_contact`，需要時讀 `match.student.contact_info` / `tutor.user.contact_info`
- 原則：共用資料只存一處，其他地方用關聯去讀，不複製。只有「需要保留當時的值」才複製（例如 `VerificationRequest.education_snapshot`、之後每堂課的價格）
- 表單可以「帶入」User 上已填的資料、存回 User，讓使用者不用重複填，但資料庫裡仍只有一份

## 目前狀態

- 期中功能全部完成：搜尋篩選、邀請、聊天（含圖片、已讀）、評價、身分認證、老師動態
- 有測試：`uv run manage.py test apps`

## 下一步 / 想法

- [x] 清除 `TutorProfile = TeacherProfile` 別名
- [ ] 依命名規則把 `TeacherProfile` 一組改回 `TutorProfile`（下一個要做）
- [ ] 改為自訂 User model，併入 UserProfile、整理聯絡方式（見上方「個人資料結構」）
- [ ] 正式上線：上傳檔案改雲端儲存（S3 / R2）、選主機
- [ ] 收費：學生預約時綁卡，雙方確認上課後於上課當天自動扣款（金流候選：綠界、藍新、Stripe）
- [ ] 影片轉檔／串流服務（使用者變多時再做）

## 給 Claude 的工作規則

- 先讀這份，需要時再讀相關的一兩個檔案，不要整個專案掃一遍
- 直接在檔案做局部修改，不要在回覆裡重貼整個檔案
- 我是網頁開發新手：說明概念為主，不用逐行解釋
- 討論出新的專案決定或功能想法時，回答完問我是否要更新這份 PROJECT.md
