/**
 * 仪表盘引擎 v2.0
 * =================
 * 首页仪表盘的全部交互逻辑。
 *
 * 功能模块:
 *   1. 欢迎横幅（问候语 + 打卡状态）
 *   2. 统计卡片（总题数、今日复习、连续打卡、知识点数）
 *   3. 今日复习预览（可交互的快速打卡列表）
 *   4. 分类分布条形图
 *   5. 最近归档列表（支持实时搜索）
 *   6. 知识点标签云
 *   7. 快速搜索（即时过滤）
 */
(async function() {
  await App.init('index');
  const D = App.data;
  if (!D) return;

  const qs = D.questions || [];
  const cats = D.categories || {};
  const todayReviewed = App.getReviewed(App.today);
  const streak = App.getStreak();
  const tagCounts = App.getTagCounts();
  const catCounts = App.getCategoryCounts();

  // ==========================================================
  // 1. 欢迎横幅
  // ==========================================================
  (function renderWelcome() {
    const hour = new Date().getHours();
    const greeting = hour < 6 ? '夜深了，注意休息 🌙' :
                     hour < 9 ? '早上好！新的一天 ☀️' :
                     hour < 12 ? '上午好！精力充沛 💪' :
                     hour < 18 ? '下午好！继续加油 🚀' : '晚上好！今天辛苦了 ✨';

    const tips = [
      `${greeting}。题库共 ${qs.length} 题，今日已复习 ${todayReviewed.length} 题`,
      `${greeting}。连续打卡 ${streak} 天，坚持就是胜利！`,
      `${greeting}。${qs.length > 0 ? `还有 ${qs.length - todayReviewed.length} 题等待复习` : '快去添加题目吧'}`,
      `${greeting}。每天复习一点，面试轻松一点 📝`,
    ];

    const idx = Math.min(streak % tips.length, tips.length - 1);
    const el = document.getElementById('welcome-msg');
    if (el) el.textContent = tips[idx];
  })();

  // ==========================================================
  // 2. 统计卡片
  // ==========================================================
  (function renderStats() {
    const catCount = Object.values(catCounts).filter(c => c > 0).length;
    const tagCount = Object.keys(tagCounts).length;
    const todayPct = qs.length > 0 ? Math.round(todayReviewed.length / qs.length * 100) : 0;

    const stats = [
      { value: qs.length, label: '题库总数', color: 'accent', sub: `${catCount} 个分类`, clickable: true,
        onclick: "location.href='questions.html'" },
      { value: todayReviewed.length, label: '今日已复习', color: 'green', sub: `${todayPct}% 完成`,
        clickable: true, onclick: "location.href='daily.html'" },
      { value: streak, label: '连续打卡', color: 'orange', sub: '天' },
      { value: tagCount, label: '知识点标签', color: 'purple', sub: '个',
        clickable: true, onclick: "location.href='knowledge.html'" },
    ];

    const el = document.getElementById('stat-cards');
    if (el) el.innerHTML = App.statCards(stats);
  })();

  // ==========================================================
  // 3. 今日复习预览
  // ==========================================================
  (function renderReviewPreview() {
    const el = document.getElementById('today-review-preview');
    if (!el) return;

    if (qs.length === 0) {
      el.innerHTML = App.emptyState('📭', '题库还是空的', '使用 /面经助手 开始添加面试题');
      return;
    }

    const unreviewed = qs.filter(q => !todayReviewed.includes(q.id));
    const reviewed = qs.filter(q => todayReviewed.includes(q.id));
    const preview = [...unreviewed.slice(0, 5), ...reviewed.slice(0, 2)].slice(0, 6);

    if (preview.length === 0 && unreviewed.length === 0) {
      el.innerHTML = '<div class="insight tip"><span class="insight-icon">🎉</span> 今日复习全部完成！太棒了！</div>';
      return;
    }

    let html = '<div style="display:flex;flex-direction:column;gap:4px;">';
    preview.forEach(q => {
      const done = todayReviewed.includes(q.id);
      const cat = App.catInfo(q.category);
      html += `<div class="review-item ${done ? 'done' : ''}">
        <div class="review-check ${done ? 'checked' : ''}" data-qid="${q.id}">${done ? '✓' : ''}</div>
        <div class="review-body">
          <div class="review-q"><a href="q/${q.id}.html">${App.esc(q.question)}</a></div>
          <div class="review-meta">${App.diffEmoji(q.difficulty)} ${App.diffName(q.difficulty)} · ${cat.icon || ''} ${cat.name || q.category}</div>
        </div>
        <a href="q/${q.id}.html" class="btn btn-sm btn-ghost">📖</a>
      </div>`;
    });
    html += '</div>';

    if (unreviewed.length > 5) {
      html += `<p style="text-align:center;font-size:0.78rem;color:var(--text-2);margin-top:8px;">
        还有 <strong>${unreviewed.length - 5}</strong> 题待复习...
        <a href="daily.html">去每日复习 →</a>
      </p>`;
    }
    el.innerHTML = html;

    // 绑定打卡事件
    el.querySelectorAll('.review-check').forEach(chk => {
      chk.addEventListener('click', (e) => {
        e.stopPropagation();
        const qid = chk.dataset.qid;
        const added = App.toggleReview(qid);
        chk.classList.toggle('checked', added);
        chk.textContent = added ? '✓' : '';
        chk.closest('.review-item').classList.toggle('done', !added);
        App.toast(added ? '✅ 已标记复习完成' : '⬜ 已取消');
        // 刷新统计
        setTimeout(() => location.reload(), 800);
      });
    });
  })();

  // ==========================================================
  // 4. 分类分布
  // ==========================================================
  (function renderCategoryDist() {
    const el = document.getElementById('cat-distribution');
    if (!el) return;

    const entries = Object.entries(catCounts).filter(([,c]) => c > 0).sort((a, b) => b[1] - a[1]);

    if (entries.length === 0) {
      el.innerHTML = App.emptyState('📊', '暂无分类数据');
      return;
    }

    const maxCount = Math.max(...entries.map(([,c]) => c), 1);
    const colors = ['var(--accent)', 'var(--purple)', 'var(--green)', 'var(--orange)', 'var(--cyan)', 'var(--red)'];

    el.innerHTML = `<div class="bar-chart">${entries.map(([k, count], i) => {
      const cat = App.catInfo(k);
      const pct = Math.round(count / maxCount * 100);
      return `<div class="bar-row">
        <span class="bar-label">${cat.icon || ''} ${cat.name || k}</span>
        <div class="bar-track">
          <div class="bar-fill" style="width:${pct}%;background:${colors[i % colors.length]};">${count}</div>
        </div>
      </div>`;
    }).join('')}</div>`;
  })();

  // ==========================================================
  // 5. 最近归档 + 快速搜索
  // ==========================================================
  (function renderRecent() {
    const el = document.getElementById('recent-questions');
    if (!el) return;

    const recent = [...qs].sort((a, b) => (b.created || '').localeCompare(a.created || '')).slice(0, 10);

    if (recent.length === 0) {
      el.innerHTML = App.emptyState('📝', '暂无题目', '使用 /面经助手 开始添加', '<a href="about.html" class="btn btn-sm btn-secondary">查看使用指南</a>');
      return;
    }

    const renderList = (items) => {
      if (items.length === 0) return App.emptyState('🔍', '无匹配结果', '换个关键词试试');
      return `<div class="q-list">${items.map(q => App.questionCard(q, { showReview: true, maxTags: 3 })).join('')}</div>`;
    };

    el.innerHTML = renderList(recent);

    // 快速搜索
    const searchInput = document.getElementById('quick-search');
    if (!searchInput) return;

    let searchTimer;
    searchInput.addEventListener('input', function() {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        const kw = this.value.trim().toLowerCase();
        if (!kw) { el.innerHTML = renderList(recent); return; }
        const filtered = qs.filter(q =>
          q.question.toLowerCase().includes(kw) ||
          (q.tags || []).some(t => t.toLowerCase().includes(kw)) ||
          (q.category || '').toLowerCase().includes(kw)
        ).slice(0, 10);
        el.innerHTML = renderList(filtered);
      }, 200);
    });
  })();

  // ==========================================================
  // 6. 标签云
  // ==========================================================
  (function renderTagCloud() {
    const el = document.getElementById('tag-cloud-mini');
    if (!el) return;

    const entries = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).slice(0, 40);
    if (entries.length === 0) {
      el.innerHTML = '<span style="color:var(--text-2);font-size:0.85rem;">暂无标签，快去答题吧</span>';
      return;
    }

    const maxCount = Math.max(...entries.map(([,c]) => c), 1);

    el.innerHTML = entries.map(([tag, count]) => {
      const size = 0.7 + (count / maxCount) * 1.2;
      const opacity = 0.5 + (count / maxCount) * 0.5;
      return `<span class="tag" style="font-size:${size.toFixed(2)}rem;opacity:${opacity.toFixed(2)};cursor:pointer;"
                    onclick="location.href='questions.html?tag=${encodeURIComponent(tag)}'"
                    title="${tag}: ${count} 题">${tag}<sup style="font-size:0.65em;opacity:0.6;">${count}</sup></span>`;
    }).join(' ');
  })();

  // ==========================================================
  // 7. 键盘快捷键
  // ==========================================================
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    switch (e.key) {
      case 'd': location.href = 'daily.html'; break;
      case 'q': location.href = 'questions.html'; break;
      case 'k': location.href = 'knowledge.html'; break;
      case 's': location.href = 'stats.html'; break;
      case '/': document.getElementById('quick-search')?.focus(); e.preventDefault(); break;
    }
  });

  console.log('[Dashboard] Ready — Press / to search, d/q/k/s to navigate');
})();
