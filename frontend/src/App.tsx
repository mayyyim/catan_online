import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { RoomProvider } from './context/RoomContext'
import { GameProvider } from './context/GameContext'

const Home = lazy(() => import('./pages/Home'))
const Auth = lazy(() => import('./pages/Auth'))
const Room = lazy(() => import('./pages/Room'))
const Game = lazy(() => import('./pages/Game'))
const Maps = lazy(() => import('./pages/Maps'))

function PageFallback() {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0d1b2a',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#6c757d',
        fontSize: '15px',
      }}
    >
      Loading...
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <RoomProvider>
          <GameProvider>
            <Suspense fallback={<PageFallback />}>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/auth" element={<Auth />} />
                <Route path="/maps" element={<Maps />} />
                <Route path="/room/:roomId" element={<Room />} />
                <Route path="/game/:roomId" element={<Game />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </GameProvider>
        </RoomProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
