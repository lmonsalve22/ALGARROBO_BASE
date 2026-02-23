const fs = require('fs');
const path = require('path');

const vistasDir = 'vistas2';

if (!fs.existsSync(vistasDir)) {
    console.error('Directory not found:', vistasDir);
    process.exit(1);
}

const files = fs.readdirSync(vistasDir);

files.forEach(file => {
    if (!file.endsWith('.html') || !file.startsWith('vista')) return;

    const filePath = path.join(vistasDir, file);
    let content = fs.readFileSync(filePath, 'utf8');

    const match = file.match(/vista(\d+)/);
    if (!match) return;
    const vid = match[1];
    const spanId = `v${vid}_ia_analysis`;

    // Remove old block (aggressively to clean up old ones)
    // We remove any alert--info div that contains the specific id OR just any generic ia_analysis id to be safe
    // But be careful not to remove OTHER alert--infos.
    // We target the specific span id pattern.
    const oldBlockRegex = /<div class="alert alert--info"[\s\S]*?id="v\d+_ia_analysis"[\s\S]*?<\/div>/g;
    content = content.replace(oldBlockRegex, '');

    // Also remove any previous injection that might have used a different ID format if necessary
    // For now, assume consistent ID format v{N}_ia_analysis

    // New Block
    const newBlock = `
<div class="alert alert--info" style="margin-top: 1.5rem;">
    <strong>🤖 Análisis de Situación:</strong> <span id="${spanId}">Cargando análisis...</span>
</div>`;

    // Insert after question-section
    // We assume question-section ends with </div> and is followed by either <div class="cards-grid"> or similar.
    // We search for <div class="question-section" ...> ... </div>
    // To match until the closing div, we rely on indentation or structure.
    // The question-section usually ends line 21 in vista1.html.

    const qsStart = content.indexOf('<div class="question-section"');
    if (qsStart === -1) {
        console.warn(`Skipping ${file} (No question-section)`);
        return;
    }

    // Find the closing div of question-section.
    // Since question-section contains only h2 and p (no divs), the first </div> after qsStart is the closing one.
    const qsEnd = content.indexOf('</div>', qsStart);
    if (qsEnd === -1) {
        console.warn(`Skipping ${file} (No closing div for question-section)`);
        return;
    }

    // Insert after the closing div
    const before = content.substring(0, qsEnd + 6); // +6 for </div>
    const after = content.substring(qsEnd + 6);

    const newContent = before + '\n' + newBlock + after;

    fs.writeFileSync(filePath, newContent, 'utf8');
    console.log(`Updated ${file}`);
});
