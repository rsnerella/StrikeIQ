/** @type {import('next').NextConfig} */

const nextConfig = {
  reactStrictMode: false,

  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  },

  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: "http",
        hostname: "**",
        port: "8000",
      },
      {
        protocol: "http",
        hostname: "**",
      },
    ],
  },

  allowedDevOrigins: ["*"],
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'https://strikeiq-production-e1cd.up.railway.app/api/v1/:path*',
      },
    ]
  },
};

module.exports = nextConfig;