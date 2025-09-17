import { TaskMeta } from '../types'

interface PageHeaderProps {
  meta: TaskMeta | null
}

export function PageHeader({ meta }: PageHeaderProps) {
  return (
    <div>
      <h1 className="text-2xl font-bold">量化统计</h1>
      <p className="text-sm text-muted-foreground">选择因子并点击表格中的"运行"按钮启动数据分析</p>
      {meta?.created_at && (
        <p className="text-xs text-muted-foreground mt-1">
          最近运行: {new Date(meta.created_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })} — {meta?.count ?? 0} 条记录
          {meta.from_cache && (
            <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
              缓存数据
            </span>
          )}
        </p>
      )}
    </div>
  )
}