const API_BASE = 'https://cccarolyn.top/api/miniapp'

// 全局 token
let _token = ''
let _openid = ''

App({
  onLaunch() {
    this.checkLogin()
  },

  checkLogin() {
    const saved = wx.getStorageSync('token')
    if (saved) {
      _token = saved
      _openid = wx.getStorageSync('openid')
      return
    }

    // 微信登录
    wx.login({
      success: (res) => {
        if (!res.code) return
        wx.request({
          url: `${API_BASE}/login`,
          method: 'POST',
          data: { code: res.code },
          success: (resp) => {
            if (resp.statusCode === 200 && resp.data.token) {
              _token = resp.data.token
              _openid = resp.data.openid
              wx.setStorageSync('token', _token)
              wx.setStorageSync('openid', _openid)
            }
          }
        })
      }
    })
  },

  getToken() { return _token },
  getOpenid() { return _openid },
  getApiBase() { return API_BASE }
})
