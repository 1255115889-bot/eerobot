const { request } = require('../../app.js')

Page({
  data: {
    messages: [
      { id: 0, isUser: false, text: '你好！我是 HR 政策顾问 🤖\n可以问我年假、请假、薪资、证明等问题。', source: '', cards: [] }
    ],
    inputVal: '',
    scrollTo: ''
  },

  onInput(e) { this.setData({ inputVal: e.detail.value }) },

  sendMsg() {
    var q = this.data.inputVal.trim()
    if (!q) return
    var msgs = this.data.messages
    msgs.push({ id: Date.now(), isUser: true, text: q, source: '', cards: [] })
    this.setData({ messages: msgs, inputVal: '', scrollTo: 'msg-bottom' })

    var that = this
    request('/chat', { query: q }).then(function(data) {
      msgs.push({
        id: Date.now() + 1, isUser: false,
        text: data.answer || '(无回复)',
        source: data.source || '',
        cards: data.cards || []
      })
      that.setData({ messages: msgs, scrollTo: 'msg-bottom' })
    }).catch(function(err) {
      msgs.push({ id: Date.now() + 1, isUser: false, text: '服务暂时不可用: ' + (err.errMsg || JSON.stringify(err)), source: '', cards: [] })
      that.setData({ messages: msgs, scrollTo: 'msg-bottom' })
    })
  }
})
