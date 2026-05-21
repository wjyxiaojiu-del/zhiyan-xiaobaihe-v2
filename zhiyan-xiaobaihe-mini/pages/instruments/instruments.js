const api = require('../../utils/api')

Page({
  data: {
    instruments: [],
    loading: true
  },

  onLoad() { this.loadInstruments() },
  onPullDownRefresh() { this.loadInstruments().then(() => wx.stopPullDownRefresh()) },

  async loadInstruments() {
    this.setData({ loading: true })
    try {
      const data = await api.getInstruments()
      this.setData({ instruments: data, loading: false })
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'error' })
      this.setData({ loading: false })
    }
  },

  onCardTap(e) {
    wx.navigateTo({ url: '/pages/instrument-detail/instrument-detail?id=' + e.currentTarget.dataset.id })
  }
})
