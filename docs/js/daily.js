/**
 * 每日复习引擎 v2.0
 * ==================
 * 完整的每日复习工作流：进度追踪、30 天月历、分类筛选复习、一键全标记、
 * 复习笔记（日记条目）、今日摘要、连续打卡激励。
 *
 * localStorage 数据结构:
 *   reviewed_YYYY-MM-DD: ["q0001", "q0002", ...]
 *   daily_notes_YYYY-MM-DD: "今天的复习笔记..."
 */
const DR = {
  async init() {
    await App.init('daily');
    this.renderAll();
    this.bindKeyboard();
  },

  renderAll() {
    this.renderStats();
    this.renderProgress();
    this.renderCalendar();
    this.renderReviewList();
    this.renderQuickActions();
    this.renderDailyNote();
    this.updatePageTitle();
  },

  // ---- 更新页面标题 ----
  updatePageTitle() {
    const todayReviewed = App.countReviewed(App.today);
    const total = (App.data?.questions || []).length;
    document.title = `每日复习 (${todayReviewed}/${total}) — Interview Coach`;
  },

  // ---- 统计卡片 ----
  renderStats() {
    const el = document.getElementById('daily-stats');
    if (!el) return;
    const todayReviewed = App.countReviewed(App.today);
    const streak = App.getStreak();
    const total = (App.data?.questions || []).length;
    const remaining = total - todayReviewed;
    const yesterdayReviewed = App.countReviewed(
      new Date(Date.now() - 86400000).toISOString().slice(0, 10)
    );

    el.innerHTML = App.statCards([
      { value: todayReviewed, label: '今日已复习', color: 'green', sub: `共 ${total} 题 · ${Math.round(todayReviewed/Math.max(total,1)*100)}%` },
      { value: remaining, label: '剩余待复习', color: 'accent', sub: remaining === 0 ? '全部完成！🎉' : '继续加油' },
      { value: streak, label: '连续打卡', color: 'orange', sub: '天' },
      { value: yesterdayReviewed, label: '昨日复习', color: 'purple', sub: '题', clickable: true },
    ]);
  },

  // ---- 进度条 ----
  renderProgress() {
    const total = (App.data?.questions || []).length;
    const done = App.countReviewed(App.today);
    const pct = total > 0 ? Math.round(done / total * 100) : 0;

    const progLabel = document.getElementById('prog-label');
    const progPct = document.getElementById('prog-pct');
    const progFill = document.getElementById('prog-fill');

    if (progLabel) progLabel.textContent = `${done} / ${total} 题`;
    if (progPct) progPct.textContent = `${pct}%`;
    if (progFill) {
      progFill.style.width = `${pct}%`;
      if (pct >= 100) progFill.style.background = 'var(--green)';
      else if (pct >= 50) progFill.style.background = 'linear-gradient(90deg, var(--green), var(--accent))';
      else progFill.style.background = 'var(--accent)';
    }
  },

  // ---- 30 天月历 ----
  renderCalendar() {
    const el = document.getElementById('cal-mini');
    if (!el) return;
    const today = new Date();
    let html = '';

    for (let i = 29; i >= 0; i--) {
      const d = new Date(today.getTime() - i * 86400000);
      const ds = d.toISOString().slice(0, 10);
      const reviewedCount = App.countReviewed(ds);
      const isToday = ds === App.today;

      let cls = 'cal-day';
      let title = ds;
      if (isToday) { cls += ' today'; title = '今天'; }
      else if (reviewedCount > 0) cls += ' done';
      else if (ds < App.today) cls += ' miss';

      if (reviewedCount > 0) title += ` · ${reviewedCount} 题`;

      html += `<div class="${cls}" title="${title}" ${isToday ? '' : `onclick="DR.showDateDetail('${ds}')"`}>${d.getDate()}</div>`;
    }
    el.innerHTML = html;
  },

  showDateDetail(dateStr) {
    const reviewed = App.getReviewed(dateStr);
    App.toast(`${dateStr}: 复习了 ${reviewed.length} 题`, 'info');
  },

  // ---- 复习清单 ----
  renderReviewList() {
    const el = document.getElementById('review-list');
    if (!el) return;

    const qs = App.data?.questions || [];
    const todayReviewed = App.getReviewed(App.today);

    if (qs.length === 0) {
      el.innerHTML = App.emptyState('📭', '题库为空', '先用 /面经助手 添加题目吧');
      return;
    }

    const unreviewed = qs.filter(q => !todayReviewed.includes(q.id));
    const reviewed = qs.filter(q => todayReviewed.includes(q.id));

    let html = '';

    // 未复习区域
    if (unreviewed.length > 0) {
      html += `<div class="date-group">
        <div class="date-head">
          <span>⬜ 待复习</span>
          <span class="date-badge date-today">${unreviewed.length} 题</span>
        </div>`;
      html += unreviewed.map(q => this.buildReviewItem(q, false)).join('');
      html += '</div>';
    } else if (qs.length > 0) {
      html += '<div class="insight tip"><span class="insight-icon">🎉</span> 全部复习完成！今天太棒了！继续保持！</div>';
    }

    // 已复习区域
    if (reviewed.length > 0) {
      html += `<div class="date-group">
        <div class="date-head">
          <span>✅ 已复习</span>
          <span class="date-badge" style="background:var(--green-bg);color:var(--green);">${reviewed.length} 题</span>
        </div>`;
      html += reviewed.map(q => this.buildReviewItem(q, true)).join('');
      html += '</div>';
    }

    el.innerHTML = html;

    // 绑定打卡事件
    el.querySelectorAll('.review-check[data-qid]').forEach(chk => {
      chk.addEventListener('click', () => {
        const qid = chk.dataset.qid;
        const added = App.toggleReview(qid);
        this.renderAll();
        App.toast(added ? '✅ 已标记复习完成' : '⬜ 已取消标记');
      });
    });
  },

  buildReviewItem(q, done) {
    const cat = App.catInfo(q.category);
    return `<div class="review-item ${done ? 'done' : ''}">
      <div class="review-check ${done ? 'checked' : ''}" data-qid="${q.id}">${done ? '✓' : ''}</div>
      <div class="review-body">
        <div class="review-q"><a href="q/${q.id}.html">${App.esc(q.question)}</a></div>
        <div class="review-meta">
          ${cat.icon || ''} ${cat.name || q.category} ·
          ${App.diffEmoji(q.difficulty)} ${App.diffName(q.difficulty)}
          ${q.created ? ' · ' + App.formatDate(q.created.slice(0, 10)) : ''}
        </div>
      </div>
      <div class="review-link">
        <a href="q/${q.id}.html" class="btn btn-sm btn-ghost" title="查看答案">📖</a>
      </div>
    </div>`;
  },

  // ---- 快捷操作 ----
  renderQuickActions() {
    // 按钮已在 HTML 中
  },

  markAll() {
    const qs = App.data?.questions || [];
    if (qs.length === 0) { App.toast('题库为空', 'warn'); return; }
    if (!confirm(`确定要标记全部 ${qs.length} 题为已复习吗？`)) return;

    const allIds = qs.map(q => q.id);
    App.setReviewed(App.today, allIds);
    this.renderAll();
    App.toast(`✅ 已标记全部 ${allIds.length} 题为复习完成`);
  },

  // ---- 每日笔记 ----
  renderDailyNote() {
    const noteKey = 'daily_notes_' + App.today;
    const saved = localStorage.getItem(noteKey) || '';

    // 找到或创建笔记区域
    let noteEl = document.getElementById('daily-note-section');
    if (!noteEl) {
      const reviewList = document.getElementById('review-list');
      if (!reviewList) return;
      noteEl = document.createElement('div');
      noteEl.id = 'daily-note-section';
      noteEl.innerHTML = `
        <div class="card" style="margin-top:20px;">
          <div class="card-header"><span class="card-title">📝 今日笔记</span></div>
          <div class="card-body">
            <textarea class="input" id="daily-note-input" placeholder="记录今天的复习心得、遇到的困难、明日计划..." style="min-height:100px;">${saved}</textarea>
            <div style="margin-top:8px;display:flex;justify-content:flex-end;">
              <button class="btn btn-sm btn-primary" id="save-note-btn">💾 保存笔记</button>
            </div>
            <p id="note-saved-msg" style="font-size:0.75rem;color:var(--green);margin-top:4px;display:none;">✅ 已保存</p>
          </div>
        </div>`;
      reviewList.parentNode.insertBefore(noteEl, reviewList.nextSibling);

      document.getElementById('save-note-btn').addEventListener('click', () => {
        const text = document.getElementById('daily-note-input').value;
        localStorage.setItem(noteKey, text);
        const msg = document.getElementById('note-saved-msg');
        msg.style.display = 'block';
        setTimeout(() => { msg.style.display = 'none'; }, 2000);
      });
    }
  },

  // ---- 键盘快捷键 ----
  bindKeyboard() {
    document.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      switch (e.key) {
        case 'm': this.markAll(); break;
        case 'i': location.href = 'index.html'; break;
        case 'q': location.href = 'questions.html'; break;
        case 'k': location.href = 'knowledge.html'; break;
      }
    });
  },
};

document.addEventListener('DOMContentLoaded', () => DR.init());
