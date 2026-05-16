import { createI18n } from 'vue-i18n'
import en from './en'
import zh from './zh'
import de from './de'
import cs from './cs'

export type Locale = 'en' | 'zh' | 'de' | 'cs'

export const localeNames: Record<Locale, string> = {
  en: 'English',
  zh: '中文',
  de: 'Deutsch',
  cs: 'Čeština',
}

export const localeFlags: Record<Locale, string> = {
  en: '🇬🇧',
  zh: '🇨🇳',
  de: '🇩🇪',
  cs: '🇨🇿',
}

const savedLocale = (localStorage.getItem('locale') as Locale) || 'en'

const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: 'en',
  messages: { en, zh, de, cs },
})

export default i18n
