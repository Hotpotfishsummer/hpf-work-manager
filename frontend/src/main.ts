import { createApp } from 'vue'
import { createPinia } from 'pinia'
// ElementPlus on-demand imports (tree-shaken)
import {
  ElButton,
  ElIcon,
  ElTabs,
  ElTabPane,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElSelect,
  ElOption,
  ElDatePicker,
  ElDialog,
  ElTag,
  ElProgress,
  ElSlider,
  ElEmpty,
  ElDropdown,
  ElDropdownMenu,
  ElDropdownItem,
  ElRadioGroup,
  ElRadioButton,
  ElMessage,
  ElMessageBox,
  ElTable,
  ElTableColumn,
  ElTimeline,
  ElTimelineItem,
  ElAlert,
} from 'element-plus'
import 'element-plus/theme-chalk/el-button.css'
import 'element-plus/theme-chalk/el-icon.css'
import 'element-plus/theme-chalk/el-tabs.css'
import 'element-plus/theme-chalk/el-tab-pane.css'
import 'element-plus/theme-chalk/el-form.css'
import 'element-plus/theme-chalk/el-form-item.css'
import 'element-plus/theme-chalk/el-input.css'
import 'element-plus/theme-chalk/el-input-number.css'
import 'element-plus/theme-chalk/el-select.css'
import 'element-plus/theme-chalk/el-option.css'
import 'element-plus/theme-chalk/el-date-picker.css'
import 'element-plus/theme-chalk/el-dialog.css'
import 'element-plus/theme-chalk/el-tag.css'
import 'element-plus/theme-chalk/el-progress.css'
import 'element-plus/theme-chalk/el-slider.css'
import 'element-plus/theme-chalk/el-empty.css'
import 'element-plus/theme-chalk/el-dropdown.css'
import 'element-plus/theme-chalk/el-dropdown-menu.css'
import 'element-plus/theme-chalk/el-dropdown-item.css'
import 'element-plus/theme-chalk/el-radio.css'
import 'element-plus/theme-chalk/el-message.css'
import 'element-plus/theme-chalk/el-message-box.css'
import 'element-plus/theme-chalk/el-table.css'
import 'element-plus/theme-chalk/el-table-column.css'
import 'element-plus/theme-chalk/el-timeline.css'
import 'element-plus/theme-chalk/el-timeline-item.css'
import 'element-plus/theme-chalk/el-alert.css'
import 'element-plus/theme-chalk/base.css'
// Font subset: latin only
import '@fontsource/inter/latin-400.css'
import '@fontsource/inter/latin-500.css'
import '@fontsource/inter/latin-600.css'
import './design/tokens.css'
import './design/element-plus.css'
import './design/global.css'
import App from './App.vue'
import router from './router'
import { useThemeStore } from '@/stores/theme'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

// Register ElementPlus components globally (tree-shaken)
app.component('ElButton', ElButton)
app.component('ElIcon', ElIcon)
app.component('ElTabs', ElTabs)
app.component('ElTabPane', ElTabPane)
app.component('ElForm', ElForm)
app.component('ElFormItem', ElFormItem)
app.component('ElInput', ElInput)
app.component('ElInputNumber', ElInputNumber)
app.component('ElSelect', ElSelect)
app.component('ElOption', ElOption)
app.component('ElDatePicker', ElDatePicker)
app.component('ElDialog', ElDialog)
app.component('ElTag', ElTag)
app.component('ElProgress', ElProgress)
app.component('ElSlider', ElSlider)
app.component('ElEmpty', ElEmpty)
app.component('ElDropdown', ElDropdown)
app.component('ElDropdownMenu', ElDropdownMenu)
app.component('ElDropdownItem', ElDropdownItem)
app.component('ElRadioGroup', ElRadioGroup)
app.component('ElRadioButton', ElRadioButton)
app.component('ElTable', ElTable)
app.component('ElTableColumn', ElTableColumn)
app.component('ElTimeline', ElTimeline)
app.component('ElTimelineItem', ElTimelineItem)
app.component('ElAlert', ElAlert)

// Global methods (not components)
app.config.globalProperties.$message = ElMessage
app.config.globalProperties.$msgbox = ElMessageBox
app.config.globalProperties.$confirm = ElMessageBox.confirm
app.config.globalProperties.$prompt = ElMessageBox.prompt
app.config.globalProperties.$alert = ElMessageBox.alert

// 初始化主题（index.html 已预置 data-theme，这里是状态同步 + 系统监听）
useThemeStore(pinia)

app.mount('#app')
