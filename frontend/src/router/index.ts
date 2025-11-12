import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
} from "vue-router";
import LoginPage from "@/pages/LoginPage.vue";
import SignupPage from "@/pages/SignupPage.vue";
import HomePage from "@/pages/HomePage.vue";
import NotFoundPage from "@/pages/NotFoundPage.vue";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage.vue";
import UpdatePasswordPage from "@/pages/UpdatePasswordPage.vue";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: LoginPage,
    meta: { requiresAuth: false, title: "Login" },
  },
  {
    path: "/signup",
    name: "signup",
    component: SignupPage,
    meta: { requiresAuth: false, title: "Sign Up" },
  },
  {
    path: "/forgot-password",
    name: "forgot-password",
    component: ForgotPasswordPage,
    meta: { requiresAuth: false, title: "Forgot Password" },
  },
  {
    path: "/update-password",
    name: "update-password",
    component: UpdatePasswordPage,
    meta: { requiresAuth: true, title: "Update Password" },
  },
  {
    path: "/",
    name: "home",
    component: HomePage,
    meta: { requiresAuth: true, title: "Home" },
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: NotFoundPage,
    meta: { title: "404 Not Found" },
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

// Navigation guards - removed, moved to main.ts for cleaner middleware approach
router.afterEach(() => {
  // Loading completed
});

export default router;
