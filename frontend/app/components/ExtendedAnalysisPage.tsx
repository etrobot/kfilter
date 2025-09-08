import { useState } from 'react'
import { Button } from './ui/button'
import { PlayIcon, RefreshCwIcon } from 'lucide-react'
import { api } from '../services/api'
import { useIsMobile } from '../hooks/use-mobile'

interface SectorStock {
  code: string
  name: string
  limit_up_count: number
  price: number
}

interface SectorData {
  sector_code: string
  sector_name: string
  total_stocks: number
  limit_up_count_today: number
  limit_up_ratio: number
  stocks: SectorStock[]
}

interface ExtendedAnalysisResult {
  analysis_date: string
  total_sectors_with_limit_ups: number
  sectors: SectorData[]
}

export function ExtendedAnalysisPage() {
  const [isRunning, setIsRunning] = useState(false)
  const isMobile = useIsMobile()
  const [result, setResult] = useState<ExtendedAnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const runAnalysis = async () => {
    setIsRunning(true)
    setError(null)

    try {
      const data = await api.runExtendedAnalysis()
      
      if (data.error) {
        setError(data.error)
      } else {
        setResult(data)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '运行分析时发生错误')
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className={`${isMobile ? 'p-4' : 'p-8'} space-y-6`}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">扩展分析</h1>
          <p className="text-gray-600 mt-1">
            基于最新交易日的板块涨停分析，展示各板块涨停股票及历史涨停次数
          </p>
        </div>
        <Button 
          onClick={runAnalysis}
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

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="text-red-800">
            <strong>错误:</strong> {error}
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
                <span className="text-gray-600">有涨停的板块数: </span>
                <span className="font-medium">{result.total_sectors_with_limit_ups}</span>
              </div>
            </div>
          </div>

          <div className="bg-white border rounded-lg overflow-hidden">
            <div className="p-4 border-b bg-gray-50">
              <h3 className="font-semibold">板块涨停分析</h3>
              <p className="text-sm text-gray-600 mt-1">
                按涨停比例排序，显示各板块的涨停股票及其历史表现
              </p>
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
                          {sector.limit_up_ratio}%
                        </div>
                        <div className="text-sm text-gray-600">
                          {sector.limit_up_count_today}/{sector.total_stocks} 涨停
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
                            <th className="text-right p-3 font-medium">历史涨停次数</th>
                            <th className="text-right p-3 font-medium">当前价格</th>
                          </tr>
                        </thead>
                        <tbody>
                          {sector.stocks.map((stock, stockIndex) => (
                            <tr key={stock.code} className="border-t">
                              <td className="p-3">{stockIndex + 1}</td>
                              <td className="p-3 font-mono">{stock.code}</td>
                              <td className="p-3">{stock.name}</td>
                              <td className="p-3 text-right font-semibold text-red-600">
                                {stock.limit_up_count}
                              </td>
                              <td className="p-3 text-right">
                                ¥{stock.price.toFixed(2)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {result.sectors.length === 0 && (
            <div className="bg-white border rounded-lg p-8 text-center">
              <p className="text-gray-600">当日无涨停板块数据</p>
            </div>
          )}
        </div>
      )}

      {!result && !error && !isRunning && (
        <div className="bg-white border rounded-lg p-8 text-center">
          <p className="text-gray-600 mb-4">点击"运行分析"开始扩展分析</p>
        </div>
      )}
    </div>
  )
}