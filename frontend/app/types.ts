export type FactorRecord = {
  代码: string
  名称?: string
  当前价格?: number
  收盘?: number
  支撑位?: number
  支撑因子?: number
  动量?: number
  动量因子?: number
  支撑位评分?: number
  动量评分?: number
  支撑评分?: number
  综合评分?: number
  涨跌幅?: number
  换手板?: number
  [key: string]: any
}

export type ColumnSpec = {
  key: string
  label: string
  type: 'number' | 'integer' | 'percent' | 'string' | 'score'
  description?: string
  sortable?: boolean
}

export type FactorMeta = {
  id: string
  name: string
  description?: string
  columns: ColumnSpec[]
}

export type FactorListResponse = { items: FactorMeta[] }

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed'

export type TaskResult = {
  task_id: string
  status: TaskStatus
  progress: number
  message: string
  created_at: string
  completed_at?: string
  top_n: number
  data?: FactorRecord[]
  count?: number
  error?: string
}

export type RunResponse = {
  task_id: string
  status: TaskStatus
  message: string
}

export type TaskMeta = {
  task_id?: string
  created_at?: string
  count?: number
}