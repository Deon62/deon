"""Transactional email through Resend (https://resend.com).

Every email is a branded HTML layout (tables + inline styles, so it renders the
same in Gmail, Outlook and Apple Mail) with a plain-text twin. Sending happens
in a background task, so a slow or failed email never blocks a request.
"""

import logging
from datetime import date, datetime
from html import escape
from urllib.parse import quote as urlquote

import httpx

from .config import get_settings

log = logging.getLogger("deon.email")

INK, MUTED, FAINT, LINE, GREEN, GREEN_SOFT, BG = "#16181D", "#5B5E66", "#8A8C93", "#E8E4DC", "#0B6B53", "#E4F0EA", "#F7F7F5"
FONT = "'Manrope','Helvetica Neue',Helvetica,Arial,sans-serif"
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"

SERVICE_NAMES = {
    "website": "Websites", "webapp": "Web applications", "mobile": "Mobile apps", "payments": "Payments & APIs",
    "ai": "AI engineering", "contracts": "Smart contracts", "data": "Data science", "care": "Maintenance",
    "consult": "Consultation",
}
EXTRA_NAMES = {
    "mpesa": "M-Pesa payments", "auth": "User accounts", "admin": "Admin dashboard", "cms": "Editable content",
    "design": "Custom design", "seo": "SEO setup",
}
TIMELINES = {"flexible": "Flexible", "standard": "Standard", "rush": "Urgent"}
STAGE_LABELS = {"discovery": "Discovery", "design": "Design", "build": "Build", "testing": "Testing", "launch": "Launch", "done": "Complete"}


# ── Sending ─────────────────────────────────────────────────────────────
def enabled() -> bool:
    return bool(get_settings().resend_api_key)


async def send(to: str | list[str], subject: str, html: str, text: str, reply_to: str | None = None) -> bool:
    """One email to one or more people. With several, they all see each other (a client team), so reply-all works."""
    s = get_settings()
    to = [t for t in ([to] if isinstance(to, str) else to) if t and "@" in t][:50]
    if not to:
        return False
    if not s.resend_api_key:
        log.info("email skipped (RESEND_API_KEY not set): %s -> %s", subject, to)
        return False
    body = {"from": s.email_from, "to": to, "subject": subject, "html": html, "text": text,
            "reply_to": reply_to or s.email_reply_to}
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post("https://api.resend.com/emails", json=body,
                             headers={"Authorization": f"Bearer {s.resend_api_key}"})
        if r.status_code >= 400:
            log.error("resend error %s for %r: %s", r.status_code, subject, r.text[:300])
            return False
        log.info("email sent: %s -> %s", subject, to)
        return True
    except httpx.HTTPError as e:
        log.error("resend unreachable for %r: %s", subject, e)
        return False


# ── Building blocks ─────────────────────────────────────────────────────
def e(s) -> str:
    return escape(str(s or ""))


def kes(n) -> str:
    return f"KES {int(round(n or 0)):,}"


def fmt_date(d) -> str:
    if isinstance(d, str):
        d = datetime.fromisoformat(d)
    return f"{d.day} {d:%b %Y}" if isinstance(d, (date, datetime)) else ""


def first_name(name: str) -> str:
    return (name or "").strip().split(" ")[0] or "there"


def url(path: str) -> str:
    return get_settings().site_url.rstrip("/") + path


def button(label: str, href: str, primary: bool = True) -> str:
    bg, fg, border = (GREEN, "#FFFFFF", GREEN) if primary else ("#FFFFFF", INK, "#C9C1B5")
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="display:inline-table;margin:0 8px 8px 0">'
        f'<tr><td align="center" bgcolor="{bg}" style="border-radius:999px;border:1px solid {border}">'
        f'<a href="{e(href)}" target="_blank" style="display:inline-block;padding:15px 30px;font-family:{FONT};font-size:12px;'
        f'font-weight:700;letter-spacing:1.6px;text-transform:uppercase;color:{fg};text-decoration:none;border-radius:999px">{e(label)}</a>'
        f'</td></tr></table>'
    )


def buttons(*items: str) -> str:
    return f'<div style="margin:32px 0 8px">{"".join(i for i in items if i)}</div>'


def p(html: str, muted: bool = False, size: int = 16) -> str:
    return f'<p style="margin:0 0 18px;font-family:{FONT};font-size:{size}px;line-height:1.65;color:{MUTED if muted else INK}">{html}</p>'


def details(rows: list[tuple[str, str]]) -> str:
    """Key/value table. Values are already-escaped HTML."""
    trs = "".join(
        f'<tr><td style="padding:13px 0;border-bottom:1px dashed {LINE};font-family:{FONT};font-size:14px;color:{MUTED};vertical-align:top;white-space:nowrap;padding-right:24px">{e(k)}</td>'
        f'<td align="right" style="padding:13px 0;border-bottom:1px dashed {LINE};font-family:{FONT};font-size:14px;color:{INK};vertical-align:top">{v}</td></tr>'
        for k, v in rows if v
    )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 8px;border-top:1px solid {INK}">{trs}</table>'


def label(text: str) -> str:
    return f'<p style="margin:36px 0 14px;font-family:{FONT};font-size:11px;font-weight:600;letter-spacing:2.4px;text-transform:uppercase;color:{FAINT}">{e(text)}</p>'


def steps(items: list[tuple[str, str]]) -> str:
    rows = "".join(
        f'<tr><td style="vertical-align:top;padding:0 16px 18px 0;width:28px">'
        f'<div style="width:28px;height:28px;border-radius:50%;background:{GREEN_SOFT};color:{GREEN};font-family:{FONT};font-size:12px;font-weight:700;line-height:28px;text-align:center">{i}</div></td>'
        f'<td style="vertical-align:top;padding:3px 0 18px;font-family:{FONT};font-size:15px;line-height:1.55;color:{INK}"><strong style="font-weight:600">{e(t)}</strong><br><span style="color:{MUTED}">{e(d)}</span></td></tr>'
        for i, (t, d) in enumerate(items, 1)
    )
    return f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">{rows}</table>'


def progress_bar(pct: int, stage: str) -> str:
    pct = max(0, min(100, int(pct)))
    fill = f'<td width="{pct}%" style="background:{GREEN};height:6px;font-size:0;line-height:0">&nbsp;</td>' if pct else ""
    rest = f'<td style="background:{LINE};height:6px;font-size:0;line-height:0">&nbsp;</td>' if pct < 100 else ""
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 6px"><tr>'
        f'<td style="font-family:{FONT};font-size:44px;font-weight:300;letter-spacing:-1.5px;color:{INK};line-height:1">{pct}%</td>'
        f'<td align="right" style="font-family:{FONT};font-size:14px;color:{MUTED};vertical-align:bottom">Stage: <strong style="color:{INK};font-weight:600">{e(STAGE_LABELS.get(stage, stage))}</strong></td>'
        f'</tr></table>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:14px 0 8px;border-radius:3px;overflow:hidden"><tr>{fill}{rest}</tr></table>'
    )


def code_box(code: str, caption: str) -> str:
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 8px">'
        f'<tr><td align="center" style="background:{BG};border:1px solid {LINE};padding:26px 16px">'
        f'<div style="font-family:{FONT};font-size:11px;font-weight:600;letter-spacing:2.4px;text-transform:uppercase;color:{FAINT}">{e(caption)}</div>'
        f'<div style="font-family:{MONO};font-size:28px;letter-spacing:4px;color:{INK};margin-top:10px">{e(code)}</div>'
        f'</td></tr></table>'
    )


def layout(*, preheader: str, heading: str, body: str, signoff: bool = True) -> str:
    s = get_settings()
    sign = p("Talk soon,<br><strong style='font-weight:600'>Deon</strong>", size=16) if signoff else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light"><title>{e(heading)}</title>
<style>@media (max-width:600px){{.card{{padding:32px 24px!important}}.wrap{{padding:16px 8px!important}}h1{{font-size:26px!important}}}}</style>
</head>
<body style="margin:0;padding:0;background:{BG};-webkit-text-size-adjust:100%">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent">{e(preheader)}&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BG}">
<tr><td align="center" class="wrap" style="padding:40px 16px">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:580px">
    <tr><td style="padding:0 4px 22px">
      <a href="{e(s.site_url)}" style="font-family:{FONT};font-size:24px;font-weight:600;letter-spacing:-0.6px;color:{INK};text-decoration:none">deon<span style="color:{GREEN}">.</span></a>
    </td></tr>
    <tr><td class="card" style="background:#FFFFFF;border:1px solid {LINE};padding:48px 44px">
      <h1 style="margin:0 0 22px;font-family:{FONT};font-size:30px;line-height:1.15;font-weight:400;letter-spacing:-0.8px;color:{INK}">{e(heading)}</h1>
      {body}
      {f'<div style="margin-top:36px">{sign}</div>' if sign else ''}
    </td></tr>
    <tr><td style="padding:28px 4px 0;font-family:{FONT};font-size:12px;line-height:1.7;color:{FAINT}">
      <strong style="color:{MUTED};font-weight:600">Deon Orina</strong> · Software Developer · Kenya<br>
      <a href="mailto:ceo@ardena.co.ke" style="color:{FAINT}">ceo@ardena.co.ke</a> · <a href="tel:+254702248984" style="color:{FAINT}">0702 248 984</a> ·
      <a href="{e(s.site_url)}" style="color:{FAINT}">deon.ardena.co.ke</a>
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""


def plain(*lines: str) -> str:
    return "\n".join(lines) + "\n\n--\nDeon Orina · Software Developer\nceo@ardena.co.ke · 0702 248 984 · deon.ardena.co.ke\n"


# ── Templates. Each returns (subject, html, text). ──────────────────────
def quote_received(q: dict) -> tuple[str, str, str]:
    name = first_name(q["name"])
    services = ", ".join(SERVICE_NAMES.get(s, s) for s in q["services"])
    extras = ", ".join(EXTRA_NAMES.get(x, x) for x in q.get("extras") or [])
    subject = f"Thanks, {name}. Your quote is on its way"
    body = (
        p(f"Thank you for thinking of me for this. Your request is in, and I'm already reading through it.")
        + p(f"You'll have a fixed, itemised quote from me within <strong style='font-weight:600'>24 hours</strong>, usually sooner. No surprises later: the price I quote is the price you pay.", muted=True)
        + label("Your request")
        + details([
            ("Reference", f'<span style="font-family:{MONO}">{e(q["number"])}</span>'),
            ("Services", e(services)),
            ("Extras", e(extras)),
            ("Timeline", e(TIMELINES.get(q.get("timeline"), q.get("timeline")))),
        ])
        + label("What happens next")
        + steps([
            ("I review your brief", "If anything needs clarifying, I'll ask a quick question by email."),
            ("You get a fixed quote", "Scope, price and timeline, all in writing."),
            ("We get started", "A 50% deposit kicks things off, and you get a link to follow progress live."),
        ])
        + buttons(
            button("Add more details", f"mailto:ceo@ardena.co.ke?subject={urlquote('Re: ' + q['number'])}"),
            button("See my work", url("/#work"), primary=False),
        )
        + p("Have files, examples or a deadline in mind? Just reply to this email.", muted=True, size=14)
    )
    html = layout(preheader="I'll send you a fixed quote within 24 hours.", heading=f"Thanks for reaching out, {name}.", body=body)
    text = plain(
        f"Thanks for reaching out, {name}.", "",
        "Your request is in, and I'm already reading through it. You'll have a fixed, itemised quote from me within 24 hours.", "",
        f"Reference: {q['number']}", f"Services: {services}", *( [f"Extras: {extras}"] if extras else [] ),
        f"Timeline: {TIMELINES.get(q.get('timeline'), q.get('timeline'))}", "",
        "What happens next:", "1. I review your brief", "2. You get a fixed quote", "3. We get started: a 50% deposit, and a link to follow progress live", "",
        "Reply to this email to add details.", "", "Talk soon,", "Deon",
    )
    return subject, html, text


def quote_notify(q: dict) -> tuple[str, str, str]:
    services = ", ".join(SERVICE_NAMES.get(s, s) for s in q["services"])
    who = q["name"] + (f" ({q['company']})" if q.get("company") else "")
    subject = f"New quote request {q['number']} from {who}"
    body = (
        p("A new quote request just came in. Reply to this email to answer the client directly.", muted=True)
        + details([
            ("Reference", f'<span style="font-family:{MONO}">{e(q["number"])}</span>'),
            ("Name", e(q["name"])), ("Company", e(q.get("company"))),
            ("Email", f'<a href="mailto:{e(q["email"])}" style="color:{GREEN}">{e(q["email"])}</a>'),
            ("Phone", e(q.get("phone"))), ("Services", e(services)),
            ("Extras", e(", ".join(EXTRA_NAMES.get(x, x) for x in q.get("extras") or []))),
            ("Timeline", e(TIMELINES.get(q.get("timeline"), q.get("timeline")))),
        ])
        + (label("Brief") + p(e(q["brief"]).replace("\n", "<br>"), size=15) if q.get("brief") else "")
        + buttons(button("Open admin", url("/admin")), button("Reply to client", f"mailto:{q['email']}?subject={urlquote('Your quote ' + q['number'])}", primary=False))
    )
    html = layout(preheader=f"{services} · {TIMELINES.get(q.get('timeline'), '')}", heading="New quote request", body=body, signoff=False)
    text = plain(subject, "", f"Email: {q['email']}", f"Phone: {q.get('phone') or '-'}", f"Services: {services}", "", q.get("brief") or "")
    return subject, html, text


def payment_receipt(pay: dict) -> tuple[str, str, str]:
    name = first_name(pay["name"])
    subject = f"Payment received: {kes(pay['amount'])}"
    receipt_url = url(f"/receipt?id={pay['receipt_token']}")
    rows = [
        ("Amount", f"<strong style='font-weight:600'>{kes(pay['amount'])}</strong>"),
        ("For", e(pay["description"])),
        ("M-Pesa code" if pay.get("method", "M-Pesa") == "M-Pesa" else pay["method"] + " ref", f'<span style="font-family:{MONO}">{e(pay["mpesa_code"])}</span>'),
        ("Receipt", f'<span style="font-family:{MONO}">{e(pay["receipt_number"])}</span>'),
        ("Date", e(fmt_date(pay["paid_at"]))),
    ]
    if pay.get("invoice"):
        rows.append(("Balance on " + pay["invoice"], "Paid in full" if not pay.get("balance") else kes(pay["balance"])))
    body = (
        p("Your payment came through. Thank you.")
        + p("Here are the details for your records. Your receipt is always available from the button below.", muted=True)
        + details(rows)
        + buttons(
            button("View receipt", receipt_url),
            button("Track your project", url(f"/track?code={pay['project_code']}"), primary=False) if pay.get("project_code") else "",
        )
    )
    html = layout(preheader=f"{kes(pay['amount'])} received. Your receipt is inside.", heading=f"Thank you, {name}.", body=body)
    text = plain(
        f"Thank you, {name}.", "", "Your payment came through.", "",
        f"Amount: {kes(pay['amount'])}", f"For: {pay['description']}", f"M-Pesa code: {pay['mpesa_code']}",
        f"Receipt: {pay['receipt_number']}", "", f"View receipt: {receipt_url}", "", "Talk soon,", "Deon",
    )
    return subject, html, text


def payment_notify(pay: dict) -> tuple[str, str, str]:
    subject = f"Paid: {kes(pay['amount'])} from {pay['name']}"
    body = details([
        ("Amount", f"<strong style='font-weight:600'>{kes(pay['amount'])}</strong>"), ("For", e(pay["description"])),
        ("From", e(pay["name"])), ("Email", e(pay["email"])), ("Phone", e("0" + pay["phone"][3:]) if pay["phone"] else ""),
        ("Method", e(pay.get("method", "M-Pesa"))),
        ("Code / ref", f'<span style="font-family:{MONO}">{e(pay["mpesa_code"])}</span>'),
        ("Receipt", e(pay["receipt_number"])),
    ]) + buttons(button("Open admin", url("/admin")))
    html = layout(preheader=pay["description"], heading="Payment received", body=body, signoff=False)
    return subject, html, plain(subject, pay["description"], f"M-Pesa: {pay['mpesa_code']}")


def project_welcome(pr: dict, money: dict | None = None) -> tuple[str, str, str]:
    """money (optional): {invoice, total, paid, balance, due_date, receipt_token} for the project's price."""
    name = first_name(pr["client_name"])
    track = url(f"/track?code={pr['code']}")
    team = pr.get("emails") or [pr["client_email"]]
    subject = f"We're underway: {pr['title']}"
    who = (
        f"Open your project page with this code and <strong style='font-weight:600'>{e(team[0])}</strong>."
        if len(team) == 1 else
        "Everyone on this email can open your project page with this code and their own email address: "
        + ", ".join(f"<strong style='font-weight:600'>{e(x)}</strong>" for x in team) + "."
    )
    payments = ""
    if money:
        payments = (
            label("Payments")
            + details([
                ("Agreed price", kes(money["total"])),
                ("Deposit received", f"<span style='color:{GREEN}'>{kes(money['paid'])}</span>" if money.get("paid") else ""),
                ("Balance", f"<strong style='font-weight:600'>{kes(money['balance'])}</strong>"),
                ("Balance due", e(fmt_date(money["due_date"])) if money.get("due_date") and money.get("balance") else ""),
                ("Invoice", f'<span style="font-family:{MONO}">{e(money["invoice"])}</span>'),
            ])
            + p("Pay the balance any time from your project page with M-Pesa, or by the method we agreed."
                if money.get("balance") else "The project is fully paid. Thank you.", muted=True, size=14)
        )
    body = (
        p(f"Your project <strong style='font-weight:600'>{e(pr['title'])}</strong> has officially started. Thank you for trusting me with it.")
        + p("You don't need to chase me for updates. Everything I ship, every milestone and any invoice shows up on your project page, and I'll email you when something important happens.", muted=True)
        + code_box(pr["code"], "Your project code")
        + p(who, muted=True, size=14)
        + buttons(
            button("Track your project", track),
            button("Deposit receipt", url(f"/receipt?id={money['receipt_token']}"), primary=False) if money and money.get("receipt_token") else "",
        )
        + (label("Target date") + p(e(fmt_date(pr["due_date"])), size=15) if pr.get("due_date") else "")
        + payments
    )
    html = layout(preheader=f"Your project code is {pr['code']}. Follow progress anytime.", heading=f"We're underway, {name}.", body=body)
    text = plain(
        f"We're underway, {name}.", "", f"Your project \"{pr['title']}\" has started.", "",
        f"Project code: {pr['code']}", f"Track it here (with {' or '.join(team)}): {track}",
        *([ "", f"Agreed price: {kes(money['total'])}", f"Deposit received: {kes(money['paid'])}",
            f"Balance: {kes(money['balance'])} (invoice {money['invoice']})"] if money else []),
        "", "Talk soon,", "Deon",
    )
    return subject, html, text


def project_update(pr: dict, up: dict) -> tuple[str, str, str]:
    name = first_name(pr["client_name"])
    track = url(f"/track?code={pr['code']}")
    done = up["stage"] == "done"
    subject = f"{'Complete' if done else 'Update'}: {pr['title']}, {up['title']}"
    body = (
        p(f"Hi {e(name)}, here's the latest on <strong style='font-weight:600'>{e(pr['title'])}</strong>.", muted=True)
        + progress_bar(up["progress"], up["stage"])
        + label("What's new")
        + (p(e(up["body"]).replace("\n", "<br>")) if up.get("body") else "")
        + buttons(
            button("Take a look", up["link"]) if up.get("link") else "",
            button("See full progress", track, primary=not up.get("link")),
        )
        + p("Questions or feedback? Just reply to this email.", muted=True, size=14)
    )
    heading = "Your project is complete." if done else up["title"]
    html = layout(preheader=f"{up['progress']}% · {STAGE_LABELS.get(up['stage'], up['stage'])}", heading=heading, body=body)
    text = plain(
        f"Hi {name},", "", f"Update on {pr['title']}: {up['title']}",
        f"Progress: {up['progress']}% ({STAGE_LABELS.get(up['stage'], up['stage'])})", "",
        up.get("body") or "", *( [f"Take a look: {up['link']}"] if up.get("link") else [] ),
        f"Full progress: {track}", "", "Talk soon,", "Deon",
    )
    return subject, html, text


def qty_note(qty) -> str:
    q = float(qty)
    return "" if q == 1 else f' <span style="color:{MUTED}">&times; {q:g}</span>'


def invoice_issued(inv: dict) -> tuple[str, str, str]:
    name = first_name(inv["client_name"])
    pay_url = url(f"/pay?inv={inv['number']}")
    paid = int(inv.get("paid") or 0)
    due = int(inv["balance"]) if inv.get("balance") is not None else inv["total"]
    subject = (f"Invoice {inv['number']}: balance of {kes(due)}" if paid
               else f"Invoice {inv['number']} from Deon Orina, {kes(inv['total'])}")
    items = "".join(
        f'<tr><td style="padding:12px 0;border-bottom:1px solid {LINE};font-family:{FONT};font-size:14px;color:{INK}">{e(i["desc"])}'
        f'{qty_note(i["qty"])}</td>'
        f'<td align="right" style="padding:12px 0;border-bottom:1px solid {LINE};font-family:{FONT};font-size:14px;color:{INK};white-space:nowrap">{kes(float(i["qty"]) * i["rate"])}</td></tr>'
        for i in inv["items"]
    )
    totals = (
        (f'<tr><td style="padding:10px 0 0;font-family:{FONT};font-size:14px;color:{MUTED}">VAT 16%</td><td align="right" style="padding:10px 0 0;font-family:{FONT};font-size:14px;color:{MUTED}">{kes(inv["vat"])}</td></tr>' if inv["vat"] else "")
        + (
            f'<tr><td style="padding:14px 0 0;font-family:{FONT};font-size:14px;color:{MUTED}">Total</td><td align="right" style="padding:14px 0 0;font-family:{FONT};font-size:14px;color:{MUTED}">{kes(inv["total"])}</td></tr>'
            f'<tr><td style="padding:10px 0 0;font-family:{FONT};font-size:14px;color:{GREEN}">Paid so far</td><td align="right" style="padding:10px 0 0;font-family:{FONT};font-size:14px;color:{GREEN}">&minus; {kes(paid)}</td></tr>'
            if paid else ""
        )
        + f'<tr><td style="padding:14px 0 0;font-family:{FONT};font-size:17px;font-weight:600;color:{INK}">{"Balance due" if paid else "Total due"}</td><td align="right" style="padding:14px 0 0;font-family:{FONT};font-size:17px;font-weight:600;color:{INK}">{kes(due)}</td></tr>'
    )
    body = (
        p(f"Hi {e(name)}, " + ("here's your invoice for the balance. Thank you for the payment so far." if paid else "here's your invoice.")
          + " You can pay it with M-Pesa in under a minute: tap the button, confirm, and approve the prompt on your phone.", muted=True)
        + details([
            ("Invoice", f'<span style="font-family:{MONO}">{e(inv["number"])}</span>'),
            ("Issued", e(fmt_date(inv["created_at"]))),
            ("Due", e(fmt_date(inv["due_date"])) if inv.get("due_date") else "On receipt"),
        ])
        + f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:20px 0 0">{items}{totals}</table>'
        + buttons(
            button(f"Pay {kes(due)} with M-Pesa", pay_url),
            button("Track your project", url(f"/track?code={inv['project_code']}"), primary=False) if inv.get("project_code") else "",
        )
        + (p(e(inv["notes"]).replace("\n", "<br>"), muted=True, size=14) if inv.get("notes") else "")
    )
    html = layout(preheader=f"{kes(due)} due. Pay with M-Pesa in a minute.", heading=f"Invoice {inv['number']}", body=body)
    text = plain(
        f"Hi {name},", "", f"Invoice {inv['number']}: {kes(inv['total'])}",
        *[f"- {i['desc']}: {kes(float(i['qty']) * i['rate'])}" for i in inv["items"]],
        *([f"Paid so far: {kes(paid)}", f"Balance due: {kes(due)}"] if paid else []), "",
        f"Pay with M-Pesa: {pay_url}", "", "Talk soon,", "Deon",
    )
    return subject, html, text
