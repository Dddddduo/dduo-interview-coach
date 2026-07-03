/**
 * 题库浏览器引擎 v2.0
 * =====================
 * 全功能题库浏览器：列表/日期分组/紧凑三视图、分类筛选、难度过滤、
 * 全文搜索、标签过滤、排序、URL参数同步。
 *
 * URL 参数支持: ?cat=java&tag=JVM&diff=medium&search=B+树&view=daily
 */
const QB = {
  view: 'list',
  category: 'all',
  difficulty: 'all',
  search: '',
  tag: null,
  sort: 'newest',

  async init() {
    await App.init('questions');
    this.readUrlParams();
    this.renderAll();
    this.bindAll();
  },

  // ---- URL 参数 ----
  readUrlParams() {
    const p = new URLSearchParams(window.location.search);
    if (p.get('cat')) this.category = p.get('cat');
    if (p.get('tag')) this.tag = p.get('tag');
    if (p.get('diff')) this.difficulty = p.get('diff');
    if (p.get('search')) this.search = p.get('search');
    if (p.get('view')) this.view = p.get('view');
    if (p.get('sort')) this.sort = p.get('sort');
  },

  writeUrlParams() {
    const p = new URLSearchParams();
    if (this.category !== 'all') p.set('cat', this.category);
    if (this.tag) p.set('tag', this.tag);
    if (this.difficulty !== 'all') p.set('diff', this.difficulty);
    if (this.search) p.set('search', this.search);
    if (this.view !== 'list') p.set('view', this.view);
    if (this.sort !== 'newest') p.set('sort', this.sort);
    const qs = p.toString();
    window.history.replaceState({}, '', qs ? '?' + qs : window.location.pathname);
  },

  // ---- 获取过滤后题目 ----
  getQuestions() {
    let qs = [...(App.data?.questions || [])];
    if (this.category !== 'all') qs = qs.filter(q => q.category === this.category);
    if (this.difficulty !== 'all') qs = qs.filter(q => q.difficulty === this.difficulty);
    if (this.tag) qs = qs.filter(q => (q.tags || []).includes(this.tag));
    if (this.search) {
      const kw = this.search.toLowerCase();
      qs = qs.filter(q =>
        q.question.toLowerCase().includes(kw) ||
        (q.tags || []).some(t => t.toLowerCase().includes(kw)) ||
        (q.category || '').toLowerCase().includes(kw)
      );
    }
    // 排序
    switch (this.sort) {
      case 'oldest': qs.sort((a, b) => (a.created || '').localeCompare(b.created || '')); break;
      case 'difficulty': {
        const order = { easy: 0, medium: 1, hard: 2 };
        qs.sort((a, b) => (order[a.difficulty] || 1) - (order[b.difficulty] || 1));
        break;
      }
      case 'category': qs.sort((a, b) => (a.category || '').localeCompare(b.category || '')); break;
      default: qs.sort((a, b) => (b.created || '').localeCompare(a.created || '')); break;
    }
    return qs;
  },

  // ---- 渲染全部 ----
  renderAll() {
    this.renderStats();
    this.renderCategories();
    this.renderDifficultyFilter();
    this.renderContent();
    this.writeUrlParams();
  },

  renderStats() {
    const el = document.getElementById('browser-stats');
    if (!el) return;
    const qs = this.getQuestions();
    const total = (App.data?.questions || []).length;
    el.innerHTML = App.statCards([
      { value: qs.length, label: '筛选结果', color: 'accent', sub: `共 ${total} 题` },
      { value: new Set(qs.map(q => q.category)).size, label: '分类数', color: 'purple' },
      { value: new Set(qs.flatMap(q => q.tags || [])).size, label: '标签数', color: 'green' },
    ]);
  },

  renderCategories() {
    const el = document.getElementById('cat-pills');
    if (!el) return;
    const cats = App.data?.categories || {};
    const total = (App.data?.questions || []).length;
    const catCounts = App.getCategoryCounts();

    let html = `<span class="pill ${this.category === 'all' ? 'active' : ''}" onclick="QB.setFilter('category','all')">📋 全部 <span class="count">${total}</span></span>`;
    for (const [key, cat] of Object.entries(cats)) {
      const count = catCounts[key] || 0;
      if (count === 0) continue;
      html += `<span class="pill ${this.category === key ? 'active' : ''}" onclick="QB.setFilter('category','${key}')">${cat.icon || ''} ${cat.name} <span class="count">${count}</span></span>`;
    }
    el.innerHTML = html;
  },

  renderDifficultyFilter() {
    const el = document.getElementById('diff-pills');
    if (!el) return;
    const diffs = [
      { key: 'all', label: '全部', color: '#8b949e' },
      { key: 'easy', label: '🟢 基础', color: 'var(--green)' },
      { key: 'medium', label: '🟡 中级', color: 'var(--orange)' },
      { key: 'hard', label: '🔴 进阶', color: 'var(--red)' },
    ];
    el.innerHTML = diffs.map(d => `
      <button class="btn btn-sm ${this.difficulty === d.key ? '' : 'btn-ghost'}"
              style="${this.difficulty === d.key ? `border-color:${d.color};color:${d.color};` : ''}"
              onclick="QB.setFilter('difficulty','${d.key}')">${d.label}</button>
    `).join('');
  },

  renderContent() {
    const qs = this.getQuestions();
    document.getElementById('result-count').textContent = qs.length !== (App.data?.questions||[]).length ? `筛选到 ${qs.length} 题` : '';

    if (qs.length === 0) {
      document.getElementById('question-content').innerHTML = App.emptyState('🔍', '无匹配结果', '调整筛选条件或搜索词');
      return;
    }

    switch (this.view) {
      case 'daily': this.renderDaily(qs); break;
      case 'compact': this.renderCompact(qs); break;
      default: this.renderList(qs); break;
    }
  },

  renderList(qs) {
    document.getElementById('question-content').innerHTML =
      `<div class="q-list">${qs.map(q => App.questionCard(q, { showReview: true, showActions: true })).join('')}</div>
       <div style="text-align:center;color:var(--text-2);font-size:0.82rem;padding:12px;">共 ${qs.length} 道题</div>`;
  },

  renderDaily(qs) {
    const groups = {};
    qs.forEach(q => {
      const d = (q.created || '').slice(0, 10) || 'unknown';
      if (!groups[d]) groups[d] = [];
      groups[d].push(q);
    });
    const sorted = Object.keys(groups).sort().reverse();
    let html = '';
    sorted.forEach(date => {
      const items = groups[date];
      html += `<div class="date-group"><div class="date-head">
        <span class="date-badge ${date===App.today?'date-today':(date===new Date(Date.now()-86400000).toISOString().slice(0,10)?'date-yesterday':'date-older')}">${App.dateLabel(date)}</span>
        <span style="font-size:0.8rem;color:var(--text-2);">${date} · ${items.length} 题</span>
      </div><div class="q-list">${items.map(q => App.questionCard(q, { compact: true, showReview: true })).join('')}</div></div>`;
    });
    document.getElementById('question-content').innerHTML = html;
  },

  renderCompact(qs) {
    document.getElementById('question-content').innerHTML =
      `<div class="q-list">${qs.map(q => App.questionCard(q, { compact: true, maxTags: 2 })).join('')}</div>
       <div style="text-align:center;color:var(--text-2);font-size:0.82rem;padding:12px;">共 ${qs.length} 道题</div>`;
  },

  // ---- 过滤器 ----
  setFilter(type, value) {
    if (type === 'category') { this.category = value; this.tag = null; }
    else if (type === 'difficulty') this.difficulty = value;
    else if (type === 'tag') { this.tag = value; this.category = 'all'; }
    this.renderAll();
  },

  // ---- 事件绑定 ----
  bindAll() {
    // 搜索
    let timer;
    document.getElementById('search-input')?.addEventListener('input', e => {
      clearTimeout(timer);
      timer = setTimeout(() => { this.search = e.target.value.trim(); this.renderContent(); this.writeUrlParams(); }, 250);
    });
    // 搜索框预填
    if (this.search) document.getElementById('search-input').value = this.search;

    // 视图切换
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.view = btn.dataset.view;
        this.renderContent();
        this.writeUrlParams();
      });
      if (btn.dataset.view === this.view) btn.classList.add('active');
    });

    // 排序
    document.getElementById('sort-select')?.addEventListener('change', e => {
      this.sort = e.target.value;
      this.renderContent();
      this.writeUrlParams();
    });
    if (document.getElementById('sort-select')) document.getElementById('sort-select').value = this.sort;
  },
};

document.addEventListener('DOMContentLoaded', () => QB.init());
