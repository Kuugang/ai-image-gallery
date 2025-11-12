<script setup lang="ts">
import { ref, computed } from 'vue'
import type { HTMLAttributes } from "vue"
import { cn } from "@/lib/utils"
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useRouter } from 'vue-router'

const router = useRouter()
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const confirmPassword = ref('')

const props = defineProps<{
  class?: HTMLAttributes["class"]
  email?: string
  password?: string
  isLoading?: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  'update:email': [value: string]
  'update:password': [value: string]
  'submit': []
  'clear-error': []
}>()

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
}

const toggleConfirmPasswordVisibility = () => {
  showConfirmPassword.value = !showConfirmPassword.value
}

const passwordMismatch = computed(() => {
  return props.password && confirmPassword.value && props.password !== confirmPassword.value
})

const isFormValid = computed(() => {
  return props.email && props.password && confirmPassword.value && !passwordMismatch.value
})

const handleSubmit = () => {
  if (passwordMismatch.value) {
    return
  }
  emit('submit')
}
</script>

<template>
  <div :class="cn('flex flex-col gap-6', props.class)">
    <Card class="overflow-hidden p-0">
      <CardContent class="grid p-0 md:grid-cols-2">
        <form class="p-6 md:p-8" @submit.prevent="handleSubmit">
          <div class="flex flex-col gap-6">
            <div class="flex flex-col items-center text-center">
              <h1 class="text-2xl font-bold">
                Create an account
              </h1>
              <p class="text-muted-foreground text-balance">
                Sign up for your AI Image Gallery account
              </p>
            </div>

            <div v-if="error" class="p-3 bg-red-50 text-red-700 rounded-md text-sm">
              {{ error }}
            </div>

            <div class="grid gap-3">
              <Label for="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="m@example.com"
                :model-value="email"
                @update:model-value="emit('update:email', $event)"
                @focus="emit('clear-error')"
                :disabled="isLoading"
                required
              />
            </div>
            <div class="grid gap-3">
              <Label for="password">Password</Label>
              <div class="relative">
                <Input
                  :id="`password-${Math.random()}`"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="••••••••"
                  :model-value="password"
                  @update:model-value="emit('update:password', $event)"
                  @focus="emit('clear-error')"
                  :disabled="isLoading"
                  required
                />
                <button
                  type="button"
                  @click="togglePasswordVisibility"
                  :disabled="isLoading"
                  class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 disabled:opacity-50"
                  :aria-label="showPassword ? 'Hide password' : 'Show password'"
                >
                  <!-- Eye icon -->
                  <svg v-if="!showPassword" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                  <!-- Eye off icon -->
                  <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.26 3.64M9 12a3 3 0 0 0 3 3M1 1l22 22"></path>
                  </svg>
                </button>
              </div>
            </div>
            <div class="grid gap-3">
              <Label for="confirm-password">Confirm Password</Label>
              <div class="relative">
                <Input
                  id="confirm-password"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  placeholder="••••••••"
                  v-model="confirmPassword"
                  @focus="emit('clear-error')"
                  :disabled="isLoading"
                  required
                />
                <button
                  type="button"
                  @click="toggleConfirmPasswordVisibility"
                  :disabled="isLoading"
                  class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 disabled:opacity-50"
                  :aria-label="showConfirmPassword ? 'Hide password' : 'Show password'"
                >
                  <!-- Eye icon -->
                  <svg v-if="!showConfirmPassword" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                  <!-- Eye off icon -->
                  <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.26 3.64M9 12a3 3 0 0 0 3 3M1 1l22 22"></path>
                  </svg>
                </button>
              </div>
              <div v-if="passwordMismatch" class="text-sm text-red-600">
                Passwords do not match
              </div>
            </div>

            <Button type="submit" class="w-full" :disabled="isLoading || !isFormValid">
              {{ isLoading ? 'Signing up...' : 'Sign up' }}
            </Button>
            <div class="text-center text-sm">
              Already have an account?
              <router-link to="/login" class="underline underline-offset-4">
                Login
              </router-link>
            </div>
          </div>
        </form>
        <div class="bg-muted relative hidden md:block">
          <img
            src="https://placehold.co/600x400"
            alt="Image"
            class="absolute inset-0 h-full w-full object-cover dark:brightness-[0.2] dark:grayscale"
          >
        </div>
      </CardContent>
    </Card>
  </div>
</template>
