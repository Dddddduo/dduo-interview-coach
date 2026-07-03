/**
 * Interview Coach — 核心应用框架 v2.0
 * ======================================
 * 全局状态管理、数据层、路由、组件工厂、工具函数。
 * 所有页面通过此模块获取数据和通用能力。
 *
 * 驾驭工程体现：
 *   - 单一数据源 (data.json → App.data)
 *   - 统一状态管理 (App.state)
 *   - localStorage 抽象层
 *   - 组件工厂方法
 *   - 错误边界
 */

const App = {
  // ---- 全局状态 ----
  data: null,
  state: {
    page: '',
    category: 'all',
    difficulty: 'all',
    search: '',
    tag: null,
    view: 'list',      // 'list' | 'daily' | 'compact'
    sidebarOpen: false,
  },
  today: new Date().toISOString().slice(0, 10),

  // ---- 生命周期 ----
  async init(page) {
    this.state.page = page;
    this._setupErrorBoundary();
    await this.loadData();
    this.setupSidebar();
    this.setupMobileMenu();
    this.highlightCurrentNav();
    this._reportInit(page);
  },

  // ---- 数据加载 ----
  async loadData(force = false) {
    if (this.data && !force) return this.data;

    const urls = ['data.json', 'index.json', '../questions/index.json'];
    for (const url of urls) {
      try {
        const resp = await fetch(url + '?' + Date.now());
        if (resp.ok) {
          this.data = await resp.json();
          this._normalizeData();
          return this.data;
        }
      } catch (e) { continue; }
    }

    // 最终回退
    this.data = this._emptyData();
    return this.data;
  },

  _emptyData() {
    return {
      meta: { last_updated: '', total_questions: 0, project: 'Interview Coach' },
      categories: {},
      cat_stats: {},
      top_tags: [],
      dates: [],
      by_date: {},
      questions: [],
      difficulty_levels: { easy: { name: '基础', color: '#3fb950' }, medium: { name: '中级', color: '#d2991d' }, hard: { name: '进阶', color: '#f85149' } },
    };
  },

  _normalizeData() {
    // 确保数据结构完整
    const d = this.data;
    d.questions = d.questions || [];
    d.categories = d.categories || {};
    d.top_tags = d.top_tags || [];
    d.dates = d.dates || [];
    d.by_date = d.by_date || {};
    d.cat_stats = d.cat_stats || {};

    // 为每个 question 补充默认值
    d.questions.forEach(q => {
      q.tags = q.tags || [];
      q.difficulty = q.difficulty || 'medium';
      q.category = q.category || 'unknown';
    });

    // 生成 top_tags（如果缺失）
    if (d.top_tags.length === 0 && d.questions.length > 0) {
      const tagCounts = {};
      d.questions.forEach(q => (q.tags||[]).forEach(t => {
        tagCounts[t] = (tagCounts[t] || 0) + 1;
      }));
      d.top_tags = Object.entries(tagCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 30)
        .map(([tag, count]) => ({ tag, count }));
    }

    // 生成 by_date（如果缺失）
    if (Object.keys(d.by_date).length === 0 && d.questions.length > 0) {
      d.questions.forEach(q => {
        const date = (q.created || '').slice(0, 10) || 'unknown';
        if (!d.by_date[date]) d.by_date[date] = [];
        d.by_date[date].push(q);
      });
      d.dates = Object.keys(d.by_date).sort().reverse();
    }
  },

  // ---- 错误边界 ----
  _setupErrorBoundary() {
    window.addEventListener('error', (e) => {
      console.error('App Error:', e.error);
      // 不阻断用户，仅记录
    });
  },

  _reportInit(page) {
    const qs = this.data?.questions || [];
    console.log(`[App] Init page="${page}" questions=${qs.length} today="${this.today}"`);
  },

  // ============================================================
  // 日期工具
  // ============================================================
  dateLabel(dateStr) {
    if (!dateStr) return '';
    if (dateStr === this.today) return '今天';
    const y = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    if (dateStr === y) return '昨天';
    const d = new Date(dateStr + 'T00:00:00');
    const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    return `${dateStr.slice(5)} ${days[d.getDay()]}`;
  },

  formatDate(dateStr, fmt = 'short') {
    if (!dateStr) return '';
    if (fmt === 'short') return dateStr.slice(5); // MM-DD
    if (fmt === 'full') return dateStr;
    if (fmt === 'relative') return this.dateLabel(dateStr);
    return dateStr;
  },

  daysAgo(dateStr) {
    if (!dateStr) return Infinity;
    const d1 = new Date(dateStr + 'T00:00:00');
    const d2 = new Date(this.today + 'T00:00:00');
    return Math.floor((d2 - d1) / 86400000);
  },

  // ============================================================
  // 格式化 & 转义
  // ============================================================
  esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
  },

  diffName(d) { return { easy: '基础', medium: '中级', hard: '进阶' }[d] || d || '未知'; },
  diffColor(d) { return { easy: 'var(--green)', medium: 'var(--orange)', hard: 'var(--red)' }[d] || 'var(--text-2)'; },
  diffBadge(d) { return { easy: 'badge-green', medium: 'badge-orange', hard: 'badge-red' }[d] || ''; },
  diffEmoji(d) { return { easy: '🟢', medium: '🟡', hard: '🔴' }[d] || '⚪'; },

  catInfo(catKey) {
    const cats = this.data?.categories || {};
    return cats[catKey] || { name: catKey || '未分类', icon: '📌' };
  },

  truncate(str, len = 80) {
    if (!str) return '';
    return str.length > len ? str.slice(0, len) + '...' : str;
  },

  // ============================================================
  // localStorage 复习数据层
  // ============================================================
  getReviewed(date) {
    try { return JSON.parse(localStorage.getItem('reviewed_' + date) || '[]'); }
    catch { return []; }
  },

  setReviewed(date, ids) {
    localStorage.setItem('reviewed_' + date, JSON.stringify(ids));
  },

  toggleReview(qid, date) {
    date = date || this.today;
    const reviewed = this.getReviewed(date);
    const idx = reviewed.indexOf(qid);
    if (idx >= 0) { reviewed.splice(idx, 1); }
    else { reviewed.push(qid); }
    this.setReviewed(date, reviewed);
    return idx < 0; // true = 新增复习, false = 取消
  },

  isReviewed(qid, date) {
    return this.getReviewed(date || this.today).includes(qid);
  },

  countReviewed(date) {
    return this.getReviewed(date || this.today).length;
  },

  getStreak() {
    let s = 0;
    const d = new Date();
    // 检查今天是否还没开始(允许今天没复习但昨天有)
    const todayReviewed = this.getReviewed(this.today);
    if (todayReviewed.length === 0) {
      // 今天还没复习，从昨天开始算
      d.setDate(d.getDate() - 1);
    }
    while (true) {
      const key = 'reviewed_' + d.toISOString().slice(0, 10);
      if (this.getReviewed(key).length > 0) { s++; d.setDate(d.getDate() - 1); }
      else break;
    }
    return s;
  },

  // ============================================================
  // 侧边栏
  // ============================================================
  setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar || sidebar.children.length > 0) return;

    const data = this.data;
    const qs = data?.questions || [];
    const cats = data?.categories || {};
    const catCounts = {};
    qs.forEach(q => { catCounts[q.category] = (catCounts[q.category] || 0) + 1; });

    const reviewedToday = this.countReviewed(this.today);
    const streak = this.getStreak();

    sidebar.innerHTML = `
      <div class="sidebar-brand"><span class="logo">🎯</span> Interview Coach</div>
      <nav class="sidebar-nav">
        <div class="sidebar-section">主菜单</div>
        <a href="index.html" class="sidebar-link" data-page="index"><span class="icon">🏠</span> 仪表盘</a>
        <a href="daily.html" class="sidebar-link" data-page="daily">
          <span class="icon">📅</span> 每日复习
          ${reviewedToday > 0 ? `<span class="badge">${reviewedToday}</span>` : ''}
        </a>
        <a href="knowledge.html" class="sidebar-link" data-page="knowledge"><span class="icon">🧠</span> 知识图谱</a>
        <a href="stats.html" class="sidebar-link" data-page="stats"><span class="icon">📊</span> 学习统计</a>
        <div class="sidebar-section">题库分类</div>
        ${Object.entries(cats)
          .filter(([, v]) => (catCounts[v.name] || catCounts[Object.keys(cats).find(k=>cats[k]===v)||'']) > 0 || true)
          .slice(0, 13)
          .map(([k, v]) => {
            const count = catCounts[k] || 0;
            return `<a href="questions.html?cat=${k}" class="sidebar-link" data-page="questions" style="${count===0?'opacity:0.4':''}">
              <span class="icon">${v.icon || '📌'}</span> ${v.name || k}
              ${count > 0 ? `<span class="badge">${count}</span>` : ''}
            </a>`;
          }).join('')}
      </nav>
      <div class="sidebar-footer">🔥 连续 ${streak} 天<br>📝 ${qs.length} 题 · ${Object.values(catCounts).filter(c=>c>0).length} 分类</div>
    `;
  },

  highlightCurrentNav() {
    document.querySelectorAll('.sidebar-link').forEach(a => {
      a.classList.toggle('active', a.dataset.page === this.state.page);
    });
  },

  setupMobileMenu() {
    const btn = document.getElementById('menu-btn');
    const sidebar = document.getElementById('sidebar');
    if (!btn || !sidebar) return;
    btn.addEventListener('click', () => {
      this.state.sidebarOpen = !this.state.sidebarOpen;
      sidebar.classList.toggle('open', this.state.sidebarOpen);
      if (this.state.sidebarOpen) {
        const overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        overlay.id = 'sidebar-overlay';
        overlay.addEventListener('click', () => {
          sidebar.classList.remove('open');
          overlay.remove();
          this.state.sidebarOpen = false;
        });
        document.body.appendChild(overlay);
      } else {
        document.getElementById('sidebar-overlay')?.remove();
      }
    });
  },

  // ============================================================
  // 组件工厂方法
  // ============================================================
  statCards(stats) {
    return `<div class="stat-cards">${stats.map(s => `
      <div class="stat-card ${s.color||''}${s.clickable?' clickable':''}" ${s.onclick?`onclick="${s.onclick}"`:''}>
        <div class="stat-value">${s.value}</div>
        <div class="stat-label">${s.label}</div>
        ${s.sub?`<div class="stat-sub">${s.sub}</div>`:''}
      </div>`).join('')}</div>`;
  },

  questionCard(q, opts = {}) {
    const cat = this.catInfo(q.category);
    const reviewed = opts.showReview ? this.isReviewed(q.id, opts.date) : null;
    const tags = (q.tags || []).slice(0, opts.maxTags || 4)
      .map(t => `<span class="tag" onclick="event.stopPropagation();event.preventDefault();location.href='questions.html?tag=${encodeURIComponent(t)}'">${this.esc(t)}</span>`).join('');

    const compact = opts.compact ? ' compact' : '';

    return `<a href="q/${q.id}.html" class="q-card${compact}">
      <span class="q-id">${q.id}</span>
      <div class="q-body">
        <div class="q-question">${this.esc(q.question)}</div>
        <div class="q-meta">
          <span>${cat.icon || ''} ${cat.name || q.category}</span>
          <span class="badge ${this.diffBadge(q.difficulty)}">${this.diffEmoji(q.difficulty)} ${this.diffName(q.difficulty)}</span>
          ${q.created ? `<span>${this.formatDate(q.created.slice(0,10))}</span>` : ''}
        </div>
        ${tags ? `<div class="q-tags">${tags}</div>` : ''}
      </div>
      ${reviewed !== null ? `<span class="q-status" style="color:${reviewed?'var(--green)':'var(--text-3)'};font-size:0.85rem;">${reviewed?'✅':'○'}</span>` : ''}
      ${opts.showActions ? `<div class="q-actions">
        <button class="btn btn-sm btn-ghost" onclick="event.stopPropagation();event.preventDefault();App.toggleReview('${q.id}');this.closest('.q-card').querySelector('.q-status').textContent=App.isReviewed('${q.id}')?'✅':'○';">✓</button>
      </div>` : ''}
    </a>`;
  },

  emptyState(icon, title, desc, action) {
    return `<div class="empty-state">
      <span class="empty-icon">${icon || '📭'}</span>
      <h3>${title || '暂无数据'}</h3>
      ${desc ? `<p>${desc}</p>` : ''}
      ${action ? `<div style="margin-top:16px;">${action}</div>` : ''}
    </div>`;
  },

  loading() {
    return '<div class="loading"><div class="spinner"></div><p style="margin-top:12px;">加载中...</p></div>';
  },

  // ============================================================
  // Toast 通知
  // ============================================================
  toast(msg, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const t = document.createElement('div');
    t.className = `toast ${type === 'error' ? 'error' : type === 'warn' ? 'warn' : ''}`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity 0.3s'; setTimeout(() => t.remove(), 300); }, 2200);
  },

  // ============================================================
  // URL 参数解析
  // ============================================================
  getUrlParam(name) {
    return new URLSearchParams(window.location.search).get(name);
  },

  setUrlParam(name, value) {
    const url = new URL(window.location);
    if (value) url.searchParams.set(name, value);
    else url.searchParams.delete(name);
    window.history.replaceState({}, '', url);
  },

  // ============================================================
  // 数据查询
  // ============================================================
  getQuestions(opts = {}) {
    let qs = [...(this.data?.questions || [])];
    if (opts.category) qs = qs.filter(q => q.category === opts.category);
    if (opts.difficulty) qs = qs.filter(q => q.difficulty === opts.difficulty);
    if (opts.tag) qs = qs.filter(q => (q.tags || []).includes(opts.tag));
    if (opts.search) {
      const kw = opts.search.toLowerCase();
      qs = qs.filter(q => q.question.toLowerCase().includes(kw) || (q.tags || []).some(t => t.toLowerCase().includes(kw)));
    }
    if (opts.sortBy === 'created') qs.sort((a, b) => (b.created || '').localeCompare(a.created || ''));
    if (opts.limit) qs = qs.slice(0, opts.limit);
    return qs;
  },

  getTagCounts() {
    const counts = {};
    (this.data?.questions || []).forEach(q => {
      (q.tags || []).forEach(t => { counts[t] = (counts[t] || 0) + 1; });
    });
    return counts;
  },

  getCategoryCounts() {
    const counts = {};
    (this.data?.questions || []).forEach(q => {
      counts[q.category || 'unknown'] = (counts[q.category || 'unknown'] || 0) + 1;
    });
    return counts;
  },

  /** 浏览器兼容性检查 */
  checkCompatibility() {
    const issues = [];
    if (!window.localStorage) issues.push('localStorage');
    if (!window.fetch) issues.push('fetch');
    return issues.length === 0;
  },

  /** 获取过去 N 天的日期列表 */
  getDateRange(days) {
    const dates = [], today = new Date();
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(today.getTime() - i * 86400000);
      dates.push(d.toISOString().slice(0, 10));
    }
    return dates;
  },

  /** 导出复习数据用于备份 */
  exportReviewData() {
    const data = {};
    this.getDateRange(365).forEach(date => {
      const r = this.getReviewed(date);
      if (r.length > 0) data[date] = r;
    });
    return { exported_at: new Date().toISOString(), total_dates: Object.keys(data).length, reviews: data };
  },

  /** 从备份恢复复习数据 */
  importReviewData(data) {
    if (!data?.reviews) return 0;
    let count = 0;
    Object.entries(data.reviews).forEach(([date, ids]) => { this.setReviewed(date, ids); count += ids.length; });
    return count;
  },

  /** 清除超过 N 天的旧复习数据 */
  cleanOldReviewData(maxDays) {
    const cutoff = new Date(Date.now() - maxDays * 86400000).toISOString().slice(0, 10);
    let cleaned = 0;
    this.getDateRange(maxDays * 2).forEach(date => {
      if (date < cutoff) { localStorage.removeItem('reviewed_' + date); cleaned++; }
    });
    return cleaned;
  },
};

// ============================================================
// 数据导出/导入工具 (用于备份和迁移复习数据)
// ============================================================
// 使用方式:
//   App.exportAllData()  → 下载完整备份 JSON
//   App.importAllData(json) → 恢复备份
// 数据包含: 复习记录 + 每日笔记

// ===== 数据备份与恢复 =====
// 在浏览器控制台运行: App.exportReviewData() 导出复习数据
// App.importReviewData(json) 恢复数据
// App.cleanOldReviewData(90) 清理90天前的旧数据

