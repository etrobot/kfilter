import { ExtendedAnalysis } from '../types'
import { StockLink } from './StockLink'

interface ExtendedAnalysisViewProps {
  extended?: ExtendedAnalysis
}

export function ExtendedAnalysisView({ extended }: ExtendedAnalysisViewProps) {
  return (
    <div className="overflow-auto border rounded max-h-[70vh] p-4 space-y-3">
      <div className="text-sm text-muted-foreground">
        基于涨停表的扩展分析：展示 top10 板块中涨停最多的个股，并做去重排行。
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-muted">
              <th className="text-left p-2 whitespace-nowrap sticky left-0 z-20 bg-muted border-r">序号</th>
              <th className="text-left p-2 whitespace-nowrap sticky left-12 z-20 bg-muted border-r">股票</th>
              <th className="text-left p-2 whitespace-nowrap">代码</th>
              <th className="text-left p-2 whitespace-nowrap">所属板块</th>
              <th className="text-right p-2 whitespace-nowrap">涨停次数</th>
            </tr>
          </thead>
          <tbody>
            {extended && Array.isArray(extended.limit_up_ranking) && extended.limit_up_ranking.length > 0 ? (
              extended.limit_up_ranking.map((item: any, idx: number) => (
                <tr key={`${item.code}-${idx}`} className="border-t">
                  <td className="p-2 sticky left-0 bg-white z-10 border-r">{idx + 1}</td>
                  <td className="p-2 sticky left-12 bg-white z-10 border-r">
                    <StockLink code={item.code} name={item.name} />
                  </td>
                  <td className="p-2 font-mono">{item.code}</td>
                  <td className="p-2">{Array.isArray(item.concept_names) && item.concept_names.length > 0 ? item.concept_names.join('、') : (item.concept_name || item.concept_code || '-')}</td>
                  <td className="p-2 text-right">{item.limit_up_count ?? 0}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="p-4 text-center text-muted-foreground">
                  暂无扩展分析数据，请点击"运行"后查看。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}