import { useTranslation } from 'react-i18next'
import { setLanguage } from '../i18n'
import styles from './LanguageSwitcher.module.css'

export function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const current = i18n.language.startsWith('zh') ? 'zh' : 'en'

  return (
    <div className={styles.switcher} role="group" aria-label="Language">
      <button
        type="button"
        className={`${styles.btn} ${current === 'en' ? styles.active : ''}`}
        onClick={() => setLanguage('en')}
      >
        EN
      </button>
      <button
        type="button"
        className={`${styles.btn} ${current === 'zh' ? styles.active : ''}`}
        onClick={() => setLanguage('zh')}
      >
        中
      </button>
    </div>
  )
}
