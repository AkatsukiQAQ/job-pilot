# 岗位搜索来源（全球 + 日本）

> **AI 调研附录**（生成于 2026-09-16，英文）。内容由并行调研 agent 对照官方页面整理，verified/unverified 标注以原文为准；实现前需再次核对。相关更正见 japan-critique.md 与 proposal-judgments.md。

# Programmatic job-search sources for a personal, read-only job-search assistant (global + Tokyo tech market), as of 2026-09-16

## Summary
Feasible, ToS-clean, free, read-only ingestion exists at three layers. (1) Company-watch via official, unauthenticated ATS job-board endpoints: Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee, Personio (XML), Teamtailor (RSS) and Rippling all publish keyless JSON/XML/RSS for any customer's public board; I verified live responses for Greenhouse (stripe), Lever (spotify), Ashby (ashby), SmartRecruiters (smartrecruiters), Teamtailor (career.teamtailor.com/jobs.rss) and Rippling (rippling). (2) Keyword search via a small set of free aggregator APIs: Adzuna (official limits 25/min, 250/day, 1000/week, 2500/month; ~19 countries, no Japan; snippet-only descriptions; mandatory "Jobs by Adzuna" attribution) and JSearch/OpenWeb Ninja (Google-for-Jobs scrape resold as an API; free 200 requests/month; supports country/language codes so Japan is reachable), plus Jooble (free key per country incl. ja.jooble.org, but a 500-request lifetime cap per key). (3) Free remote-job APIs with attribution terms: Remotive (max 4 calls/day, 24h publication delay), Himalayas (JSON + RSS, 24h cache), Jobicy (poll <=1/hour), RemoteOK (legal notice in first array element), Arbeitnow (no key, no documented limits), The Muse (500 req/h without key). Not feasible: Indeed (Publisher API closed; docs.indeed.com is partner-only employer-side GraphQL; RSS disallowed in robots.txt), LinkedIn (no job-search API; Job Posting API closed to new partners; robots.txt bans all automated access; User Agreement 8.2.2 bans scraping), Glassdoor (help center: "no longer supports API partnerships"), Google Jobs direct (Cloud Talent Solution is bring-your-own-data; only SERP scrapers like SerpApi, free 250/month). Japan-specific boards (Wantedly, Green, Bizreach, doda, Rikunabi NEXT, Indeed JP) offer no listings API; their ToS restrict reuse beyond private use (Wantedly explicitly bans scraping and ingestion into AI models; Bizreach robots blocks GPTBot/ClaudeBot/anthropic-ai on /jobs/), so the read-only-compliant path for those is parsing the alert/scout emails they already send to the user's Gmail. TokyoDev and Japan Dev are the two Tokyo tech boards that are robots-permissive with full sitemaps (~550 Japan Dev job URLs; TokyoDev /companies/{slug}/jobs/{slug}) and schema.org JobPosting JSON-LD on job pages, making polite daily sitemap-diffing low risk. HelloWork has an official XML API but it is restricted to municipalities and licensed placement agencies (paper application), so it is not usable by an individual. A normalized schema keyed on (source, source_id) with a blocking key sha1(company_norm|title_norm|country|city_or_remote) plus RapidFuzz title similarity and MinHash/SimHash on descriptions handles cross-source dedup; ATS-direct records should win as canonical over aggregator copies whose redirect resolves to an ATS domain.

## Hard constraints
  - Read-only: every recommended source is consumed via GET (or a search POST that creates no server-side state, e.g. Workday cxs, Jooble). Never call ATS application POST endpoints (Greenhouse /jobs/{id} POST, Lever POST /postings/{site}/{id}?key=) and never use Gmail scopes beyond gmail.readonly.
  - No official job-search API exists for individuals from Indeed (Publisher API closed; docs.indeed.com is partner-only employer-side GraphQL: Job Sync, Indeed Apply, Disposition Sync, Sponsored Jobs; access requires a signed Developer Agreement), LinkedIn (Job Posting API 'not accepting new partnerships'; Talent Solutions partners must be incorporated companies), or Glassdoor (help center: 'Glassdoor no longer supports API partnerships'). Indeed Japan and LinkedIn Japan are the same products; Rikunabi NEXT now distributes via Indeed PLUS. Design must not depend on these.
  - Scraping LinkedIn, Indeed, Wantedly, Bizreach, doda, Green is prohibited or restricted by their terms/robots.txt; LinkedIn robots.txt bans all automated access; Wantedly terms ban scraping and ingestion into AI/ML models; Bizreach robots.txt blocks GPTBot/ClaudeBot/anthropic-ai on /jobs/. For these, ingest only what arrives in the user's own Gmail.
  - Google Cloud Talent Solution is NOT a job source (you upload your own jobs); Google for Jobs has no public API - only third-party SERP scrapers (SerpApi, JSearch).
  - Adzuna: default limits 25/min, 250/day, 1000/week, 2500/month; descriptions are snippets; 'Jobs by Adzuna' attribution (116x23 px, linked) required wherever ads are displayed; one account per individual; do not contact third-party content providers; no Japan market.
  - JSearch free tier is 200 requests/month; Jooble free key is 500 requests lifetime per country key; Remotive max 4 calls/day and 2/min block with 24h posting delay; Jobicy max 1 poll/hour with 6h delay; Himalayas 24h cache (RSS ttl=1440); The Muse 500 req/h without key. Poll schedulers must encode these caps.
  - Attribution obligations: Remotive, Himalayas, Jobicy, RemoteOK require naming the source and linking the original URL (RemoteOK: dofollow, no redirects, no logo) and forbid re-posting to other job boards. Store attribution_required/attribution_text per source and render it in the UI.
  - Workday cxs endpoint hard-caps limit at 20 and returns an empty jobPostings array (HTTP 200) for larger limits; total may only be present on the first page; tenant/site/wdN must be taken from the real careers URL.
  - HelloWork's official API is restricted to municipalities and licensed placement agencies; not obtainable by an individual.
  - Playwright/HTML scraping is only for public, login-free pages; honor robots.txt (Protego), use a descriptive User-Agent, never create accounts or bypass Cloudflare/CAPTCHA (that conduct is what produced hiQ's $500k judgment).
  - Multilingual normalization required: Japanese postings use full-width characters and company suffixes 株式会社/合同会社/(株); apply NFKC before hashing; keep a language field (en/ja/zh) per posting.

## Recommendation
v1 (free, ToS-clean, all official or robots-permitted, ~1-2 weeks): (a) Company watchlist connector using official keyless ATS endpoints - Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee, Personio XML, Teamtailor RSS, Rippling - with an ATS auto-detector that inspects a careers URL/HTML for boards.greenhouse.io, jobs.lever.co, jobs.ashbyhq.com, jobs.smartrecruiters.com, apply.workable.com, *.recruitee.com, *.jobs.personio.de, *.teamtailor.com, ats.rippling.com; poll every 2-6 h. (b) Keyword discovery via Adzuna (one free key; budget 250 calls/day across saved searches; countries the user cares about, no Japan) plus JSearch free tier (200 req/month, country=jp&language=ja for Tokyo and country=us/gb/etc. for global; use date_posted=week and num_pages=1 to stretch quota). (c) Remote boards daily: Remotive, Himalayas (JSON + RSS), Jobicy, Arbeitnow, RemoteOK, The Muse - with attribution stored and displayed. (d) Tokyo: TokyoDev + Japan Dev daily sitemap diff + JSON-LD parse (2 requests/day + 1 per new job). (e) Japanese boards and LinkedIn/Indeed: Gmail-alert ingestion only (gmail.readonly), which doubles as the 'in-progress process' tracker. Storage: SQLite (single user) with the job_posting/job_canonical/job_sighting/watch_target tables below; scheduler APScheduler; HTTP httpx with ETag/If-Modified-Since and per-source token buckets; robots via Protego; JSON-LD via extruct; dedup via rapidfuzz + datasketch MinHash. v2: Workday cxs and BambooHR careers/list connectors (undocumented but read-only; biggest coverage gain for enterprise targets), Personio search.json, generic career-page monitor with Playwright fallback (robots + per-site ToS check), Jooble on-demand key(s) incl. ja.jooble.org for one-off Japanese queries, SerpApi google_jobs paid tier or JSearch Pro ($25) once quota pinches, HiringCafe only if they publish an official API. Never: scraping LinkedIn/Indeed/Glassdoor/Bizreach/doda/Wantedly/Green, python-jobspy against those sites, HelloWork.

## Options
### Direct ATS public job-board endpoints (official, keyless) [read_only_ok=True, cost=Free, effort=days, risk=none]
Poll each watched company's public board via the ATS vendor's documented unauthenticated endpoint: Greenhouse boards-api, Lever postings v0, Ashby posting-api, SmartRecruiters Posting API, Workable widget API, Recruitee /api/offers, Personio XML feed, Teamtailor /jobs.rss, Rippling board API. Config = one row per company (ats_kind + board identifier).
Pros:
  - Zero auth, zero cost, official docs; GET-only so inherently read-only
  - Full HTML descriptions, stable native IDs, structured location/department/remote/compensation (Ashby, Recruitee, Greenhouse pay_input_ranges, Lever salaryRange)
  - Freshest possible signal (no aggregator delay); ideal for 'track every process I am in' because the user's target companies are known
  - One integration per ATS covers every customer of that ATS
Cons:
  - Requires discovering each company's ATS and board token (from careers-page URL or HTML)
  - Rate limits mostly undocumented (SmartRecruiters: 10 req/s, 8 concurrent, X-RateLimit-* headers); be polite (poll every 2-6 h per board)
  - Only covers companies you enumerate; no keyword discovery
  - Some boards are huge (OpenAI Ashby board >10 MB JSON) - stream/parse incrementally
### Adzuna Jobs API [read_only_ok=True, cost=Free within default limits; higher limits via https://www.adzuna.co.uk/hire/partners/, effort=hours, risk=low]
GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}?app_id=&app_key=&what=&where=&results_per_page=50&max_days_old=&sort_by=date. Instant self-serve key. Also salary histogram/history endpoints.
Pros:
  - Free self-serve key, documented limits (25/min, 250/day, 1000/week, 2500/month)
  - ~19 country markets (gb, us, de, fr, au, ca, in, sg, ...) with geodata and salary analytics
  - Clean JSON with created, salary_min/max, salary_is_predicted, contract_type, redirect_url, category
Cons:
  - No Japan market
  - description is a snippet only; redirect_url goes through Adzuna (traffic-driving design)
  - ToS: must show 'Jobs by Adzuna' (116x23 px, linked) wherever ads are displayed; must not contact third-party content providers; one account per person; organisations only get a 14-day trial before a licence 'may be required'
  - 250/day caps you to roughly 8-10 saved searches x 3 countries x 1-2 polls/day
### JSearch (OpenWeb Ninja, also on RapidAPI) [read_only_ok=True, cost=Free 200 req/month; $25-$150/month paid tiers, effort=hours, risk=low]
Google-for-Jobs aggregate exposed as REST: GET /search?query=&page=&num_pages=&country=jp&language=ja&date_posted=week&work_from_home=&employment_types=&job_requirements=&radius=&exclude_job_publishers=&fields= ; also /job-details, /estimated-salary, /company-job-salary, /search-filters. Header x-api-key (direct) or x-rapidapi-key (base https://jsearch.p.rapidapi.com).
Pros:
  - Widest discovery surface (LinkedIn, Indeed, Glassdoor, ZipRecruiter, company sites as indexed by Google for Jobs) without you scraping those sites
  - Country + language parameters make Tokyo/Japanese-language searches possible
  - Structured job_min_salary/job_max_salary/job_salary_period, job_is_remote, job_posted_at_datetime_utc, apply_options, job_highlights
  - Free tier for prototyping
Cons:
  - Free tier is only 200 requests/month (each 10-result page = 1 request); Pro $25/10k, Ultra $75/50k, Mega $150/200k, PAYG $0.005/req
  - Vendor is scraping Google; ToS exposure sits with vendor but data provenance is indirect and job_id stability across days is not guaranteed
  - No official Japan coverage statement - verify country=jp results quality
### Jooble REST API (per-country keys, incl. Japan) [read_only_ok=True, cost=Free (500 requests lifetime), effort=hours, risk=low]
POST https://{cc}.jooble.org/api/{api_key} (US: jooble.org, JP: ja.jooble.org - jp.jooble.org 301s there) with JSON {keywords, location, radius(0|4|8|16|26|40|80), salary, page, ResultOnPage, SearchMode, companysearch}. Response {totalCount, jobs[{id,title,location,snippet,salary,source,type,link,company,updated}]}.
Pros:
  - Free key via web form; Japan domain exists with Japanese-language form
  - Aggregates many local boards per country
Cons:
  - Free plan reported as 500 requests LIFETIME per key (help-center/third-party sources) - unusable for polling; on-demand only
  - Snippet-only descriptions, free-text salary, link goes to Jooble landing page
  - Separate key per country; POST-only with key in URL path
  - Form asks for company website/phone (aimed at webmasters)
### Free remote-job APIs bundle (Remotive, Himalayas, Jobicy, RemoteOK, Arbeitnow, The Muse) [read_only_ok=True, cost=Free, effort=hours, risk=low]
Remotive GET https://remotive.com/api/remote-jobs?category=software-dev&search=&limit= ; Himalayas GET https://himalayas.app/jobs/api?limit=20&cursor= and /jobs/api/search?q=&country=JP&worldwide= plus RSS https://himalayas.app/jobs/rss ; Jobicy GET https://jobicy.com/api/v2/remote-jobs?count=200&geo=&industry=&tag= ; RemoteOK GET https://remoteok.com/api ; Arbeitnow GET https://www.arbeitnow.com/api/job-board-api?page=N ; The Muse GET https://www.themuse.com/api/public/jobs?page=1&category=&level=&location=&api_key=.
Pros:
  - No auth (Muse key optional), all verified live today, JSON with salary fields (Himalayas minSalary/maxSalary/currency/salaryPeriod; Jobicy salaryMin/salaryMax/salaryCurrency/salaryPeriod; RemoteOK salary_min/max)
  - Good coverage of remote/worldwide roles relevant to a multilingual candidate
  - Arbeitnow has full HTML descriptions and is EU/Germany heavy; Himalayas search supports country filter
Cons:
  - Attribution terms: Remotive/Himalayas/Jobicy require naming the source and linking the original URL and forbid re-posting to Jooble/Google Jobs/LinkedIn; RemoteOK requires a dofollow direct link and bans logo use
  - Rate/poll rules: Remotive max 4 calls/day (>2/min blocked) and 24 h publication delay; Himalayas RSS ttl 1440 min and JSON API 24 h cache (429 on abuse); Jobicy <=1 poll/hour and 6 h publication delay; Muse 500 req/h without key, 3600/h with key; Arbeitnow undocumented
  - Remote-only; little Japan-local content
### SerpApi google_jobs engine (or equivalent SERP wrappers) [read_only_ok=True, cost=Free 250 searches/month; $25-$150/month paid, effort=hours, risk=low]
GET https://serpapi.com/search?engine=google_jobs&q=&location=&hl=ja&gl=jp&next_page_token= (10 results/page; 'start' offset discontinued by Google). Returns jobs_results[{title, company_name, location, via, detected_extensions{posted_at,salary,schedule_type}, job_highlights, apply_options, job_id}].
Pros:
  - Direct Google for Jobs coverage incl. Japan (gl=jp, hl=ja)
  - Vendor handles scraping/CAPTCHA; U.S. 'Legal Shield' on Production tier ($150+)
Cons:
  - Free tier 250 searches/month, 50/h; Starter $25/1000, Developer $75/5000, Production $150/15000
  - Pagination only via next_page_token; 10 results per paid search makes broad monitoring expensive
  - Still fundamentally a Google scrape resold; treat as discovery, not system of record
### Semi-official ATS endpoints (Workday cxs, BambooHR careers/list, Personio search.json, Teamtailor jobs.json) [read_only_ok=True, cost=Free, effort=days, risk=low]
Undocumented-but-stable JSON used by the vendors' own career sites: Workday POST https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs body {"appliedFacets":{},"limit":20,"offset":0,"searchText":""} + GET /wday/cxs/{tenant}/{site}/job/{externalPath}; BambooHR GET https://{slug}.bamboohr.com/careers/list -> {meta:{totalCount},result:[{id,jobOpeningName,departmentLabel,location{city,state},isRemote}]}; Personio GET https://{company}.jobs.personio.de/search.json; Teamtailor /jobs.json.
Pros:
  - Workday alone covers a large share of enterprise careers sites (NVIDIA, Salesforce, Adobe, ...), unreachable otherwise
  - Same read-only GET/POST-search pattern; no login, no writes
Cons:
  - Undocumented: field names drift; Workday silently returns an empty jobPostings array when limit>20 (hard cap 20) and 'total' may appear only on first page; tenant/site/wdN cannot be guessed - extract from the careers URL
  - BambooHR list has no descriptions (second call per job) and no company name in payload; validate slug against ^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$ to avoid host injection
  - No published rate limits; keep to a few requests per minute with browser-like Accept/Referer headers
### TokyoDev + Japan Dev sitemap diff + JSON-LD extraction [read_only_ok=True, cost=Free, effort=days, risk=low]
Daily fetch https://www.tokyodev.com/sitemap.xml (urlset; job URLs /companies/{slug}/jobs/{slug}; no lastmod) and https://japan-dev.com/sitemap.xml -> https://japan-dev.com/cdn/sitemaps/sitemap.xml (~550 job URLs /jobs/{company}/{slug}; no lastmod). Diff URL sets; for new URLs fetch the page once and parse schema.org JobPosting JSON-LD (extruct) for title, hiringOrganization, jobLocation, baseSalary, datePosted, validThrough, employmentType, jobLocationType=TELECOMMUTE.
Pros:
  - The two English-language Tokyo tech boards; both list salary bands, Japanese-level requirement, visa sponsorship, remote policy
  - robots.txt permissive: TokyoDev 'User-agent: * Allow: /' (only /c/, /frames/ disallowed; Amazonbot blocked); Japan Dev disallows only one blog post and one PDF
  - Sitemap diffing = ~2 requests/day plus one per new job; negligible load
Cons:
  - No official API or RSS (tokyodev.com/jobs.rss returns 404); this is light scraping, so check each site's terms page (not verified) and set a descriptive User-Agent
  - No lastmod, so updates to existing postings are invisible without re-fetching pages (re-fetch weekly)
  - JSON-LD presence confirmed for Japan Dev via third-party scraper docs; verify for TokyoDev
### Gmail alert/scout email ingestion for Japanese boards and LinkedIn/Indeed [read_only_ok=True, cost=Free, effort=days, risk=none]
Do not touch Wantedly, Green, Bizreach, doda, Rikunabi NEXT, Indeed JP or LinkedIn programmatically; instead have the user enable job alerts/scout mails on each site and parse those emails via Gmail API scope https://www.googleapis.com/auth/gmail.readonly (filter by from-domain: linkedin.com e.g. jobalerts-noreply@linkedin.com, indeed.com e.g. alert@indeed.com, wantedly.com, bizreach.jp, green-japan.com, doda.jp, rikunabi.com - confirm exact addresses against the user's inbox). Extract title/company/URL from HTML, store as source=gmail_alert.
Pros:
  - Fully compliant: the sites deliver the data to the user voluntarily; no ToS exposure; also captures recruiter scouts and interview-scheduling threads, which is exactly the 'track every process' requirement
  - Covers boards that have no API at all (Bizreach is login-gated; Rikunabi NEXT now distributes via Indeed PLUS)
  - Read-only Gmail scope matches the hard constraint
Cons:
  - Latency = alert cadence (daily/instant per site settings); only what the user's alert criteria cover
  - Email HTML parsing per sender is brittle; needs per-sender templates and a fallback to LLM extraction
  - Requires Gmail OAuth setup (covered by the Gmail integration workstream)
### HiringCafe internal Next.js data route [read_only_ok=True, cost=Free (or Apify actors ~$1.15-1.25 per 1k results), effort=days, risk=medium]
Site moved to https://hiringcafe.com (Next.js). Old POST /api/search-jobs is gone; community tools use GET /_next/data/{BUILD_ID}/index.json?searchState={url-encoded JSON}&page=N with BUILD_ID scraped from page HTML; Cloudflare in front. robots.txt allows /, /jobs/, /job/ but disallows /viewjob/, /company/ and any URL with searchState or page query params.
Pros:
  - Aggregates ~2.8M postings from 46 ATS platforms with AI-enriched fields (seniority, visa, salary)
  - Sitemaps for jobs are published in robots.txt (six sitemap files) - sitemap-based discovery is robots-permitted
Cons:
  - No official API or developer terms; the search data route is explicitly disallowed by robots.txt (searchState/page params) and protected by Cloudflare (residential proxies needed per Apify vendors)
  - BUILD_ID changes each deploy; high maintenance
  - Duplicates what direct ATS polling already gives you for known companies
### Direct scraping of LinkedIn / Indeed / Glassdoor / Wantedly / Green / doda / Bizreach (python-jobspy, Playwright) [read_only_ok=True, cost=Free software; proxies $ if you try to scale, effort=days, risk=high]
python-jobspy (PyPI, Python>=3.10) scrapes indeed, linkedin, zip_recruiter, google, glassdoor, bayt, naukri, bdjobs with proxy rotation; Playwright could drive Japanese boards. Included only to document why it is excluded.
Pros:
  - Broadest raw coverage
  - Off-the-shelf library exists
Cons:
  - LinkedIn robots.txt: 'The use of robots or other automated means to access LinkedIn without the express permission of LinkedIn is strictly prohibited'; disallows /jobs-guest/, /api/jobPostings/, /jsearch; User Agreement 8.2.2/8.2.13 bans scrapers and bots (hiQ ended with a $500k judgment on contract/trespass claims despite the CFAA win)
  - Indeed Developer Agreement bans scraping/permanent copies; jp.indeed.com robots disallows /job/, /viewjob?, /rss; frequent 429 blocks
  - Wantedly user terms ban crawling/scraping and any ingestion of content into ML/AI models; Bizreach robots blocks GPTBot/ClaudeBot/anthropic-ai/CCBot on /jobs/ and job detail is login-gated; Green ToS Art.11(11) and doda ToS forbid use beyond private use and doda robots disallows JobSearchList/JobSearchDetail; Rikunabi NEXT robots disallows /api/ and all filter params
  - Glassdoor has aggressive bot detection and merged into Indeed (July 2026 per reports)
  - Feeding this content to Claude/GPT would itself violate Wantedly's AI clause
### HelloWork (ハローワーク) official job-data API / CSV [read_only_ok=True, cost=Free but inaccessible, effort=weeks, risk=medium]
MHLW 求人・求職情報提供サービス: XML API or CSV of all nationwide public postings (employers can opt out), updated once per business day at 06:00 with data as of 20:00 previous business day. Portal https://www.hellowork.mhlw.go.jp/provide/provide_top.html; API spec 'API インタフェース仕様書 v1.4 (Oct 2023)'.
Pros:
  - Official, comprehensive Japanese labor-market data, free
Cons:
  - Eligibility limited to local governments and licensed/notified private placement agencies; application PDF must be signed and mailed to the labour bureau; annual usage report; terms forbid redistribution to the general public - not available to an individual job seeker
  - Scraping hellowork.mhlw.go.jp is done by hobbyists (Selenium) but is outside the official framework; low tech-job relevance anyway
### Generic career-page monitoring for companies on no known ATS (RSS/Atom, sitemap diff, JSON-LD, Playwright fallback) [read_only_ok=True, cost=Free, effort=days, risk=low]
Per watched company: (1) look for <link rel=alternate type=application/rss+xml> or /jobs.rss, /feed; (2) parse /robots.txt (protego) and Sitemap: entries, diff job URLs daily; (3) on new URLs fetch once and extract schema.org JobPosting JSON-LD (extruct) - Google requires title, description, datePosted, hiringOrganization, jobLocation and recommends validThrough, baseSalary, employmentType, identifier, jobLocationType, applicantLocationRequirements, directApply; (4) only if the page is JS-rendered, Playwright headless GET with descriptive User-Agent, 1 request/site/day, honoring robots.txt.
Pros:
  - Works for any company; JSON-LD is present on most SEO-optimised careers pages because Google for Jobs requires it
  - Public, non-login pages; scraping public job postings is the lowest-risk category (hiQ: public access is not CFAA 'without authorization'), and JSON-LD is literally published for machine consumption
Cons:
  - Contract/ToS risk depends on each site's terms (Meta v. Bright Data 2024 reinforced ToS-based claims); robots.txt is not law but ignoring it undermines good faith
  - Playwright adds Chromium dependency and maintenance; sitemaps often lack lastmod
  - Per-company heuristics; false negatives when careers pages are iframes of an ATS (then switch to the ATS endpoint instead)

## Concrete details
  - Greenhouse: GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true ; GET /jobs/{job_id}?questions=true ; /departments ; /offices . Fields: id, internal_job_id, requisition_id, title, updated_at, first_published, language, application_deadline, location.name, absolute_url, content (HTML-escaped: html.unescape), departments[], offices[], metadata[], pay_input_ranges[], company_name. Verified live with board_token=stripe.
  - Lever: GET https://api.lever.co/v0/postings/{site}?mode=json&skip=0&limit=100 (EU tenants: https://api.eu.lever.co/v0/postings/{site}); filters location, commitment, team, department, level, group. Fields: id, text, categories{commitment,department,location,team,allLocations}, workplaceType (on-site|remote|hybrid|unspecified), country, hostedUrl, applyUrl, createdAt (ms epoch), description, descriptionPlain, descriptionBody, lists[], additional, additionalPlain, salaryRange (optional). Verified live with site=spotify; empty array for unknown/empty boards.
  - Ashby: GET https://api.ashbyhq.com/posting-api/job-board/{jobBoardName}?includeCompensation=true (jobBoardName from jobs.ashbyhq.com/{name}). Fields: apiVersion, jobs[{id, title, department, team, employmentType, location, secondaryLocations[], publishedAt, isListed, isRemote, workplaceType, address.postalAddress, jobUrl, applyUrl, descriptionHtml, descriptionPlain, compensation{compensationTierSummary, scrapeableCompensationSalarySummary, compensationTiers[], summaryComponents[{compensationType, interval, currencyCode, minValue, maxValue}]}}]. Missing fields are omitted, not null. Large boards exceed 10 MB (openai) - stream.
  - SmartRecruiters: GET https://api.smartrecruiters.com/v1/companies/{companyIdentifier}/postings?limit=100&offset=0&updatedAfter=YYYY-MM-DDThh:mm:ssZ&country=&city=&department= ; detail GET .../postings/{id} for jobAd.sections (HTML) and applyUrl. List fields: offset, limit, totalFound, content[{id, uuid, name, refNumber, releasedDate, location{city,region,country,remote,fullLocation}, industry, department, function, typeOfEmployment, experienceLevel, customField[], ref, company{identifier,name}, language, jobAdId}]. No auth needed for public postings (verified live). Limits 10 req/s, 8 concurrent; headers X-RateLimit-Concurrent-Limit / -Remaining, Retry-After on 429.
  - Workable: GET https://apply.workable.com/api/v1/widget/accounts/{subdomain}?details=true (https://www.workable.com/api/accounts/{subdomain} 302-redirects here). Fields: name, description, jobs[{title, shortcode, code, employment_type, telecommuting, workplace_type (on_site|hybrid|remote), department, url, shortlink, application_url, published_on, created_at, country, city, state, education, experience, function, industry, description (details=true)}]. Unknown subdomain -> 404 {"error":"not-found"}.
  - Recruitee: GET https://{company}.recruitee.com/api/offers/?department=&tag= ; GET /api/offers/{id}. Fields: offers[{id, guid, slug, title, company_name, department, description, requirements, remote, hybrid, on_site, locations[{city,country,country_code,state}], employment_type_code, category_code, experience_code, salary{min,max,currency,period}, careers_url, careers_apply_url, created_at, published_at, updated_at, tags[], translations{}}].
  - Personio: official XML GET https://{company}.jobs.personio.de/xml?language=en (also ?language=de|fr|es|nl|it|pt; some tenants use .com). Undocumented JSON GET https://{company}.jobs.personio.de/search.json (fields id, name, office, department, recruitingCategory, employmentType, seniority, schedule, yearsOfExperience, keywords, createdAt, jobDescriptions). Note: Personio bakes city into titles ('... Engineer, Krakau') - strip trailing ', {city}' before title_norm.
  - Teamtailor: GET https://{company}.teamtailor.com/jobs.rss?per_page=200&offset=0 (custom domains too, e.g. https://career.teamtailor.com/jobs.rss). RSS 2.0 items: title, link, guid (UUID), pubDate, description (HTML), tt:locations{name,address,zip,city,country}, tt:department, tt:role, tt:division, remoteStatus (e.g. hybrid). Verified live. Authenticated API (api.teamtailor.com / api.na.teamtailor.com, Token token=) is NOT needed.
  - Rippling: GET https://api.rippling.com/platform/api/ats/v1/board/{board_slug}/jobs?searchTerm=&workLocation=&department= -> [{uuid, name, department{id,label}, url, workLocation{id,label}}] (no description; follow url for detail). Official docs at developer.rippling.com/documentation/job-board-api; verified live with board_slug=rippling (500+ jobs).
  - Workday (v2, undocumented): POST https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs  headers Accept: application/json, Content-Type: application/json, Referer: https://{tenant}.wd{N}.myworkdayjobs.com/en-US/{site}  body {"appliedFacets":{},"limit":20,"offset":0,"searchText":""} -> {total, jobPostings[{title, externalPath, locationsText, postedOn, bulletFields[]}]}; detail GET https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/job{externalPath} -> jobPostingInfo{title, jobDescription, location, postedOn, startDate, timeType, jobReqId, externalUrl}. limit must be <=20. Example: nvidia.wd5 / NVIDIAExternalCareerSite; salesforce.wd12 / External_Career_Site; adobe.wd5 / external_experienced.
  - BambooHR (v2, undocumented): GET https://{slug}.bamboohr.com/careers/list -> {meta:{totalCount}, result:[{id, jobOpeningName, departmentLabel, location{city,state}, isRemote}]}; per-job detail requires a second request (careers page /careers/{id}); validate slug with ^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$ before building the hostname.
  - Adzuna: GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}?app_id=&app_key=&what=&what_exclude=&where=&distance=&results_per_page=50&sort_by=date&max_days_old=7&salary_min=&full_time=1&permanent=1&content-type=application/json . Fields: results[{id, title, company.display_name, location{display_name, area[]}, latitude, longitude, salary_min, salary_max, salary_is_predicted, created, redirect_url, description (snippet), contract_type, contract_time, category{label,tag}}], count. Country codes enumerated at https://developer.adzuna.com/activedocs (commonly gb, us, at, au, be, br, ca, ch, de, es, fr, in, it, mx, nl, nz, pl, sg, za; no jp). Limits per ToS: 25/min, 250/day, 1000/week, 2500/month; 429 on excess.
  - JSearch: direct base https://api.openwebninja.com (header x-api-key) or https://jsearch.p.rapidapi.com (header x-rapidapi-key). GET /search?query=backend%20engineer%20in%20Tokyo&page=1&num_pages=1&country=jp&language=ja&date_posted=week&work_from_home=false&employment_types=FULLTIME,CONTRACTOR&job_requirements=more_than_3_years_experience&radius=50&exclude_job_publishers=Dice&fields=job_title,job_apply_link . Response {status, request_id, parameters, data[{job_id, job_title, employer_name, employer_website, employer_logo, job_publisher, job_employment_type, job_apply_link, job_apply_is_direct, apply_options[], job_description, job_is_remote, job_posted_at_datetime_utc, job_location, job_city, job_state, job_country, job_latitude, job_longitude, job_min_salary, job_max_salary, job_salary_period, job_highlights{Qualifications,Responsibilities,Benefits}, job_google_link}]}. Pricing: Free 200 req/mo (1000/h), Pro $25 10k, Ultra $75 50k, Mega $150 200k, PAYG $0.005.
  - Jooble: POST https://ja.jooble.org/api/{api_key} (Japan) / https://jooble.org/api/{api_key} (US) / https://uk.jooble.org/api/{api_key} ... Content-Type: application/json body {"keywords":"バックエンド エンジニア","location":"東京","radius":"40","page":"1","ResultOnPage":"20","companysearch":"false"} -> {totalCount, jobs[{id, title, location, snippet, salary, source, type, link, company, updated}]}. 403 = bad key. Free key: 500 requests lifetime.
  - Remotive: GET https://remotive.com/api/remote-jobs?category=software-dev&search=&company_name=&limit=100 -> {job-count, jobs[{id, url, title, company_name, company_logo, category, tags[], job_type, publication_date, candidate_required_location, salary, description (HTML)}]}. Max 4 calls/day; >2/min blocked; 24 h delay.
  - Himalayas: GET https://himalayas.app/jobs/api?limit=20&cursor= ; GET https://himalayas.app/jobs/api/search?q=&country=JP&worldwide=true&seniority=Senior&employment_type=Full%20Time&sort=recent&page=1 ; RSS https://himalayas.app/jobs/rss (100 newest, ttl 1440). Fields: title, excerpt, description, companyName, companySlug, companyLogo, employmentType, locationRestrictions[], timezoneRestriction, category, parentCategories, minSalary, maxSalary, salaryPeriod, currency, pubDate, expiryDate, applicationLink, guid.
  - Jobicy: GET https://jobicy.com/api/v2/remote-jobs?count=200&geo=japan&industry=engineering&tag=python ; ?get=locations / ?get=industries for slugs. Response {apiVersion, documentationUrl, friendlyNotice, jobCount, lastUpdate, jobs[{id, url, jobSlug, jobTitle, companyName, companyLogo, jobIndustry[], jobType[], jobGeo, jobLevel, jobExcerpt, jobDescription, pubDate, salaryMin, salaryMax, salaryCurrency, salaryPeriod}]}. Verified live (apiVersion 2.2.16).
  - RemoteOK: GET https://remoteok.com/api -> array; element[0] = {legal: "...link back (with follow...) ... mention Remote OK as a source..."}; elements[1..] = {slug, id, epoch, date, company, company_logo, position, tags[], description, location, apply_url, salary_min, salary_max, logo, url}.
  - Arbeitnow: GET https://www.arbeitnow.com/api/job-board-api?page=N -> {data[{slug, company_name, title, description (HTML), remote (bool), url, tags[], job_types[], location, created_at (unix)}]} (no meta/links observed today; stop when data is empty).
  - The Muse: GET https://www.themuse.com/api/public/jobs?page=1&descending=true&category=Software%20Engineering&level=Senior%20Level&location=Tokyo%2C%20Japan&api_key= -> {page, page_count, results[20]}; headers X-RateLimit-Limit/-Remaining/-Reset; 500 req/h keyless, 3600 req/h with key.
  - SerpApi: GET https://serpapi.com/search?engine=google_jobs&q=software+engineer&location=Tokyo,+Japan&hl=ja&gl=jp&api_key= ; paginate with next_page_token (10 results/page). Free 250/mo, 50/h.
  - TokyoDev: robots.txt = 'User-agent: * / Allow: / / Disallow: /c/ /frames/ /ja/frames/ ; Amazonbot Disallow: / ; Sitemap: https://www.tokyodev.com/sitemap.xml' (urlset, job URLs /companies/{company}/jobs/{slug}, no lastmod). Japan Dev: robots allows all except one blog post + one PDF; sitemap index https://japan-dev.com/sitemap.xml -> https://japan-dev.com/cdn/sitemaps/sitemap.xml (job URLs https://japan-dev.com/jobs/{company}/{slug}, ~550 jobs, <priority> only). Parse JobPosting JSON-LD with extruct; fall back to selectolax CSS selectors.
  - Gmail ingestion (read-only): scope https://www.googleapis.com/auth/gmail.readonly ; users.messages.list q='from:(linkedin.com OR indeed.com OR wantedly.com OR bizreach.jp OR green-japan.com OR doda.jp OR rikunabi.com) newer_than:2d' ; known senders jobalerts-noreply@linkedin.com, alert@indeed.com (confirm the Japanese boards' exact sender addresses from the inbox). Store as source='gmail_alert', source_id=Gmail message id + link index.
  - Normalized schema (SQLite/Postgres) - table job_posting: id TEXT PK (uuid), canonical_id TEXT FK->job_canonical.id, source TEXT CHECK IN ('greenhouse','lever','ashby','smartrecruiters','workable','recruitee','personio','teamtailor','rippling','workday','bamboohr','adzuna','jsearch','jooble','remotive','himalayas','jobicy','remoteok','arbeitnow','themuse','serpapi','tokyodev','japandev','gmail_alert','manual'), source_id TEXT, source_url TEXT, apply_url TEXT, title TEXT, title_norm TEXT, company_name TEXT, company_norm TEXT, company_domain TEXT, location_raw TEXT, city TEXT, region TEXT, country_code CHAR(2), remote_type TEXT CHECK IN ('onsite','hybrid','remote','unspecified'), employment_type TEXT CHECK IN ('full_time','part_time','contract','intern','temporary','other'), salary_min NUMERIC, salary_max NUMERIC, salary_currency CHAR(3), salary_period TEXT CHECK IN ('year','month','week','day','hour'), salary_is_estimate BOOLEAN, description_html TEXT, description_text TEXT, language TEXT, posted_at TIMESTAMPTZ, source_updated_at TIMESTAMPTZ, expires_at TIMESTAMPTZ, first_seen_at TIMESTAMPTZ, last_seen_at TIMESTAMPTZ, is_active BOOLEAN, content_hash CHAR(64), simhash64 BIGINT, attribution_required BOOLEAN, attribution_text TEXT, raw JSON; UNIQUE(source, source_id).
  - Table job_canonical: id TEXT PK, blocking_key CHAR(40), best_posting_id TEXT, company_norm TEXT, title_norm TEXT, country_code CHAR(2), first_seen_at, last_seen_at, source_count INT, status TEXT (open|closed). Table job_sighting: posting_id, seen_at, http_status, still_listed BOOLEAN (mark is_active=false after 3 consecutive misses). Table watch_target: id, kind (ats enum|careers_page|sitemap|rss), company_name, identifier (board token / tenant+site / URL), poll_interval_min, last_polled_at, etag, last_modified, last_hash, enabled.
  - Normalization: NFKC -> casefold -> strip legal suffixes {inc, inc., llc, ltd, limited, gmbh, ag, sas, k.k., kk, co., corp, corporation, 株式会社, (株), 合同会社, 有限会社} and leading/trailing punctuation -> collapse whitespace. title_norm additionally removes bracketed/parenthetical text, trailing ', {city}' and ' - {city}' segments, seniority-neutral tokens are kept. city_norm: map JP prefecture/city variants (東京都, Tokyo, Tokyo-to) to one bucket; remote_type='remote' replaces city in the key.
  - Dedup pipeline: (1) UNIQUE(source, source_id). (2) canonical_apply_url = apply_url or source_url with tracking params stripped (utm_*, gh_src, gh_jid retained, lever-source, ashby_jid retained, ref, source) and host lowercased; if it resolves to an ATS domain (greenhouse.io, lever.co, ashbyhq.com, myworkdayjobs.com, smartrecruiters.com, workable.com, recruitee.com, personio.de, teamtailor.com, rippling.com) match on that URL first. (3) blocking_key = sha1(company_norm|title_norm|country_code|city_norm_or_remote). (4) within a block, merge when rapidfuzz.fuzz.token_set_ratio(title_norm_a, title_norm_b) >= 90 AND (MinHash Jaccard over 5-word shingles of description_text >= 0.7 via datasketch, or SimHash64 Hamming distance <= 3); two different roles with similar titles at one company stay separate when descriptions diverge. (5) Merge policy: keep all postings as sightings; canonical best_posting_id prefers ATS-direct source > aggregator; posted_at = min; salary fields = union (prefer non-estimate); description = longest. (6) Sanity: expect ~10-15% cross-source merge rate; alert if >50% or 0%.
  - Python stack: uv add httpx pydantic feedparser extruct selectolax protego datasketch rapidfuzz apscheduler python-dateutil ; optional simhash, playwright (v2). Per-source token-bucket limiter table keyed by source with (capacity, refill_per_sec) e.g. adzuna (25/min & 250/day), remotive (4/day), jobicy (1/hour), themuse (500/hour).

## Open questions
  - Which countries/cities beyond Tokyo does the user target? This decides Adzuna country codes (no jp), JSearch country/language pairs, and whether Jooble keys are worth requesting.
  - Which specific companies should be on the watchlist, and which ATS does each use? (Determines whether Workday/BambooHR connectors need to be pulled into v1.)
  - Does the user already receive job-alert/scout emails from LinkedIn, Indeed, Wantedly, Bizreach, Green, doda, Rikunabi NEXT? Exact sender addresses and HTML templates must be sampled from the inbox before writing parsers.
  - Is JobPilot strictly personal/non-commercial? Adzuna's ToS gives organisations only a 14-day trial; an individual's personal use appears fine but should be confirmed if the project is ever open-sourced or shared.
  - Can Wantedly/Bizreach-derived content be sent to Claude/GPT at all? Wantedly's terms prohibit ingesting its content into AI models; safest is to store only metadata (title/company/URL) for those sources and exclude their text from LLM prompts.
  - TokyoDev and Japan Dev terms-of-use pages were not verified (robots.txt is permissive); confirm they do not forbid automated access before enabling the sitemap crawler, and confirm TokyoDev pages carry JobPosting JSON-LD.
  - JSearch quality for Japanese-language queries (country=jp&language=ja) is unverified; run a 5-request smoke test within the free quota.
  - Adzuna's exact current country list is only enumerated in the JS-rendered activedocs page; confirm after signup (400 'Invalid country' on unsupported codes).
  - Jooble's 500-request lifetime cap comes from help-center/third-party summaries; confirm from the API key email before designing around it.
  - Should the app verify posting liveness by re-fetching source_url (HEAD) - this adds requests to third-party sites and should respect the same per-source limits.

## Sources
- Adzuna API Overview: https://developer.adzuna.com/overview
- Adzuna API Search ads docs: https://developer.adzuna.com/docs/search
- Adzuna API Terms of Service (Default API access limits, attribution): https://developer.adzuna.com/docs/terms_of_service
- Adzuna Interactive Endpoint Documentation (country list): https://developer.adzuna.com/activedocs
- JSearch API - OpenWeb Ninja (pricing, endpoints): https://www.openwebninja.com/api/jsearch
- JSearch on RapidAPI: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
- Jooble REST API Documentation (Help Center): https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation
- Connecting to the Jooble REST API (regional keys): https://help.jooble.org/en/support/solutions/articles/60000922689-how-to-connect-to-the-jooble-rest-api-after-receiving-the-key
- Jooble REST API Japan request page: https://ja.jooble.org/api/about
- Arbeitnow Job Board API: https://www.arbeitnow.com/api/job-board-api
- Remotive Remote Jobs API (GitHub): https://github.com/remotive-com/remote-jobs-api
- The Muse API v2: https://www.themuse.com/developers/api/v2
- Himalayas Remote Jobs API: https://himalayas.app/api
- Himalayas Remote Jobs RSS feed (GitHub): https://github.com/Himalayas-App/remote-jobs-rss-feed
- Jobicy Remote Jobs API (GitHub): https://github.com/Jobicy/remote-jobs-api
- Jobicy Remote Jobs API/RSS Feed: https://jobicy.com/jobs-rss-feed
- RemoteOK API (legal notice in first element): https://remoteok.com/api
- SerpApi Google Jobs API: https://serpapi.com/google-jobs-api
- SerpApi Pricing: https://serpapi.com/pricing
- Indeed Partner Docs: https://docs.indeed.com/
- Indeed Additional API Terms and Guidelines (ja-JP): https://docs.indeed.com/dev/docs/additional-api-terms-and-guidelines-ja-jp
- Indeed Job Sync API guide: https://docs.indeed.com/job-sync-api/job-sync-api-guide
- Does Indeed Have an API? What Happened to the Publisher API (RolesAPI): https://rolesapi.com/blog/does-indeed-have-an-api/
- HR Dive: Visibility ends for certain free single-source XML feeds on Indeed: https://www.hrdive.com/news/visibility-ends-for-certain-free-single-source-xml-feeds-on-indeed/816209/
- LinkedIn Job Posting API Overview (Microsoft Learn) - not accepting new partnerships: https://learn.microsoft.com/en-us/linkedin/talent/job-postings/api/overview?view=li-lts-2026-03
- LinkedIn Talent Solutions Partner Application: https://business.linkedin.com/talent-solutions/ats-partners/partner-application
- LinkedIn User Agreement (8.2 Don'ts): https://www.linkedin.com/legal/user-agreement
- LinkedIn robots.txt: https://www.linkedin.com/robots.txt
- Glassdoor Help Center: Glassdoor API (no longer supports API partnerships): https://help.glassdoor.com/s/article/Glassdoor-API?language=en_US
- Google Cloud Talent Solution - Job Search basics (bring your own jobs): https://docs.cloud.google.com/talent-solution/job-search/docs/basics
- Google Search Central: JobPosting structured data: https://developers.google.com/search/docs/appearance/structured-data/job-posting
- Greenhouse Job Board API: https://docs.greenhouse.io/job-board.html
- Lever Postings API (GitHub): https://github.com/lever/postings-api
- Ashby Public Job Posting API: https://developers.ashbyhq.com/docs/public-job-posting-api
- Workable Job Board (widget) API reference: https://workable.readme.io/reference/jobs-1
- SmartRecruiters Posting API: https://developers.smartrecruiters.com/docs/posting-api
- SmartRecruiters Rate Limiting: https://developers.smartrecruiters.com/docs/rate-limiting
- SmartRecruiters Throttling Policies: https://developers.smartrecruiters.com/docs/throttling-policies
- Recruitee Careers Site API - Offers: https://docs.recruitee.com/reference/offers
- Personio XML feed - Retrieve open positions: https://developer.personio.de/v1.0/reference/get_xml
- Personio Recruiting API v2 - List all jobs (authenticated alternative): https://developer.personio.de/reference/get_v2-recruiting-jobs
- Teamtailor RSS feed how-to guide: https://support.teamtailor.com/en/articles/11171756-rss-feed-how-to-guide
- Teamtailor API (authenticated): https://docs.teamtailor.com/
- Rippling Job Board API - GET /board/{board_slug}/jobs: https://developer.rippling.com/documentation/job-board-api/reference/get-board-slug-jobs
- Workday job boards have a JSON API too (DEV Community): https://dev.to/udaninn/workday-job-boards-have-a-json-api-too-its-just-better-hidden-23fl
- Ask Workday's public API for 100 jobs and you get zero (limit=20 cap): https://dev.to/juancarlosguti/ask-workdays-public-api-for-100-jobs-and-you-get-zero-with-no-error-54b2
- CleanJobData: How to Scrape Workday Job Listings: https://cleanjobdata.com/articles/how-to-scrape-workday-job-listings
- plin-code/job-boards-bamboohr (BambooHR /careers/list shape): https://packagist.org/packages/plin-code/job-boards-bamboohr
- BambooHR Jobs API developer reference (JobsPipe): https://jobspipe.dev/guides/bamboohr-jobs-api
- BambooHR Get Job Summaries (authenticated ATS API): https://documentation.bamboohr.com/reference/get-job-summaries
- hiring-cafe-alerts (Next.js data route replaced POST /api/search-jobs): https://github.com/arg999999/hiring-cafe-alerts
- hiringcafe.com robots.txt: https://hiringcafe.com/robots.txt
- Wantedly Open API developers page (embed widgets): https://sg.wantedly.com/developers
- Wantedly 利用規約 (scraping / AI-ingestion prohibitions): https://service-terms.wantedly.com/user_terms/ja_JP
- Wantedly API利用規約: https://service-terms.wantedly.com/open_api/ja_JP
- Wantedly robots.txt: https://www.wantedly.com/robots.txt
- Green 利用規約: https://www.green-japan.com/contents/terms
- Green robots.txt: https://www.green-japan.com/robots.txt
- doda 利用規約: https://doda.jp/material/kiyaku/001.html
- doda 免責事項: https://doda.jp/info/menseki/
- doda robots.txt: https://doda.jp/robots.txt
- Bizreach robots.txt: https://www.bizreach.jp/robots.txt
- Rikunabi NEXT robots.txt: https://next.rikunabi.com/robots.txt
- リクナビNEXT Indeed PLUS 連携 (2025 model change): https://www.naito.jp/knowledge/jobad/2489/
- HRMOS採用 API 提供決定 (Bizreach ATS, 2026-08): https://hrmos.co/info/news/20260831-2/
- doda Assist API連携 (ATS-only): https://prtimes.jp/main/html/rd/p/000000179.000022215.html
- jp.indeed.com robots.txt: https://jp.indeed.com/robots.txt
- Indeed Japan 利用規約: https://jp.indeed.com/legal
- TokyoDev robots.txt: https://www.tokyodev.com/robots.txt
- TokyoDev sitemap.xml: https://www.tokyodev.com/sitemap.xml
- Japan Dev robots.txt: https://japan-dev.com/robots.txt
- Japan Dev sitemap (jobs): https://japan-dev.com/cdn/sitemaps/sitemap.xml
- ハローワーク求人・求職情報提供サービス portal: https://www.hellowork.mhlw.go.jp/provide/provide_top.html
- e-Gov API catalog: HelloWork job information API: https://api-catalog.e-gov.go.jp/info/en/apicatalog/view/57
- ハローワーク求人情報提供サービス 導入マニュアル (民間職業紹介事業者用): https://www.hellowork.mhlw.go.jp/doc/kyuujin_dounyuu_manual_pri202207.pdf
- Yahoo! JAPAN 求人API 終了告知 (2025-03-31): https://developer.yahoo.co.jp/changelog/2024-11-25-job10.html
- python-jobspy (PyPI): https://pypi.org/project/python-jobspy/
- speedyapply/JobSpy README: https://github.com/speedyapply/JobSpy/blob/main/README.md
- EFF: Scraping Public Websites (Still) Isn't a Crime (hiQ v. LinkedIn, 9th Cir. 2022): https://www.eff.org/deeplinks/2022/04/scraping-public-websites-still-isnt-crime-court-appeals-declares
- Morgan Lewis: LinkedIn v. hiQ settlement and consent judgment: https://www.morganlewis.com/blogs/sourcingatmorganlewis/2022/12/linkedin-v-hiq-landmark-data-scraping-suit-provides-guidance-to-data-scrapers-and-web-operators
- Lightcast: How does Lightcast handle duplicate postings?: https://kb.lightcast.io/en/articles/6957661-how-does-lightcast-handle-duplicate-postings
- The same job is posted on three boards - how to deduplicate (DEV Community): https://dev.to/get_anything/the-same-job-is-posted-on-three-boards-heres-how-to-deduplicate-job-listings-properly-2862
- freehire: Collapsing duplicate jobs without hiding real ones: https://freehire.me/blog/2026-07-20-collapsing-duplicate-jobs
- NeMo Curator: Fuzzy Deduplication (MinHash/LSH parameters): https://docs.nvidia.com/nemo/curator/curate-text/process-data/deduplication/fuzzy
- Feedly: How can I follow job feeds (LinkedIn/Indeed email alerts): https://docs.feedly.com/article/746-how-can-i-follow-job-feeds-in-feedly
