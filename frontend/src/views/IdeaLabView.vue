<template>
  <div class="page-container idea-lab-view">
    <div class="view-header">
      <div>
        <h1 class="page-title">💡 灵感与规划推演工坊 (Idea Lab)</h1>
        <p class="page-desc">由 AI 深度扫描本地代码库（Git/README/TODOs）或碰撞微型项目，推演高价值 Next Steps 并一键签发至 Agent 看板。</p>
      </div>
      <div class="header-actions">
        <el-button @click="router.push('/')">
          🎯 查看任务看板
        </el-button>
        <el-button @click="router.push('/quota')">
          ⚡ 算力调度雷达
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="lab-tabs">
      <!-- 既有项目 Next Steps 推演 -->
      <el-tab-pane label="🔍 现有项目体检与 Next Steps 推演" name="repo-analysis">
        <div class="section-card">
          <div class="control-row">
            <div class="proj-picker">
              <span class="label">选择服务器代码库：</span>
              <el-select v-model="selectedProject" placeholder="请选择本地项目" style="width: 280px" filterable>
                <el-option
                  v-for="p in projectList"
                  :key="p.name"
                  :label="p.name"
                  :value="p.name"
                >
                  <span style="float: left">{{ p.name }}</span>
                  <span style="float: right; color: var(--md-on-surface-variant-2); font-size: var(--md-text-caption)">
                    {{ p.is_git ? 'Git' : 'Dir' }}
                  </span>
                </el-option>
              </el-select>
            </div>
            <el-button type="primary" :loading="analyzing" :disabled="!selectedProject" @click="runAnalysis">
              🚀 深度体检并推演下一步
            </el-button>
          </div>

          <div v-if="analyzing" class="loading-state">
            <el-skeleton :rows="5" animated />
            <div class="loading-tip">正在读取仓库结构、最新提交与 README，由 AI 推演架构与功能走向（通常需 20~40 秒，请稍候）...</div>
          </div>

          <div v-else-if="suggestions.length > 0" class="suggestions-container">
            <div class="sub-header">
              <h3>🎯 为项目 <code>{{ selectedProject }}</code> 推演出的 {{ suggestions.length }} 个高价值 Next Steps：</h3>
              <span class="tip">可直接点击“复制 Prompt”交由 dsh 执行，或“放入待办”流转入任务看板</span>
            </div>

            <div class="tasks-grid">
              <div v-for="(item, idx) in suggestions" :key="idx" class="task-card">
                <div class="card-top">
                  <div class="badge-row">
                    <el-tag size="small" :type="categoryTag(item.category)" effect="plain">{{ item.category }}</el-tag>
                    <el-tag size="small" :type="priorityTag(item.priority)" effect="light">{{ priorityLabel(item.priority) }}</el-tag>
                    <span class="hours" v-if="item.estimated_hours">⏱️ ~{{ item.estimated_hours }}h</span>
                    <el-tag v-if="item.certified_by" size="small" type="info" effect="plain" class="cert-tag">
                      🛡️ {{ item.certified_by[0] }}
                    </el-tag>
                  </div>
                  <h4 class="task-title">{{ item.title }}</h4>
                </div>

                <div class="reason-box">
                  <strong>💡 推荐理由：</strong>{{ item.reason }}
                </div>

                <div class="desc-box">
                  <div class="desc-header">
                    <span class="desc-label">Agent 执行 Prompt：</span>
                    <button class="text-copy-btn" @click="copyPromptText(item)">📋 复制</button>
                  </div>
                  <pre class="desc-content">{{ item.description }}</pre>
                </div>

                <div class="card-footer">
                  <el-button
                    size="small"
                    @click="copyPromptText(item)"
                  >
                    📋 复制 Prompt
                  </el-button>
                  <el-button
                    type="primary"
                    size="small"
                    :loading="savingTaskIdx === idx"
                    @click="applyTask(item, idx)"
                  >
                    📥 放入看板待办 (To Cockpit)
                  </el-button>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="empty-placeholder">
            <div class="icon">📂</div>
            <div class="title">选择一个本地项目开始推演</div>
            <div class="sub">AI 将阅读 README、Git 记录及代码中的 TODO，为你提供架构治理、功能演进或测试保底方案。</div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 全新灵感碰撞机 -->
      <el-tab-pane label="✨ 全新项目灵感孵化机" name="spark">
        <div class="section-card">
          <div class="spark-control-box">
            <div class="spark-input-row">
              <el-input
                v-model="sparkTheme"
                placeholder="输入你想探索的灵感方向，例如：NAS 离线相册检索、个人轻量记账、自动发布飞书机器人..."
                clearable
                size="large"
                class="spark-main-input"
                @keyup.enter="runBrainstorm"
              >
                <template #prefix>
                  <span class="spark-prefix-icon">💡</span>
                </template>
              </el-input>
              <el-button
                type="primary"
                size="large"
                :loading="brainstorming"
                :disabled="!sparkTheme.trim()"
                @click="runBrainstorm"
              >
                ✨ 碰撞生成 MVP 灵感
              </el-button>
            </div>

            <div class="spark-presets-row">
              <span class="presets-label">🔥 热门方向快捷挑选:</span>
              <button
                v-for="preset in sparkPresets"
                :key="preset"
                type="button"
                class="preset-pill"
                :class="{ 'is-active': sparkTheme === preset }"
                @click="sparkTheme = preset"
              >
                {{ preset }}
              </button>
            </div>
          </div>

          <div v-if="brainstorming" class="loading-state">
            <el-skeleton :rows="5" animated />
            <div class="loading-tip">正在围绕「{{ sparkTheme }}」探索高痛点场景、微型软件与极简技术栈组合（通常需 15~30 秒）...</div>
          </div>

          <div v-else-if="ideas.length > 0" class="ideas-grid">
            <div v-for="(idea, idx) in ideas" :key="idx" class="idea-card">
              <div class="idea-top">
                <h3 class="idea-title">{{ idea.title }}</h3>
                <div class="idea-tagline">“{{ idea.tagline }}”</div>
              </div>

              <div class="idea-section">
                <span class="sec-label">🎯 解决痛点：</span>
                <span class="sec-text">{{ idea.problem }}</span>
              </div>

              <div class="idea-section">
                <span class="sec-label">🛠️ 建议技术栈：</span>
                <span class="sec-text code-font">{{ idea.tech_stack }}</span>
              </div>

              <div class="idea-section">
                <span class="sec-label">📦 MVP 核心特性：</span>
                <ul class="mvp-list">
                  <li v-for="(feat, fIdx) in idea.mvp_features" :key="fIdx">{{ feat }}</li>
                </ul>
              </div>

              <div class="prompt-preview">
                <div class="p-header">
                  <span class="p-label">启动任务 Prompt：</span>
                  <button class="text-copy-btn" @click="copyIdeaPrompt(idea)">📋 复制</button>
                </div>
                <code>{{ idea.initial_task_prompt }}</code>
              </div>

              <div class="idea-footer">
                <el-button
                  size="small"
                  @click="copyIdeaPrompt(idea)"
                >
                  📋 复制 Prompt
                </el-button>
                <el-button
                  type="primary"
                  size="small"
                  :loading="savingIdeaIdx === idx"
                  @click="applyIdea(idea, idx)"
                >
                  🚀 签发到看板并创建第一张卡片
                </el-button>
              </div>
            </div>
          </div>

          <div v-else class="empty-placeholder">
            <div class="icon">💡</div>
            <div class="title">缺少新项目灵感？选个主题一键碰撞</div>
            <div class="sub">AI 将为你设计轻量可行、1~2 个周末即可用 Harness 闭环的有趣项目原型。</div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '@/api/http'
import { copyText } from '@/utils/clipboard'

const router = useRouter()
const activeTab = ref('repo-analysis')
const selectedProject = ref('')
const sparkTheme = ref('开发者效率与个人自动化工具')
const sparkPresets = [
  '开发者效率与个人自动化工具',
  'AI Agent 工作流与 Micro-SaaS',
  '极简 CLI 终端神器与数据同步',
  '本地隐私与自托管 Web 实用小工具',
  '趣味微型实验项目与技术栈实战',
]

const projectList = ref<Array<{ name: string; is_git: boolean; description: string }>>([])
const analyzing = ref(false)
const brainstorming = ref(false)
const suggestions = ref<any[]>([])
const ideas = ref<any[]>([])
const savingTaskIdx = ref<number | null>(null)
const savingIdeaIdx = ref<number | null>(null)

async function loadProjects() {
  try {
    const res: any = await http.get('/ideator/projects')
    if (Array.isArray(res)) {
      projectList.value = res
      if (res.length > 0 && !selectedProject.value) {
        selectedProject.value = res[0].name
      }
    }
  } catch (err) {
    console.error('Failed to load projects:', err)
  }
}

async function runAnalysis() {
  if (!selectedProject.value) return
  analyzing.value = true
  suggestions.value = []
  try {
    const res: any = await http.post('/ideator/analyze', { project_name: selectedProject.value }, { timeout: 120000 })
    if (res && res.suggestions) {
      suggestions.value = res.suggestions
      ElMessage.success(`推演完成！已为 ${selectedProject.value} 生成 ${res.suggestions.length} 项高价值规划`)
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '分析失败')
  } finally {
    analyzing.value = false
  }
}

async function runBrainstorm() {
  brainstorming.value = true
  ideas.value = []
  try {
    const res: any = await http.post('/ideator/brainstorm', { theme: sparkTheme.value }, { timeout: 120000 })
    if (res && res.ideas) {
      ideas.value = res.ideas
      ElMessage.success(`创意生成成功！探索到 ${res.ideas.length} 个新项目方向`)
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '灵感碰撞失败')
  } finally {
    brainstorming.value = false
  }
}

async function copyPromptText(item: any) {
  const p = `【目标】${item.title}\n【类别】${item.category}\n【理由】${item.reason}\n\n【Agent Prompt】\n${item.description}`
  const ok = await copyText(p)
  if (ok) {
    ElMessage.success(`Prompt 已复制！可直接粘入 dsh 对话框`)
  } else {
    ElMessage.info('已复制或请手动选中文本')
  }
}

async function copyIdeaPrompt(idea: any) {
  const p = `【新项目立项】${idea.title}\n【痛点】${idea.problem}\n【技术栈】${idea.tech_stack}\n\n【启动Prompt】\n${idea.initial_task_prompt}`
  const ok = await copyText(p)
  if (ok) {
    ElMessage.success(`启动 Prompt 已复制！可直接粘入 dsh 对话框`)
  } else {
    ElMessage.info('已复制或请手动选中文本')
  }
}

async function applyTask(item: any, idx: number) {
  savingTaskIdx.value = idx
  try {
    const payload = {
      project_name: selectedProject.value, // 自动归属于独立项目
      name: `[${item.category}] ${item.title}`,
      description: `【推荐理由】${item.reason}\n\n【任务Prompt】\n${item.description}`,
      priority: item.priority || 'medium',
      estimated_hours: item.estimated_hours || 2,
    }
    const res: any = await http.post('/ideator/apply-task', payload)
    ElMessage.success(`已为独立项目「${res.project_name || selectedProject.value}」签发工单并放入看板！`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '创建任务失败')
  } finally {
    savingTaskIdx.value = null
  }
}

async function applyIdea(idea: any, idx: number) {
  savingIdeaIdx.value = idx
  try {
    const payload = {
      create_new_project: true, // 独立立项为全新项目
      project_name: idea.title,
      project_description: `${idea.tagline} | ${idea.problem} | 技术栈: ${idea.tech_stack}`,
      name: `[MVP 核心特性] ${idea.mvp_features?.[0] || '初始化工程并实现核心原型'}`,
      description: `【定位】${idea.tagline}\n【痛点】${idea.problem}\n【技术栈】${idea.tech_stack}\n\n【启动Prompt】\n${idea.initial_task_prompt}`,
      priority: 'high',
      estimated_hours: 4,
    }
    const res: any = await http.post('/ideator/apply-task', payload)
    ElMessage.success(`立项成功！已创建独立项目「${res.project_name || idea.title}」及首张 MVP 工单！`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '签发失败')
  } finally {
    savingIdeaIdx.value = null
  }
}

function categoryTag(cat: string) {
  if (cat === 'architecture' || cat === '架构') return 'warning'
  if (cat === 'feature' || cat === '功能') return 'primary'
  if (cat === 'testing' || cat === '测试') return 'success'
  if (cat === 'refactor' || cat === '重构') return 'info'
  return 'info'
}

function priorityTag(p: string) {
  if (p === 'high') return 'danger'
  if (p === 'medium') return 'warning'
  return 'info'
}

function priorityLabel(p: string) {
  if (p === 'high') return '高优'
  if (p === 'medium') return '中优'
  return '低优'
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.idea-lab-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: var(--md-text-title-lg);
  font-weight: var(--md-weight-semibold);
  margin: 0 0 6px 0;
  color: var(--md-on-surface);
}

.page-desc {
  margin: 0;
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
  max-width: 800px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-card {
  background: var(--md-surface);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-md);
  padding: 24px;
  min-height: 500px;
}

.spark-control-box {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--md-outline-variant);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.spark-input-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.spark-main-input {
  flex: 1;
  max-width: 680px;
}

.spark-prefix-icon {
  margin-right: 4px;
  font-size: var(--md-text-body-lg);
}

.spark-presets-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.presets-label {
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface-variant);
  font-weight: 500;
}

.preset-pill {
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-pill);
  padding: 4px 12px;
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface-variant);
  cursor: pointer;
  transition: all 0.15s ease;
}

.preset-pill:hover {
  background: var(--md-surface-container-high);
  border-color: var(--md-primary);
  color: var(--md-primary);
}

.preset-pill.is-active {
  background: var(--md-primary-tint);
  border-color: var(--md-primary);
  color: var(--md-primary);
  font-weight: 600;
}

.control-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--md-outline-variant);
}

.proj-picker {
  display: flex;
  align-items: center;
  gap: 8px;
}

.proj-picker .label {
  font-size: var(--md-text-label-md);
  font-weight: 500;
  color: var(--md-on-surface);
}

.loading-state {
  padding: 40px 20px;
  text-align: center;
}

.loading-tip {
  margin-top: 16px;
  font-size: var(--md-text-label-md);
  color: var(--md-primary);
}

.sub-header {
  margin-bottom: 20px;
}

.sub-header h3 {
  font-size: var(--md-text-title-md);
  margin: 0 0 4px 0;
  color: var(--md-on-surface);
}

.sub-header .tip {
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface-variant);
}

.tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 18px;
}

.task-card {
  background: var(--md-surface-container-low);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-sm);
  padding: 18px;
  display: flex;
  flex-direction: column;
  transition: all 0.2s ease;
}

.task-card:hover {
  border-color: var(--md-primary);
  box-shadow: var(--md-shadow-1);
}

.badge-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.badge-row .hours {
  font-size: var(--md-text-caption);
  color: var(--md-on-surface-variant);
  margin-left: auto;
}

.task-title {
  font-size: var(--md-text-body-lg);
  font-weight: 600;
  margin: 0 0 10px 0;
  color: var(--md-on-surface);
}

.reason-box {
  background: var(--md-warning-container);
  border-left: var(--md-accent-bar-width) solid var(--md-warning);
  padding: 8px 10px;
  border-radius: var(--md-radius-xs);
  font-size: var(--md-text-body-sm);
  line-height: 1.45;
  margin-bottom: 12px;
  color: var(--md-on-warning-container);
}

.desc-box {
  background: var(--md-surface);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-sm);
  padding: 10px;
  margin-bottom: 16px;
  flex: 1;
}

.desc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.desc-label {
  font-size: var(--md-text-caption);
  font-weight: 600;
  color: var(--md-on-surface-variant);
}

.text-copy-btn {
  background: none;
  border: none;
  color: var(--md-primary);
  cursor: pointer;
  font-size: var(--md-text-caption);
  padding: 0;
}
.text-copy-btn:hover { text-decoration: underline; }

.desc-content {
  font-size: var(--md-text-body-sm);
  line-height: 1.5;
  color: var(--md-on-surface);
  white-space: pre-wrap;
  margin: 0;
  font-family: inherit;
  max-height: 130px;
  overflow-y: auto;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px dashed var(--md-outline-variant);
}

/* 灵感孵化机 */
.ideas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 20px;
}

.idea-card {
  background: var(--md-surface-container-low);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.idea-top {
  margin-bottom: 12px;
}

.idea-title {
  font-size: var(--md-text-title-md);
  font-weight: var(--md-weight-semibold);
  margin: 0 0 4px 0;
  color: var(--md-on-surface);
}

.idea-tagline {
  font-size: var(--md-text-label-md);
  color: var(--md-primary);
  font-style: italic;
}

.idea-section {
  margin-bottom: 10px;
  font-size: var(--md-text-label-md);
  line-height: 1.45;
}

.sec-label { font-weight: 600; color: var(--md-on-surface); }
.sec-text { color: var(--md-on-surface-variant); }
.code-font { font-family: var(--md-font-mono); background: var(--md-surface); padding: 1px 4px; border-radius: var(--md-radius-xs); }

.mvp-list {
  margin: 4px 0 0 18px;
  padding: 0;
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface-variant);
}

.prompt-preview {
  background: var(--md-surface);
  border: 1px dashed var(--md-outline-variant);
  border-radius: var(--md-radius-sm);
  padding: 10px;
  font-size: var(--md-text-body-sm);
  margin-top: 8px;
  margin-bottom: 14px;
}

.p-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.p-label { font-weight: 600; color: var(--md-on-surface-variant); font-size: var(--md-text-caption); }

.prompt-preview code {
  color: var(--md-on-surface);
  word-break: break-all;
  white-space: pre-wrap;
  font-size: var(--md-text-caption);
}

.idea-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px dashed var(--md-outline-variant);
}

.empty-placeholder {
  text-align: center;
  padding: 60px 20px;
}

.empty-placeholder .icon { font-size: var(--md-text-display-xl); margin-bottom: 12px; }
.empty-placeholder .title { font-size: var(--md-text-title-md); font-weight: 600; margin-bottom: 6px; color: var(--md-on-surface); }
.empty-placeholder .sub { font-size: var(--md-text-label-md); color: var(--md-on-surface-variant); max-width: 480px; margin: 0 auto; }
</style>
