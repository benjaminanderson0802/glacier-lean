import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GalleryThread } from './GalleryThread.tsx'
import './thread.css'
import '../../theme/deep-glacier-tokens.css'

const root = document.getElementById('root')
if (!root) throw new Error('Conversation gallery root is missing')
createRoot(root).render(<StrictMode><GalleryThread /></StrictMode>)
