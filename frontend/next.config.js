/** @type {import('next').NextConfig} */

const nextConfig = {
  reactStrictMode: false,

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
};

module.exports = nextConfig;