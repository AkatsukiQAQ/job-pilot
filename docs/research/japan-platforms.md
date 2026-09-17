# 日本新卒平台、公司招聘页与 ATS：只读可获取什么

> **AI 调研附录**（生成于 2026-09-16，英文）。内容由并行调研 agent 对照官方页面整理，verified/unverified 标注以原文为准；实现前需再次核对。相关更正见 japan-critique.md 与 proposal-judgments.md。

# Japan 新卒 / new-grad-friendly job platforms, company career pages and ATS vendors: what JobPilot can ingest read-only (Gmail read-only, public JSON/RSS, exports) for a 2027卒 AI/ML candidate late in the cycle (2026-09-16)

## Summary
Verified against official pages: (1) None of the big Japanese navi sites (マイナビ, リクナビ, ONE CAREER, 外資就活, unistyle, キャリタス, Goodfind, OfferBox, LabBase, Bizreach Campus, OpenWork, paiza, サポーターズ) offer a user-facing export or public API for the user's own data (applied companies, MyPage status, ES deadlines, bookings). The only compliant ingestion path for them is the notification email each one sends to the user's Gmail, plus manual entry. (2) Scraping is explicitly prohibited by マイナビ (sitepolicy: 'ロボットや巡回プログラム等を用いて機械的に取得する行為'), Wantedly (crawl/scrape/data-mining incl. 'AI またはエージェント型 AI'), Bizreach Campus ('自動巡回プログラム', 'クローリング'), OpenWork ('断続的な機械的なアクセス行為、コンテンツを一括ダウンロードする行為'), and LinkedIn (User Agreement 8.2). ONE CAREER, 外資就活, unistyle, Goodfind, paiza, リクナビ, HelloWork have no literal 'scraping' clause but have private-use-only / 業務妨害 / 不適切 catch-alls, so scraping logged-in pages is still an account-termination risk. (3) Public JSON exists for the ATS layer used by foreign/startup employers: Greenhouse Job Board API (no auth), Lever Postings API (no auth), Workable widget API (verified for Mercari: 324 jobs incl. '28卒対象' and 'Internship' titles; SmartNews also on Workable), Workday cxs endpoint (POST-based read, unverified here). HERP (Tier IV), HRMOS (Visional, CyberAgent 中途), TalentIO (PFN) are HTML-only with no feed. (4) Japanese 新卒 MyPages are concentrated on a handful of ATS domains that JobPilot should recognise as email senders/link targets: *.snar.jp (SONAR ATS: Toyota, DeNA, CyberAgent, Sony Network), *.i-web.jpn.com (i-web/Humanage), job.axol.jp + axol.jp (マイナビ アクセスオンライン: Nomura, logs in with マイナビ会員ID), www.e2r.jp/ja/{company}{year}/ (Hitachi), plus company-owned domains (mypage.smbc-recruitment.jp, www.mypage.bk.mufg.jp). (5) Late-cycle status as of today: Rakuten opened 'Applications for October 2027 Entry' on 2026-09-01; Mercari is 通年採用 via Workable; Sakana AI hires via careers@sakana.ai + Google Form with Intern/Visiting Researcher options; Tier IV lists '5002_学生データエンジニア' on HERP; Recruit, LINEヤフー and Nomura have closed 2027 entry. (6) Existing 就活管理アプリ (two iOS '就活管理' apps, Jobhun, Notion/Spreadsheet templates, i-web CONNECT) are all manual-entry MyPage/ID trackers with no email ingestion, no calendar sync and no export; that is JobPilot's differentiator.

## Items
### マイナビ2027 (job.mynavi.jp/2027/) [medium]
Largest 新卒 navi site (株式会社マイナビ). Holds the user's エントリー企業 list, 説明会/セミナー予約, 企業からのメッセージ/DM/スカウト (受信箱・お返事箱), and My CareerBox ES submissions with 締切. Login via My CareerID; the same マイナビ会員ID also logs into company MyPages on axol.jp (アクセスオンライン).
Read-only access: Email only. Official senders to allow (Q&A page): sys2027@job.mynavi.jp (system mail), info-job@miws.mynavi.jp (企業からのメッセージ via MIWS), mcbox.user@mcbox.mynavi.jp (My CareerBox 締切リマインド), job-s27@mynavi.jp / job-h27@mynavi.jp (smartphone). Domain allowlist 'mynavi.jp'. No export, no API for students. Site policy prohibits 'ロボットや巡回プログラム等を用いて機械的に取得する行為' and applies to anyone who merely accesses the site — scraping is a ToS violation.
Notes: 利用規約 (2025-04-01) 第5条 has no literal scraping clause but includes '業務の運営を妨げる行為' and 'その他、当社が不適切と判断する行為'. Messages are mirrored in マイページ 受信箱, so a Gmail filter on the three sender addresses captures the same data. AI/ML roles are rare here; value is 秋採用 listings from manufacturing/finance and the SSO into axol MyPages.
Src: https://job.mynavi.jp/conts/2027/kaiin/message.html
### リクナビ2027 (job.rikunabi.com) [medium]
Recruit's 新卒 navi site; requires リクルートID. Holds プレエントリー companies, OpenES, 説明会予約, 企業からのお知らせ. Scout applications via Indeed use an @indeedemail.com alias.
Read-only access: Email only. Exact sender address could not be verified (help.job.rikunabi.com is a JS Salesforce site that returned 503); use domain-level filters on rikunabi.com, recruit.co.jp and indeedemail.com and confirm from a real message header. No export/API for students. リクナビ会員規約 prohibits 無断複製 of 企業情報/コンテンツ and 'その他当社が不適切と判断する行為'; リクルートID規約 (cmm-t-1022) lets Recruit suspend the whole Recruit ID (Airリザーブ, ホットペッパー etc.) for a violation on one service — an extra reason not to scrape.
Notes: リクルートWEBサービス API (rws-t-1001) exists but covers other Recruit media, not 新卒 job data. The 2022/2024/2026 会員規約 are at cdn.p.recruit.co.jp/terms/{r26-t-1001,...}; the 2027 version is likely r27-t-1001 (not fetched).
Src: https://cdn.p.recruit.co.jp/terms/ngr-t-1001/index.html
### ONE CAREER / ワンキャリア (onecareer.jp) [high]
締切カレンダー for 本選考/インターン, 体験談/ES database, イベント, scouts, company pages. The go-to 秋採用/通年採用 deadline source for 27卒 right now. Has 'ONE CAREER for Engineer' as a separate product.
Read-only access: Email only. Registration mail subject '【ONE CAREER】新規登録確認メール'; subject prefix '【ONE CAREER】' is the pattern to filter on. Sender address not confirmed (support.onecareer.jp returns 403 to fetchers). No export/API. 利用規約 第14条 (30 items) has no literal scraping clause; relevant items: 1 (無断複製 of 体験記), 16 (server load / 運営妨害), 28 (目的外利用), 29-30. Terms were amended 2025-09-16; re-check before shipping.
Notes: Public deadline data is broadcast on X (@onecareerjp) — no RSS. Notification settings: web マイページ → 受信設定 → メール配信の設定; app → その他 → 通知設定. '重要なお知らせ' mails are sent regardless of settings.
Src: https://www.onecareer.jp/infos/terms
### 外資就活ドットコム (gaishishukatsu.com) [high]
Foreign-capital / consulting / 総合商社 focused 新卒 site (ハウテレビジョン). 締切一覧 of 募集情報, コミュニティ, scouts, events. Requires a university email (.edu/.ac.uk/.ubc.ca accepted for overseas) or student ID upload.
Read-only access: Email only. Official FAQ names the sender to allow: info@gaishishukatsu.com. No export/API. 利用規約 第10条: all information obtained may only be used for '会員の個人としての私的利用' — no reproduction/publication; no explicit bot clause but this covers bulk copying. Scraping is therefore grey-to-prohibited; stick to email.
Notes: Maintenance windows announced on site (e.g. 9/15 5:00-7:00). X account @gaishishukatsu posts 27卒/28卒 deadlines. Relevant for McKinsey/BCG/Accenture/Nomura-type 通年 and 秋 openings.
Src: https://gaishishukatsu.com/faq
### unistyle (unistyleinc.com) [medium]
ES/ガクチカ database plus weekly 締切まとめ (unistyleinc.com/topics), LINE オープンチャット, app. Operated by Unistyle株式会社 (ネオキャリア group). Distributes a 企業管理シート spreadsheet template for tracking MyPages/選考状況.
Read-only access: Email only (heavy メルマガ; sender not verified, expect @unistyleinc.com). Weekly deadline lists are public HTML at /topics but 利用規約 (/rule) has an IP clause and '(11)他のユーザーの個人情報を収集、蓄積する行為'; no literal scraping clause. No export/API.
Notes: Registration triggers 同時登録 with partner services (e.g. doda campus) — expect extra sender domains after signup. Their 企業管理シート is a useful reference schema for JobPilot's company table.
Src: https://unistyleinc.com/rule
### キャリタス就活2027 (job.career-tasu.jp/2027/) [low]
Navi site by 株式会社キャリタス (ex-DISCO). Holds エントリー, イベント申込, 企業メッセージ. Also runs キャリタス就活エージェント and 学生モニター.
Read-only access: Email only. Official help: allow domain '@career-tasu.jp'; related services send from @career-tasu.co.jp (syoukai@career-tasu.co.jp for エージェント, career-tasu_research@career-tasu.co.jp for モニター). Mail is mirrored in マイページ → メッセージBOX → 「キャリタスより」. No export/API. 2027 help pages were not reachable (404); scraping clause not verified.
Notes: Phishing warnings posted on agent MyPage — filter strictly on the two domains.
Src: https://job.career-tasu.jp/2021/help_index/mail.html
### LabBase就職 (labbase.jp / compass.labbase.jp) [high]
Scout platform for 理系 research students (株式会社LabBase). Student registers 研究内容/skills; companies send 通常スカウト / 特別スカウト (ES免除, インターン招待, 個別面談). '興味あり' button, events (LabBase SUMMIT online on 10/3 with Panasonic, Shiseido, Fujifilm).
Read-only access: Email only. メルマガ通知 toggle at labbase.jp/student/setting/mail_magazine; '選考に関わる連絡など重要な通知' are sent regardless. Sender address not published (expect @labbase.jp); help center at labbasestudent.zendesk.com. Student terms are a PDF (terms_student_5_2.pdf) that could not be text-extracted here — read before any scraping; treat as prohibited by default.
Notes: Best fit for research-track (e.g. VLM/multimodal) profiles; scouts arrive by email so Gmail ingestion covers it.
Src: https://compass.labbase.jp/
### Goodfind (goodfind.jp) [medium]
スローガン株式会社's curated startup/consulting career site: skill seminars, 厳選企業 intern/選考 info, seminar reservations (マイページ → セミナー → 予約中).
Read-only access: Email only (メールマガジン配信設定 in マイページ; sender not verified). 利用規約 lists 6 prohibited acts with no explicit scraping clause, but 'Goodfindの運営を妨げる行為' plus a damages clause and login-gating make scraping risky. No export/API.
Notes: Seminar cancellation deadline: 2 days before; repeated no-shows restrict future bookings — a useful reminder rule for JobPilot's calendar.
Src: https://www.goodfind.jp/terms
### OfferBox (offerbox.jp, app.offerbox.jp) [medium]
Reverse-scout 新卒 platform (株式会社i-plug). Holds received オファー (with 承認/保留 status), profile, 就職活動状況 flag.
Read-only access: Email + push. Official help: sender info@offerbox.jp, subject pattern '【OfferBox】 ユーザー仮登録が完了しました'; allow domain '@offerbox.jp'. 通知設定 controls per-event mail. No export/API. Full student terms page not located; help states multiple accounts are prohibited.
Notes: Apple-ID users may be registered under @privaterelay.appleid.com. 2025卒 accounts were locked on 2025-10-01 — expect the same cutoff for 2027卒 on 2027-10-01, so ingest early.
Src: https://offerboxhelp.zendesk.com/hc/ja/articles/360052681973
### Wantedly (wantedly.com) [high]
Startup-heavy 'casual visit' platform; holds 話を聞きに行きたい applications, company messages, scouts (setting: 受け取らない / 月5通 / 何通でも).
Read-only access: Email only. 利用規約 explicitly bans crawl/scrape/data-mining by 'ボット、スクレイパー、スパイダー、AI またはエージェント型 AI' (except robots.txt scope) and bans using content for AI training. Unanswered-scout reminders go out every Friday around 15:00 by mail/push. Sender not confirmed (help page 403; expect @wantedly.com). Partner API利用規約 exists but is for companies, not users.
Notes: Manage at 設定 → メール通知. Strong fit for AI startups; also hosts many 新卒歓迎 postings that are not on navi sites.
Src: https://service-terms.wantedly.com/user_terms/ja_JP
### ビズリーチ・キャンパス (br-campus.jp) [medium]
OB/OG訪問 + scout platform (Visional). 123 universities; scouts offer 選考免除/限定セミナー; industry/role events.
Read-only access: Email only. 利用規約 第13条 permits 事務連絡/メールマガジン to the registered address (sender not published; expect @br-campus.jp). Scraping is explicitly prohibited: 第12条2項 forbids any use 'クローリングを含みますが、それに限りません'; 第16条2項7号キ⑩ forbids '自動巡回プログラムを用いる等の方法をもって...負荷をかけ'. No export/API.
Notes: Useful for OB訪問 scheduling — those bookings arrive as emails and should map to calendar items.
Src: https://br-campus.jp/staticpages/terms
### OpenWork (openwork.jp) [medium]
Company-review site with 新卒 求人 and 内定者 就活レポート (/student_report/list, /guide/student). Used for company research rather than tracking.
Read-only access: Email only for recommendations (sender not verified). Scraping explicitly prohibited: 利用規約 (/rule.php) 第11条1項12号 '本サービスへ断続的な機械的なアクセス行為、コンテンツを一括ダウンロードする行為又はそれに類する行為'. No export/API.
Notes: Recommended by 外資就活's own '27卒 apps' article for internal company info. Store only the URL of a company page in JobPilot; do not cache review text.
Src: https://www.openwork.jp/rule.php
### paiza新卒 (paiza.jp/student) [medium]
Engineer-only 新卒 site: スキルチェック rank (aim for B以上), 669 IT engineer 求人 at fetch time, scouts to high-rank students, direct 選考.
Read-only access: Email only (第1条2項 permits 通知メール; sender not verified, expect @paiza.jp). Public job list HTML at /student/job_offers, /student/job_offers/list/new_graduate_occupation-{ID}, .../new_graduate_industry-{ID}, ?dev_languages[]={code}. 利用規約 第24条5項 limits use of obtained information to 私的利用 — no literal bot clause, but bulk copying is out. No API/RSS.
Notes: Positions skew to web/SaaS engineering rather than ML research, but 新卒エンジニア roles are still open late in the cycle.
Src: https://paiza.jp/guide/kiyaku
### サポーターズ (talent.supporterz.jp / biz.supporterz.jp) [high]
Engineer-student matching (新卒採用マッチング on '日本最大級のエンジニア学生DB') plus 技育プロジェクト (技育祭, 技育CAMP hackathons). 1on1 面談 events with companies.
Read-only access: Email only; sender and terms not verifiable (talent.supporterz.jp is a browser-gated SPA). No export/API.
Notes: Historically strong for CyberAgent/DeNA/LINEヤフー-type engineer 新卒 and for 27卒 秋 matching events. Treat as email-ingest only.
Src: https://corp.supporterz.jp/
### TokyoDev (tokyodev.com/jobs) [medium]
English-language job board for developers in Japan. URL pattern /companies/{company}/jobs/{slug}. Seniority filter includes Intern/Junior but listings are mostly mid/senior (only a few intern roles at fetch time).
Read-only access: Newsletter email (/newsletters). No RSS/JSON found (/jobs.rss returns 403). Public HTML listing; no ToS scraping clause checked — prefer newsletter.
Notes: Good for foreign-capital engineering roles in Tokyo; not 新卒-oriented.
Src: https://www.tokyodev.com/jobs
### Japan Dev (japan-dev.com) [medium]
English job board; URL pattern /jobs/{company}/{company}-{title}-{id}. Filters by tech/job type; no junior/new-grad filter.
Read-only access: Newsletter email via /signup ('hand-picked tech jobs in Japan – straight to your inbox'). No RSS/JSON/API found (/jobs.rss 404).
Notes: Similar profile to TokyoDev; overlap with Mercari/SmartNews/PayPay listings.
Src: https://japan-dev.com/
### LinkedIn (linkedin.com) — Japan usage for foreign firms/startups [high]
Primary channel for foreign-capital firms, AI labs and startups in Japan; job alerts, recruiter InMail, Easy Apply confirmations.
Read-only access: Email: job alerts / application confirmations / messages arrive from *.linkedin.com (commonly jobs-noreply@, jobalerts-noreply@, messages-noreply@linkedin.com — not re-verified here; LinkedIn's help page only names phishing@linkedin.com and says legitimate mails carry a security footer with your name and headline). Export: LinkedIn's 'Get a copy of your data' download (Settings → Data privacy) includes job applications — knowledge-based, verify. Scraping prohibited: User Agreement 8.2(2) '...scripts, robots... to scrape or copy the Services' and 8.2(13) bots/automated access.
Notes: Do not automate LinkedIn; ingest alert emails and the periodic data export only.
Src: https://www.linkedin.com/legal/user-agreement
### ハローワークインターネットサービス / 新卒応援ハローワーク [low]
Public employment service. Online 求人検索 at https://www.hellowork.mhlw.go.jp/kensaku/GECA110010.do?action=initDisp&screenId=GECA110010; 求職者マイページ for saved searches/messages. 新卒応援ハローワーク = dedicated offices for students and graduates within roughly 3 years (details page returned 404; description knowledge-based).
Read-only access: No public API/RSS/CSV for individuals; job data is provided institutionally to 民間人材ビジネス via 求人情報提供サービス (not for personal apps). 利用規約 第15条 bans '...システム又はセキュリティに支障又は危険を及ぼす可能性のある一切の行為'; 第19条 references 転載・利用 violating the site policy. マイページ notification emails come from the mhlw.go.jp domain (exact sender not verified).
Notes: Low yield for AI roles; keep as optional manual source.
Src: https://www.hellowork.mhlw.go.jp/info/terms.html
### ATS: Greenhouse Job Board API [high]
Public read API for any employer on Greenhouse. GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs (?content=true for description/department/office), /jobs/{id}, /departments, /offices. 'Job Board data is publicly available, so authentication is not required for any GET endpoints.'
Read-only access: Public JSON, no auth, GET only — fully compliant with the read-only constraint. No documented rate limit.
Notes: Token 'mercari' exists but returned only 2 US jobs (Mercari Japan is on Workable). Tokens tried for Woven by Toyota (wovenbytoyota, woven-by-toyota, wovenplanet, woven) and SmartNews (smartnews, smartnewsinc) all 404 — discover tokens from the employer's careers page HTML (gh_jid / boards.greenhouse.io links) rather than guessing.
Src: https://docs.greenhouse.io/job-board.html
### ATS: Lever Postings API [medium]
Public read API: GET https://api.lever.co/v0/postings/{SITE}?mode=json&skip=&limit=&location=&team=&department=&commitment=&level=; single posting at /v0/postings/{SITE}/{POSTING-ID}. EU tenants at api.eu.lever.co.
Read-only access: Public JSON, no auth for GET. Only the POST apply endpoint needs a key (and JobPilot never applies).
Notes: Fewer Japanese employers than Greenhouse/Workable; check site slug from jobs.lever.co links.
Src: https://github.com/lever/postings-api
### ATS: Workable (apply.workable.com) — Mercari, SmartNews [high]
Workable-hosted job boards. Verified public widget API: GET https://apply.workable.com/api/v1/widget/accounts/mercari returned name 'Mercari, inc.', 324 jobs, titles such as '28卒対象 / Circular Economy Researcher - Mercari Group (Internship)' and 'AI Research Scientist, R4D, Mercari'; job URLs https://apply.workable.com/j/{SHORTCODE}. SmartNews careers (careers.smartnews.com) links to https://apply.workable.com/smartnews/.
Read-only access: Public JSON via the widget endpoint (GET, no auth). Mercari 新卒 page states '通年採用を実施している' and targets '2028年4月以降に入社が可能な16歳以上の学生'.
Notes: Filter titles on '新卒', 'New Grad', '卒対象', 'Internship'. Workable's own ToS on widget use was not reviewed — the endpoint is the one their embeddable widget uses, so treat as public but poll gently (e.g. hourly).
Src: https://careers.mercari.com/new-graduates/
### ATS: Workday (myworkdayjobs.com) — Accenture Japan, likely other foreign firms [medium]
Accenture Japan job search links to accenture.wd103.myworkdayjobs.com ('応募履歴の確認'). Workday tenants expose a JSON search at POST https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs with body {appliedFacets, limit, offset, searchText}; GET returns HTML.
Read-only access: JSON is reachable only via HTTP POST (a read query, writes nothing) — unverified here because shell access was denied. Decide whether a read-only POST search is acceptable under the HARD CONSTRAINT; otherwise ingest Workday application emails ({tenant}@myworkday.com style senders) instead.
Notes: Application-status emails from Workday tenants are a reliable read-only signal for status changes.
Src: https://www.accenture.com/jp-ja/careers/jobsearch
### ATS: HERP Careers (herp.careers) — Tier IV [high]
Job board at https://herp.careers/v1/tier4 ('Powered by HERP'); job URL pattern https://herp.careers/v1/tier4/{job-id}. 59 positions at fetch time, including category '01. Students / New graduates' with '5002_学生データエンジニア'.
Read-only access: Public HTML only; no RSS/JSON (/feed and .rss 404). HERP application mails go to the candidate's email — ingestible.
Notes: Tier IV (autonomous driving, Autoware) is a direct fit; monitor the page HTML for changes politely or rely on their mails.
Src: https://herp.careers/v1/tier4
### ATS: HRMOS採用 (hrmos.co/pages/{company}) — Visional, CyberAgent 中途 [low]
Bizreach's ATS career pages, e.g. https://hrmos.co/pages/visional/jobs/0000381, https://hrmos.co/pages/cyberagent-group (キャリア採用). Footer: 'HRMOS利用基本規約'.
Read-only access: Public HTML; no RSS/JSON endpoints visible. Mostly 中途 boards; 新卒 for these companies runs elsewhere.
Notes: Preferred Networks is NOT on HRMOS (404) — it is on TalentIO.
Src: https://hrmos.co/pages/visional/jobs
### ATS: TalentIO (open.talentio.com) — Preferred Networks [high]
PFN careers link to https://open.talentio.com/r/1/c/preferred/homes/4619 (新卒採用) and .../homes/4618 (キャリア採用・第二新卒). PFN 2027 timeline: プレエントリー 2025-09-01, 第1期 2025-11-04, 第2期 2025-12-01.
Read-only access: Public HTML; no verified public JSON. TalentIO sends applicant emails (sender domain not verified).
Notes: Check whether a 第3期 or 通年 window exists for 27卒 — PFN also hires interns year-round.
Src: https://www.preferred.jp/ja/careers/
### ATS: SONAR ATS (*.snar.jp, Thinkings) — Toyota, DeNA, CyberAgent, Sony Network Communications [high]
新卒 MyPage system. Verified tenants: toyota-saiyo.snar.jp (2027卒 and 2028以降), dena.snar.jp (AIスペシャリスト / AIジェネラリスト courses, '2027年4月入社 or 2026年10月入社'), cyberagent.snar.jp/login.aspx, sonynetwork.snar.jp/index.aspx. Manager side: manager.snar.jp.
Read-only access: Email only: MyPage notifications (説明会予約, 選考結果, 面接日程) are emailed; sender is either the company's own address or an snar.jp address (not verified). Login pages are ASP.NET (.aspx); no public API. Scraping a MyPage means automating an authenticated session — avoid.
Notes: Recognise any URL matching https://{tenant}.snar.jp/ in email bodies as a MyPage link and attach it to the company record.
Src: https://recruit.toyota/
### ATS: i-web (Humanage) — *.i-web.jpn.com MyPages + i-web CONNECT app [high]
No.1 新卒 ATS; MyPages at https://{company}.i-web.jpn.com/{year}/ (e.g. fujifilm, jcb, mitsui, shiseido) or https://mypage.{id}.i-web.jpn.com/. The 'i-web CONNECT' app aggregates all i-web MyPages with one login and shows お知らせ 'メールと異なり、埋もれずに'.
Read-only access: Email only; sender domain varies (company domain or i-web domain — Humanage publishes no whitelist page). Real-time integration with リクナビ/キャリタス means MyPage invitations are auto-mailed right after navi エントリー.
Notes: i-web CONNECT is the closest official 'aggregator' competitor, but it only covers i-web tenants and has no export.
Src: https://i-web-ats.humanage.co.jp/
### ATS: axol / マイナビ アクセスオンライン (job.axol.jp, axol.jp) — Nomura [medium]
Mynavi's ATS. Nomura 2027 MyPage: https://job.axol.jp/bx/s/nomura_27/mypage/login (ID番号 + パスワード, or 'マイナビ会員ID･パスワードでログイン'); 2028: https://axol.jp/zw/s/nomura_28/mypage/login. Nomura's 2027 entry closed 2026-02-26.
Read-only access: Email only (sender likely on mynavi.jp or axol.jp — unverified). URL patterns job.axol.jp/bx/s/{company}_{yy}/ and axol.jp/zw/s/{company}_{yy}/ identify the tenant.
Notes: Because it accepts マイナビ会員ID, the same Gmail account receives both navi and MyPage mail.
Src: https://www.nomura-recruit.jp/
### ATS: e2R (www.e2r.jp) — Hitachi [medium]
Hitachi 2027 新卒 MyPage at https://www.e2r.jp/ja/hitachi2027/ ('HITACHI RECRUITING MY PAGE'), reminders at www.e2r.jp/eARTH/e2r/user/{IdReminder,PasswordReminder}?siteID=hitachi2027, support portal support.portal.e2r.jp. Vendor name not shown on page.
Read-only access: Email only; sender not verified.
Notes: Pattern www.e2r.jp/ja/{company}{yyyy}/ — treat as MyPage link type.
Src: https://www.hitachi.com/ja-jp/recruit/
### Company-owned MyPage domains — SMBC, MUFG, Sony [low]
SMBC: https://mypage.smbc-recruitment.jp/2027/ (also /2028/, /overseas/). MUFG Bank: https://www.mypage.bk.mufg.jp/mufgbank2027/ (2028 site opened 2026-06-01). Sony Group: 2027/2028 共通 sites at https://www.recruit.sony.co.jp/2027/ and /2028/ ('業務委託先ページへ遷移'); MyPage domain not exposed on the landing page.
Read-only access: Email only; senders not published. These are probably white-labelled i-web/SONAR tenants — confirm from email headers.
Notes: 2027 MyPages are still linked, i.e. 秋 additional rounds may exist, but as of 2026-09-16 (two weeks before 内定式) treat banks as low probability.
Src: https://www.saiyo.bk.mufg.jp/
### Company: Sakana AI (sakana.ai/careers) [high]
No ATS. Roles listed as cards (Research/Product/GTM/Corporate); apply by emailing careers@sakana.ai and filling a Google Form (forms.gle/NFE3U5XoiYLWhnH48). Listed: 'Applied Research Engineer (Product)' (Full-time/Contract/Intern), 'Member of Technical Staff (RSI Lab)' (Full-time/Visiting Researcher/Internship), 'Business Intern (Product Team)'.
Read-only access: Public HTML page (monitor for changes); replies arrive from @sakana.ai — ingest by sender domain. No feed.
Notes: Applied Research Engineer is an exact title match for the example target roles; Internship/Visiting Researcher tracks fit a 2027卒 still in school.
Src: https://sakana.ai/careers/
### Company: Rakuten (global.rakuten.com/corp/careers/graduates/) [high]
New-grad program with fixed intakes: 'Applications for October 2027 Entry are now open' (posted 2026-09-01); April 2027 opened 2026-01-13. Apply platform not exposed on the page (Rakuten corporate careers historically on Workday; unverified).
Read-only access: Public HTML news list; application/status emails from rakuten.com domains.
Notes: An October 2027 intake is one of the few large-company windows still open for a 2027卒 as of today.
Src: https://global.rakuten.com/corp/careers/graduates/
### Companies with 2027 entry closed (verified): 株式会社リクルート, LINEヤフー, 野村證券 [low]
Recruit: '2027年度新卒採用のエントリー受付は終了いたしました' (2026-04-01; courses エンジニア / プロダクトグロース / データスペシャリスト). LINEヤフー newgrads page: '2027年度新卒採用のエントリー受付は終了しました'. Nomura: 'エントリー受付終了' 2026-02-26.
Read-only access: Not applicable for 2027卒; watch for 秋 追加募集 notices via their pages or 外資就活/ONE CAREER deadline lists.
Notes: Recruit 新卒 site is under www.recruit.co.jp/employment/students/ (recruit-saiyo.jp does not resolve).
Src: https://www.recruit.co.jp/employment/students/
### Companies not verified in this pass: Woven by Toyota, Panasonic, DENSO, NTT DATA, McKinsey Japan, BCG Japan [medium]
Woven: careers page is JS-rendered ('No matching roles found' at fetch), internship page /en/careers/internship/, ATS unknown (Greenhouse tokens guessed all 404). Panasonic recruit.jpn.panasonic.com returned 503 twice; DENSO careers.denso.com returned 403; NTT DATA nttdata-recruit.com exposes no MyPage link on the top page; McKinsey pages timed out; BCG careers.bcg.com runs on Phenom CareerConnect (careers.bcg.com/global/en/search-results).
Read-only access: Unknown/unverified; default to ingesting their emails by company domain (woven.toyota, jp.panasonic.com, denso.com, nttdata.com, mckinsey.com, bcg.com).
Notes: Re-run these fetches from a browser context; the 403/503s were bot-protection, not dead sites.
Src: https://woven.toyota/en/careers/
### Competitor/reference: 就活管理アプリ ecosystem [medium]
iOS '就活管理 - マイページ管理・選考状況管理アプリ' (Takuma Matsuo, free, v1.7.1): stores MyPage URL/ID/PW, 選考状況 filters, one-tap copy — no reminders, calendar or CSV. iOS '就活管理 : 選考プロセスと企業情報を一括管理' (Rei Ootomo, v2.0.2 2025-03-25, 3000+ users): local-only, sorts by 予定日. 'Jobhun' (kanban 選考フェーズ). Templates: Notion databases, Googleスプレッドシート for マイページ管理 (外資就活's 27卒 recommendation), unistyle 企業管理シート. Generic: Googleカレンダー, TimeTree, ジョルテ, Lifebear, Todoist, Microsoft To Do, Evernote. Official aggregator: i-web CONNECT (i-web tenants only). Lognavi (株式会社アスパーク) is a scout/AI面接/セミナー予約 app, not a tracker.
Read-only access: None of them ingest Gmail or Calendar; all are manual entry with no export or API. Reference only.
Notes: JobPilot's read-only Gmail + Calendar ingestion, sender-domain → company mapping, and deadline extraction from '【…】' subject lines are absent from every existing tool found.
Src: https://jws-japan.or.jp/whitecareer/blog/5632

## Concrete details
  - Gmail sender allowlist (verified): sys2027@job.mynavi.jp, info-job@miws.mynavi.jp, mcbox.user@mcbox.mynavi.jp, job-s27@mynavi.jp, job-h27@mynavi.jp (マイナビ2027); info@gaishishukatsu.com (外資就活); info@offerbox.jp (OfferBox); @career-tasu.jp and @career-tasu.co.jp (キャリタス); careers@sakana.ai (Sakana AI).
  - Gmail domain-level filters (sender not individually verified): rikunabi.com, recruit.co.jp, indeedemail.com (リクナビ/Indeed scout alias); onecareer.jp; unistyleinc.com; labbase.jp; goodfind.jp; wantedly.com; br-campus.jp; openwork.jp; paiza.jp; supporterz.jp; linkedin.com; snar.jp; i-web.jpn.com; axol.jp; e2r.jp; myworkday.com / myworkdayjobs.com; workable.com; herp.careers; talentio.com; mhlw.go.jp.
  - Subject-line patterns seen in official docs: '【ONE CAREER】新規登録確認メール' (prefix 【ONE CAREER】), '【OfferBox】 ユーザー仮登録が完了しました' (prefix 【OfferBox】). Japanese ATS mail generally uses '【会社名】' or '【重要】' prefixes — parse the bracketed prefix as company/system hint.
  - MyPage URL patterns to detect in email bodies: https://{tenant}.snar.jp/... (SONAR ATS; e.g. toyota-saiyo, dena, cyberagent, sonynetwork); https://{company}.i-web.jpn.com/{yyyy}/ and https://mypage.{id}.i-web.jpn.com/ (i-web); https://job.axol.jp/bx/s/{company}_{yy}/mypage/login and https://axol.jp/zw/s/{company}_{yy}/mypage/login (マイナビ アクセスオンライン); https://www.e2r.jp/ja/{company}{yyyy}/ (e2R); https://mypage.smbc-recruitment.jp/{yyyy}/; https://www.mypage.bk.mufg.jp/mufgbank{yyyy}/; https://open.talentio.com/r/1/c/{company}/homes/{id} (TalentIO); https://herp.careers/v1/{company}/{jobid} (HERP); https://hrmos.co/pages/{company}/jobs/{id} (HRMOS); https://apply.workable.com/{account}/ and https://apply.workable.com/j/{SHORTCODE} (Workable); https://{tenant}.wd{N}.myworkdayjobs.com/... (Workday).
  - Public JSON endpoints usable without auth (GET): Greenhouse https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true ; Lever https://api.lever.co/v0/postings/{site}?mode=json ; Workable https://apply.workable.com/api/v1/widget/accounts/{account} (verified: mercari → 324 jobs incl. '28卒対象' / 'Internship' / 'AI Research Scientist, R4D'). Workday JSON requires POST to /wday/cxs/{tenant}/{site}/jobs (read query; unverified here).
  - Explicit anti-scraping clauses (quote-level): マイナビ sitepolicy '当サイトに掲載される情報を、ロボットや巡回プログラム等を用いて機械的に取得する行為'; Wantedly 利用規約 '自動化されたシステム（ボット、スクレイパー、スパイダー、AI またはエージェント型 AI 等を含みます）...クロール、スクレイピング、データマイニング等を行う行為'; ビズリーチ・キャンパス 第12条2項 '（クローリングを含みますが、それに限りません）' and 第16条2項7号キ⑩ '自動巡回プログラムを用いる等'; OpenWork 第11条1項12号 '断続的な機械的なアクセス行為、コンテンツを一括ダウンロードする行為'; LinkedIn UA 8.2(2) and 8.2(13).
  - Private-use-only / catch-all clauses (no literal 'scraping' word but effectively prohibitive for bulk copying): 外資就活 第10条 '会員の個人としての私的利用以外の利用'; paiza 第24条5項 '私的利用の範囲を超えて利用する行為'; ONE CAREER 第14条 items 1, 16, 28, 29; リクナビ会員規約 無断複製 + 'その他当社が不適切と判断する行為' (Recruit-ID-wide suspension risk per リクルートID規約); マイナビ2027 利用規約 第5条 '業務の運営を妨げる行為'; Goodfind 'Goodfindの運営を妨げる行為'; HelloWork 第15条 'システム又はセキュリティに支障又は危険を及ぼす可能性のある一切の行為'.
  - Late-cycle 2027卒 windows verified today: Rakuten 'Applications for October 2027 Entry are now open' (2026-09-01); Mercari 通年採用 via Workable (titles now labelled 28卒対象 but 通年); Sakana AI internship / visiting researcher / Applied Research Engineer via careers@sakana.ai; Tier IV '5002_学生データエンジニア' on HERP; Toyota, DeNA, Hitachi, SMBC, MUFG still expose 2027 MyPage logins. Closed: Recruit (2026-04-01), LINEヤフー, Nomura (2026-02-26). PFN ran 第1期 (2025-11-04) and 第2期 (2025-12-01) for 2027入社.
  - Account lifecycle: OfferBox locked 2025卒 accounts on 2025-10-01, so expect 2027卒 lockout ~2027-10-01; ONE CAREER and Goodfind push graduates to '卒業生アカウント' to stop mail. Ingest and archive navi-site mail before those cutoffs.
  - Notification cadence facts: Wantedly unanswered-scout reminder every Friday ~15:00 (mail + push); Goodfind seminar cancel deadline = 2 days before; マイナビ My CareerBox sends 締切リマインド from mcbox.user@mcbox.mynavi.jp; キャリタス mirrors mail in メッセージBOX→「キャリタスより」; マイナビ mirrors in 受信箱/お返事箱.
  - Existing 就活管理 apps found: '就活管理 - マイページ管理・選考状況管理アプリ' (iOS id6450649498, Takuma Matsuo), '就活管理 : 選考プロセスと企業情報を一括管理' (iOS id1629725427, Rei Ootomo), Jobhun, Notion/Google Sheets templates, unistyle 企業管理シート, i-web CONNECT (official, i-web tenants only). None ingest email or calendar; none export.

## Recommendation
Build ingestion in three tiers. Tier 1 (default, zero ToS risk): Gmail read-only with a sender-domain → platform/company classifier seeded from the verified addresses above (mynavi.jp family, gaishishukatsu.com, offerbox.jp, career-tasu.jp, sakana.ai) and domain-level rules for the rest; extract 締切/日時 from subject prefixes like 【ONE CAREER】/【OfferBox】/【会社名】 and from MyPage URL patterns (*.snar.jp, *.i-web.jpn.com, job.axol.jp, www.e2r.jp/ja/*, apply.workable.com/j/*, herp.careers/v1/*, open.talentio.com/r/1/c/*, *.myworkdayjobs.com). Tier 2 (public JSON, GET only): poll Greenhouse boards-api, Lever postings, and Workable widget API for the user's watchlist (Mercari and SmartNews on Workable are verified; discover Greenhouse/Lever tokens from each employer's careers HTML rather than guessing), filtering titles on 新卒/卒対象/New Grad/Intern/Research. Decide explicitly whether a Workday cxs POST search counts as 'writing' under the hard constraint; if not allowed, rely on Workday application emails. Tier 3 (manual): CSV/paste import for navi-site MyPage state, LinkedIn's data export, and Sakana AI-style Google-Form applications. Do NOT scrape マイナビ, リクナビ, Wantedly, Bizreach Campus, OpenWork, LinkedIn or any authenticated MyPage — every one has an explicit or catch-all prohibition and Recruit ties violations to the whole リクルートID. Late-cycle (Sept 2026) examples of channels still open to a 27卒 AI/ML candidate: Rakuten Oct-2027 intake, Mercari 通年 (Workable), Sakana AI intern/visiting-researcher, Tier IV HERP, PFN TalentIO (check for a late window), LabBase scouts and LabBase SUMMIT 10/3, plus ONE CAREER/外資就活 秋採用 deadline mail. Position JobPilot against the existing 就活管理 apps as the only tool that derives status/deadlines from email and calendar instead of manual entry.

## Open questions
  - Exact sender addresses for リクナビ2027 (help.job.rikunabi.com articles 000025607/000025977 are JS-rendered and returned 503), ONE CAREER (support.onecareer.jp 403), Wantedly, Bizreach Campus, LabBase, Goodfind, unistyle, paiza, サポーターズ, OpenWork — confirm from real message headers in the user's Gmail.
  - Sender domains used by the ATS layer for MyPage notifications: SONAR (snar.jp vs company domain), i-web (i-web.jpn.com / i-web.jp vs company domain), axol (axol.jp vs mynavi.jp), e2R, TalentIO, HERP — verify from headers; Humanage publishes no whitelist page.
  - Does a Workday /wday/cxs/{tenant}/{site}/jobs POST search violate the 'never posts' constraint? It writes nothing but is an HTTP POST; needs a product decision. Endpoint itself was not verified in this session (shell probes were denied).
  - Woven by Toyota's job-board vendor and token (Greenhouse guesses wovenbytoyota / woven-by-toyota / wovenplanet / woven all 404; careers page is client-rendered). Also Panasonic (503), DENSO (403), NTT DATA MyPage domain, McKinsey Japan (timeouts) — re-fetch from a browser.
  - Sony Group 新卒 MyPage domain behind www.recruit.sony.co.jp/2027/ ('業務委託先ページ') — not exposed on the landing or inquiry pages.
  - Whether Rakuten's new-grad application runs on Workday (rakuten.careers did not resolve; corporate page hides the platform) and whether the October 2027 intake accepts 2027年3月卒 candidates.
  - LabBase student terms (material.labbase.jp/pdf_contents/compass/terms_student_5_2.pdf) could not be text-extracted (no PDF renderer) — read for any explicit bot clause.
  - キャリタス就活2027 利用規約 scraping language (2027 help/terms pages 404'd; only 2021 help pages were readable).
  - Whether Mercari's 通年採用 roles labelled '28卒対象' will accept a 2027卒 (they specify '2028年4月以降に入社が可能な学生'); and whether PFN has a 第3期 / 通年 window for 2027入社 after 第2期 (2025-12-01).
  - LinkedIn data-export contents (job applications CSV) and exact alert sender addresses were stated from knowledge, not re-verified against a LinkedIn help page in this session.
  - 新卒応援ハローワーク official page returned 404 at the MHLW URL tried; eligibility ('卒業後3年以内') and office count are knowledge-based — confirm on mhlw.go.jp.
  - Existing-app competitor list came from one listicle (jws-japan.or.jp) and two App Store pages; Android-only 就活管理 apps and Notion template marketplaces were not surveyed.

## Sources
- マイナビ2027 Q&A メール・メッセージ (sender addresses): https://job.mynavi.jp/conts/2027/kaiin/message.html
- マイナビ サイトポリシー (機械的取得の禁止): https://job.mynavi.jp/sitepolicy/index.html
- マイナビ2027 利用規約: https://job.mynavi.jp/conts/2027/kiyaku/
- リクナビ会員規約: https://cdn.p.recruit.co.jp/terms/ngr-t-1001/index.html
- リクルートID規約: https://cdn.p.recruit.co.jp/terms/cmm-t-1022/index.html
- リクナビ help: リクナビからのメールが届かない: https://help.job.rikunabi.com/rn2/s/article/000025607
- ONE CAREER 利用規約 (第14条): https://www.onecareer.jp/infos/terms
- ONE CAREER support: メールの配信を停止したいです: https://support.onecareer.jp/hc/ja/articles/4403090942489
- 外資就活ドットコム ヘルプ (info@gaishishukatsu.com): https://gaishishukatsu.com/faq
- 外資就活ドットコム 利用規約: https://gaishishukatsu.com/terms
- unistyle 利用規約: https://unistyleinc.com/rule
- キャリタス就活 ヘルプ（メールについて）: https://job.career-tasu.jp/2021/help_index/mail.html
- LabBase就職 (student LP, terms PDF link): https://compass.labbase.jp/
- LabBase就職 help: メール配信を停止したい: https://labbasestudent.zendesk.com/hc/ja/articles/9898960203151
- Goodfind 利用規約: https://www.goodfind.jp/terms
- Goodfind よくある質問: https://www.goodfind.jp/faq
- OfferBox help: ユーザー登録の確認メールが届かない (info@offerbox.jp): https://offerboxhelp.zendesk.com/hc/ja/articles/360052681973
- OfferBox help: 通知設定とは: https://offerboxhelp.zendesk.com/hc/ja/articles/22228492564889
- Wantedly 利用規約 (scraping / AI agent prohibition): https://service-terms.wantedly.com/user_terms/ja_JP
- Wantedly help: 未返信スカウトのリマインド通知: https://help.wantedly.com/hc/ja/articles/25219154715161
- ビズリーチ・キャンパス 利用規約: https://br-campus.jp/staticpages/terms
- ビズリーチ・キャンパス top: https://br-campus.jp/
- OpenWork 利用規約 (/rule.php): https://www.openwork.jp/rule.php
- paiza 利用規約: https://paiza.jp/guide/kiyaku
- paiza新卒: https://paiza.jp/student
- サポーターズ corporate site: https://corp.supporterz.jp/
- TokyoDev jobs: https://www.tokyodev.com/jobs
- Japan Dev: https://japan-dev.com/
- LinkedIn User Agreement (8.2 Don'ts): https://www.linkedin.com/legal/user-agreement
- ハローワークインターネットサービス 利用規約: https://www.hellowork.mhlw.go.jp/info/terms.html
- ハローワークインターネットサービス top (求人検索 URL): https://www.hellowork.mhlw.go.jp/
- Greenhouse Job Board API docs: https://docs.greenhouse.io/job-board.html
- Lever Postings API (GitHub): https://github.com/lever/postings-api
- Workable widget API — Mercari (verified JSON): https://apply.workable.com/api/v1/widget/accounts/mercari
- Mercari 新卒採用 (通年採用, Workable): https://careers.mercari.com/new-graduates/
- SmartNews careers (Workable): https://careers.smartnews.com/en/
- Accenture Japan job search (Workday wd103): https://www.accenture.com/jp-ja/careers/jobsearch
- BCG careers (Phenom): https://careers.bcg.com/
- Tier IV on HERP Careers: https://herp.careers/v1/tier4
- HRMOS careers page (Visional): https://hrmos.co/pages/visional/jobs
- Preferred Networks careers (TalentIO links, 2027 schedule): https://www.preferred.jp/ja/careers/
- Sakana AI careers: https://sakana.ai/careers/
- Toyota 新卒採用 (toyota-saiyo.snar.jp): https://recruit.toyota/
- DeNA 新卒採用 (dena.snar.jp): https://student.dena.com/
- CyberAgent careers (cyberagent.snar.jp, hrmos.co/pages/cyberagent-group): https://www.cyberagent.co.jp/careers/
- Sony 新卒採用 2027 common site: https://www.recruit.sony.co.jp/2027/
- Sony recruit top: https://www.sony.co.jp/recruit/
- Hitachi recruit (e2r.jp MyPage): https://www.hitachi.com/ja-jp/recruit/
- Hitachi 2027 MyPage login (e2R): https://www.e2r.jp/ja/hitachi2027/
- Nomura recruit (axol MyPages, 2027 closed): https://www.nomura-recruit.jp/
- Nomura 2027 MyPage login (job.axol.jp): https://job.axol.jp/bx/s/nomura_27/mypage/login
- SMBC 新卒採用 (mypage.smbc-recruitment.jp): https://www.smbc-freshers.com/
- MUFG Bank 新卒採用 (www.mypage.bk.mufg.jp): https://www.saiyo.bk.mufg.jp/
- Rakuten new graduate hiring (Oct 2027 entry open): https://global.rakuten.com/corp/careers/graduates/
- リクルート 新卒採用 (2027 entry closed): https://www.recruit.co.jp/employment/students/
- LINEヤフー 新卒採用 (2027 entry closed): https://www.lycorp.co.jp/ja/recruit/newgrads/
- Woven by Toyota careers: https://woven.toyota/en/careers/
- SONAR ATS (Thinkings): https://sonar-ats.jp/
- i-web ATS (Humanage): https://i-web-ats.humanage.co.jp/
- i-web CONNECT app: https://apps.apple.com/jp/app/i-web-connect/id1499299153
- 就活管理アプリおすすめ13選 (competitor list): https://jws-japan.or.jp/whitecareer/blog/5632
- App Store: 就活管理 - マイページ管理・選考状況管理アプリ: https://apps.apple.com/jp/app/id6450649498
- App Store: 就活管理 : 選考プロセスと企業情報を一括管理: https://apps.apple.com/jp/app/id1629725427
- 外資就活: 27卒 トップ就活生が使うべきアプリ7選: https://gaishishukatsu.com/archives/203124
- Lognavi: https://lognavi.com/
