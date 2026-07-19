/**
 * Dedicated streaming passthrough for the SSE alert feed.
 *
 * next.config.ts's rewrites() proxy every other /api/* route fine, but
 * confirmed in production: its internal proxy buffers the entire response
 * rather than streaming it, which is fatal for a long-lived SSE connection —
 * the alert stream never delivered anything through the rewrite, even after
 * 10s+. A literal (non-dynamic) file-based route here takes precedence over
 * the array-form /api/:path* rewrite for this exact path (Next.js checks
 * filesystem routes before applying array-form rewrites), so only this one
 * path bypasses the rewrite and manually forwards the backend's stream body
 * instead of buffering it.
 */
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";
  const authHeader = request.headers.get("authorization");

  const backendResponse = await fetch(`${apiUrl}/api/alerts/stream`, {
    headers: authHeader ? { authorization: authHeader } : undefined,
  });

  return new Response(backendResponse.body, {
    status: backendResponse.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      // Must be forwarded, not just set on the FastAPI response — Elestio's
      // own outer edge proxy (in front of this whole compose stack, a layer
      // no local test ever exercises) sits beyond this route entirely, and
      // only sees headers this Response object itself sends.
      "X-Accel-Buffering": "no",
    },
  });
}
