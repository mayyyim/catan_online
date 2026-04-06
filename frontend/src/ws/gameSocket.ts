import type { ClientMessage, ServerMessage } from '../types'

type MessageHandler = (msg: ServerMessage) => void
type StatusHandler = (status: 'connected' | 'disconnected' | 'error') => void

class GameSocket {
  private ws: WebSocket | null = null
  private handlers: MessageHandler[] = []
  private statusHandlers: StatusHandler[] = []
  private pingInterval: ReturnType<typeof setInterval> | null = null
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  private roomId = ''
  private playerId = ''
  private shouldReconnect = false

  connect(roomId: string, playerId: string): void {
    this.roomId = roomId
    this.playerId = playerId
    this.shouldReconnect = true
    this.openSocket()
  }

  private openSocket(): void {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const url = `${protocol}://${host}/ws/${this.roomId}/${this.playerId}`

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.notifyStatus('connected')
      this.pingInterval = setInterval(() => this.send({ type: 'ping' }), 20_000)
    }

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as ServerMessage
        this.handlers.forEach(h => h(msg))
      } catch {
        // malformed message — ignore
      }
    }

    this.ws.onclose = () => {
      this.cleanup()
      this.notifyStatus('disconnected')
      if (this.shouldReconnect) {
        this.reconnectTimeout = setTimeout(() => this.openSocket(), 3_000)
      }
    }

    this.ws.onerror = () => {
      this.notifyStatus('error')
    }
  }

  send(message: ClientMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.push(handler)
    return () => {
      this.handlers = this.handlers.filter(h => h !== handler)
    }
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.push(handler)
    return () => {
      this.statusHandlers = this.statusHandlers.filter(h => h !== handler)
    }
  }

  disconnect(): void {
    this.shouldReconnect = false
    this.cleanup()
    this.ws?.close()
    this.ws = null
  }

  private cleanup(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
  }

  private notifyStatus(status: 'connected' | 'disconnected' | 'error'): void {
    this.statusHandlers.forEach(h => h(status))
  }
}

// Singleton per tab
export const gameSocket = new GameSocket()
