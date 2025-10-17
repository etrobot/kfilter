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
  console.log(`API Call: ${options?.method || 'GET'} ${endpoint}`)
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })
  console.log(`API Response: ${response.status} ${endpoint}`)

  if (!response.ok) {
    let errorMessage = `HTTP error! status: ${response.status}`
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorData.message || errorMessage
    } catch {
      // Ignore JSON parse errors
    }
    throw new ApiError(response.status, errorMessage)
  }

  const data = await response.json()
  console.log(`API Data:`, data)
  return data
}

export const api = {
  async startAnalysis(topN: number = 200, selectedFactors?: string[], collectLatestData: boolean = true): Promise<RunResponse> {
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

  async getRandomStocks(nDays: number = 30): Promise<any> {
    return apiCall<any>(`/dashboard/random-stocks?n_days=${nDays}`)
  },

  async runExtendedAnalysis(): Promise<any> {
    return apiCall<any>('/extended-analysis/run', {
      method: 'POST',
    })
  },

  createExtendedAnalysisStream(onEvent: (type: string, payload: any) => void): () => void {
    const url = `${API_BASE_URL}/extended-analysis/stream`
    const es = new EventSource(url)

    es.addEventListener('start', (e: MessageEvent) => {
      try { onEvent('start', JSON.parse(e.data)) } catch { onEvent('start', {}) }
    })
    es.addEventListener('progress', (e: MessageEvent) => {
      try { onEvent('progress', JSON.parse(e.data)) } catch { onEvent('progress', {}) }
    })
    es.addEventListener('complete', (e: MessageEvent) => {
      try { onEvent('complete', JSON.parse(e.data)) } catch { onEvent('complete', {}) }
      es.close()
    })
    es.addEventListener('error', (e: MessageEvent) => {
      try { onEvent('error', JSON.parse((e as any).data)) } catch { onEvent('error', {message: 'Stream error'}) }
      es.close()
    })

    return () => es.close()
  },

  async getExtendedAnalysisResults(): Promise<any> {
    return apiCall<any>('/extended-analysis/results')
  },

  async clearExtendedAnalysisCache(): Promise<any> {
    return apiCall<any>('/extended-analysis/cache', {
      method: 'DELETE',
    })
  },

  async getExtendedAnalysisTaskStatus(taskId: string): Promise<any> {
    return apiCall<any>(`/extended-analysis/${taskId}/status`)
  },

  async getRunningExtendedAnalysisStatus(): Promise<any> {
    return apiCall<any>('/extended-analysis/status')
  },

  async stopExtendedAnalysisTask(taskId: string): Promise<any> {
    return apiCall<any>(`/extended-analysis/${taskId}/stop`, {
      method: 'POST',
    })
  },

  // Config APIs
  async getZaiConfig(): Promise<{
    configured: boolean
    OPENAI_BASE_URL: string
    OPENAI_MODEL: string
    zai_configured: boolean
    openai_configured: boolean
  }> {
    return apiCall('/config/zai')
  },

  async updateZaiConfig(payload: { ZAI_BEARER_TOKEN: string; ZAI_USER_ID: string; OPENAI_API_KEY: string; OPENAI_BASE_URL: string; OPENAI_MODEL: string; }): Promise<{ success: boolean; message: string }>{
    return apiCall('/config/zai', {
      method: 'POST',
      body: JSON.stringify(payload),
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