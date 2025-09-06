import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog'
import { Button } from './ui/button'

interface AuthDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  title?: string
  description?: string
}

export function AuthDialog({ 
  open, 
  onOpenChange, 
  onSuccess,
  title = "操作权限验证",
  description = "请输入用户名和密码以继续操作"
}: AuthDialogProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!username.trim() || !password.trim()) {
      setError('请输入用户名和密码')
      return
    }

    setLoading(true)
    setError(null)

    try {
      // 简单的验证逻辑 - 可以根据需要修改
      // 这里使用固定的用户名密码，实际项目中应该调用后端API
      if (username === 'admin' && password === 'admin123') {
        // 验证成功，保存到sessionStorage
        sessionStorage.setItem('auth_token', 'authenticated')
        sessionStorage.setItem('auth_time', Date.now().toString())
        onSuccess()
        onOpenChange(false)
        // 清空表单
        setUsername('')
        setPassword('')
      } else {
        setError('用户名或密码错误')
      }
    } catch (err) {
      setError('验证失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    setUsername('')
    setPassword('')
    setError(null)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            {description}
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="username" className="text-sm font-medium">
              用户名
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="请输入用户名"
              disabled={loading}
            />
          </div>
          
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">
              密码
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="请输入密码"
              disabled={loading}
            />
          </div>

          {error && (
            <div className="text-red-500 text-sm bg-red-50 p-2 rounded">
              {error}
            </div>
          )}

          <DialogFooter>
            <Button 
              type="button" 
              variant="outline" 
              onClick={handleCancel}
              disabled={loading}
            >
              取消
            </Button>
            <Button 
              type="submit" 
              disabled={loading || !username.trim() || !password.trim()}
            >
              {loading ? '验证中...' : '确认'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}