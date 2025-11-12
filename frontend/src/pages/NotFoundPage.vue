<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const router = useRouter()
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background p-4">
    <Card class="w-full max-w-md">
      <CardHeader class="text-center">
        <CardTitle class="text-4xl font-bold">404</CardTitle>
        <CardDescription>Page not found</CardDescription>
      </CardHeader>
      <CardContent class="space-y-4">
        <p class="text-gray-600 text-center">
          The page you are looking for doesn't exist or has been moved.
        </p>
        <div class="flex flex-col gap-3">
          <Button
            variant="outline"
            class="w-full"
            @click="router.back()"
          >
            Go Back
          </Button>
          <Button
            class="w-full"
            @click="router.push('/')"
          >
            Go Home
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
