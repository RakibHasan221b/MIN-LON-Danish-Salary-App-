# Deployment guide

Target setup: the Next.js frontend on Vercel, the FastAPI backend on a
separate host (Render or Railway), talking to each other over HTTPS. The
backend is never assumed to run on Vercel itself.

This guide covers the deployment-infrastructure side only. It does not
change any tax logic, calculation behavior, or UI behavior, those are
documented in `docs/research_2026.md`, `docs/tax_data_verification_checklist.md`,
and `docs/v1_2_implementation_audit.md`.

## 1. Backend on Render or Railway

Both platforms work the same way for this project: point them at the
repository root, use Python 3.10+ (the app is tested against 3.10), and
run the commands below.

**Install command:**
```
pip install -r requirements.txt
```

**Start command:**
```
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```
Both Render and Railway set a `$PORT` environment variable automatically;
the app must bind to it, not a hardcoded port. Do not use `--reload` in
production, that flag is for local development only.

**Required environment variables (backend):**

| Variable | Required | Purpose |
|---|---|---|
| `CORS_ALLOWED_ORIGINS` | Yes, for production | Comma-separated list of frontend origins allowed to call this API from a browser. Example: `https://min-loen.vercel.app,https://www.min-loen.dk`. If unset, the API only allows `http://localhost:3000` and `http://127.0.0.1:3000`, so a deployed frontend will get CORS errors until this is set. |
| `CURRENCY_API_KEY` | No | Optional. Only needed to use a keyed currency provider instead of the default free, keyless one. Leave unset unless you have a reason to use the keyed provider. |

**Health check:** the API exposes `GET /health` (returns `{"status": "ok"}`),
use this as the platform's health check endpoint if it asks for one.

## 2. Frontend on Vercel

Point Vercel at the `web/` directory as the project root (both Render/
Railway's project root and Vercel's project root need to be set correctly
since this is a single repo with both `api/`+`app/` for the backend and
`web/` for the frontend side by side).

**Build command:** `npm run build` (Vercel detects this automatically for
a Next.js project).

**Required environment variables (frontend, set in Vercel's project
settings, not committed to the repo):**

| Variable | Required | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | The deployed backend's base URL, e.g. `https://min-loen-api.onrender.com`. Without this, the frontend falls back to `http://localhost:8000`, which will not work once deployed. |

`NEXT_PUBLIC_*` variables are baked into the frontend build (they are
public by design, this is standard Next.js behavior), so do not put a
secret in a `NEXT_PUBLIC_*` variable.

## 3. Wiring the two together

1. Deploy the backend first (Render or Railway), note its public URL.
2. Set `CORS_ALLOWED_ORIGINS` on the backend once you know the frontend's
   final URL (you can set this after step 3 and redeploy the backend,
   the two steps can happen in either order, just make sure both are set
   before relying on the deployed app).
3. Deploy the frontend on Vercel with `NEXT_PUBLIC_API_URL` set to the
   backend's URL from step 1.
4. After both are live, confirm `CORS_ALLOWED_ORIGINS` on the backend
   includes the frontend's actual Vercel URL, then redeploy the backend
   if you changed it.

## 4. Local development (unchanged)

Local development continues to work exactly as before, no environment
variables are required for local use:

```
pip install -r requirements-dev.txt
pytest app/tests/ -v
uvicorn api.main:app --reload --port 8000
```

```
cd web
npm install
npm run dev
```

The backend's CORS defaults already allow `http://localhost:3000`, and
the frontend's default `NEXT_PUBLIC_API_URL` is `http://localhost:8000`,
so no `.env` files are required for local development. `.env.example`
and `web/.env.local.example` document the variables you would set for a
non-default local setup or for production.

## 5. Known open item, deliberately deferred

`npm audit` currently reports 1 high and 1 critical vulnerability, both
tracing back to `next@14.2.35` (and a transitive `postcss` dependency).
The only fix path `npm audit fix` offers is a jump to `next@16.x`, which
is a breaking major version change. This is intentionally NOT addressed
in this deployment-hardening pass, it needs its own branch and its own
test pass against the existing frontend code (`page.tsx`, `ResultBreakdown.tsx`,
and the other components) before being merged. Track this as a follow-up
task before, or shortly after, going live. Running the app in production
on the current Next.js version carries this known, documented risk in the
meantime.

## 6. What is intentionally NOT covered here

- Android (Phase 7) remains not started, per prior direction.
- Logging/observability, rate limiting, and CI are not set up as part of
  this pass, they were flagged in the pre-deployment review but are
  separate decisions the project owner should make deliberately rather
  than have defaulted for them.
- Custom domains, TLS certificates, and platform-specific scaling
  settings are standard Render/Railway/Vercel configuration and are not
  specific to this project, refer to each platform's own docs for that.
