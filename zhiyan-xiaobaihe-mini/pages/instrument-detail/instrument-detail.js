const api = require('../../utils/api')

Page({
  data: {
    id: '',
    instrument: null,
    currentHotspot: null,
    showPanel: false,
    loading: true
  },

  onLoad(options) {
    this.setData({ id: options.id })
    this.loadDetail()
  },

  async loadDetail() {
    this.setData({ loading: true })
    try {
      const data = await api.getInstrument(this.data.id)
      this.setData({ instrument: data, loading: false })
      wx.setNavigationBarTitle({ title: data.name })
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'error' })
      this.setData({ loading: false })
    }
  },

  onHotspotTap(e) {
    const idx = e.currentTarget.dataset.idx
    this.setData({
      currentHotspot: this.data.instrument.hotspots[idx],
      showPanel: true
    })
  },

  onClosePanel() {
    this.setData({ showPanel: false, currentHotspot: null })
  },

  onProtocolTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/detail/detail?id=' + id })
  }
})
