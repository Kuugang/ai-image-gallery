import { createApp } from "vue";
import { createPinia } from "pinia";
import "./style.css";
import App from "./App.vue";
import router from "./router";
import { useAuthStore } from "./stores/auth";

const app = createApp(App);

app.use(createPinia());
app.use(router);

// Initialize auth state on app startup - try to restore user from cookies
// This must happen BEFORE router guard runs
const authStore = useAuthStore();
const authPromise = authStore.restoreAuthFromCookies();

// Auth middleware - run before routing
router.beforeEach(async (to, _from, next) => {
  // Wait for auth restoration to complete
  await authPromise;

  // Set page title
  document.title = `${to.meta.title || "App"} - AI Image Gallery`;

  // 1. If on login page and already authenticated, redirect to home
  if (to.name === "login" && authStore.user) {
    return next({ name: "home", replace: true });
  }

  // 2. If route requires auth
  if (to.meta.requiresAuth) {
    // 3. No credentials - redirect to login
    if (!authStore.hasCredentials) {
      return next({
        name: "login",
        query: { redirect: to.fullPath },
        replace: true,
      });
    }

    // 4. Has credentials and user is already loaded - allow access
    if (authStore.user) {
      return next();
    }

    // 5. Has credentials but user not loaded - fetch and check
    try {
      const user = await authStore.fetchCurrentUser();
      if (user) {
        return next();
      }
      return next({
        name: "login",
        query: { redirect: to.fullPath },
        replace: true,
      });
    } catch (error) {
      console.error("Failed to fetch user:", error);
      authStore.user = null;
      return next({
        name: "login",
        query: { redirect: to.fullPath },
        replace: true,
      });
    }
  }

  // Default: allow access
  next();
});

// Wait for router to be ready before mounting
router.isReady().then(() => {
  app.mount("#app");
});
