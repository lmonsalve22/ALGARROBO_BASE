const fs = require('fs');

const filesToFix = [
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\secplan\\admin_general\\mapa2.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\seguridad\\admin_general\\vistas2\\vista11.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\seguridad\\admin_general\\vistas2\\vista10.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\seguridad\\admin_general\\vistas2\\vista17.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\seguridad\\admin_general\\vistas2\\vista16.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\seguridad\\admin_general\\vistas2\\vista19.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\seguridad\\admin_general\\vistas2\\vista15.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\seguridad\\admin_general\\vistas2\\vista18.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\seguridad\\admin_general\\vistas2\\vista14.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\seguridad\\admin_general\\vistas2\\vista13.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\seguridad\\admin_general\\vistas2\\vista12.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\secplan\\admin_general\\user.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\secplan\\admin_general\\header.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\secplan\\admin_general\\chat.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\secplan\\admin_general\\calendario.html",
    "d:\\GitHub\\ALGARROBO_BASE\\frontend\\division\\secplan\\admin_general\\analisis.html"
];

const replaces = {
    'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
    'Ã±': 'ñ', 'Ã‘': 'Ñ',
    'Ã ': 'Á', 'Ã‰': 'É', 'Ã ': 'Í', 'Ã“': 'Ó', 'Ãš': 'Ú',
    'Â¿': '¿', 'Â¡': '¡', 'Âº': 'º', 'Â°': '°',
    'Ã¼': 'ü', 'Ãœ': 'Ü',
    'Ã\x8d': 'Í', // the 'Í' can be problematic
    'Ã‘': 'Ñ',
    // also replace others if latin1-decoding strategy fails
};

function autoFixEncoding(str) {
    try {
        // Option 1: Double-encoded utf-8 detection
        // if str contains Ã, it's very likely decoded as latin1 and we want back to utf8
        let fixed = Buffer.from(str, 'latin1').toString('utf8');
        // if the fixed still has weird artifacts or if it includes the replacement char , fallback to map
        if (fixed.includes('')) {
            throw new Error("Invalid utf8 characters found from latin1 Buffer conversion");
        }
        return fixed;
    } catch (e) {
        // Fallback option 2: literal replacement
        console.log("Fallback to literal map replacement");
        let res = str;
        for (const [bad, good] of Object.entries(replaces)) {
            res = res.split(bad).join(good);
        }
        return res;
    }
}

// Ensure the fix doesn't break files
filesToFix.forEach(filepath => {
    if (!fs.existsSync(filepath)) return;
    const content = fs.readFileSync(filepath, 'utf8');
    if (content.includes('Ã')) {
        let fixedContent = content;
        // manually replace using map as it is safer and more robust for HTML files that might have mixed encodings
        for (const [bad, good] of Object.entries(replaces)) {
            fixedContent = fixedContent.split(bad).join(good);
        }

        // check if there's any remaining Ã 
        // to catch missing uppercase chars or specific sequences
        fixedContent = fixedContent.replace(/Ã(\x8d|\x81|\x89|\x93|\x9a)/g, (match, p1) => {
            const map = { '\x81': 'Á', '\x89': 'É', '\x8d': 'Í', '\x93': 'Ó', '\x9a': 'Ú' };
            return map[p1] || match;
        });

        fs.writeFileSync(filepath, fixedContent, 'utf8');
        console.log('Fixed:', filepath);
    }
});
