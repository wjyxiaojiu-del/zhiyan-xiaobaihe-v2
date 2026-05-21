const api = require('../../utils/api')

Page({
  data: {
    modes: ['摩尔浓度→质量', '质量→摩尔浓度', '溶液稀释', '梯度稀释', 'RPM↔RCF'],
    currentMode: 0,
    // 输入字段
    mw: '', molarity: '', volume: '',
    mass: '', vol2: '',
    stock: '', target: '', vol3: '',
    start: '', factor: '', steps: '', vol4: '',
    radius: '', rpmValue: '', rcfValue: '',
    rcfMode: 'rpm_to_rcf',
    // 结果
    result: null
  },

  onModeTap(e) {
    this.setData({ currentMode: e.currentTarget.dataset.idx, result: null })
  },

  onInput(e) {
    this.setData({ [e.currentTarget.dataset.field]: e.detail.value })
  },

  onRcfModeChange(e) {
    this.setData({ rcfMode: e.detail.value === '0' ? 'rpm_to_rcf' : 'rcf_to_rpm' })
  },

  async onCalculate() {
    const m = this.data.currentMode
    let data = {}

    if (m === 0) {
      data = { type: 'molarity_to_mass', mw: +this.data.mw, molarity: +this.data.molarity, volume: +this.data.volume }
    } else if (m === 1) {
      data = { type: 'mass_to_molarity', mw: +this.data.mw, mass: +this.data.mass, volume: +this.data.vol2 }
    } else if (m === 2) {
      data = { type: 'dilution', stock: +this.data.stock, target: +this.data.target, volume: +this.data.vol3 }
    } else if (m === 3) {
      data = { type: 'gradient', start: +this.data.start, factor: +this.data.factor, steps: +this.data.steps, vol: +this.data.vol4 }
    } else if (m === 4) {
      data = { type: 'rpm_rcf', mode: this.data.rcfMode, radius: +this.data.radius, value: +this.data.rpmValue }
    }

    try {
      const res = await api.calculate(data)
      this.setData({ result: res })
    } catch (e) {
      wx.showToast({ title: '计算失败', icon: 'error' })
    }
  }
})
