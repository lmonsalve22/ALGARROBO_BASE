const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, '../vistas2/vista2.html');
let content = fs.readFileSync(filePath, 'utf8');

// 1. Update Title
content = content.replace(
    '¿Cómo ha evolucionado la delincuencia en las últimas semanas?',
    '¿Cómo ha evolucionado la delincuencia en los últimos meses?'
);

// 2. Update Description
content = content.replace(
    'Tendencia de corto plazo',
    'Tendencia de mediano plazo (24 semanas)'
);

// 3. Update Slice Logic (8 -> 24)
content = content.replace(
    'allWeeksSorted.slice(0, 8).reverse()',
    'allWeeksSorted.slice(0, 24).reverse()'
);

// 4. Update Chart Styling (dataset 0)
// We need to be careful not to replace other pointRadius if any (ranges have 0)
// The first dataset has pointRadius: 6
content = content.replace('pointRadius: 6,', 'pointRadius: 4,');
content = content.replace('borderWidth: 3,', 'borderWidth: 2,'); // First one usually

fs.writeFileSync(filePath, content, 'utf8');
console.log('Vista 2 Updated Successfully');
