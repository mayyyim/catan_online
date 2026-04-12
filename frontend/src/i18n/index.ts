import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import zh from './locales/zh.json'

const STORAGE_KEY = 'catan_lang'

function detectInitialLang(): 'en' | 'zh' {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'en' || saved === 'zh') return saved
  const browser = navigator.language.toLowerCase()
  return browser.startsWith('zh') ? 'zh' : 'en'
}

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      zh: { translation: zh },
    },
    lng: detectInitialLang(),
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  })

export function setLanguage(lang: 'en' | 'zh') {
  i18n.changeLanguage(lang)
  localStorage.setItem(STORAGE_KEY, lang)
}

export default i18n
