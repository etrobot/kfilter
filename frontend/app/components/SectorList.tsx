import { useIsMobile } from '../hooks/use-mobile'
import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// LLM Evaluation JSON formatter component
function LLMEvaluationDisplay({ evaluation }: { evaluation: any }) {
  if (typeof evaluation === 'string') {
    return <div className="text-sm text-purple-800 leading-relaxed">{evaluation}</div>
  }

  const { criteria_result, overall_score, top_scoring_criterion, top_score } = evaluation

  return (
    <div className="space-y-4">
      {/* Overall Score */}
      <div className="flex items-center justify-between bg-purple-100 p-3 rounded-lg">
        <h5 className="font-medium text-purple-900 mb-2 flex items-center gap-2">
          <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
          LLM智能评估
        </h5>
        <div className="flex items-center gap-2">
          <span className="text-xl font-bold text-purple-700">{overall_score}</span>
          <span className="text-sm text-purple-600">/100</span>
        </div>
      </div>

      {/* Top Scoring Criterion */}
      {top_scoring_criterion && (
        <div className="bg-green-50 border border-green-200 p-3 rounded-lg">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            <span className="font-medium text-green-800">最强优势</span>
          </div>
          <div className="text-sm text-green-700">{top_scoring_criterion}</div>
        </div>
      )}

      {/* Category */}
      {criteria_result?.category && (
        <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
            <span className="font-medium text-blue-800">行业分类</span>
          </div>
          <div className="text-sm text-blue-700">{criteria_result.category}</div>
        </div>
      )}

      {/* Detailed Scores */}
      <div className="space-y-3">
        <h6 className="font-medium text-purple-900 text-sm">详细评分</h6>
        {Object.entries(criteria_result || {}).map(([key, value]: [string, any]) => {
          if (key === 'category' || typeof value !== 'object') return null

          const score = parseInt(value.score || '0')
          const explanation = value.explanation || ''

          return (
            <div key={key} className="border border-purple-200 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-purple-800 text-sm">{key}</span>
                <div className="flex items-center gap-2">
                  <div className="flex">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <span
                        key={star}
                        className={`text-sm ${star <= score ? 'text-yellow-400' : 'text-gray-300'
                          }`}
                      >
                        ★
                      </span>
                    ))}
                  </div>
                  <span className="text-sm font-medium text-purple-700">{score}/5</span>
                </div>
              </div>
              {explanation && (
                <p className="text-xs text-purple-600 leading-relaxed">{explanation}</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface SectorStock {
  code: string
  name: string
  price: number
  change_pct: number
  volume: number
  turnover: number
}

interface SectorData {
  sector_code: string
  sector_name: string
  total_stocks: number
  hotspot_count: number
  hotspot_ratio: number
  stocks: SectorStock[]
  concept_analysis?: string
  llm_evaluation?: any
}

interface SectorListProps {
  sectors: SectorData[]
}

function SectorItem({ sector, index }: { sector: SectorData; index: number }) {
  return (
    <div id={`sector-${sector.sector_code}`} className="border-b last:border-b-0">
      <div className="p-4 bg-gray-25">
        <div className="flex justify-between items-center">
          <div>
            <h4 className="font-medium text-gray-900">
              {index + 1} {sector.sector_name}
            </h4>
            <p className="text-sm text-gray-600">
              代码: {sector.sector_code}
            </p>
          </div>
          <div className="text-right">
            <div className="text-lg font-bold text-red-600">
              {sector.hotspot_ratio}%
            </div>
            <div className="text-sm text-gray-600">
              {sector.hotspot_count}/{sector.total_stocks} 热点
            </div>
          </div>
        </div>
      </div>
      <div className='md:grid md:grid-cols-3'>
        {/* LLM评估结果 */}
        {sector.llm_evaluation && (
          <div className="p-4 bg-purple-50 border-t">
            <LLMEvaluationDisplay evaluation={sector.llm_evaluation} />
          </div>
        )}

        {/* 概念分析内容 */}
        {sector.concept_analysis && (
          <div className="p-4 bg-blue-50 border-t md:col-span-2">
            <h5 className="font-medium text-blue-900 mb-2 flex items-center gap-2">
              <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
              概念深度分析
            </h5>
            <div className="text-sm text-blue-800 leading-relaxed prose prose-sm prose-headings:text-blue-900 prose-strong:text-blue-900 prose-code:bg-blue-100 prose-code:text-blue-900 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs break-words">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  table: ({ node, ...props }) => (
                    <div className="overflow-x-auto my-4">
                      <table className="min-w-full divide-y divide-blue-200 border border-blue-200" {...props} />
                    </div>
                  ),
                  thead: ({ node, ...props }) => (
                    <thead className="bg-blue-100" {...props} />
                  ),
                  th: ({ node, ...props }) => (
                    <th className="px-3 py-2 text-left text-xs font-semibold text-blue-700 uppercase tracking-wider border border-blue-200" {...props} />
                  ),
                  td: ({ node, ...props }) => (
                    <td className="px-3 py-2 text-sm text-blue-900 border border-blue-200" {...props} />
                  ),
                }}
              >
                {sector.concept_analysis}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function SectorSidebar({ sectors }: { sectors: SectorData[] }) {
  const scrollToSection = (sectorCode: string) => {
    const element = document.getElementById(`sector-${sectorCode}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return (
    <div className="w-40 bg-white rounded-lg p-4 sticky top-4 max-h-[70vh] overflow-y-auto">
      <nav className="space-y-1">
        {sectors.map((sector) => (
          <button
            key={sector.sector_code}
            onClick={() => scrollToSection(sector.sector_code)}
            className="w-full text-left px-3 py-2 rounded-md text-sm transition-colors text-gray-600 hover:bg-gray-50 hover:text-gray-900"
          >
            <div className="flex items-center justify-between">
              <span className="truncate">{sector.sector_name}</span>
            </div>
          </button>
        ))}
      </nav>
    </div>
  )
}

export function SectorList({ sectors }: SectorListProps) {
  const isMobile = useIsMobile()

  if (sectors.length === 0) {
    return (
      <div className="bg-white rounded-lg p-8 text-center">
        <p className="text-gray-600">当前无热点板块数据</p>
      </div>
    )
  }

  const sectorItems = sectors.map((sector, index) => (
    <SectorItem key={sector.sector_code} sector={sector} index={index} />
  ))

  const scrollContainer = (
    <div className="max-h-[70vh] overflow-y-auto" style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'none' }}>
      {sectorItems}
    </div>
  )

  if (isMobile) {
    return (
      <div className="bg-white rounded-lg overflow-hidden">
        {scrollContainer}
      </div>
    )
  }

  return (
    <div className="flex gap-3 w-full">
      <SectorSidebar sectors={sectors} />
      <div className="flex-1 bg-white rounded-lg overflow-hidden">
        {scrollContainer}
      </div>
    </div>
  )
}