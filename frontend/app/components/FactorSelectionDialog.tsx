import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog'
import { Checkbox } from './ui/checkbox'
import { Button } from './ui/button'
import { FactorMeta } from '../types'
import { api } from '../services/api'

interface FactorSelectionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (selectedFactors: string[], collectLatestData: boolean) => void
}

export function FactorSelectionDialog({ 
  open, 
  onOpenChange, 
  onConfirm 
}: FactorSelectionDialogProps) {
  const [factors, setFactors] = useState<FactorMeta[]>([])
  const [selectedFactors, setSelectedFactors] = useState<string[]>([])
  const [collectLatestData, setCollectLatestData] = useState(true)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (open) {
      loadFactors()
    }
  }, [open])

  const loadFactors = async () => {
    try {
      setLoading(true)
      const response = await api.getFactors()
      setFactors(response.items)
      // 默认选择所有因子
      setSelectedFactors(response.items.map(f => f.id))
    } catch (error) {
      console.error('Failed to load factors:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFactorToggle = (factorId: string, checked: boolean) => {
    if (checked) {
      setSelectedFactors(prev => [...prev, factorId])
    } else {
      setSelectedFactors(prev => prev.filter(id => id !== factorId))
    }
  }

  const handleConfirm = () => {
    if (selectedFactors.length === 0) {
      alert('请至少选择一个因子')
      return
    }
    onConfirm(selectedFactors, collectLatestData)
    onOpenChange(false)
  }

  const handleCancel = () => {
    onOpenChange(false)
  }

  const handleSelectAll = () => {
    setSelectedFactors(factors.map(f => f.id))
  }

  const handleSelectNone = () => {
    setSelectedFactors([])
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>选择计算因子</DialogTitle>
          <DialogDescription>
            请选择要计算的因子类型（至少选择一个）
          </DialogDescription>
        </DialogHeader>
        
        <div className="py-4">
          {loading ? (
            <div className="text-center py-4">加载因子列表...</div>
          ) : (
            <>
              <div className="flex gap-2 mb-4">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleSelectAll}
                >
                  全选
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleSelectNone}
                >
                  全不选
                </Button>
              </div>
              
              <div className="space-y-3">
                {factors.map((factor) => (
                  <div key={factor.id} className="flex items-start space-x-3">
                    <Checkbox
                      id={factor.id}
                      checked={selectedFactors.includes(factor.id)}
                      onCheckedChange={(checked) => 
                        handleFactorToggle(factor.id, checked as boolean)
                      }
                    />
                    <div className="grid gap-1.5 leading-none">
                      <label
                        htmlFor={factor.id}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        {factor.name}
                      </label>
                      {factor.description && (
                        <p className="text-xs text-muted-foreground">
                          {factor.description}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              {factors.length === 0 && !loading && (
                <div className="text-center py-4 text-muted-foreground">
                  暂无可用因子
                </div>
              )}
            </>
          )}
          
          {/* 数据采集选项 */}
          <div className="border-t pt-4 mt-4">
            <div className="flex items-start space-x-3">
              <Checkbox
                id="collect-latest-data"
                checked={collectLatestData}
                onCheckedChange={(checked) => setCollectLatestData(checked as boolean)}
              />
              <div className="grid gap-1.5 leading-none">
                <label
                  htmlFor="collect-latest-data"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  采集最新数据
                </label>
                <p className="text-xs text-muted-foreground">
                  勾选后会获取最新的热点数据，不勾选则直接使用日K线历史数据进行因子计算
                </p>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            取消
          </Button>
          <Button 
            onClick={handleConfirm}
            disabled={selectedFactors.length === 0}
          >
            确定 ({selectedFactors.length} 个因子)
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}