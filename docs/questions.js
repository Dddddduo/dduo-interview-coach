/**
 * 题库浏览器 — 动态加载、分类、搜索、标签过滤
 * ================================================
 * 从 questions/index.json 加载数据，纯前端渲染。
 */

const QuestionBrowser = {
  data: null,
  activeCategory: 'all',
  activeDifficulty: 'all',
  searchQuery: '',
  activeTag: null,

  async init() {
    await this.loadData();
    this.renderAll();
    this.bindEvents();
  },

  async loadData() {
    try {
      const resp = await fetch('../questions/index.json');
      this.data = await resp.json();
    } catch (e) {
      // GitHub Pages fallback — try relative to docs/
      try {
        const resp = await fetch('index.json');
        this.data = await resp.json();
      } catch (e2) {
        document.getElementById('app').innerHTML =
          '<p style="text-align:center;padding:40px;">⚠️ 题库数据加载失败</p>';
      }
    }
  },

  // ==========================================
  // 过滤逻辑
  // ==========================================

  get filteredQuestions() {
    if (!this.data) return [];
    let qs = this.data.questions || [];
    if (this.activeCategory !== 'all') {
      qs = qs.filter(q => q.category === this.activeCategory);
    }
    if (this.activeDifficulty !== 'all') {
      qs = qs.filter(q => q.difficulty === this.activeDifficulty);
    }
    if (this.activeTag) {
      qs = qs.filter(q => (q.tags || []).includes(this.activeTag));
    }
    if (this.searchQuery) {
      const kw = this.searchQuery.toLowerCase();
      qs = qs.filter(q =>
        q.question.toLowerCase().includes(kw) ||
        (q.tags || []).some(t => t.toLowerCase().includes(kw)) ||
        (q.category || '').toLowerCase().includes(kw)
      );
    }
    return qs;
  },

  // ==========================================
  // 渲染
  // ==========================================

  renderAll() {
    this.renderStats();
    this.renderCategoryNav();
    this.renderQuestionList();
    this.renderTagCloud();
  },

  renderStats() {
    const meta = this.data.meta || {};
    const qs = this.data.questions || [];
    const cats = this.data.categories || {};
    const el = document.getElementById('stats');
    if (!el) return;

    const catCount = Object.keys(cats).length;
    const tagCount = new Set(qs.flatMap(q => q.tags || [])).size;

    el.innerHTML = `
      <div class="stat-card">
        <div class="stat-num">${qs.length}</div>
        <div class="stat-label">总题数</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">${catCount}</div>
        <div class="stat-label">分类</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">${tagCount}</div>
        <div class="stat-label">标签</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">${meta.last_updated ? meta.last_updated.slice(0,10) : 'N/A'}</div>
        <div class="stat-label">最近更新</div>
      </div>
    `;
  },

  renderCategoryNav() {
    const cats = this.data.categories || {};
    const el = document.getElementById('category-nav');
    if (!el) return;

    const total = (this.data.questions || []).length;
    let html = `<button class="cat-btn ${this.activeCategory === 'all' ? 'active' : ''}"
                      onclick="QuestionBrowser.selectCategory('all')">
                  📋 全部 <span class="count">${total}</span>
                </button>`;

    for (const [key, cat] of Object.entries(cats)) {
      const count = (this.data.questions || []).filter(q => q.category === key).length;
      if (count === 0) continue;
      html += `<button class="cat-btn ${this.activeCategory === key ? 'active' : ''}"
                       onclick="QuestionBrowser.selectCategory('${key}')">
                 ${cat.icon || '📌'} ${cat.name} <span class="count">${count}</span>
               </button>`;
    }

    el.innerHTML = html;
  },

  renderQuestionList() {
    const el = document.getElementById('question-list');
    if (!el) return;

    const qs = this.filteredQuestions;
    const diffs = this.data.difficulty_levels || {};
    const cats = this.data.categories || {};

    if (qs.length === 0) {
      el.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📭</div>
          <p>还没有题目，快去答题吧！</p>
          <p style="font-size:0.85rem;color:var(--text-secondary);">
            运行 <code>/面经助手</code> 或 <code>python scripts/interview_agent.py "题目"</code>
          </p>
        </div>`;
      return;
    }

    // 难度筛选按钮
    const diffFilter = `
      <div class="diff-filter">
        <span style="color:var(--text-secondary);font-size:0.85rem;">难度：</span>
        <button class="diff-btn ${this.activeDifficulty === 'all' ? 'active' : ''}"
                onclick="QuestionBrowser.selectDifficulty('all')">全部</button>
        ${Object.entries(diffs).map(([k, v]) => `
          <button class="diff-btn ${this.activeDifficulty === k ? 'active' : ''}"
                  style="color:${v.color};${this.activeDifficulty===k?`border-color:${v.color};background:${v.color}22;`:''}"
                  onclick="QuestionBrowser.selectDifficulty('${k}')">${v.name}</button>
        `).join('')}
        ${this.activeTag ? `<span style="margin-left:12px;font-size:0.85rem;">
          🏷️ <code style="cursor:pointer;color:var(--accent);" onclick="QuestionBrowser.clearTag()">${this.activeTag} ✕</code>
        </span>` : ''}
      </div>`;

    const cards = qs.map(q => {
      const cat = cats[q.category] || {};
      const diff = diffs[q.difficulty] || {};
      const tags = (q.tags || []).map(t =>
        `<span class="tag" onclick="QuestionBrowser.filterByTag('${t}')">${t}</span>`
      ).join('');

      return `
        <div class="question-card">
          <div class="qc-header">
            <span class="qc-id">${q.id}</span>
            <span class="qc-cat">${cat.icon || ''} ${cat.name || q.category}</span>
            <span class="qc-diff" style="color:${diff.color || '#888'}">● ${diff.name || q.difficulty}</span>
            ${q.created ? `<span class="qc-date">${q.created.slice(0,10)}</span>` : ''}
          </div>
          <div class="qc-question">${this.escapeHtml(q.question)}</div>
          <div class="qc-tags">${tags}</div>
          ${q.file ? `<div class="qc-file">📄 <a href="../${q.file}" target="_blank">查看完整答案</a></div>` : ''}
        </div>`;
    }).join('');

    el.innerHTML = diffFilter + `<div class="question-cards">${cards}</div>
      <div class="result-count">共 ${qs.length} 道题</div>`;
  },

  renderTagCloud() {
    const el = document.getElementById('tag-cloud');
    if (!el) return;

    const tagCounts = {};
    for (const q of (this.data.questions || [])) {
      for (const t of (q.tags || [])) {
        tagCounts[t] = (tagCounts[t] || 0) + 1;
      }
    }

    const maxCount = Math.max(...Object.values(tagCounts), 1);
    const tags = Object.entries(tagCounts)
      .sort((a, b) => b[1] - a[1]);

    el.innerHTML = tags.map(([tag, count]) => {
      const size = 0.75 + (count / maxCount) * 1.0;
      const opacity = 0.5 + (count / maxCount) * 0.5;
      return `<span class="tag-cloud-item"
                    style="font-size:${size.toFixed(2)}rem;opacity:${opacity.toFixed(2)};"
                    onclick="QuestionBrowser.filterByTag('${tag}')"
                    title="${tag} (${count}题)">${tag}</span>`;
    }).join(' ');
  },

  // ==========================================
  // 事件
  // ==========================================

  bindEvents() {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.trim();
        this.renderQuestionList();
      });
    }
  },

  selectCategory(cat) {
    this.activeCategory = cat;
    this.activeTag = null;
    this.renderCategoryNav();
    this.renderQuestionList();
  },

  selectDifficulty(diff) {
    this.activeDifficulty = diff;
    this.renderQuestionList();
  },

  filterByTag(tag) {
    this.activeTag = tag;
    this.activeCategory = 'all';
    this.activeDifficulty = 'all';
    this.renderCategoryNav();
    this.renderQuestionList();
  },

  clearTag() {
    this.activeTag = null;
    this.renderQuestionList();
  },

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
};

// 启动
document.addEventListener('DOMContentLoaded', () => QuestionBrowser.init());
