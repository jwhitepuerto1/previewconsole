from fastapi import FastAPI

from app.core.config import settings  # validates env vars on boot
from app.middleware.auth import AuthMiddleware
from app.middleware.preview import PreviewIsolationMiddleware
from app.api.routes import accounts, auth, dashboard, pipeline, preview, targets

app = FastAPI(
    title="IAS Capital Raise Module",
    description="Preview Mode marketing demo + real account/rep-tools Phase 1.",
    version="0.2.0",
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


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "environment": settings.environment}
