# Deployment Guide — Shariah Audit System

Stack: Railway (Python backend) + Netlify (Next.js frontend) + Supabase (database)

---

## Step 1 — Push code to GitHub

### 1a. Create two GitHub repositories

Go to https://github.com/new and create:
- `shariah-auditor`   ← for the Python backend
- `shariah-dashboard` ← for the Next.js frontend

Keep both **private**.

### 1b. Push the Python backend

Open a terminal in your `shariah_auditor/` folder:

```bash
cd shariah_auditor

git init
git add .
git commit -m "Initial commit — Shariah audit backend"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/shariah-auditor.git
git push -u origin main
```

### 1c. Push the Next.js frontend

Open a terminal in your `shariah_dashboard/` folder:

```bash
cd shariah_dashboard

git init
git add .
git commit -m "Initial commit — Shariah audit dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/shariah-dashboard.git
git push -u origin main
```

---

## Step 2 — Set up Supabase (if not done yet)

1. Go to https://supabase.com → Sign up → New project
2. Choose a region close to Malaysia (Singapore is closest)
3. Once the project is ready, go to **SQL Editor**
4. Paste the entire contents of `supabase/schema.sql` and click **Run**
5. Go to **Settings → API** and copy:
   - **Project URL** (looks like `https://xxxx.supabase.co`)
   - **service_role** key (under "Project API keys" — use the secret key, NOT anon)

Keep these — you'll need them for both Railway and Netlify.

---

## Step 3 — Deploy the Python backend to Railway

### 3a. Sign up for Railway

Go to https://railway.app → **Start a New Project** → sign in with GitHub.

### 3b. Create a new project

1. Click **New Project → Deploy from GitHub repo**
2. Select your `shariah-auditor` repository
3. Railway auto-detects Python and reads your `Procfile`

### 3c. Set environment variables

In Railway → your project → **Variables** tab, add:

| Variable              | Value                                  |
|-----------------------|----------------------------------------|
| `ANTHROPIC_API_KEY`   | `sk-ant-...` (your Anthropic key)      |
| `SUPABASE_URL`        | `https://xxxx.supabase.co`             |
| `SUPABASE_SERVICE_KEY`| your Supabase service_role key         |
| `FRONTEND_URL`        | leave blank for now (fill after Step 4)|

### 3d. Deploy

Click **Deploy**. Railway will:
- Install Python dependencies from `requirements.txt`
- Start the server: `uvicorn api:app --host 0.0.0.0 --port $PORT`
- Run the `/health` check to confirm it's live

Once deployed, copy your Railway URL — it looks like:
```
https://shariah-auditor-production.up.railway.app
```

### 3e. Test the backend

Open your browser and go to:
```
https://your-railway-url.up.railway.app/health
```
You should see: `{"status": "ok", "service": "shariah-audit-api"}`

Also visit the auto-generated docs:
```
https://your-railway-url.up.railway.app/docs
```

---

## Step 4 — Deploy the Next.js frontend to Netlify

### 4a. Sign up for Netlify

Go to https://netlify.com → **Sign up** → **Sign up with GitHub**.

### 4b. Import your repository

1. Click **Add new site → Import an existing project**
2. Choose **GitHub** → select `shariah-dashboard`
3. Netlify reads `netlify.toml` automatically — no build settings to change

### 4c. Set environment variables

In Netlify → your site → **Site configuration → Environment variables**, add:

| Variable                    | Value                                              |
|-----------------------------|----------------------------------------------------|
| `BACKEND_URL`               | your Railway URL (from Step 3d)                   |
| `NEXT_PUBLIC_SUPABASE_URL`  | `https://xxxx.supabase.co`                        |
| `SUPABASE_SERVICE_KEY`      | your Supabase service_role key                     |

### 4d. Deploy

Click **Deploy site**. Netlify will:
- Run `npm run build`
- Deploy the Next.js app with the `@netlify/plugin-nextjs` plugin

Once done, copy your Netlify URL — it looks like:
```
https://shariah-audit-dashboard.netlify.app
```

### 4e. Update Railway with the frontend URL

Go back to Railway → **Variables** → update `FRONTEND_URL` with your Netlify URL.
Then click **Redeploy** so the CORS middleware allows your frontend domain.

---

## Step 5 — Verify the full system

Open your Netlify URL in a browser and:

1. **Dashboard** loads with seed data from Supabase
2. Go to **/upload** → upload `data/bnm_policies/bnm_sgf_2019_sample.txt`
   (rename to `.txt` if needed — the upload accepts text files)
3. Enter a contract ID like `MUR-2024-0099` → click **Start Shariah Audit**
4. Watch the **/audit/MUR-2024-0099** page — phases should advance every few seconds
5. When escalated, go to **/review/MUR-2024-0099** → enter a decision
6. Check Supabase **Table Editor → audits** — your record should be there with all fields populated

---

## Environment variable summary

### Railway (Python backend)
```
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
FRONTEND_URL=https://your-site.netlify.app
```

### Netlify (Next.js frontend)
```
BACKEND_URL=https://your-project.up.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

---

## Redeployment (after code changes)

Both Railway and Netlify watch your GitHub `main` branch.
Push any change and both services redeploy automatically:

```bash
# Backend change
cd shariah_auditor
git add .
git commit -m "Your change"
git push

# Frontend change
cd shariah_dashboard
git add .
git commit -m "Your change"
git push
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Railway build fails | Check `requirements.txt` has `fastapi` and `uvicorn` |
| `/health` returns 502 | Check Railway logs — likely a missing env var |
| Netlify build fails | Check `netlify.toml` is in the repo root |
| CORS error in browser | Confirm `FRONTEND_URL` in Railway matches your Netlify URL exactly |
| Supabase auth error | Make sure you're using `service_role` key, not `anon` key |
| Agents not calling Claude | Confirm `ANTHROPIC_API_KEY` is set in Railway variables |
