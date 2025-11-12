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

const newPassword = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const submitted = ref(false)

async function handleSubmit() {
  if (!newPassword.value || !confirmPassword.value) {
    authStore.error = 'Please fill in all fields'
    return
  }

  if (newPassword.value !== confirmPassword.value) {
    authStore.error = 'Passwords do not match'
    return
  }

  if (newPassword.value.length < 6) {
    authStore.error = 'Password must be at least 6 characters'
    return
  }

  isLoading.value = true
  try {
    await authStore.updatePassword(newPassword.value)
    submitted.value = true
    setTimeout(() => {
      router.push('/')
    }, 2000)
  } catch (error) {
    console.error('Update password error:', error)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background p-4">
    <Card class="w-full max-w-md">
      <CardHeader class="text-center">
        <CardTitle class="text-2xl">Update your password</CardTitle>
        <CardDescription>
          {{ submitted ? 'Password updated successfully' : 'Create a new password for your account' }}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div v-if="!submitted" class="space-y-6">
          <div v-if="authStore.error" class="p-3 bg-red-50 text-red-700 rounded-md text-sm">
            {{ authStore.error }}
          </div>
          <form @submit.prevent="handleSubmit" class="space-y-4">
            <div class="grid gap-3">
              <Label for="password">New Password</Label>
              <Input
                id="password"
                v-model="newPassword"
                type="password"
                placeholder="••••••••"
                required
                :disabled="isLoading"
              />
            </div>
            <div class="grid gap-3">
              <Label for="confirm-password">Confirm Password</Label>
              <Input
                id="confirm-password"
                v-model="confirmPassword"
                type="password"
                placeholder="••••••••"
                required
                :disabled="isLoading"
              />
            </div>
            <Button type="submit" class="w-full" :disabled="isLoading">
              {{ isLoading ? 'Updating...' : 'Update password' }}
            </Button>
          </form>
        </div>
        <div v-else class="text-center space-y-4">
          <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-100">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
          </div>
          <p class="text-gray-600">Your password has been updated successfully.</p>
          <p class="text-sm text-gray-500">Redirecting to home in 2 seconds...</p>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
