import { useState } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'
import { ScoreBar } from './ScoreBar'
import { FactorRecord } from '../types'

type SortField = '名称' | '当前价格' | '区间涨跌幅' | '动量因子' | '支撑因子' | '换手板' | '动量评分' | '支撑评分' | '综合评分'
type SortDirection = 'asc' | 'desc'

interface ResultsTableProps {
  data: FactorRecord[]
}

export function ResultsTable({ data }: ResultsTableProps) {
  const [sortField, setSortField] = useState<SortField | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  
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

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const getSortedData = () => {
    if (!sortField) return data

    return [...data].sort((a, b) => {
      let aValue: any
      let bValue: any

      switch (sortField) {
        case '名称':
          aValue = a.名称 || a.代码
          bValue = b.名称 || b.代码
          break
        case '当前价格':
          aValue = a.当前价格 || a.收盘 || 0
          bValue = b.当前价格 || b.收盘 || 0
          break
        case '区间涨跌幅':
          aValue = a.涨跌幅 || 0
          bValue = b.涨跌幅 || 0
          break
        case '动量因子':
          aValue = a.动量因子 || a.动量 || 0
          bValue = b.动量因子 || b.动量 || 0
          break
        case '支撑因子':
          aValue = a.支撑因子 || a.支撑位 || 0
          bValue = b.支撑因子 || b.支撑位 || 0
          break
        case '换手板':
          aValue = a.换手板 || 0
          bValue = b.换手板 || 0
          break
        case '动量评分':
          aValue = a.动量评分 || 0
          bValue = b.动量评分 || 0
          break
        case '支撑评分':
          aValue = a.支撑位评分 || a.支撑评分 || 0
          bValue = b.支撑位评分 || b.支撑评分 || 0
          break
        case '综合评分':
          aValue = a.综合评分 || 0
          bValue = b.综合评分 || 0
          break
        default:
          return 0
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue, 'zh-CN')
          : bValue.localeCompare(aValue, 'zh-CN')
      }

      return sortDirection === 'asc' ? aValue - bValue : bValue - aValue
    })
  }

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ChevronsUpDown className="w-4 h-4 text-gray-400 ml-1 inline" />
    }
    return sortDirection === 'asc' ? (
      <ChevronUp className="w-4 h-4 ml-1 inline" />
    ) : (
      <ChevronDown className="w-4 h-4 ml-1 inline" />
    )
  }

  const getColumnClassName = (field: SortField, baseClassName: string) => {
    const isActive = sortField === field
    return `${baseClassName} ${isActive ? 'bg-gray-50' : ''}`
  }

  return (
      <div className="overflow-auto border rounded max-h-[70vh]">
        <table className="min-w-full text-sm">
          <thead className="sticky top-0 z-10">
            <tr className="bg-muted">
              <th className="text-center p-2 w-16 bg-muted">序号</th>
              <th className={getColumnClassName('名称', "text-left p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted")} onClick={() => handleSort('名称')}>
                股票{renderSortIcon('名称')}
              </th>
              <th className={getColumnClassName('当前价格', "text-right p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted")} onClick={() => handleSort('当前价格')}>
                当前价格{renderSortIcon('当前价格')}
              </th>
              <th className={getColumnClassName('区间涨跌幅', "text-right p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted")} onClick={() => handleSort('区间涨跌幅')}>
                区间涨跌幅{renderSortIcon('区间涨跌幅')}
              </th>
              <th className={getColumnClassName('动量因子', "text-right p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted")} onClick={() => handleSort('动量因子')}>
                动量因子{renderSortIcon('动量因子')}
              </th>
              <th className={getColumnClassName('支撑因子', "text-right p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted")} onClick={() => handleSort('支撑因子')}>
                支撑因子{renderSortIcon('支撑因子')}
              </th>
              <th className={getColumnClassName('换手板', "text-right p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted")} onClick={() => handleSort('换手板')}>
                换手板{renderSortIcon('换手板')}
              </th>
              <th className={getColumnClassName('动量评分', "text-left p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted")} onClick={() => handleSort('动量评分')}>
                动量评分{renderSortIcon('动量评分')}
              </th>
              <th className={getColumnClassName('支撑评分', "text-left p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted")} onClick={() => handleSort('支撑评分')}>
                支撑评分{renderSortIcon('支撑评分')}
              </th>
              <th className={getColumnClassName('综合评分', "text-left p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted")} onClick={() => handleSort('综合评分')}>
                综合评分{renderSortIcon('综合评分')}
              </th>
            </tr>
          </thead>
          <tbody>
            {getSortedData().map((record, index) => {
              const currentPrice = record.当前价格 || record.收盘 || 0
              const changePct = record.涨跌幅 || 0
              const momentum = record.动量因子 || record.动量 || 0
              const support = record.支撑因子 || record.支撑位 || 0
              const momentumScore = record.动量评分 || 0
              const supportScore = record.支撑位评分 || record.支撑评分 || 0
              const compositeScore = record.综合评分 || 0
              const hsCount = record.换手板 || 0
              
              return (
                <tr key={record.代码} className="border-t">
                  <td className="p-2 text-center text-gray-500 font-mono">{index + 1}</td>
                  <td className={getColumnClassName('名称', "p-2 cursor-pointer hover:text-blue-600 hover:underline")} onClick={() => handleStockClick(record.代码)}>
                    <div>
                      <div className="font-medium">{record.名称 || record.代码}</div>
                      <div className="text-xs text-muted-foreground font-mono">{getFullStockCode(record.代码)}</div>
                    </div>
                  </td>
                  <td className={getColumnClassName('当前价格', "p-2 text-right")}>{currentPrice.toFixed(2)}</td>
                  <td className={getColumnClassName('区间涨跌幅', `p-2 text-right ${changePct >= 0 ? 'text-red-500' : 'text-green-500'}`)}>
                    {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
                  </td>
                  <td className={getColumnClassName('动量因子', "p-2 text-right")}>{(momentum * 100).toFixed(2)}%</td>
                  <td className={getColumnClassName('支撑因子', "p-2 text-right")}>{(support * 100).toFixed(2)}%</td>
                  <td className={getColumnClassName('换手板', "p-2 text-right")}>{hsCount}</td>
                  <td className={getColumnClassName('动量评分', "p-2")}><ScoreBar value={momentumScore} color="bg-emerald-500" /></td>
                  <td className={getColumnClassName('支撑评分', "p-2")}><ScoreBar value={supportScore} color="bg-blue-500" /></td>
                  <td className={getColumnClassName('综合评分', "p-2")}><ScoreBar value={compositeScore} color="bg-purple-500" /></td>
                </tr>
              )
            })}
            {data.length === 0 && (
              <tr>
                <td className="p-4 text-center text-muted-foreground" colSpan={10}>暂无数据，请点击"运行"</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
  )
}