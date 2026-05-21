const api = require('../../utils/api')

Page({
  data: {
    protocols: [],
    filtered: [],
    categories: ['全部', '植物生理', '分子生物', '基础操作'],
    currentCat: '全部',
    loading: true
  },

  onLoad() {
    this.loadProtocols()
  },

  onPullDownRefresh() {
    this.loadProtocols().then(() => wx.stopPullDownRefresh())
  },

  async loadProtocols() {
    this.setData({ loading: true })
    try {
      const data = await api.getProtocols()
      this.setData({ protocols: data, filtered: data, loading: false })
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'error' })
      this.setData({ loading: false })
    }
  },

  onCategoryTap(e) {
    const cat = e.currentTarget.dataset.cat
    const filtered = cat === '全部'
      ? this.data.protocols
      : this.data.protocols.filter(p => p.category === cat)
    this.setData({ currentCat: cat, filtered })
  },

  onSearchTap() {
    wx.navigateTo({ url: '/pages/search/search' })
  },

  onCardTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/detail/detail?id=' + id })
  }
})
