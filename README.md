# 🎵 Music Theory Agent — Web Version

A browser-based conversational voice agent for music theory, powered by [AssemblyAI's Voice Agent API](https://www.assemblyai.com/docs/voice-agents/voice-agent-api/overview).

**Live demo:** `https://YOUR_GITHUB_USERNAME.github.io/music-theory-agent`

---

## Architecture

```
Browser (GitHub Pages)
  └─ fetches temp token → FastAPI backend (Render)
  └─ WebSocket → AssemblyAI Voice Agent API
```

Your API key lives only on Render — never in the browser.

---

## Deployment

### Step 1 — Deploy the backend to Render

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → **New → Web Service**.
3. Connect your GitHub repo and select the `backend/` folder as the root directory (or set the working directory).
4. Fill in:
   - **Runtime:** Python 3.11
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `ASSEMBLYAI_API_KEY` = your AssemblyAI API key
6. Click **Deploy**. Copy the URL Render gives you (e.g. `https://music-agent-xyz.onrender.com`).

### Step 2 — Update CORS and frontend config

In `backend/main.py`, replace `YOUR_GITHUB_USERNAME` in `ALLOWED_ORIGINS` with your actual GitHub username.

In `frontend/index.html`, replace `YOUR_RENDER_APP` in `BACKEND_URL` with your actual Render URL:
```js
const BACKEND_URL = 'https://music-agent-xyz.onrender.com';
```

Commit and push both changes.

### Step 3 — Enable GitHub Pages

1. Go to your repo on GitHub → **Settings → Pages**.
2. Under **Source**, select **Deploy from a branch**.
3. Choose `main` branch and set the folder to `/frontend`.
4. Click **Save**.

GitHub will publish your site at:
`https://YOUR_GITHUB_USERNAME.github.io/REPO_NAME`

---

## Local development

```bash
# Backend
cd backend
pip install -r requirements.txt
ASSEMBLYAI_API_KEY=your_key uvicorn main:app --reload --port 8000

# Frontend — open in browser via Live Server or:
cd frontend
python -m http.server 5500
# then open http://localhost:5500
```

Make sure `BACKEND_URL` in `index.html` points to `http://localhost:8000` during local dev.

---

## Project structure

```
music-theory-agent/
├── backend/
│   ├── main.py           # FastAPI server — mints tokens
│   └── requirements.txt
└── frontend/
    └── index.html        # Single-file browser app
```

---

## Notes

- **Render free tier** spins down after 15 min of inactivity — the first request after sleep takes ~30s. Upgrade to a paid plan if you need always-on.
- **Microphone access** requires HTTPS — both GitHub Pages and Render serve HTTPS by default, so you're covered.
- The browser connects directly to AssemblyAI after getting the token, so audio never passes through your backend.

---

## License

MIT
