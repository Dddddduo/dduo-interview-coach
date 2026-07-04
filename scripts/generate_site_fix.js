/**
 * Generate site data for GitHub Pages
 * Replaces generate_site.py when Python is not available
 */
const fs = require('fs');
const path = require('path');

const INDEX_FILE = 'questions/index.json';
const DOCS_DIR = 'docs';
const OUTPUT_HTML_DIR = 'docs/q';

// Read index
const index = JSON.parse(fs.readFileSync(INDEX_FILE, 'utf-8'));

// Ensure output dir exists
if (!fs.existsSync(OUTPUT_HTML_DIR)) {
    fs.mkdirSync(OUTPUT_HTML_DIR, { recursive: true });
}

// Copy index.json to docs/
fs.writeFileSync(path.join(DOCS_DIR, 'index.json'), JSON.stringify(index, null, 2), 'utf-8');
console.log('Copied index.json to docs/');

// Update data.json
const dataPath = path.join(DOCS_DIR, 'data.json');
let data;
try {
    let raw = fs.readFileSync(dataPath, 'utf-8').trim();
    // Fix potential trailing issue
    data = JSON.parse(raw);
} catch (e) {
    console.log('data.json parse error, creating new:', e.message);
    data = {
        meta: {},
        total: 0,
        categories: index.categories,
        difficulty_levels: index.difficulty_levels || {},
        questions: []
    };
}

data.meta = index.meta;
data.total = index.meta.total_questions;
data.questions = index.questions;
for (const cat in data.categories) {
    if (index.categories[cat]) {
        data.categories[cat].count = index.categories[cat].count;
    }
}
fs.writeFileSync(dataPath, JSON.stringify(data, null, 2), 'utf-8');
console.log('Updated data.json with ' + data.questions.length + ' questions');

// Generate HTML for each question
const diffMap = { easy: '基础', medium: '中级', hard: '进阶' };
const catMap = {};
for (const c in index.categories) {
    catMap[c] = index.categories[c].name || c;
}

for (const entry of index.questions) {
    const mdFile = entry.file;
    if (!fs.existsSync(mdFile)) {
        console.log('File not found: ' + mdFile);
        continue;
    }

    let md = fs.readFileSync(mdFile, 'utf-8');

    // Remove frontmatter
    md = md.replace(/^---\n[\s\S]*?\n---\n\n/, '');
    // Remove the first heading (title)
    md = md.replace(/^# .*\n\n/, '');

    // Simple markdown to HTML
    let html = '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n' +
        '<meta charset="UTF-8">\n' +
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n' +
        '<title>' + escapeHtml(entry.question) + ' - 面经题库</title>\n' +
        '<link rel="stylesheet" href="../css/question.css">\n' +
        '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">\n' +
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>\n' +
        '<script>hljs.highlightAll();</script>\n' +
        '</head>\n<body>\n' +
        '<div class="question-container">\n' +
        '<div class="question-header">\n' +
        '<span class="question-id">' + entry.id + '</span>\n' +
        '<h1>' + escapeHtml(entry.question) + '</h1>\n' +
        '<div class="question-meta">\n' +
        '<span class="difficulty ' + entry.difficulty + '">' + (diffMap[entry.difficulty] || entry.difficulty) + '</span>\n' +
        '<span class="category">' + (catMap[entry.category] || entry.category) + '</span>\n' +
        '<span class="tags">' + (entry.tags || []).map(t => '<span class="tag">' + escapeHtml(t) + '</span>').join(' ') + '</span>\n' +
        '</div>\n</div>\n' +
        '<div class="question-content markdown-body">\n' +
        mdToHtml(md) +
        '\n</div>\n</div>\n</body>\n</html>';

    const htmlFile = path.join(OUTPUT_HTML_DIR, entry.id + '.html');
    fs.writeFileSync(htmlFile, html, 'utf-8');
    console.log('Generated: ' + htmlFile);
}

console.log('Site generation complete!');

function escapeHtml(text) {
    return text.replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function mdToHtml(text) {
    // Escape HTML
    text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // Code blocks
    text = text.replace(/```(\w*)\n([\s\S]*?)```/g, (m, lang, code) => {
        return '<pre><code class="language-' + lang + '">' + code + '</code></pre>';
    });

    // Inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic
    text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Headings
    text = text.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    text = text.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    text = text.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // HR
    text = text.replace(/^---$/gm, '<hr>');

    // Tables
    text = text.replace(/\|(.+)\|\n\|[-| ]+\|\n((?:\|.+\|\n?)*)/g, (m, header, body) => {
        const headerCells = header.split('|').map(c => c.trim()).filter(Boolean);
        const bodyRows = body.trim().split('\n');
        let tableHtml = '<table><thead><tr>';
        headerCells.forEach(c => { tableHtml += '<th>' + c + '</th>'; });
        tableHtml += '</tr></thead><tbody>';
        bodyRows.forEach(row => {
            const cells = row.split('|').map(c => c.trim()).filter(Boolean);
            if (cells.length > 0) {
                tableHtml += '<tr>';
                cells.forEach(c => { tableHtml += '<td>' + c + '</td>'; });
                tableHtml += '</tr>';
            }
        });
        tableHtml += '</tbody></table>';
        return tableHtml;
    });

    // Unordered lists
    text = text.replace(/^- (.+)$/gm, '<li>$1</li>');
    text = text.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');

    // Ordered lists
    text = text.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Paragraphs
    text = text.replace(/\n\n/g, '</p><p>');

    // Line breaks
    text = text.replace(/\n/g, '<br>');

    return '<p>' + text + '</p>';
}
