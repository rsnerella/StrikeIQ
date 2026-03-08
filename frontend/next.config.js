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
        hostname: "localhost",
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
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },

  /*
  Allow Next.js dev server to accept requests from
  mobile devices on the same network.
  */

  allowedDevOrigins: [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
  ],
};

module.exports = nextConfig;