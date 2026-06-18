const app = getApp()

Page({
  data: {
    messages: [],
    inputText: '',
    sending: false,
    scrollTo: ''
  },

  onLoad() {
    // 等待登录完成
    setTimeout(() => {
      if (!app.getToken()) {
        wx.showToast({ title: '登录中...', icon: 'loading' })
        app.checkLogin()
      }
    }, 500)
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value })
  },

  askPreset(e) {
    const q = e.currentTarget.dataset.q
    this.setData({ inputText: q })
    this.sendMessage()
  },

  async sendMessage() {
    const text = this.data.inputText.trim()
    if (!text || this.data.sending) return

    // 确保已登录
    if (!app.getToken()) {
      wx.showToast({ title: '正在登录...', icon: 'loading' })
      app.checkLogin()
      setTimeout(() => this.sendMessage(), 1000)
      return
    }

    const messages = this.data.messages
    const userMsg = { id: Date.now(), role: 'user', content: text }
    const thinkMsg = { id: Date.now() + 1, role: 'ai', thinking: true }

    this.setData({
      messages: [...messages, userMsg, thinkMsg],
      inputText: '',
      sending: true,
      scrollTo: 'scroll-bottom'
    })

    try {
      const resp = await this._request('/chat', { query: text })

      // 移除思考中
      const msgs = this.data.messages.filter(m => !m.thinking)
      const aiMsg = {
        id: Date.now() + 2,
        role: 'ai',
        content: resp.answer || '(无响应)',
        source: resp.source || '',
        cards: resp.cards || []
      }
      this.setData({
        messages: [...msgs, aiMsg],
        sending: false,
        scrollTo: 'scroll-bottom'
      })
    } catch (err) {
      const msgs = this.data.messages.filter(m => !m.thinking)
      const errMsg = {
        id: Date.now() + 2,
        role: 'ai',
        content: '⚠️ 服务暂时不可用，请稍后重试'
      }
      this.setData({
        messages: [...msgs, errMsg],
        sending: false,
        scrollTo: 'scroll-bottom'
      })
    }
  },

  _request(path, data) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${app.getApiBase()}${path}`,
        method: 'POST',
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${app.getToken()}`
        },
        data: data,
        success: (res) => {
          if (res.statusCode === 200) resolve(res.data)
          else if (res.statusCode === 401) {
            wx.removeStorageSync('token')
            app.checkLogin()
            reject(new Error('请重新登录'))
          } else {
            reject(new Error(res.data.error || '请求失败'))
          }
        },
        fail: reject
      })
    })
  }
})
