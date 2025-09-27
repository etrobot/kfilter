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

  // Simple responsive sizing using CSS/Tailwind breakpoints
  const SIZE = 320; // Mobile-first size that fits in most mobile screens
  const RADIUS = SIZE / 2;

  const partition = (data: SunburstData) =>
    d3.partition<SunburstData>().size([2 * Math.PI, RADIUS])(
      d3
        .hierarchy(data)
        .sum((d) => d.value || 0)
        .sort((a, b) => (b.value || 0) - (a.value || 0))
    );

  const getColor = () => {
    // 马卡龙色系配色方案
    const colorPalette = [
      '#FFB3BA', // 粉红
      '#FFDFBA', // 桃色
      '#FFFFBA', // 柠檬黄
      '#BAFFC9', // 薄荷绿
      '#BAE1FF', // 天蓝
      '#E6BAFF', // 淡紫
      '#FFE1BA', // 杏色
      '#FFBAE1', // 樱花粉
      '#BAFFFF', // 浅青
      '#D4BAFF', // 薰衣草
      '#C9FFBA', // 浅绿
      '#FFCABA', // 珊瑚色
    ];

    if (!data?.children) return d3.scaleOrdinal<string, string>().range([colorPalette[0]]);

    // 为每个顶级板块分配固定的马卡龙色
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
    
    const baseColor = color(node.data.name);
    
    // 为不同层级添加透明度变化，创造深浅效果
    if (d.depth === 1) {
      return baseColor; // 顶级使用原色
    } else {
      // 子级使用稍微深一点的颜色
      return d3.color(baseColor)?.darker(0.2)?.toString() || baseColor;
    }
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
    <div className="w-full flex justify-center items-center" style={{ position: 'relative' }}>
      <svg 
        width={SIZE} 
        height={SIZE} 
        ref={svgRef}
        className="w-80 h-80 md:w-[500px] md:h-[500px]"
        viewBox={`0 0 ${SIZE} ${SIZE}`}
      >
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
          fontSize={8}
          fontFamily="sans-serif"
          className="text-xs md:text-sm"
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
                style={{ 
                  fontWeight: d.depth === 1 ? 'bold' : 'normal' 
                }}
                className={d.depth === 1 ? 'text-xs md:text-sm' : 'text-[10px] md:text-xs'}
              >
                {truncateText(d.data.name, 7)}
              </text>
            ))}
        </g>
      </svg>
      
      {hoveredSegment && (
        <div
          className="absolute bg-background border rounded-lg p-2 md:p-3 shadow-lg pointer-events-none text-xs md:text-sm z-50 min-w-20 md:min-w-28"
          style={{
            left: Math.min(tooltipPosition.x, SIZE - 100),
            top: Math.max(tooltipPosition.y - 50, 10),
            transform: 'translate(5px, -25px)',
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