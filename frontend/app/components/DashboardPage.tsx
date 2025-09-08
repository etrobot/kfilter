import { useState, useEffect } from 'react'
import { ResponsiveBar } from '@nivo/bar'
import { ResponsiveLine } from '@nivo/line'
import { api } from '../services/api'
import { TaskProgressCard } from './TaskProgressCard'
import { TaskResult } from '../types'
import { useIsMobile } from '../hooks/use-mobile'

interface KLineData {
  code: string
  name: string
  amplitude: number
  trend_data: number[]
  dates: string[]
}

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


  const renderBarChart = () => {
    if (!data?.stocks) return null

    const chartData = data.stocks.map(stock => ({
      code: stock.code,
      name: stock.name,
      amplitude: stock.amplitude,
    }))

    return (
      <div className="bg-white p-2 rounded-lg shadow-md">
        <h3 className="mb-4">K线实体排行 (过去{nDays}天,越短越安全)</h3>
        <div className="h-64 w-full overflow-x-auto md:overflow-x-visible" style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'none' }}>
          <div className="min-w-[1200px] md:min-w-full h-full">
            <ResponsiveBar
              data={chartData}
              keys={["amplitude"]}
              indexBy="name"
              margin={{ top: 10, right: 10, bottom: 80, left: 40 }}
              padding={0.2}
              colors={(bar: any) => (((bar.data as any).amplitude as number) >= 0 ? '#ef4444' : '#22c55e')}
              enableGridY={true}
              enableGridX={false}
              axisBottom={{
                tickSize: 5,
                tickPadding: 5,
                tickRotation: -45,
              }}
              axisLeft={{
                tickSize: 5,
                tickPadding: 5,
                format: (v: number) => `${v}%`,
              }}
              labelSkipWidth={12}
              labelSkipHeight={12}
              labelTextColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
              tooltip={(bar: any) => (
                <div style={{ background: 'white', padding: '6px 8px', border: '1px solid #eee', fontSize: 12 }}>
                  <div style={{ marginBottom: 4 }}>{bar.indexValue as string}</div>
                  <div><span style={{ color: bar.color }}>幅度</span>: {bar.data.amplitude > 0 ? '+' : ''}{Number(bar.data.amplitude).toFixed(2)}%</div>
                </div>
              )}
              theme={{
                axis: {
                  ticks: {
                    text: {
                      fontSize: 10,
                    },
                  },
                  legend: { text: { fontSize: 12 } },
                },
              }}
              role="img"
            />
          </div>
        </div>
      </div>
    )
  }

  const renderTrendChart = () => {
    if (!data?.top_5) return null

    const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6']

    const series = data.top_5.map((stock, idx) => ({
      id: `${stock.code} ${stock.name}`,
      color: colors[idx % colors.length],
      data: (stock.trend_data || []).map((y, i) => ({ x: i + 1, y })),
    }))

    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">前五名走势叠加图</h3>
        <div className="h-80">
          <ResponsiveLine
            data={series}
            margin={{ top: 40, right: 10, bottom: 40, left: 50 }}
            xScale={{ type: 'linear' }}
            yScale={{ type: 'linear', stacked: false, min: 'auto', max: 'auto' }}
            curve="monotoneX"
            axisBottom={{
              tickSize: 5,
              tickPadding: 5,
              tickRotation: 0,
              legend: '交易日',
              legendOffset: 32,
              legendPosition: 'middle',
            }}
            axisLeft={{
              tickSize: 5,
              tickPadding: 5,
              tickRotation: 0,
              format: (v: number) => `${v}%`,
              legend: '涨跌幅 (%)',
              legendOffset: -40,
              legendPosition: 'middle',
            }}
            enableGridX={false}
            enableGridY={true}
            enablePoints={false}
            lineWidth={2}
            colors={{ datum: 'color' }}
            useMesh={true}
            tooltip={({ point }: any) => (
              <div style={{ background: 'white', padding: '6px 8px', border: '1px solid #eee', fontSize: 12 }}>
                <div style={{ marginBottom: 4 }}><span style={{ color: point.serieColor }}>{point.serieId}</span></div>
                <div>第{point.data.x as number}个交易日: {Number(point.data.y).toFixed(2)}%</div>
              </div>
            )}
            legends={[{
              anchor: 'top',
              direction: 'row',
              justify: false,
              translateX: 0,
              translateY: -30,
              itemsSpacing: 8,
              itemDirection: 'left-to-right',
              itemWidth: 120,
              itemHeight: 16,
              itemOpacity: 1,
              symbolSize: 8,
              symbolShape: 'circle',
              effects: [
                {
                  on: 'hover',
                  style: {
                    itemOpacity: 0.75,
                  },
                },
              ]
            }]}
            theme={{
              axis: {
                ticks: { text: { fontSize: 10 } },
                legend: { text: { fontSize: 12 } },
              },
              legends: { text: { fontSize: 12 } },
              tooltip: { basic: { fontSize: 12 }, container: { fontSize: 12 } },
            }}
            role="img"
          />
        </div>
      </div>
    )
  }

  const renderStockList = () => {
    if (!data?.stocks) return null

    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">股票列表</h3>
        <div className="space-y-2 max-h-96 overflow-y-auto" style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'none' }}>
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
            {renderBarChart()}
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