import React, { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from 'recharts'
import { api } from '../services/api'
import { TaskProgressCard } from './TaskProgressCard'
import { TaskResult } from '../types'

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
      fill: stock.amplitude >= 0 ? '#ef4444' : '#22c55e'
    }))

    return (
      <div className="bg-white p-2 rounded-lg shadow-md">
        <h3 className="mb-4">K线实体幅度排序 (过去{nDays}天最长)</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="name" 
                angle={-45}
                textAnchor="end"
                height={60}
                fontSize={12}
              />
              <YAxis 
                label={{ value: '幅度 (%)', angle: -90, position: 'insideLeft' }}
                fontSize={12}
              />
              <Tooltip 
                formatter={(value: number, name, props) => [
                  `${value > 0 ? '+' : ''}${value.toFixed(2)}%`, 
                  '幅度'
                ]}
                labelFormatter={(label) => {
                  const item = chartData.find(d => d.name === label)
                  return item ? `${item.code} ${item.name}` : label
                }}
              />
              <Bar dataKey="amplitude" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  const renderTrendChart = () => {
    if (!data?.top_5) return null

    // 准备图表数据，将所有股票的走势数据合并
    const maxLength = Math.max(...data.top_5.map(stock => stock.trend_data?.length || 0))
    const chartData = Array.from({ length: maxLength }, (_, index) => {
      const dataPoint: any = { index: index + 1 }
      data.top_5.forEach((stock, stockIndex) => {
        if (stock.trend_data && stock.trend_data[index] !== undefined) {
          dataPoint[`${stock.code}`] = stock.trend_data[index]
        }
      })
      return dataPoint
    })

    const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6']
    
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">前五名走势叠加图</h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart 
              data={chartData} 
              margin={{ 
                top: 10, 
                right: 10, 
                left: 10, 
                bottom: 5 
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="index" 
                label={{ 
                  value: '交易日', 
                  position: 'insideBottom', 
                  offset: -5,
                  style: { fontSize: 12 }
                }}
                tick={{ fontSize: 10 }}
                height={40}
              />
              <YAxis 
                label={{ 
                  value: '涨跌幅 (%)', 
                  angle: -90, 
                  position: 'insideLeft',
                  style: { fontSize: 12 }
                }}
                tick={{ fontSize: 10 }}
                width={40}
              />
              <Tooltip 
                formatter={(value: number, name: string) => [
                  `${value > 0 ? '+' : ''}${value?.toFixed(2) || 'N/A'}%`,
                  name
                ]}
                labelFormatter={(label) => `第${label}个交易日`}
                contentStyle={{ fontSize: 12 }}
              />
              <Legend 
                layout="horizontal" 
                verticalAlign="top"
                height={40}
                wrapperStyle={{
                  paddingBottom: '10px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  fontSize: '12px'
                }}
              />
              {data.top_5.map((stock, index) => (
                <Line
                  key={stock.code}
                  type="monotone"
                  dataKey={stock.code}
                  stroke={colors[index]}
                  strokeWidth={2}
                  dot={false}
                  name={`${stock.code} ${stock.name}`}
                  connectNulls={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  const renderStockList = () => {
    if (!data?.stocks) return null

    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">股票列表</h3>
        <div className="space-y-2 max-h-96 overflow-y-auto">
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
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-900">K线幅度分析面板</h1>
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
          <div className="flex gap-4">
            <div className="flex-1">{renderTrendChart()}</div>
            <div className="flex-1">{renderStockList()}</div>
          </div>
        </div>
      )}
    </div>
  )
}