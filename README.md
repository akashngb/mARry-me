# mARry-me

Two connected pieces for the live-venue AR party demo:

1. **AR web app — "Lucy Live"** (`server/`, Node/Express)
   Laptop webcam → Decart Lucy 2.5 realtime video effects (fal.ai, WebRTC), with
   spoken/typed commands sharpened into effect prompts by Claude. This is the
   part that shows the live venue and lets you talk to it.

2. **Party City cart automation** (`automation.py`, `server.py`, Python/Flask)
   A visible Chrome window that swaps a **balloon** or **piñata** in the real
   Party City cart.

They are wired together: when you tell the AR page to *"switch balloons to
piñata"* (or back), it both **restyles the live venue** and **opens Party City
to remove the old item and add the new one**.

```
browser (server/public/index.html)
  ├─ Lucy AR effect ──▶ fal.ai / Decart (restyle the venue)
  └─ POST /party ─────▶ Express (server/index.js)
                          └─ POST /change ─▶ Flask (server.py) ─▶ visible Chrome ─▶ Party City cart
```

## Run both

**1. Party City automation (Python, Flask on `:5001`):**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
.venv/bin/python server.py
```

**2. AR web app (Node, Express on `:8787`):**

```bash
cd server
npm install
cp .env.example .env    # add ANTHROPIC_API_KEY + FAL_KEY (+ optional PARTY_CITY_URL)
npm start
```

Open **http://localhost:8787**, click **Start camera + Lucy**, then tap the
**"switch balloons to piñata"** preset (or type it / say it). The venue restyles
and the Party City cart updates in the visible Chrome window.

If the Python service isn't running, the AR effect still works and the cart swap
is skipped (logged in the on-page LOG box).

## Party City service directly

Send a structured target or a raw transcript:

```bash
curl -X POST http://127.0.0.1:5001/change \
  -H 'Content-Type: application/json' \
  -d '{"item":"balloon"}'

curl -X POST http://127.0.0.1:5001/change \
  -H 'Content-Type: application/json' \
  -d '{"transcript":"change balloon to pinata"}'
```

For a direct one-item browser test:

```bash
.venv/bin/python server.py balloon
```

Set `HEADLESS=1` only for automated testing; the default opens visible Chrome.
