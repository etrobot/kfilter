import React from 'react'
import { Download, X } from 'lucide-react'
import { usePWA } from '../hooks/usePWA'

export function PWAInstallPrompt() {
  const { isInstallable, installApp } = usePWA()
  const [showPrompt, setShowPrompt] = React.useState(false)

  React.useEffect(() => {
    if (isInstallable) {
      // Show prompt after a delay to not be intrusive
      const timer = setTimeout(() => setShowPrompt(true), 3000)
      return () => clearTimeout(timer)
    }
  }, [isInstallable])

  if (!isInstallable || !showPrompt) return null

  const handleInstall = async () => {
    const success = await installApp()
    if (success) {
      setShowPrompt(false)
    }
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-80 bg-white border border-gray-200 rounded-lg shadow-lg p-4 z-50">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <Download size={20} className="text-indigo-600" />
            <h3 className="font-medium text-gray-900">安装应用</h3>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            将股票分析系统添加到主屏幕，获得更好的使用体验
          </p>
          <div className="flex space-x-2">
            <button
              onClick={handleInstall}
              className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 transition-colors"
            >
              安装
            </button>
            <button
              onClick={() => setShowPrompt(false)}
              className="px-3 py-1.5 text-gray-600 text-sm rounded-md hover:bg-gray-100 transition-colors"
            >
              稍后
            </button>
          </div>
        </div>
        <button
          onClick={() => setShowPrompt(false)}
          className="text-gray-400 hover:text-gray-600 ml-2"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  )
}