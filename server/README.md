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
- `GET /health`

Keys live only in `.env` (git-ignored). The Lucy WebRTC signaling mapping in
`public/index.html` logs every message to the on-page LOG box for easy tuning.
