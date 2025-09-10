import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Button } from './ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from './ui/dialog'

interface ConfigDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved?: () => void
}

export function ConfigDialog({ open, onOpenChange, onSaved }: ConfigDialogProps) {
  const [bearer, setBearer] = useState('')
  const [cookie, setCookie] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [configured, setConfigured] = useState<boolean | null>(null)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const cfg = await api.getZaiConfig()
        if (!cancelled) {
          setConfigured(Boolean(cfg.configured))
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : '加载配置失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [open])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      if (!bearer.trim() || !cookie.trim()) {
        setError('请输入完整的 Bearer Token 与 Cookie 字符串')
        setSaving(false)
        return
      }
      await api.updateZaiConfig({ ZAI_BEARER_TOKEN: bearer.trim(), ZAI_COOKIE_STR: cookie.trim() })
      setConfigured(true)
      if (onSaved) onSaved()
      onOpenChange(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>配置 ZAI 凭证</DialogTitle>
          <DialogDescription>
            输入从 chat.z.ai 获取的 Bearer Token 与 Cookie，保存后将写入后端的 config.json。
          </DialogDescription>
        </DialogHeader>

        {configured !== null && (
          <div className={`text-sm mb-2 ${configured ? 'text-green-700' : 'text-amber-700'}`}>
            {configured ? '当前已配置凭证' : '当前未配置凭证'}
          </div>
        )}

        {error && (
          <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-2">{error}</div>
        )}

        <div className="space-y-4 mt-2">
          <div>
            <label className="block text-sm font-medium mb-1">ZAI_BEARER_TOKEN</label>
            <textarea
              className="w-full border rounded-md p-2 text-sm min-h-[80px]"
              placeholder="Bearer token"
              value={bearer}
              onChange={(e) => setBearer(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">ZAI_COOKIE_STR</label>
            <textarea
              className="w-full border rounded-md p-2 text-sm min-h-[80px]"
              placeholder="Cookie string"
              value={cookie}
              onChange={(e) => setCookie(e.target.value)}
            />
          </div>
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>取消</Button>
          <Button onClick={handleSave} disabled={saving || loading}>
            {saving ? '保存中...' : '保存'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
