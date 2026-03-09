/** @type {import('next').NextConfig} */

const nextConfig = {
  reactStrictMode: true,

  turbopack: {
    root: __dirname,
  },

  images: {
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

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*", // FIXED
      },
    ];
  },

  allowedDevOrigins: ["*"],
};

module.exports = nextConfig;