<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import SignupForm from '@/components/SignupForm.vue'
import type { SignupRequest } from '@/services/api'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const successMessage = ref('')

onMounted(() => {
  authStore.clearError()
})

async function handleSignup() {
    if (!email.value || !password.value) {
        authStore.error = 'Please fill in all fields'
        console.warn('Signup validation failed: missing fields')
        return
    }

    authStore.isLoading = true
    try {
        const response = await authStore.signup({
            email: email.value,
            password: password.value,
        } as SignupRequest)

        // Clear form and show success message
        successMessage.value = 'Account created successfully! You can now log in.'
        email.value = ''
        password.value = ''

        // Redirect to login after 2 seconds
        setTimeout(() => {
            router.push('/login')
        }, 2000)
    } catch (error) {
        // Error is handled by auth store
        console.error('Signup error:', error)
        console.error('Error details:', {
            message: (error as any).message,
            response: (error as any).response?.data,
            status: (error as any).response?.status,
        })
    } finally {
        authStore.isLoading = false
    }
}
</script>

<template>
    <div class="min-h-screen flex items-center justify-center bg-background">
        <div class="w-full max-w-4xl">
            <div v-if="successMessage" class="mb-4 p-4 bg-green-50 text-green-700 rounded-lg">
                {{ successMessage }}
            </div>
            <SignupForm 
                :email="email" 
                :password="password" 
                :is-loading="authStore.isLoading" 
                :error="authStore.error"
                @update:email="email = $event" 
                @update:password="password = $event" 
                @submit="handleSignup"
                @clear-error="authStore.clearError()" 
            />
        </div>
    </div>
</template>
