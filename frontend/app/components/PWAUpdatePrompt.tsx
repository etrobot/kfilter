import React from 'react'
import { RefreshCw } from 'lucide-react'

interface PWAUpdatePromptProps {
  onUpdate: () => void
  show: boolean
}

export function PWAUpdatePrompt({ onUpdate, show }: PWAUpdatePromptProps) {
  if (!show) return null

  return (
    <div className="fixed top-4 left-4 right-4 md:left-auto md:right-4 md:w-80 bg-indigo-600 text-white rounded-lg shadow-lg p-4 z-50">
      <div className="flex items-center space-x-2 mb-2">
        <RefreshCw size={20} />
        <h3 className="font-medium">新版本可用</h3>
      </div>
      <p className="text-sm text-indigo-100 mb-3">
        发现新版本，点击更新获得最新功能
      </p>
      <button
        onClick={onUpdate}
        className="w-full px-3 py-2 bg-white text-indigo-600 text-sm font-medium rounded-md hover:bg-indigo-50 transition-colors"
      >
        立即更新
      </button>
    </div>
  )
}