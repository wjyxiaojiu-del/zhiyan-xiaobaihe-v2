const api = require('../../utils/api')

Page({
  data: {
    query: '',
    results: [],
    searched: false,
    loading: false
  },

  onInput(e) {
    this.setData({ query: e.detail.value })
  },

  async onSearch() {
    const q = this.data.query.trim()
    if (!q) return
    this.setData({ loading: true, searched: true })
    try {
      const data = await api.search(q)
      this.setData({ results: data.results || [], loading: false })
    } catch (e) {
      this.setData({ results: [], loading: false })
    }
  },

  onResultTap(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/detail/detail?id=' + id })
  }
})
