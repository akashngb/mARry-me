# mARry-me Party City demo

This demo accepts a JSON voice/AR command and uses a visible Chrome window to
swap a balloon or pinata in the Party City cart.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

Start the API and browser:

```bash
.venv/bin/python server.py
```

Then send either a structured target or a transcript:

```bash
curl -X POST http://127.0.0.1:5000/change \
  -H 'Content-Type: application/json' \
  -d '{"item":"balloon"}'

curl -X POST http://127.0.0.1:5000/change \
  -H 'Content-Type: application/json' \
  -d '{"transcript":"change balloon to pinata"}'
```

For a direct one-item browser test:

```bash
.venv/bin/python server.py balloon
```

Set `HEADLESS=1` only for automated testing; the default opens visible Chrome.