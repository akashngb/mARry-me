# mARry-me

## Run

### 1. Start the Python service

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
.venv/bin/python server.py
```

### 2. Start the Node server

```bash
cd server
npm install
cp .env.example .env    # add ANTHROPIC_API_KEY + FAL_KEY (+ optional PARTY_CITY_URL)
npm start
```

### 3. Open the app

Go to **http://localhost:8787**.
