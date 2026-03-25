/** @type {import('next').NextConfig} */

const nextConfig = {
  reactStrictMode: true,

  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ]
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

  turbopack: {
    root: __dirname,
  },

  allowedDevOrigins: ["*"],
};

module.exports = nextConfig;