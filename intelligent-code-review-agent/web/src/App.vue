<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { useI18n } from 'vue-i18n'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'

const { t } = useI18n()
</script>

<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="logo">
        <h1>{{ t('app.title') }}</h1>
        <span class="subtitle">{{ t('app.subtitle') }}</span>
      </div>
      <nav>
        <RouterLink to="/">
          <span class="icon">🏠</span> {{ t('nav.dashboard') }}
        </RouterLink>
        <RouterLink to="/scan">
          <span class="icon">🔍</span> {{ t('nav.newScan') }}
        </RouterLink>
        <RouterLink to="/file-scan">
          <span class="icon">📂</span> {{ t('nav.fileScan') }}
        </RouterLink>
        <RouterLink to="/compare">
          <span class="icon">📊</span> {{ t('nav.compare') }}
        </RouterLink>
        <RouterLink to="/guidelines">
          <span class="icon">📋</span> {{ t('nav.guidelines') }}
        </RouterLink>
        <RouterLink to="/settings">
          <span class="icon">⚙️</span> {{ t('nav.settings') }}
        </RouterLink>
      </nav>
    </aside>
    <main class="main-content">
      <div class="top-bar">
        <LanguageSwitcher />
      </div>
      <RouterView />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-card: #334155;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --accent: #3b82f6;
  --accent-hover: #2563eb;
  --critical: #ef4444;
  --error: #f97316;
  --warning: #eab308;
  --info: #3b82f6;
  --success: #22c55e;
  --border: #475569;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
}

.app-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  padding: 1.5rem 0;
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  overflow-y: auto;
}

.logo {
  padding: 0 1.5rem 1.5rem;
  border-bottom: 1px solid var(--border);
}

.logo h1 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--accent);
}

.logo .subtitle {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

nav {
  display: flex;
  flex-direction: column;
  padding: 1rem 0.75rem;
  gap: 0.25rem;
}

nav a {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.9rem;
  transition: all 0.15s;
}

nav a:hover {
  background: var(--bg-card);
  color: var(--text-primary);
}

nav a.router-link-active {
  background: var(--accent);
  color: white;
}

.icon {
  font-size: 1.1rem;
}

.main-content {
  flex: 1;
  margin-left: 240px;
  padding: 2rem;
  min-height: 100vh;
}

.top-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1.5rem;
}
</style>
