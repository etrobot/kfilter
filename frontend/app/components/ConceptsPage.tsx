import { useState, useEffect, useRef } from 'react'
import { Button } from './ui/button'
import { TaskProgressCard } from './TaskProgressCard'
import { AuthDialog } from './AuthDialog'
import { api, createConceptTaskStatusPoller } from '../services/api'
import { ConceptRecord, ConceptTaskResult } from '../types'
import { AuthService } from '../services/auth'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'
import { useIsMobile } from '../hooks/use-mobile'

type SortField = 'name' | 'market_cap' | 'stock_count' | 'updated_at' | null
type SortDirection = 'asc' | 'desc'

export function ConceptsPage() {
  const pollerCleanupRef = useRef<(() => void) | null>(null)
  const isMobile = useIsMobile()
  const [concepts, setConcepts] = useState<ConceptRecord[]>([])
  const [currentTask, setCurrentTask] = useState<ConceptTaskResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [showAuthDialog, setShowAuthDialog] = useState(false)
  const [sortField, setSortField] = useState<SortField>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  const loadConcepts = async () => {
    try {
      const response = await api.getConcepts()
      setConcepts(response.concepts)
    } catch (err) {
      console.error('Failed to load concepts:', err)
    }
  }

  const handleCollectConceptsClick = () => {
    // 检查是否已认证
    if (AuthService.isAuthenticated()) {
      handleCollectConcepts()
    } else {
      setShowAuthDialog(true)
    }
  }

  const handleCollectConcepts = async () => {
    setError(null)
    setLoading(true)
    
    try {
      // Stop any existing poller
      if (pollerCleanupRef.current) {
        try { pollerCleanupRef.current() } catch {}
        pollerCleanupRef.current = null
      }

      const response = await api.collectConcepts()
      
      // Start polling for task status
      const cleanup = createConceptTaskStatusPoller(
        response.task_id,
        (task) => setCurrentTask(task),
        async (task) => {
          setCurrentTask(null)
          setLoading(false)
          await loadConcepts()
        },
        (errorMsg) => {
          setError(errorMsg)
          setCurrentTask(null)
          setLoading(false)
        }
      )
      pollerCleanupRef.current = cleanup
    } catch (err) {
      setError(err instanceof Error ? err.message : '启动采集任务失败')
      setLoading(false)
    }
  }

  const handleAuthSuccess = () => {
    handleCollectConcepts()
  }

  useEffect(() => {
    let cancelled = false

    const init = async () => {
      // Load existing concepts
      await loadConcepts()

      // Check for active concept tasks
      try {
        const tasks = await api.getAllConceptTasks()
        if (!cancelled && Array.isArray(tasks) && tasks.length > 0) {
          const active = tasks
            .filter(t => t.status === 'running' || t.status === 'pending')
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          
          if (active.length > 0) {
            const latest = active[0]
            setCurrentTask(latest)
            setLoading(true)

            const cleanup = createConceptTaskStatusPoller(
              latest.task_id,
              (task) => setCurrentTask(task),
              async (task) => {
                setCurrentTask(null)
                setLoading(false)
                await loadConcepts()
              },
              (errorMsg) => {
                setError(errorMsg)
                setCurrentTask(null)
                setLoading(false)
              }
            )
            pollerCleanupRef.current = cleanup
          }
        }
      } catch {
        // Ignore errors when checking tasks
      }
    }

    init()

    return () => {
      cancelled = true
      if (pollerCleanupRef.current) {
        try { pollerCleanupRef.current() } catch {}
        pollerCleanupRef.current = null
      }
    }
  }, [])

  const formatMarketCap = (marketCap?: number) => {
    if (!marketCap) return '-'
    if (marketCap >= 1e12) {
      return `${(marketCap / 1e12).toFixed(2)}万亿`
    } else if (marketCap >= 1e8) {
      return `${(marketCap / 1e8).toFixed(0)}亿`
    } else {
      return `${(marketCap / 1e4).toFixed(0)}万`
    }
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ChevronsUpDown className="w-4 h-4 text-gray-400 ml-1 inline" />
    }
    return sortDirection === 'asc' ? (
      <ChevronUp className="w-4 h-4 ml-1 inline" />
    ) : (
      <ChevronDown className="w-4 h-4 ml-1 inline" />
    )
  }

  const getSortedConcepts = () => {
    if (!sortField) return concepts

    return [...concepts].sort((a, b) => {
      let aValue: any
      let bValue: any

      switch (sortField) {
        case 'name':
          aValue = a.name
          bValue = b.name
          break
        case 'market_cap':
          aValue = a.market_cap || 0
          bValue = b.market_cap || 0
          break
        case 'stock_count':
          aValue = a.stock_count || 0
          bValue = b.stock_count || 0
          break
        case 'updated_at':
          aValue = a.updated_at ? new Date(a.updated_at).getTime() : 0
          bValue = b.updated_at ? new Date(b.updated_at).getTime() : 0
          break
        default:
          return 0
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue, 'zh-CN')
          : bValue.localeCompare(aValue, 'zh-CN')
      }

      return sortDirection === 'asc' ? (Number(aValue) - Number(bValue)) : (Number(bValue) - Number(aValue))
    })
  }

  return (
    <div className={`${isMobile ? 'p-4' : 'p-8'} space-y-6 w-full`}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">概念板块</h1>
          <p className="text-gray-600 mt-1">
            共 {concepts.length} 个概念板块
          </p>
        </div>
        <Button 
          onClick={handleCollectConceptsClick} 
          disabled={loading}
        >
          {loading ? '采集中...' : '采集概念数据'}
        </Button>
      </div>

      {currentTask && <TaskProgressCard task={currentTask} title="概念数据采集进度" />}

      {error && (
        <div className="text-red-500 p-4 bg-red-50 rounded-lg">
          错误: {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden border">
        <div className="overflow-auto max-h-[70vh] relative" style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'none' }}>
          <table className="min-w-full text-sm">
            <thead className="sticky top-0 z-30 bg-gray-50">
              <tr>
                <th 
                  className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap sticky left-0 z-40 bg-gray-50 border-r border-b cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('name')}
                >
                  板块信息 {renderSortIcon('name')}
                </th>
                <th 
                  className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('market_cap')}
                >
                  总市值 {renderSortIcon('market_cap')}
                </th>
                <th 
                  className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('stock_count')}
                >
                  个股个数 {renderSortIcon('stock_count')}
                </th>
                <th 
                  className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('updated_at')}
                >
                  更新时间 {renderSortIcon('updated_at')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {getSortedConcepts().map((concept, index) => (
                <tr key={concept.code} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm font-medium text-gray-900 sticky left-0 bg-white z-10 border-r">
                    <div>
                      <div>{concept.name}</div>
                      <div className="text-xs text-muted-foreground">{concept.code}</div>
                    </div>
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                    {formatMarketCap(concept.market_cap)}
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                    {concept.stock_count}
                  </td>
                  <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                    {concept.updated_at ? new Date(concept.updated_at).toLocaleString('zh-CN') : '-'}
                  </td>
                </tr>
              ))}
              {concepts.length === 0 && !loading && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                    暂无数据，点击右上角按钮开始采集概念数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <AuthDialog
        open={showAuthDialog}
        onOpenChange={setShowAuthDialog}
        onSuccess={handleAuthSuccess}
        title="概念数据采集权限验证"
        description="采集概念数据需要管理员权限，请输入用户名和密码"
      />
    </div>
  )
}