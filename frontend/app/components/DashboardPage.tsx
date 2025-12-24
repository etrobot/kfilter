import { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { api } from '../services/api'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend
)
import ReactMarkdown from 'react-markdown'
import { TaskProgressCard } from './TaskProgressCard'
import { TaskResult, KLineData } from '../types'
import { useIsMobile } from '../hooks/use-mobile'
import { BarChart } from './BarChart'
import { Button } from './ui/button'
import { StockLink } from './StockLink'

interface DashboardData {
  stocks: KLineData[]
  hot_stocks: KLineData[]
  top_5: KLineData[]
  last_5: KLineData[]
  random_5?: KLineData[]
}

interface DashboardPageProps {
  currentTask?: TaskResult | null
}

interface MarketAnalysisData {
  success: boolean
  analysis: string
  last_updated?: string
  error?: string
  file_exists?: boolean
}

export function DashboardPage({ currentTask }: DashboardPageProps) {
  const [data, setData] = useState<DashboardData | null>(null)
  const isMobile = useIsMobile()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [nDays, setNDays] = useState<number>(30)
  const [randomLoading, setRandomLoading] = useState(false)
  const [paginationOffset, setPaginationOffset] = useState<number>(0)
  const [marketAnalysis, setMarketAnalysis] = useState<MarketAnalysisData | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false)
  const [analysisMessage, setAnalysisMessage] = useState<string | null>(null)

  const isTaskRunning = currentTask?.status === 'running' || currentTask?.status === 'pending'

  useEffect(() => {
    fetchDashboardData()
    fetchMarketAnalysis()
  }, [nDays])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.getDashboardData(nDays)
      setData(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dashboard data')
    } finally {
      setLoading(false)
    }
  }

  const fetchMarketAnalysis = async () => {
    setIsLoadingAnalysis(true)
    setAnalysisMessage(null)
    try {
      const response = await api.getMarketAnalysis()
      setMarketAnalysis(response)
    } catch (err) {
      console.error('Failed to fetch market analysis:', err)
      setMarketAnalysis({
        success: false,
        analysis: '',
        error: '加载分析失败',
        file_exists: false,
      })
    } finally {
      setIsLoadingAnalysis(false)
    }
  }

  const handleGenerateAnalysis = async () => {
    setIsGenerating(true)
    setAnalysisMessage('正在生成分析...')
    try {
      const response = await api.generateMarketAnalysis()

      if (response.success) {
        await fetchMarketAnalysis()
        setAnalysisMessage(null)
      } else {
        setAnalysisMessage(response.error || '生成失败，请稍后再试')
      }
    } catch (err) {
      console.error('Failed to generate market analysis:', err)
      setAnalysisMessage('生成分析时发生错误，请稍后重试')
    } finally {
      setIsGenerating(false)
    }
  }

  const createChartOptions = (isDateData: boolean) => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom' as const,
        labels: {
          boxWidth: 12,
          font: {
            size: 10
          },
          padding: 5
        }
      },
      tooltip: {
        callbacks: {
          title: (context: any) => {
            const label = context[0].label
            return typeof label === 'string' && label.includes('-')
              ? label
              : `第${label}个交易日`
          },
          label: (context: any) => {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`
          },
        },
      },
    },
    scales: {
      x: {
        title: {
          display: false,
        },
        ticks: {
          font: {
            size: 10,
          },
          maxTicksLimit: 8,
          maxRotation: 45,
          minRotation: 0,
        },
        grid: {
          display: false,
        },
      },
      y: {
        title: {
          display: false,
        },
        ticks: {
          callback: (value: any) => `${value}%`,
          font: {
            size: 10,
          },
        },
        grid: {
          display: true,
        },
      },
    },
    interaction: {
      intersect: false,
      mode: 'index' as const,
    },
  })

  const createChartData = (stocks: KLineData[], colorPalette: string[]) => {
    if (!stocks || stocks.length === 0) return null

    const labels = stocks.length > 0 && stocks[0].dates && stocks[0].dates.length > 0
      ? stocks[0].dates
      : Array.from({ length: Math.max(...stocks.map(stock => stock.trend_data?.length || 0)) }, (_, i) => (i + 1).toString())

    return {
      labels,
      datasets: stocks.map((stock, idx) => ({
        label: `${stock.code} ${stock.name}`,
        data: stock.trend_data || [],
        borderColor: colorPalette[idx % colorPalette.length],
        backgroundColor: colorPalette[idx % colorPalette.length] + '20',
        borderWidth: 2,
        fill: false,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4,
      })),
    }
  }

  const refreshRandomStocks = async () => {
    try {
      setRandomLoading(true)
      const randomStocks = await api.getRandomStocks(nDays)
      setData(prev => prev ? { ...prev, random_5: randomStocks.random_5 } : null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch random stocks')
    } finally {
      setRandomLoading(false)
    }
  }

  const getPaginatedStocks = () => {
    if (!data?.hot_stocks || data.hot_stocks.length === 0) return []
    const startIndex = paginationOffset
    const endIndex = paginationOffset + 5
    // If we have fewer than 5 stocks, just return what we have
    return data.hot_stocks.slice(startIndex, endIndex)
  }

  const handleNextPage = () => {
    if (data?.hot_stocks && paginationOffset + 5 < data.hot_stocks.length) {
      setPaginationOffset(prev => prev + 5)
    }
  }

  const handlePrevPage = () => {
    if (paginationOffset >= 5) {
      setPaginationOffset(prev => prev - 5)
    }
  }

  const renderTrendChart = () => {
    const paginatedStocks = getPaginatedStocks()
    if (paginatedStocks.length === 0) return null

    const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6']
    const chartData = createChartData(paginatedStocks, colors)
    if (!chartData) return null

    const options = createChartOptions(true)
    const currentPage = Math.floor(paginationOffset / 5) + 1
    const totalPages = data?.hot_stocks ? Math.ceil(data.hot_stocks.length / 5) : 1

    return (
      <div className="bg-white p-3 rounded-lg h-96">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-lg font-semibold">
            成交额{paginationOffset + 1}-{Math.min(paginationOffset + 5, data?.stocks?.length || 0)} 走势叠加图
          </h3>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrevPage}
              disabled={paginationOffset === 0 || loading}
              className="text-xs"
            >
              上一页
            </Button>
            <span className="text-sm text-gray-600">
              {currentPage} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleNextPage}
              disabled={!data?.stocks || paginationOffset + 5 >= data.stocks.length || loading}
              className="text-xs"
            >
              下一页
            </Button>
          </div>
        </div>
        <div className="flex w-full justify-between bg-gray-100 p-1">
          {paginatedStocks.map((stock, idx) => (
            <StockLink
              key={stock.code}
              code={stock.code}
              name={stock.name}
              className="text-xs"
            />
          ))}
        </div>
        <div className="h-72">
          <Line data={chartData} options={options} />
        </div>
      </div>
    )
  }

  const renderLastFiveTrendChart = () => {
    const chartData = data?.random_5 || data?.last_5
    if (!chartData) return null

    const colors = ['#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f59e0b']
    const chartDataConfig = createChartData(chartData, colors)
    if (!chartDataConfig) return null

    const options = createChartOptions(true)

    return (
      <div className="bg-white p-3 rounded-lg h-96">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-lg font-semibold">随机五名走势叠加图</h3>
          <Button
            variant="outline"
            size="sm"
            onClick={refreshRandomStocks}
            disabled={randomLoading || isTaskRunning}
          >
            {randomLoading ? '请求中...' : '换一批'}
          </Button>
        </div>
        <div className="flex w-full justify-between bg-gray-100 p-1">
          {chartData.map((stock, idx) => (
            <StockLink
              key={stock.code}
              code={stock.code}
              name={stock.name}
              className="text-xs"
            />
          ))}
        </div>
        <div className="h-72">
          <Line data={chartDataConfig} options={options} />
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-6 xl:space-y-0 xl:grid xl:grid-cols-[minmax(0,1.1fr)_minmax(0,2fr)] xl:gap-4">
      <div className="space-y-6 lg:max-h-[calc(100vh-4rem)] lg:overflow-y-auto lg:pr-2 no-scrollbar">
        <div className="w-full bg-white rounded-lg p-4 space-y-4">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">市场分析报告</h2>
              {marketAnalysis?.last_updated && (
                <p className="text-sm text-gray-500">上次更新：{marketAnalysis.last_updated}</p>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={fetchMarketAnalysis}
                disabled={isLoadingAnalysis || isGenerating}
              >
                {isLoadingAnalysis ? '刷新中...' : '刷新分析'}
              </Button>
              <Button
                size="sm"
                onClick={handleGenerateAnalysis}
                disabled={isGenerating || isTaskRunning}
              >
                {isGenerating ? '生成中...' : '生成分析'}
              </Button>
            </div>
          </div>
          <div className="w-full min-h-[180px] rounded-md bg-gray-50 p-4">
            {isLoadingAnalysis ? (
              <div className="text-sm text-gray-500">分析加载中...</div>
            ) : marketAnalysis?.analysis ? (
              <div className="text-sm leading-relaxed space-y-3 text-gray-900 max-h-[70vh] overflow-y-auto pr-2 no-scrollbar">
                <ReactMarkdown
                  components={{
                    p: ({ node, ...props }) => (
                      <p className="mb-3 last:mb-0" {...props} />
                    ),
                    li: ({ node, ...props }) => (
                      <li className="mb-1 last:mb-0" {...props} />
                    ),
                  }}
                >
                  {marketAnalysis.analysis}
                </ReactMarkdown>
              </div>
            ) : marketAnalysis?.error ? (
              <div className="text-sm text-red-500 whitespace-pre-line">
                {marketAnalysis.error}
              </div>
            ) : analysisMessage ? (
              <div className="text-sm text-gray-700 whitespace-pre-line">{analysisMessage}</div>
            ) : (
              <div className="text-sm text-gray-500">
                {marketAnalysis?.file_exists === false
                  ? '暂无分析，请先生成市场分析。'
                  : '暂无可显示的分析内容。'}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-bold text-gray-900">大成交额标的分析</h1>
            {currentTask && (
              <div className="text-sm text-gray-600">
                {currentTask.message} ({(currentTask.progress * 100).toFixed(0)}%)
              </div>
            )}
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium">天数:</label>
              <select
                value={nDays}
                onChange={(e) => setNDays(Number(e.target.value))}
                className="border rounded px-2 py-1 text-sm"
                disabled={isTaskRunning}
              >
                <option value={7}>7天</option>
                <option value={15}>15天</option>
                <option value={30}>30天</option>
                <option value={60}>60天</option>
              </select>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="text-red-800">错误: {error}</div>
            <button
              onClick={() => setError(null)}
              className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
            >
              关闭
            </button>
          </div>
        )}

        {currentTask && <TaskProgressCard task={currentTask} title="数据分析进度" />}

        {loading && (
          <div className="flex justify-center items-center h-64">
            <div className="text-gray-500">加载中...</div>
          </div>
        )}

        {!loading && (
          <div className="space-y-6">
            <div>
              <BarChart stocks={data?.stocks || []} nDays={nDays} />
            </div>
            <div className="md:flex md:gap-4">
              <div className="flex-1">{renderTrendChart()}</div>
              <div className="flex-1">{renderLastFiveTrendChart()}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}