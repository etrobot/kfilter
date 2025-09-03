import { TaskMeta, TaskResult } from '../types'

interface DashboardHeaderProps {
  meta: TaskMeta | null
  currentTask: TaskResult | null
}

export function DashboardHeader({ meta, currentTask }: DashboardHeaderProps) {
  return (
    <div>
      <h1 className="text-2xl font-bold">量化统计 Dashboard</h1>
      <p className="text-sm text-muted-foreground">选择因子并点击表格中的"运行"按钮启动数据分析</p>
      {meta?.created_at && (
        <p className="text-xs text-muted-foreground mt-1">
          最近运行: {new Date(meta.created_at).toLocaleString()} — {meta?.count ?? 0} 条记录
        </p>
      )}
    </div>
  )
}