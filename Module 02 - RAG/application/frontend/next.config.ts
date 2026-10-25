import type { NextConfig } from "next";

const backend = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Les appels /api/* du navigateur sont relayés vers le backend FastAPI :
  // le navigateur ne parle qu'au serveur Next.js (même origine, pas de CORS).
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
  experimental: {
    // Un modèle de raisonnement, ou un palier gratuit saturé, peut mettre plus de 30 s à répondre.
    proxyTimeout: 120_000,
  },
};

export default nextConfig;
