# Deon API

FastAPI backend for deon.ardena.co.ke: quote requests, invoices, M-Pesa payments through PayHero, receipts, and client project tracking.

## Deploy on Render

1. In Render: **New > Blueprint**, pick the `Deon62/deon` repo. `render.yaml` creates the `deon-api` web service and the `deon-db` Postgres database.
2. When asked, fill in `PAYHERO_API_USERNAME`, `PAYHERO_API_PASSWORD` and `PAYHERO_CHANNEL_ID` (PayHero dashboard > API Keys / Payment Channels).
3. `ADMIN_KEY` and `PAYHERO_CALLBACK_SECRET` are generated for you. Copy `ADMIN_KEY` from the service's Environment tab: it opens `/admin` and the invoice builder.
4. If Render gives the service a URL other than `https://deon-api.onrender.com`, update `PUBLIC_API_URL` here and `API` at the top of `script.js`.

Payments stay switched off (the pay page says so) until the three PayHero values are set.

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
- Render's free Postgres expires after a trial period. Check the current terms and move to a paid database before real client data goes in.
