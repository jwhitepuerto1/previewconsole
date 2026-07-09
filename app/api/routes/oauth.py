"""
GET /oauth/callback — Mautic's OAuth2 redirect target for the one-time
authorization step (see scripts/mautic_authorize.py's docstring). Completes
the code exchange server-side, immediately on redirect, because Mautic
expires authorization codes too fast for a human to copy-paste the code
from the browser into a terminal.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.integrations.mautic import exchange_code_for_tokens

router = APIRouter()


@router.get("/oauth/callback", response_class=HTMLResponse)
async def mautic_oauth_callback(code: str | None = None, error: str | None = None):
    if error:
        return HTMLResponse(f"<p>Mautic authorization failed: {error}</p>", status_code=400)
    if not code:
        return HTMLResponse("<p>No code parameter received.</p>", status_code=400)

    try:
        await exchange_code_for_tokens(code)
    except Exception as exc:
        return HTMLResponse(f"<p>Token exchange failed: {exc}</p>", status_code=400)

    return HTMLResponse("<p>Mautic authorized successfully. You can close this tab.</p>")
