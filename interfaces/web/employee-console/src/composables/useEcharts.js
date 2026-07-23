// 按需引入 echarts —— 只注册用到的 chart 类型，减小 bundle 体积。
// 使用：在组件内 import { useBarChart, useLineChart, useGaugeChart } from '@/composables/useEcharts'

import * as echarts from 'echarts/core'
import { BarChart, LineChart, GaugeChart, PieChart, GraphChart } from 'echarts/charts'
import {
  GridComponent, TitleComponent, TooltipComponent, LegendComponent,
  DatasetComponent, GraphicComponent, PolarComponent, RadarComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

let _registered = false

function ensureRegistered() {
  if (_registered) return
  echarts.use([
    BarChart, LineChart, GaugeChart, PieChart, GraphChart,
    GridComponent, TitleComponent, TooltipComponent, LegendComponent,
    DatasetComponent, GraphicComponent, PolarComponent, RadarComponent,
    CanvasRenderer,
  ])
  _registered = true
}

// 引导注册一次（模块级 side-effect）
ensureRegistered()

// neon 调色板（霓虹深空主题）
export const NEON_PALETTE = [
  '#00f0ff',  // cyan
  '#ff2d9c',  // pink
  '#c12bff',  // magenta
  '#6cff66',  // lime
  '#ffb648',  // amber
  '#4cf6ff',
  '#a259ff',
]

// 通用 dark 主题 option 片段
export const NEON_THEME_FRAGMENT = {
  backgroundColor: 'transparent',
  textStyle: {
    color: '#9aa4cf',
    fontFamily: 'Inter, sans-serif',
  },
  grid: {
    top: 30, left: 40, right: 20, bottom: 30,
    containLabel: true,
  },
  tooltip: {
    backgroundColor: 'rgba(10, 14, 36, 0.95)',
    borderColor: 'rgba(0, 240, 255, 0.32)',
    borderWidth: 1,
    textStyle: { color: '#e8ecff', fontSize: 12 },
  },
}

export { echarts }

// 创建 chart 实例的 helper
export function createChart(dom, option) {
  const chart = echarts.init(dom, null, { renderer: 'canvas' })
  chart.setOption(option)
  // 响应容器尺寸
  const observer = new ResizeObserver(() => chart.resize())
  observer.observe(dom)
  return [chart, observer]
}

export function disposeChart([chart, observer]) {
  if (observer) observer.disconnect()
  if (chart) chart.dispose()
}
