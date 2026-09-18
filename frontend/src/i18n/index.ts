import { en, type Key } from './en';
import { ja } from './ja';
import { zh } from './zh';

export type Lang = 'zh' | 'ja' | 'en';
export type { Key };

export const LANGS: Lang[] = ['zh', 'ja', 'en'];
export const LANG_LABEL: Record<Lang, string> = { zh: '中文', ja: '日本語', en: 'English' };

export const DICT: Record<Lang, Record<Key, string>> = { en, zh, ja };
