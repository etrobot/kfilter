import { ProgressBar } from './ProgressBar'
import { TaskResult } from '../types'

interface TaskProgressCardProps {
  task: TaskResult
}

export function TaskProgressCard({ task }: TaskProgressCardProps) {
  if (task.status !== 'running' && task.status !== 'pending') {
    return null
  }

  return (
    <div className="border rounded p-4">
      <h3 className="font-semibold mb-2">分析进度</h3>
      <ProgressBar progress={task.progress} message={task.message} />
    </div>
  )
}