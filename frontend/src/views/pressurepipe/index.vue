<template>
  <section class="page" data-module="pressurepipe">
    <header class="page-head">
      <div>
        <h2>压力管道管理</h2>
        <p class="page-desc">维护压力管道，围绕管道编号、管道名称、管道级别、公称直径做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记压力管道</button>
        <button class="btn" type="button" @click="exportRows">导出压力管道清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无压力管道数据，可先登记压力管道</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条压力管道记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/pressurepipe'
const columns = ["管道编号", "管道名称", "管道级别", "公称直径", "输送介质", "敷设方式", "下次检验日", "管道状态"]
const actions = ["办理投用", "安排检修", "停用管道"]
const stats = [{"label": "在用管道", "value": 0}, {"label": "隔离检修", "value": 0}, {"label": "管道总长", "value": 0}]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

function resetFilters() {
  filters.value = {}
  void reload()
}

// 列表与导出共用同一套查询参数，导出携带的范围与列表当前范围严格一致。
function listQuery() {
  // 页面筛选框只有前三列，其中后端只支持按管道编号过滤；
  // 管道名称、管道级别后端没有对应条件，保持不参与查询的既有口径。
  const params = new URLSearchParams()
  const keyword = filters.value['管道编号']?.trim()
  if (keyword) params.set('keyword', keyword)
  return params.toString()
}

async function exportRows() {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/export?${listQuery()}`)
    if (!response.ok) {
      throw new Error('压力管道清单导出失败')
    }
    const payload = (await response.json()) as {
      total?: number
      items?: Row[]
    }
    const items = payload.items ?? []
    const serverTotal = payload.total ?? items.length
    // 服务端按当前过滤范围返回，条数对不上说明口径有偏差，不落盘并提示。
    if (serverTotal !== total.value || items.length !== serverTotal) {
      throw new Error(
        `导出条数 ${items.length}（服务端合计 ${serverTotal}）与列表当前范围 ${total.value} 条不一致，请重新查询后再导出`,
      )
    }
    saveExportFile(response, items, serverTotal)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '压力管道清单导出失败'
  }
}

function saveExportFile(response: Response, items: Row[], total: number) {
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const star = /filename\*=UTF-8''([^;]+)/i.exec(disposition)
  const plain = /filename="?([^";]+)"?/i.exec(disposition)
  const filename = star
    ? decodeURIComponent(star[1])
    : plain?.[1] ?? '压力管道清单.json'
  const blob = new Blob([JSON.stringify(items, null, 2)], {
    type: 'application/json;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
  errorMessage.value = `已另存 ${filename}，共 ${total} 条，与列表当前范围一致`
}

function openCreate() {
  errorMessage.value = '压力管道登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('压力管道动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '压力管道操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = listQuery()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('压力管道列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '压力管道列表读取失败'
  }
}

onMounted(reload)
</script>
