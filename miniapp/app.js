const API = 'https://cccarolyn.top/api/miniapp'
const app = getApp ? getApp() : { globalData: { token: '' } }

App({
  globalData: { token: '', openid: '' },

  onLaunch() {
    const saved = wx.getStorageSync('token')
    if (saved) { this.globalData.token = saved; return }
    wx.login({
      success: res => {
        wx.request({
          url: API + '/login', method: 'POST',
          data: { code: res.code },
          success: r => {
            if (r.data && r.data.token) {
              this.globalData.token = r.data.token
              wx.setStorageSync('token', r.data.token)
            }
          }
        })
      }
    })
  }
})

function request(path, data, method) {
  method = method || 'POST'
  var token = (getApp() && getApp().globalData && getApp().globalData.token) || ''
  return new Promise(function(resolve, reject) {
    wx.request({
      url: API + path, method: method,
      header: { 'Authorization': 'Bearer ' + token },
      data: data,
      success: function(r) {
        if (r.statusCode === 200) resolve(r.data); else reject(r.data)
      },
      fail: reject
    })
  })
}

module.exports = { request: request }
