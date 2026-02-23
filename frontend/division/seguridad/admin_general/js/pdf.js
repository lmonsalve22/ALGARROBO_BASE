/**
 * PDF Module - Enhanced Cover Page Generation
 * Creates professional PDF reports with:
 * - Cover page
 * - Executive summary (auto-generated)
 * - Table of contents with links
 * - Headers/footers with page numbers
 * - Back cover with contact info
 * - Detailed progress bar with time estimation
 */

const PDFModule = {
    // Configuration
    config: {
        pageWidth: 210,
        pageHeight: 297,
        margins: { top: 15, bottom: 20, left: 15, right: 15 },
        headerHeight: 12,
        footerHeight: 15
    },

    // Progress tracking for time estimation
    progressTracker: {
        startTime: null,
        capturedViews: 0,
        totalViews: 0,
        averageTimePerView: 0
    },

    /**
     * Adds an image to the PDF with smart slicing to avoid cutting cards/tables
     */
    addSmartSlices(pdf, imgData, originalImgHeight, sectionTitle, startPage, totalPages, cardBoundaries) {
        const { pageWidth, pageHeight, headerHeight, footerHeight } = this.config;
        const usableHeight = pageHeight - headerHeight - footerHeight;

        let heightLeft = originalImgHeight;
        let currentY = 0; // Relative to img start (mm)
        let currentPage = startPage;

        while (heightLeft > 0.1) { // Floating point safety
            if (currentY > 0) {
                pdf.addPage();
            }

            let sliceHeight = Math.min(heightLeft, usableHeight);

            // Smart Break Check
            if (heightLeft > usableHeight && cardBoundaries && cardBoundaries.length > 0) {
                const targetCutLine = currentY + usableHeight;

                // Find a card that is being cut (overlaps the targetCutLine)
                const overlappingCard = cardBoundaries.find(b =>
                    b.top < targetCutLine - 2 && b.bottom > targetCutLine + 2
                );

                if (overlappingCard && overlappingCard.top > currentY + 5) {
                    // Cut BEFORE the overlapping card to keep it together on the next page
                    sliceHeight = overlappingCard.top - currentY;
                }
            }

            const pageTitle = currentY === 0 ? sectionTitle : `${sectionTitle} (cont.)`;
            this.addHeader(pdf, currentPage, totalPages, pageTitle);
            this.addFooter(pdf, currentPage);

            // Draw slice (using negative y position)
            // Clipping is handled by the PDF viewer boundaries
            pdf.addImage(imgData, 'JPEG', 0, headerHeight - currentY, pageWidth, originalImgHeight);

            // Clean overlays for header and footer areas
            pdf.setFillColor(248, 250, 252); // Match header bg
            pdf.rect(0, 0, pageWidth, headerHeight, 'F');
            pdf.setFillColor(255, 255, 255); // Match body bg
            pdf.rect(0, pageHeight - footerHeight, pageWidth, footerHeight, 'F');

            // Re-draw header/footer over the overlays to ensure text is visible
            this.addHeader(pdf, currentPage, totalPages, pageTitle);
            this.addFooter(pdf, currentPage);

            heightLeft -= sliceHeight;
            currentY += sliceHeight;
            currentPage++;
        }

        return currentPage;
    },

    /**
     * #5 - Generate consistent header for content pages
     * @param {jsPDF} pdf - The jsPDF instance
     * @param {number} pageNum - Current page number
     * @param {number} totalPages - Total page count
     * @param {string} sectionTitle - Optional section title
     */
    addHeader(pdf, pageNum, totalPages, sectionTitle = '') {
        const { pageWidth, margins, headerHeight } = this.config;
        const state = window.STATE_DATA || {};
        const comuna = state.comunaName ? (state.comunaName.charAt(0).toUpperCase() + state.comunaName.slice(1).toLowerCase()) : 'Comuna';

        // Header background bar
        pdf.setFillColor(248, 250, 252);
        pdf.rect(0, 0, pageWidth, headerHeight, 'F');

        // Bottom border line
        pdf.setDrawColor(226, 232, 240);
        pdf.setLineWidth(0.3);
        pdf.line(0, headerHeight, pageWidth, headerHeight);

        // Left: Logo text
        pdf.setFontSize(8);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(79, 70, 229);
        pdf.text('MONITOR DELITO', margins.left, 7);

        // Center: Section title or document title
        pdf.setFont('helvetica', 'normal');
        pdf.setTextColor(100, 116, 139);
        const centerText = sectionTitle || `Reporte de Inteligencia Delictual - ${comuna}`;
        pdf.text(centerText, pageWidth / 2, 7, { align: 'center' });

        // Right: Page number
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(30, 41, 59);
        pdf.text(`${pageNum} / ${totalPages}`, pageWidth - margins.right, 7, { align: 'right' });
    },

    /**
     * #5 - Generate consistent footer for content pages
     * @param {jsPDF} pdf - The jsPDF instance
     * @param {number} pageNum - Current page number
     */
    addFooter(pdf, pageNum) {
        const { pageWidth, pageHeight, margins, footerHeight } = this.config;
        const footerY = pageHeight - footerHeight;

        // Footer background
        pdf.setFillColor(248, 250, 252);
        pdf.rect(0, footerY, pageWidth, footerHeight, 'F');

        // Top border line
        pdf.setDrawColor(226, 232, 240);
        pdf.setLineWidth(0.3);
        pdf.line(0, footerY, pageWidth, footerY);

        // Left: Instituto Libertad
        pdf.setFontSize(7);
        pdf.setFont('helvetica', 'normal');
        pdf.setTextColor(107, 114, 128);
        pdf.text('© Instituto Libertad - Todos los derechos reservados', margins.left, footerY + 8);

        // Center: Confidentiality notice
        pdf.setFont('helvetica', 'italic');
        pdf.text('Documento de uso interno', pageWidth / 2, footerY + 8, { align: 'center' });

        // Right: Generation date
        const now = new Date();
        const dateStr = now.toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: 'numeric' });
        pdf.setFont('helvetica', 'normal');
        pdf.text(`Generado: ${dateStr}`, pageWidth - margins.right, footerY + 8, { align: 'right' });
    },

    /**
     * #6 - Generate Table of Contents
     * @param {jsPDF} pdf - The jsPDF instance
     * @param {Array} sections - Array of {title, page} objects
     * @param {number} startPage - Page number where TOC starts
     */
    generateTableOfContents(pdf, sections, startPage) {
        const { pageWidth, margins } = this.config;
        const state = window.STATE_DATA || {};

        // TOC Header
        pdf.setFontSize(20);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(30, 41, 59);
        pdf.text('Índice de Contenidos', pageWidth / 2, 40, { align: 'center' });

        // Decorative line under title
        pdf.setDrawColor(79, 70, 229);
        pdf.setLineWidth(1);
        pdf.line(80, 45, 130, 45);

        let yPos = 60;
        const lineHeight = 6.5; // Reduced from 8
        const dotGap = 2;

        // Group sections by category
        const categories = [
            { name: 'Portada y Resumen', icon: '📋', range: [0, 2] },
            { name: 'Análisis STOP', icon: '🛡️', range: [1, 20] },
            { name: 'Análisis CEAD', icon: '📊', range: [21, 40] },
            { name: 'Análisis Integrado', icon: '🔗', range: [41, 45] }
        ];

        sections.forEach((section, index) => {
            if (yPos > 260) {
                pdf.addPage();
                this.addHeader(pdf, startPage + 1, 0, 'Índice de Contenidos');
                yPos = 30;
            }

            // Section number
            pdf.setFontSize(9);
            pdf.setFont('helvetica', 'bold');
            pdf.setTextColor(79, 70, 229);
            pdf.text(`${String(index + 1).padStart(2, '0')}`, margins.left, yPos);

            // Section title
            pdf.setFont('helvetica', 'normal');
            pdf.setTextColor(30, 41, 59);
            const titleX = margins.left + 12;
            const maxTitleWidth = 120;
            const truncatedTitle = section.title.length > 50 ? section.title.substring(0, 47) + '...' : section.title;
            pdf.text(truncatedTitle, titleX, yPos);

            // Dotted line
            const titleEndX = titleX + pdf.getTextWidth(truncatedTitle) + dotGap;
            const pageNumX = pageWidth - margins.right - 12; // Increased gap to 12mm
            pdf.setDrawColor(200, 200, 200);
            pdf.setLineDashPattern([0.5, 3], 0);
            pdf.line(titleEndX, yPos - 1, pageNumX, yPos - 1);
            pdf.setLineDashPattern([], 0);

            // Page number
            pdf.setFont('helvetica', 'bold');
            pdf.setTextColor(79, 70, 229);
            pdf.text(String(section.page), pageWidth - margins.right, yPos, { align: 'right' });

            yPos += lineHeight;
        });

        return pdf.internal.getNumberOfPages();
    },

    /**
     * Generate professional back cover page
     */
    generateBackCover(pdf) {
        const { pageWidth, pageHeight } = this.config;
        const state = window.STATE_DATA || {};
        const comuna = state.comunaName ? (state.comunaName.charAt(0).toUpperCase() + state.comunaName.slice(1).toLowerCase()) : 'Comuna';

        // Dark background
        pdf.setFillColor(15, 23, 42);
        pdf.rect(0, 0, pageWidth, pageHeight, 'F');

        // Top gradient bar (purple to blue)
        const barHeight = 8;
        pdf.setFillColor(79, 70, 229);
        pdf.rect(0, 0, pageWidth / 2, barHeight, 'F');
        pdf.setFillColor(59, 130, 246);
        pdf.rect(pageWidth / 2, 0, pageWidth / 2, barHeight, 'F');

        // Logo section - centered prominently
        const logoY = 50;

        // Logo background circle
        pdf.setFillColor(30, 41, 59);
        pdf.circle(pageWidth / 2, logoY + 15, 25, 'F');

        // Logo border
        pdf.setDrawColor(79, 70, 229);
        pdf.setLineWidth(2);
        pdf.circle(pageWidth / 2, logoY + 15, 25, 'S');

        // Instituto Libertad text
        pdf.setFontSize(18);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(255, 255, 255);
        pdf.text('INSTITUTO', pageWidth / 2, logoY + 12, { align: 'center' });
        pdf.text('LIBERTAD', pageWidth / 2, logoY + 22, { align: 'center' });

        // Tagline
        pdf.setFontSize(8);
        pdf.setFont('helvetica', 'normal');
        pdf.setTextColor(156, 163, 175);
        pdf.text('Inteligencia para la Seguridad Ciudadana', pageWidth / 2, logoY + 50, { align: 'center' });

        // Decorative line
        pdf.setDrawColor(79, 70, 229);
        pdf.setLineWidth(0.5);
        pdf.line(50, logoY + 60, pageWidth - 50, logoY + 60);

        // Contact Information Section
        const infoY = logoY + 80;

        pdf.setFontSize(10);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(255, 255, 255);
        pdf.text('INFORMACION DE CONTACTO', pageWidth / 2, infoY, { align: 'center' });

        // Contact section divider
        pdf.setDrawColor(55, 65, 81);
        pdf.setLineWidth(0.3);
        pdf.line(60, infoY + 5, pageWidth - 60, infoY + 5);

        // Contact details with text icons (no emoji)
        pdf.setFontSize(9);
        pdf.setFont('helvetica', 'normal');
        pdf.setTextColor(209, 213, 219);

        const contactY = infoY + 18;
        const iconX = 55;
        const textX = 75;

        // Web
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(79, 70, 229);
        pdf.text('WEB', iconX, contactY, { align: 'center' });
        pdf.setFont('helvetica', 'normal');
        pdf.setTextColor(209, 213, 219);
        pdf.text('www.institutolibertad.cl', textX, contactY);

        // Email
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(79, 70, 229);
        pdf.text('EMAIL', iconX, contactY + 10, { align: 'center' });
        pdf.setFont('helvetica', 'normal');
        pdf.setTextColor(209, 213, 219);
        pdf.text('contacto@institutolibertad.cl', textX, contactY + 10);

        // Location
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(79, 70, 229);
        pdf.text('SEDE', iconX, contactY + 20, { align: 'center' });
        pdf.setFont('helvetica', 'normal');
        pdf.setTextColor(209, 213, 219);
        pdf.text('Santiago, Chile', textX, contactY + 20);

        // Legal Disclaimer Box
        const disclaimerY = contactY + 50;

        // Box background
        pdf.setFillColor(30, 41, 59);
        pdf.roundedRect(25, disclaimerY - 8, pageWidth - 50, 40, 4, 4, 'F');

        // Box border
        pdf.setDrawColor(249, 115, 22);
        pdf.setLineWidth(0.5);
        pdf.roundedRect(25, disclaimerY - 8, pageWidth - 50, 40, 4, 4, 'S');

        // Disclaimer header
        pdf.setFontSize(8);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(249, 115, 22);
        pdf.text('AVISO LEGAL', pageWidth / 2, disclaimerY, { align: 'center' });

        // Disclaimer text
        pdf.setFont('helvetica', 'normal');
        pdf.setTextColor(156, 163, 175);
        pdf.setFontSize(6.5);
        const disclaimer = 'Este documento contiene informacion elaborada con base en fuentes publicas oficiales (STOP y CEAD). Los datos presentados corresponden a estadisticas oficiales del Sistema STOP y CEAD. La reproduccion total o parcial de este documento requiere autorizacion expresa del Instituto Libertad.';
        const lines = pdf.splitTextToSize(disclaimer, pageWidth - 60);
        pdf.text(lines, pageWidth / 2, disclaimerY + 8, { align: 'center' });

        // Data Sources Section
        const sourcesY = disclaimerY + 50;

        pdf.setFontSize(9);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(107, 114, 128);
        pdf.text('FUENTES DE DATOS OFICIALES', pageWidth / 2, sourcesY, { align: 'center' });

        // Sources divider
        pdf.setDrawColor(55, 65, 81);
        pdf.setLineWidth(0.3);
        pdf.line(50, sourcesY + 4, pageWidth - 50, sourcesY + 4);

        pdf.setFontSize(7);
        pdf.setFont('helvetica', 'normal');
        pdf.setTextColor(156, 163, 175);

        const sources = [
            'STOP - Sistema Tactico de Operacion Policial (Carabineros de Chile)',
            'CEAD - Centro de Analisis del Delito (Subsecretaria de Prevencion del Delito)',
            'INE - Instituto Nacional de Estadisticas'
        ];

        sources.forEach((source, i) => {
            // Bullet point
            pdf.setFillColor(79, 70, 229);
            pdf.circle(35, sourcesY + 10 + (i * 6), 1, 'F');
            // Text
            pdf.text(source, 40, sourcesY + 11 + (i * 6));
        });

        // Footer - positioned above the bottom bar
        pdf.setFontSize(7);
        pdf.setTextColor(156, 163, 175);
        const year = new Date().getFullYear();
        pdf.text(`${year} Instituto Libertad. Todos los derechos reservados.`, pageWidth / 2, pageHeight - 12, { align: 'center' });

        // Bottom gradient bar
        pdf.setFillColor(79, 70, 229);
        pdf.rect(0, pageHeight - 6, pageWidth / 2, 6, 'F');
        pdf.setFillColor(59, 130, 246);
        pdf.rect(pageWidth / 2, pageHeight - 6, pageWidth / 2, 6, 'F');
    },

    /**
     * #31 - Generate Executive Summary Page
     * @param {jsPDF} pdf - The jsPDF instance
     */
    generateExecutiveSummary(pdf) {
        const { pageWidth, pageHeight, margins } = this.config;
        const state = window.STATE_DATA || {};
        const comuna = state.comunaName ? (state.comunaName.charAt(0).toUpperCase() + state.comunaName.slice(1).toLowerCase()) : 'Comuna';
        const semana = state.semanaDetalle || 'Semana --';
        const warning = state.warningZ || 'Sin datos';

        // White background
        pdf.setFillColor(255, 255, 255);
        pdf.rect(0, 0, pageWidth, pageHeight, 'F');

        // Header bar
        pdf.setFillColor(79, 70, 229);
        pdf.rect(0, 0, pageWidth, 25, 'F');

        pdf.setFontSize(14);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(255, 255, 255);
        pdf.text('RESUMEN EJECUTIVO', pageWidth / 2, 15, { align: 'center' });

        // Main content starts
        let yPos = 40;

        // Key Metrics Section
        pdf.setFontSize(11);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(30, 41, 59);
        pdf.text('Indicadores Clave', margins.left, yPos);

        yPos += 10;

        // KPI Cards - 4 columns
        const kpiData = this.extractKPIData();
        const cardWidth = 42;
        const cardHeight = 28;
        const cardGap = 5;

        kpiData.forEach((kpi, index) => {
            const x = margins.left + (index % 4) * (cardWidth + cardGap);
            const y = yPos + Math.floor(index / 4) * (cardHeight + cardGap);

            // Card background
            pdf.setFillColor(248, 250, 252);
            pdf.roundedRect(x, y, cardWidth, cardHeight, 2, 2, 'F');

            // Card border
            pdf.setDrawColor(226, 232, 240);
            pdf.setLineWidth(0.3);
            pdf.roundedRect(x, y, cardWidth, cardHeight, 2, 2, 'D');

            // KPI Value
            pdf.setFontSize(14);
            pdf.setFont('helvetica', 'bold');
            pdf.setTextColor(kpi.color.r, kpi.color.g, kpi.color.b);
            pdf.text(kpi.value, x + cardWidth / 2, y + 12, { align: 'center' });

            // KPI Label
            pdf.setFontSize(6);
            pdf.setFont('helvetica', 'normal');
            pdf.setTextColor(107, 114, 128);
            const labelLines = pdf.splitTextToSize(kpi.label, cardWidth - 4);
            pdf.text(labelLines, x + cardWidth / 2, y + 19, { align: 'center' });
        });

        yPos += Math.ceil(kpiData.length / 4) * (cardHeight + cardGap) + 15;

        // Context Section
        pdf.setFontSize(11);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(30, 41, 59);
        pdf.text('Contexto del Análisis', margins.left, yPos);

        yPos += 8;

        // Info boxes
        const infoBoxes = [
            { label: 'Comuna Analizada', value: comuna, icon: '📍' },
            { label: 'Período', value: semana, icon: '📅' },
            { label: 'Estado de Alerta IA', value: warning, icon: '🔔' }
        ];

        infoBoxes.forEach((box, index) => {
            const boxWidth = (pageWidth - margins.left - margins.right - 10) / 3;
            const boxX = margins.left + index * (boxWidth + 5);

            pdf.setFillColor(254, 252, 232);
            pdf.roundedRect(boxX, yPos, boxWidth, 20, 2, 2, 'F');

            pdf.setFontSize(7);
            pdf.setFont('helvetica', 'normal');
            pdf.setTextColor(133, 77, 14);
            pdf.text(box.label, boxX + boxWidth / 2, yPos + 7, { align: 'center' });

            pdf.setFontSize(9);
            pdf.setFont('helvetica', 'bold');
            pdf.setTextColor(120, 53, 15);
            const valueText = box.value.length > 25 ? box.value.substring(0, 22) + '...' : box.value;
            pdf.text(valueText, boxX + boxWidth / 2, yPos + 15, { align: 'center' });
        });

        yPos += 35;

        // AI Summary Section
        pdf.setFontSize(11);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(30, 41, 59);
        pdf.text('Síntesis de Inteligencia', margins.left, yPos);

        yPos += 8;

        // AI Summary box
        pdf.setFillColor(239, 246, 255);
        pdf.roundedRect(margins.left, yPos, pageWidth - margins.left - margins.right, 50, 3, 3, 'F');

        pdf.setDrawColor(59, 130, 246);
        pdf.setLineWidth(0.5);
        pdf.roundedRect(margins.left, yPos, pageWidth - margins.left - margins.right, 50, 3, 3, 'D');

        // AI Icon
        pdf.setFillColor(59, 130, 246);
        pdf.circle(margins.left + 10, yPos + 10, 5, 'F');
        pdf.setFontSize(8);
        pdf.setTextColor(255, 255, 255);
        pdf.text('IA', margins.left + 10, yPos + 12, { align: 'center' });

        // Summary text
        pdf.setFontSize(8);
        pdf.setFont('helvetica', 'normal');
        pdf.setTextColor(30, 64, 175);
        const summaryText = this.generateAISummaryText();
        const summaryLines = pdf.splitTextToSize(summaryText, pageWidth - margins.left - margins.right - 25);
        pdf.text(summaryLines, margins.left + 20, yPos + 10);

        yPos += 60;

        // Document Structure Section
        pdf.setFontSize(11);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(30, 41, 59);
        pdf.text('Estructura del Documento', margins.left, yPos);

        yPos += 10;

        const structure = [
            { section: 'Análisis STOP', desc: 'Estadísticas del Sistema Táctico de Operación Policial', pages: '20 vistas' },
            { section: 'Análisis CEAD', desc: 'Datos del Centro de Análisis del Delito', pages: '20 vistas' },
            { section: 'Análisis Integrado', desc: 'Correlación de fuentes STOP y CEAD', pages: '5 vistas' }
        ];

        structure.forEach((item, index) => {
            pdf.setFillColor(index % 2 === 0 ? 248 : 255, index % 2 === 0 ? 250 : 255, index % 2 === 0 ? 252 : 255);
            pdf.rect(margins.left, yPos, pageWidth - margins.left - margins.right, 12, 'F');

            pdf.setFontSize(8);
            pdf.setFont('helvetica', 'bold');
            pdf.setTextColor(30, 41, 59);
            pdf.text(item.section, margins.left + 3, yPos + 7);

            pdf.setFont('helvetica', 'normal');
            pdf.setTextColor(107, 114, 128);
            pdf.text(item.desc, margins.left + 45, yPos + 7);

            pdf.setFont('helvetica', 'bold');
            pdf.setTextColor(79, 70, 229);
            pdf.text(item.pages, pageWidth - margins.right - 3, yPos + 7, { align: 'right' });

            yPos += 12;
        });

        // Footer note
        pdf.setFontSize(7);
        pdf.setFont('helvetica', 'italic');
        pdf.setTextColor(156, 163, 175);
        pdf.text('Este resumen ha sido generado automáticamente con base en los datos disponibles.', pageWidth / 2, pageHeight - 20, { align: 'center' });
    },

    /**
     * Extract KPI data from STATE_DATA
     */
    extractKPIData() {
        const state = window.STATE_DATA || {};
        const colors = {
            primary: { r: 79, g: 70, b: 229 },
            success: { r: 16, g: 185, b: 129 },
            warning: { r: 245, g: 158, b: 11 },
            danger: { r: 239, g: 68, b: 68 }
        };

        return [
            { label: 'Semana Actual', value: state.semanaNum?.toString() || '--', color: colors.primary },
            { label: 'Año', value: state.year?.toString() || '--', color: colors.primary },
            { label: 'Estado Operacional', value: state.estadoOperacional || '--', color: colors.success },
            { label: 'Nivel de Alerta', value: state.warningZ || '--', color: colors.warning },
            { label: 'Delitos Totales', value: state.totalDelitos?.toLocaleString() || '--', color: colors.danger },
            { label: 'Variación Semanal', value: state.variacionSemanal || '--', color: colors.warning },
            { label: 'Delito Principal', value: state.delitoPrincipal || '--', color: colors.danger },
            { label: 'Día Crítico', value: state.diaCritico || '--', color: colors.primary }
        ];
    },

    /**
     * Generate AI summary text
     */
    generateAISummaryText() {
        const state = window.STATE_DATA || {};
        const comuna = state.comunaName || 'la comuna';
        const semana = state.semanaNum || '--';

        if (typeof IAModule !== 'undefined' && IAModule.interpretations?.vista1) {
            const interpretation = IAModule.interpretations.vista1;
            return interpretation.substring(0, 400) + (interpretation.length > 400 ? '...' : '');
        }

        return `El presente informe analiza la situación delictual de ${comuna} durante la semana ${semana}. ` +
            `Los datos provienen de fuentes oficiales (STOP, CEAD e INE) y han sido procesados mediante algoritmos de ` +
            `inteligencia artificial para detectar patrones, tendencias y generar alertas tempranas. ` +
            `Se recomienda revisar cada sección para obtener un panorama completo de la situación de seguridad.`;
    },

    /**
     * #44 - Show Enhanced Export Overlay with Progress Bar and Time Estimation
     * @param {number} totalViews - Total views to process
     */
    showEnhancedOverlay(totalViews) {
        this.progressTracker = {
            startTime: Date.now(),
            capturedViews: 0,
            totalViews: totalViews,
            averageTimePerView: 0,
            viewTimes: []
        };

        const overlay = document.createElement('div');
        overlay.id = 'pdfExportOverlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(15, 23, 42, 0.95);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            backdrop-filter: blur(8px);
        `;

        overlay.innerHTML = `
            <div style="background: white; padding: 2.5rem 3rem; border-radius: 20px; max-width: 520px; width: 90%; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
                <!-- Header -->
                <div style="text-align: center; margin-bottom: 1.5rem;">
                    <div style="width: 70px; height: 70px; background: linear-gradient(135deg, #4f46e5, #7c3aed); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.5);">
                        <i class="fa-solid fa-file-pdf fa-beat-fade" style="font-size: 28px; color: white;"></i>
                    </div>
                    <h3 style="margin: 0 0 0.25rem; color: #1e293b; font-size: 1.35rem; font-weight: 700;">Generando Informe PDF</h3>
                    <p style="margin: 0; color: #64748b; font-size: 0.9rem;" id="pdfPhaseText">Inicializando...</p>
                </div>

                <!-- Progress Bar -->
                <div style="margin-bottom: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.85rem;">
                        <span style="color: #475569; font-weight: 600;" id="pdfProgressLabel">Vista 0 de ${totalViews}</span>
                        <span style="color: #4f46e5; font-weight: 700;" id="pdfProgressPercent">0%</span>
                    </div>
                    <div style="background: #e2e8f0; border-radius: 10px; height: 14px; overflow: hidden; position: relative;">
                        <div id="pdfProgressBar" style="background: linear-gradient(90deg, #4f46e5, #7c3aed); height: 100%; width: 0%; transition: width 0.4s ease; border-radius: 10px; position: relative;">
                            <div style="position: absolute; right: 0; top: 0; bottom: 0; width: 30px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3)); animation: shimmer 1.5s infinite;"></div>
                        </div>
                    </div>
                </div>

                <!-- Time Estimation -->
                <div style="display: flex; justify-content: space-between; padding: 1rem; background: #f8fafc; border-radius: 10px; margin-bottom: 1.5rem;">
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px;">Tiempo transcurrido</div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #1e293b;" id="pdfElapsedTime">00:00</div>
                    </div>
                    <div style="width: 1px; background: #e2e8f0;"></div>
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px;">Tiempo restante est.</div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #4f46e5;" id="pdfRemainingTime">Calculando...</div>
                    </div>
                </div>

                <!-- Current Step -->
                <div style="padding: 0.75rem 1rem; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; display: flex; align-items: center; gap: 0.75rem;">
                    <i class="fa-solid fa-circle-notch fa-spin" style="color: #3b82f6;"></i>
                    <span style="color: #1e40af; font-size: 0.85rem;" id="pdfCurrentStep">Preparando captura de vistas...</span>
                </div>

                <!-- Warning -->
                <div style="margin-top: 1rem; padding: 0.75rem 1rem; background: #fff7ed; border: 1px solid #ffedd5; border-radius: 8px; display: flex; gap: 0.75rem;">
                    <i class="fa-solid fa-lightbulb" style="color: #f59e0b; margin-top: 2px;"></i>
                    <div>
                        <strong style="display: block; color: #9a3412; font-size: 0.8rem; margin-bottom: 2px;">Importante</strong>
                        <span style="color: #c2410c; font-size: 0.75rem; line-height: 1.4;">Mantenga esta pestaña activa para asegurar capturas de máxima calidad.</span>
                    </div>
                </div>
            </div>

            <style>
                @keyframes shimmer {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(100%); }
                }
            </style>
        `;

        document.body.appendChild(overlay);

        // Start time update interval
        this.timeUpdateInterval = setInterval(() => this.updateTimeDisplay(), 1000);
    },

    /**
     * #44 - Update progress display
     * @param {number} current - Current view number
     * @param {string} step - Current step description
     */
    updateProgress(current, step) {
        const tracker = this.progressTracker;
        tracker.capturedViews = current;

        // Calculate timing
        const now = Date.now();
        if (current > 0) {
            const elapsed = now - tracker.startTime;
            tracker.averageTimePerView = elapsed / current;
        }

        // Update UI elements
        const progressBar = document.getElementById('pdfProgressBar');
        const progressPercent = document.getElementById('pdfProgressPercent');
        const progressLabel = document.getElementById('pdfProgressLabel');
        const currentStep = document.getElementById('pdfCurrentStep');
        const phaseText = document.getElementById('pdfPhaseText');

        const percent = Math.round((current / tracker.totalViews) * 100);

        if (progressBar) progressBar.style.width = `${percent}%`;
        if (progressPercent) progressPercent.textContent = `${percent}%`;
        if (progressLabel) progressLabel.textContent = `Vista ${current} de ${tracker.totalViews}`;
        if (currentStep) currentStep.textContent = step;
        if (phaseText) {
            if (percent < 30) phaseText.textContent = 'Capturando vistas iniciales...';
            else if (percent < 70) phaseText.textContent = 'Procesando contenido...';
            else if (percent < 100) phaseText.textContent = 'Finalizando capturas...';
            else phaseText.textContent = 'Generando documento PDF...';
        }
    },

    /**
     * #44 - Update time display
     */
    updateTimeDisplay() {
        const tracker = this.progressTracker;
        const elapsed = Date.now() - tracker.startTime;

        // Format elapsed time
        const elapsedEl = document.getElementById('pdfElapsedTime');
        if (elapsedEl) {
            const mins = Math.floor(elapsed / 60000);
            const secs = Math.floor((elapsed % 60000) / 1000);
            elapsedEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        }

        // Calculate and format remaining time
        const remainingEl = document.getElementById('pdfRemainingTime');
        if (remainingEl && tracker.capturedViews > 0) {
            const remaining = tracker.averageTimePerView * (tracker.totalViews - tracker.capturedViews);
            if (remaining > 0) {
                const mins = Math.floor(remaining / 60000);
                const secs = Math.floor((remaining % 60000) / 1000);
                remainingEl.textContent = `~${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            } else {
                remainingEl.textContent = '< 00:10';
            }
        }
    },

    /**
     * Hide enhanced overlay
     */
    hideEnhancedOverlay() {
        if (this.timeUpdateInterval) {
            clearInterval(this.timeUpdateInterval);
            this.timeUpdateInterval = null;
        }
        const overlay = document.getElementById('pdfExportOverlay');
        if (overlay) {
            overlay.style.opacity = '0';
            overlay.style.transition = 'opacity 0.3s ease';
            setTimeout(() => overlay.remove(), 300);
        }
    },

    /**
     * Export Single Page (Current View)
     * Fixes: onclick="PDFModule.exportSinglePage()"
     */
    async exportSinglePage() {
        const btn = document.getElementById('btnExportSingle');
        const originalText = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generando...';
        }

        try {
            const { jsPDF } = window.jspdf;
            const container = document.getElementById('viewContainer');

            // Capture
            const canvas = await html2canvas(container, {
                scale: 2,
                useCORS: true,
                logging: false,
                backgroundColor: '#f8fafc'
            });

            const imgData = canvas.toDataURL('image/jpeg', 0.95);
            const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'landscape' });

            const pdfW = 297;
            const pdfH = 210;
            const imgH = (canvas.height * pdfW) / canvas.width;

            pdf.addImage(imgData, 'JPEG', 0, 0, pdfW, imgH);

            const viewName = window.App?.state?.currentView || 'vista';
            pdf.save(`Reporte_Individual_${viewName}.pdf`);

        } catch (error) {
            console.error("Export Single Error:", error);
            alert("Error exportando hoja actual.");
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }
    },

    /**
     * Export Full Report with Cover
     * Fixes: onclick="PDFModule.exportWithCover()"
     * Delegates to V2 module if available and relevant.
     */
    async exportWithCover() {
        // Check if we contain Vistas 2 module
        if (window.PDFModuleV2 && window.location.href.includes('vistas2')) {
            console.log("Delegating to PDFModuleV2...");
            await window.PDFModuleV2.exportReport();
            return;
        }

        // Fallback or Standard Impl
        console.warn("Standard exportWithCover not fully implemented in this context. Using V2 delegation.");
        if (window.PDFModuleV2) {
            await window.PDFModuleV2.exportReport();
        } else {
            alert("Módulo de reporte completo no inicializado.");
        }
    },

    /**
     * Generate cover page on a jsPDF instance
     * @param {jsPDF} pdf - The jsPDF instance
     */
    generateCoverPage(pdf) {
        const pageWidth = 210;
        const pageHeight = 297;
        const state = window.STATE_DATA || {};
        const comuna = state.comunaName ? (state.comunaName.charAt(0).toUpperCase() + state.comunaName.slice(1).toLowerCase()) : 'Comuna';
        const region = state.regionName ? (state.regionName.charAt(0).toUpperCase() + state.regionName.slice(1).toLowerCase()) : 'Región';
        const semanaFull = state.semanaDetalle || 'Semana --';
        const warning = state.warningZ || 'Nivel --';

        function capitalizeWords(str) { return str.toLowerCase().replace(/(?:^|\s)\S/g, a => a.toUpperCase()); }
        const comunaDisplay = capitalizeWords(state.comunaName || 'Comuna');
        const regionDisplay = capitalizeWords(state.regionName || 'Región');

        let semanaTitle = "Semana --";
        let semanaDates = "--";
        if (semanaFull.includes(' (')) {
            const parts = semanaFull.split(' (');
            semanaTitle = parts[0];
            semanaDates = parts[1].replace(')', '');
        } else { semanaTitle = semanaFull; }

        const now = new Date();
        const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const dateStr = now.toLocaleDateString('es-ES', dateOptions);
        const dateCap = dateStr.charAt(0).toUpperCase() + dateStr.slice(1);

        // 1. Background White
        pdf.setFillColor(255, 255, 255);
        pdf.rect(0, 0, pageWidth, pageHeight, 'F');

        // 2. Header Dark Blue/Black
        pdf.setFillColor(10, 15, 30);
        pdf.rect(0, 0, pageWidth, 50, 'F');

        // Header Text Left
        pdf.setTextColor(200, 200, 200);
        pdf.setFontSize(8);
        pdf.setFont('helvetica', 'italic');
        pdf.text('Un producto elaborado por el Instituto', 15, 18);
        pdf.text('Libertad con base en fuentes públicas', 15, 22);
        pdf.text('de información.', 15, 26);

        // Header Center (Logo Image)
        try {
            const logoW = 50;
            const logoH = 15;
            const logoX = (pageWidth - logoW) / 2;
            pdf.addImage('img/logo_instituto.png', 'PNG', logoX, 15, logoW, logoH);
        } catch (e) {
            pdf.setTextColor(255, 255, 255);
            pdf.setFont('helvetica', 'bold');
            pdf.setFontSize(16);
            pdf.text('INSTITUTO LIBERTAD', 105, 25, { align: 'center' });
        }

        // Header Right (Last update)
        const badgeCenter = 170;
        const badgeY = 12;

        pdf.setDrawColor(16, 185, 129);
        pdf.setLineWidth(0.5);
        pdf.roundedRect(145, badgeY, 50, 8, 4, 4, 'D');

        pdf.setFontSize(7);
        const updateText = 'Última actualización de datos';
        const textWidth = pdf.getTextWidth(updateText);
        const circleSize = 1.5;
        const gap = 2;
        const totalContentWidth = (circleSize * 2) + gap + textWidth;
        const startX = badgeCenter - (totalContentWidth / 2);

        pdf.setFillColor(16, 185, 129);
        pdf.circle(startX + circleSize, badgeY + 4, circleSize, 'F');

        pdf.setTextColor(16, 185, 129);
        pdf.text(updateText, startX + (circleSize * 2) + gap, badgeY + 6);

        pdf.setTextColor(156, 163, 175);
        pdf.text(dateCap, badgeCenter, 26, { align: 'center' });

        // 3. Body
        const startY = 80;

        // Badge
        pdf.setFillColor(254, 243, 199);
        pdf.roundedRect(30, startY - 5, 35, 8, 1, 1, 'F');
        pdf.setTextColor(180, 83, 9);
        pdf.setFontSize(8);
        pdf.setFont('helvetica', 'bold');
        pdf.text('INFORME SEMANAL', 47.5, startY, { align: 'center' });

        // Location Info
        pdf.setTextColor(0, 0, 0);
        pdf.setFontSize(10);
        pdf.setFont('helvetica', 'normal');
        pdf.text(`Comuna de ${comunaDisplay}, Región: ${regionDisplay}`, 70, startY);

        // Main Title
        const titleY = startY + 25;
        pdf.setFontSize(28);
        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(0, 0, 0);
        pdf.text('REPORTE DE INTELIGENCIA', 30, titleY);

        pdf.text('DELICTUAL', 30, titleY + 12);
        const delWidth = pdf.getTextWidth('DELICTUAL ');

        // Comuna in Orange
        pdf.setTextColor(249, 115, 22);
        pdf.text(comunaDisplay, 30 + delWidth, titleY + 12);

        // Subtitle
        pdf.setFontSize(12);
        pdf.setTextColor(107, 114, 128);
        pdf.setFont('helvetica', 'normal');
        pdf.text('Análisis táctico, estratégico y predictivo para la toma de decisiones.', 30, titleY + 30);

        // 4. Info Blocks
        const infoY = titleY + 60;

        // Block 1
        pdf.setFontSize(7);
        pdf.setTextColor(156, 163, 175);
        pdf.setFont('helvetica', 'bold');
        pdf.text('PERIODO ANALIZADO', 32, infoY);

        pdf.setFontSize(18);
        pdf.setTextColor(30, 41, 59);
        pdf.text(semanaTitle, 32, infoY + 8);

        pdf.setFontSize(9);
        pdf.setTextColor(156, 163, 175);
        pdf.setFont('helvetica', 'normal');
        pdf.text(semanaDates, 32, infoY + 14);

        // Vertical Line
        pdf.setDrawColor(200, 200, 200);
        pdf.setLineWidth(0.5);
        pdf.line(95, infoY, 95, infoY + 15);

        // Block 2
        pdf.setFontSize(7);
        pdf.setTextColor(156, 163, 175);
        pdf.setFont('helvetica', 'bold');
        pdf.text('ESTADO DE ALERTA IA', 105, infoY);

        pdf.setFontSize(18);
        pdf.setTextColor(30, 41, 59);
        if (warning.includes('Nivel')) {
            pdf.text(warning, 105, infoY + 8);
        } else {
            pdf.text('Nivel ' + warning, 105, infoY + 8);
        }

        pdf.setFontSize(9);
        pdf.setTextColor(156, 163, 175);
        pdf.setFont('helvetica', 'normal');
        pdf.text('Foco: Robos con Violencia', 105, infoY + 14);

        // 5. Footer
        const footerY = 250;
        pdf.setFontSize(9);
        pdf.setTextColor(100, 100, 100);
        pdf.text('Fecha Emisión del Reporte:', 50, footerY);

        pdf.setFont('helvetica', 'bold');
        pdf.setTextColor(0, 0, 0);
        pdf.text(dateCap, 100, footerY);
    },

    /**
     * Build sections list for TOC
     * @param {Array} views - Array of view names
     */
    buildTOCSections(views) {
        const viewTitles = {
            vista1: 'Resumen General de Delitos',
            vista2: 'Comparativa Semanal',
            vista3: 'Tendencia Histórica',
            vista4: 'Distribución por Delito',
            vista5: 'Análisis por Día de Semana',
            vista6: 'Análisis por Hora',
            vista7: 'Mapa de Calor Temporal',
            vista8: 'Top Sectores Afectados',
            vista9: 'Evolución Mensual',
            vista10: 'Comparativa Anual',
            vista11: 'Delitos de Mayor Impacto',
            vista12: 'Análisis de Robos',
            vista13: 'Análisis de Hurtos',
            vista14: 'Delitos Violentos',
            vista15: 'Delitos contra Propiedad',
            vista16: 'Tasa por 100 mil hab.',
            vista17: 'Ranking Regional',
            vista18: 'Predicción Semanal',
            vista19: 'Alertas Tempranas',
            vista20: 'Recomendaciones IA',
            vista21: 'Resumen CEAD',
            vista22: 'Comparativa CEAD',
            vista23: 'Tendencia CEAD',
            vista24: 'Distribución CEAD',
            vista25: 'Día de Semana CEAD',
            vista26: 'Hora CEAD',
            vista27: 'Mapa Temporal CEAD',
            vista28: 'Sectores CEAD',
            vista29: 'Evolución CEAD',
            vista30: 'Comparativa Anual CEAD',
            vista31: 'Impacto CEAD',
            vista32: 'Robos CEAD',
            vista33: 'Hurtos CEAD',
            vista34: 'Violentos CEAD',
            vista35: 'Propiedad CEAD',
            vista36: 'Tasa CEAD',
            vista37: 'Ranking CEAD',
            vista38: 'Predicción CEAD',
            vista39: 'Alertas CEAD',
            vista40: 'Recomendaciones CEAD',
            vista41: 'Integración STOP-CEAD',
            vista42: 'Correlación de Fuentes',
            vista43: 'Discrepancias',
            vista44: 'Consolidado Final',
            vista45: 'Conclusiones Generales'
        };

        // Start page: Cover(1) + Exec Summary(2) + TOC(3) = content starts at 4
        let currentPage = 4;

        return views.map((view, index) => ({
            title: viewTitles[view] || `Vista ${view.replace('vista', '')}`,
            page: currentPage + index,
            view: view
        }));
    },

    /**
     * Export PDF with Cover Page (Enhanced with all improvements)
     * Captures all views, then creates PDF with cover + exec summary + toc + views + back cover
     */
    async exportWithCover() {
        if (App.state.isExporting) return;

        // Check if IA analysis is complete
        if (typeof IAModule !== 'undefined' && !IAModule.isLoaded) {
            const proceed = confirm(
                '⚠️ El análisis de IA aún no ha terminado.\n\n' +
                '¿Desea generar el informe sin las interpretaciones de IA?\n\n' +
                'Presione "Aceptar" para continuar o "Cancelar" para esperar.'
            );
            if (!proceed) return;
        }

        App.state.isExporting = true;
        const originalView = App.state.currentView;
        const container = App.elements.viewContainer;
        const btn = document.getElementById('btnExportCover');

        // Update button state
        const originalBtnText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Preparando...';
        btn.disabled = true;

        // Filter to include only STOP views (vista1 to vista20)
        const stopViews = App.config.views.filter(view => {
            const match = view.match(/^vista(\d+)$/);
            if (match) {
                const num = parseInt(match[1]);
                return num >= 1 && num <= 20;
            }
            return false;
        });

        // #44 - Show enhanced overlay with progress tracking
        this.showEnhancedOverlay(stopViews.length);

        // Desactivar animaciones globalmente para la exportación
        if (typeof Chart !== 'undefined') Chart.defaults.animation = false;

        try {
            const pageWidth = 210;
            const pageHeight = 297;

            // STEP 1: Capture all views
            const capturedPages = [];

            for (let i = 0; i < stopViews.length; i++) {
                const viewName = stopViews[i];

                // #44 - Update detailed progress
                this.updateProgress(i, `Capturando ${viewName}...`);
                btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${i + 1}/${stopViews.length}`;

                // Destroy previous charts
                App.destroyAllCharts();

                // Load view
                await App.loadView(viewName);

                // Wait for charts to render (Estabilización para PDF)
                await App.delay(4000);

                // Capture
                const canvas = await html2canvas(container, {
                    scale: App.config.pdfScale,
                    useCORS: true,
                    allowTaint: true,
                    backgroundColor: '#f1f5f9',
                    logging: false
                });

                const imgData = canvas.toDataURL('image/jpeg', 0.95);
                const imgHeight = (canvas.height * pageWidth) / canvas.width;

                // Smart Boundaries: Identify card positions to avoid cutting them
                const containerRect = container.getBoundingClientRect();
                const pxToMm = pageWidth / canvas.width;
                const cards = Array.from(container.querySelectorAll('.card, .indicator-card, .chart-card, .v2-card, .performance-table'));
                const cardBoundaries = cards.map(card => {
                    const rect = card.getBoundingClientRect();
                    return {
                        top: (rect.top - containerRect.top) * pxToMm,
                        bottom: (rect.bottom - containerRect.top) * pxToMm
                    };
                });

                // Store captured image and boundaries
                capturedPages.push({ imgData, imgHeight, viewName, cardBoundaries });

                // Update progress after capture
                this.updateProgress(i + 1, `Vista ${viewName} capturada`);
            }

            // STEP 2: Create PDF document
            this.updateProgress(stopViews.length, 'Generando documento PDF...');

            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({ unit: 'mm', format: 'a4' });

            // Page 1: Cover page
            this.generateCoverPage(pdf);

            // Page 2: Table of Contents (#6)
            pdf.addPage();
            const tocSections = this.buildTOCSections(stopViews);
            this.generateTableOfContents(pdf, tocSections, 2);

            // Calculate total pages for headers/footers

            let totalContentPages = 0;
            capturedPages.forEach(({ imgHeight }) => {
                totalContentPages += Math.ceil(imgHeight / pageHeight);
            });
            const totalPages = 2 + totalContentPages + 1; // Cover + TOC + Content + BackCover

            // STEP 3: Add all captured pages with headers/footers
            let currentPage = 3;
            for (let i = 0; i < capturedPages.length; i++) {
                const { imgData, imgHeight, viewName, cardBoundaries } = capturedPages[i];
                const sectionTitle = tocSections[i]?.title || '';

                pdf.addPage();

                // Use Smart Slicing instead of fixed position sliced image
                currentPage = this.addSmartSlices(pdf, imgData, imgHeight, sectionTitle, currentPage, totalPages, cardBoundaries);
            }

            // Page N: Back Cover (#7)
            pdf.addPage();
            this.generateBackCover(pdf);

            // Save PDF
            const date = new Date().toISOString().split('T')[0];
            const state = window.STATE_DATA || {};
            const comunaName = state.comunaName || 'Comuna';
            pdf.save(`Informe_RID_${comunaName}_${date}.pdf`);

        } catch (error) {
            console.error('Error exporting PDF with cover:', error);
            alert('Error al exportar PDF. Por favor intente nuevamente.');
        } finally {
            // Restaurar animaciones
            if (typeof Chart !== 'undefined') Chart.defaults.animation = true;

            // Restore state
            this.hideEnhancedOverlay();
            btn.innerHTML = originalBtnText;
            btn.disabled = false;
            App.state.isExporting = false;
            App.loadView(originalView);
        }
    },

    /**
     * Export Full PDF Report (All Views) - Also enhanced with all improvements
     */
    async exportFullReport() {
        if (App.state.isExporting) return;

        // Check if IA analysis is complete
        if (typeof IAModule !== 'undefined' && !IAModule.isLoaded) {
            const proceed = confirm(
                '⚠️ El análisis de IA aún no ha terminado.\n\n' +
                '¿Desea generar el informe sin las interpretaciones de IA?\n\n' +
                'Presione "Aceptar" para continuar o "Cancelar" para esperar.'
            );
            if (!proceed) return;
        }

        App.state.isExporting = true;
        const originalView = App.state.currentView;
        const container = App.elements.viewContainer;
        const btn = document.getElementById('btnExportFull');

        // Update button state
        const originalBtnText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Preparando...';
        btn.disabled = true;

        // USE ALL CONFIGURED VIEWS
        const viewsToExport = App.config.views;

        // #44 - Show enhanced overlay
        this.showEnhancedOverlay(viewsToExport.length);

        // Desactivar animaciones globalmente para la exportación
        if (typeof Chart !== 'undefined') Chart.defaults.animation = false;

        try {
            const pageWidth = 210;
            const pageHeight = 297;

            // STEP 1: Capture all views
            const capturedPages = [];

            for (let i = 0; i < viewsToExport.length; i++) {
                const viewName = viewsToExport[i];

                // #44 - Update progress
                this.updateProgress(i, `Capturando ${viewName}...`);
                btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${i + 1}/${viewsToExport.length}`;

                // Destroy previous charts
                App.destroyAllCharts();

                // Load view
                await App.loadView(viewName);

                // Wait for charts to render (Estabilización para PDF)
                await App.delay(4000);

                // Capture
                const canvas = await html2canvas(container, {
                    scale: App.config.pdfScale,
                    useCORS: true,
                    allowTaint: true,
                    backgroundColor: '#f1f5f9',
                    logging: false
                });

                const imgData = canvas.toDataURL('image/jpeg', 0.95);
                const imgHeight = (canvas.height * pageWidth) / canvas.width;

                // Smart Boundaries
                const containerRect = container.getBoundingClientRect();
                const pxToMm = pageWidth / canvas.width;
                const cards = Array.from(container.querySelectorAll('.card, .indicator-card, .chart-card, .v2-card, .performance-table'));
                const cardBoundaries = cards.map(card => {
                    const rect = card.getBoundingClientRect();
                    return {
                        top: (rect.top - containerRect.top) * pxToMm,
                        bottom: (rect.bottom - containerRect.top) * pxToMm
                    };
                });

                capturedPages.push({ imgData, imgHeight, viewName, cardBoundaries });
                this.updateProgress(i + 1, `Vista ${viewName} capturada`);
            }

            // STEP 2: Create PDF
            this.updateProgress(viewsToExport.length, 'Generando documento PDF completo...');

            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({ unit: 'mm', format: 'a4' });

            // Page 1: Cover
            this.generateCoverPage(pdf);

            // Page 2: TOC
            pdf.addPage();
            const tocSections = this.buildTOCSections(viewsToExport);
            this.generateTableOfContents(pdf, tocSections, 2);

            // Calculate total pages
            let totalContentPages = 0;
            capturedPages.forEach(({ imgHeight }) => {
                totalContentPages += Math.ceil(imgHeight / pageHeight);
            });
            const totalPages = 2 + totalContentPages + 1;

            // Add all captured pages with headers/footers
            let currentPage = 3;
            for (let i = 0; i < capturedPages.length; i++) {
                const { imgData, imgHeight, viewName, cardBoundaries } = capturedPages[i];
                const sectionTitle = tocSections[i]?.title || '';

                pdf.addPage();

                // Use Smart Slicing
                currentPage = this.addSmartSlices(pdf, imgData, imgHeight, sectionTitle, currentPage, totalPages, cardBoundaries);
            }

            // Back Cover
            pdf.addPage();
            this.generateBackCover(pdf);

            // Save PDF
            const date = new Date().toISOString().split('T')[0];
            const state = window.STATE_DATA || {};
            const comunaName = state.comunaName || 'Comuna';
            pdf.save(`Informe_RID_Completo_${comunaName}_${date}.pdf`);

        } catch (error) {
            console.error('Error exporting Full PDF:', error);
            alert('Error al exportar PDF Completo. Por favor intente nuevamente.');
        } finally {
            // Restaurar animaciones
            if (typeof Chart !== 'undefined') Chart.defaults.animation = true;

            this.hideEnhancedOverlay();
            btn.innerHTML = originalBtnText;
            btn.disabled = false;
            App.state.isExporting = false;
            App.loadView(originalView);
        }
    },

    /**
     * Export Single Page PDF - Current view only, no cover
     */
    async exportSinglePage() {
        if (App.state.isExporting) return;

        App.state.isExporting = true;
        const btn = document.getElementById('btnExportSingle');
        const originalBtnText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generando...';
        btn.disabled = true;

        try {
            // Wait for charts to render
            await new Promise(r => setTimeout(r, 500));

            const container = document.getElementById('viewContainer');
            if (!container || container.scrollHeight < 10) {
                alert('No hay contenido para exportar.');
                return;
            }

            // Capture current view
            const canvas = await html2canvas(container, {
                scale: 2,
                useCORS: true,
                logging: false,
                backgroundColor: '#f1f5f9',
                windowWidth: container.scrollWidth,
                windowHeight: container.scrollHeight
            });

            const imgData = canvas.toDataURL('image/jpeg', 0.95);
            const imgWidth = 210; // ancho total A4 en mm
            const imgHeight = (canvas.height * imgWidth) / canvas.width;

            // Identificar límites de tarjetas para evitar cortes
            const containerRect = container.getBoundingClientRect();
            const pxToMm = imgWidth / canvas.width;
            const cards = Array.from(container.querySelectorAll('.card, .indicator-card, .chart-card, .v2-card, .performance-table'));
            const cardBoundaries = cards.map(card => {
                const rect = card.getBoundingClientRect();
                return {
                    top: (rect.top - containerRect.top) * pxToMm,
                    bottom: (rect.bottom - containerRect.top) * pxToMm
                };
            });

            // Crear PDF
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({ unit: 'mm', format: 'a4' });

            // Usar Smart Slices para evitar cortes en tablas
            const currentView = App.state.currentView || 'vista';
            this.addSmartSlices(pdf, imgData, imgHeight, currentView, 1, 1, cardBoundaries);


            // Save
            const comunaName = window.STATE_DATA?.comunaName || 'Santiago';
            pdf.save(`${currentView}_${comunaName}.pdf`);

        } catch (error) {
            console.error('Error exporting single page:', error);
            alert('Error al exportar. Por favor intente nuevamente.');
        } finally {
            btn.innerHTML = originalBtnText;
            btn.disabled = false;
            App.state.isExporting = false;
        }
    }
};

// Expose for global access
window.PDFModule = PDFModule;
