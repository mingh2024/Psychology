<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { init, use, type EChartsType } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GraphChart } from 'echarts/charts'
import { LegendComponent, TimelineComponent, TitleComponent, TooltipComponent } from 'echarts/components'
import type { GraphSeriesOption } from 'echarts/charts'
import type { EChartsOption } from 'echarts'
import { courseData, extraRelations, timelineSlots, type CourseRecord, type GraphLink, type NodeCategory } from './data/graph-data'

use([CanvasRenderer, GraphChart, LegendComponent, TimelineComponent, TitleComponent, TooltipComponent])

type GraphNode = {
  id: string
  name: string
  category: NodeCategory
  symbolSize: number
  value?: string
  x?: number
  y?: number
  fixed?: boolean
}

const relationColors: Record<string, string> = {
  覆盖: '#0ea5e9',
  前置于: '#f97316',
  从属于: '#64748b',
  应用于: '#22c55e',
  影响: '#e11d48',
  测量: '#8b5cf6',
  演变: '#d97706',
  解释: '#14b8a6',
}

type KnowledgeSnapshot = {
  year: string
  courses: CourseRecord[]
  nodes: GraphNode[]
  links: GraphLink[]
  coverageCount: number
}

const courseNodeSize = 56

const categories: { name: NodeCategory }[] = [
  { name: '课程' },
  { name: '领域' },
  { name: '构念' },
  { name: '方法' },
  { name: '理论' },
  { name: '应用场景' },
]

const legendItems: { name: NodeCategory; className: string }[] = [
  { name: '课程', className: 'course' },
  { name: '领域', className: 'domain' },
  { name: '构念', className: 'construct' },
  { name: '方法', className: 'method' },
  { name: '理论', className: 'theory' },
  { name: '应用场景', className: 'application' },
]

const relationLegendItems = Object.entries(relationColors).map(([name, color]) => ({ name, color }))

function inferCategory(id: string): NodeCategory {
  if (id.startsWith('K')) return '课程'
  if (id.startsWith('D')) return '领域'
  if (id.startsWith('M')) return '方法'
  if (id.startsWith('T') || id.startsWith('H')) return '理论'
  if (id.startsWith('A')) return '应用场景'
  return '构念'
}

const courseByName = new Map(courseData.map((course) => [course.name, course]))

function addNode(nodes: Map<string, GraphNode>, node: GraphNode) {
  const current = nodes.get(node.id)
  if (!current || current.symbolSize < node.symbolSize) {
    nodes.set(node.id, node)
  }
}

function getCoursesByYear(year: (typeof timelineSlots)[number]['year']) {
  if (year === '总览') {
    return [...courseData].sort((first, second) => first.order - second.order)
  }

  return courseData
    .filter((course) => course.time === year || (course.time === '大三或大四' && (year === '大三' || year === '大四')))
    .sort((first, second) => first.order - second.order)
}

function buildSnapshot(slot: (typeof timelineSlots)[number]): KnowledgeSnapshot {
  const courses = getCoursesByYear(slot.year)
  const nodes = new Map<string, GraphNode>()
  const links: GraphLink[] = []

  for (const course of courses) {
    addNode(nodes, {
      id: course.id,
      name: course.name,
      category: '课程',
      symbolSize: courseNodeSize,
      value: `${course.category}｜${course.stage}`,
    })

    for (const prerequisiteName of course.prerequisites) {
      const prerequisite = courseByName.get(prerequisiteName)
      if (!prerequisite) continue

      addNode(nodes, {
        id: prerequisite.id,
        name: prerequisite.name,
        category: '课程',
        symbolSize: courseNodeSize,
        value: `前置课程｜${prerequisite.category}`,
      })
      links.push({ source: prerequisite.id, target: course.id, name: '前置于' })
    }

    course.coveredIds.forEach((id, index) => {
      const category = inferCategory(id)
      const name = course.coveredNames[index] ?? id

      addNode(nodes, {
        id,
        name,
        category,
        symbolSize: category === '课程' ? courseNodeSize : 32,
        value: `由「${course.name}」覆盖`,
      })
      links.push({ source: course.id, target: id, name: '覆盖' })
    })
  }

  const visibleNodeIds = new Set(nodes.keys())
  const existingLinkIds = new Set(links.map((link) => `${link.source}->${link.target}->${link.name}`))

  for (const relation of extraRelations) {
    if (!visibleNodeIds.has(relation.source) || !visibleNodeIds.has(relation.target)) continue

    const linkId = `${relation.source}->${relation.target}->${relation.name}`
    if (existingLinkIds.has(linkId)) continue

    existingLinkIds.add(linkId)
    links.push(relation)
  }

  return {
    year: slot.year,
    courses,
    nodes: Array.from(nodes.values()),
    links,
    coverageCount: courses.reduce((sum, course) => sum + course.coveredCount, 0),
  }
}

function layoutNodes(snapshot: KnowledgeSnapshot): GraphNode[] {
  const groups: Record<NodeCategory, GraphNode[]> = {
    课程: [],
    领域: [],
    构念: [],
    方法: [],
    理论: [],
    应用场景: [],
  }

  for (const node of snapshot.nodes) {
    groups[node.category].push(node)
  }

  for (const group of Object.values(groups)) {
    group.sort((first, second) => first.name.localeCompare(second.name, 'zh-Hans-CN'))
  }

  const layoutGrid = (
    items: GraphNode[],
    startX: number,
    startY: number,
    columns: number,
    columnGap: number,
    rowGap: number,
  ) =>
    items.map((node, index) => ({
      ...node,
      x: startX + (index % columns) * columnGap,
      y: startY + Math.floor(index / columns) * rowGap,
      fixed: true,
    }))

  const isOverview = snapshot.year === '总览'

  return [
    ...layoutGrid(groups.领域, -1680, -540, 3, 330, 210),
    ...layoutGrid(groups.方法, -1680, isOverview ? 880 : 360, 3, 330, 210),
    ...layoutGrid(groups.课程, -580, -400, 3, 500, 330),
    ...layoutGrid(groups.构念, 750, -750, 6, 290, 210),
    ...layoutGrid(groups.理论, 890, isOverview ? 2740 : 1380, 4, 370, 230),
    ...layoutGrid(groups.应用场景, 890, isOverview ? 5320 : 2440, 4, 370, 230),
  ]
}

const snapshots = timelineSlots.map((slot) => buildSnapshot(slot)) as [KnowledgeSnapshot, ...KnowledgeSnapshot[]]

const activeIndex = ref(0)
const chartElement = ref<HTMLDivElement>()
const chart = shallowRef<EChartsType>()
let resizeObserver: ResizeObserver | undefined

const activeSnapshot = computed(() => snapshots[activeIndex.value] ?? snapshots[0])

type TooltipPayload = {
  dataType?: string
  data: {
    name?: string
    category?: string
    value?: string
    source?: string
    target?: string
  }
}

const makeGraphSeries = (snapshot: KnowledgeSnapshot): GraphSeriesOption => ({
  type: 'graph',
  layout: 'none',
  animation: false,
  roam: true,
  draggable: false,
  categories,
  data: layoutNodes(snapshot).map((node) => ({
    ...node,
    fixed: true,
    label: { show: true },
  })),
  links: snapshot.links.map((link) => ({
    ...link,
    lineStyle: {
      color: relationColors[link.name] ?? '#94a3b8',
      opacity: 0.72,
      width: link.name === '前置于' ? 2.2 : 1.5,
    },
  })),
  label: {
    color: '#17202a',
    fontSize: 11,
    fontWeight: 1000,
    position: 'bottom',
    distance: 4,
    width: 96,
    overflow: 'truncate',
  },
  edgeSymbol: ['none', 'arrow'],
  edgeSymbolSize: 7,
  edgeLabel: {
    show: false,
  },
  lineStyle: {
    color: '#94a3b8',
    curveness: 0.14,
    opacity: 0.62,
    width: 1.4,
  },
  emphasis: {
    focus: 'adjacency',
    label: {
      show: true,
    },
    edgeLabel: {
      show: true,
      formatter(params: unknown) {
        const payload = params as { data?: { name?: string } }
        return payload.data?.name ?? ''
      },
    },
    lineStyle: {
      width: 3,
      opacity: 0.9,
    },
  },
})

const option: EChartsOption = {
  color: ['#2563eb', '#1e3a8a', '#7c3aed', '#16a34a', '#d97706', '#e11d48'],
  baseOption: {
    backgroundColor: '#f7f9fc',
    title: {
      text: '心理学知识图谱课程时间轴',
      subtext: '按大学四年展示课程与知识点覆盖关系',
      left: 24,
      top: 18,
      textStyle: {
        color: '#111827',
        fontSize: 22,
        fontWeight: 700,
      },
      subtextStyle: {
        color: '#64748b',
      },
    },
    tooltip: {
      trigger: 'item',
      formatter(params: unknown) {
        const payload = params as TooltipPayload

        if (payload.dataType === 'edge') {
          return `${payload.data.source} -> ${payload.data.target}<br/>关系：${payload.data.name}`
        }

        return `${payload.data.name}<br/>类型：${payload.data.category}<br/>${payload.data.value ?? ''}`
      },
    },
    legend: {
      right: 24,
      top: 24,
      orient: 'vertical',
      data: categories.map((item) => item.name),
    },
    timeline: {
      axisType: 'category',
      autoPlay: false,
      top: 190,
      left: 44,
      right: 44,
      currentIndex: 0,
      data: snapshots.map((snapshot) => snapshot.year),
      label: {
        color: '#475569',
      },
      checkpointStyle: {
        color: '#2563eb',
        borderColor: '#1d4ed8',
      },
      controlStyle: {
        color: '#2563eb',
        borderColor: '#2563eb',
      },
    },
    series: [makeGraphSeries(snapshots[0])],
  },
  options: snapshots.map((snapshot) => ({
    title: {
      subtext: `${snapshot.year}：${snapshot.courses.length}门课程，覆盖${snapshot.coverageCount}个知识点`,
    },
    series: [makeGraphSeries(snapshot)],
  })),
}

function handleTimelineChanged(payload: unknown) {
  const timelinePayload = payload as { currentIndex?: number }

  if (typeof timelinePayload.currentIndex === 'number') {
    activeIndex.value = timelinePayload.currentIndex
  }
}

onMounted(() => {
  if (!chartElement.value) return

  chart.value = init(chartElement.value)
  chart.value.setOption(option)
  chart.value.on('timelinechanged', handleTimelineChanged)

  resizeObserver = new ResizeObserver(() => {
    chart.value?.resize()
  })
  resizeObserver.observe(chartElement.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  chart.value?.off('timelinechanged', handleTimelineChanged)
  chart.value?.dispose()
})
</script>

<template>
  <main class="page">
    <section class="workspace">
      <div class="chart-panel">
        <div ref="chartElement" class="chart"></div>
      </div>

      <aside class="info-panel">
        <p class="eyebrow">{{ activeSnapshot.year }}</p>
        <h1>本科四年心理学知识图谱</h1>
        <p class="description">按大学四年展示课程、前置关系与覆盖知识点。</p>

        <div class="metric-grid">
          <div>
            <strong>{{ activeSnapshot.courses.length }}</strong>
            <span>本年课程</span>
          </div>
          <div>
            <strong>{{ activeSnapshot.coverageCount }}</strong>
            <span>覆盖节点</span>
          </div>
        </div>

        <div class="legend" aria-label="节点类型图例">
          <span v-for="item in legendItems" :key="item.name" :class="['legend-item', item.className]">
            {{ item.name }}
          </span>
        </div>

        <div class="relation-legend" aria-label="关系类型图例">
          <span v-for="item in relationLegendItems" :key="item.name" class="relation-legend-item">
            <span class="relation-line" :style="{ '--relation-color': item.color }"></span>
            {{ item.name }}
          </span>
        </div>

        <div class="section">
          <h2>课程</h2>
          <ul class="course-list">
            <li v-for="course in activeSnapshot.courses" :key="course.id">
              <span>{{ course.name }}</span>
              <small>{{ course.category }}｜{{ course.coveredCount }}节点</small>
            </li>
          </ul>
        </div>

        <div class="section">
          <h2>前置关系</h2>
          <ul class="link-list">
            <li v-for="course in activeSnapshot.courses.filter((item) => item.prerequisites.length)" :key="course.id">
              {{ course.prerequisites.join('、') }} -> {{ course.name }}
            </li>
          </ul>
        </div>
      </aside>
    </section>
  </main>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(body) {
  margin: 0;
  min-width: 320px;
  color: #17202a;
  background: #e8edf3;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.page {
  min-height: 100vh;
  padding: 24px;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  min-height: calc(100vh - 48px);
}

.chart-panel,
.info-panel {
  border: 1px solid #d7dee8;
  background: #f7f9fc;
  box-shadow: 0 16px 48px rgba(15, 23, 42, 0.08);
}

.chart-panel {
  min-height: 1120px;
  overflow: hidden;
}

.chart {
  width: 100%;
  height: 100%;
  min-height: 1120px;
}

.info-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
  overflow: auto;
}

.eyebrow {
  margin: 0;
  color: #2563eb;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0;
}

h1,
h2,
p {
  margin-top: 0;
}

h1 {
  margin-bottom: 10px;
  font-size: 28px;
  line-height: 1.18;
}

h2 {
  margin-bottom: 6px;
  color: #344054;
  font-size: 16px;
}

.description {
  margin-bottom: 0;
  color: #526070;
  line-height: 1.7;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.legend-item {
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
}

.relation-legend {
  display: grid;
  gap: 8px;
  margin-top: -4px;
}

.relation-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #475467;
  font-size: 13px;
  font-weight: 650;
}

.relation-line {
  position: relative;
  width: 42px;
  height: 0;
  border-top: 3px solid var(--relation-color);
}

.relation-line::after {
  position: absolute;
  top: -6px;
  right: -1px;
  width: 0;
  height: 0;
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  border-left: 8px solid var(--relation-color);
  content: '';
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.metric-grid div {
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}

.metric-grid strong {
  display: block;
  color: #111827;
  font-size: 24px;
  line-height: 1;
}

.metric-grid span {
  display: block;
  margin-top: 8px;
  color: #667085;
  font-size: 12px;
}

.section {
  border-top: 1px solid #dfe6ef;
  padding-top: 18px;
}

.legend-item.course {
  color: #1d4ed8;
  background: #dbeafe;
}

.legend-item.domain {
  color: #1e3a8a;
  background: #dbeafe;
}

.legend-item.construct {
  color: #6d28d9;
  background: #ede9fe;
}

.legend-item.method {
  color: #166534;
  background: #dcfce7;
}

.legend-item.theory {
  color: #7c2d12;
  background: #ffedd5;
}

.legend-item.application {
  color: #9f1239;
  background: #ffe4e6;
}

.course-list,
.link-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.course-list li {
  display: grid;
  gap: 4px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  padding: 10px 12px;
  background: #ffffff;
}

.course-list span {
  min-width: 0;
  font-weight: 650;
}

.course-list small {
  color: #667085;
}

.link-list li {
  border-left: 3px solid #93c5fd;
  padding: 4px 0 4px 10px;
  color: #475467;
  line-height: 1.5;
}

@media (max-width: 980px) {
  .page {
    padding: 12px;
  }

  .workspace {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .chart-panel,
  .chart {
    min-height: 620px;
  }
}
</style>
