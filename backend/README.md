# Deon API

FastAPI backend for deon.ardena.co.ke: quote requests, invoices, M-Pesa payments through PayHero, receipts, and client project tracking.

## Database: Supabase

1. Create a project at https://supabase.com (region: closest to Frankfurt, e.g. `eu-central-1`).
2. **Project Settings > Database > Connection string**, pick **Session pooler**, copy the URI and put your database password in it:
   `postgresql://postgres.<ref>:<password>@aws-0-eu-central-1.pooler.supabase.com:5432/postgres`
3. Set that as `DATABASE_URL` on Render. Tables are created on the next boot.

Use the Session pooler, not the "Direct connection": the direct host is IPv6-only and Render can't reach it.

## Email: Resend

1. At https://resend.com, **Domains > Add domain**: `deon.ardena.co.ke` (or `ardena.co.ke`), and add the DNS records it shows wherever ardena.co.ke's DNS is managed. Wait for "Verified".
2. **API Keys > Create**, with "Sending access".
3. On Render set `RESEND_API_KEY`, and `EMAIL_FROM` to an address on the verified domain, e.g. `Deon Orina <hello@deon.ardena.co.ke>`.
4. Open `/admin` and press **Send test emails**: a sample of each client email lands in `NOTIFY_EMAIL`.

Emails sent: quote received (client + you), project started with tracking code, progress updates (toggle per update), invoice with a Pay button (toggle), payment receipt (client + you).

## Deploy on Render

The service runs at https://deon-api.onrender.com from `render.yaml` (root dir `backend`). Environment variables:
`DATABASE_URL`, `ADMIN_KEY`, `PAYHERO_API_USERNAME`, `PAYHERO_API_PASSWORD`, `PAYHERO_CHANNEL_ID`, `PAYHERO_CALLBACK_SECRET`,
`RESEND_API_KEY`, `EMAIL_FROM`, `PUBLIC_API_URL`, `CORS_ORIGINS`. `/health` shows whether payments, email and Postgres are on.

A sample project is created on boot so anyone can try the tracker: code `DO-DEMO01`, email `demo@deon.ardena.co.ke`
(or just open `/track?demo=1`). Set `SEED_DEMO=false` to stop that.

## Run locally

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                              # PAYHERO_MOCK=true fakes successful payments
uvicorn app.main:app --reload
```

Serve the site from the repo root (`npx serve` or `python -m http.server 5511`); pages on localhost call `http://localhost:8000`.
Interactive docs: http://localhost:8000/docs

## Endpoints

Public (the website):

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/quotes` | Save a quote request, returns `QT-YYYY-NNNN` |
| GET | `/api/invoices/{number}` | Total, paid and balance for the pay page (no contact details) |
| POST | `/api/payments` | Start an M-Pesa STK push. Invoice amounts are set by the server |
| GET | `/api/payments/{reference}` | Poll status; checks PayHero directly if the callback is slow |
| POST | `/api/payhero/callback/{secret}` | PayHero result callback |
| GET | `/api/receipts/{token}` | Receipt by its unguessable link token |
| POST | `/api/receipts/lookup` | Receipt number + M-Pesa code to receipt token |
| POST | `/api/track` | Project code + client email to progress, updates and invoices |

Admin (header `X-Admin-Key`): `/api/admin/quotes`, `/api/admin/invoices`, `/api/admin/payments`, `/api/admin/projects`, `/api/admin/projects/{code}/updates`.

## Notes

- Tables are created on startup. If you later change a column, add Alembic migrations.
- Render's free web service sleeps when idle; the first request after a quiet spell takes up to a minute. Pages ping `/health` on load to wake it early. Upgrade to a paid instance before relying on it for payments.
- Supabase's free plan pauses a project after a week with no activity; the site's traffic normally keeps it awake.
