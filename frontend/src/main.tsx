import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { initTheme } from './utils/theme'
import './i18n'
import './styles/global.css'

initTheme()

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {})
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
