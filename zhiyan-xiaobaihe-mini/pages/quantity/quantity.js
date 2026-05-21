const api = require('../../utils/api')

Page({
  data: {
    id: '',
    sampleCount: 3,
    replicates: 3,
    scaleFactor: 9,
    quantities: [],
    scaledContent: '',
    loading: false,
    showResult: false
  },

  onLoad(options) {
    this.setData({ id: options.id })
  },

  onSampleInput(e) {
    const v = parseInt(e.detail.value) || 1
    this.setData({ sampleCount: v, scaleFactor: v * this.data.replicates })
  },

  onReplicateInput(e) {
    const v = parseInt(e.detail.value) || 1
    this.setData({ replicates: v, scaleFactor: this.data.sampleCount * v })
  },

  async onCalculate() {
    this.setData({ loading: true })
    try {
      const data = await api.scaleProtocol({
        protocol_id: this.data.id,
        sample_count: this.data.sampleCount,
        replicates: this.data.replicates
      })
      this.setData({
        quantities: data.original_quantities || [],
        scaledContent: data.scaled_content || '',
        scaleFactor: data.scale_factor,
        showResult: true,
        loading: false
      })
    } catch (e) {
      wx.showToast({ title: '计算失败', icon: 'error' })
      this.setData({ loading: false })
    }
  },

  onCopyScaled() {
    wx.setClipboardData({
      data: this.data.scaledContent,
      success() { wx.showToast({ title: '已复制', icon: 'success' }) }
    })
  }
})
