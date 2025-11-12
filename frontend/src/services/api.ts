import axios from "axios";
import type { AxiosInstance, AxiosError } from "axios";

const API_BASE_URL = "http://localhost/api/v1";

export interface ApiResponse<T> {
  data?: T;
  message?: string;
}

export interface UserOut {
  access_token: string | null;
  refresh_token?: string | null;
  user_id: string;
  email: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface UpdatePasswordRequest {
  access_token: string;
  new_password: string;
}

export interface Token {
  access_token: string;
  refresh_token: string;
}

class ApiClient {
  private instance: AxiosInstance;

  constructor() {
    this.instance = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        "Content-Type": "application/json",
      },
      withCredentials: true, // Enable sending cookies with requests
    });

    // Add response interceptor for token refresh on 401
    this.instance.interceptors.response.use(
      (response) => {
        return response;
      },
      async (error: AxiosError) => {
        const originalRequest = error.config as any;
        const requestUrl = error.config?.url || "";

        // Don't retry auth endpoints (login, signup, logout, refresh)
        // A 401 on these means the request itself failed, not token expiry
        if (
          requestUrl.includes("/auth/login") ||
          requestUrl.includes("/auth/signup") ||
          requestUrl.includes("/auth/logout") ||
          requestUrl.includes("/auth/refresh")
        ) {
          return Promise.reject(error);
        }

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            await this.instance.post("/auth/refresh");
            return this.instance(originalRequest);
          } catch (refreshError) {
            console.warn("Refresh failed, user is no longer authenticated");
            window.dispatchEvent(new Event("auth:logout"));
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      },
    );
  }

  isAuthenticated(): boolean {
    // HttpOnly cookies can't be read from JavaScript
    // Check is done in auth store with hasCredentials flag
    return false; // Not used - store handles this
  }

  // Auth endpoints
  async login(credentials: LoginRequest): Promise<UserOut> {
    const response = await this.instance.post<ApiResponse<UserOut>>(
      "/auth/login",
      credentials,
    );
    // Tokens are automatically set in cookies by the backend
    return response.data.data!;
  }

  async signup(data: SignupRequest): Promise<UserOut> {
    const response = await this.instance.post<ApiResponse<UserOut>>(
      "/auth/signup",
      data,
    );
    // Tokens are automatically set in cookies by the backend
    return response.data.data!;
  }

  async logout(): Promise<void> {
    try {
      await this.instance.post("/auth/logout");
    } finally {
      // Cookies are cleared by the backend
      window.dispatchEvent(new Event("auth:logout"));
    }
  }

  async refreshAccessToken(): Promise<void> {
    // Call refresh with cookies - backend will set new cookies
    await this.instance.post("/auth/refresh");
  }

  async requestPasswordReset(
    data: PasswordResetRequest,
  ): Promise<{ message: string }> {
    const response = await this.instance.post("/auth/password-reset", data);
    return response.data;
  }

  async updatePassword(
    data: UpdatePasswordRequest,
  ): Promise<{ message: string }> {
    const response = await this.instance.post("/auth/update-password", data);
    return response.data;
  }

  async getCurrentUser(): Promise<UserOut> {
    try {
      const response =
        await this.instance.get<ApiResponse<UserOut>>("/auth/me");
      if (!response.data.data) {
        throw new Error("Invalid response structure from /auth/me");
      }
      return response.data.data;
    } catch (error: any) {
      console.error(
        "getCurrentUser error:",
        error.response?.status,
        error.message,
      );
      throw error;
    }
  }
}

export const apiClient = new ApiClient();
