<template>
  <div class="landing">
    <header class="header">
      <h1>RZC</h1>
      <nav>
        <router-link to="/login" class="btn btn-primary">Get Started</router-link>
      </nav>
    </header>

    <main class="hero">
      <h2>Royal Zeni Coin</h2>
      <p class="tagline">The future of digital payments</p>
      <p class="description">
        Buy, sell, and transfer RZC instantly. Secure wallet powered by blockchain technology.
      </p>
      <router-link to="/login" class="btn btn-large btn-primary">Start Now</router-link>
    </main>

    <section class="features">
      <div class="feature">
        <h3>Fast</h3>
        <p>Instant transfers on the Avalanche network</p>
      </div>
      <div class="feature">
        <h3>Secure</h3>
        <p>Your keys, your crypto. Always in your control.</p>
      </div>
      <div class="feature">
        <h3>Simple</h3>
        <p>Easy to use, just like sending a message</p>
      </div>
    </section>

    <footer class="footer">
      <p>&copy; 2026 Royal Zeni Coin. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup>
</script>

<style scoped>
.landing {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  background: #1a1a2e;
}

.header h1 {
  font-size: 1.5rem;
  color: #ffd700;
  margin: 0;
}

.hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 4rem 2rem;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.hero h2 {
  font-size: 3rem;
  color: #ffd700;
  margin: 0 0 1rem;
}

.tagline {
  font-size: 1.5rem;
  color: #888;
  margin: 0 0 2rem;
}

.description {
  font-size: 1.1rem;
  color: #ccc;
  max-width: 500px;
  margin: 0 0 2rem;
  line-height: 1.6;
}

.features {
  display: flex;
  justify-content: center;
  gap: 4rem;
  padding: 4rem 2rem;
  background: #0f0f1a;
}

.feature {
  text-align: center;
  max-width: 200px;
}

.feature h3 {
  color: #ffd700;
  margin: 0 0 0.5rem;
}

.feature p {
  color: #888;
  margin: 0;
  font-size: 0.95rem;
}

.footer {
  padding: 1.5rem;
  text-align: center;
  background: #1a1a2e;
  color: #666;
}

.footer p {
  margin: 0;
}

.btn {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.2s;
  cursor: pointer;
  border: none;
  font-size: 1rem;
}

.btn-primary {
  background: #ffd700;
  color: #1a1a2e;
}

.btn-primary:hover {
  background: #ffed4a;
  transform: translateY(-2px);
}

.btn-large {
  padding: 1rem 2.5rem;
  font-size: 1.1rem;
}
</style>
