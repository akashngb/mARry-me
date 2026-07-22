import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import Anthropic from '@anthropic-ai/sdk';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const PORT = process.env.PORT || 8787;
const FAL_KEY = process.env.FAL_KEY;
const FAL_MODEL_ID = process.env.FAL_MODEL_ID || 'decart/lucy-2-5/realtime';
const CLAUDE_MODEL = process.env.CLAUDE_MODEL || 'claude-haiku-4-5-20251001';

const anthropic = process.env.ANTHROPIC_API_KEY
  ? new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  : null;

const app = express();
app.use(cors());
app.use(express.json({ limit: '1mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// Expose the Decart key to the local page (localhost dev only — use a token in prod).
app.get('/api/decart-key', (_req, res) =>
  res.json({ apiKey: process.env.DECART_API_KEY || '' }),
);

// Claude turns a spoken command into an optimized Lucy edit prompt.
const SYSTEM = `You convert a short spoken command into a vivid, concise prompt for Decart Lucy 2.5, a real-time video-to-video model that transforms a live camera feed.
Rules:
- Output ONLY the edit prompt text. No preamble, no quotes, no explanation.
- Keep it under 25 words describing the visual transformation to apply.
- Preserve the person and scene unless the command explicitly says to change them.
Examples:
command: make it snow
prompt: heavy snowfall across the scene, snowflakes drifting, cold blue winter light, frost forming on surfaces
command: turn me into a cyberpunk
prompt: cyberpunk restyle of the person, neon accents and glowing implants, rain-slick neon-lit city reflections`;

app.get('/health', (_req, res) =>
  res.json({ ok: true, model: CLAUDE_MODEL, anthropic: !!anthropic, fal: !!FAL_KEY }),
);

// POST /rewrite { command } -> { prompt }
app.post('/rewrite', async (req, res) => {
  const command = String(req.body?.command ?? '').trim();
  if (!command) return res.status(400).json({ error: 'missing command' });
  if (!anthropic) return res.json({ prompt: command }); // no key -> passthrough

  try {
    const msg = await anthropic.messages.create({
      model: CLAUDE_MODEL,
      max_tokens: 120,
      system: SYSTEM,
      messages: [{ role: 'user', content: `command: ${command}\nprompt:` }],
    });
    const text = msg.content
      .filter((b) => b.type === 'text')
      .map((b) => b.text)
      .join(' ')
      .trim();
    res.json({ prompt: text || command });
  } catch (e) {
    console.error('rewrite error:', e);
    res.status(500).json({ error: String(e?.message ?? e) });
  }
});

// POST /fal/token { app } -> { token }  (short-lived realtime token; FAL_KEY stays here)
app.post('/fal/token', async (req, res) => {
  if (!FAL_KEY) return res.status(500).json({ error: 'FAL_KEY not set' });
  const allowedApp = String(req.body?.app ?? FAL_MODEL_ID);
  try {
    const r = await fetch('https://rest.fal.ai/tokens/realtime', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Key ${FAL_KEY}` },
      body: JSON.stringify({ app: allowedApp, allowed_apps: [allowedApp], duration: 120 }),
    });
    if (!r.ok) {
      return res.status(r.status).json({ error: `fal token: ${await r.text()}` });
    }
    const data = await r.json();
    // fal may return the token as a raw string or as { token }.
    res.json({ token: typeof data === 'string' ? data : data.token });
  } catch (e) {
    console.error('fal token error:', e);
    res.status(500).json({ error: String(e?.message ?? e) });
  }
});

app.listen(PORT, () =>
  console.log(`proxy listening on http://0.0.0.0:${PORT}  (claude: ${CLAUDE_MODEL})`),
);
