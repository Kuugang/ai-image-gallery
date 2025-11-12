<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoginForm from '@/components/LoginForm.vue'
import type { LoginRequest } from '@/services/api'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const isLoading = ref(false)

async function handleLogin(e) {
  if (!email.value || !password.value) {
    authStore.error = 'Please fill in all fields'
    console.warn('Login validation failed: missing fields')
    return
  }

  isLoading.value = true
  try {
    await authStore.login({
      email: email.value,
      password: password.value,
    } as LoginRequest)

    // Middleware will fetch user and validate on navigation to home
    // Just redirect and let middleware handle the auth check
    const redirect = router.currentRoute.value.query.redirect as string
    await router.push({ path: redirect || '/', replace: true })
  } catch (error) {
    console.error('Login error:', error)
    console.error('Error details:', {
      message: (error as any).message,
      response: (error as any).response?.data,
      status: (error as any).response?.status,
    })
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background">
    <div class="w-full max-w-4xl">
      <LoginForm
        :email="email"
        :password="password"
        :is-loading="isLoading"
        :error="authStore.error"
        @update:email="email = $event"
        @update:password="password = $event"
        @submit="handleLogin"
        @clear-error="authStore.clearError()"
      />
    </div>
  </div>
</template>
