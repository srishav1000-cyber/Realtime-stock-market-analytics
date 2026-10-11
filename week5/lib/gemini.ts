// Edge-safe Gemini client (fetch only). Shared by /api/copilot and /api/sentiment.

export type GeminiResult = { ok: true; text: string } | { ok: false; reason: 'no_key' | 'cooldown' | 'quota' | 'auth' | 'error'; detail?: string };

let cooldownUntil = 0;
let cooldownReason: 'quota' | 'auth' | 'error' = 'error';

export const geminiConfigured = () => Boolean(process.env.GEMINI_API_KEY);

interface Opts {
  system?: string;
  prompt: string;
  /** base64 images / PDFs sent as inlineData parts (vision) */
  images?: { mimeType: string; data: string }[];
  json?: boolean;
  maxTokens?: number;
  temperature?: number;
}

export async function callGemini({ system, prompt, images, json, maxTokens = 600, temperature = 0.3 }: Opts): Promise<GeminiResult> {
  const key = process.env.GEMINI_API_KEY;
  if (!key) return { ok: false, reason: 'no_key' };
  // after a quota / auth / outage response, stop calling for a while so the local fallback serves traffic
  if (Date.now() < cooldownUntil) return { ok: false, reason: 'cooldown', detail: cooldownReason };

  const model = process.env.GEMINI_MODEL || 'gemini-2.0-flash';
  const trip = (reason: 'quota' | 'auth' | 'error', ms: number, detail: string): GeminiResult => {
    cooldownUntil = Date.now() + ms;
    cooldownReason = reason;
    return { ok: false, reason, detail };
  };

  try {
    // GEMINI_API_BASE exists so the quota / outage fallback can be tested against a mock server
    const base = process.env.GEMINI_API_BASE || 'https://generativelanguage.googleapis.com';
    const res = await fetch(`${base}/v1beta/models/${encodeURIComponent(model)}:generateContent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-goog-api-key': key },
      body: JSON.stringify({
        ...(system ? { systemInstruction: { parts: [{ text: system }] } } : {}),
        contents: [{ role: 'user', parts: [{ text: prompt }, ...(images ?? []).map((im) => ({ inlineData: { mimeType: im.mimeType, data: im.data } }))] }],
        generationConfig: { temperature, maxOutputTokens: maxTokens, ...(json ? { responseMimeType: 'application/json' } : {}) },
      }),
      signal: AbortSignal.timeout(images?.length ? 25_000 : 9000),
    });

    if (res.status === 429) {
      const retry = Number(res.headers.get('retry-after'));
      return trip('quota', Math.min(10 * 60_000, Math.max(30_000, (Number.isFinite(retry) ? retry : 60) * 1000)), 'HTTP 429');
    }
    if (res.status === 401 || res.status === 403) return trip('auth', 10 * 60_000, 'HTTP ' + res.status);
    if (!res.ok) {
      const body = await res.text().catch(() => '');
      if (/RESOURCE_EXHAUSTED/.test(body)) return trip('quota', 60_000, 'RESOURCE_EXHAUSTED');
      return trip('error', 15_000, 'HTTP ' + res.status);
    }
    const data = await res.json();
    const text: string | undefined = data?.candidates?.[0]?.content?.parts?.map((p: { text?: string }) => p.text ?? '').join('');
    if (!text?.trim()) return trip('error', 15_000, 'empty response (possibly blocked by safety filters)');
    return { ok: true, text: text.trim() };
  } catch (e) {
    return trip('error', 15_000, e instanceof Error ? e.message : 'network error');
  }
}
