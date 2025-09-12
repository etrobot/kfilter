import React, { useState } from 'react';
import * as d3 from 'd3';
import { SunburstData } from '../types';

interface EvaluationSunburstProps {
  data: SunburstData | null;
}

const EvaluationSunburst: React.FC<EvaluationSunburstProps> = ({ data }) => {
  const [hoveredSegment, setHoveredSegment] = useState<{name: string, value: number} | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{x: number, y: number}>({x: 0, y: 0});
  const svgRef = React.useRef<SVGSVGElement>(null);

  const SIZE = 500;
  const RADIUS = SIZE / 2;

  const partition = (data: SunburstData) =>
    d3.partition<SunburstData>().size([2 * Math.PI, RADIUS])(
      d3
        .hierarchy(data)
        .sum((d) => d.value || 0)
        .sort((a, b) => (b.value || 0) - (a.value || 0))
    );

  const getColor = () => {
    // 动态生成颜色方案
    const colorPalette = [
      '#3B82F6', // 蓝色
      '#10B981', // 绿色
      '#F59E0B', // 黄色
      '#8B5CF6', // 紫色
      '#EF4444', // 红色
      '#06B6D4', // 青色
      '#84CC16', // 青绿
      '#F97316', // 橙色
      '#EC4899', // 粉色
      '#6B7280', // 灰色
    ];

    if (!data?.children) return d3.scaleOrdinal<string, string>().range([colorPalette[0]]);

    const domain = data.children.map((c) => c.name);
    return d3.scaleOrdinal<string, string>().domain(domain).range(colorPalette);
  };

  const arc = d3
    .arc<d3.HierarchyRectangularNode<SunburstData>>()
    .startAngle((d) => d.x0)
    .endAngle((d) => d.x1)
    .padAngle((d) => Math.min((d.x1 - d.x0) / 2, 0.005))
    .padRadius(RADIUS / 2)
    .innerRadius((d) => d.y0)
    .outerRadius((d) => d.y1 - 1);

  const getSegmentColor = (d: d3.HierarchyRectangularNode<SunburstData>) => {
    const color = getColor();
    // 找到顶级父节点以保持颜色一致性
    let node = d;
    while (node.depth > 1) node = node.parent!;
    return color(node.data.name);
  };

  const getTextTransform = (d: d3.HierarchyRectangularNode<SunburstData>) => {
    const angle = (d.x0 + d.x1) / 2;
    const radius = (d.y0 + d.y1) / 2;
    const x = Math.cos(angle - Math.PI / 2) * radius;
    const y = Math.sin(angle - Math.PI / 2) * radius;
    const rotation = (angle * 180) / Math.PI - 90;

    return `translate(${x},${y}) rotate(${rotation > 90 ? rotation + 180 : rotation})`;
  };

  const truncateText = (text: string, maxLength: number = 8): string => {
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };

  if (!data || !data.children || data.children.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <div className="text-center">
          <div className="text-lg mb-2">暂无数据</div>
          <div className="text-sm">完成评估后将显示旭日图</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center" style={{ position: 'relative' }}>
      <svg width={SIZE} height={SIZE} ref={svgRef}>
        <g transform={`translate(${SIZE/2},${SIZE/2})`} fillOpacity={0.8}>
          {partition(data)
            .descendants()
            .filter((d) => d.depth)
            .map((d, i) => (
              <path
                key={`${d.data.name}-${i}`}
                fill={getSegmentColor(d)}
                stroke="hsl(var(--background))"
                strokeWidth={1}
                strokeLinejoin="round"
                d={arc(d) || undefined}
                style={{
                  transition: 'all 0.3s ease-in-out',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.stroke = '#f59e0b';
                  e.currentTarget.style.strokeWidth = '2';
                  e.currentTarget.style.fillOpacity = '1';
                  setHoveredSegment({name: d.data.name, value: d.value || 0});
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.stroke = 'hsl(var(--background))';
                  e.currentTarget.style.strokeWidth = '1';
                  e.currentTarget.style.fillOpacity = '0.8';
                  setHoveredSegment(null);
                }}
                onMouseMove={(e) => {
                  const svgRect = svgRef.current?.getBoundingClientRect();
                  if (svgRect) {
                    setTooltipPosition({
                      x: e.clientX - svgRect.left,
                      y: e.clientY - svgRect.top
                    });
                  }
                }}
              />
            ))}
        </g>
        <g
          transform={`translate(${SIZE/2},${SIZE/2})`}
          pointerEvents="none"
          textAnchor="middle"
          fontSize={9}
          fontFamily="sans-serif"
        >
          {partition(data)
            .descendants()
            .filter((d) => d.depth && d.depth <= 2 && ((d.y0 + d.y1) / 2) * (d.x1 - d.x0) > 10)
            .map((d, i) => (
              <text
                key={`text-${d.data.name}-${i}`}
                transform={getTextTransform(d)}
                dy="0.35em"
                dx="3"
                style={{ fontSize: d.depth === 1 ? '10px' : '8px', fontWeight: d.depth === 1 ? 'bold' : 'normal' }}
              >
                {truncateText(d.data.name)}
              </text>
            ))}
        </g>
      </svg>
      
      {hoveredSegment && (
        <div
          className="absolute bg-background border rounded-lg p-3 shadow-lg pointer-events-none text-sm z-50"
          style={{
            left: tooltipPosition.x,
            top: tooltipPosition.y,
            transform: 'translate(10px, -50px)',
            minWidth: '120px',
          }}
        >
          <div className="font-semibold">{hoveredSegment.name}</div>
          <div className="text-muted-foreground">
            评分: {hoveredSegment.value.toFixed(1)}
          </div>
        </div>
      )}
    </div>
  );
};

export default EvaluationSunburst;