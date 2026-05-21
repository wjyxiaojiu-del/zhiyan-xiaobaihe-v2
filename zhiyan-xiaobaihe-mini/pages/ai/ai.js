const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    messages: [],
    inputText: '',
    apiKey: '',
    loading: false,
    showKeyInput: false
  },

  onLoad() {
    const savedKey = wx.getStorageSync('ai_api_key')
    if (savedKey) this.setData({ apiKey: savedKey })
    else this.setData({ showKeyInput: true })
  },

  onKeyInput(e) { this.setData({ apiKey: e.detail.value }) },

  onSaveKey() {
    wx.setStorageSync('ai_api_key', this.data.apiKey)
    app.globalData.apiKey = this.data.apiKey
    this.setData({ showKeyInput: false })
    wx.showToast({ title: '已保存', icon: 'success' })
  },

  onInputChange(e) { this.setData({ inputText: e.detail.value }) },

  async onSend() {
    const msg = this.data.inputText.trim()
    if (!msg || this.data.loading) return

    const key = this.data.apiKey
    if (!key) {
      this.setData({ showKeyInput: true })
      return
    }

    const messages = this.data.messages.concat([{ role: 'user', content: msg }])
    this.setData({ messages, inputText: '', loading: true })

    try {
      const data = await api.chat(msg, key)
      const reply = data.response || data.error || '无回复'
      this.setData({
        messages: messages.concat([{ role: 'assistant', content: reply }]),
        loading: false
      })
    } catch (e) {
      this.setData({
        messages: messages.concat([{ role: 'assistant', content: '请求失败，请检查网络和API Key' }]),
        loading: false
      })
    }
  },

  onClearChat() {
    this.setData({ messages: [] })
  }
})
