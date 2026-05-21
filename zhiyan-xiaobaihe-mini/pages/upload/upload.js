const api = require('../../utils/api')

Page({
  data: {
    filePath: '',
    fileName: '',
    apiKey: '',
    loading: false,
    extracted: null,
    sections: {}
  },

  onLoad() {
    const savedKey = wx.getStorageSync('ai_api_key')
    if (savedKey) this.setData({ apiKey: savedKey })
  },

  onKeyInput(e) { this.setData({ apiKey: e.detail.value }) },

  onChooseFile() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['pdf', 'docx'],
      success: (res) => {
        const file = res.tempFiles[0]
        this.setData({ filePath: file.path, fileName: file.name })
      }
    })
  },

  async onExtract() {
    if (!this.data.filePath) {
      wx.showToast({ title: '请先选择文件', icon: 'error' })
      return
    }
    if (!this.data.apiKey) {
      wx.showToast({ title: '请输入API Key', icon: 'error' })
      return
    }

    this.setData({ loading: true })
    try {
      const data = await api.uploadFile(this.data.filePath, this.data.apiKey)
      if (data.data) {
        this.setData({
          extracted: data.data,
          sections: data.data,
          loading: false
        })
      } else {
        wx.showToast({ title: data.error || '提取失败', icon: 'error' })
        this.setData({ loading: false })
      }
    } catch (e) {
      wx.showToast({ title: '上传失败', icon: 'error' })
      this.setData({ loading: false })
    }
  },

  onFieldInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ ['sections.' + field]: e.detail.value })
  },

  onStepTitleInput(e) {
    const idx = e.currentTarget.dataset.idx
    const key = 'sections.steps[' + idx + '].title'
    this.setData({ [key]: e.detail.value })
  },

  onStepHowInput(e) {
    const idx = e.currentTarget.dataset.idx
    const key = 'sections.steps[' + idx + '].how'
    this.setData({ [key]: e.detail.value })
  },

  async onSave() {
    this.setData({ loading: true })
    try {
      const data = await api.saveProtocol(this.data.sections)
      if (data.success) {
        wx.showToast({ title: '已保存 ' + data.id, icon: 'success' })
        setTimeout(() => wx.navigateBack(), 1500)
      } else {
        wx.showToast({ title: data.error || '保存失败', icon: 'error' })
      }
    } catch (e) {
      wx.showToast({ title: '保存失败', icon: 'error' })
    }
    this.setData({ loading: false })
  }
})
