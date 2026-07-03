/**
 * 学习统计引擎 v2.0
 * ==================
 * 全面的学习数据分析与可视化。
 *
 * 功能模块:
 *   1. 总览统计卡片
 *   2. 学习时间线（按日期排列）
 *   3. 分类详情表（含难度分布和覆盖率）
 *   4. 难度分布进度条
 *   5. 智能学习建议（基于数据分析）
 *   6. 每日复习热力图数据
 */
const Stats = {
  async init() {
    await App.init('stats');
    this.renderAll();
    console.log(`[Stats] ${App.data?.questions?.length || 0} questions analyzed`);
  },

  renderAll() {
    this.renderOverview();
    this.renderTimeline();
    this.renderCategoryDetails();
    this.renderDifficulty();
    this.renderInsights();
    this.renderHeatmapData();
  },

  // ---- 1. 总览 ----
  renderOverview() {
    const el = document.getElementById('overview-stats');
    if (!el) return;
    const qs = App.data?.questions || [];
    const cats = App.data?.categories || {};
    const usedCats = new Set(qs.map(q => q.category)).size;
    const dates = [...new Set(qs.map(q => (q.created || '').slice(0, 10)).filter(Boolean))];
    const streak = App.getStreak();

    // 累计复习人次
    let totalReviewed = 0;
    const today = new Date();
    for (let i = 0; i < 365; i++) {
      const d = new Date(today.getTime() - i * 86400000);
      totalReviewed += App.countReviewed(d.toISOString().slice(0, 10));
    }

    el.innerHTML = App.statCards([
      { value: qs.length, label: '题库总数', color: 'accent', sub: `${usedCats}/${Object.keys(cats).length} 分类`, clickable: true, onclick: "location.href='questions.html'" },
      { value: dates.length, label: '学习天数', color: 'purple', sub: dates.length > 0 ? `${dates[0]} → ${dates[dates.length-1]}` : 'N/A' },
      { value: totalReviewed, label: '累计复习人次', color: 'green', sub: '近一年' },
      { value: streak, label: '当前连续', color: 'orange', sub: '天' },
    ]);
  },

  // ---- 2. 时间线 ----
  renderTimeline() {
    const el = document.getElementById('timeline');
    if (!el) return;
    const qs = App.data?.questions || [];
    const dates = {};

    qs.forEach(q => {
      const d = (q.created || '').slice(0, 10);
      if (!d) return;
      if (!dates[d]) dates[d] = { added: [], reviewed: App.countReviewed(d) };
      dates[d].added.push(q);
    });

    const sorted = Object.entries(dates).sort((a, b) => b[0].localeCompare(a[0])).slice(0, 30);

    if (sorted.length === 0) {
      el.innerHTML = App.emptyState('📅', '暂无时间线数据', '开始答题后这里会显示学习记录');
      return;
    }

    el.innerHTML = sorted.map(([date, data]) => `
      <div class="timeline-item">
        <div class="timeline-dot"></div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-weight:600;">${App.dateLabel(date)}</span>
          <span style="font-size:0.78rem;color:var(--text-3);">${date}</span>
        </div>
        <div style="font-size:0.82rem;color:var(--text-2);margin:4px 0;">
          📝 新增 <strong>${data.added.length}</strong> 题
          ${data.reviewed > 0 ? ` · ✅ 复习 <strong>${data.reviewed}</strong> 题` : ''}
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;">
          ${data.added.slice(0, 4).map(q => `
            <span class="tag tag-accent" style="cursor:pointer;" onclick="location.href='q/${q.id}.html'"
                  title="${App.esc(q.question)}">${App.esc(App.truncate(q.question, 25))}</span>
          `).join('')}
          ${data.added.length > 4 ? `<span style="font-size:0.72rem;color:var(--text-3);">+${data.added.length - 4} 更多</span>` : ''}
        </div>
      </div>
    `).join('');
  },

  // ---- 3. 分类详情 ----
  renderCategoryDetails() {
    const el = document.getElementById('cat-details');
    if (!el) return;
    const qs = App.data?.questions || [];
    const cats = App.data?.categories || {};

    const catStats = {};
    qs.forEach(q => {
      const c = q.category || 'unknown';
      if (!catStats[c]) {
        catStats[c] = { total: 0, easy: 0, medium: 0, hard: 0, tags: new Set(), dates: new Set() };
      }
      catStats[c].total++;
      const diff = q.difficulty || 'medium';
      catStats[c][diff] = (catStats[c][diff] || 0) + 1;
      (q.tags || []).forEach(t => catStats[c].tags.add(t));
      if (q.created) catStats[c].dates.add(q.created.slice(0, 10));
    });

    const entries = Object.entries(catStats).sort((a, b) => b[1].total - a[1].total);
    if (entries.length === 0) { el.innerHTML = App.emptyState('📂', '暂无数据'); return; }

    const maxTotal = Math.max(...entries.map(([, s]) => s.total), 1);

    el.innerHTML = `<div style="overflow-x:auto;"><table class="data-table striped">
      <thead><tr>
        <th>分类</th><th>题数</th><th>覆盖率</th><th>基础</th><th>中级</th><th>进阶</th><th>标签数</th><th>学习天数</th>
      </tr></thead>
      <tbody>${entries.map(([key, s]) => {
        const cat = cats[key] || {};
        const pct = Math.round(s.total / maxTotal * 100);
        return `<tr>
          <td><strong>${cat.icon || ''} ${cat.name || key}</strong></td>
          <td><strong>${s.total}</strong></td>
          <td>
            <span style="display:inline-flex;align-items:center;gap:6px;">
              <div class="progress-bar sm" style="width:60px;"><div class="progress-fill accent" style="width:${pct}%;"></div></div>
              ${pct}%
            </span>
          </td>
          <td><span class="badge badge-green">${s.easy || 0}</span></td>
          <td><span class="badge badge-orange">${s.medium || 0}</span></td>
          <td><span class="badge badge-red">${s.hard || 0}</span></td>
          <td>${s.tags.size}</td>
          <td>${s.dates.size}</td>
        </tr>`;
      }).join('')}</tbody></table></div>`;
  },

  // ---- 4. 难度分布 ----
  renderDifficulty() {
    const el = document.getElementById('diff-dist');
    if (!el) return;
    const qs = App.data?.questions || [];
    const diffs = { easy: 0, medium: 0, hard: 0 };
    qs.forEach(q => { diffs[q.difficulty || 'medium']++; });
    const total = qs.length || 1;

    const bars = [
      { label: '🟢 基础', key: 'easy', count: diffs.easy, color: 'var(--green)' },
      { label: '🟡 中级', key: 'medium', count: diffs.medium, color: 'var(--orange)' },
      { label: '🔴 进阶', key: 'hard', count: diffs.hard, color: 'var(--red)' },
    ];

    el.innerHTML = bars.map(b => {
      const pct = Math.round(b.count / total * 100);
      return `<div style="margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-bottom:4px;">
          <span>${b.label}</span><span>${b.count} 题 (${pct}%)</span>
        </div>
        <div class="progress-bar lg">
          <div class="progress-fill" style="width:${Math.max(pct, 2)}%;background:${b.color};"></div>
        </div>
      </div>`;
    }).join('');

    // 难度分布评价
    const idealDist = total > 0 ? `
      <div class="insight info" style="margin-top:12px;">
        <span class="insight-icon">📊</span>
        理想分布: 基础 40-50% / 中级 30-40% / 进阶 10-20%。
        ${diffs.easy / total > 0.6 ? '基础题偏多，建议增加中级和进阶题目。' :
          diffs.hard / total > 0.4 ? '进阶题偏多，建议补充基础题巩固根基。' :
          '难度分布比较均衡，继续保持！'}
      </div>` : '';
    el.innerHTML += idealDist;
  },

  // ---- 5. 学习建议 ----
  renderInsights() {
    const el = document.getElementById('insights');
    if (!el) return;
    const qs = App.data?.questions || [];
    const todayReviewed = App.countReviewed(App.today);
    const streak = App.getStreak();
    const insights = [];

    // 题库规模
    if (qs.length === 0) {
      insights.push({ type: 'warn', text: '还没有任何题目。使用 /面经助手 开始添加面试题。' });
    } else if (qs.length < 10) {
      insights.push({ type: 'info', text: `题库只有 ${qs.length} 题，建议扩充到 50+ 题以覆盖更多知识点。` });
    } else if (qs.length >= 50) {
      insights.push({ type: 'tip', text: `题库已有 ${qs.length} 题，知识点覆盖良好！` });
    }

    // 复习进度
    if (qs.length > 0) {
      if (todayReviewed === 0) {
        insights.push({ type: 'warn', text: '今天还没开始复习！去每日复习页开始打卡吧 📅' });
      } else if (todayReviewed === qs.length) {
        insights.push({ type: 'tip', text: '🎉 今天全部复习完成！非常棒！' });
      } else {
        const pct = Math.round(todayReviewed / qs.length * 100);
        insights.push({ type: 'info', text: `今日复习进度 ${pct}%，还有 ${qs.length - todayReviewed} 题待复习。` });
      }
    }

    // 连续打卡
    if (streak >= 30) {
      insights.push({ type: 'tip', text: `🔥 ${streak} 天连续打卡！你已经是复习大师了！👑` });
    } else if (streak >= 7) {
      insights.push({ type: 'tip', text: `已连续 ${streak} 天打卡，习惯正在养成！` });
    } else if (streak > 0) {
      insights.push({ type: 'info', text: `当前连续 ${streak} 天，坚持到 7 天养成习惯！` });
    } else {
      insights.push({ type: 'info', text: '今天开始打卡吧！每天复习一点，面试轻松一点。' });
    }

    // 分类覆盖
    const activeCats = new Set(qs.map(q => q.category)).size;
    const totalCats = Object.keys(App.data?.categories || {}).length;
    if (activeCats < totalCats * 0.5) {
      insights.push({ type: 'warn', text: `只覆盖了 ${activeCats}/${totalCats} 个分类，建议扩展知识面。` });
    }

    el.innerHTML = insights.map(i => `
      <div class="insight ${i.type === 'tip' ? 'tip' : i.type === 'warn' ? 'warn' : 'info'}">
        <span class="insight-icon">${i.type === 'tip' ? '💡' : i.type === 'warn' ? '⚠️' : 'ℹ️'}</span>
        <span>${i.text}</span>
      </div>
    `).join('');
  },

  // ---- 6. 热力图数据（控制台输出） ----
  renderHeatmapData() {
    const data = [];
    const today = new Date();
    for (let i = 364; i >= 0; i--) {
      const d = new Date(today.getTime() - i * 86400000);
      const ds = d.toISOString().slice(0, 10);
      const count = App.countReviewed(ds);
      if (count > 0) data.push({ date: ds, count });
    }
    console.log('[Stats] Review heatmap data:', data.length, 'days with activity');
    // 未来可集成到热力图组件
  },
};

document.addEventListener('DOMContentLoaded', () => Stats.init());
