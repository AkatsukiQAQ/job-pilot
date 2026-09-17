# 2027 卒时间线与 2026 年秋仍开放的机会

> **AI 调研附录**（生成于 2026-09-16，英文）。内容由并行调研 agent 对照官方页面整理，verified/unverified 标注以原文为准；实现前需再次核对。相关更正见 japan-critique.md 与 proposal-judgments.md。

# 2027卒 hiring timeline (Japan) and what is still open in autumn 2026 - official 就活ルール, 早期選考 reality, 秋採用/通年採用, research-track hiring, Japan-aware pipeline stages, 内定承諾 norms, 留学生 visa timing, and 新卒 salary expression

## Summary
Official 2027卒 rule (内閣官房 要請, dated 2026-03-24): 広報活動 2026-03-01以降, 採用選考活動 2026-06-01以降, 正式内定 2026-10-01以降, with an exception letting 専門活用型インターンシップ (2週間以上, 春休み以降) participants enter selection before June. Reality is far earlier: per the 内閣官房 R7.12.26 資料, ~60% of firms started 広報 before Feb, ~70% started selection before May, ~60% issued 内々定 before May; 就職白書2026 says 41.4% of firms began 内々定出し by Feb of the pre-graduation year (1.2% for 2017卒). 27卒 内定率: Recruit 6/1 = 77.2% (理系 81.1%, 進路確定率 57.3%); Mynavi 8月末 = 85.6% (理系男子 89.3%); 学情/Nikkei 7月末 = 84.8% "4年ぶりの低水準", 就職活動率 27.9% (8/5). 26卒 benchmark at 9/1 was 94.8% with 11.5% still active, so on 2026-09-16 roughly 1 in 7 27卒 lack an offer and ~1 in 4 are still active - the 秋採用 pool is real. 秋採用 runs Sep-Nov (peak after 内定式 2026-10-01 when 内定辞退 opens seats), with 冬採用 Dec-Feb; decisions typically in 1-2 weeks with 2-3 interviews. Status of named targets as of today: PFN 2027年入社 ran 第1期-第4期 (Nov 2025-Feb 28 2026 23:59) and opened 2028年入社 プレエントリー on 2026-09-01 (no 第5期 announced; "随時更新"); Rakuten opened "October 2027 Entry" applications on 2026-09-01 (the one confirmed big-tech 新卒 window still open for 27卒); Mercari is 通年採用 (4月/10月 入社) but its student page now targets 2028年4月以降入社; LINEヤフー and Sony (ジョブマッチング Mar 1-9, 2026) and AWS Japan SA (now 28卒) are closed for 27卒; Sakana AI, Sony AI, RIKEN AIP, Woven by Toyota hire on rolling job-posting basis (no 新卒 program) via careers@sakana.ai + Google Form, Workday, riken.jp careers, and Lever respectively. Japan-aware stages: プレエントリー → ES提出 → Webテスト (SPI3/玉手箱/TG-WEB/SCOA) → コーディングテスト → 録画面接 → GD → 一次/二次/最終面接 → 内々定 → オファー面談 → 内定承諾 → 内定(10/1) → 入社. 留学生: ISA says apply for 留学→技術・人文知識・国際業務 "12月1日から1月末までの間" for April start (i.e., 2026-12-01 to 2027-01-31 for 27卒), document-omission for 本邦大学卒業(予定)者 since 2025-12-01, extra category-3/4 documents since 2026-04-15; no offer by graduation → 特定活動(継続就職活動) 6か月+1回更新 = 最長1年 with 大学推薦状. Salary: 新卒 offers are quoted as 初任給 月給 by degree (Sony 2026年度: 博士 383,000円〜, 修士 363,000円〜, 学部 333,000円〜, 賞与 年1回), often 基本給+固定残業代 (Mercari: 月給 300,000 = 基本給 221,965 + 45時間分 固定残業代 78,035, 賞与 3月・9月), or 年俸制/想定年収 at foreign firms and startups, or 裁量労働制 for R&D - so the job model needs a salary_basis enum plus degree tier, fixed-OT hours/amount, bonus-inclusion and fiscal-year fields.

## Items
### 2027卒 就活ルール (政府要請) - 内閣官房「2027年度卒業・修了予定者等の就職・採用活動に関する要請」 [high]
Official government-requested schedule (経団連 rule abolished 2018; government-led since 2021卒). For 2027卒: 広報活動開始 = 卒業・修了年度に入る直前の3月1日以降 (2026-03-01); 採用選考活動開始 = 卒業・修了年度の6月1日以降 (2026-06-01); 正式な内定日 = 卒業・修了年度の10月1日以降 (2026-10-01). 要請文 dated 令和8年3月24日 (2026-03-24), issued jointly by 内閣官房・文部科学省・厚生労働省・経済産業省 to 経済団体・業界団体. Exception: students judged highly specialised via 専門活用型インターンシップ (2週間以上, 春休み以降実施) may move into 採用選考プロセス before June. Also requests 学事日程への配慮, ハラスメント等の防止 (incl. オワハラ), 多様で公平・公正な採用選考機会.
Read-only access: Public HTML page https://www.cas.go.jp/jp/seisaku/shushoku_katsudou_yousei/2027nendosotu/index.html and PDF 2027betten1.pdf; no RSS. Static reference - fetch once per cycle.
Notes: It is a 要請 (request), not law; non-binding. A 28卒-onward rule review is under way (関係省庁連絡会議, R7.12.26「考え方」): universities asked that selection happen only in 春休み以降長期休業期間; economic side said 充足率 is falling. For the app: hard-code 2026-03-01 / 2026-06-01 / 2026-10-01 as the 27卒 milestones, and 2026-10-01 (Thursday) as default 内定式 date.
Src: https://www.cas.go.jp/jp/seisaku/shushoku_katsudou_yousei/2027nendosotu/index.html
### 早期選考 / インターン経由選考 reality (内閣官房 R7.12.26 資料 + 就職白書2026) [high]
Government's own evidence of the rule/reality gap: 文科省 company survey shows ~6割 started 広報活動 in Feb or earlier, ~7割 started 採用選考 in May or earlier, ~6割 issued 内々定 in May or earlier. インターンシップ等 participation ~7割 of students, ramping from July of the pre-graduation year. 三省合意 (2022 revision) allows student info from qualifying (タイプ3/4) internships to be used in 広報・選考. Recruit 就職白書2026: firms starting 内々定・内定出し by Feb of pre-graduation year = 41.4% for 2026卒 vs 1.2% for 2017卒.
Read-only access: Public PDF https://www.cas.go.jp/jp/seisaku/shushoku_katsudou/pdf/r071226_siryou.pdf (PDF text extraction failed in this session; mirror at fukui-ut.ac.jp). 就職白書2026 landing https://shushokumirai.recruit.co.jp/white_paper_article/20260220001/ with 5MB PDF.
Notes: Practical meaning for a 27卒 in Sept 2026: the main-cycle 内々定 wave (Jan-Jun 2026) is over; what remains is 秋採用/通年採用/追加募集 and rolling (non-新卒) postings. For 28卒-style tracks (PFN 2028 pre-entry, Sony 2028 site, AWS 2028卒 SA) the user is generally ineligible unless deferring graduation.
Src: https://www.cas.go.jp/jp/seisaku/shushoku_katsudou/pdf/r071226_siryou.pdf
### 27卒 内定率 trackers: リクルート就職みらい研究所 就職プロセス調査 / マイナビ キャリアリサーチLab / 学情 (via 日経) [high]
Monthly public surveys usable as the app's 'market pressure' gauge. Recruit (大学生, 大学院生除く): 2/1 32.8%, 3/1 38.1% (文系35.2/理系44.4), 5/1 67.0%, 6/1 77.2% (文系75.1/理系81.1; 関東80.3; 進路確定率57.3%). Mynavi 内々定率: 3/1 46.0, 3月末 58.7, 4月末 70.9, 5月末 76.4, 6月末 81.2, 7月末 83.7, 8月末 85.6 (理系男子89.3, 理系女子88.1, 文系女子86.2, 文系男子80.8). 学情 via 日経: 7月末 84.8% '4年ぶりの低水準', 就職活動率 27.9% at 8/5 (+3.5pt vs 26卒). 26卒 benchmark (Recruit): 9/1 内定率 94.8%, 就職活動実施率 11.5%.
Read-only access: Public HTML. Recruit index https://shushokumirai.recruit.co.jp/research/ ; article URL pattern research_article/YYYYMMDD001/ (27卒 6/1 = 20260706001; 26卒 9/1 = 20250909001, 10/1 = 20251009001, 12/1 = 20251215001). Mynavi rolling column https://career-research.mynavi.jp/column/20260317_108783/ (updated monthly). No RSS found; scrape-only (check ToS), or read numbers manually.
Notes: Recruit's 27卒 9/1 report was not yet posted at fetch time (26卒 equivalent was published 2025-09-09); expect it any day, then 10/1 (~Oct 9) and 12/1 (~Dec 15). 27卒 is tracking slightly below 26卒, i.e., more students still active - more competition in 秋採用 but also more firms with unfilled seats.
Src: https://shushokumirai.recruit.co.jp/research/
### 秋採用 / 追加募集 aggregator lists for 27卒 (就活エンジン, 就活マップ noahs-ark, ONE CAREER, 外資就活, type就活, ミキワメ) [medium]
Third-party lists of companies still recruiting 27卒. 就活エンジン (updated 2026-09-08) defines 秋採用 as 9月〜11月末 selection to backfill 内定辞退, notes fast エントリー→内定; names サイバーエージェント, LINEヤフー, メルカリ, DeNA, BCG, アクセンチュア, SMBC, トヨタ, 日立, 富士通, KDDI. 就活マップ (updated 2026-08-31) lists ソフトバンク, LINEヤフー, サイバーエージェント, メルカリ, 富士通, NTTデータ, みずほFG, 日本銀行, 損保ジャパン, 三井住友海上, トヨタ, 本田技研, 東芝, 三菱電機, 三菱商事, 住友商事, 丸紅 as 継続採用; describes 秋採用 (9-11月 peak), 冬採用 (12-2月, 年度内採用完了), 通年採用 (IT/人材/営業系). Typical 秋採用: result in 1-2 weeks, 2-3 interviews, applicant pools drop from thousands to hundreds.
Read-only access: Public HTML (scrape-only; no API/RSS): https://shukatsu-engine.com/autumn-recruitment-oote/ ; https://noahs-ark.co.jp/maniau-entry/ ; ONE CAREER 27卒 本選考 list sortable by 締切日 https://www.onecareer.jp/events/selection/graduate_year/2027 ; type就活 https://typeshukatsu.jp/recruitment/year-2027/ (URL pattern /company/{id}/recruitment/{id}/; showed only 終了 items). 外資就活 deadline list https://gaishishukatsu.com/recruiting_info?order=deadline&allgy=false is login-gated (email digests from gaishishukatsu.com if the user registers).
Notes: Aggregator claims must be re-verified on official pages - one conflict already found: LINEヤフー official page says '2027年度新卒採用のエントリー受付は終了しました' while both aggregators list it as 継続採用. Store aggregator hits as 待核実, never 確認在招.
Src: https://shukatsu-engine.com/autumn-recruitment-oote/
### Preferred Networks (PFN) 新卒採用 2027年入社 / 2028年入社 [high]
Research-track AI company hiring エンジニア・リサーチャー in waves. 2027年入社: プレエントリー 2025-09-01; 第1期 2025-11-04; 第2期 2025-12-01; 第3期 2025-12-25; 第4期 2026-02-03 with 締切 2026-02-28(土) 23:59; statement '第4期締切終了後は、随時採用サイトにて更新いたします'; no 第5期 announced as of 2026-09-16. Fields: プロダクト・アプリ・サービス開発, ソリューションエンジニアリング・データサイエンス, 生成AI・基盤モデル, 計算基盤, AIチップ, 材料探索. 入社時期 2027年4月 (pre-entry text mentioned 4月または10月). 選考: 書類選考 → コーディングテスト → 面接(複数回) → 内定. 2028年入社 プレエントリー opened 2026-09-01 (news /ja/news/pr20260901-0). Summer intern 2026-08-06〜09-18.
Read-only access: Public news tag page https://www.preferred.jp/ja/news/tag/149 (新卒採用) and category https://www.preferred.jp/ja/news/category/careers ; WordPress-style site so /feed/ likely exists (verify). Application-confirmation emails come from preferred.jp (ATS not identified).
Notes: For a 27卒 today: 2027 新卒 windows are closed; watch tag/149 for any 2027年入社 追加募集, or consider キャリア採用 postings (rolling) for 2027年10月 start. 2028 pre-entry targets 2028年4月/10月 入社 - only relevant if the user defers graduation. Reported new-grad comp (secondary, InterviewCat) 700万円後半-900万円 年収.
Src: https://www.preferred.jp/ja/news/pr20260203
### Sakana AI careers (rolling, no 新卒 program) [high]
Tokyo AI lab with 23 open roles (2026-09-16): Research - Software Engineer (R&D), Member of Technical Staff (LLM Development), MTS (RSI Lab; Full-time/Visiting Researcher/Internship), Program Manager (RSI Lab); Product - Applied Research Engineer (Product; Full-time/Contract/Intern), Software Engineer (Product), SWE (Infrastructure & Platform Reliability), Data Engineer, PM, Product Designer, Business Intern; GTM - Forward Deployed Engineer (GTM), Product Sales/AE; Corporate roles. Application: email careers@sakana.ai then Google Form https://forms.gle/NFE3U5XoiYLWhnH48 with English CV + cover letter. No 新卒/PhD program stated; no rolling-hiring statement but postings are continuous.
Read-only access: Public HTML https://sakana.ai/careers/ (scrape-only; no ATS, no RSS). Recruiting emails only from @sakana.ai addresses (site warns against impostors).
Notes: If a self-hoster currently works at any target company, that domain should be configurable as an 'own employer' exclusion so its mail is not classified as inbound recruiter mail. Applied Research Engineer (Product) and Forward Deployed Engineer (GTM) overlap the ARE / FDE target-role examples in REQUIREMENTS 1.4.
Src: https://sakana.ai/careers/
### Sony Group 新卒採用 (ソニー株式会社 2027年度) and Sony AI [medium]
Sony 27卒: ジョブマッチング募集期間 2026-03-01〜03-09, 技術系面接 3月下旬〜4月上旬 - closed; no 秋採用 statement. 応募資格 wording: '2027年3月末までに大学、大学院または高等専門学校専攻科を卒業見込みの方' and '2027年4月時点で、最終学歴卒業後3年未満の方（職歴をお持ちの場合を含みます）'. 初任給 (2026年度, 月給): 博士了 383,000円〜, 修士了 363,000円〜, 大学卒 333,000円〜; 賞与 年1回; 給与改定 '年功ではなく個人の役割・実績に応じ改定'. 2028卒 joint MyPage live at https://www.recruit.sony.co.jp/2028/ (27卒 was /2027/). Sony AI (ai.sony) lists only internships (must be enrolled in PhD/MSc), full-time research scientists hired experienced; ATS = Workday sonyglobal.wd1.myworkdayjobs.com/SonyJapanCareers.
Read-only access: Public HTML https://www.sony.co.jp/recruit/newgrads/ ; MyPage emails from recruit.sony.co.jp (業務委託先 = outsourced ATS); Sony AI via Workday (myworkdayjobs.com notification domain).
Notes: Illustrates two norms: (1) 卒業後3年未満 counts as 新卒 (per 厚労省 青少年雇用機会確保指針), so a 27卒 stays 新卒-eligible at Sony through the 2028 and 2029 cycles; (2) 初任給 is quoted 月給 by degree with bonus separate. Sony AI internships are the visible pipeline into research roles.
Src: https://www.sony.co.jp/recruit/newgrads/
### Rakuten 新卒採用 - October 2027 Entry (open since 2026-09-01) [high]
Rakuten Group graduate hiring with two entry points per year: 'Applications for April 2027 are now open' (posted 2026-01-13) and 'Applications for October 2027 Entry are now open' (posted 2026-09-01); Engineer and Business tracks; summer intern for 2028 joiners opened 2026-04-24. Salary details on /corp/careers/graduates/recruit_business/ (updated 2025-04-01).
Read-only access: Public HTML https://global.rakuten.com/corp/careers/graduates/ (news list; scrape-only). Application platform not identified on page.
Notes: The one confirmed large-tech 新卒 window still open that a March-2027 graduate can plausibly use (join 2027-10). Open question: eligibility wording for 2027年3月卒 and visa handling for the Apr-Oct gap (特定活動 内定待機, see visa item).
Src: https://global.rakuten.com/corp/careers/graduates/
### Mercari 新卒採用 (通年採用 example) [medium]
Explicit 通年採用: 'メルカリでは通年採用を実施しているため、必ずしも上記のスケジュールに当てはまらない場合があります'. 入社時期 '毎年 4月・10月'. Current target: '2028年4月以降に入社が可能な16歳以上の学生'. 選考: 書類選考 → 技術課題 (エンジニア; 'コンピューターサイエンスに関する知識を確認') → 面接. Salary shown as 月給 with fixed OT: '月給例）300,000円 の場合：基本給 221,965円＋45時間分の固定残業代 78,035円'; '賞与あり（3月・9月）'.
Read-only access: Public HTML https://careers.mercari.com/jp/students/ (scrape-only; Mercari uses its own careers site).
Notes: Best concrete example of the 基本給+固定残業代 disclosure format the app's salary parser must handle. Unclear whether a 27卒 aiming for 2027年10月入社 is accepted now that the page targets 2028年4月以降 - ask via 待核実.
Src: https://careers.mercari.com/jp/students/
### LINEヤフー 新卒採用 (closed for 27卒) [low]
Official page states '2027年度新卒採用のエントリー受付は終了しました' (2026). Engineering hiring emphasises 実装力.
Read-only access: Public HTML https://www.lycorp.co.jp/ja/recruit/newgrads/
Notes: Contradicts aggregator '継続採用' lists - proves the need to verify on official pages before marking 確認在招.
Src: https://www.lycorp.co.jp/ja/recruit/newgrads/
### AWS Japan 新卒 Solutions Architect (now 2028年卒) [low]
Page shows '2028 年卒対象 SA 本選考応募受付開始' linking to amazon.jobs/jp/jobs/10503564/2028-aws-solution-architect-field-ags-apj-tech-cs. 27卒 SA cycle is therefore closed. Foreign-firm pattern: single annual 本選考 opening ~Sept of the pre-graduation year.
Read-only access: Public HTML https://aws.amazon.com/jp/careers/newgraduate/solutionsarchitect ; applications via amazon.jobs (notification domain amazon.jobs / amazon.com).
Notes: Amazon Japan comp is expressed as 年収 base + RSU + サインオン (foreign-firm 年収 basis). 27卒 user should look at Amazon Japan's experienced/early-career postings instead.
Src: https://aws.amazon.com/jp/careers/newgraduate/solutionsarchitect
### Woven by Toyota / Toyota Research Institute [medium]
Woven by Toyota (Tokyo) has no dedicated 新卒 page; hires via job postings and internships. Internship: eligible if '2028年3月以前に卒業予定'; June 2026 cohort deadlines Feb 2-Mar 20, 2026; Aug 2026 cohort Apr 6-May 22, 2026; internship 'can lead to full-time employment' (正社員採用に繋がることがあります). ATS = Lever (jobs.lever.co/woven-by-toyota). Toyota Research Institute is US-based (Los Altos/Cambridge) and is not a Japan 新卒 channel.
Read-only access: Public HTML https://woven.toyota/jp/careers/ and /jp/careers/internship/ ; Lever postings JSON is public at https://api.lever.co/v0/postings/woven-by-toyota?mode=json (standard Lever endpoint; verify). Lever emails come from hire.lever.co / jobs.lever.co.
Notes: Autonomous-driving target that hires 27卒-equivalents through regular postings; treat as rolling (通年) with per-role 'No matching roles found' checks.
Src: https://woven.toyota/jp/careers/internship/
### RIKEN AIP (理研 革新知能統合研究センター) researcher postings [low]
10-11 open Research Scientist / Postdoctoral Researcher positions (posting IDs e.g., 26-1238 Geoinformatics, 26-1237 Computational Physics ML, 26-938 Dynamical Systems Learning, 26-595 Robot Learning, 26-372 AI Security and Privacy). These are fixed-term (任期制) PhD-level research posts, rolling, not 新卒 tracks; also 'collaboration program for overseas students'.
Read-only access: Public HTML https://aip.riken.jp/careers/ linking to https://www.riken.jp/en/careers/researchers/ ; RIKEN also posts to JREC-IN Portal (jrecin.jst.go.jp, which has RSS/email alerts).
Notes: Relevant only if the user pursues a PhD/postdoc path; for 修士 graduates, RIKEN offers 研究パートタイマー/テクニカルスタッフ roles. Special Postdoctoral Researcher (SPDR) has annual spring deadlines.
Src: https://aip.riken.jp/careers/
### NTT研究所 (NTT R&D) 新卒 research hiring [medium]
Could not be verified this session: https://www.rd.ntt/recruit/ and https://group.ntt/jp/recruit/ returned 404, and https://www.rd.ntt/ has no recruit link. From general knowledge (unverified): 研究職 is hired through NTT持株会社 新卒採用 on the standard 大手 calendar (ES ~Mar-Apr, 面接 Apr-Jun, 内々定 by June), with 博士 candidates also hired via research-lab-specific/通年 routes.
Read-only access: none confirmed; find the current 新卒 MyPage via NTT持株 採用サイト (likely an i-web/業務委託 domain) and record its sender domain once known.
Notes: Open question for the user; 27卒 window is almost certainly closed - check for 博士/ジョブ型 通年 postings.
Src: https://www.rd.ntt/
### Consulting and finance 新卒 timing in Japan (MBB, Big4/アクセンチュア, 外資IB) [medium]
McKinsey Japan (application-process-for-undergrads-2026 page) timed out twice; BCG global page had no Japan specifics; Accenture Japan campus URL 404. From general knowledge (unverified this session): MBB Japan run fixed rounds tied to internships - 夏選考 (apply May-Jun of 3rd year), 秋選考 (Sep-Oct), 冬選考 (Dec-Jan) - so 27卒 rounds ended by ~spring 2026 and current rounds are 28卒. Foreign IB (GS/MS/JPM Japan): summer internship → 本選考 Sep-Nov of 3rd year (27卒 finished autumn 2025). Big4/アクセンチュア/アビーム/日系コンサル run multiple 本選考 rounds through the year and some accept 27卒 into 秋採用 (aggregators list アクセンチュア, デロイト トーマツ サイバー, アビーム - the type就活 entries for the latter two show 終了).
Read-only access: Official pages: https://www.mckinsey.com/jp/careers/careers-in-japan/application-process-for-undergrads-2026 (slow), https://careers.bcg.com/locations/japan/graduates ; 外資就活ドットコム deadline feed (login-gated); ONE CAREER public list.
Notes: For the user, consulting AI roles are more likely via 秋採用 at Big4/Accenture (AI/データサイエンティスト courses) than MBB. Verify each on the official page; store as 待核実.
Src: https://www.mckinsey.com/jp/careers/careers-in-japan/application-process-for-undergrads-2026
### 留学 → 技術・人文知識・国際業務 在留資格変更 timing (出入国在留管理庁) [high]
ISA official: '４月からの就労を希望する場合、１２月１日から１月末までの間に申請をしていただくようお願いします' → for 27卒 the filing window is 2026-12-01 to 2027-01-31 (submit 卒業見込証明書 + 内定通知/雇用契約書). After graduation: '卒業証明書を受け取った後に必要書類を持参して地方出入国在留管理局にお越しいただき、資格変更後の在留カードを受け取る'. Since 2025-12-01: document omission (カテゴリー2相当) for 本邦の大学卒業(予定)者, 海外優秀大学(世界ランキング上位300)卒業者, and firms already employing 留学→就労 converts (派遣 excluded). Since 2026-04-15 (令和8年4月15日以降の申請): カテゴリー3/4 employers must add 所属機関の代表者に関する申告書 and, for language-heavy roles, CEFR B2 proof (本邦大学卒 = deemed B2 Japanese). 在留期間 granted: 5年/3年/1年/3月. Processing 2週間〜2か月 (Dec-May is peak).
Read-only access: Public HTML https://www.moj.go.jp/isa/10_00240.html and https://www.moj.go.jp/isa/applications/status/gijinkoku.html ; ISA sends no email - track as manual milestones.
Notes: App should create 3 dated tasks once an offer is accepted: 2026-11 gather documents; 2026-12-01 file 在留資格変更; graduation (2027-03) → collect new 在留カード. Startups/labs are often カテゴリー3/4 → longer document list. Fee (general knowledge, verify): 6,000円 窓口 / 5,500円 オンライン since 2025-04-01. For an October 2027 start (e.g., Rakuten Oct entry) the student needs 特定活動(内定待機) after graduation - knowledge-based, confirm with 入管/大学.
Src: https://www.moj.go.jp/isa/10_00240.html
### 特定活動 (継続就職活動) after graduation without an offer [high]
ISA: graduates of 大学/大学院/短大/高専/専修学校専門課程 may change from 留学 to 特定活動 to continue job hunting if the school recommends them and they were already actively job hunting before graduation. 在留期間 6月, one renewal → 最長1年 after graduation. Requirements: 卒業した学校の推薦状, evidence of continuous 就職活動, 経費支弁能力. 資格外活動許可 possible (週28時間以内; can exceed for internship-type activity with permission). 2nd year possible only via 地方公共団体の就職支援事業 participation (特定活動 6月 + 1 renewal). Once an offer is obtained, change to 技術・人文知識・国際業務.
Read-only access: Public HTML https://www.moj.go.jp/isa/applications/resources/nyukan_nyukan84.html ; manual milestone only.
Notes: Safety net for a 27卒 still active in Jan-Mar 2027: the app should surface '大学推薦状を依頼' and '就活実績の記録 (応募ログ = evidence)' as tasks around 2027-02 if no 内定承諾 exists. Job-hunting activity logs kept by the app double as 入管 evidence.
Src: https://www.moj.go.jp/isa/applications/resources/nyukan_nyukan84.html
### Japan 新卒 selection-stage taxonomy + assessment vendors (pipeline enum) [high]
Canonical stage order: プレエントリー (MyPage登録) → 説明会/座談会 → 本エントリー/ES提出 → 適性検査・Webテスト → コーディングテスト/技術課題 → 録画面接/動画選考 → グループディスカッション(GD) → 一次面接 → 二次面接 (技術面接/研究プレゼン for research track; ジョブマッチング面談 at Sony) → 最終面接 (役員面接) → 内々定 → オファー面談/条件面談 → 内定承諾 (内定承諾書・誓約書提出) → 正式内定 (内定式 10/1, 内定通知書) → 内定者フォロー → 入社. Webテスト vendors and delivery domains: SPI3 (リクルートMS; テストセンター/WEBテスティング; arorua.net), 玉手箱/GAB/CAB/Web-CAB (日本SHL; e-exams.jp), TG-WEB (ヒューマネージ; c-personal.com, e-gitest.com; often bundled with i-web MyPage), SCOA (NOMA), CUBIC, TAL, eF-1G, GPS, 3E-IP. Coding-test platforms: Track (tracks.run), HireRoo (hireroo.io), paiza (paiza.jp), Codility, HackerRank, CodeSignal, company-hosted 技術課題 (Mercari). Video: HireVue, harutaka, インタビューメーカー. Confirmed flows: PFN = 書類選考 → コーディングテスト → 面接(複数回) → 内定; Mercari = 書類選考 → 技術課題 → 面接.
Read-only access: Stage detection from Gmail subject lines and sender domains (read-only); vendor domains above are notification senders (arorua.net returned 403 to bots but resolves; e-exams.jp / c-personal.com did not resolve at www. - verify exact hosts from real emails).
Notes: Mapping to the design doc's pipeline: 已申请 ⊇ {プレエントリー, ES提出}; 笔试或课题 ⊇ {Webテスト, コーディングテスト, 録画面接}; 面试中 ⊇ {GD, 一次, 二次, 最終}; Offer ⊇ {内々定, オファー面談, 内定承諾, 内定}. Keep 内々定 (pre-10/1, informal) distinct from 内定 (10/1以降, formal) and from 内定承諾 (user's acceptance). Research-track extras: 研究概要書, 推薦書, 研究プレゼン, リファレンス.
Src: https://www.preferred.jp/ja/news/pr20260203
### 新卒 salary expression and the job model's salary_basis field [high]
Japanese 新卒 comp is expressed in several incompatible bases: (1) 初任給 月給 by degree - e.g., Sony 2026年度 博士 383,000円〜 / 修士 363,000円〜 / 学部 333,000円〜 (月給), 賞与 年1回 separate; (2) 月給 with 固定残業代/みなし残業 - e.g., Mercari '月給 300,000円 = 基本給 221,965円 + 45時間分の固定残業代 78,035円', 賞与 3月・9月; (3) 年俸制 (annual, paid /12 or /14; foreign firms, consulting, some startups; may or may not include 賞与); (4) 想定年収/理論年収/モデル年収 ranges (e.g., 年収 500万〜800万円) which usually include 賞与 and sometimes 見込み残業; (5) 裁量労働制 (専門業務型 for 研究開発職; 'X時間労働したものとみなす', 裁量労働手当; often not applied to new grads in year 1) or 高度プロフェッショナル制度; (6) foreign-firm packages: base 年収 + 業績賞与 + RSU + サインオン; (7) intern 時給/日給. Legal disclosure rule (職業安定法 5条の3 + 指針, in force since 2018-01-01; from general knowledge, MHLW page could not be fetched): when 固定残業代 is included, the posting must show (a) 固定残業代を除いた基本給の額, (b) 固定残業代の金額と充当する労働時間数, (c) 超過分は追加で割増賃金を支払う旨. Since 2024-04-01, 就業場所・業務の変更の範囲 must also be disclosed.
Read-only access: Parsed from official 募集要項 pages (public HTML), 労働条件通知書/内定通知書 PDFs the user uploads, or オファー面談 notes (manual).
Notes: Recommended salary_basis enum: monthly_starting_by_degree (初任給 月給, 学部/修士/博士), monthly_incl_fixed_overtime (月給・固定残業代込み; store fixed_ot_hours, fixed_ot_amount, base_wage), annual_salary_system (年俸制; store payments_per_year, bonus_included), model_annual_income (想定年収/理論年収; store bonus_included, overtime_included), discretionary_labor (裁量労働制; store deemed_hours), hourly (時給), unknown. Companion fields: degree_tier, bonus_frequency (年1回/年2回/なし), fiscal_year_of_figure (e.g., 2026年度実績), currency, allowances (住宅/通勤). Normalise to an estimated 年収 for sorting but always display the original basis.
Src: https://careers.mercari.com/jp/students/
### 内定承諾期限, 内定辞退 and オワハラ norms [high]
General practice (knowledge-based; no single official source fetched this session): after 内々定 a company sets a 承諾期限 (返答期限) typically 1〜2週間 (startups sometimes 3日〜1週間; large firms often allow 保留 until the candidate's other 最終面接 or until 6月上旬 / at latest before 内定式 10/1). Candidates commonly ask for 保留 once. 内定承諾書/入社誓約書 has no legal binding on the student; legally 内定 is a 始期付解約権留保付労働契約 and the student may withdraw (内定辞退) until 2 weeks before 入社日 under 民法627条 (courtesy norm: notify promptly, by phone + email). The government 要請 explicitly asks firms to prevent ハラスメント (オワハラ = pressure to end job hunting), and the 内閣官房 資料 flags 'ルールを遵守しようとする企業' losing candidates. 内定式 is conventionally held on 10月1日 (2026-10-01, Thursday); 26卒 Recruit data shows 内定辞退率 tracked monthly (10/1 report includes 内定式 実施状況 by 従業員規模/形式).
Read-only access: From Gmail subject patterns like 「内定承諾書のご提出について」「内々定のご連絡」「ご回答期限」 and 内定通知書 PDFs; Recruit 就職プロセス調査 for aggregate 辞退率 (public HTML).
Notes: App fields: naitei_date, acceptance_deadline (返答期限), hold_requested (保留申請), acceptance_date (承諾日), formal_naitei_date (10/1), withdrawal_notice_date. Default reminder: 3 days before 返答期限. For 秋採用 offers expect shorter deadlines (days, not weeks).
Src: https://www.cas.go.jp/jp/seisaku/shushoku_katsudou_yousei/2027nendosotu/index.html
### Gmail sender-domain and subject-line patterns for 新卒 ATS / 就活サイト (read-only ingestion) [high]
Sender domains seen or standard in Japan 新卒 hiring: 就活 platforms - mynavi.jp (job.mynavi.jp), rikunabi.com, onecareer.jp, gaishishukatsu.com, offerbox.jp, typeshukatsu.jp, career-tasu.jp, br-campus.jp (ビズリーチ・キャンパス), wantedly.com, labbase.jp (research scouting), acaric.jp (大学院生), techoffer.jp, paiza.jp; company ATS/MyPage - i-web.jp / *.i-webs.jp (ヒューマネージ; many 大手 MyPages incl. Sony's outsourced recruit.sony.co.jp), sonar-ats (Thinkings), herp.cloud / herp.careers, hrmos.co, talent-clip, jobcan; global ATS - myworkdayjobs.com / myworkday.com (Sony AI), jobs.lever.co / hire.lever.co (Woven by Toyota), greenhouse (no-reply@us.greenhouse-mail.io), ashbyhq.com, smartrecruiters.com, icims.com, amazon.jobs; direct - preferred.jp, careers@sakana.ai (hiring-target contact address). Assessment senders: arorua.net (SPI3), e-exams.jp (玉手箱/GAB), c-personal.com / e-gitest.com (TG-WEB), tracks.run, hireroo.io, hirevue.com. Typical Japanese subjects: 「【会社名】選考結果のご連絡」「選考結果について」「一次面接のご案内」「面接日程調整のお願い」「Webテスト受検のご案内」「適性検査受検のお願い」「エントリーシート受付完了」「マイページ登録完了のお知らせ」「【重要】内々定のご連絡」「内定通知書送付のご案内」「オファー面談のご案内」「内定承諾書のご提出について」「エントリー締切迫る」; English: 'Application received', 'Interview invitation', 'Coding assessment invitation', 'Next steps', 'Offer letter'. Calendar: 面接/面談/選考 events with Google Meet/Zoom/Teams links, JST.
Read-only access: Gmail read-only OAuth (gmail.readonly) query e.g. from:(i-web.jp OR myworkdayjobs.com OR lever.co OR onecareer.jp) OR subject:(選考 OR 面接 OR 内々定 OR 内定 OR Webテスト OR 適性検査 OR エントリー); Calendar read-only for 面接 events. Vendor host names partly from general knowledge - confirm from real headers.
Notes: Stage classifier keywords → stage: 受付完了/登録完了 → 已申请; 受検/適性検査/コーディング/課題 → 笔试或课题; 面接/面談/GD/グループディスカッション → 面试中 (extract 一次/二次/最終); 内々定/内定/オファー/承諾 → Offer; お見送り/ご縁がなかった/今回は残念ながら → 已落选. Never auto-create links when the mail says オンライン面接 without a URL (per design doc).
Src: https://ai.sony/joinus/jobroles/

## Concrete details
  - Official 27卒 milestones (内閣官房 要請 2026-03-24): 広報活動 2026-03-01以降; 採用選考活動 2026-06-01以降; 正式内定 2026-10-01以降 (内定式 conventionally 10/1 = Thursday 2026-10-01).
  - Exception text: 専門活用型インターンシップ（２週間以上）で春休み以降に実施されるもの → 高い専門的知識や能力を有すると判断された学生 may enter 採用選考プロセス before 6月.
  - Reality (内閣官房 R7.12.26 資料 / 文科省調査): 広報を2月以前に開始 約6割; 選考を5月以前に開始 約7割; 5月以前に内々定 約6割. 就職白書2026: 卒業前年2月までに内々定出し開始 41.4% (2026卒) vs 1.2% (2017卒).
  - 27卒 内定率 (Recruit 就職みらい研究所, 大学生): 2026-02-01 32.8%; 03-01 38.1%; 05-01 67.0%; 06-01 77.2% (文系 75.1 / 理系 81.1; 進路確定率 57.3%). Mynavi 内々定率 8月末 85.6% (理系男子 89.3). 学情/日経 7月末 84.8%, 就職活動率 27.9% (2026-08-05). 26卒 benchmark 9/1: 内定率 94.8%, 就職活動実施率 11.5%.
  - 秋採用 cadence: applications Sep-Nov (peak after 10/1 内定式 when 内定辞退 frees seats), 冬採用 Dec-Feb; typical 2-3 interviews and result within 1-2 weeks; pools shrink from thousands to hundreds of applicants.
  - PFN 2027年入社: プレエントリー 2025-09-01; 第1期 2025-11-04; 第2期 2025-12-01; 第3期 2025-12-25; 第4期 2026-02-03, 締切 2026-02-28 (土) 23:59; '第4期締切終了後は、随時採用サイトにて更新'; 2028年入社 プレエントリー opened 2026-09-01 (preferred.jp/ja/news/pr20260901-0). Flow: 書類選考 → コーディングテスト → 面接(複数回) → 内定.
  - Rakuten: 'Applications for October 2027 Entry are now open' posted 2026-09-01 at global.rakuten.com/corp/careers/graduates/ (April 2027 entry opened 2026-01-13).
  - Mercari: 通年採用, 入社 毎年4月・10月, target now '2028年4月以降に入社が可能な16歳以上の学生'; 月給例 300,000円 = 基本給 221,965円 + 45時間分の固定残業代 78,035円; 賞与 3月・9月; flow 書類選考 → 技術課題 → 面接.
  - Sony 27卒: ジョブマッチング募集 2026-03-01〜03-09; 応募資格 '2027年4月時点で、最終学歴卒業後3年未満'; 初任給 2026年度 月給: 博士 383,000円〜 / 修士 363,000円〜 / 学部 333,000円〜; 賞与 年1回; 2028卒 MyPage https://www.recruit.sony.co.jp/2028/.
  - Closed for 27卒 (official): LINEヤフー ('2027年度新卒採用のエントリー受付は終了しました'), AWS Japan SA (now 2028年卒 本選考 via amazon.jobs/jp/jobs/10503564/...), Sony ジョブマッチング (Mar 2026), PFN 第4期 (Feb 2026).
  - Rolling/no-新卒-program employers and their intake channels: Sakana AI (careers@sakana.ai + https://forms.gle/NFE3U5XoiYLWhnH48; 23 roles incl. Applied Research Engineer (Product), Forward Deployed Engineer (GTM), SWE (R&D), MTS (LLM Development)); Sony AI (Workday sonyglobal.wd1.myworkdayjobs.com/SonyJapanCareers; internships only, PhD/MSc enrolled); Woven by Toyota (Lever jobs.lever.co/woven-by-toyota; interns must graduate before 2028-03); RIKEN AIP (riken.jp/en/careers/researchers/, posting IDs like 26-1238; PhD fixed-term).
  - Visa (ISA): for April start, file 留学→技術・人文知識・国際業務 '１２月１日から１月末までの間' → 2026-12-01 to 2027-01-31; bring 卒業証明書 after graduation to receive the new 在留カード; document omission for 本邦の大学卒業(予定)者 since 2025-12-01; カテゴリー3/4 extra documents (代表者申告書, CEFR B2 proof for language roles) for applications from 2026-04-15; 在留期間 5年/3年/1年/3月.
  - No offer by graduation: 特定活動(継続就職活動) 6か月 + 1回更新 = 最長1年 (大学推薦状 + 就活実績 + 経費支弁; 資格外活動 週28時間); 2nd year only through 地方公共団体 就職支援事業.
  - Japan-aware stage enum: プレエントリー → 説明会 → ES提出 → Webテスト(SPI3/玉手箱/TG-WEB/SCOA) → コーディングテスト → 録画面接 → GD → 一次面接 → 二次面接(技術/研究プレゼン) → 最終面接(役員) → 内々定 → オファー面談 → 内定承諾 → 内定(10/1) → 入社; map to design-doc statuses 已申请/笔试或课题/面试中/Offer.
  - Assessment/ATS notification domains (verify from real headers): arorua.net (SPI3), e-exams.jp (玉手箱/GAB/CAB), c-personal.com / e-gitest.com / i-web.jp / *.i-webs.jp (TG-WEB, i-web MyPage), tracks.run, hireroo.io, paiza.jp, myworkdayjobs.com, lever.co, greenhouse-mail.io, ashbyhq.com, amazon.jobs, herp.cloud, hrmos.co, mynavi.jp, rikunabi.com, onecareer.jp, gaishishukatsu.com, offerbox.jp, labbase.jp, acaric.jp.
  - Subject-line patterns: 「【会社名】選考結果のご連絡」「一次面接のご案内」「面接日程調整のお願い」「Webテスト受検のご案内」「適性検査受検のお願い」「エントリーシート受付完了」「マイページ登録完了」「内々定のご連絡」「内定通知書」「オファー面談のご案内」「内定承諾書のご提出について」; rejection cues 「お見送り」「ご縁がなかった」「今回は残念ながら」.
  - Salary bases to support: 初任給 月給 by degree (学部/修士/博士); 月給 = 基本給 + 固定残業代 (must disclose hours + amount + 超過分支払い, 職業安定法 rule since 2018-01-01); 年俸制; 想定年収/理論年収 (賞与込み); 裁量労働制 (専門業務型, deemed hours); foreign-firm base 年収 + RSU + サインオン; intern 時給. Since 2024-04-01 postings must also show 就業場所・業務の変更の範囲.
  - 内定承諾 norms (general practice): 返答期限 typically 1-2 weeks after 内々定 (days at startups/秋採用), 保留 commonly granted once, 承諾書 not legally binding, 内定辞退 possible until 2 weeks before 入社 (民法627条); government 要請 asks firms to prevent オワハラ.
  - Public trackers to poll: shushokumirai.recruit.co.jp/research/ (URL pattern research_article/YYYYMMDD001/; 27卒 9/1 report expected mid-Sept 2026, 10/1 ~Oct 9, 12/1 ~Dec 15); career-research.mynavi.jp/column/20260317_108783/ (monthly); onecareer.jp/events/selection/graduate_year/2027 (sortable by 締切日; scrape-only).

## Recommendation
1) Encode the 27卒 calendar as fixed milestones (2026-03-01 / 2026-06-01 / 2026-10-01 内定式, 2026-12-01〜2027-01-31 visa filing window, 2027-02 特定活動 fallback prep) and treat 2026-09-16 as 'late cycle': default every new opportunity to 待核実 and require an official-page check (LINEヤフー already contradicts aggregators). 2) Maintain three opportunity classes with different verification logic: (a) 新卒 秋採用/追加募集 (dated 締切, expect fast 1-2 week decisions; poll ONE CAREER/公式 pages), (b) 通年採用/second-intake 新卒 windows (Rakuten October 2027 Entry - open now; Mercari 4月/10月 - confirm 27卒 eligibility), (c) rolling non-新卒 postings at AI labs and auto/robotics firms (Sakana AI, Sony AI, Woven by Toyota, PFN キャリア採用, RIKEN AIP) where '確認在招' means the specific posting is live today and the role does not require prior internship. 3) Implement the Japan-aware stage enum as sub-stages under the design doc's 已申请/笔试或课题/面试中/Offer, keeping 内々定, 内定承諾 and 内定(10/1) distinct, and add acceptance_deadline + hold_requested fields with a 3-day-before reminder. 4) Model salary with a salary_basis enum (monthly_starting_by_degree, monthly_incl_fixed_overtime, annual_salary_system, model_annual_income, discretionary_labor, hourly, unknown) plus degree_tier, fixed_ot_hours/amount, bonus_included/frequency, fiscal_year; normalise to estimated 年収 only for sorting. 5) For Gmail read-only ingestion, seed sender-domain and subject-keyword rules listed above, and let the self-hoster configure their own employer domain(s) as an exclusion list for inbound-recruiter classification. 6) Poll Recruit 就職プロセス調査 and Mynavi monthly pages for the 27卒 9/1, 10/1, 12/1 figures to display 'market pressure' context, not as probabilities.

## Open questions
  - Recruit 就職みらい研究所 27卒 2026-09-01 内定率/就職活動実施率 was not yet published at fetch time; confirm when it appears (26卒 equivalent was released 2025-09-09).
  - Will PFN run any 2027年入社 追加募集/第5期 (page says 随時更新) or accept a 2027年10月 start via キャリア採用? No announcement as of 2026-09-16.
  - Rakuten 'October 2027 Entry' - exact eligibility wording for 2027年3月卒業 students and whether the company sponsors the Apr-Oct 2027 gap (特定活動 内定待機) - unverified.
  - Mercari student page now targets 2028年4月以降入社 - does 通年採用 still accept a 27卒 for 2027年10月入社?
  - NTT研究所 新卒/博士 hiring page could not be located (rd.ntt/recruit and group.ntt/jp/recruit returned 404); current entry point and any 通年 博士 route unverified.
  - McKinsey/BCG/Accenture Japan pages could not be fetched (timeout/404/generic); 27卒 秋採用 availability at Big4/Accenture AI tracks is aggregator-claimed only.
  - Official MHLW page for the 固定残業代 display rule (職業安定法 指針) could not be fetched (multiple 404s); rule stated from general knowledge - verify wording before hard-coding validation.
  - 特定活動(内定待機) for post-graduation offers, and the 在留資格変更 手数料 (6,000円 窓口 / 5,500円 オンライン since 2025-04-01) are from general knowledge, not verified this session.
  - Exact assessment-vendor email hosts (arorua.net returned 403; www.e-exams.jp and www.c-personal.com did not resolve) should be confirmed from real message headers in the user's mailbox.
  - Region pack / settings should support an 'own employer' domain list so that internal-transfer mail is classified separately from external applications.
  - Whether the user is 修士 or 博士 track and graduation month (2027-03 vs 2027-09) - affects Sony's 卒業後3年未満 eligibility, PFN 2028 pre-entry relevance, and the visa filing window.
  - The 28卒 rule review (関係省庁連絡会議 R7.12.26 考え方) may change dates for later cohorts; irrelevant to 27卒 but worth a note if the app is reused.

## Sources
- 内閣官房 2027（令和9）年度卒業・修了予定者等の就職・採用活動に関する要請 (index): https://www.cas.go.jp/jp/seisaku/shushoku_katsudou_yousei/2027nendosotu/index.html
- 内閣官房 要請文 別添1 (令和8年3月24日) PDF: https://www.cas.go.jp/jp/seisaku/shushoku_katsudou_yousei/2027nendosotu/2027betten1.pdf
- 内閣官房 2027年度卒業・修了予定者の就職・採用活動日程に関する考え方 (令和7年12月26日) PDF: https://www.cas.go.jp/jp/seisaku/shushoku_katsudou/pdf/r071226_siryou.pdf
- 就職みらい研究所 就職プロセス調査 index: https://shushokumirai.recruit.co.jp/research/
- 就職みらい研究所 2027年卒 就職内定率調査 (2026年6月1日時点): https://shushokumirai.recruit.co.jp/research_article/20260706001/
- 就職みらい研究所 2027年卒 就職内定率調査 (2026年3月1日時点): https://shushokumirai.recruit.co.jp/research_article/20260327001/
- 就職みらい研究所 就職プロセス調査（2026年卒）2025年9月1日時点: https://shushokumirai.recruit.co.jp/research_article/20250909001/
- 就職みらい研究所 就職白書2026: https://shushokumirai.recruit.co.jp/white_paper_article/20260220001/
- マイナビ キャリアリサーチLab 2027年卒 就職内定率の状況 (monthly): https://career-research.mynavi.jp/column/20260317_108783/
- アルク 27卒9月最新 内定状況 (secondary; cites 学情/日経 84.8% and 26卒 9/1 94.8%): https://www.alc.co.jp/job-change/newgrad-nnt/
- 就活エンジン 27卒 秋採用を行う大手企業一覧 (updated 2026-09-08): https://shukatsu-engine.com/autumn-recruitment-oote/
- 就活マップ まだ間に合う新卒採用 27卒 (updated 2026-08-31): https://noahs-ark.co.jp/maniau-entry/
- ONE CAREER 27年卒 本選考一覧: https://www.onecareer.jp/events/selection/graduate_year/2027
- type就活 2027卒向け募集要項一覧: https://typeshukatsu.jp/recruitment/year-2027/
- 外資就活ドットコム (top; deadline list login-gated): https://gaishishukatsu.com/
- 人事ZINE 2027年卒の就活解禁日: https://offerbox.jp/company/jinji-zine/open-date/
- リクナビ 2027年卒 就活スケジュール: https://job.rikunabi.com/contents/schedule/26579/
- PFN 新卒採用 news tag: https://www.preferred.jp/ja/news/tag/149
- PFN 2027年入社 第4期 新卒採用 募集開始: https://www.preferred.jp/ja/news/pr20260203
- PFN 2027年入社 第1期 新卒採用 募集開始: https://www.preferred.jp/ja/news/pr20251104
- PFN careers news category (2028年入社 プレエントリー 2026-09-01): https://www.preferred.jp/ja/news/category/careers
- Sakana AI Careers: https://sakana.ai/careers/
- Sony AI Job Roles: https://ai.sony/joinus/jobroles/
- ソニー株式会社 新卒採用: https://www.sony.co.jp/recruit/newgrads/
- ソニーグループ 2027 joint MyPage: https://www.recruit.sony.co.jp/2027/
- Rakuten Graduates: https://global.rakuten.com/corp/careers/graduates/
- Mercari Students (新卒採用): https://careers.mercari.com/jp/students/
- LINEヤフー 新卒採用: https://www.lycorp.co.jp/ja/recruit/newgrads/
- AWS Japan 新卒 Solutions Architect: https://aws.amazon.com/jp/careers/newgraduate/solutionsarchitect
- Woven by Toyota Internship: https://woven.toyota/jp/careers/internship/
- Woven by Toyota Careers: https://woven.toyota/jp/careers/
- RIKEN AIP Careers: https://aip.riken.jp/careers/
- 出入国在留管理庁 在留資格「留学」から就労資格への変更申請を予定されている皆様へ: https://www.moj.go.jp/isa/10_00240.html
- 出入国在留管理庁 在留資格「技術・人文知識・国際業務」: https://www.moj.go.jp/isa/applications/status/gijinkoku.html
- 出入国在留管理庁 大学等を卒業後就職活動のための滞在をご希望のみなさまへ (特定活動): https://www.moj.go.jp/isa/applications/resources/nyukan_nyukan84.html
- 厚生労働省 2024年4月から労働条件明示のルールが変わります: https://www.mhlw.go.jp/stf/newpage_32105.html
- McKinsey Japan application process for undergrads 2026 (timed out): https://www.mckinsey.com/jp/careers/careers-in-japan/application-process-for-undergrads-2026
- Mita JobPilot design baseline (local): ../ref/gpt_design.txt
