import React, { useState, useEffect, useRef } from 'react'
import ReactDOM from 'react-dom/client'
import { BarChart3, Lightbulb, TrendingUp } from 'lucide-react'
import { PageHeader } from './components/PageHeader'
import { TaskProgressCard } from './components/TaskProgressCard'
import { ResultsTable } from './components/ResultsTable'
import { ConceptsPage } from './components/ConceptsPage'
import { DashboardPage } from './components/DashboardPage'
import { MobileNavigation } from './components/MobileNavigation'
import { api, createTaskStatusPoller } from './services/api'
import { publish, EVENTS } from './services/eventBus'
import { FactorRecord, TaskResult, TaskMeta, FactorMeta } from './types'
import { useIsMobile } from './hooks/use-mobile'
import './index.css'

type Page = 'ranking' | 'concepts' | 'dashboard'

function App() {
  const pollerCleanupRef = useRef<(() => void) | null>(null)
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')
  const [results, setResults] = useState<FactorRecord[]>([])
  const [currentTask, setCurrentTask] = useState<TaskResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [meta, setMeta] = useState<TaskMeta | null>(null)
  const [factorMeta, setFactorMeta] = useState<FactorMeta[]>([])
  const [extended, setExtended] = useState<any>(null)
  const isMobile = useIsMobile()

  const handleStopAnalysis = () => {
    if (pollerCleanupRef.current) {
      try { 
        pollerCleanupRef.current() 
        pollerCleanupRef.current = null
        setCurrentTask(null)
      } catch (e) {
        console.error('Error stopping analysis:', e)
      }
    }
  }

  const handleRunAnalysis = async (taskId: string) => {
    setError(null)
    // stop any existing poller
    if (pollerCleanupRef.current) {
      try { pollerCleanupRef.current() } catch {}
      pollerCleanupRef.current = null
    }
    
    // Start polling for the new task status
    const cleanup = createTaskStatusPoller(
      taskId,
      (task) => setCurrentTask(task),
      (task) => {
        setResults(task.data || [])
        setMeta({ 
          task_id: task.task_id, 
          created_at: task.created_at, 
          count: task.count 
        })
        setExtended((task as any).extended || null)
        setCurrentTask(null)
        // Notify dashboard to refresh
        try { publish(EVENTS.ANALYSIS_COMPLETED, { taskId: task.task_id }) } catch {}
      },
      (errorMsg) => {
        setError(errorMsg)
        setCurrentTask(null)
      }
    )
    pollerCleanupRef.current = cleanup
  }

  useEffect(() => {
    let cancelled = false

    const init = async () => {
      // 0) Load factor metadata first
      try {
        const res = await api.getFactors()
        if (!cancelled && res && Array.isArray(res.items)) {
          setFactorMeta(res.items)
        }
      } catch {
        // ignore
      }

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
          setExtended((result as any).extended || null)
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
                setExtended((task as any).extended || null)
                setCurrentTask(null)
                // Notify dashboard to refresh
                try { publish(EVENTS.ANALYSIS_COMPLETED, { taskId: task.task_id }) } catch {}
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
    <div className="min-h-screen bg-gray-50 flex w-full">
      {/* Desktop Sidebar - hidden on mobile */}
      {!isMobile && (
        <nav className="bg-white shadow-md w-20 flex flex-col">
          <div className="flex flex-col space-y-4 p-4">
            <button
              onClick={() => setCurrentPage('dashboard')}
              className={`flex flex-col items-center justify-center p-3 rounded-lg transition-colors ${
                currentPage === 'dashboard'
                  ? 'bg-indigo-100 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <TrendingUp size={24} />
              <span className="text-xs mt-1">面板</span>
            </button>
            <button
              onClick={() => setCurrentPage('ranking')}
              className={`flex flex-col items-center justify-center p-3 rounded-lg transition-colors ${
                currentPage === 'ranking'
                  ? 'bg-indigo-100 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <BarChart3 size={24} />
              <span className="text-xs mt-1">分析</span>
            </button>
            <button
              onClick={() => setCurrentPage('concepts')}
              className={`flex flex-col items-center justify-center p-3 rounded-lg transition-colors ${
                currentPage === 'concepts'
                  ? 'bg-indigo-100 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Lightbulb size={24} />
              <span className="text-xs mt-1">概念</span>
            </button>
          </div>
        </nav>
      )}

      {/* Main Content */}
      <div className={`flex-1 ${isMobile ? 'pb-16' : ''} w-full`}>
        {currentPage === 'ranking' ? (
          <div className="p-8 space-y-6">
            <PageHeader 
              meta={meta} 
              currentTask={currentTask} 
            />

            {currentTask && <TaskProgressCard task={currentTask} />}

            {error && (
              <div className="text-red-500">错误: {error}</div>
            )}

            <ResultsTable 
              data={results} 
              factorMeta={factorMeta} 
              extended={extended}
              onRunAnalysis={handleRunAnalysis}
              onStopAnalysis={handleStopAnalysis}
              currentTaskId={currentTask?.task_id}
              isTaskRunning={currentTask?.status === 'running' || currentTask?.status === 'pending'}
            />
          </div>
        ) : currentPage === 'concepts' ? (
          <ConceptsPage />
        ) : (
          <DashboardPage 
            currentTask={currentTask}
          />
        )}
      </div>

      {/* Mobile Navigation */}
      {isMobile && (
        <MobileNavigation 
          currentPage={currentPage} 
          setCurrentPage={setCurrentPage} 
        />
      )}
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
