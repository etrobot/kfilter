import { useState } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'
import { ScoreBar } from './ScoreBar'
import { StockLink } from './StockLink'
import { FactorRecord, FactorMeta, ColumnSpec } from '../types'

type SortField = string | null
type SortDirection = 'asc' | 'desc'

interface ResultsMainViewProps {
  data: FactorRecord[]
  factorMeta?: FactorMeta[]
}

export function ResultsMainView({ data, factorMeta = [] }: ResultsMainViewProps) {
  const [sortField, setSortField] = useState<SortField | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const getValue = (record: FactorRecord, key: string): any => {
    const value = (record as any)[key]
    
    switch (key) {
      case '名称':
        return record.名称 || record.代码
      case '所属板块':
        return record.所属板块 || ''
      case '当前价格':
        return record.当前价格 || record.收盘 || 0
      case '涨跌幅':
        return record.涨跌幅 || 0
      default:
        return value
    }
  }

  const getSortedData = () => {
    if (!sortField) return data

    return [...data].sort((a, b) => {
      const aValue: any = getValue(a, sortField)
      const bValue: any = getValue(b, sortField)

      // Handle undefined/null values - always push to end
      if (aValue === null || aValue === undefined || aValue === '') {
        return 1 // a goes after b
      }
      if (bValue === null || bValue === undefined || bValue === '') {
        return -1 // b goes after a
      }

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

  // Derive any missing factor columns from the actual data as a fallback
  const knownBaseKeys = new Set<string>([
    '代码', '名称', '当前价格', '收盘', '涨跌幅', '涨跌幅', '换手板', '综合评分', '所属板块'
  ])
  if (data && data.length > 0) {
    const existingKeys = new Set(factorColumns.map(c => c.key))
    const sampleKeys = Object.keys(data.reduce((acc, cur) => Object.assign(acc, cur), {} as Record<string, any>))
    sampleKeys.forEach((key) => {
      if (existingKeys.has(key) || knownBaseKeys.has(key)) return
      // Only add columns that have some data
      if (!hasDataInColumn(key)) return
      // Infer type
      const value = getValue(data[0], key)
      let type: ColumnSpec['type'] = 'string'
      if (typeof value === 'number') {
        // Heuristic: keys ending with '评分' are score bars
        type = key.endsWith('评分') ? 'score' : 'number'
      } else if (typeof value === 'string') {
        type = 'string'
      }
      factorColumns.push({ key, label: key, type, sortable: true })
    })
  }

  // Filter out columns that have no data
  const filteredFactorColumns = factorColumns.filter(col => hasDataInColumn(col.key))

  // Separate factor columns from score columns for better organization
  const factorValueColumns = filteredFactorColumns.filter(col => col.type !== 'score')
  const scoreColumns = filteredFactorColumns.filter(col => col.type === 'score')

  const renderCell = (record: FactorRecord, col: ColumnSpec) => {
    const value = getValue(record, col.key)
    
    // Special handling for "最长K线天数" - always treat as integer
    if (col.key === '最长K线天数' || col.key.startsWith('最长K线天数_')) {
      return Math.round(Number(value || 0))
    }
    
    switch (col.type) {
      case 'percent':
        return `${(Number(value || 0) * 100).toFixed(2)}%`
      case 'score':
        return <ScoreBar value={Number(value || 0)} />
      case 'integer':
        return Math.round(Number(value || 0))
      case 'number':
        return Number(value || 0).toFixed(2)
      default:
        return String(value ?? '')
    }
  }

  return (
    <div className="overflow-auto border rounded max-h-[70vh]" style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'none' }}>
      <table className="min-w-full text-sm">
        <thead className="sticky top-0 z-30">
          <tr className="bg-muted">
            <th className="text-center p-2 bg-muted sticky left-0 z-30 border-r whitespace-nowrap">序号</th>
            <th className={getColumnClassName('名称', "text-left p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted sticky left-[40px] z-30 border-r whitespace-nowrap")} onClick={() => handleSort('名称')}>
              股票{renderSortIcon('名称')}
            </th>
            <th className={getColumnClassName('所属板块', "text-left p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted whitespace-nowrap")} onClick={() => handleSort('所属板块')}>
              所属板块{renderSortIcon('所属板块')}
            </th>
            <th className={getColumnClassName('当前价格', "text-right p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted whitespace-nowrap")} onClick={() => handleSort('当前价格')}>
              当前价格{renderSortIcon('当前价格')}
            </th>
            <th className={getColumnClassName('涨跌幅', "text-right p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted whitespace-nowrap")} onClick={() => handleSort('涨跌幅')}>
              涨跌幅{renderSortIcon('涨跌幅')}
            </th>
            {/* Dynamic factor value columns */}
            {factorValueColumns.map((col) => (
              <th
                key={col.key}
                className={getColumnClassName(col.key, `text-right p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted whitespace-nowrap`)}
                onClick={() => col.sortable !== false ? handleSort(col.key) : undefined}
              >
                {col.label}{col.sortable !== false ? renderSortIcon(col.key) : null}
              </th>
            ))}
            <th className={getColumnClassName('换手板', "text-right p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted whitespace-nowrap")} onClick={() => handleSort('换手板')}>
              换手板{renderSortIcon('换手板')}
            </th>
            {/* Dynamic score columns */}
            {scoreColumns.map((col) => (
              <th
                key={col.key}
                className={getColumnClassName(col.key, `text-left p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted whitespace-nowrap w-32`)}
                onClick={() => col.sortable !== false ? handleSort(col.key) : undefined}
              >
                {col.label}{col.sortable !== false ? renderSortIcon(col.key) : null}
              </th>
            ))}
            <th className={getColumnClassName('综合评分', "text-left p-2 cursor-pointer hover:bg-gray-100 select-none bg-muted whitespace-nowrap w-32")} onClick={() => handleSort('综合评分')}>
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
                <td className="p-2 text-center text-gray-500 font-mono sticky left-0 bg-white z-20 border-r">{index + 1}</td>
                <td className={getColumnClassName('名称', "p-2 sticky left-[40px] bg-white z-20 border-r")}>
                  <StockLink code={record.代码} name={record.名称} />
                </td>
                <td className={getColumnClassName('所属板块', "p-2")}>
                  {record.所属板块 || '-'}
                </td>
                <td className={getColumnClassName('当前价格', "p-2 text-right")}>{currentPrice.toFixed(2)}</td>
                <td className={getColumnClassName('涨跌幅', `p-2 text-right ${changePct >= 0 ? 'text-red-500' : 'text-green-500'}`)}>
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
                  <td key={col.key} className={getColumnClassName(col.key, "p-2 w-32")}>
                    {renderCell(record, col)}
                  </td>
                ))}
                <td className={getColumnClassName('综合评分', "p-2 w-32")}><ScoreBar value={compositeScore} color="bg-purple-500" /></td>
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
  )
}
