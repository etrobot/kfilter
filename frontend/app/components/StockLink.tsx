import React from 'react'

interface StockLinkProps {
  code: string
  name?: string
  className?: string
}

function getXueqiuUrl(stockCode: string) {
  const code = stockCode.replace(/\D/g, '')
  let fullCode = ''
  if (code.startsWith('6')) {
    fullCode = `SH${code}`
  } else if (code.startsWith('8')) {
    fullCode = `BJ${code}`
  } else if (code.startsWith('0') || code.startsWith('3')) {
    fullCode = `SZ${code}`
  } else {
    fullCode = `SH${code}`
  }
  return `https://xueqiu.com/S/${fullCode}`
}

function getFullStockCode(stockCode: string) {
  const code = stockCode.replace(/\D/g, '')
  if (code.startsWith('6')) {
    return `SH${code}`
  } else if (code.startsWith('8')) {
    return `BJ${code}`
  } else if (code.startsWith('0') || code.startsWith('3')) {
    return `SZ${code}`
  } else {
    return `SH${code}`
  }
}

export function StockLink({ code, name, className = '' }: StockLinkProps) {
  return (
    <a
      href={getXueqiuUrl(code)}
      target="_blank"
      rel="noopener noreferrer"
      className={`hover:text-blue-600 hover:underline ${className}`}
    >
      <div className="font-medium">{name || code}</div>
      <div className="text-xs text-muted-foreground font-mono">{getFullStockCode(code)}</div>
    </a>
  )
}
