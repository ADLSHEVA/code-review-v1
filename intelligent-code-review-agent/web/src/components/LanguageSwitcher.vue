<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { localeNames, localeFlags, type Locale } from '@/locales'

const { locale } = useI18n()
const open = ref(false)

const locales: Locale[] = ['en', 'zh', 'de', 'cs']

function switchLocale(l: Locale) {
  locale.value = l
  localStorage.setItem('locale', l)
  open.value = false
}
</script>

<template>
  <div class="lang-switcher">
    <button class="lang-btn" @click="open = !open">
      {{ localeFlags[locale as Locale] }} {{ localeNames[locale as Locale] }}
      <span class="arrow" :class="{ open }">▾</span>
    </button>
    <div v-if="open" class="lang-dropdown">
      <button
        v-for="l in locales"
        :key="l"
        :class="['lang-option', { active: locale === l }]"
        @click="switchLocale(l)"
      >
        <span class="flag">{{ localeFlags[l] }}</span>
        <span class="name">{{ localeNames[l] }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.lang-switcher {
  position: relative;
}

.lang-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 0.4rem;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.8rem;
  white-space: nowrap;
}

.lang-btn:hover {
  border-color: var(--accent);
}

.arrow {
  font-size: 0.65rem;
  transition: transform 0.15s;
}

.arrow.open {
  transform: rotate(180deg);
}

.lang-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 0.4rem;
  overflow: hidden;
  z-index: 100;
  min-width: 140px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.lang-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.6rem 0.75rem;
  background: transparent;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.8rem;
  text-align: left;
}

.lang-option:hover {
  background: var(--bg-card);
}

.lang-option.active {
  background: var(--accent);
  color: white;
}

.flag {
  font-size: 1rem;
}
</style>
