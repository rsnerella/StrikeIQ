self.__BUILD_MANIFEST = {
  "/": [
    "static/chunks/pages/index.js"
  ],
  "/auth": [
    "static/chunks/pages/auth.js"
  ],
  "/auth/success": [
    "static/chunks/pages/auth/success.js"
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
    "/IntelligenceDashboard",
    "/IntelligenceDashboardFinal",
    "/_app",
    "/_error",
    "/auth",
    "/auth/error",
    "/auth/success",
    "/dashboard",
    "/production"
  ]
};self.__BUILD_MANIFEST_CB && self.__BUILD_MANIFEST_CB()