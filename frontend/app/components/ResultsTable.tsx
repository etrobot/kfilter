import { useState } from 'react'
import { Play, Square } from 'lucide-react'
import { FactorSelectionDialog } from './FactorSelectionDialog'
import { AuthDialog } from './AuthDialog'
import { Button } from './ui/button'
import { FactorRecord, FactorMeta } from '../types'
import { api } from '../services/api'
import { AuthService } from '../services/auth'
import { ResultsMainView } from './ResultsMainView'

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
  const [showFactorDialog, setShowFactorDialog] = useState(false)
  const [showAuthDialog, setShowAuthDialog] = useState(false)

  const handleRunClick = () => {
    if (isTaskRunning && currentTaskId) {
      handleStopClick()
    } else {
      // 检查是否已认证
      if (AuthService.isAuthenticated()) {
        setShowFactorDialog(true)
      } else {
        setShowAuthDialog(true)
      }
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

  const handleAuthSuccess = () => {
    setShowFactorDialog(true)
  }

  return (
    <div className="space-y-4 w-full">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">分析结果</h2>
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

      <div style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'none' }}>
        <ResultsMainView data={data} factorMeta={factorMeta} />
      </div>

      <FactorSelectionDialog
        open={showFactorDialog}
        onOpenChange={setShowFactorDialog}
        onConfirm={handleFactorConfirm}
      />

      <AuthDialog
        open={showAuthDialog}
        onOpenChange={setShowAuthDialog}
        onSuccess={handleAuthSuccess}
        title="数据分析权限验证"
        description="启动数据分析需要管理员权限，请输入用户名和密码"
      />
    </div>
  )
}
