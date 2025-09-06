import { ExtendedAnalysis } from '../types'
import { StockLink } from './StockLink'

interface ExtendedAnalysisViewProps {
  extended?: ExtendedAnalysis
}

export function ExtendedAnalysisView({ extended }: ExtendedAnalysisViewProps) {
  return (
    <div className="overflow-auto border rounded max-h-[70vh] p-4 space-y-3">
      {extended && Array.isArray(extended.limit_up_ranking) && extended.limit_up_ranking.length > 0 ? (
        <>
          <div className="text-sm text-muted-foreground">
            基于涨停表的扩展分析：展示 top10 板块中涨停最多的个股，并做去重排行。
          </div>
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-muted">
                <th className="text-left p-2">序号</th>
                <th className="text-left p-2">股票</th>
                <th className="text-left p-2">代码</th>
                <th className="text-left p-2">所属板块</th>
                <th className="text-right p-2">涨停次数</th>
              </tr>
            </thead>
            <tbody>
              {extended.limit_up_ranking.map((item: any, idx: number) => (
                <tr key={`${item.code}-${idx}`} className="border-t">
                  <td className="p-2">{idx + 1}</td>
                  <td className="p-2">
                    <StockLink code={item.code} name={item.name} />
                  </td>
                  <td className="p-2 font-mono">{item.code}</td>
                  <td className="p-2">{Array.isArray(item.concept_names) && item.concept_names.length > 0 ? item.concept_names.join('、') : (item.concept_name || item.concept_code || '-')}</td>
                  <td className="p-2 text-right">{item.limit_up_count ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <div className="text-muted-foreground text-sm">暂无扩展分析数据，请点击“运行”后查看。</div>
      )}
    </div>
  )
}
