// i18n dictionary hub (round 201): the runtime tables live in per-language
// modules (dict-zh.ts statically — the SSR/default language; dict-en.ts on
// demand) so the every-route chunk carries one language, not both. This
// module keeps the types + is still the audit's key-universe source.

export type Lang = "zh" | "en";

import type { zh } from "./dict-zh";

export type DictKey = keyof typeof zh;
