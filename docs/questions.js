/**
 * 题库浏览器 — 动态渲染引擎
 * ================================
 * 从 data.json 加载数据，支持列表/日期分组两种视图、分类筛选、
 * 难度过滤、全文搜索、标签云、每日复习追踪。
 */

const QB = {
  data: null,
  state: {
    view: 'list',           // 'list' | 'daily'
    category: 'all',
    difficulty: 'all',
    search: '',
    tag: null,
  },

  async init() {
    await this.load();
    if (!this.data) return;
    this.renderStats();
    this.renderCategories();
    this.renderDifficulty();
    this.renderContent();
    this.renderTagCloud();
    this.bindEvents();
  },

  async load() {
    try {
      const resp = await fetch('data.json?' + Date.now());
      this.data = await resp.json();
    } catch (e) {
      try {
        const resp = await fetch('index.json');
        this.data = await resp.json();
      } catch (e2) {
        document.getElementById('content').innerHTML =
          '<div class="empty"><div class="empty-icon">📭</div><p>题库数据加载失败</p><p style="font-size:0.85rem;color:var(--text-secondary);">请先运行 <code>python scripts/generate_site.py</code></p></div>';
      }
    }
  },

  // ============================================================
  // 过滤
  // ============================================================

  getFiltered() {
    if (!this.data) return [];
    let qs = [...(this.data.questions || [])];

    if (this.state.category !== 'all')
      qs = qs.filter(q => q.category === this.state.category);
    if (this.state.difficulty !== 'all')
      qs = qs.filter(q => q.difficulty === this.state.difficulty);
    if (this.state.tag)
      qs = qs.filter(q => (q.tags || []).includes(this.state.tag));
    if (this.state.search) {
      const kw = this.state.search.toLowerCase();
      qs = qs.filter(q =>
        q.question.toLowerCase().includes(kw) ||
        (q.tags || []).some(t => t.toLowerCase().includes(kw)) ||
        (q.category || '').toLowerCase().includes(kw)
      );
    }
    return qs;
  },

  // ============================================================
  // 渲染
  // ============================================================

  renderStats() {
    const el = document.getElementById('stats-bar');
    if (!el) return;
    const qs = this.data.questions || [];
    const today = new Date().toISOString().slice(0, 10);
    const todayReviewed = JSON.parse(localStorage.getItem('reviewed_' + today) || '[]');
    const streak = this.calcStreak();

    el.innerHTML = `
      <div class="stat-pill">📝 <strong>${qs.length}</strong> 题</div>
      <div class="stat-pill">📂 <strong>${Object.keys(this.data.cat_stats || {}).length}</strong> 分类</div>
      <div class="stat-pill">✅ 今日已复习 <strong>${todayReviewed.length}</strong> 题</div>
      ${streak > 0 ? `<div class="stat-pill streak">🔥 连续 <strong>${streak}</strong> 天</div>` : ''}
    `;
  },

  calcStreak() {
    let streak = 0;
    const d = new Date();
    while (true) {
      const key = 'reviewed_' + d.toISOString().slice(0, 10);
      const reviewed = JSON.parse(localStorage.getItem(key) || '[]');
      if (reviewed.length > 0) { streak++; d.setDate(d.getDate() - 1); }
      else break;
    }
    return streak;
  },

  renderCategories() {
    const el = document.getElementById('cat-pills');
    if (!el) return;
    const cats = this.data.categories || {};
    const qs = this.data.questions || [];
    let html = `<button class="cat-pill ${this.state.category === 'all' ? 'active' : ''}"
                      onclick="QB.setFilter('category','all')">📋 全部 <span class="count">${qs.length}</span></button>`;
    for (const [key, cat] of Object.entries(cats)) {
      const count = qs.filter(q => q.category === key).length;
      if (count === 0) continue;
      html += `<button class="cat-pill ${this.state.category === key ? 'active' : ''}"
                       onclick="QB.setFilter('category','${key}')">${cat.icon || ''} ${cat.name} <span class="count">${count}</span></button>`;
    }
    el.innerHTML = html;
  },

  renderDifficulty() {
    const el = document.getElementById('diff-row');
    if (!el) return;
    const diffs = [
      { key: 'all',  label: '全部', color: '#8b949e' },
      { key: 'easy', label: '基础', color: '#3fb950' },
      { key: 'medium', label: '中级', color: '#d2991d' },
      { key: 'hard', label: '进阶', color: '#f85149' },
    ];
    el.innerHTML = '<span class="label">难度：</span>' + diffs.map(d => `
      <button class="view-btn ${this.state.difficulty === d.key ? 'active' : ''}"
              style="${this.state.difficulty===d.key?`border-color:${d.color};color:${d.color};`:''}"
              onclick="QB.setFilter('difficulty','${d.key}')">
        <span class="diff-dot" style="background:${d.color};"></span>${d.label}
      </button>
    `).join('');
  },

  renderContent() {
    const el = document.getElementById('content');
    if (!el) return;
    const qs = this.getFiltered();
    document.getElementById('search-info').textContent =
      qs.length !== (this.data.questions || []).length ? `筛选结果：${qs.length} 道题` : '';

    if (qs.length === 0) {
      el.innerHTML = `<div class="empty"><div class="empty-icon">📭</div>
        <p>没有匹配的题目</p><p style="font-size:0.85rem;color:var(--text-secondary);">换个筛选条件试试</p></div>`;
      return;
    }

    if (this.state.view === 'daily') {
      this.renderDailyView(qs);
    } else {
      this.renderListView(qs);
    }
  },

  renderListView(qs) {
    const el = document.getElementById('content');
    const todayStr = new Date().toISOString().slice(0, 10);
    const todayReviewed = JSON.parse(localStorage.getItem('reviewed_' + todayStr) || '[]');
    const cats = this.data.categories || {};
    const diffs = { easy: '基础', medium: '中级', hard: '进阶' };

    const cards = qs.map(q => {
      const cat = cats[q.category] || {};
      const diffLabel = diffs[q.difficulty] || q.difficulty;
      const diffColor = { easy: '#3fb950', medium: '#d2991d', hard: '#f85149' }[q.difficulty] || '#888';
      const tags = (q.tags || []).slice(0, 4).map(t => `<span class="card-tag">${t}</span>`).join('');
      const isReviewed = todayReviewed.includes(q.id);

      return `<a href="q/${q.id}.html" class="card">
        <span class="card-id">${q.id}</span>
        <div class="card-body">
          <div class="card-question">${this.esc(q.question)}</div>
          <div class="card-meta">
            <span class="card-cat">${cat.icon || ''} ${cat.name || q.category}</span>
            <span class="card-diff" style="color:${diffColor}">● ${diffLabel}</span>
            <span style="color:var(--text-secondary);font-size:0.72rem;">${q.created ? q.created.slice(0,10) : ''}</span>
          </div>
          <div class="card-tags">${tags}</div>
        </div>
        <span class="card-review ${isReviewed ? '' : 'pending'}">${isReviewed ? '✅' : '○'}</span>
      </a>`;
    }).join('');

    el.innerHTML = `<div class="card-grid">${cards}</div>
      <div style="text-align:center;color:var(--text-secondary);font-size:0.82rem;padding:16px;">共 ${qs.length} 道题</div>`;
  },

  renderDailyView(qs) {
    const el = document.getElementById('content');
    const todayStr = new Date().toISOString().slice(0, 10);
    const yesterdayStr = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    const cats = this.data.categories || {};
    const diffs = { easy: '基础', medium: '中级', hard: '进阶' };

    // 按日期分组
    const groups = {};
    for (const q of qs) {
      const date = (q.created || '').slice(0, 10) || 'unknown';
      if (!groups[date]) groups[date] = [];
      groups[date].push(q);
    }

    const sortedDates = Object.keys(groups).sort().reverse();
    const todayReviewed = JSON.parse(localStorage.getItem('reviewed_' + todayStr) || '[]');

    let html = '';
    for (const date of sortedDates) {
      const qsDate = groups[date];
      let badgeClass = 'date-older', badgeLabel = date;
      if (date === todayStr) { badgeClass = 'date-today'; badgeLabel = '📅 今天'; }
      else if (date === yesterdayStr) { badgeClass = 'date-yesterday'; badgeLabel = '📅 昨天'; }

      html += `<div class="date-group">
        <div class="date-head">
          <span class="date-badge ${badgeClass}">${badgeLabel}</span>
          <span style="font-size:0.8rem;color:var(--text-secondary);">${date} · ${qsDate.length} 题</span>
        </div>
        <div class="card-grid">`;

      for (const q of qsDate) {
        const cat = cats[q.category] || {};
        const diffColor = { easy: '#3fb950', medium: '#d2991d', hard: '#f85149' }[q.difficulty] || '#888';
        const diffLabel = diffs[q.difficulty] || q.difficulty;
        const tags = (q.tags || []).slice(0, 4).map(t => `<span class="card-tag">${t}</span>`).join('');
        const isReviewed = todayReviewed.includes(q.id);

        html += `<a href="q/${q.id}.html" class="card">
          <span class="card-id">${q.id}</span>
          <div class="card-body">
            <div class="card-question">${this.esc(q.question)}</div>
            <div class="card-meta">
              <span class="card-cat">${cat.icon || ''} ${cat.name || q.category}</span>
              <span class="card-diff" style="color:${diffColor}">● ${diffLabel}</span>
            </div>
            <div class="card-tags">${tags}</div>
          </div>
          <span class="card-review ${isReviewed ? '' : 'pending'}">${isReviewed ? '✅ 已复习' : '○ 待复习'}</span>
        </a>`;
      }

      html += `</div></div>`;
    }

    el.innerHTML = html;
  },

  renderTagCloud() {
    const el = document.getElementById('tag-cloud');
    if (!el) return;
    const tags = this.data.top_tags || [];
    if (tags.length === 0) { el.innerHTML = ''; return; }

    const maxCount = Math.max(...tags.map(t => t.count), 1);
    el.innerHTML = tags.map(t => {
      const size = 0.75 + (t.count / maxCount) * 0.9;
      return `<span class="tcloud-item ${this.state.tag===t.tag?'active':''}"
                    style="font-size:${size.toFixed(2)}rem;"
                    onclick="QB.setFilter('tag','${t.tag}')"
                    title="${t.tag} (${t.count}题)">${t.tag}</span>`;
    }).join(' ');
  },

  // ============================================================
  // 交互
  // ============================================================

  setFilter(type, value) {
    if (type === 'category') { this.state.category = value; this.state.tag = null; }
    else if (type === 'difficulty') this.state.difficulty = value;
    else if (type === 'tag') { this.state.tag = value; this.state.category = 'all'; }

    this.renderCategories();
    this.renderDifficulty();
    this.renderContent();
    this.renderTagCloud();
  },

  bindEvents() {
    document.getElementById('search').addEventListener('input', (e) => {
      this.state.search = e.target.value.trim();
      this.renderContent();
    });

    document.querySelectorAll('.view-btn[data-view]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.state.view = btn.dataset.view;
        document.querySelectorAll('.view-btn[data-view]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.renderContent();
      });
    });
  },

  esc(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
};

document.addEventListener('DOMContentLoaded', () => QB.init());
