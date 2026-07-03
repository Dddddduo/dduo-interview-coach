/**
 * 每日复习 — 追踪引擎
 * =====================
 * localStorage 驱动的复习打卡系统：
 *  - 连续打卡天数
 *  - 30 天月历视图
 *  - 按日期浏览题目
 *  - 一键标记复习完成
 */

const DR = {
  data: null,
  today: new Date().toISOString().slice(0, 10),

  async init() {
    await this.loadData();
    this.renderAll();
  },

  async loadData() {
    try { const r = await fetch('data.json'); this.data = await r.json(); }
    catch {
      try { const r = await fetch('index.json'); this.data = await r.json(); }
      catch { document.getElementById('review-list').innerHTML = '<div class="empty"><p>数据加载失败</p></div>'; }
    }
  },

  // ============================================================
  // localStorage 操作
  // ============================================================

  getReviewed(date) {
    return JSON.parse(localStorage.getItem('reviewed_' + date) || '[]');
  },

  toggleReview(qid) {
    const reviewed = this.getReviewed(this.today);
    const idx = reviewed.indexOf(qid);
    if (idx >= 0) reviewed.splice(idx, 1);
    else reviewed.push(qid);
    localStorage.setItem('reviewed_' + this.today, JSON.stringify(reviewed));
    this.renderAll();
  },

  getStreak() {
    let streak = 0, d = new Date();
    while (true) {
      const key = 'reviewed_' + d.toISOString().slice(0, 10);
      if (JSON.parse(localStorage.getItem(key) || '[]').length > 0) { streak++; d.setDate(d.getDate() - 1); }
      else break;
    }
    // 如果今天还没复习，检查昨天是否有连续
    if (streak === 0) {
      const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
      if (JSON.parse(localStorage.getItem('reviewed_' + yesterday) || '[]').length > 0) {
        return this.getStreakFrom(yesterday);
      }
    }
    return streak;
  },

  getStreakFrom(date) {
    let s = 0, d = new Date(date + 'T00:00:00');
    while (true) {
      const key = 'reviewed_' + d.toISOString().slice(0, 10);
      if (JSON.parse(localStorage.getItem(key) || '[]').length > 0) { s++; d.setDate(d.getDate() - 1); }
      else break;
    }
    return s;
  },

  // ============================================================
  // 渲染
  // ============================================================

  renderAll() {
    this.renderStreak();
    this.renderProgress();
    this.renderCalendar();
    this.renderDateTabs();
    this.renderReviewList();
  },

  renderStreak() {
    const streak = this.getStreak();
    document.getElementById('streak-num').textContent = `${streak} 天`;
    const subs = {
      0: '今天开始复习吧！💪',
      1: '好的开始！坚持就是胜利 ✨',
      3: '连续 3 天！渐入佳境 🚀',
      7: '一周了！你已经很棒了 🎉',
      14: '半个月！习惯正在养成 🔥',
      30: '一个月！你已经是复习达人了 👑',
    };
    let sub = '';
    for (const [d, msg] of Object.entries(subs)) { if (streak >= +d) sub = msg; }
    document.getElementById('streak-sub').textContent = sub;
  },

  renderProgress() {
    const todayReviewed = this.getReviewed(this.today);
    const total = (this.data?.questions || []).length;
    const done = todayReviewed.length;
    const pct = total > 0 ? Math.round(done / total * 100) : 0;

    document.getElementById('progress-text').textContent = `${done} / ${total} 题`;
    document.getElementById('progress-fill').style.width = `${Math.min(pct, 100)}%`;
  },

  renderCalendar() {
    const el = document.getElementById('calendar');
    let html = '';

    for (let i = 29; i >= 0; i--) {
      const d = new Date(Date.now() - i * 86400000);
      const ds = d.toISOString().slice(0, 10);
      const reviewed = this.getReviewed(ds);
      const isToday = ds === this.today;

      let cls = 'cal-day';
      if (i < 0) cls += ' future';
      else if (isToday) cls += ' today';
      else if (reviewed.length > 0) cls += ' reviewed';
      else if (ds < this.today) cls += ' missed';

      html += `<div class="${cls}" title="${ds}${reviewed.length?' · '+reviewed.length+'题':''}">${d.getDate()}</div>`;
    }
    el.innerHTML = html;
  },

  renderDateTabs() {
    const el = document.getElementById('date-tabs');
    const dates = this.getAvailableDates();

    el.innerHTML = dates.map((d, i) => {
      const reviewed = this.getReviewed(d);
      const active = d === this.today ? ' active' : '';
      const label = d === this.today ? `📅 今天` :
                    d === dates[0] && d !== this.today ? '' : d;
      return `<button class="date-tab${active}" onclick="DR.selectDate('${d}')">
        ${d === this.today ? '📅 今天' : d} · ${reviewed.length}题
      </button>`;
    }).join('');
  },

  getAvailableDates() {
    const dates = new Set();
    for (const q of (this.data?.questions || [])) {
      dates.add((q.created || '').slice(0, 10));
    }
    // 确保今天在列表中
    dates.add(this.today);
    return [...dates].sort().reverse().slice(0, 14);
  },

  selectDate(date) {
    // 重新高亮
    document.querySelectorAll('.date-tab').forEach(b => b.classList.remove('active'));
    // 渲染该日期的题目
    this.renderReviewList(date);
  },

  renderReviewList(date) {
    date = date || this.today;
    const el = document.getElementById('review-list');
    document.getElementById('review-list-title').textContent =
      date === this.today ? '📋 今日待复习' : `📋 ${date} 的题目`;

    const reviewed = this.getReviewed(date);
    const cats = this.data?.categories || {};

    // 收集该日期的所有题目 + 所有题目（每日复习应包含所有题）
    let qs = this.data?.questions || [];

    // 过滤：只显示当天创建的题目 或 全部题目（看用户偏好）
    // 默认显示全部，因为每天都要复习所有题
    // 可以按日期筛选
    if (date !== this.today) {
      qs = qs.filter(q => (q.created || '').slice(0, 10) === date);
    }

    if (qs.length === 0) {
      el.innerHTML = '<div class="empty"><p>这天没有题目</p></div>';
      return;
    }

    el.innerHTML = qs.map(q => {
      const isDone = reviewed.includes(q.id);
      const cat = cats[q.category] || {};
      const diffColor = { easy: '#3fb950', medium: '#d2991d', hard: '#f85149' }[q.difficulty] || '#888';

      return `<div class="review-card ${isDone ? 'done' : ''}">
        <div class="rc-check ${isDone ? 'checked' : ''}" onclick="DR.toggleReview('${q.id}')">
          ${isDone ? '✓' : ''}
        </div>
        <div class="rc-body">
          <div class="rc-question">
            <a href="q/${q.id}.html" target="_blank">${this.esc(q.question)}</a>
          </div>
          <div class="rc-meta">
            ${cat.icon || ''} ${cat.name || q.category} ·
            <span style="color:${diffColor}"> ${({easy:'基础',medium:'中级',hard:'进阶'})[q.difficulty]}</span>
            ${q.created ? ' · ' + q.created.slice(0, 10) : ''}
          </div>
        </div>
        <div class="rc-link"><a href="q/${q.id}.html" target="_blank">📖 查看 →</a></div>
      </div>`;
    }).join('');
  },

  esc(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
};

document.addEventListener('DOMContentLoaded', () => DR.init());
