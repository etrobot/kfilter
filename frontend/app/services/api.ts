import { TaskResult, RunResponse, FactorListResponse, ConceptTaskResult, ConceptListResponse } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.PROD ? '' : 'http://localhost:8000')

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiCall<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new ApiError(response.status, `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

export const api = {
  async startAnalysis(topN: number = 100, selectedFactors?: string[], collectLatestData: boolean = true): Promise<RunResponse> {
    return apiCall<RunResponse>('/run', {
      method: 'POST',
      body: JSON.stringify({ 
        top_n: topN,
        selected_factors: selectedFactors,
        collect_latest_data: collectLatestData
      }),
    })
  },

  async getTaskStatus(taskId: string): Promise<TaskResult> {
    return apiCall<TaskResult>(`/task/${taskId}`)
  },

  async stopTask(taskId: string): Promise<TaskResult> {
    return apiCall<TaskResult>(`/task/${taskId}/stop`, { method: 'POST' })
  },


  async getLatestResults(): Promise<TaskResult> {
    return apiCall<TaskResult>('/results')
  },

  async getAllTasks(): Promise<TaskResult[]> {
    return apiCall<TaskResult[]>('/tasks')
  },

  async getFactors(): Promise<FactorListResponse> {
    return apiCall<FactorListResponse>('/factors')
  },

  // Concept APIs
  async collectConcepts(): Promise<RunResponse> {
    return apiCall<RunResponse>('/concepts/collect', {
      method: 'POST',
    })
  },

  async getConceptTaskStatus(taskId: string): Promise<ConceptTaskResult> {
    return apiCall<ConceptTaskResult>(`/concepts/task/${taskId}`)
  },

  async getLatestConceptResults(): Promise<ConceptTaskResult> {
    return apiCall<ConceptTaskResult>('/concepts/results')
  },

  async getAllConceptTasks(): Promise<ConceptTaskResult[]> {
    return apiCall<ConceptTaskResult[]>('/concepts/tasks')
  },

  async getConcepts(): Promise<ConceptListResponse> {
    return apiCall<ConceptListResponse>('/concepts')
  },

  async getDashboardData(nDays: number = 30): Promise<any> {
    return apiCall<any>(`/dashboard/kline-amplitude?n_days=${nDays}`)
  },

  async runExtendedAnalysis(): Promise<any> {
    return apiCall<any>('/extended-analysis/run', {
      method: 'POST',
    })
  },
}

export function createTaskStatusPoller(
  taskId: string,
  onUpdate: (task: TaskResult) => void,
  onComplete: (task: TaskResult) => void,
  onError: (error: string) => void
): () => void {
  const pollInterval = setInterval(async () => {
    try {
      const taskResult = await api.getTaskStatus(taskId)
      onUpdate(taskResult)

      if (taskResult.status === 'completed') {
        clearInterval(pollInterval)
        onComplete(taskResult)
      } else if (taskResult.status === 'failed') {
        clearInterval(pollInterval)
        onError(taskResult.error || '任务执行失败')
      }
    } catch (err) {
      clearInterval(pollInterval)
      onError(err instanceof Error ? err.message : 'An error occurred')
    }
  }, 1000)

  return () => clearInterval(pollInterval)
}

export function createConceptTaskStatusPoller(
  taskId: string,
  onUpdate: (task: ConceptTaskResult) => void,
  onComplete: (task: ConceptTaskResult) => void,
  onError: (error: string) => void
): () => void {
  const pollInterval = setInterval(async () => {
    try {
      const taskResult = await api.getConceptTaskStatus(taskId)
      onUpdate(taskResult)

      if (taskResult.status === 'completed') {
        clearInterval(pollInterval)
        onComplete(taskResult)
      } else if (taskResult.status === 'failed') {
        clearInterval(pollInterval)
        onError(taskResult.error || '概念数据采集失败')
      }
    } catch (err) {
      clearInterval(pollInterval)
      onError(err instanceof Error ? err.message : 'An error occurred')
    }
  }, 1000)

  return () => clearInterval(pollInterval)
}