// Dates: stored as UTC ISO, shown in the campaign's timezone as `2026-10-01（水）14:00 JST`.
import type { Lang } from '@/i18n';

const WEEKDAY: Record<Lang, string[]> = {
  zh: ['日', '一', '二', '三', '四', '五', '六'],
  ja: ['日', '月', '火', '水', '木', '金', '土'],
  en: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
};

function parts(iso: string, tz: string) {
  const d = new Date(iso);
  const f = new Intl.DateTimeFormat('en-CA', {
    timeZone: tz,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    weekday: 'short',
  });
  const p: Record<string, string> = Object.fromEntries(
    f.formatToParts(d).map((x) => [x.type, x.value]),
  );
  return {
    year: p.year,
    month: p.month,
    day: p.day,
    hour: p.hour === '24' ? '00' : p.hour,
    minute: p.minute,
    weekdayIndex: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(p.weekday),
  };
}

function tzShort(iso: string, tz: string, lang: Lang): string {
  const locale = lang === 'en' ? 'en-US' : lang === 'ja' ? 'ja-JP' : 'zh-CN';
  const part = new Intl.DateTimeFormat(locale, { timeZone: tz, timeZoneName: 'short' })
    .formatToParts(new Date(iso))
    .find((x) => x.type === 'timeZoneName');
  return part?.value ?? tz;
}

export function fmtDate(iso: string, tz: string, lang: Lang): string {
  const p = parts(iso, tz);
  const wd = WEEKDAY[lang][p.weekdayIndex];
  return lang === 'en' ? `${p.year}-${p.month}-${p.day} (${wd})` : `${p.year}-${p.month}-${p.day}（${wd}）`;
}

export function fmtDateTime(iso: string, tz: string, lang: Lang): string {
  const p = parts(iso, tz);
  return `${fmtDate(iso, tz, lang)}${p.hour}:${p.minute} ${tzShort(iso, tz, lang)}`;
}

export function timeOfDay(iso: string, tz: string): 'morning' | 'afternoon' | 'evening' {
  const hour = Number(parts(iso, tz).hour);
  return hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening';
}

/** Whole days between `iso` and now (positive = past). */
export function daysAgo(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
}

/** Calendar-day distance (in `tz`) between `iso` and `nowIso`; `null` when past or beyond this week. */
export function relativeDay(iso: string, tz: string, nowIso: string): 'today' | 'tomorrow' | 'later_this_week' | null {
  const a = parts(iso, tz);
  const b = parts(nowIso, tz);
  const due = Date.UTC(Number(a.year), Number(a.month) - 1, Number(a.day));
  const now = Date.UTC(Number(b.year), Number(b.month) - 1, Number(b.day));
  const diffDays = Math.round((due - now) / 86_400_000);
  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'tomorrow';
  // Week runs Mon–Sun in the display timezone; weekdayIndex 0 is Sunday.
  const daysToWeekEnd = b.weekdayIndex === 0 ? 0 : 7 - b.weekdayIndex;
  if (diffDays >= 2 && diffDays <= daysToWeekEnd) return 'later_this_week';
  return null;
}


function wallMillis(p: ReturnType<typeof parts>): number {
  return Date.UTC(Number(p.year), Number(p.month) - 1, Number(p.day), Number(p.hour), Number(p.minute));
}

/** Interpret a `datetime-local` value ('YYYY-MM-DDTHH:mm') as wall-clock time in `tz`, return UTC ISO. */
export function zonedInputToIso(value: string, tz: string): string {
  const [datePart, timePart] = value.split('T');
  const [year, month, day] = datePart.split('-').map(Number);
  const [hour, minute] = timePart.split(':').map(Number);
  const guess = Date.UTC(year, month - 1, day, hour, minute);
  const offset = wallMillis(parts(new Date(guess).toISOString(), tz)) - guess;
  return new Date(guess - offset).toISOString();
}

/** `datetime-local` value ('YYYY-MM-DDTHH:mm') for `iso` as displayed in `tz`. */
export function isoToZonedInput(iso: string, tz: string): string {
  const p = parts(iso, tz);
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}

/** `datetime-local` value ('YYYY-MM-DDTHH:mm') for "now" as displayed in `tz`. */
export function nowInputInTz(tz: string): string {
  return isoToZonedInput(new Date().toISOString(), tz);
}
