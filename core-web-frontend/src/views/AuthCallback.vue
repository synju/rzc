<template>
  <div class="callback">
    <div class="loading">
      <p v-if="error">{{ error }}</p>
      <p v-else>Signing you in...</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { walletApi } from '../api'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  const token = route.query.token
  const error = route.query.error

  if (error) {
    router.push('/login')
    return
  }

  if (token) {
    const userData = JSON.parse(atob(token.split('.')[1]))
    authStore.setAuth(token, {
      id: userData.sub,
      email: userData.email
    })

    try {
      await authStore.checkAuth()
      await authStore.loadWallets()
      if (!authStore.activeWallet?.address) {
        await walletApi.createWallet()
        await authStore.loadWallets()
      }
    } catch (e) {
      console.error('Wallet error:', e)
    }

    router.push('/dashboard')
    return
  }

  const code = route.query.code

  if (!code) {
    router.push('/login')
    return
  }

  try {
    const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8001'
    const response = await fetch(`${baseURL}/auth/google/callback?code=${code}`, {
      credentials: 'include'
    })
    const data = await response.json()

    if (data.access_token) {
      authStore.setAuth(data.access_token, {
        id: data.user_id,
        email: data.email
      })

      await authStore.checkAuth()
      await authStore.loadWallets()

      if (!authStore.activeWallet?.address) {
        await walletApi.createWallet()
        await authStore.loadWallets()
      }

      router.push('/dashboard')
    } else {
      throw new Error('No access token received')
    }
  } catch (err) {
    console.error('Auth error:', err)
    router.push('/login')
  }
})
</script>

<style scoped>
.callback {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #1a1a2e;
}

.loading {
  text-align: center;
  color: #ffd700;
}
</style>
