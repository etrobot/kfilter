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
  const [openaiApiKey, setOpenaiApiKey] = useState('')
  const [openaiBaseUrl, setOpenaiBaseUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [zaiConfigured, setZaiConfigured] = useState<boolean | null>(null)
  const [openaiConfigured, setOpenaiConfigured] = useState<boolean | null>(null)

  // URL验证函数
  const isValidUrl = (urlString: string) => {
    try {
      const url = new URL(urlString)
      return url.protocol === 'http:' || url.protocol === 'https:'
    } catch (e) {
      return false
    }
  }

  useEffect(() => {
    if (!open) return
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const cfg = await api.getZaiConfig()
        if (!cancelled) {
          setConfigured(cfg.configured)
          setZaiConfigured(cfg.zai_configured)
          setOpenaiConfigured(cfg.openai_configured)
          // 填充现有配置值
          if (cfg.ZAI_BEARER_TOKEN_preview) {
            setBearer(cfg.ZAI_BEARER_TOKEN_preview)
          }
          if (cfg.ZAI_COOKIE_STR_preview) {
            setCookie(cfg.ZAI_COOKIE_STR_preview)
          }
          if (cfg.OPENAI_API_KEY_preview) {
            setOpenaiApiKey(cfg.OPENAI_API_KEY_preview)
          }
          if (cfg.OPENAI_BASE_URL) {
            setOpenaiBaseUrl(cfg.OPENAI_BASE_URL)
          }
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
      // 验证必填字段
      if (!bearer.trim() || !cookie.trim()) {
        setError('请输入完整的 ZAI Bearer Token 与 Cookie 字符串')
        setSaving(false)
        return
      }
      // 如果提供了OpenAI API Key，则验证Base URL格式
      if (openaiApiKey.trim() && openaiBaseUrl.trim() && !isValidUrl(openaiBaseUrl.trim())) {
        setError('请输入有效的 OpenAI Base URL')
        setSaving(false)
        return
      }
      
      // 构建配置对象
      const config = {
        ZAI_BEARER_TOKEN: bearer.trim(),
        ZAI_COOKIE_STR: cookie.trim(),
        OPENAI_API_KEY: openaiApiKey.trim(),
        OPENAI_BASE_URL: openaiBaseUrl.trim() || 'https://api.openai.com/v1'
      }
      
      await api.updateZaiConfig(config)
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
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>系统配置</DialogTitle>
          <DialogDescription>
            配置 ZAI 深度搜索凭证和 OpenAI API 设置，保存后将写入后端的 config.json。
          </DialogDescription>
        </DialogHeader>

        <div className="-mt-2 mb-4 text-sm">
          <span
            className={`mr-4 font-medium ${zaiConfigured ? 'text-green-700' : 'text-amber-700'}`}>
            ZAI 凭证: {zaiConfigured ? '已配置' : '未配置'}
          </span>
          <span className={`font-medium ${openaiConfigured ? 'text-green-700' : 'text-amber-700'}`}>
            OpenAI 凭证: {openaiConfigured ? '已配置' : '未配置'}
          </span>
        </div>

        {error && (
          <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-2">{error}</div>
        )}

        <div className="space-y-4 mt-2">
          {/* ZAI 配置部分 */}
          <div className="border-b pb-4">
            <h3 className="text-sm font-semibold mb-3 text-gray-700">ZAI 深度搜索配置</h3>
            <div className="space-y-3">
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
          </div>

          {/* OpenAI 配置部分 */}
          <div>
            <h3 className="text-sm font-semibold mb-3 text-gray-700">OpenAI API 配置</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">
                  OPENAI_API_KEY <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  className="w-full border rounded-md p-2 text-sm"
                  placeholder="sk-..."
                  value={openaiApiKey}
                  onChange={(e) => setOpenaiApiKey(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">OPENAI_BASE_URL</label>
                <input
                  type="url"
                  className="w-full border rounded-md p-2 text-sm"
                  placeholder="https://api.openai.com/v1 (默认)"
                  value={openaiBaseUrl}
                  onChange={(e) => setOpenaiBaseUrl(e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">
                  留空将使用默认的 OpenAI API 端点
                </p>
              </div>
            </div>
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
