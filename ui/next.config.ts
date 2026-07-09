import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server.js output — much smaller Docker image, no need
  // to ship node_modules or run `next start` against the full source tree.
  output: "standalone",
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";
    return [
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
      // /auth/* is mounted with no /api prefix on the backend (matches
      // spec section 8's literal /auth/login) — needs its own rewrite or
      // Next.js 404s it as an unmatched app route.
      { source: "/auth/:path*", destination: `${apiUrl}/auth/:path*` },
      // Mautic's OAuth2 redirect target — see app/api/routes/oauth.py.
      { source: "/oauth/:path*", destination: `${apiUrl}/oauth/:path*` },
    ];
  },
};

export default nextConfig;
