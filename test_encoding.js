const fs = require('fs');
const content = fs.readFileSync('d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\secplan\\admin_general\\mapa2.html', 'utf8');
const sample = content.substring(100, 500);
console.log("Original:", sample);

try {
    const fixed = Buffer.from(sample, 'latin1').toString('utf8');
    console.log("Fixed:", fixed);
} catch (e) {
    console.log("Error:", e);
}
