import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
  apiClient,
  type UserOut,
  type LoginRequest,
  type SignupRequest,
} from "@/services/api";

export const useAuthStore = defineStore("auth", () => {
  const user = ref<UserOut | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const isInitialized = ref(false);
  const hasCredentials = ref(false); // Track if we have valid cookies

  const isAuthenticated = computed(
    () => hasCredentials.value || user.value !== null,
  );

  async function login(credentials: LoginRequest) {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await apiClient.login(credentials);
      user.value = response;
      hasCredentials.value = true; // Cookies were set by backend
      return response;
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail || err.message || "Login failed";
      error.value = errorMsg;
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function signup(credentials: SignupRequest) {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await apiClient.signup(credentials);
      user.value = response;
      hasCredentials.value = true; // Cookies were set by backend
      return response;
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail || err.message || "Signup failed";
      error.value = errorMsg;
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function logout() {
    isLoading.value = true;
    error.value = null;
    try {
      await apiClient.logout();
      user.value = null;
      hasCredentials.value = false;
    } catch (err: any) {
      console.error("Logout error:", err);
      // Even if logout request fails, clear local state
      user.value = null;
      hasCredentials.value = false;
      // Dispatch event to ensure cleanup
      window.dispatchEvent(new Event("auth:logout"));
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchCurrentUser() {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await apiClient.getCurrentUser();
      user.value = response;
      hasCredentials.value = true;
      return response;
    } catch (err: any) {
      // If fetch fails, we don't have valid credentials
      user.value = null;
      hasCredentials.value = false;
      return null;
    } finally {
      isLoading.value = false;
      isInitialized.value = true;
    }
  }

  async function restoreAuthFromCookies() {
    // Silently attempt to restore auth state from cookies
    // If cookies exist and are valid, this succeeds
    // If cookies don't exist or are expired, this fails silently
    try {
      const response = await apiClient.getCurrentUser();
      user.value = response;
      hasCredentials.value = true;
      return response;
    } catch (err: any) {
      // No valid cookies - user is not authenticated
      user.value = null;
      hasCredentials.value = false;
      return null;
    } finally {
      isInitialized.value = true;
    }
  }

  async function requestPasswordReset(email: string) {
    isLoading.value = true;
    error.value = null;
    try {
      return await apiClient.requestPasswordReset({ email });
    } catch (err: any) {
      error.value =
        err.response?.data?.detail || err.message || "Password reset failed";
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function updatePassword(newPassword: string) {
    isLoading.value = true;
    error.value = null;
    try {
      return await apiClient.updatePassword({
        access_token: "", // Not used with cookies, but kept for API compatibility
        new_password: newPassword,
      });
    } catch (err: any) {
      error.value =
        err.response?.data?.detail || err.message || "Update password failed";
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  function clearError() {
    error.value = null;
  }

  return {
    user,
    isLoading,
    error,
    isAuthenticated,
    isInitialized,
    hasCredentials,
    login,
    signup,
    logout,
    fetchCurrentUser,
    restoreAuthFromCookies,
    requestPasswordReset,
    updatePassword,
    clearError,
  };
});
