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

interface DashboardData {
  stocks: KLineData[]
  top_5: KLineData[]
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


  

  const renderTrendChart = () => {
    if (!data?.top_5) return null

    const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6']

    // Use actual dates from the first stock that has dates, or fallback to indices
    const labels = data.top_5.length > 0 && data.top_5[0].dates && data.top_5[0].dates.length > 0
      ? data.top_5[0].dates
      : Array.from({ length: Math.max(...data.top_5.map(stock => stock.trend_data?.length || 0)) }, (_, i) => (i + 1).toString())

    const chartData = {
      labels,
      datasets: data.top_5.map((stock, idx) => ({
        label: `${stock.code} ${stock.name}`,
        data: stock.trend_data || [],
        borderColor: colors[idx % colors.length],
        backgroundColor: colors[idx % colors.length] + '20',
        borderWidth: 2,
        fill: false,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4,
      })),
    }

    const options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top' as const,
          labels: {
            usePointStyle: true,
            pointStyle: 'circle',
            font: {
              size: 12,
            },
            boxWidth: 8,
            boxHeight: 8,
          },
        },
        tooltip: {
          callbacks: {
            title: (context: any) => {
              // Show actual date if available, otherwise show trading day index
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
            display: true,
            text: labels.length > 0 && typeof labels[0] === 'string' && labels[0].includes('-') ? '日期' : '交易日',
            font: {
              size: 12,
            },
          },
          ticks: {
            font: {
              size: 10,
            },
            maxTicksLimit: 8, // Limit number of ticks to prevent overcrowding
            maxRotation: 45, // Rotate labels if they're dates
            minRotation: 0,
          },
          grid: {
            display: false,
          },
        },
        y: {
          title: {
            display: true,
            text: '涨跌幅 (%)',
            font: {
              size: 12,
            },
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
    }

    return (
      <div className="bg-white p-6 rounded-lg shadow-md h-96">
        <h3 className="text-lg font-semibold mb-4">前五名走势叠加图</h3>
        <div className="h-80">
          <Line data={chartData} options={options} />
        </div>
      </div>
    )
  }

  const renderStockList = () => {
    if (!data?.stocks) return null

    return (
      <div className="bg-white p-6 rounded-lg shadow-md h-96">
        <h3 className="text-lg font-semibold mb-4">股票列表</h3>
        <div className="space-y-2 h-80 overflow-y-auto" style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'none' }}>
          <div className="flex items-center space-x-3 pb-2 border-b font-semibold text-sm text-gray-600">
            <div className="w-16">代码</div>
            <div className="w-20">名称</div>
            <div className="w-20 text-right">幅度%</div>
            <div className="flex-1 text-center">排名</div>
          </div>
          {data.stocks.map((stock, index) => (
            <div key={stock.code} className="flex items-center space-x-3 py-1">
              <div className="text-sm font-mono w-16">{stock.code}</div>
              <div className="text-sm w-20 truncate">{stock.name}</div>
              <div className={`text-sm font-mono w-20 text-right ${stock.amplitude >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                {stock.amplitude > 0 ? '+' : ''}{stock.amplitude.toFixed(2)}%
              </div>
              <div className="flex-1 text-center text-sm text-gray-500">#{index + 1}</div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className={`${isMobile ? 'p-4' : 'p-8'} space-y-6`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-900">大成交额标的分析</h1>
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
            <div className="flex-1">{renderStockList()}</div>
          </div>
        </div>
      )}
    </div>
  )
}