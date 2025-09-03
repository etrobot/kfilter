import { Button } from '@/components/ui/button'
import { TaskMeta, TaskResult } from '../types'

interface DashboardHeaderProps {
  meta: TaskMeta | null
  currentTask: TaskResult | null
  onRunCalculation: () => void
}

export function DashboardHeader({ meta, currentTask, onRunCalculation }: DashboardHeaderProps) {
  const isRunning = currentTask?.status === 'running' || currentTask?.status === 'pending'
  
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold">量化统计 Dashboard</h1>
        <p className="text-sm text-muted-foreground">点击"运行"启动后台数据抓取和计算</p>
        {meta?.created_at && (
          <p className="text-xs text-muted-foreground mt-1">
            最近运行: {new Date(meta.created_at).toLocaleString()} — {meta?.count ?? 0} 条记录
          </p>
        )}
      </div>
      <Button onClick={onRunCalculation} disabled={isRunning}>
        {isRunning ? '运行中...' : '运行'}
      </Button>
    </div>
  )
}