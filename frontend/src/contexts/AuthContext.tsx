import React, {
  createContext,
  useContext,
  useReducer,
  useEffect,
  useRef,
  ReactNode
} from "react";

import api from "../api/axios";

/* ------------------------------------------------ */
/* TYPES */
/* ------------------------------------------------ */

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  loginUrl: string | null;
  mode: "LOADING" | "AUTH" | "READY" | "ERROR";
  backendStatus: "online" | "offline" | "unknown";
}

type AuthAction =
  | { type: "AUTH_CHECK_START" }
  | { type: "AUTH_CHECK_SUCCESS"; isAuthenticated: boolean }
  | { type: "AUTH_REQUIRED"; payload: { login_url: string } }
  | { type: "AUTH_CHECK_ERROR"; error: string }
  | { type: "BACKEND_OFFLINE" }
  | { type: "BACKEND_ONLINE" };

/* ------------------------------------------------ */
/* INITIAL STATE */
/* ------------------------------------------------ */

const initialState: AuthState = {
  isAuthenticated: false,
  isLoading: true,
  error: null,
  loginUrl: null,
  mode: "LOADING",
  backendStatus: "unknown"
};

/* ------------------------------------------------ */
/* REDUCER */
/* ------------------------------------------------ */

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {

    case "AUTH_CHECK_START":
      return {
        ...state,
        isLoading: true,
        error: null,
        mode: "LOADING"
      };

    case "AUTH_CHECK_SUCCESS":
      return {
        ...state,
        isAuthenticated: action.isAuthenticated,
        isLoading: false,
        error: null,
        mode: action.isAuthenticated ? "READY" : "AUTH",
        backendStatus: "online"
      };

    case "AUTH_REQUIRED":
      return {
        ...state,
        isAuthenticated: false,
        isLoading: false,
        error: "Authentication required",
        loginUrl: action.payload.login_url,
        mode: "AUTH",
        backendStatus: "online"
      };

    case "AUTH_CHECK_ERROR":
      return {
        ...state,
        isAuthenticated: false,
        isLoading: false,
        error: action.error,
        mode: "ERROR"
      };

    case "BACKEND_OFFLINE":
      return {
        ...state,
        backendStatus: "offline",
        isLoading: false,
        mode: "ERROR"
      };

    case "BACKEND_ONLINE":
      return {
        ...state,
        backendStatus: "online"
      };

    default:
      return state;
  }
}

/* ------------------------------------------------ */
/* CONTEXT */
/* ------------------------------------------------ */

interface AuthContextType {
  state: AuthState;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/* ------------------------------------------------ */
/* PROVIDER */
/* ------------------------------------------------ */

export function AuthProvider({ children }: { children: ReactNode }) {

  const [state, dispatch] = useReducer(authReducer, initialState);

  const authChecked = useRef(false);

  /* ---------------- AUTH CHECK ---------------- */

  const checkAuth = async () => {

    console.log("🔍 AUTH STATUS API CALL");

    dispatch({ type: "AUTH_CHECK_START" });

    try {

      const response = await api.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/status`, {
        timeout: 10000
      });

      const data = response.data;

      console.log("✅ AUTH STATUS RESPONSE:", data);

      dispatch({ type: "BACKEND_ONLINE" });

      if (data.authenticated) {

        dispatch({
          type: "AUTH_CHECK_SUCCESS",
          isAuthenticated: true
        });

      } else {

        dispatch({
          type: "AUTH_REQUIRED",
          payload: { login_url: data.login_url }
        });

      }

    } catch (error: any) {

      console.error("❌ AUTH STATUS FAILED", error.message);

      /* Backend unreachable */

      if (!error.response) {
        dispatch({ type: "BACKEND_OFFLINE" });
        return;
      }

      if (error.response.status >= 500) {
        dispatch({ type: "BACKEND_OFFLINE" });
        return;
      }

      dispatch({
        type: "AUTH_CHECK_ERROR",
        error: "Authentication check failed"
      });
    }
  };

  /* ---------------- MANUAL AUTH ONLY ---------------- */

  // Removed automatic auth check - authentication is now manual only
  // useEffect(() => {
  //   if (authChecked.current) return;
  //   authChecked.current = true;
  //   checkAuth();
  // }, []);

  /* ---------------- AUTH EXPIRED LISTENER - DISABLED ---------------- */

  // Disabled auth expired listener to prevent automatic redirects
  // useEffect(() => {
  //   const handleAuthExpired = () => {
  //     console.log("🔐 Auth expired event received");
  //     dispatch({
  //       type: "AUTH_REQUIRED",
  //       payload: { login_url: "/auth" }
  //     });
  //   };

  //   window.addEventListener("auth-expired", handleAuthExpired);
  //   return () => window.removeEventListener("auth-expired", handleAuthExpired);
  // }, []);

  const value: AuthContextType = {
    state,
    checkAuth
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

/* ------------------------------------------------ */
/* HOOK */
/* ------------------------------------------------ */

export function useAuth(): AuthContextType {

  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}

/* ------------------------------------------------ */
/* OPTIONAL HELPER */
/* ------------------------------------------------ */

export function useAuthState() {

  const { state } = useAuth();

  return {
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    error: state.error,
    loginUrl: state.loginUrl
  };
}