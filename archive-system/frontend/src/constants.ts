/**
 * 共享常量 — 所有 mock/fallback 数据的唯一来源
 *
 * 避免多个组件各自维护重复数据
 */

// ============================================================
// 角色
// ============================================================

export const ROLE_LABELS: Record<string, string> = {
  system_admin: '系统管理员',
  archive_admin: '档案管理员',
  reviewer: '审核员',
  searcher: '查档人员',
}

export const ROLE_COLORS: Record<string, string> = {
  system_admin: 'purple',
  archive_admin: 'blue',
  reviewer: 'gray',
}

// ============================================================
// Mock 用户（回退数据）
// ============================================================

export const MOCK_USERS: { username: string; name: string; role: string; search?: number; view?: number; download?: number; print?: number }[] = [
  { username: 'wangjg', name: '王建国', role: 'reviewer', search: 186, view: 342, download: 28, print: 12 },
  { username: 'zhaojing', name: '赵静', role: 'reviewer', search: 156, view: 289, download: 22, print: 8 },
  { username: 'lifang', name: '李芳', role: 'archive_admin', search: 98, view: 156, download: 45, print: 0 },
  { username: 'chenxh', name: '陈小红', role: 'archive_admin', search: 76, view: 134, download: 32, print: 0 },
  { username: 'liuwei', name: '刘伟', role: 'reviewer', search: 23, view: 45, download: 5, print: 0 },
  { username: 'zhangmh', name: '张明华', role: 'reviewer', search: 12, view: 28, download: 3, print: 0 },
  { username: 'admin', name: '管理员', role: 'system_admin', search: 12, view: 28, download: 3, print: 0 },
]

// ============================================================
// 档案门类树（检索侧栏）
// ============================================================

export const CATEGORY_TREE: any[] = [
  { key: '行政档案', label: '行政档案', count: 45210, expanded: false, children: [
    { key: '学校办公室', label: '学校办公室', count: 12800 },
    { key: '人事处', label: '人事处', count: 9800 },
    { key: '财务处', label: '财务处', count: 7200 },
  ]},
  { key: '党群档案', label: '党群档案', count: 18500, expanded: false, children: [
    { key: '组织部', label: '组织部', count: 5200 },
    { key: '纪委', label: '纪委', count: 3100 },
    { key: '工会', label: '工会', count: 2100 },
  ]},
  { key: '教学档案', label: '教学档案', count: 23100, expanded: false, children: [
    { key: '教务处', label: '教务处', count: 11000 },
    { key: '研究生院', label: '研究生院', count: 4500 },
  ]},
  { key: '科研档案', label: '科研档案', count: 12050, expanded: false, children: [] },
  { key: '人事档案', label: '人事档案', count: 9800, expanded: false, children: [] },
  { key: '财务档案', label: '财务档案', count: 7200, expanded: false, children: [] },
  { key: '基建档案', label: '基建档案', count: 3800, expanded: false, children: [] },
  { key: '声像档案', label: '声像档案', count: 2100, expanded: false, children: [] },
]

// ============================================================
// 全宗号选项
// ============================================================

export const FONDS_OPTIONS = ['XZ', 'DQ', 'JX', 'CW', 'RS', 'KY', 'JJ', 'SX']

// ============================================================
// 年度列表（回退）
// ============================================================

export const MOCK_YEAR_LIST = [
  { year: 2025, count: 12300 }, { year: 2024, count: 11800 }, { year: 2023, count: 10500 },
  { year: 2022, count: 9800 }, { year: 2021, count: 9200 }, { year: 2020, count: 8900 },
  { year: 2010, count: 7500 }, { year: 2000, count: 6800 }, { year: 1990, count: 5200 },
  { year: 1980, count: 3400 }, { year: 1970, count: 2100 },
]

// ============================================================
// 首页最近活动（回退）
// ============================================================

export const MOCK_ACTIVITIES = [
  { type: 'search', desc: '用户"管理员"检索了关键词"招生 1996"', time: '2 分钟前' },
  { type: 'review', desc: 'AI 预审任务 REV-2026-001 完成 560 件', time: '15 分钟前' },
  { type: 'ocr', desc: 'OCR 任务"历史档案补录"处理完成 2400 页', time: '1 小时前' },
  { type: 'system', desc: '文件增量同步完成，新增 125 个文件', time: '2 小时前' },
  { type: 'login', desc: '用户"审核员李芳"登录系统', time: '3 小时前' },
]

// ============================================================
// 统计页面回退数据
// ============================================================

export const MOCK_STATS_TYPE = [
  { type: 'search', count: 342 }, { type: 'view', count: 156 },
  { type: 'review', count: 89 }, { type: 'download', count: 45 },
  { type: 'print', count: 23 }, { type: 'login', count: 198 },
]

export const MOCK_METHOD_DETAIL = [
  { type: 'search', month_count: 1280, pct: 23.1, year_count: 8560, trend: 'up' },
  { type: 'view', month_count: 2340, pct: 42.2, year_count: 15680, trend: 'up' },
  { type: 'download', month_count: 320, pct: 5.8, year_count: 2340, trend: 'down' },
  { type: 'print', month_count: 85, pct: 1.5, year_count: 680, trend: 'flat' },
]

// ============================================================
// 操作类型标签
// ============================================================

export const OP_TYPE_LABELS: Record<string, string> = {
  search: '检索', view: '浏览', review: '审核', download: '下载',
  print: '打印', admin: '管理', login: '登录', logout: '退出',
  ocr: 'OCR', sync: '同步',
}

// ============================================================
// 预审工作台回退数据
// ============================================================

export const MOCK_REVIEW_FALLBACK = {
  risk_score: 48, risk_level: '中', suggestion: '建议部分开放',
  reason: '该档案引用了上级单位来文，且包含部分个人隐私信息。建议对相关段落做遮盖脱敏处理后开放其余内容。',
  sensitive_items: [
    { type: '上级来文引用', content: '根据国务院[1973]XX号文件精神...', start_char: 50, end_char: 80 },
    { type: '个人隐私', content: '学生张三，家庭出身地主，父亲张某某...', start_char: 200, end_char: 235 },
    { type: '内部事项', content: '经校长办公会研究决定...', start_char: 350, end_char: 370 },
  ],
  llm_confidence: 0.87, rule_hits_count: 5, llm_raw_score: 45,
}
