<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const isLoading = ref(false)
const submitted = ref(false)

async function handleSubmit() {
  if (!email.value) {
    authStore.error = 'Please enter your email'
    return
  }

  isLoading.value = true
  try {
    await authStore.requestPasswordReset(email.value)
    submitted.value = true
    setTimeout(() => {
      router.push('/login')
    }, 3000)
  } catch (error) {
    console.error('Password reset error:', error)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background p-4">
    <Card class="w-full max-w-md">
      <CardHeader class="text-center">
        <CardTitle class="text-2xl">Reset your password</CardTitle>
        <CardDescription>
          {{ submitted ? 'Check your email for reset instructions' : 'Enter your email to receive a password reset link' }}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div v-if="!submitted" class="space-y-6">
          <div v-if="authStore.error" class="p-3 bg-red-50 text-red-700 rounded-md text-sm">
            {{ authStore.error }}
          </div>
          <form @submit.prevent="handleSubmit" class="space-y-4">
            <div class="grid gap-3">
              <Label for="email">Email</Label>
              <Input
                id="email"
                v-model="email"
                type="email"
                placeholder="m@example.com"
                required
                :disabled="isLoading"
              />
            </div>
            <Button type="submit" class="w-full" :disabled="isLoading">
              {{ isLoading ? 'Sending...' : 'Send reset link' }}
            </Button>
          </form>
          <div class="text-center text-sm">
            <router-link to="/login" class="text-primary hover:underline">
              Back to login
            </router-link>
          </div>
        </div>
        <div v-else class="text-center space-y-4">
          <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-100">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
          </div>
          <p class="text-gray-600">
            We've sent a password reset link to <strong>{{ email }}</strong>
          </p>
          <p class="text-sm text-gray-500">Redirecting to login in 3 seconds...</p>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
