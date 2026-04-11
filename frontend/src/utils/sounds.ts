// Minimal sound effects using Web Audio API (no external files needed)

let audioCtx: AudioContext | null = null
let _muted = localStorage.getItem('catan_muted') === 'true'

function getCtx(): AudioContext {
  if (!audioCtx) audioCtx = new AudioContext()
  return audioCtx
}

export function isMuted(): boolean {
  return _muted
}

export function setMuted(m: boolean): void {
  _muted = m
  localStorage.setItem('catan_muted', String(m))
}

function guard(): AudioContext | null {
  if (_muted) return null
  return getCtx()
}

export function playDiceRoll(): void {
  // Short rattling sound: rapid sequence of clicks
  const ctx = guard()
  if (!ctx) return
  for (let i = 0; i < 8; i++) {
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'square'
    osc.frequency.value = 200 + Math.random() * 400
    gain.gain.value = 0.08
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.06 + 0.05)
    osc.connect(gain).connect(ctx.destination)
    osc.start(ctx.currentTime + i * 0.06)
    osc.stop(ctx.currentTime + i * 0.06 + 0.05)
  }
}

export function playBuild(): void {
  // "Thud" sound: low frequency hit
  const ctx = guard()
  if (!ctx) return
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.type = 'sine'
  osc.frequency.value = 150
  osc.frequency.exponentialRampToValueAtTime(80, ctx.currentTime + 0.15)
  gain.gain.value = 0.2
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2)
  osc.connect(gain).connect(ctx.destination)
  osc.start()
  osc.stop(ctx.currentTime + 0.2)
}

export function playTurnStart(): void {
  // Short ascending chime: two quick notes
  const ctx = guard()
  if (!ctx) return
  const freqs = [523, 659] // C5, E5
  freqs.forEach((f, i) => {
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.value = f
    gain.gain.value = 0.12
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.12 + 0.15)
    osc.connect(gain).connect(ctx.destination)
    osc.start(ctx.currentTime + i * 0.12)
    osc.stop(ctx.currentTime + i * 0.12 + 0.15)
  })
}

export function playTradeComplete(): void {
  // Coin jingle: high pitched ping
  const ctx = guard()
  if (!ctx) return
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.type = 'sine'
  osc.frequency.value = 880
  gain.gain.value = 0.1
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3)
  osc.connect(gain).connect(ctx.destination)
  osc.start()
  osc.stop(ctx.currentTime + 0.3)
}

export function playVictory(): void {
  // Ascending fanfare: 4 quick notes
  const ctx = guard()
  if (!ctx) return
  const freqs = [523, 659, 784, 1047] // C5, E5, G5, C6
  freqs.forEach((f, i) => {
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'triangle'
    osc.frequency.value = f
    gain.gain.value = 0.15
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.15 + 0.3)
    osc.connect(gain).connect(ctx.destination)
    osc.start(ctx.currentTime + i * 0.15)
    osc.stop(ctx.currentTime + i * 0.15 + 0.3)
  })
}

export function playError(): void {
  // Low buzz
  const ctx = guard()
  if (!ctx) return
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.type = 'sawtooth'
  osc.frequency.value = 100
  gain.gain.value = 0.08
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15)
  osc.connect(gain).connect(ctx.destination)
  osc.start()
  osc.stop(ctx.currentTime + 0.15)
}
