import { useState } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown, Play } from 'lucide-react'
import { ScoreBar } from './ScoreBar'
import { FactorSelectionDialog } from './FactorSelectionDialog'
import { Button } from './ui/button'
import { FactorRecord, FactorMeta, ColumnSpec } from '../types'
import { api } from '../services/api'

type SortField = string | null
type SortDirection = 'asc' | 'desc'

interface ResultsTableProps {
  data: FactorRecord[]
  factorMeta?: FactorMeta[]
  onRunAnalysis?: (taskId: string) => void
}

export function ResultsTable({ data, factorMeta = [], onRunAnalysis }: ResultsTableProps) {
  const [sortField, setSortField] = useState<SortField | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [showFactorDialog, setShowFactorDialog] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  
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

  const getValue = (record: FactorRecord, key: string): any => {
    switch (key) {
      case '名称':
        return record.名称 || record.代码
      case '当前价格':
        return record.当前价格 || record.收盘 || 0
      case '区间涨跌幅':
        return record.涨跌幅 || 0
      default:
        return (record as any)[key]
    }
  }

  const getSortedData = () => {
    if (!sortField) return data

    return [...data].sort((a, b) => {
      const aValue: any = getValue(a, sortField)
      const bValue: any = getValue(b, sortField)

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue, 'zh-CN')
          : bValue.localeCompare(aValue, 'zh-CN')
      }

      return sortDirection === 'asc' ? (Number(aValue) - Number(bValue)) : (Number(bValue) - Number(aValue))
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

  // Helper function to check if a column has any non-empty values in the data
  const hasDataInColumn = (columnKey: string): boolean => {
    if (data.length === 0) return false
    return data.some(record => {
      const value = getValue(record, columnKey)
      // Check for meaningful values - 0 is a valid value for factors
      if (value === null || value === undefined) return false
      if (typeof value === 'string' && value.trim() === '') return false
      if (typeof value === 'number' && isNaN(value)) return false
      return true
    })
  }

  // Build dynamic factor columns from metadata
  const factorColumns: ColumnSpec[] = []
  factorMeta.forEach(f => {
    (f.columns || []).forEach(c => {
      if (!factorColumns.find(x => x.key === c.key)) {
        factorColumns.push(c)
      }
    })
  })

  // Filter out columns that have no data
  const filteredFactorColumns = factorColumns.filter(col => hasDataInColumn(col.key))

  // Separate factor columns from score columns for better organization
  const factorValueColumns = filteredFactorColumns.filter(col => col.type !== 'score')
  const scoreColumns = filteredFactorColumns.filter(col => col.type === 'score')

  const handleRunClick = () => {
    setShowFactorDialog(true)
  }

  const handleFactorConfirm = async (selectedFactors: string[]) => {
    try {
      setIsRunning(true)
      const response = await api.startAnalysis(100, selectedFactors)
      if (onRunAnalysis) {
        onRunAnalysis(response.task_id)
      }
    } catch (error) {
      console.error('Failed to start analysis:', error)
      alert('启动分析失败，请重试')
    } finally {
      setIsRunning(false)
    }
  }

  const renderCell = (record: FactorRecord, col: ColumnSpec) => {
    const value = getValue(record, col.key)
    switch (col.type) {
      case 'percent':
        return `${(Number(value || 0) * 100).toFixed(2)}%`
      case 'score':
        return <ScoreBar value={Number(value || 0)} />
      case 'integer':
        return Number(value || 0)
      case 'number':
        return Number(value || 0).toFixed(2)
      default:
        return String(value ?? '')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">分析结果</h2>
        <Button 
          onClick={handleRunClick}
          disabled={isRunning}
          className="flex items-center gap-2"
        >
          <Play className="w-4 h-4" />
          {isRunning ? '运行中...' : '运行'}
        </Button>
      </div>
      
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
              {/* Dynamic factor value columns */}
              {factorValueColumns.map((col) => (
                <th
                  key={col.key}
                  className={getColumnClassName(col.key, `text-right p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted`)}
                  onClick={() => col.sortable !== false ? handleSort(col.key) : undefined}
                >
                  {col.label}{col.sortable !== false ? renderSortIcon(col.key) : null}
                </th>
              ))}
              <th className={getColumnClassName('换手板', "text-right p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted")} onClick={() => handleSort('换手板')}>
                换手板{renderSortIcon('换手板')}
              </th>
              {/* Dynamic score columns */}
              {scoreColumns.map((col) => (
                <th
                  key={col.key}
                  className={getColumnClassName(col.key, `text-left p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted`)}
                  onClick={() => col.sortable !== false ? handleSort(col.key) : undefined}
                >
                  {col.label}{col.sortable !== false ? renderSortIcon(col.key) : null}
                </th>
              ))}
              <th className={getColumnClassName('综合评分', "text-left p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted")} onClick={() => handleSort('综合评分')}>
                综合评分{renderSortIcon('综合评分')}
              </th>
            </tr>
          </thead>
          <tbody>
            {getSortedData().map((record, index) => {
              const currentPrice = record.当前价格 || record.收盘 || 0
              const changePct = record.涨跌幅 || 0
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
                  {/* Dynamic factor value columns */}
                  {factorValueColumns.map((col) => (
                    <td key={col.key} className={getColumnClassName(col.key, "p-2 text-right")}>
                      {renderCell(record, col)}
                    </td>
                  ))}
                  <td className={getColumnClassName('换手板', "p-2 text-right")}>{hsCount}</td>
                  {/* Dynamic score columns */}
                  {scoreColumns.map((col) => (
                    <td key={col.key} className={getColumnClassName(col.key, "p-2")}>
                      {renderCell(record, col)}
                    </td>
                  ))}
                  <td className={getColumnClassName('综合评分', "p-2")}><ScoreBar value={compositeScore} color="bg-purple-500" /></td>
                </tr>
              )
            })}
            {data.length === 0 && (
              <tr>
                <td className="p-4 text-center text-muted-foreground" colSpan={6 + filteredFactorColumns.length}>暂无数据，请点击"运行"</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      <FactorSelectionDialog
        open={showFactorDialog}
        onOpenChange={setShowFactorDialog}
        onConfirm={handleFactorConfirm}
      />
    </div>
  )
}