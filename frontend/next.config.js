/** @type {import('next').NextConfig} */

const nextConfig = {
  output: 'export',
  reactStrictMode: true,
  basePath: '/StrikeIQ',
  assetPrefix: '/StrikeIQ',

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