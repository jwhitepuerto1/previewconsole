from fastapi import FastAPI

from app.core.config import settings  # validates env vars on boot
from app.middleware.auth import AuthMiddleware
from app.middleware.preview import PreviewIsolationMiddleware
from app.api.routes import (
    accounts, alerts, auth, campaigns, dashboard, data_room, email_sequences,
    funding, linkedin, meetings, notes, oauth, onboarding, pipeline, preview,
    reports, support, targets,
)

app = FastAPI(
    title="IAS Capital Raise Module",
    description="Preview Mode marketing demo + real account/rep-tools Phase 1 + Phase 2 campaign workflow + Phase 3 data room/onboarding/funding + Phase 4 support dashboard.",
    version="0.5.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Starlette runs the LAST-added middleware FIRST — Auth must populate
# request.state before Preview isolation reads it.
app.add_middleware(PreviewIsolationMiddleware)
app.add_middleware(AuthMiddleware)

app.include_router(preview.router, prefix="/api/preview", tags=["Preview"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(targets.router, prefix="/api/targets", tags=["Targets"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["Pipeline"])
app.include_router(oauth.router, tags=["OAuth"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(email_sequences.router, prefix="/api/email-events", tags=["Email Sequences"])
app.include_router(linkedin.router, prefix="/api/linkedin", tags=["LinkedIn"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["Meetings"])
app.include_router(notes.router, prefix="/api/notes", tags=["Notes"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(data_room.router, prefix="/api/data-room", tags=["Data Room"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(funding.router, prefix="/api/funding", tags=["Funding"])
app.include_router(support.router, prefix="/api/support", tags=["Support"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "environment": settings.environment}
