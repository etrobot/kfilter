import { TaskResult, RunResponse } from '../types'

const API_BASE_URL = 'http://localhost:8000'

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
  async startAnalysis(topN: number = 100): Promise<RunResponse> {
    return apiCall<RunResponse>('/run', {
      method: 'POST',
      body: JSON.stringify({ top_n: topN }),
    })
  },

  async getTaskStatus(taskId: string): Promise<TaskResult> {
    return apiCall<TaskResult>(`/task/${taskId}`)
  },

  async getLatestResults(): Promise<TaskResult> {
    return apiCall<TaskResult>('/results')
  },

  async getAllTasks(): Promise<TaskResult[]> {
    return apiCall<TaskResult[]>('/tasks')
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