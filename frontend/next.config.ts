import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:5050/api/:path*",
      },
      {
        source: "/latest",
        destination: "http://127.0.0.1:5050/latest",
      },
      {
        source: "/stream",
        destination: "http://127.0.0.1:5050/stream",
      },
      {
        source: "/health",
        destination: "http://127.0.0.1:5050/health",
      },
    ];
  },
};

export default nextConfig;
