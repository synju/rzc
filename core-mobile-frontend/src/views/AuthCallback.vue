<template>
  <div class="callback">
    <p>Authenticating...</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  const params = new URLSearchParams(window.location.search)
  const token = params.get('token')
  const error = params.get('error')

  if (error) {
    router.push('/login')
    return
  }

  if (token) {
    localStorage.setItem('rzc_token', token)
    
    try {
      const response = await api.get('/auth/me')
      authStore.setAuth(token, response.data)
      router.push('/dashboard')
    } catch (e) {
      localStorage.removeItem('rzc_token')
      router.push('/login')
    }
  } else {
    router.push('/login')
  }
})
</script>

<style scoped>
.callback {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0d0d14;
  color: #fff;
}

.error {
  color: #f44336;
}
</style>