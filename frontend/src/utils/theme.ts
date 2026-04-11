export type Theme = 'dark' | 'light'

export function getTheme(): Theme {
  return (localStorage.getItem('catan_theme') as Theme) ?? 'dark'
}

export function setTheme(theme: Theme) {
  localStorage.setItem('catan_theme', theme)
  document.documentElement.setAttribute('data-theme', theme)
}

export function initTheme() {
  setTheme(getTheme())
}
