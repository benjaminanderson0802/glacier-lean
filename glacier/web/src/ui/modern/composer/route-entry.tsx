import { createRoot } from 'react-dom/client'
import '../../../theme/deep-glacier-tokens.css'
import './GalleryRoute.tsx'
import GalleryRoute from './GalleryRoute.tsx'
import './route-entry.css'

const root = document.getElementById('root')
if (root) createRoot(root).render(<GalleryRoute />)
