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
          maxRotation: 50,
          minRotation: 45,
          font: {
            size: 10,
          },
          autoSkip: false
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

  return (
    <div className="bg-white p-2 rounded-lg shadow-md">
      <h3 className="mb-4">K线实体排行 (过去{nDays}天,越短越安全)</h3>
      <div className="h-64 w-full relative">
        
        {/* 底层固定图表 - 完全一样的图表 */}
        <div className="absolute left-0 top-0 bottom-0 right-0 z-10">
          <Bar
            data={chartData}
            options={options}
          />
        </div>

        {/* 上层可滚动图表 - 完全一样的图表，向右偏移一点点 */}
        <div 
          className="absolute top-0 bottom-0 right-0 z-20 overflow-x-auto bg-white md:hidden"
          style={{
            left: '28px', // 向右偏移28px，刚好覆盖住Y轴区域
            WebkitOverflowScrolling: 'touch',
            overscrollBehavior: 'none'
          }}
        >
          <div style={{ minWidth: '1400px', height: '100%', position: 'relative' }}>
            <Bar
              data={chartData}
              options={options}
            />
            {/* CSS遮罩层，遮住上层图表的Y轴标签区域 */}
            <div 
              className="absolute top-0 bottom-0 left-0 bg-white z-10"
              style={{ width: '28px' }}
            />
          </div>
        </div>
        
      </div>
    </div>
  )
}