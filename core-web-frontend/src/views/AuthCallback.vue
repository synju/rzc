<template>
  <div class="callback">
    <div v-if="displayToken" class="token-display">
      <h2>Login Successful!</h2>
      <p>Copy your token below and paste it in the mobile app:</p>
      <div class="token-box">{{ displayToken }}</div>
      <button @click="copyToken" class="btn-copy">Copy Token</button>
      <p v-if="copied" class="copied-msg">Copied!</p>
    </div>
    <div v-else-if="error" class="loading">
      <p class="error">{{ error }}</p>
      <a href="/login" class="btn-back">Back to Login</a>
    </div>
    <div v-else class="loading">
      <p>Signing you in...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { walletApi } from '../api'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const displayToken = ref('')
const error = ref('')
const copied = ref(false)

const copyToken = async () => {
  await navigator.clipboard.writeText(displayToken.value)
  copied.value = true
}

const processTokenAndRedirect = async (token) => {
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
}

onMounted(async () => {
  const token = route.query.token
  const errorQuery = route.query.error
  const showToken = route.query.show_token === 'true'

  if (errorQuery) {
    error.value = 'Authentication failed. Please try again.'
    return
  }

  if (token) {
    if (showToken) {
      displayToken.value = token
      const userData = JSON.parse(atob(token.split('.')[1]))
      authStore.setAuth(token, {
        id: userData.sub,
        email: userData.email
      })
    } else {
      await processTokenAndRedirect(token)
    }
    return
  }

  const code = route.query.code

  if (!code) {
    error.value = 'No authentication code received.'
    return
  }

  try {
    const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8001'
    const response = await fetch(`${baseURL}/auth/google/callback?code=${code}`, {
      credentials: 'include'
    })
    const data = await response.json()

    if (data.access_token) {
      const fullToken = data.access_token
      displayToken.value = fullToken
      
      authStore.setAuth(fullToken, {
        id: data.user_id,
        email: data.email
      })

      await authStore.checkAuth()
      await authStore.loadWallets()

      if (!authStore.activeWallet?.address) {
        await walletApi.createWallet()
        await authStore.loadWallets()
      }

      if (showToken) {
        await router.push('/dashboard')
      } else {
        await router.push('/dashboard')
      }
    } else {
      throw new Error('No access token received')
    }
  } catch (err) {
    console.error('Auth error:', err)
    error.value = 'Authentication failed. Please try again.'
  }
})
</script>

<style scoped>
.callback {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #0d0d14;
  padding: 2rem;
}

.token-display {
  text-align: center;
  max-width: 500px;
}

.token-display h2 {
  color: #4caf50;
  margin-bottom: 1rem;
}

.token-display p {
  color: #888;
  margin-bottom: 1.5rem;
}

.token-box {
  background: #1f1f2e;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 1rem;
  font-family: monospace;
  font-size: 0.85rem;
  word-break: break-all;
  color: #ffd700;
  margin-bottom: 1rem;
  max-height: 150px;
  overflow-y: auto;
}

.btn-copy {
  background: #ffd700;
  color: #0d0d14;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  font-size: 1rem;
}

.btn-copy:hover {
  background: #ffed4a;
}

.copied-msg {
  color: #4caf50;
  margin-top: 1rem;
}

.loading {
  text-align: center;
}

.loading p {
  color: #ffd700;
  font-size: 1.25rem;
}

.error {
  color: #f44336;
  font-size: 1.25rem;
  margin-bottom: 1rem;
}

.btn-back {
  display: inline-block;
  background: #ffd700;
  color: #0d0d14;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
}
</style>
