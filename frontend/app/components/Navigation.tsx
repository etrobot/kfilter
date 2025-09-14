import { BarChart3, Lightbulb, TrendingUp, Target } from 'lucide-react'
import { useIsMobile } from '../hooks/use-mobile'

interface NavigationItem {
  id: 'ranking' | 'concepts' | 'dashboard' | 'extended-analysis'
  icon: React.ComponentType<{ size?: number }>
  label: string
}

interface NavigationProps {
  currentPage: 'ranking' | 'concepts' | 'dashboard' | 'extended-analysis'
  setCurrentPage: (page: 'ranking' | 'concepts' | 'dashboard' | 'extended-analysis') => void
}

const navigationItems: NavigationItem[] = [
  { id: 'dashboard', icon: TrendingUp, label: '面板' },
  { id: 'ranking', icon: BarChart3, label: '分析' },
  { id: 'extended-analysis', icon: Target, label: '扩展' },
  { id: 'concepts', icon: Lightbulb, label: '概念' },
]

export function Navigation({ currentPage, setCurrentPage }: NavigationProps) {
  const isMobile = useIsMobile()

  if (isMobile) {
    // Mobile bottom navigation
    return (
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
        <div className="flex justify-around">
          {navigationItems.map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              onClick={() => setCurrentPage(id)}
              className={`flex flex-col items-center justify-center p-3 w-full transition-colors ${
                currentPage === id
                  ? 'text-indigo-600'
                  : 'text-gray-500'
              }`}
            >
              <Icon size={20} />
              <span className="text-xs mt-1">{label}</span>
            </button>
          ))}
        </div>
      </nav>
    )
  }

  // Desktop sidebar navigation
  return (
    <nav className="bg-white shadow-md w-20 flex flex-col">
      <div className="flex flex-col space-y-4 p-4">
        {navigationItems.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            onClick={() => setCurrentPage(id)}
            className={`flex flex-col items-center justify-center p-3 rounded-lg transition-colors ${
              currentPage === id
                ? 'bg-indigo-100 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Icon size={24} />
            <span className="text-xs mt-1">{label}</span>
          </button>
        ))}
      </div>
    </nav>
  )
}