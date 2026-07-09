"""
Local fallback for one-time OAuth2 authorization of the Mautic integration.

Prefer opening authorize_url() in a browser directly against a running
deployment: MAUTIC_REDIRECT_URI points at api/routes/oauth.py's
/oauth/callback route, which completes the code exchange server-side the
instant the browser redirects there. Mautic expires authorization codes
within roughly a minute, often faster — a manual copy-paste from browser to
this script's prompt frequently loses that race (that's why the callback
route exists at all). Only use this script if MAUTIC_REDIRECT_URI points
somewhere that isn't running the /oauth/callback route.

Usage:
    python crm/scripts/mautic_authorize.py

The refresh token is written to the platform DB (platform_integration_tokens
— see app/integrations/mautic.py), not .env, so it survives redeploys.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.integrations.mautic import authorize_url, exchange_code_for_tokens


async def main() -> None:
    if not settings.mautic_base_url or not settings.mautic_client_id:
        print("MAUTIC_BASE_URL / MAUTIC_CLIENT_ID are not set — nothing to authorize.", file=sys.stderr)
        sys.exit(1)

    print("Open this URL in a browser, log into Mautic, and approve access:\n")
    print(authorize_url())
    print(
        "\nYou'll land on the redirect URI with a 404 (expected) — copy the "
        "value after '?code=' from the browser's address bar."
    )
    code = input("\nPaste the code here: ").strip()
    if not code:
        print("No code entered, aborting.", file=sys.stderr)
        sys.exit(1)

    tokens = await exchange_code_for_tokens(code)
    print(f"\nSuccess. Access token obtained (expires in {tokens.get('expires_in')}s).")
    print("Refresh token stored in the platform DB — the app will keep itself refreshed from here.")


if __name__ == "__main__":
    asyncio.run(main())
