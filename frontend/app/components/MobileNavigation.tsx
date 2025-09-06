import React from 'react'
import { BarChart3, Lightbulb, TrendingUp } from 'lucide-react'
import { useIsMobile } from '../hooks/use-mobile'

interface MobileNavigationProps {
  currentPage: 'ranking' | 'concepts' | 'dashboard'
  setCurrentPage: (page: 'ranking' | 'concepts' | 'dashboard') => void
}

export function MobileNavigation({ currentPage, setCurrentPage }: MobileNavigationProps) {
  const isMobile = useIsMobile()
  
  if (!isMobile) {
    return null
  }

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
      <div className="flex justify-around">
        <button
          onClick={() => setCurrentPage('dashboard')}
          className={`flex flex-col items-center justify-center p-3 w-full transition-colors ${
            currentPage === 'dashboard'
              ? 'text-indigo-600'
              : 'text-gray-500'
          }`}
        >
          <TrendingUp size={20} />
          <span className="text-xs mt-1">面板</span>
        </button>
        <button
          onClick={() => setCurrentPage('ranking')}
          className={`flex flex-col items-center justify-center p-3 w-full transition-colors ${
            currentPage === 'ranking'
              ? 'text-indigo-600'
              : 'text-gray-500'
          }`}
        >
          <BarChart3 size={20} />
          <span className="text-xs mt-1">分析</span>
        </button>
        <button
          onClick={() => setCurrentPage('concepts')}
          className={`flex flex-col items-center justify-center p-3 w-full transition-colors ${
            currentPage === 'concepts'
              ? 'text-indigo-600'
              : 'text-gray-500'
          }`}
        >
          <Lightbulb size={20} />
          <span className="text-xs mt-1">概念</span>
        </button>
      </div>
    </nav>
  )
}