# mARry me — Lucy Live (backend + web page)

A tiny Express server that:

- serves a **single web page** (`public/index.html`) — laptop webcam → **Decart Lucy 2.5**
  realtime video effects (via **fal.ai**, WebRTC), with prompts sharpened by **Claude**
- proxies the API keys so they never reach the browser

## Run

```bash
npm install
```
```bash
cp .env.example .env    # then add ANTHROPIC_API_KEY + FAL_KEY
```
```bash
npm start               # -> http://localhost:8787
```

Open **http://localhost:8787** in Chrome/Edge, click **Start camera + Lucy**, allow the
camera, then tap a preset or type an effect. `localhost` is a secure origin, so the webcam
works over plain http.

## Endpoints

- `GET /` — the web page
- `POST /rewrite {command}` → `{prompt}` — Claude turns a spoken/typed command into a Lucy prompt
- `POST /fal/token {app}` → `{token}` — short-lived fal realtime token (keeps `FAL_KEY` server-side)
- `POST /party {command}` — forwards a decoration swap to the Party City cart automation (`PARTY_CITY_URL`, default `http://127.0.0.1:5000/change`)
- `GET /health`

## Party City cart integration

The page runs two things off the same command:

1. **AR restyle** — Claude → Lucy transforms the live venue feed.
2. **Real cart** — when the command mentions **balloon** or **piñata**, the page
   also `POST`s it to `/party`, which forwards to the Python/Flask automation in
   `../server.py`. That opens a visible Chrome window and swaps the item in the
   real Party City cart (removes the old item, adds the new one).

So saying *"switch balloons to piñata"* both restyles the venue **and** opens
Party City to remove the balloons and add a piñata. Start that service first:

```bash
cd ..                                   # repo root
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
.venv/bin/python server.py              # Flask on http://127.0.0.1:5000
```

If the Party City service is not running, the AR effect still works; the cart
swap is skipped and logged in the on-page LOG box.

Keys live only in `.env` (git-ignored). The Lucy WebRTC signaling mapping in
`public/index.html` logs every message to the on-page LOG box for easy tuning.
