const app = getApp()

function request(url, options = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.baseUrl + url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...options.header
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res.data)
        }
      },
      fail(err) {
        reject(err)
      }
    })
  })
}

// 获取全部Protocol列表
function getProtocols() {
  return request('/api/protocols')
}

// 获取单个Protocol详情
function getProtocol(id) {
  return request('/api/protocol/' + id)
}

// 搜索
function search(query) {
  return request('/api/search', { method: 'POST', data: { query } })
}

// 试剂计算器
function calculate(data) {
  return request('/api/calculate', { method: 'POST', data })
}

// AI聊天
function chat(message, apiKey) {
  return request('/api/chat', { method: 'POST', data: { message, api_key: apiKey } })
}

// 获取仪器列表
function getInstruments() {
  return request('/api/instruments')
}

// 获取仪器详情
function getInstrument(id) {
  return request('/api/instrument/' + id)
}

// 用量缩放
function scaleProtocol(data) {
  return request('/api/scale-protocol', { method: 'POST', data })
}

// 保存Protocol
function saveProtocol(sections) {
  return request('/api/save-protocol', { method: 'POST', data: { sections } })
}

// 上传文件（需要特殊处理multipart）
function uploadFile(filePath, apiKey) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: app.globalData.baseUrl + '/api/upload',
      filePath: filePath,
      name: 'file',
      formData: { api_key: apiKey },
      success(res) {
        const data = JSON.parse(res.data)
        if (data.success || data.data) {
          resolve(data)
        } else {
          reject(data)
        }
      },
      fail: reject
    })
  })
}

module.exports = {
  request,
  getProtocols,
  getProtocol,
  search,
  calculate,
  chat,
  getInstruments,
  getInstrument,
  scaleProtocol,
  saveProtocol,
  uploadFile
}
