"""PayHero M-Pesa client.

Docs: https://docs.payhero.co.ke  (STK push: POST /payments, status: GET /transaction-status)
Credentials stay on the server; the browser only ever talks to this API.
"""

import httpx

from .config import get_settings


class PayHeroError(Exception):
    pass


def _client() -> httpx.AsyncClient:
    s = get_settings()
    return httpx.AsyncClient(
        base_url=s.payhero_base_url,
        auth=httpx.BasicAuth(s.payhero_api_username, s.payhero_api_password),
        timeout=httpx.Timeout(25.0),
        headers={"Accept": "application/json"},
    )


async def stk_push(*, amount: int, phone: str, reference: str, name: str) -> dict:
    """Send the M-Pesa prompt. `phone` is 2547XXXXXXXX. Returns PayHero's JSON
    (includes `reference` and `CheckoutRequestID`)."""
    s = get_settings()
    body = {
        "amount": amount,
        "phone_number": "0" + phone[3:],
        "channel_id": s.payhero_channel_id,
        "provider": "m-pesa",
        "external_reference": reference,
        "customer_name": name[:60],
        "callback_url": f"{s.public_api_url.rstrip('/')}/api/payhero/callback/{s.payhero_callback_secret}",
    }
    try:
        async with _client() as c:
            r = await c.post("/payments", json=body)
    except httpx.HTTPError as e:
        raise PayHeroError("Could not reach M-Pesa. Please try again.") from e
    data = _json(r)
    if r.status_code >= 400 or not data.get("success", False):
        raise PayHeroError(data.get("error_message") or data.get("message") or "M-Pesa did not accept the request.")
    return data


async def transaction_status(payhero_reference: str) -> dict:
    """Returns PayHero's view of a payment: status is QUEUED, SUCCESS or FAILED."""
    try:
        async with _client() as c:
            r = await c.get("/transaction-status", params={"reference": payhero_reference})
    except httpx.HTTPError as e:
        raise PayHeroError("status check failed") from e
    if r.status_code >= 400:
        raise PayHeroError(f"status check failed ({r.status_code})")
    return _json(r)


def _json(r: httpx.Response) -> dict:
    try:
        data = r.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}
