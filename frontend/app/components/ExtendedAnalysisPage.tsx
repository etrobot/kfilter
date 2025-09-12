import { useState, useEffect } from 'react'
import { Button } from './ui/button'
import { PlayIcon, RefreshCwIcon, ClockIcon } from 'lucide-react'
import { api } from '../services/api'
import { useIsMobile } from '../hooks/use-mobile'
import { AuthDialog } from './AuthDialog'
import { AuthService } from '../services/auth'
import { ConfigDialog } from './ConfigDialog'
import EvaluationSunburst from './EvaluationSunburst'
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

  const runAnalysis = async (forceRefresh: boolean = false) => {
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
        // 开始
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
      } else if (type === 'error') {
        onErrorChange(payload?.error || '运行分析时发生错误')
        onSuccessChange(null)
        onLoadingChange(false)
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
    <div className={`${isMobile ? 'p-4' : 'p-8'} space-y-6`}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">扩展分析</h1>
          <p className="text-gray-600 mt-1">
            基于实时热点股票的板块分析，展示各板块热点股票及其市场表现
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            onClick={handleConfigClick}
            variant="outline"
            disabled={isRunning}
          >
            配置
          </Button>
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
                运行分析
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
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="text-green-800">
            <strong>成功:</strong> {successMessage}
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <div className="bg-white border rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-4">分析结果</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
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
          <div className="bg-white border rounded-lg overflow-hidden">
            <div className="p-4 border-b bg-gray-50">
              <h3 className="font-semibold">板块热点分析</h3>
              <p className="text-sm text-gray-600 mt-1">
                按热点比例排序，显示各板块的热点股票及其实时表现
              </p>
            </div>
            
            {/* 旭日图可视化 */}
            <div className="p-6 border-b bg-gradient-to-r from-blue-50 to-indigo-50">
              <h4 className="font-medium text-gray-900 mb-4 text-center">板块热点可视化</h4>
              <EvaluationSunburst data={convertToSunburstData(result)} />
            </div>
            
            <div className="max-h-[70vh] overflow-y-auto" style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'none' }}>
              {result.sectors.map((sector, index) => (
                <div key={sector.sector_code} className="border-b last:border-b-0">
                  <div className="p-4 bg-gray-25">
                    <div className="flex justify-between items-center">
                      <div>
                        <h4 className="font-medium text-gray-900">
                          #{index + 1} {sector.sector_name}
                        </h4>
                        <p className="text-sm text-gray-600">
                          代码: {sector.sector_code}
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-red-600">
                          {sector.hotspot_ratio}%
                        </div>
                        <div className="text-sm text-gray-600">
                          {sector.hotspot_count}/{sector.total_stocks} 热点
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {sector.stocks.length > 0 && (
                    <div className="overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'none' }}>
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="text-left p-3 font-medium">序号</th>
                            <th className="text-left p-3 font-medium">股票代码</th>
                            <th className="text-left p-3 font-medium">股票名称</th>
                            <th className="text-right p-3 font-medium">涨跌幅</th>
                            <th className="text-right p-3 font-medium">当前价格</th>
                            <th className="text-right p-3 font-medium">成交额</th>
                          </tr>
                        </thead>
                        <tbody>
                          {sector.stocks.map((stock, stockIndex) => (
                            <tr key={stock.code} className="border-t">
                              <td className="p-3">{stockIndex + 1}</td>
                              <td className="p-3 font-mono">{stock.code}</td>
                              <td className="p-3">{stock.name}</td>
                              <td className="p-3 text-right font-semibold" style={{color: (stock.change_pct ?? 0) >= 0 ? '#dc2626' : '#16a34a'}}>
                                {stock.change_pct != null ? `${stock.change_pct > 0 ? '+' : ''}${stock.change_pct.toFixed(2)}%` : 'N/A'}
                              </td>
                              <td className="p-3 text-right">
                                {stock.price != null ? `¥${stock.price.toFixed(2)}` : 'N/A'}
                              </td>
                              <td className="p-3 text-right">
                                {stock.turnover != null ? `${(stock.turnover / 10000).toFixed(2)}万` : 'N/A'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  
                  {/* 概念分析内容 */}
                  {sector.concept_analysis && (
                    <div className="p-4 bg-blue-50 border-t">
                      <h5 className="font-medium text-blue-900 mb-2 flex items-center gap-2">
                        <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                        概念深度分析
                      </h5>
                      <div className="text-sm text-blue-800 leading-relaxed whitespace-pre-wrap">
                        {sector.concept_analysis}
                      </div>
                    </div>
                  )}
                  
                  {/* LLM评估结果 */}
                  {sector.llm_evaluation && (
                    <div className="p-4 bg-purple-50 border-t">
                      <h5 className="font-medium text-purple-900 mb-2 flex items-center gap-2">
                        <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                        LLM智能评估
                      </h5>
                      <div className="text-sm text-purple-800 leading-relaxed">
                        {typeof sector.llm_evaluation === 'string' 
                          ? sector.llm_evaluation 
                          : JSON.stringify(sector.llm_evaluation, null, 2)
                        }
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {result.sectors.length === 0 && (
            <div className="bg-white border rounded-lg p-8 text-center">
              <p className="text-gray-600">当前无热点板块数据</p>
            </div>
          )}
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