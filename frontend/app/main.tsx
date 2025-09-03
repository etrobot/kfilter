import React, { useState, useEffect, useRef } from 'react'
import ReactDOM from 'react-dom/client'
import { DashboardHeader } from './components/DashboardHeader'
import { TaskProgressCard } from './components/TaskProgressCard'
import { ResultsTable } from './components/ResultsTable'
import { api, createTaskStatusPoller } from './services/api'
import { FactorRecord, TaskResult, TaskMeta } from './types'
import './index.css'

function App() {
  const pollerCleanupRef = useRef<(() => void) | null>(null)
  const [results, setResults] = useState<FactorRecord[]>([])
  const [currentTask, setCurrentTask] = useState<TaskResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [meta, setMeta] = useState<TaskMeta | null>(null)

  const runCalculation = async () => {
    setError(null)
    setCurrentTask(null)
    // stop any existing poller
    if (pollerCleanupRef.current) {
      try { pollerCleanupRef.current() } catch {}
      pollerCleanupRef.current = null
    }
    try {
      const response = await api.startAnalysis()
      
      // Start polling for task status
      const cleanup = createTaskStatusPoller(
        response.task_id,
        (task) => setCurrentTask(task),
        (task) => {
          setResults(task.data || [])
          setMeta({ 
            task_id: task.task_id, 
            created_at: task.created_at, 
            count: task.count 
          })
          setCurrentTask(null)
        },
        (errorMsg) => {
          setError(errorMsg)
          setCurrentTask(null)
        }
      )
      pollerCleanupRef.current = cleanup
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  useEffect(() => {
    let cancelled = false

    const init = async () => {
      // 1) Load last results for display
      try {
        const result: any = await api.getLatestResults()
        if (!cancelled && result && result.data) {
          setResults(result.data)
          setMeta({
            task_id: result.task_id,
            created_at: result.created_at,
            count: result.count,
          })
        }
      } catch {
        // Ignore errors when loading last results
      }

      // 2) Proactively check active tasks on page load and start polling
      try {
        const tasks = await api.getAllTasks()
        if (!cancelled && Array.isArray(tasks) && tasks.length > 0) {
          const active = tasks
            .filter(t => t.status === 'running' || t.status === 'pending')
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          if (active.length > 0) {
            const latest = active[0]
            setCurrentTask(latest)

            // stop any existing poller first
            if (pollerCleanupRef.current) {
              try { pollerCleanupRef.current() } catch {}
              pollerCleanupRef.current = null
            }

            const cleanup = createTaskStatusPoller(
              latest.task_id,
              (task) => setCurrentTask(task),
              (task) => {
                setResults(task.data || [])
                setMeta({
                  task_id: task.task_id,
                  created_at: task.created_at,
                  count: task.count,
                })
                setCurrentTask(null)
              },
              (errorMsg) => {
                setError(errorMsg)
                setCurrentTask(null)
              }
            )
            pollerCleanupRef.current = cleanup
          }
        }
      } catch {
        // Ignore errors when checking tasks
      }
    }

    init()

    return () => {
      cancelled = true
      if (pollerCleanupRef.current) {
        try { pollerCleanupRef.current() } catch {}
        pollerCleanupRef.current = null
      }
    }
  }, [])

  return (
    <div className="p-8 space-y-6">
      <DashboardHeader 
        meta={meta} 
        currentTask={currentTask} 
        onRunCalculation={runCalculation} 
      />

      {currentTask && <TaskProgressCard task={currentTask} />}

      {error && (
        <div className="text-red-500">错误: {error}</div>
      )}

      <ResultsTable data={results} />
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
