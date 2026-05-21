const api = require('../../utils/api')

Page({
  data: {
    id: '',
    meta: {},
    content: {},
    instruments: [],
    tabs: ['概览', '操作步骤', '试剂配方', '避坑指南', '数据处理'],
    currentTab: 0,
    loading: true
  },

  onLoad(options) {
    this.setData({ id: options.id })
    this.loadDetail()
  },

  async loadDetail() {
    this.setData({ loading: true })
    try {
      const data = await api.getProtocol(this.data.id)
      this.setData({
        meta: data.meta,
        content: data.content,
        instruments: data.instruments || [],
        loading: false
      })
      wx.setNavigationBarTitle({ title: data.meta.name })
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'error' })
      this.setData({ loading: false })
    }
  },

  onTabTap(e) {
    this.setData({ currentTab: e.currentTarget.dataset.idx })
  },

  // 复制Markdown到剪贴板
  onCopyMD() {
    wx.showLoading({ title: '生成中...' })
    api.request('/api/export/' + this.data.id + '/md')
      .then(() => {
        // 如果API返回的是文件，用Clipboard API代替
        wx.hideLoading()
      })
      .catch(() => wx.hideLoading())

    // 构建简易MD文本复制到剪贴板
    const c = this.data.content
    const m = this.data.meta
    let md = `# ${m.id} ${m.name}\n\n`
    if (c.principle) md += `## 实验原理\n${c.principle}\n\n`
    if (c.steps && Array.isArray(c.steps)) {
      md += `## 操作步骤\n`
      c.steps.forEach((s, i) => {
        md += `### 步骤${i + 1}：${s.title}\n`
        if (s.how) md += `${s.how}\n`
        if (s.why) md += `- 为什么：${s.why}\n`
        md += '\n'
      })
    }
    if (c.reagents) md += `## 试剂\n${c.reagents}\n\n`
    if (c.safety) md += `## 安全提示\n${c.safety}\n\n`

    wx.setClipboardData({
      data: md,
      success() { wx.showToast({ title: '已复制到剪贴板', icon: 'success' }) }
    })
  },

  // 跳转运量配置
  onQuantity() {
    wx.navigateTo({ url: '/pages/quantity/quantity?id=' + this.data.id })
  }
})
