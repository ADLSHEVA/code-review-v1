<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { configApi } from '@/services/api'

const { t } = useI18n()
const config = ref<any>(null)
const languages = ref<any[]>([])

onMounted(async () => {
  const [c, l] = await Promise.all([configApi.get(), configApi.languages()])
  config.value = c.data
  languages.value = l.data
})
</script>

<template>
  <div>
    <h2 class="page-title">{{ t('settings.title') }}</h2>

    <div v-if="config" class="settings-grid">
      <div class="settings-section">
        <h3>{{ t('settings.llmConfig') }}</h3>
        <div class="setting-item">
          <span class="setting-label">{{ t('settings.model') }}</span>
          <span class="setting-value">{{ config.claude_model }}</span>
        </div>
        <div class="setting-item">
          <span class="setting-label">{{ t('settings.temperature') }}</span>
          <span class="setting-value">{{ config.temperature }}</span>
        </div>
        <div class="setting-item">
          <span class="setting-label">{{ t('settings.maxTokens') }}</span>
          <span class="setting-value">{{ config.max_context_tokens }}</span>
        </div>
        <div class="setting-item">
          <span class="setting-label">{{ t('settings.confidenceThreshold') }}</span>
          <span class="setting-value">{{ config.confidence_threshold }}</span>
        </div>
        <div class="setting-item">
          <span class="setting-label">{{ t('settings.apiEndpoint') }}</span>
          <span class="setting-value mono">{{ config.anthropic_base_url || t('settings.default') }}</span>
        </div>
      </div>

      <div class="settings-section">
        <h3>{{ t('settings.supportedLanguages') }} ({{ languages.length }})</h3>
        <div class="language-grid">
          <div v-for="lang in languages" :key="lang.language" class="lang-card">
            <span class="lang-name">{{ lang.language }}</span>
            <span class="lang-exts">{{ lang.extensions.join(', ') }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="loading">{{ t('settings.loading') }}</div>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; }

.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.settings-section {
  background: var(--bg-secondary);
  border-radius: 0.5rem;
  padding: 1.5rem;
}

.settings-section h3 {
  font-size: 1rem;
  margin-bottom: 1rem;
  color: var(--accent);
}

.setting-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border);
  font-size: 0.85rem;
}

.setting-item:last-child { border-bottom: none; }

.setting-label { color: var(--text-secondary); }
.setting-value { font-weight: 600; }
.setting-value.mono { font-family: monospace; font-size: 0.8rem; }

.language-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.5rem;
}

.lang-card {
  background: var(--bg-card);
  border-radius: 0.25rem;
  padding: 0.5rem 0.75rem;
}

.lang-name {
  display: block;
  font-weight: 600;
  font-size: 0.85rem;
  margin-bottom: 0.2rem;
}

.lang-exts {
  font-size: 0.7rem;
  color: var(--text-secondary);
}

.loading {
  text-align: center;
  color: var(--text-secondary);
  padding: 4rem;
}
</style>
