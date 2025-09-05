import { useState } from 'react'
import { Play, Square } from 'lucide-react'
import { FactorSelectionDialog } from './FactorSelectionDialog'
import { Button } from './ui/button'
import { FactorRecord, FactorMeta } from '../types'
import { api } from '../services/api'
import { ResultsMainView } from './ResultsMainView'
import { ExtendedAnalysisView } from './ExtendedAnalysisView'

interface ResultsTableProps {
  data: FactorRecord[]
  factorMeta?: FactorMeta[]
  extended?: any
  onRunAnalysis?: (taskId: string) => void
  onStopAnalysis?: () => void
  currentTaskId?: string
  isTaskRunning?: boolean
}

export function ResultsTable({ 
  data, 
  factorMeta = [], 
  extended, 
  onRunAnalysis, 
  onStopAnalysis, 
  currentTaskId, 
  isTaskRunning = false 
}: ResultsTableProps) {
  const [activeTab, setActiveTab] = useState<'main' | 'extended'>('main')
  const [showFactorDialog, setShowFactorDialog] = useState(false)

  const handleRunClick = () => {
    if (isTaskRunning && currentTaskId) {
      handleStopClick()
    } else {
      setShowFactorDialog(true)
    }
  }

  const handleStopClick = async () => {
    if (!currentTaskId) return
    
    try {
      await api.stopTask(currentTaskId)
      console.log('Stop request sent for task:', currentTaskId)
      // 通知父组件任务已停止
      if (onStopAnalysis) {
        onStopAnalysis()
      }
    } catch (error) {
      console.error('Failed to stop analysis:', error)
      alert('停止分析失败，请重试')
    }
  }

  const handleFactorConfirm = async (selectedFactors: string[], collectLatestData: boolean) => {
    try {
      const response = await api.startAnalysis(100, selectedFactors, collectLatestData)
      if (onRunAnalysis) {
        onRunAnalysis(response.task_id)
      }
    } catch (error) {
      console.error('Failed to start analysis:', error)
      alert('启动分析失败，请重试')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold">分析</h2>
          <div className="flex bg-muted rounded p-1 text-sm">
            <button
              className={`px-3 py-1 rounded ${activeTab === 'main' ? 'bg-white shadow' : ''}`}
              onClick={() => setActiveTab('main')}
            >
              结果
            </button>
            <button
              className={`px-3 py-1 rounded ${activeTab === 'extended' ? 'bg-white shadow' : ''}`}
              onClick={() => setActiveTab('extended')}
            >
              扩展分析
            </button>
          </div>
        </div>
        <Button 
          onClick={handleRunClick}
          disabled={false}
          className="flex items-center gap-2"
        >
          {isTaskRunning ? (
            <>
              <Square className="w-4 h-4" />
              停止
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              运行
            </>
          )}
        </Button>
      </div>

      {activeTab === 'main' ? (
        <ResultsMainView data={data} factorMeta={factorMeta} />
      ) : (
        <ExtendedAnalysisView extended={extended} />
      )}

      <FactorSelectionDialog
        open={showFactorDialog}
        onOpenChange={setShowFactorDialog}
        onConfirm={handleFactorConfirm}
      />
    </div>
  )
}
