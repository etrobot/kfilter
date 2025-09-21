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
import { TaskProgressCard } from './TaskProgressCard'
import { TaskResult, KLineData } from '../types'
import { useIsMobile } from '../hooks/use-mobile'
import { BarChart } from './BarChart'
import { Button } from './ui/button'
import { StockLink } from './StockLink'

interface DashboardData {
  stocks: KLineData[]
  top_5: KLineData[]
  last_5: KLineData[]
  random_5?: KLineData[]
}

interface DashboardPageProps {
  currentTask?: TaskResult | null
}

export function DashboardPage({ currentTask }: DashboardPageProps) {
  const [data, setData] = useState<DashboardData | null>(null)
  const isMobile = useIsMobile()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [nDays, setNDays] = useState<number>(30)
  const [randomLoading, setRandomLoading] = useState(false)

  const isTaskRunning = currentTask?.status === 'running' || currentTask?.status === 'pending'

  useEffect(() => {
    fetchDashboardData()
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

  const createChartOptions = (isDateData: boolean) => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
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




  const renderTrendChart = () => {
    if (!data?.top_5) return null

    const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6']
    const chartData = createChartData(data.top_5, colors)
    if (!chartData) return null

    const options = createChartOptions(true)

    return (
      <div className="bg-white p-3 rounded-lg shadow-md h-96">
        <h3 className="text-lg font-semibold mb-2">成交额前五名走势叠加图</h3>
        <div className="flex w-full justify-between bg-gray-100 p-1">
          {data.top_5.map((stock, idx) => (
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
      <div className="bg-white p-3 rounded-lg shadow-md h-96">
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
    <div className={`${isMobile ? 'p-4' : 'p-8'} space-y-6`}>
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
  )
}