import { useState, useEffect } from 'react'
import { Button } from './ui/button'
import { PlayIcon, RefreshCwIcon, Settings2Icon, BarChart3Icon, ListIcon, StopCircleIcon } from 'lucide-react'
import { api } from '../services/api'
import { useIsMobile } from '../hooks/use-mobile'
import { AuthDialog } from './AuthDialog'
import { AuthService } from '../services/auth'
import { ConfigDialog } from './ConfigDialog'
import EvaluationSunburst from './EvaluationSunburst'
import { SectorList } from './SectorList'
import { SunburstData } from '../types'

interface SectorStock {
  code: string
  name: string
  price: number
  change_pct: number
  volume: number
  turnover: number
}

interface SectorData {
  sector_code: string
  sector_name: string
  total_stocks: number
  hotspot_count: number
  hotspot_ratio: number
  stocks: SectorStock[]
  concept_analysis?: string  // 新增：概念分析结果
  llm_evaluation?: any       // 新增：LLM评估结果
}

interface ExtendedAnalysisResult {
  analysis_date: string
  analysis_type?: string
  total_sectors_with_hotspots: number
  sectors_with_deepsearch_analysis?: number  // 新增：有深度搜索分析的板块数
  sectors_with_llm_evaluation?: number       // 新增：有LLM评估的板块数
  sectors: SectorData[]
  sunburst_data?: any
  from_cache?: boolean  // 新增：是否来自缓存
  cached_at?: string    // 新增：缓存时间
}

interface ExtendedAnalysisPageProps {
  result: ExtendedAnalysisResult | null
  error: string | null
  isRunning: boolean
  successMessage: string | null
  onResultChange: (result: ExtendedAnalysisResult | null) => void
  onErrorChange: (error: string | null) => void
  onLoadingChange: (loading: boolean) => void
  onSuccessChange: (message: string | null) => void
}

export function ExtendedAnalysisPage({
  result,
  error,
  isRunning,
  successMessage,
  onResultChange,
  onErrorChange,
  onLoadingChange,
  onSuccessChange
}: ExtendedAnalysisPageProps) {
  const isMobile = useIsMobile()
  const [showAuthDialog, setShowAuthDialog] = useState(false)
  const [showConfigDialog, setShowConfigDialog] = useState(false)
  const [pendingAction, setPendingAction] = useState<null | 'run' | 'config'>(null)
  const [hasLoadedCache, setHasLoadedCache] = useState(false)
  const [activeTab, setActiveTab] = useState<'chart' | 'list'>('chart')
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [runningTaskStatus, setRunningTaskStatus] = useState<any>(null)
  const [currentPollInterval, setCurrentPollInterval] = useState<NodeJS.Timeout | null>(null)

  // Check for running tasks on component mount
  useEffect(() => {
    const checkRunningTask = async () => {
      try {
        const status = await api.getRunningExtendedAnalysisStatus()
        if (status.status === 'running') {
          setCurrentTaskId(status.task_id)
          setRunningTaskStatus(status)
          onLoadingChange(true)
          onSuccessChange(status.message || '正在运行扩展分析...')
          // Start polling for this task
          const pollInterval = startTaskPolling(status.task_id)
          setCurrentPollInterval(pollInterval)
        }
      } catch (error) {
        // Silently ignore if no running task
        console.log('No running extended analysis task found')
      }
    }

    checkRunningTask()

    // Cleanup function to clear polling interval on component unmount
    return () => {
      if (currentPollInterval) {
        clearInterval(currentPollInterval)
        setCurrentPollInterval(null)
      }
    }
  }, []) // Empty dependency array - only run on mount/unmount

  // Load cached results on component mount
  useEffect(() => {
    const loadCachedResults = async () => {
      // Only load cache if we don't have results and haven't loaded cache yet
      if (!result && !hasLoadedCache && !isRunning) {
        try {
          const cachedResult = await api.getExtendedAnalysisResults()
          if (cachedResult && !cachedResult.message) {
            onResultChange(cachedResult)
          }
        } catch (error) {
          // Silently ignore cache loading errors
          console.log('No cached extended analysis results found')
        }
        setHasLoadedCache(true)
      }
    }

    loadCachedResults()
  }, [result, hasLoadedCache, isRunning, onResultChange])

  const startTaskPolling = (taskId: string) => {
    // Clear any existing polling interval first
    if (currentPollInterval) {
      clearInterval(currentPollInterval)
    }

    const pollInterval = setInterval(async () => {
      try {
        const taskStatus = await api.getExtendedAnalysisTaskStatus(taskId)
        setRunningTaskStatus(taskStatus)
        onSuccessChange(taskStatus.message || '正在运行扩展分析...')
        
        if (taskStatus.status === 'completed') {
          clearInterval(pollInterval)
          setCurrentPollInterval(null)
          if (taskStatus.result) {
            onResultChange(taskStatus.result)
            onSuccessChange(`分析完成！找到 ${taskStatus.result.total_sectors_with_hotspots} 个包含热点股票的板块`)
            setTimeout(() => onSuccessChange(null), 3000)
          }
          onLoadingChange(false)
          setCurrentTaskId(null)
          setRunningTaskStatus(null)
        } else if (taskStatus.status === 'failed') {
          clearInterval(pollInterval)
          setCurrentPollInterval(null)
          onErrorChange(taskStatus.error || '扩展分析失败')
          onSuccessChange(null)
          onLoadingChange(false)
          setCurrentTaskId(null)
          setRunningTaskStatus(null)
        }
      } catch (error) {
        clearInterval(pollInterval)
        setCurrentPollInterval(null)
        onErrorChange('获取任务状态失败')
        onLoadingChange(false)
        setCurrentTaskId(null)
        setRunningTaskStatus(null)
      }
    }, 2000) // Poll every 2 seconds
    
    // Store interval for cleanup
    return pollInterval
  }

  const runAnalysis = async (forceRefresh: boolean = false) => {
    // Clear any existing polling interval first
    if (currentPollInterval) {
      clearInterval(currentPollInterval)
      setCurrentPollInterval(null)
    }

    onLoadingChange(true)
    onErrorChange(null)
    onSuccessChange(null)
    // Only clear result if force refresh, otherwise keep existing result during loading
    if (forceRefresh) {
      onResultChange(null)
    }

    // 通过 SSE 获取过程反馈
    const close = api.createExtendedAnalysisStream((type, payload) => {
      if (type === 'start') {
        // 开始 - 获取任务ID
        const taskId = payload?.task_id
        if (taskId) {
          setCurrentTaskId(taskId)
        }
      } else if (type === 'progress') {
        // 实时进度提示
        const msg = payload?.message || '正在计算扩展分析...'
        onSuccessChange(msg)
      } else if (type === 'complete') {
        const data = payload?.result
        if (data?.error) {
          onErrorChange(data.error)
          onSuccessChange(null)
        } else {
          onResultChange(data)
          onSuccessChange(`分析完成！找到 ${data.total_sectors_with_hotspots} 个包含热点股票的板块`)
          setTimeout(() => onSuccessChange(null), 3000)
        }
        onLoadingChange(false)
        setCurrentTaskId(null)
        setRunningTaskStatus(null)
        setCurrentPollInterval(null)
      } else if (type === 'error') {
        onErrorChange(payload?.error || '运行分析时发生错误')
        onSuccessChange(null)
        onLoadingChange(false)
        setCurrentTaskId(null)
        setRunningTaskStatus(null)
        setCurrentPollInterval(null)
      }
    })

    return () => close()
  }

  const handleRunClick = () => {
    if (AuthService.isAuthenticated()) {
      runAnalysis()
    } else {
      setPendingAction('run')
      setShowAuthDialog(true)
    }
  }

  const handleAuthSuccess = () => {
    if (pendingAction === 'run') {
      runAnalysis()
    } else if (pendingAction === 'config') {
      setShowConfigDialog(true)
    }
    setPendingAction(null)
  }

  const handleConfigClick = () => {
    if (AuthService.isAuthenticated()) {
      setShowConfigDialog(true)
    } else {
      setPendingAction('config')
      setShowAuthDialog(true)
    }
  }

  const handleStopClick = async () => {
    if (currentTaskId) {
      try {
        // Clear polling interval immediately
        if (currentPollInterval) {
          clearInterval(currentPollInterval)
          setCurrentPollInterval(null)
        }

        await api.stopExtendedAnalysisTask(currentTaskId)
        onSuccessChange('已请求停止任务...')
        setTimeout(() => {
          onLoadingChange(false)
          setCurrentTaskId(null)
          setRunningTaskStatus(null)
          onSuccessChange(null)
        }, 2000)
      } catch (error) {
        onErrorChange('停止任务失败')
      }
    }
  }

  const convertToSunburstData = (result: ExtendedAnalysisResult): SunburstData => {
    // 优先使用后端生成的旭日图数据
    if (result.sunburst_data && result.sunburst_data.children && result.sunburst_data.children.length > 0) {
      return result.sunburst_data
    }
    
    // 如果没有后端数据或数据为空，则使用前端转换
    if (!result.sectors || result.sectors.length === 0) {
      return { name: "板块分析", children: [] }
    }

    return {
      name: "板块热点分析",
      children: result.sectors.map(sector => ({
        name: sector.sector_name,
        value: sector.hotspot_ratio,
        children: sector.stocks.length > 0 ? sector.stocks.map(stock => ({
          name: stock.name,
          value: stock.change_pct != null && Math.abs(stock.change_pct) > 0 ? Math.abs(stock.change_pct) : 1
        })) : undefined
      }))
    }
  }

  return (
    <div className={`${isMobile ? 'p-2' : 'p-8'} space-y-4`}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold text-gray-900">扩展分析</h1>
          <p className="text-gray-600 mt-1">
            板块深度分析
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            onClick={handleConfigClick}
            variant="outline"
            disabled={isRunning}
          >
            <Settings2Icon />
          </Button>
          {isRunning && currentTaskId ? (
            <Button 
              onClick={handleStopClick}
              variant="outline"
              className="flex items-center gap-2 text-red-600 border-red-200 hover:bg-red-50"
            >
              <StopCircleIcon size={16} />
              停止任务
            </Button>
          ) : null}
          <Button 
            onClick={handleRunClick}
            disabled={isRunning}
            className="flex items-center gap-2"
          >
            {isRunning ? (
              <>
                <RefreshCwIcon size={16} className="animate-spin" />
                运行中...
              </>
            ) : (
              <>
                <PlayIcon size={16} />
                运行
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="text-red-800">
            <strong>错误:</strong> {error}
          </div>
        </div>
      )}

      {/* Success Message */}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 rounded-md p-1">
          <div className="text-green-800">
            {successMessage}
            {currentTaskId && isRunning && (
              <span className="text-xs text-green-600 ml-2">
                (任务ID: {currentTaskId.slice(0, 8)})
              </span>
            )}
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-2">
          {/* Summary Stats */}
          <div className="bg-white border rounded-lg p-2">
            <div className="flex gap-4 text-sm">
              <div>
                <span className="text-gray-600">分析日期: </span>
                <span className="font-medium">{result.analysis_date}</span>
              </div>
              <div>
                <span className="text-gray-600">包含热点股票的板块数: </span>
                <span className="font-medium">{result.total_sectors_with_hotspots}</span>
              </div>
              {result.sectors_with_deepsearch_analysis !== undefined && (
                <div>
                  <span className="text-gray-600">深度分析板块数: </span>
                  <span className="font-medium text-blue-600">{result.sectors_with_deepsearch_analysis}</span>
                </div>
              )}
              {result.sectors_with_llm_evaluation !== undefined && (
                <div>
                  <span className="text-gray-600">LLM评估板块数: </span>
                  <span className="font-medium text-purple-600">{result.sectors_with_llm_evaluation}</span>
                </div>
              )}
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="bg-white border rounded-lg overflow-hidden">
            <div className="border-b">
              <div className="flex">
                <button
                  onClick={() => setActiveTab('chart')}
                  className={`flex items-center gap-2 px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                    activeTab === 'chart'
                      ? 'border-blue-500 text-blue-600 bg-blue-50'
                      : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <BarChart3Icon size={16} />
                  可视化图表
                </button>
                <button
                  onClick={() => setActiveTab('list')}
                  className={`flex items-center gap-2 px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                    activeTab === 'list'
                      ? 'border-blue-500 text-blue-600 bg-blue-50'
                      : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <ListIcon size={16} />
                  详细列表
                </button>
              </div>
            </div>

            {/* Tab Content */}
            <div className="min-h-[400px]">
              {activeTab === 'chart' && (
                <div className="p-3 bg-gray-50">
                  <h3 className="font-semibold text-gray-900 mb-4 text-center">板块热点可视化</h3>
                  <p className="text-sm text-gray-600 mb-6 text-center">
                    旭日图展示各板块热点比例及其包含的热点股票分布
                  </p>
                  <EvaluationSunburst data={convertToSunburstData(result)} />
                </div>
              )}
              
              {activeTab === 'list' && (
                <div className="p-0">
                  <SectorList sectors={result.sectors} />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {isRunning && !result && (
        <div className="bg-white border rounded-lg p-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <RefreshCwIcon size={20} className="animate-spin text-blue-600" />
            <span className="text-blue-600 font-medium">正在运行扩展分析...</span>  
          </div>
          <p className="text-gray-600 text-sm">
            正在分析实时热点股票的板块数据，请稍候...
          </p>
        </div>
      )}

      {!result && !error && !isRunning && (
        <div className="bg-white border rounded-lg p-8 text-center">
          <p className="text-gray-600 mb-4">点击"运行分析"开始扩展分析</p>
        </div>
      )}

      <AuthDialog
        open={showAuthDialog}
        onOpenChange={setShowAuthDialog}
        onSuccess={handleAuthSuccess}
        title="扩展分析运行权限验证"
        description="运行扩展分析需要管理员权限，请输入用户名和密码"
      />

      <ConfigDialog
        open={showConfigDialog}
        onOpenChange={setShowConfigDialog}
      />
    </div>
  )
}