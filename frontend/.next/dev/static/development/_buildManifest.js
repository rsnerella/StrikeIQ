self.__BUILD_MANIFEST = {
  "/_error": [
    "static/chunks/pages/_error.js"
  ],
  "/dashboard": [
    "static/chunks/pages/dashboard.js"
  ],
  "__rewrites": {
    "afterFiles": [
      {
        "source": "/api/:path*"
      }
    ],
    "beforeFiles": [],
    "fallback": []
  },
  "sortedPages": [
    "/",
    "/AuthSuccess",
    "/_app",
    "/_error",
    "/auth",
    "/auth/error",
    "/auth/success",
    "/dashboard"
  ]
};self.__BUILD_MANIFEST_CB && self.__BUILD_MANIFEST_CB()