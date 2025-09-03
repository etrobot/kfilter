import { ScoreBar } from './ScoreBar'
import { FactorRecord } from '../types'

interface TopScoresListProps {
  title: string
  data: FactorRecord[]
  getScore: (record: FactorRecord) => number
  color: string
}

export function TopScoresList({ title, data, getScore, color }: TopScoresListProps) {
  const sortedData = data
    .slice()
    .sort((a, b) => getScore(b) - getScore(a))
    .slice(0, 10)

  const getXueqiuUrl = (stockCode: string) => {
    const code = stockCode.replace(/\D/g, '')
    let fullCode = ''
    if (code.startsWith('6')) {
      fullCode = `SH${code}`
    } else if (code.startsWith('8')) {
      fullCode = `BJ${code}`
    } else if (code.startsWith('0') || code.startsWith('3')) {
      fullCode = `SZ${code}`
    } else {
      fullCode = `SH${code}`
    }
    return `https://xueqiu.com/S/${fullCode}`
  }

  const getFullStockCode = (stockCode: string) => {
    const code = stockCode.replace(/\D/g, '')
    if (code.startsWith('6')) {
      return `SH${code}`
    } else if (code.startsWith('8')) {
      return `BJ${code}`
    } else if (code.startsWith('0') || code.startsWith('3')) {
      return `SZ${code}`
    } else {
      return `SH${code}`
    }
  }

  const handleStockClick = (stockCode: string) => {
    const url = getXueqiuUrl(stockCode)
    window.open(url, '_blank')
  }

  return (
    <div className="border rounded p-4">
      <h2 className="font-semibold mb-3">{title}</h2>
      <div className="space-y-2">
        {sortedData.map((record) => {
          const score = getScore(record)
          return (
            <div key={record.代码} className="flex items-center justify-between gap-2">
              <button 
                onClick={() => handleStockClick(record.代码)}
                className="w-28 text-left hover:text-blue-600 hover:underline cursor-pointer"
              >
                <div className="truncate text-sm font-medium">{record.名称 || record.代码}</div>
                <div className="truncate text-xs text-muted-foreground font-mono">{getFullStockCode(record.代码)}</div>
              </button>
              <ScoreBar value={score} color={color} />
              <span className="w-14 text-right text-sm">{(score * 100).toFixed(0)}%</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}