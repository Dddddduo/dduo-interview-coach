/**
 * 知识图谱引擎 v2.0
 * ==================
 * 从题库自动提取知识点、构建关联网络、展示知识结构。
 *
 * 功能:
 *   - 知识点节点提取（标签→节点，含题目数、分类）
 *   - 关联边计算（同一题中的标签互相连接）
 *   - 核心知识点识别（度中心性 Top N）
 *   - 知识点→题目映射表
 *   - 知识点关联卡片
 *   - 按分类着色
 *
 * 驾驭工程体现：所有分析基于 data.json，纯前端计算，无需后端。
 */
const KG = {
  nodes: [],
  edges: [],
  catColors: {
    java: '#f89820', mysql: '#4479A1', redis: '#DC382D', spring: '#6DB33F',
    distributed: '#00ADD8', os: '#0078D7', network: '#E44D26', python: '#3776AB',
    go: '#00ADD8', behavioral: '#A371F7', 'system-design': '#F85149',
    frontend: '#F7DF1E', devops: '#FC6D26',
  },

  async init() {
    await App.init('knowledge');
    this.generate();
    this.bindEvents();
    console.log(`[Knowledge] ${this.nodes.length} nodes, ${this.edges.length} edges`);
  },

  // ---- 数据提取 ----
  generate() {
    this.nodes = this.extractNodes();
    this.edges = this.extractEdges();
    this.renderAll();
  },

  extractNodes() {
    const qs = App.data?.questions || [];
    const tagMap = {};

    qs.forEach(q => {
      (q.tags || []).forEach(tag => {
        if (!tagMap[tag]) {
          tagMap[tag] = {
            id: tag, name: tag, count: 0, questions: [],
            categories: new Set(), difficulties: { easy: 0, medium: 0, hard: 0 },
          };
        }
        tagMap[tag].count++;
        tagMap[tag].questions.push(q.id);
        tagMap[tag].categories.add(q.category);
        tagMap[tag].difficulties[q.difficulty || 'medium']++;
      });
    });

    const maxCount = Math.max(...Object.values(tagMap).map(n => n.count), 1);
    return Object.values(tagMap).map(n => ({
      ...n,
      categories: [...n.categories],
      size: 10 + (n.count / maxCount) * 30,
      color: this.catColors[n.categories[0]] || '#8b949e',
    })).sort((a, b) => b.count - a.count);
  },

  extractEdges() {
    const qs = App.data?.questions || [];
    const nodeIds = new Set(this.nodes.map(n => n.id));
    const edgeMap = {};

    qs.forEach(q => {
      const tags = (q.tags || []).filter(t => nodeIds.has(t));
      for (let i = 0; i < tags.length; i++) {
        for (let j = i + 1; j < tags.length; j++) {
          const key = [tags[i], tags[j]].sort().join('|||');
          if (!edgeMap[key]) {
            edgeMap[key] = { source: tags[i], target: tags[j], weight: 0, questions: [] };
          }
          edgeMap[key].weight++;
          if (!edgeMap[key].questions.includes(q.id)) {
            edgeMap[key].questions.push(q.id);
          }
        }
      }
    });

    return Object.values(edgeMap).sort((a, b) => b.weight - a.weight);
  },

  // ---- 渲染 ----
  renderAll() {
    this.renderStats();
    this.renderNodes();
    this.renderTopicMap();
    this.renderEdges();
    this.renderWeakAreas();
  },

  renderStats() {
    const el = document.getElementById('kg-stats');
    if (!el) return;
    const coreNodes = this.nodes.filter(n => n.count >= 2).length;
    const strongEdges = this.edges.filter(e => e.weight >= 2).length;

    el.innerHTML = App.statCards([
      { value: this.nodes.length, label: '知识点', color: 'purple', sub: `${coreNodes} 个核心` },
      { value: this.edges.length, label: '关联关系', color: 'accent', sub: `${strongEdges} 个强关联` },
      { value: coreNodes, label: '核心知识点', color: 'orange', sub: '≥2 题' },
      { value: App.data?.questions?.length || 0, label: '题库总数', color: 'green' },
    ]);
  },

  renderNodes() {
    const el = document.getElementById('kg-nodes');
    if (!el) return;
    const topNodes = this.nodes.slice(0, 36);

    el.innerHTML = `<div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;">${topNodes.map(n => `
      <span class="kg-node ${n.count >= 3 ? 'core' : ''}"
            onclick="location.href='questions.html?tag=${encodeURIComponent(n.id)}'"
            title="${n.name}: ${n.count} 题 · ${n.categories.join(', ')}">
        <span class="kg-dot" style="background:${n.color};width:${Math.min(n.size, 24)}px;height:${Math.min(n.size, 24)}px;"></span>
        ${n.name}
        <sup style="opacity:0.7;font-size:0.75em;">${n.count}</sup>
      </span>
    `).join('')}</div>`;
  },

  renderTopicMap() {
    const el = document.getElementById('topic-map');
    if (!el) return;
    const qs = App.data?.questions || [];
    const cats = App.data?.categories || {};

    const tagQuestions = {};
    this.nodes.filter(n => n.count > 0).slice(0, 25).forEach(n => {
      tagQuestions[n.name] = n.questions
        .map(id => qs.find(q => q.id === id))
        .filter(Boolean);
    });

    if (Object.keys(tagQuestions).length === 0) {
      el.innerHTML = App.emptyState('🧠', '暂无知识点数据');
      return;
    }

    el.innerHTML = Object.entries(tagQuestions).map(([tag, questions]) => {
      const node = this.nodes.find(n => n.name === tag);
      const color = node?.color || '#8b949e';

      return `<div class="topic-section">
        <div class="topic-title">
          <span class="kg-dot" style="background:${color};width:10px;height:10px;"></span>
          <span style="font-weight:600;">${tag}</span>
          <span class="badge badge-purple">${questions.length} 题</span>
          ${node?.difficulties ? `<span style="font-size:0.7rem;color:var(--text-3);">
            ${node.difficulties.easy ? '🟢'+node.difficulties.easy : ''}
            ${node.difficulties.medium ? ' 🟡'+node.difficulties.medium : ''}
            ${node.difficulties.hard ? ' 🔴'+node.difficulties.hard : ''}
          </span>` : ''}
        </div>
        <div style="padding-left:18px;">
          ${questions.map(q => {
            if (!q) return '';
            const cat = cats[q.category] || {};
            return `<div style="font-size:0.82rem;padding:3px 0;display:flex;justify-content:space-between;align-items:center;">
              <a href="q/${q.id}.html">[${q.id}] ${App.esc(App.truncate(q.question, 70))}</a>
              <span style="color:var(--text-3);font-size:0.7rem;white-space:nowrap;">${App.diffEmoji(q.difficulty)} ${cat.icon||''}</span>
            </div>`;
          }).join('')}
        </div>
      </div>`;
    }).join('');
  },

  renderEdges() {
    const el = document.getElementById('kg-links');
    if (!el) return;
    const topEdges = this.edges.filter(e => e.weight >= 2).slice(0, 24);

    if (topEdges.length === 0) {
      el.innerHTML = App.emptyState('🔗', '暂无强关联', '题目还不多，多答几道题就会出现关联');
      return;
    }

    el.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;">${topEdges.map(e => `
      <div class="kg-link-card" onclick="location.href='questions.html?tag=${encodeURIComponent(e.source)}'" style="cursor:pointer;">
        <div style="font-weight:600;font-size:0.85rem;">${e.source}</div>
        <div style="text-align:center;color:var(--text-3);margin:4px 0;">↔</div>
        <div style="font-weight:600;font-size:0.85rem;">${e.target}</div>
        <div class="kg-link-weight">${e.weight} 道共同题目</div>
      </div>
    `).join('')}</div>`;
  },

  renderWeakAreas() {
    // 找出已有分类中标签覆盖不足的
    const qs = App.data?.questions || [];
    const activeCats = new Set(qs.map(q => q.category));
    const allCats = App.data?.categories || {};

    const uncovered = Object.entries(allCats)
      .filter(([k]) => !activeCats.has(k))
      .slice(0, 5);

    if (uncovered.length > 0) {
      const el = document.getElementById('kg-links');
      if (el) {
        const note = document.createElement('div');
        note.className = 'insight warn';
        note.style.marginTop = '16px';
        note.innerHTML = `<span class="insight-icon">⚠️</span> 尚未覆盖的分类: ${uncovered.map(([,v]) => v.name || v.icon).join('、')}。建议补充这些领域的题目。`;
        el.parentNode.appendChild(note);
      }
    }
  },

  // ---- 事件 ----
  bindEvents() {
    // 点击节点跳转到题目列表
    document.querySelectorAll('.kg-node').forEach(node => {
      node.addEventListener('click', function(e) {
        const tag = this.textContent.trim().split(/\s/)[0];
        location.href = `questions.html?tag=${encodeURIComponent(tag)}`;
      });
    });
  },
};

document.addEventListener('DOMContentLoaded', () => KG.init());
