import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { KLineData } from '../types'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

interface BarChartProps {
  stocks: KLineData[]
  nDays: number
}

export function BarChart({ stocks, nDays }: BarChartProps) {
  if (!stocks) return null

  const chartData = {
    labels: stocks.map(stock => stock.name),
    datasets: [
      {
        label: '幅度',
        data: stocks.map(stock => stock.amplitude),
        backgroundColor: stocks.map(stock => 
          stock.amplitude >= 0 ? '#ef4444' : '#22c55e'
        ),
        borderColor: stocks.map(stock => 
          stock.amplitude >= 0 ? '#dc2626' : '#16a34a'
        ),
        borderWidth: 1,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          title: (context: any) => context[0].label,
          label: (context: any) => {
            const value = context.parsed.y
            return `幅度: ${value > 0 ? '+' : ''}${value.toFixed(2)}%`
          },
        },
      },
    },
    scales: {
      x: {
        ticks: {
          maxRotation: 45,
          minRotation: 45,
          font: {
            size: 10,
          },
        },
        grid: {
          display: false,
        },
      },
      y: {
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
  }

  // 创建两个相同的图表，一个用于固定Y轴，一个用于滚动
  return (
    <div className="bg-white p-2 rounded-lg shadow-md">
      <h3 className="mb-4">K线实体排行 (过去{nDays}天,越短越安全)</h3>
      <div className="h-64 w-full relative">
        {/* 主容器 */}
        <div className="h-full w-full relative">
          {/* 固定Y轴部分 */}
          {/* <div className="absolute left-0 top-0 bottom-0 z-10 bg-white" style={{ width: '60px' }}>
            <div style={{ width: '60px', height: '100%' }}>
              <Bar 
                data={chartData} 
                options={{
                  ...options,
                  responsive: true,
                  maintainAspectRatio: false,
                  // 禁用X轴标签和网格线
                  scales: {
                    ...options.scales,
                    x: {
                      display: false,
                      grid: {
                        display: false
                      }
                    }
                  }
                }} 
              />
            </div>
          </div> */}
          
          {/* 可滚动内容部分 */}
          <div 
            className="absolute left-0 right-0 top-0 bottom-0 overflow-x-auto" 
            style={{ 
              WebkitOverflowScrolling: 'touch', 
              overscrollBehavior: 'none'
            }}
          >
            <div style={{ minWidth: '1200px', height: '100%' }}>
              <Bar 
                data={chartData} 
                options={{
                  ...options,
                  responsive: true,
                  maintainAspectRatio: false
                }} 
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}