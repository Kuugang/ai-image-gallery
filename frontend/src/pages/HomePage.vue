<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ref } from 'vue'

const router = useRouter()
const authStore = useAuthStore()
const isLoggingOut = ref(false)

async function handleLogout() {
    isLoggingOut.value = true
    try {
        await authStore.logout()
        await router.push('/login')
    } catch (error) {
        console.error('Logout error:', error)
        // Even if there's an error, clear local state and redirect
        authStore.user = null
        await router.push('/login')
    } finally {
        isLoggingOut.value = false
    }
}
</script>

<template>
    <div class="min-h-screen bg-background">
        <!-- Navigation -->
        <nav class="bg-white shadow">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between h-16">
                    <div class="flex items-center">
                        <h1 class="text-xl font-semibold">AI Image Gallery</h1>
                    </div>
                    <div class="flex items-center gap-4">
                        <span class="text-sm text-gray-700">{{ authStore.user?.email }}</span>
                        <Button variant="outline" size="sm" @click="handleLogout" :disabled="isLoggingOut">
                            {{ isLoggingOut ? 'Logging out...' : 'Logout' }}
                        </Button>
                    </div>
                </div>
            </div>
        </nav>

        <!-- Main Content -->
        <main class="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
            <Card>
                <CardHeader>
                    <CardTitle>Welcome to AI Image Gallery</CardTitle>
                    <CardDescription>You are now logged in</CardDescription>
                </CardHeader>
                <CardContent>
                    <div class="space-y-4">
                        <p class="text-gray-600">
                            This is a protected page. Only authenticated users can access this content.
                        </p>
                        <div class="bg-blue-50 p-4 rounded-lg">
                            <h3 class="font-semibold text-blue-900">User Information</h3>
                            <dl class="mt-2 text-sm text-blue-800">
                                <div class="flex justify-between py-1">
                                    <dt>Email:</dt>
                                    <dd class="font-medium">{{ authStore.user?.email }}</dd>
                                </div>
                                <div class="flex justify-between py-1">
                                    <dt>User ID:</dt>
                                    <dd class="font-medium break-all">{{ authStore.user?.user_id }}</dd>
                                </div>
                            </dl>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </main>
    </div>
</template>
