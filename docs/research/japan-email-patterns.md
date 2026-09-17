# 日本招聘邮件与 ATS 发件模式（用于 Gmail 解析）

> **AI 调研附录**（生成于 2026-09-16，英文）。内容由并行调研 agent 对照官方页面整理，verified/unverified 标注以原文为准；实现前需再次核对。相关更正见 japan-critique.md 与 proposal-judgments.md。

# Japanese recruiting-email and ATS patterns for read-only Gmail parsing (2027卒 / 秋採用 context, JobPilot)

## Summary
Japan-side 新卒/中途 recruiting mail comes from three sender classes: (1) platform relays that carry MANY companies under one domain (mynavi.jp family, mail.rikunabi.com, offerbox.jp, wantedly.com, linkedin.com) where the sender only identifies the platform and the company must be parsed from subject/body; (2) per-company ATS senders whose address encodes the company (sonar: <company>@snar.jp; HRMOS採用: @<slug>.hrmos.co; Workday: <tenant>@myworkday.com; i-web: usually the company's own domain, e.g. telpdrecruit@tel.com); (3) fixed vendor no-reply addresses (HERP @candidacy.herp.cloud, Greenhouse no-reply@us.greenhouse-mail.io / no-reply@greenhouse.io, Lever no-reply@hire.lever.co, Ashby noreply@ashbyhq.com, SmartRecruiters notifications@smartrecruiters.com, Talentio @talentio.com, ジョブカン @ats.jobcan.ne.jp, SPI noreply_tc@arorua.net, Calendly notifications@calendly.com, Google Calendar calendar-notification@google.com, Zoom no-reply@zoom.us). Stage is best detected by Japanese phrase lists (応募受付 → 適性検査 → 日程調整 → 面接のご案内 → 選考結果 → 内々定/内定 → 内定承諾書 / お祈り / 辞退受付) applied after NFKC normalization and HTML-to-text conversion, with an LLM fallback only for 「選考結果のご連絡」-type ambiguous mails and free-form recruiter mail. A large share of 新卒 stage information is NOT in the mail body at all: i-web/sonar マイページ mails say 「マイページをご確認ください」, and many 新卒 teams move to LINE公式アカウント after エントリー, so the app needs a PORTAL_UPDATE stage and a manual-paste path. Google Calendar read-only plus .ics parts (DTSTART;TZID=Asia/Tokyo, LOCATION/X-GOOGLE-CONFERENCE) are more reliable than regexing dates from prose.

## Items
### i-web (株式会社ヒューマネージ) 新卒マイページ ATS [high]
Largest-share 新卒 ATS in Japan; hosts per-company マイページ used by Canon, Tokyo Electron, GMO, Capcom, NPA etc. Mail is mostly a notification pointing back to the マイページ.
Read-only access: Email notifications only. Sender is normally the COMPANY's own address configured in i-web (verified: TEL mypage states mails come from telpdrecruit@tel.com); some deployments reportedly send from i-webs.jp (unverified). Body/URL markers: https://mypage.30NN.i-webs.jp/<company><yyyy>/ (e.g. mypage.3010.i-webs.jp/tel2027/, mypage.3030.i-webs.jp/gmo2027/) and https://*.i-web.jpn.com/<company><yyyy>/ (e.g. newgraduate.i-web.jpn.com/canon2027/).
Notes: Detection rule: body contains regex https?://[a-z0-9.-]*i-webs?\.(jp|jpn\.com)/([a-z0-9]+?)(20\d{2})/ -> platform=i-web, company_slug=$2, cohort=$3. Typical subjects: 【<社名>】マイページ登録完了のお知らせ / エントリーシート受付完了 / 【重要】選考結果のご連絡 / 面接日程のご案内 / マイページに新着メッセージがあります. Pitfall: actual 選考結果 text is often only inside the マイページ (mail just says 「マイページよりご確認ください」) -> stage=PORTAL_UPDATE, action_required=true. Same vendor runs TG-WEB, so 適性検査 invitations from i-web companies often carry c-personal.com / e-gitest.com URLs.
Src: https://i-web-ats.humanage.co.jp/
### Company-hosted マイページ / 採用サイト notification mails (generic, non-i-web) [high]
Many large JP firms and 官公庁 use sonar, i-web, or in-house マイページ; mails are stubs like 「マイページに新着のお知らせがあります」.
Read-only access: Email stub only; content lives behind login. App must not log in or scrape (ToS + write risk). Provide a manual paste / screenshot-OCR path.
Notes: Classify as PORTAL_UPDATE when body matches 「マイページ(をご確認|にログイン|より)」「新着(メッセージ|のお知らせ)」「詳細はマイページ」 and no explicit stage phrase. Keep the マイページ URL as the action link. Also common: 「エントリー期間」「締切」 lines -> deadline extraction.
Src: https://i-web-ats.humanage.co.jp/about/
### HRMOS採用 (株式会社ビズリーチ) incl. 新卒エディション [high]
Mid-career + 新卒 ATS; job pages at hrmos.co/pages/<slug>/jobs/<id>. Mail relayed through HRMOS so replies land in the ATS.
Read-only access: Email. Verified sender pattern: @<company-slug>.hrmos.co (company pages tell applicants to allow @referral-kashiwabara.hrmos.co, @congre.hrmos.co, @kurashicom.hrmos.co). Company slug in From domain.
Notes: Rule: From domain matches ^([a-z0-9-]+)\.hrmos\.co$ -> platform=HRMOS, company_slug=$1 (map slug to name via display name or hrmos.co/pages/<slug>). Bizreach itself warned (2025-07) about spoofed HRMOS/ビズリーチ mails; check Gmail Authentication-Results (SPF/DKIM pass) before trusting. Job URL regex https://hrmos\.co/pages/([^/]+)/jobs/(\d+).
Src: https://hrmos.co/pages/referral-kashiwabara
### HERP Hire (株式会社HERP) [high]
Startup-heavy 中途/新卒 ATS (スクラム採用); many AI/SaaS startups in Tokyo use it. Job pages herp.careers/v1/<company>/<id>.
Read-only access: Email. Official FAQ: candidate mails are sent from the @candidacy.herp.cloud domain; replies to that address go back into HERP.
Notes: Rule: From domain == candidacy.herp.cloud -> platform=HERP; company from From display name / signature / thread's application-confirmation (herp.careers URL slug). Local-part is a token, never a company id. Subjects follow company-written templates (Japanese startup style: 「【<社名>】カジュアル面談のご案内」「選考のご案内」).
Src: https://guide.herp.cloud/faq/184ab645335243f5903d2bcb3b46ece3
### sonar ATS (Thinkings株式会社, now 'sonar ATS by HRMOS') [high]
Major 新卒 ATS (DeNA, 稲畑産業, ウチダエスコ, many 官公庁); マイページ at <company>.snar.jp; manager UI manager.snar.jp.
Read-only access: Email. Send-only address pattern <company>@snar.jp (verified on company sites: inabata@snar.jp, dena@snar.jp). Replies do NOT reach the company.
Notes: Rule: From matches ^([a-z0-9-]+)@snar\.jp$ -> company_slug=$1. Body URL regex https://([a-z0-9-]+)\.snar\.jp/ also yields slug. sonar mails often embed full 面接 details (日時/場所/持ち物) and 予約 links; also used for 説明会予約完了 mails. Known deliverability issue with iCloud/大学 domains.
Src: https://student.dena.com/contact/
### Talentio (株式会社タレンティオ) [medium]
Startup/中途 ATS; career pages open.talentio.com/r/1/c/<company>/pages/<id>; API at developers.talentio.com; mail via SendGrid.
Read-only access: Email. Company pages instruct applicants to allow the @talentio.com domain; one page references em.talentio.com (SendGrid subdomain). Verify exact From from real headers.
Notes: Rule: From domain endswith talentio.com -> platform=Talentio; company from URL slug regex https://open\.talentio\.com/r/1/c/([^/]+)/ or display name. Click-tracked links may be ct.sendgrid.net wrappers; do not auto-resolve (would register an 'open/click').
Src: https://internshipguide.jp/interns/internDetail/20002
### ジョブカン採用管理 (株式会社DONUTS) [low]
SMB-oriented ATS; applicant forms/mail via ats.jobcan.ne.jp.
Read-only access: Email. Support/system address support@ats.jobcan.ne.jp confirmed; companies may instead configure their own From via 「送信元メールアドレス設定」 (help article 225122848). Exact default no-reply local-part unverified.
Notes: Rule: From domain endswith ats.jobcan.ne.jp -> platform=Jobcan; otherwise detect via body URL ats.jobcan.ne.jp. Company from display name/signature.
Src: https://jobcan-ats.zendesk.com/hc/ja/articles/225122848
### OfferBox (株式会社i-plug) 逆求人 [medium]
Student profile -> company offer platform; offers/messages still arrive in 秋採用 for 27卒.
Read-only access: Email notifications. Official help: mails come from the @offerbox.jp domain. Message content is in-app; mail is a notification (often with company name in subject/body).
Notes: One sender, many companies -> company must be parsed from subject/body (typical, unverified template: 「【OfferBox】<社名>からオファーが届きました」「<社名>からメッセージが届いています」). Treat 'オファー' as LEAD, not APPLIED. Filter newsletter/PR mails (List-Unsubscribe header + 「おすすめ」「イベント」).
Src: https://offerboxhelp.zendesk.com/hc/ja/articles/360052681973
### Wantedly [high]
Startup hiring SNS (スカウト / 話を聞きに行きたい); heavy use by Tokyo AI startups for casual 面談.
Read-only access: Email notifications from the @wantedly.com domain (official help; e.g. customer-relations@wantedly.com for system notices). Message bodies are truncated; full thread is in-app.
Notes: One sender, many companies -> parse company from subject/body (typical: 「[Wantedly] <社名>の<氏名>さんからメッセージ/スカウトが届きました」). Stage = LEAD or INTERVIEW_SCHEDULING (「話を聞きに行きたい」承諾 -> 面談日程). Meeting links are usually posted in-app -> meeting_link_pending=true with action 'check Wantedly'.
Src: https://help.wantedly.com/hc/ja/articles/50327552221209
### マイナビ2027 (株式会社マイナビ) relay / notification mail [high]
Largest 新卒 navi site; companies message students via マイナビ 'お返事箱'/DM; マイナビ also forwards them by email.
Read-only access: Email. Official FAQ lists senders: job-s27@mynavi.jp, job-h27@mynavi.jp, sys2027@job.mynavi.jp, info-job@miws.mynavi.jp, mcbox.user@mcbox.mynavi.jp; event mails from noreply@job-gift.mynavi.jp. Domain to allow: mynavi.jp. Local parts are cohort-coded (s27/h27, sys2027) -> next cohort becomes s28/sys2028.
Notes: One sender relays MANY companies -> company from subject/body; relay subjects observed: 「…よりメッセージが届いています」「お返事が届いています」. Message categories: お返事 (company replies to applicants), お知らせ, スカウト, マイナビ編集部から. Rule: From domain endswith mynavi.jp -> platform=Mynavi; if subject/body contains 「セミナー」「合同説明会」「メールマガジン」 -> EVENT/NEWSLETTER low priority; if 「お返事」 and body has 日時/選考 -> parse as company mail. Many companies embed the same 面接案内 text they would send directly, so run the full phrase classifier on the relayed body.
Src: https://job.mynavi.jp/conts/2027/kaiin/message.html
### リクナビ2027 / リクナビNEXT (株式会社リクルート) notification mail [medium]
Second major 新卒 navi (リクナビ2027) and 中途 site (NEXT). Company mails arrive via リクナビ メッセージBOX + email.
Read-only access: Email. Official help (article 000030663) tells students to allow @mail.rikunabi.com and @indeed.com (Rikunabi is Indeed-integrated; scout replies use @indeedemail.com aliases). NEXT: center@next.rikunabi.com, noreply@next.rikunabi.com. Help site is Salesforce-rendered (not fetchable server-side).
Notes: Rule: From domain endswith rikunabi.com or indeed.com/indeedemail.com -> platform=Rikunabi/Indeed; company from body. Some companies list their own From on the リクナビ page (e.g. s1532000@facetoface.ne.jp) -> unknown-domain company mail; classify by phrases.
Src: https://help.job.rikunabi.com/s/article/000030663
### LINE公式アカウント (recruiting via LINE) - COVERAGE GAP [high]
Many 新卒 teams (and agencies) move 日程調整/リマインド/選考結果 to a company LINE公式アカウント after エントリー; no email is generated.
Read-only access: none (LINE has no read-only inbox API for consumer accounts; scraping LINE violates ToS). Only signal in Gmail: onboarding mails saying 「LINE公式アカウントを友だち追加してください」「今後のご連絡はLINEにて」.
Notes: Detect the handoff phrase and set channel=LINE on that company so the app expects silence in Gmail and prompts the user to paste LINE text (manual input path). Do not attempt to read LINE.
Src: https://job.mynavi.jp/conts/2027/kaiin/message.html
### Workday Recruiting [high]
Enterprise ATS used by many 外資 and large JP firms (Sony, Rakuten, Hitachi units, banks, consulting).
Read-only access: Email from <tenant>@myworkday.com (verified examples: uw@myworkday.com, parexel@myworkday.com, nature@myworkday.com); display name usually 'My Workday <Company>' or company name; RTX also cites @workday.com. Job URLs <company>.wdN.myworkdayjobs.com (wd1/wd3/wd5/wd103).
Notes: Rule: From matches ^([a-z0-9]+)@myworkday\.com$ -> company_tenant=$1. Subjects: 'Thank you for applying' / 「ご応募ありがとうございます」, 'Update on your application', 'Request for Additional Information', 'Interview Invitation'; Workday rejection bodies often 'we have decided to move forward with other candidates' with no 残念. Candidate home URL regex https://([a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com/.
Src: https://jobs.parexel.com/en/faqs
### Greenhouse Recruiting [high]
Common ATS at US/UK tech firms with Tokyo offices and at some JP startups.
Read-only access: Email. Official list of automated senders: no-reply@greenhouse.io, no-reply@us.greenhouse-mail.io, no-reply@eu.greenhouse-mail.io, no-reply@anz.greenhouse.io; companies may verify a domain and send as no-reply@<company>.com. Reply-To is often a hashed @us.greenhouse-mail.io address.
Notes: Rule: From/Reply-To domain in {greenhouse.io, us.greenhouse-mail.io, eu.greenhouse-mail.io, anz.greenhouse.io} -> platform=Greenhouse; company from display name or URL regex https://(boards|job-boards)\.greenhouse\.io/([^/]+)/jobs/(\d+). Self-schedule links app.greenhouse.io/scheduling/... -> INTERVIEW_SCHEDULING. Subjects: 'Thank you for your application to <Company>', 'Your application to <Company>', 'Interview with <Company>'.
Src: https://support.greenhouse.io/hc/en-us/articles/17675865619099-Greenhouse-Recruiting-no-reply-email-addresses
### Lever [medium]
ATS common at mid-size tech / AI companies.
Read-only access: Email from no-reply@hire.lever.co (cited in Lever help 'Managing failed emails' and third-party guides); Reply-To tokens @hire.lever.co. Recruiter-composed Lever mails may come from the recruiter's real corporate address (mailbox integration). Job URLs jobs.lever.co/<company>/<uuid>.
Notes: Rule: domain hire.lever.co -> platform=Lever; company from display name or https://jobs\.lever\.co/([^/]+)/. Lever's help center is a JS app (not fetchable) - official page not captured; confirm from a real header.
Src: https://www.loopcv.pro/guides/lever-application-status/
### SmartRecruiters [medium]
Enterprise ATS (e.g. Bosch, Visa, LLNL, some 外資 in Japan).
Read-only access: Email from notifications@smartrecruiters.com (LLNL fraud notice, LinkedIn post); vendor states it contacts candidates only from the @smartrecruiters.com domain. Job URLs jobs.smartrecruiters.com/<Company>/<id>, careers.smartrecruiters.com.
Notes: Rule: domain smartrecruiters.com -> platform=SmartRecruiters; company from display name / URL slug. Subjects 'Application Received', 'Your application at <Company>'.
Src: https://www.smartrecruiterscareers.com/recruitment-fraud-information
### Ashby [high]
ATS used by many frontier-AI labs and startups (high hit rate for Applied Research / FDE roles).
Read-only access: Email. Ashby docs: default sender noreply@ashbyhq.com (third parties also write no-reply@ashbyhq.com); companies can switch to a custom domain via 'Shared Email Aliases'. Job URLs jobs.ashbyhq.com/<company>/<uuid>; scheduling links app.ashbyhq.com/... .
Notes: Rule: domain ashbyhq.com -> platform=Ashby; company from display name or https://jobs\.ashbyhq\.com/([^/]+)/. Ashby self-schedule mails = INTERVIEW_SCHEDULING; confirmations include ICS + Google Meet/Zoom link.
Src: https://docs.ashbyhq.com/email-domain-setup
### HireVue (on-demand video / coding interviews) [medium]
Asynchronous video interview + coding assessments; used by 外資 (RTX, Shell, banks) and some JP 大手 (録画面接).
Read-only access: Email from the @hirevue.com domain (RTX recruitment-fraud page lists @hirevue.com as legitimate); exact local-part (commonly noreply@hirevue.com) not verified. Invitation URLs app.hirevue.com/interviews/... or <company>.hirevue.com.
Notes: Treat as stage=TEST_INVITE (video), not a live meeting: extract 'complete by <date>' / 「〇月〇日までに受験」 as deadline, meeting_url=null, link_pending=false. Reminder mails 'Your interview is due soon'.
Src: https://careers.rtx.com/global/en/recruitment-fraud
### Calendly booking confirmations [high]
Scheduling tool used by many recruiters (esp. startups/外資) for カジュアル面談 and interviews.
Read-only access: Email from notifications@calendly.com (official help); Reply-To = host's login email (gives recruiter/company domain). Also generates a calendar invite from the host's connected calendar (Google -> calendar-notification@google.com).
Notes: Subject patterns: 'Invitation: <Event> with <Host> @ <date/time>' / 'New Event: ...' / 'Rescheduled:' / 'Canceled:'. Body fields 'Event Name', 'Date & Time' (in invitee tz, label e.g. 'Japan Standard Time'), 'Location: This is a Zoom/Google Meet web conference. Join now <url>', 'Reschedule/Cancel' links calendly.com/reschedulings|cancellations/<uuid>. Prefer attached .ics. Company = Reply-To domain + event name.
Src: https://calendly.com/help/calendly-scheduling-notifications
### Google Calendar invitation mails (+ Google Meet) [high]
Interview invites sent as calendar events (Google Workspace companies, Ashby/Greenhouse/Calendly integrations).
Read-only access: Email from calendar-notification@google.com with text/calendar part (METHOD:REQUEST), plus Google Calendar API read-only for the same event (dedupe by iCalUID).
Notes: Subject templates: EN 'Invitation: <title> @ <Wed Sep 23, 2026 2pm - 3pm (JST)> (<your email>)', 'Updated invitation:', 'Canceled event:'; JA 「招待: <title> @ 2026年9月23日(水) 14:00 ～ 15:00 (JST) (<email>)」「更新された招待状:」「キャンセルされたイベント:」. Parse ICS: DTSTART;TZID=Asia/Tokyo, LOCATION, DESCRIPTION, X-GOOGLE-CONFERENCE; Meet regex https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}. Company from organizer domain (ORGANIZER:mailto:) not from Google.
Src: https://webapps.stackexchange.com/questions/60188/
### Zoom / Microsoft Teams meeting links inside recruiter mails [high]
Most JP interview links are pasted into the company's own 面接のご案内 mail rather than sent by Zoom/Microsoft.
Read-only access: Zoom system mails (registration/account) come from no-reply@zoom.us (Zoom support KB0060118); Teams invites come from the ORGANIZER's Exchange mailbox (company domain) with a text/calendar part - there is no Microsoft sender domain to key on.
Notes: URL regexes: Zoom https?://([a-z0-9-]+\.)?zoom\.(us|com)/(j|my|w)/\S+ plus 「ミーティングID[:：]\s*[\d ]{9,14}」「パスコード[:：]\s*\S+」; Teams https://teams\.microsoft\.com/l/meetup-join/\S+ or https://teams\.live\.com/meet/\S+ plus 'Microsoft Teams meeting' / 「Microsoft Teams 会議に参加」「会議 ID:」「パスコード:」; Webex https://[a-z0-9-]+\.webex\.com/\S+; Meet as above. Store passcodes encrypted; never log.
Src: https://support.zoom.com/hc/ja/article?id=zm_kb&sysparm_article=KB0060118
### SPI3 テストセンター / WEBテスティング (リクルートマネジメントソリューションズ) [high]
Most common 新卒 適性検査; test-center booking system mails and 自宅受検 URLs both on arorua.net.
Read-only access: Email from noreply_tc@arorua.net (Sapporo city SPI guide) / domain arorua.net (official FAQ). Mail types: テストセンターID取得, 受検予約完了 (date, time, venue map, mypage URL), 予約内容確認 (printable as 受検票).
Notes: Rule: domain arorua.net -> stage=TEST (SPI); if 「受検予約完了」 -> extract test datetime/venue as an appointment (type=TEST_SESSION, not interview). Company's own invitation mail usually precedes it with 「適性検査受検のご案内」 + arorua.net URL + 受検期限 -> TEST_INVITE with deadline. Note 「受検」(test) vs 「受験」 spelling both occur.
Src: https://www.spi.recruit.co.jp/testcenter/faq.html
### 玉手箱 / Web-CAB / GAB (日本SHL) [high]
Second most common 新卒 Web test (finance/consulting/IT); 玉手箱 and CAB share URLs.
Read-only access: Test invitation is normally sent by the COMPANY/ATS, not by SHL; SHL platform sender not verified. Identify by URL: web1/web2/web3.e-exams.jp, tsvs1-3.e-exams2.jp, nsvs1-2.e-exams4.jp.
Notes: Rule: body URL matches https?://[a-z0-9]+\.e-exams\d?\.jp/ -> stage=TEST_INVITE, test_vendor=SHL (cannot distinguish 玉手箱 vs CAB/GAB from URL). Extract 「受検期限」「ID」 (redact credentials).
Src: https://job.career-tasu.jp/guide/step/136/
### TG-WEB / C-TG-WEB (株式会社ヒューマネージ) [medium]
Third major 新卒 Web test; same vendor as i-web; test-center variant requires 会場予約.
Read-only access: Invitation mail usually from the company (often via i-web). Identify by URLs assessment.c-personal.com, assessment.e-gitest.com, www.e-assessment.jp. Exact platform sender unverified.
Notes: Rule: body URL contains c-personal.com | e-gitest.com | e-assessment.jp -> TEST_INVITE (TG-WEB); if 「会場の予約」「テストセンター」 + ヒューマネージ -> C-TG-WEB with a booking sub-step. Another test platform seen in results: compass-ing.com (unverified; leave as generic TEST).
Src: https://job.career-tasu.jp/guide/step/136/
### LinkedIn notification / InMail / Easy Apply mails [high]
Recruiter InMail, Easy Apply confirmations, job alerts; main channel for 外資 and AI-lab recruiters in Japan.
Read-only access: Email from @linkedin.com: messages-noreply@linkedin.com (InMail/messages), jobs-noreply@linkedin.com (Easy Apply 'Your application was sent to <Company>', 'viewed your application'), jobalerts-noreply@linkedin.com, jobs-listings@linkedin.com, notifications-noreply@linkedin.com, invitations@linkedin.com, marketing linkedin@e.linkedin.com. LinkedIn states authentic mails end in @linkedin.com.
Notes: One sender, many companies -> company from subject ('New message from <Name> at <Company>', 'Your application was sent to <Company>'). InMail bodies are truncated -> stage=LEAD, action 'reply on LinkedIn'. Easy Apply confirmation -> APPLIED. Job alerts / e.linkedin.com -> NEWSLETTER (ignore).
Src: https://clean.email/how-to-unsubscribe-from-emails/unsubscribe-from-linkedin-emails
### Direct company HR mailboxes and agencies (no ATS signature) [high]
Large share of 新卒 mail is sent by hand from saiyo@/recruit@/jinji@/shinsotsu@/careers@/hr@<company>.co.jp, or by agencies (@r-agent.com, doda/PERSOL, JAC, Robert Walters, Michael Page).
Read-only access: Email; company = sender domain (strip mail./mx. subdomains; map co.jp/com variants via alias table). Agencies are intermediaries: company name is in the body (「ご紹介企業：」「企業名：」), not the sender.
Notes: Local-part heuristics for recruiting mailbox: ^(saiyo|saiyou|recruit(ing)?|jinji|hr|shinsotsu|newgrad|careers?|talent|entry|info-recruit)\b. Signature regex for company: (株式会社|合同会社|有限会社|一般社団法人)?[^\s　]{1,30}(株式会社|Inc\.|Co\., ?Ltd\.|K\.K\.|G\.K\.|LLC|Corporation). Recruiter name/phone lines (「採用担当：」「TEL[:：]」「携帯」) are PII -> redact before LLM.
Src: https://hrmos.co/info/news/20250709-2/

## Concrete details
  - SENDER-DOMAIN TABLE (deterministic tier-1): candidacy.herp.cloud=HERP | *.hrmos.co (company slug)=HRMOS採用 | *@snar.jp (company local-part)=sonar ATS | talentio.com / em.talentio.com=Talentio | ats.jobcan.ne.jp=ジョブカン採用管理 | offerbox.jp=OfferBox | wantedly.com=Wantedly | mynavi.jp, job.mynavi.jp, miws.mynavi.jp, mcbox.mynavi.jp, job-gift.mynavi.jp=マイナビ (senders job-s27@, job-h27@, sys2027@job., info-job@miws., mcbox.user@mcbox., noreply@job-gift.) | mail.rikunabi.com, rikunabi.com, next.rikunabi.com, indeed.com, indeedemail.com=リクナビ/Indeed | *@myworkday.com (tenant local-part), workday.com=Workday | greenhouse.io, us.greenhouse-mail.io, eu.greenhouse-mail.io, anz.greenhouse.io=Greenhouse | hire.lever.co=Lever | smartrecruiters.com (notifications@)=SmartRecruiters | ashbyhq.com (noreply@)=Ashby | hirevue.com=HireVue | notifications@calendly.com=Calendly | calendar-notification@google.com=Google Calendar | no-reply@zoom.us=Zoom system | arorua.net (noreply_tc@)=SPI | *@linkedin.com (messages-noreply, jobs-noreply, jobalerts-noreply, jobs-listings, notifications-noreply, invitations, e.linkedin.com)=LinkedIn.
  - BODY-URL TABLE (tier-1b, used when From is a company or relay): i-webs.jp | i-web.jpn.com -> i-web; *.snar.jp -> sonar; hrmos.co/pages/<slug>/jobs -> HRMOS; herp.careers/v1/<co> -> HERP; open.talentio.com/r/1/c/<co> -> Talentio; boards.greenhouse.io/<co> | job-boards.greenhouse.io -> Greenhouse; jobs.lever.co/<co> -> Lever; jobs.ashbyhq.com/<co> -> Ashby; <co>.wdN.myworkdayjobs.com -> Workday; jobs.smartrecruiters.com/<Co> -> SmartRecruiters; arorua.net -> SPI; *.e-exams.jp | *.e-exams2.jp | *.e-exams4.jp -> 玉手箱/CAB/GAB; assessment.c-personal.com | assessment.e-gitest.com | e-assessment.jp -> TG-WEB; app.hirevue.com -> HireVue; hackerrank.com | codility.com | track.run | paiza.jp | coderbyte.com -> coding test.
  - STAGE=APPLIED (応募受付/エントリー完了): subject 「エントリー(受付)?完了」「エントリーありがとうございます」「ご応募ありがとうございます」「応募受付(のお知らせ|完了)」「エントリーシート(受付|提出)完了」「プレエントリー完了」「マイページ登録完了」 / 'Thank you for applying' 'Application received' 'We received your application' 'Your application was sent to'; body 「エントリーを受け付けました」「ご応募いただきありがとうございます」「応募を受理」「書類選考の上(、)?追ってご連絡」.
  - STAGE=SCREENING_RESULT (書類選考結果): subject 「書類選考(結果|通過)のご連絡」「ES選考結果」「エントリーシート選考結果」「一次選考結果」; pass body 「書類選考を通過(され|いたし)ました」「次回選考(面接)?のご案内」「次のステップ」; fail body -> see REJECTED. Ambiguous 「選考結果のご連絡」 without pass/fail phrase -> LLM.
  - STAGE=TEST_INVITE (適性検査のご案内): subject 「適性検査(受検)?のご案内」「Webテスト受検のお願い」「SPI受検のご案内」「テストセンター受検のご案内」「適性検査受検依頼」「筆記試験のご案内」「コーディングテストのご案内」 / 'Online assessment' 'Coding challenge' 'Take-home assignment' 'HackerRank invitation'; body 「受検(期限|締切|期間)」「〇月〇日(〇)\s*23[:：]59まで」「受検URL」「ログインID」「パスワード」「所要時間」; vendor via URL table. Output deadline (JST end-of-day if only date).
  - STAGE=INTERVIEW_SCHEDULING (面接日程調整): subject 「面接日程(調整|のご相談|について)」「日程調整の(お願い|ご連絡)」「ご都合をお知らせください」「面接候補日」「面談日程」 / 'Interview availability' 'Schedule your interview' 'Please select a time' 'Book a time'; body 「下記(候補日|日程)よりご都合の(よい|良い)日時」「候補日(時)?を(2|3|２|３)つ」「マイページより(予約|ご選択)」「予約ページ」「予約フォーム」 + scheduler URLs calendly.com, app.greenhouse.io/scheduling, app.ashbyhq.com, timerex.net, spirinc.com, chouseisan.com, youcanbook.me, eeasy.jp, calendar.app.google. Set meeting_link_pending=true, action_required=true; a list of 2+ datetimes = candidates, not confirmed.
  - STAGE=INTERVIEW_CONFIRMED (面接のご案内): subject 「(一次|二次|三次|最終|1次|2次)?面接(日程確定)?のご案内」「面接日時(確定)?のご連絡」「面接日程確定」「Web面接のご案内」「オンライン面接のご案内」「カジュアル面談のご案内」「面談のご案内」「リクルーター面談」「社員面談」「オファー面談」 / 'Interview confirmation' 'Interview with <Company>' 'Invitation: ' 'Your interview is scheduled'; body labels 「日時[:：]」「日程[:：]」「時間[:：]」「場所[:：]」「会場[:：]」「開催形式[:：]」「形式[:：](オンライン|Web|対面|来社)」「面接官[:：]」「所要時間[:：]」「持ち物[:：]」「服装[:：]」「URL[:：]」「接続先」「入室」「当日の流れ」. mode=online if Zoom/Teams/Meet/Webex URL or 「オンライン|Web面接|ビデオ」; onsite if 「場所[:：]」 with address/「〇階」「受付」「本社」.
  - MEETING_LINK_PENDING rule: stage==INTERVIEW_CONFIRMED && mode in {online, unknown} && no meeting URL && (body matches 「(URL|接続先|ミーティング情報)は(前日|当日|追って|別途|後日)(まで)?に?(ご案内|お送り|ご連絡)」 or 「前日までにお送りします」 or 'link will be sent' 'we will share the link' 'invite to follow'). Set meeting_link_pending=true and expected_link_by = interview_start - 1 day (if 「前日」) else interview_start - 2h. Later mail in same thread/company containing a meeting URL, or a calendar-notification@google.com invite with matching start time (±15 min), clears the flag. Also treat 「Zoom URLは当日マイページに掲載」 as pending with action 'check マイページ'.
  - STAGE=RESULT_PENDING_TEXT (選考結果のご連絡, ambiguous): subject 「選考結果のご連絡」「面接結果のご連絡」「(一次|二次|最終)面接結果」「選考結果について」「選考のご連絡」 / 'Update on your application' 'Your application status' 'Next steps'. Resolve with body: PASS if 「通過」「合格」「次回(選考|面接)」「次のステップ」「ぜひ次の」「お進みいただく」; FAIL if REJECTED phrases; OFFER if OFFER phrases; else LLM with thread context (prior stage) and cap confidence at 0.6.
  - STAGE=OFFER (内々定/内定): subject 「内々定のご連絡」「内々定通知」「内々定について」「内定のご連絡」「(採用)?内定(通知|のお知らせ)」「最終選考結果のご連絡」「オファーのご連絡」 / 'Offer' 'Offer letter' 'Congratulations' 'We are pleased to offer'; body 「内々定(と|を)(させていただき|お出し|差し上げ)」「採用内定を通知」「内定(を)?(差し上げ|お伝え)」「内定者」「内定式(10月1日|10/1)」「オファー面談」「処遇(条件)?」「労働条件通知書」「初任給」「(内定|入社)承諾書」「(承諾|回答|返答)期限」「〇月〇日までに(ご返答|ご回答|お返事)」 -> also extract offer_response_deadline. 2027卒 context: 内々定 before 2026-10-01, 内定 at/after 内定式.
  - STAGE=OFFER_DOCS (内定承諾書): subject 「内定承諾書(の)?(ご提出|送付|返送)(について|のお願い)」「入社承諾書」「内定承諾のお願い」「内定式のご案内」「入社手続きのご案内」「内定者懇親会」; body 「(内定|入社)承諾書(に)?(ご署名|ご記入|ご捺印)」「〇月〇日(必着|まで)」「ご返送」「電子署名」「クラウドサイン」「DocuSign」「GMOサイン」「内定者サイト」「内定者研修」. Extract due date; attachments (PDF/DOCX) read-only.
  - STAGE=REJECTED (お祈りメール): body 「誠に残念ながら」「残念ながら」「慎重に(選考|検討)(を)?(重ね|進め)た結果」「今回は(ご希望|ご期待)に(沿え|添え)(ない|ず|かね)」「貴意に添いかねる」「(採用を)?見送(らせて|り)」「お見送り」「不採用」「(次の|次回)選考へ(お進み|ご案内)(いただく)?ことができ(ません|ず)」「選考を終了」「ご縁がなかった」「今後の(ますますの)?ご活躍を(心より)?お祈り(申し上げ|いたし)」「ご健闘をお祈り」「他社(様)?での」「末筆ながら」 / 'we regret to inform' 'unfortunately' 'not (to )?(move|moving) forward' 'decided not to proceed' 'pursue other candidates' 'other candidates whose (skills|experience)' 'keep your (resume|profile) on file' 'wish you (the best|success|all the best)'. Require ≥1 negative core phrase (残念|見送|不採用|ご希望に沿え|regret|unfortunately|not move forward) AND NOT a pass phrase; 「お祈り申し上げます」 alone is insufficient (also appears in 内定 mails as 「ご健康をお祈り」). Also register サイレントお祈り: no mail 14 days after a stated 「〇日以内にご連絡」/「〇月〇日頃に結果」 -> status=STALE.
  - STAGE=WITHDRAWN (辞退受付): inbound subject 「(選考|内定)辞退(の)?(受付|について|のご連絡を承りました)」「辞退受付完了」; body 「辞退のご連絡を(いただき|承り)」「(選考|内定)辞退を承りました」「またご縁がありましたら」「今後のご活躍を」(here NOT a rejection - check thread: preceding SENT mail from the user with 「辞退」 in subject/body). Optionally parse the user's Sent folder (still read-only) for 「選考辞退のご連絡」「内定辞退のご連絡」 to set WITHDRAWN and for 「〇月〇日〇時でお願いいたします」「承知いたしました」 to confirm chosen interview slot.
  - STAGE=EVENT / LEAD / NEWSLETTER: 「会社説明会」「合同説明会」「セミナー(予約完了|のご案内)」「座談会」「インターンシップ(選考|のご案内)」「OB・OG訪問」「早期選考のご案内」「秋採用のご案内」「通年採用」 -> EVENT (keep dates; relevant for 秋採用); スカウト/オファー/InMail -> LEAD; List-Unsubscribe header + 「メールマガジン」「PR」「おすすめ求人」「新着求人」「Job alert」「Weekly」 -> NEWSLETTER (drop).
  - REMINDER mails: subject 「(面接)?前日のご連絡」「明日の面接について」「本日の面接について」「リマインド」「Reminder:」「Upcoming interview」 -> do not create a new stage; attach to existing interview, update meeting URL if present, clear link_pending.
  - COMPANY EXTRACTION priority: (1) platform-encoded id (sonar local-part, HRMOS subdomain, Workday tenant, Greenhouse/Lever/Ashby/Talentio/HERP URL slug, i-web mypage path slug) mapped via a user-maintained alias table; (2) From display name minus role words regex (採用(担当|チーム|グループ|事務局)|人事(部|課)?|新卒採用|Recruit(ing|ment)?( Team)?|Talent Acquisition|Careers|HR|事務局|係) and 「様」; (3) subject bracket 【...】/[...]/「...」 first token; (4) body first line 「<社名> 採用担当です」/「<社名>の<氏名>です」; (5) signature regex (株式会社|合同会社|有限会社)?[^\s　]{1,30}(株式会社|Inc\.|Co\., ?Ltd\.|K\.K\.|G\.K\.|LLC); (6) sender domain -> company (skip for relay/ATS domains). Normalize: NFKC, ㈱->株式会社, remove 株式会社/(株)/Inc./Co., Ltd. for matching key, keep display form; JP/EN alias pairs (ソニーグループ株式会社 = Sony Group Corporation).
  - POSITION EXTRACTION: regex after 「(募集|応募|希望)?職種[:：]」「ポジション[:：]」「コース[:：]」「(応募|希望)コース」「職種名」 / 'Position:' 'Role:' 'for the (.+?) (position|role)' 'your application (to|for) (.+?) at' 'applying to <Company> - <Role>'; new-grad 総合職/技術職/研究職/エンジニア職/データサイエンティスト/AIエンジニア; propagate position from the thread's first APPLIED mail (Gmail threadId, In-Reply-To/References) and from the URL job title page if already cached. Never fetch job pages that require login.
  - DATETIME (JST) EXTRACTION: pre-normalize with NFKC (１４：００ -> 14:00, （ ）-> ( ), ～/〜/~/－/ー/–/- -> '-', ：-> ':', U+3000 -> space). Patterns: (20\d{2}年)?\s*(\d{1,2})月\s*(\d{1,2})日\s*(\([月火水木金土日祝]\))?\s*((午前|午後|AM|PM)?\s*(\d{1,2})(時|:)(\d{2})?分?)\s*(-\s*((午前|午後)?\s*(\d{1,2})(時|:)(\d{2})?分?))?; 2026/09/23 14:00; 2026-09-23T14:00; 9/23(水)14:00-15:00; 令和8年 -> 2026; relative 「本日」「明日」「明後日」「来週(月|火|...)曜」 resolved against the mail Date header converted to Asia/Tokyo; missing year -> nearest future date within 8 months of mail Date (handles Dec->Jan). Default tz Asia/Tokyo unless explicit (JST|日本時間|GMT\+9|UTC\+9|PST|PDT|PT|EST|EDT|ET|CET|BST|SGT|IST|UTC); 外資 HQ recruiters sometimes send US time -> flag tz_explicit=false/true. Prefer .ics DTSTART/DTEND/TZID over prose. Store start_utc, end_utc, tz_source, raw_snippet; if ≥2 datetimes and stage is SCHEDULING -> candidates[]; if 「〇月〇日中」「〇月〇日まで」 -> deadline (23:59 JST).
  - MEETING URL EXTRACTION: search text AND <a href> of HTML; regexes: zoom https?://([a-z0-9-]+\.)?zoom\.(us|com)/(j|my|w|s)/[A-Za-z0-9?=&._-]+ ; teams https://teams\.microsoft\.com/l/meetup-join/[^\s"<>]+ | https://teams\.live\.com/meet/[^\s"<>]+ ; meet https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3} ; webex https://[a-z0-9-]+\.webex\.com/[^\s"<>]+ ; whereby https://whereby\.com/[^\s]+ ; also 「(ミーティング|会議)\s*ID[:：]\s*([\d ]{9,14})」「パスコード[:：]\s*(\S+)」. Do NOT follow click-tracking wrappers (ct.sendgrid.net, mandrillapp, links.*.hrmos.co, *.mynavi.jp/l/, lnkd.in, urldefense) - resolving them registers a click/open on the sender side, which violates the read-only posture; display the wrapped link and let the user click.
  - PII / SECRETS: redact before any LLM call or log: recruiter personal names (「採用担当[:：]\s*\S+」「担当[:：]」 lines, 姓 名 in signatures), phone numbers (0\d{1,4}-\d{1,4}-\d{3,4}, \+81[\d-]+, 「TEL」「携帯」 lines), personal/direct recruiter emails, postal addresses, the user's own 受検ID/マイページID/パスワード/テストセンターID, Zoom/Teams passcodes (store encrypted, never in prompts), 内定 salary figures (keep local only). Keep company name, generic mailbox domain, stage, datetimes, and URL host in the LLM payload.
  - HTML-ONLY BODIES: Mynavi, Workday, Greenhouse, Wantedly, OfferBox, LinkedIn often send HTML-only or HTML with a useless text/plain. Convert with a DOM-aware converter: <br>/<p>/<div>/<tr>/<li> -> newline, <td> -> tab, decode entities, drop display:none/preheader blocks, and emit anchors as 'text (href)' when link text is 「こちら」「ここ」「詳細」「Join」「参加」「Apply」 so URLs are not lost. Gmail API: request format=full, walk multipart/alternative and multipart/mixed for text/calendar and application/ics parts; use payload.headers Date, From, Reply-To, Sender, List-Unsubscribe, Authentication-Results.
  - FORWARDED MAILS (自分転送 from 大学 mail or LINE screenshots): subject prefixes ^(Fwd?|FW|転送|Fw)[:：]; body markers 「----- Original Message -----」「-------- 転送メッセージ --------」「From: ... Sent: ... To: ... Subject:」「差出人:」「送信日時:」「件名:」 -> parse inner From/Date/Subject and treat inner From domain as the real sender; strip the outer Date. University domains (\.ac\.jp$) as outer sender are common because students register 大学 mail on マイナビ/i-web.
  - 全角/半角 AND SPELLING VARIANTS: normalize with unicodedata.normalize('NFKC') then lower-case ASCII; unify 面接/面談/インタビュー, 受検/受験, 内々定/内内定, Web/WEB/ウェブ, オンライン/Online, 日程/日時, 締切/締め切り/〆切, 〇/○/◯ placeholders, 曜日 forms (水)/（水）/水曜日, times 14時00分/14:00/１４：００/午後2時/2:00 PM/14時~15時; wave dash U+301C vs U+FF5E vs '~'; long vowel 'ー' inside 'エントリー'.
  - MULTI-COMPANY RELAY SENDERS: for mynavi.jp, rikunabi.com/indeed.com, offerbox.jp, wantedly.com, linkedin.com, i-webs.jp (if seen), and agency domains, NEVER set company=sender domain; require company from subject/body; do not merge Gmail threads across companies just because subjects match (Gmail threads by subject+references); key applications by (company_norm, position_norm, cohort).
  - MAILS WITH RESULTS ONLY IN THE PORTAL: i-web/sonar/in-house マイページ mails and LINE hand-offs -> stage=PORTAL_UPDATE with action_required and portal_url; the app should surface these prominently because they hide 選考結果/面接案内 that the classifier cannot see.
  - TRUST / ANTI-PHISHING: use Gmail Authentication-Results (spf=pass dkim=pass dmarc=pass) and align From domain with the platform table; Bizreach/HRMOS published a spoofing warning (2025-07-09) and RTX/SmartRecruiters/LLNL publish legitimate-domain lists; unknown domain + 「内定」「入金」「手数料」 -> flag suspicious.
  - COHORT / CYCLE TAGS: detect 「27卒」「2027卒」「2027年卒」「2027年度(新卒)?」「2027新卒」「27年度」 and i-web path suffix 2027 -> cohort=2027; 「秋採用」「通年採用」「早期選考」「28卒」「インターン(シップ)?」 -> tag; 「内定式」 -> 2026-10-01 default anchor for 内々定->内定 transition.
  - LLM FALLBACK CONTRACT: invoke only when tier-1/2 rules give confidence <0.7 or conflicting stages; input = redacted normalized text (first 4,000 chars) + prior stage of the same (company, position) + mail Date in JST; output JSON {stage, confidence, company, position, datetimes:[{start,end,tz_explicit,kind:confirmed|candidate|deadline}], meeting_url, meeting_link_pending, portal_url, action_required, action_summary_ja}; temperature 0; few-shot with one example each of お祈り, 面接のご案内 with 「URLは前日に」, マイナビ relay, Workday rejection in English; never let the LLM override a tier-1 sender-domain platform assignment.

## Recommendation
Build the classifier as three tiers. Tier 1 (deterministic, high precision): map From/Reply-To domain and body URL hosts to a platform using the sender-domain and body-URL tables above; where the address encodes the company (snar.jp local-part, *.hrmos.co subdomain, myworkday.com tenant, Greenhouse/Lever/Ashby/Talentio/HERP/i-web URL slugs) set the company immediately; for relay platforms (mynavi.jp family, rikunabi/indeed, offerbox.jp, wantedly.com, linkedin.com) set platform only and force company extraction from subject/body. Tier 2 (deterministic phrase scoring): after HTML-to-text and NFKC normalization, score each stage with the Japanese/English phrase lists (APPLIED, SCREENING_RESULT, TEST_INVITE, INTERVIEW_SCHEDULING, INTERVIEW_CONFIRMED, RESULT_PENDING_TEXT, OFFER, OFFER_DOCS, REJECTED, WITHDRAWN, EVENT, LEAD, NEWSLETTER, PORTAL_UPDATE, REMINDER), requiring a negative core phrase for REJECTED and pass/offer phrases to disambiguate 「選考結果のご連絡」; extract datetimes (prefer .ics DTSTART;TZID=Asia/Tokyo), meeting URLs (Zoom/Teams/Meet/Webex regexes, no click-tracker resolution), deadlines, and set meeting_link_pending when an online interview is confirmed without a URL or the mail says the URL comes 前日/追って. Tier 3 (LLM fallback with strict JSON schema, redacted input, thread's prior stage as context) only for low-confidence or free-form recruiter mail. Cross-link with Google Calendar read-only events by iCalUID/start time to clear pending links and dedupe. Treat i-web/sonar マイページ stubs and LINE hand-offs as first-class PORTAL_UPDATE items with a manual-paste path, because a large share of 新卒 selection outcomes never appear in Gmail text. Seed the alias table with the user's actual applied companies and confirm the still-unverified From local-parts (HireVue, ジョブカン default no-reply, TG-WEB/玉手箱 vendor senders, Lever) from real headers in the user's mailbox during onboarding.

## Open questions
  - Exact From local-parts still unverified from official pages: HireVue (domain @hirevue.com confirmed, likely noreply@hirevue.com), ジョブカン採用管理 default no-reply (domain ats.jobcan.ne.jp confirmed via support@), Lever (no-reply@hire.lever.co from Lever help snippets/third parties; Lever help center is JS-rendered), Talentio (em.talentio.com seen once; @talentio.com confirmed by company pages). Confirm from real headers in the user's Gmail during onboarding.
  - Do TG-WEB (c-personal.com / e-gitest.com / e-assessment.jp) and 日本SHL (e-exams.jp) platforms ever email candidates directly, or is the invitation always sent by the company/ATS? Only URL-based detection is verified today.
  - Does i-web ever send from a platform domain (i-webs.jp / mypage-info.com were mentioned by 官公庁 pages but not verified), or always from the company's configured address as in the TEL example?
  - Rikunabi new-grad exact sender addresses beyond the @mail.rikunabi.com / @indeed.com allow-list (help site is Salesforce-rendered and returned 5xx to fetches).
  - Exact マイナビ relay subject template (observed fragments 「…よりメッセージが届いています」「お返事が届いています」) - capture from the user's inbox to finalize the regex.
  - Should the app parse the user's Sent folder (still read-only) to detect self-initiated 辞退 and confirmed interview slots? This materially improves WITHDRAWN and INTERVIEW_CONFIRMED accuracy.
  - How to ingest LINE公式アカウント messages: manual paste, screenshot OCR, or ignore with a visible 'LINE channel' badge per company?
  - Does the user also receive recruiting mail on a university (.ac.jp) address forwarded into Gmail? If so, forwarded-mail parsing must be enabled by default.
  - Which LLM/model and redaction policy to use for tier 3; whether to disable it entirely for mails containing 内定/処遇 figures.

## Sources
- HERP Hire FAQ - 応募者メールは @candidacy.herp.cloud から送信: https://guide.herp.cloud/faq/184ab645335243f5903d2bcb3b46ece3
- マイナビ2027 Q&A メール・メッセージ (sender addresses, お返事箱/スカウト categories): https://job.mynavi.jp/conts/2027/kaiin/message.html
- 東京エレクトロン i-web マイページ (sender telpdrecruit@tel.com notice): https://mypage.3010.i-webs.jp/tel2027/
- i-web 公式 (ヒューマネージ): https://i-web-ats.humanage.co.jp/
- キヤノン 新卒採用マイページ (i-web.jpn.com URL pattern): https://newgraduate.i-web.jpn.com/canon2027/
- DeNA 新卒 お問い合わせ (dena@snar.jp 送信用アドレス): https://student.dena.com/contact/
- 稲畑産業 エントリー (inabata@snar.jp): https://www.inabata.co.jp/recruit/entry/
- HRMOS採用 company page - 「@referral-kashiwabara.hrmos.co」 sender: https://hrmos.co/pages/referral-kashiwabara
- HRMOS/ビズリーチ spoofing warning (2025-07-09): https://hrmos.co/info/news/20250709-2/
- Talentio - company page asking to allow @talentio.com: https://internshipguide.jp/interns/internDetail/20002
- Talentio メール配信機能に関する個別規定 (SendGrid): https://www.talentio.co.jp/mail-term
- ジョブカン採用管理 help - 送信元メールアドレス設定: https://jobcan-ats.zendesk.com/hc/ja/articles/225122848
- ジョブカン採用管理 お知らせ (support@ats.jobcan.ne.jp): https://all.jobcan.ne.jp/info/update/7262/
- OfferBox help - 「@offerbox.jp」ドメインのメール受信: https://offerboxhelp.zendesk.com/hc/ja/articles/360052681973
- Wantedly help - Wantedly からのメールが届かない (@wantedly.com): https://help.wantedly.com/hc/ja/articles/50327552221209
- リクナビ help - allow @mail.rikunabi.com and @indeed.com: https://help.job.rikunabi.com/s/article/000030663
- リクナビNEXT sender center@next.rikunabi.com (third party): https://www.tenshoku-careerguide.com/article/156/
- SPI3 テストセンター FAQ (arorua.net domain): https://www.spi.recruit.co.jp/testcenter/faq.html
- 札幌市 SPI方式 申込み (noreply_tc@arorua.net): https://www.city.sapporo.jp/jinji-iinkai/saiyo/shiken/inta-netmoushikomi_spi.html
- キャリタス就活 WEBテスト見分け方 (e-exams.jp / c-personal.com / e-gitest.com URLs): https://job.career-tasu.jp/guide/step/136/
- Webテストの見分け方 URL・案内メール (SPI/玉手箱/TG-WEB): https://webtestmaster.jp/webtest-miwakekata-url-mail-spi-tamatebako-tgweb/
- Greenhouse Recruiting no-reply email addresses (official): https://support.greenhouse.io/hc/en-us/articles/17675865619099-Greenhouse-Recruiting-no-reply-email-addresses
- Lever help - Managing failed emails (no-reply@hire.lever.co): https://help.lever.co/s/article/Managing-failed-emails
- LoopCV - Lever application status emails from hire.lever.co: https://www.loopcv.pro/guides/lever-application-status/
- Ashby docs - Email domain setup (default noreply@ashbyhq.com): https://docs.ashbyhq.com/email-domain-setup
- SmartRecruiters recruitment fraud information (@smartrecruiters.com only): https://www.smartrecruiterscareers.com/recruitment-fraud-information
- LLNL job fraud statement (notifications@smartrecruiters.com): https://www.llnl.gov/sites/www/files/2023-05/LLNL-Job-Fraud-Statement-Updated-4.26.23.pdf
- Parexel FAQ - confirmation from parexel@myworkday.com: https://jobs.parexel.com/en/faqs
- University of Washington - My Workday UW (uw@myworkday.com): https://www.washington.edu/jobs/after-applying/
- RTX recruitment fraud page (@hirevue.com, @workday.com legitimate): https://careers.rtx.com/global/en/recruitment-fraud
- Calendly help - scheduling notifications sent from notifications@calendly.com: https://calendly.com/help/calendly-scheduling-notifications
- Calendly help - no-reply email for confirmations: https://calendly.com/help/how-to-use-a-no-reply-email-for-confirmations
- Zoom support (JA) - no-reply@zoom.us and mail IPs: https://support.zoom.com/hc/ja/article?id=zm_kb&sysparm_article=KB0060118
- Gmail filter for calendar-notification@google.com: https://webapps.stackexchange.com/questions/60188/
- Wired - Google Calendar invites should come from calendar-notification@google.com: https://www.wired.com/story/google-calendar-malware-is-on-the-rise-heres-how-to-stay-safe/
- LinkedIn sender addresses list (jobs-noreply, messages-noreply, etc.): https://clean.email/how-to-unsubscribe-from-emails/unsubscribe-from-linkedin-emails
- LinkedIn - Identify non-official job emails (@linkedin.com): https://www.linkedin.com/top-content/career/job-posting-verification-process/identify-non-official-job-emails/
- お祈りメール templates - 件名「選考結果のご連絡」 (OneCareer): https://service.onecareer.jp/blog/rejection_mail
- 不採用通知メール templates (リクルート DirectScout): https://directscout.recruit.co.jp/biz/guide/article/810/
- 不採用通知メール templates (OfferBox 人事ZINE): https://offerbox.jp/company/jinji-zine/rejection-mail/
- 内定通知メール例文・テンプレート集 (Vollect) - 内定承諾書 wording: https://vollect.net/hrpedia/job-offer-email/
- 内定通知メール (bsearch) - 新卒 templates: https://www.bsearch.co.jp/media/job_offer_email/
- 内定者フォローメール例文 (マルゴト) - 内定承諾書 返送期限: https://marugotoinc.jp/blog/followmail/
