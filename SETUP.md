# Setup checklist

Everything still to do before the site takes real client work. Tick items off as you go.
If you've already done a step, skip it.

---

## 1. Database: Supabase

- [ ] Create a project at https://supabase.com. Pick the region closest to Render's (Frankfurt, `eu-central-1`).
- [ ] Go to **Project Settings > Database > Connection string**, choose **Session pooler**, and copy the URI.
  It looks like `postgresql://postgres.<ref>:<password>@aws-0-eu-central-1.pooler.supabase.com:5432/postgres`.
  - Use the Session pooler, not "Direct connection" (that one is IPv6-only and Render can't reach it).
  - If your database password has symbols like `@ # / ?`, URL-encode them (for example `@` becomes `%40`), or reset the password to letters and numbers.
- [ ] In Render, open **deon-api > Environment**, set `DATABASE_URL` to that URI, and save. Render redeploys.
- [ ] Check it worked: in Supabase's **Table Editor** you should see `projects`, `invoices`, `payments`, `quotes`, `project_updates`, and the demo project `DO-DEMO01`.
- [ ] Delete the old Render database `deon-db` (Render > deon-db > Settings > Delete). It only had test data.

## 2. Email: Resend

- [ ] At https://resend.com go to **Domains > Add domain** and enter `deon.ardena.co.ke`.
- [ ] Add the DNS records Resend shows (MX, SPF TXT, DKIM TXT) wherever the DNS for `ardena.co.ke` is managed. Wait for **Verified**.
- [ ] Go to **API Keys > Create API key** with "Sending access" and copy it.
- [ ] In Render (**deon-api > Environment**), set:
  - `RESEND_API_KEY` = the key
  - `EMAIL_FROM` = `Deon Orina <hello@deon.ardena.co.ke>` (any address on the verified domain)
  - `NOTIFY_EMAIL` = where you want quote and payment alerts (default `ceo@ardena.co.ke`)
- [ ] Check https://deon-api.onrender.com/health shows `"email":"on"`.

## 3. Test the emails

- [ ] Open https://deon.ardena.co.ke/admin, enter your admin key, and press **Send test emails** in the sidebar.
- [ ] Four samples should arrive at `NOTIFY_EMAIL`: quote received, project started, progress update, invoice.
- [ ] Check them on your phone too. If they land in spam, open one and mark it "Not spam". If it keeps happening, recheck the Resend DNS records.
- [ ] Send a real quote request from https://deon.ardena.co.ke/quote using your own email. You should get the client email *and* the alert.

## 4. Payments: PayHero

- [ ] `PAYHERO_API_USERNAME`, `PAYHERO_API_PASSWORD` and `PAYHERO_CHANNEL_ID` are set on Render (health shows `"payments":"live"`). Already done.
- [ ] In admin, go to **Pending amounts > Request a payment** and create a **KES 10** test for yourself, with your own email.
- [ ] Open the pay link, pay with your own M-Pesa, and confirm:
  - the success screen and receipt page load
  - the receipt email arrives, and you get the "Paid" alert
  - in admin, the amount moves from **Pending** to **Paid** and shows under **Payments**
- [ ] Try cancelling a prompt once, to see the "not completed" screen.

## 5. Admin

- [ ] Copy `ADMIN_KEY` from Render (**deon-api > Environment**). That's your password for `/admin` and `/invoice`.
- [ ] Don't share it or paste it anywhere public. If it leaks, change the value on Render; every browser gets locked out until the new key is entered.

## 6. Hosting

- [ ] **Render plan.** The free instance sleeps after about 15 minutes idle, so the first visitor waits up to a minute. Before taking real client payments, switch `deon-api` to a paid instance (Render > deon-api > Settings > Instance type).
- [ ] **Supabase free plan.** It pauses after a week with no activity. Normal site traffic keeps it awake. Consider the Pro plan once you rely on it for client records (it adds daily backups).
- [ ] **Vercel.** Confirm the site redeploys from `master` and that `deon.ardena.co.ke` points to it.

## 7. Content and SEO

- [ ] Fix or remove the **als** project link (`als.ardena.co.ke` didn't resolve when last checked).
- [ ] Optional: add your KRA PIN in `script.js` (`BUSINESS.pin`) so it prints on invoices and receipts.
- [ ] Google Search Console: verify the site (the `google...html` file is already in the repo) and submit `https://deon.ardena.co.ke/sitemap.xml`.

---

## How the day-to-day works

1. **A quote request comes in.** The client gets a warm confirmation, and you get the brief by email and under **Quotes** in admin.
2. **They accept.** In **Quotes**, press **Start a project from this**. The client is emailed a tracking code.
3. **Ask for the deposit.** On the project, press **Request payment** (or use **Pending amounts**). The client gets an email with a Pay button. Entering the invoice number on `/pay` shows them the pending amount.
4. **Paid in cash or by bank?** In **Pending amounts**, use **Record a payment** so the balance and receipts stay right.
5. **Keep them posted.** Use **Post update** with the stage, a percentage and an optional staging link. Untick "Email the client" for small changes.
6. **Change status anytime.** Use the **Status** dropdown (Active / On hold / Completed). Clients see it on `/track`.
7. **Finish.** Post a "Complete" update or set the status to Completed, and request the balance.

Anyone curious can see a sample project at https://deon.ardena.co.ke/track?demo=1.
