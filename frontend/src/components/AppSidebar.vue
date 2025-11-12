<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { Button } from '@/components/ui/button'

const router = useRouter()
const authStore = useAuthStore()

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <Sidebar class="border-r border-[#e5e8e0] bg-white">
    <SidebarHeader>
      <div class="px-4 py-4">
        <div class="flex items-center gap-2 mb-1">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-[#78d035] to-[#66db80] flex items-center justify-center text-white font-bold">
            🖼️
          </div>
          <h1 class="text-xl font-bold text-[#060802]">AI Gallery</h1>
        </div>
        <p class="text-xs text-[#6b7366] ml-10">Creative Studio</p>
      </div>
    </SidebarHeader>
    
    <SidebarContent>
      <!-- Navigation Group -->
      <SidebarGroup>
        <SidebarGroupLabel class="text-[#6b7366] text-xs font-semibold uppercase tracking-wider">Navigation</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton asChild class="hover:bg-[#f5f7f1] hover:text-[#78d035]">
                <router-link to="/" class="flex items-center gap-3">
                  <span class="text-lg">🏠</span>
                  <span class="text-[#060802]">Home</span>
                </router-link>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton asChild class="hover:bg-[#f5f7f1] hover:text-[#78d035]">
                <router-link to="/profile" class="flex items-center gap-3">
                  <span class="text-lg">👤</span>
                  <span class="text-[#060802]">Profile</span>
                </router-link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      <!-- Account Group -->
      <SidebarGroup>
        <SidebarGroupLabel class="text-[#6b7366] text-xs font-semibold uppercase tracking-wider">Account</SidebarGroupLabel>
        <SidebarGroupContent>
          <div class="px-4 py-3 rounded-lg bg-[#f5f7f1] border border-[#e5e8e0]">
            <p class="text-xs text-[#6b7366] font-medium mb-1">Logged in as</p>
            <p class="text-sm font-semibold text-[#060802] truncate">
              {{ authStore.user?.email || 'Loading...' }}
            </p>
          </div>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
    
    <SidebarFooter>
      <div class="p-4 space-y-3 border-t border-[#e5e8e0]">
        <Button 
          @click="handleLogout" 
          class="w-full bg-gradient-to-r from-[#78d035] to-[#66db80] text-white hover:from-[#5fa029] hover:to-[#5aa076] h-10 font-medium"
        >
          Logout
        </Button>
        <p class="text-xs text-[#6b7366] text-center">
          AI Image Gallery
        </p>
      </div>
    </SidebarFooter>
  </Sidebar>
</template>

<style scoped>
:deep(.sidebar-menu-button) {
  transition: all 0.2s ease;
}
</style>
