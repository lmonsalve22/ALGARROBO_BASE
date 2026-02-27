/**
 * PDF Module V2 - Seguridad Municipal
 * Restricted to 5 strategic views: vista1, vista5, vista13, vista18, vista22
 * Extends capabilities of standard PDFModule with specific structure.
 */

const capitalize = (str) =>
    str ? str.charAt(0).toUpperCase() + str.slice(1) : str;

window.PDFModuleV2 = {
    // Config
    config: {
        pageWidth: 210,
        pageHeight: 297,
        margins: { top: 15, bottom: 20, left: 15, right: 15 },
        views: ['vista1', 'vista5', 'vista13', 'vista18', 'vista22']
    },

    // View Meta — indexed by view name
    viewMeta: {
        'vista1': { title: 'Resumen Ejecutivo', level: 'Nivel 1: Resumen Ejecutivo', icon: '📋' },
        'vista5': { title: 'Delitos Críticos', level: 'Nivel 2: Delitos Críticos', icon: '📅' },
        'vista13': { title: 'Vs. Comunas Similares', level: 'Nivel 4: Benchmarking Geográfico', icon: '🌍' },
        'vista18': { title: 'Gravedad por Delito', level: 'Nivel 6: Gravedad e Impacto Social', icon: '⚖️' },
        'vista22': { title: 'Priorización Estratégica', level: 'Nivel 7: Priorización Estratégica', icon: '🏗️' }
    },

    /**
     * Entry Point: Generate Complete Report
     */
    async exportReport() {
        if (!window.PDFModule) {
            console.error("Standard PDFModule required for base functions (covers, overlays, utils).");
            return;
        }

        const base = window.PDFModule;
        const views = this.config.views;
        const totalViews = views.length;

        // Show Base Overlay
        base.showEnhancedOverlay(totalViews);
        const originalView = App.state.currentView;

        try {
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({ unit: 'mm', format: 'a4' });

            // 1. Cover Page
            generateCoverV2(pdf);
            pdf.addPage();

            // 2. Executive Summary
            this.generateExecutiveSummaryV2(pdf);
            pdf.addPage();

            // 3. Table of Contents
            this.generateTOC(pdf);
            pdf.addPage();

            let pageCount = 4; // Cover=1, Exec=2, TOC=3

            // 4. Capture Views
            for (let i = 0; i < totalViews; i++) {
                const viewName = views[i];
                const meta = this.viewMeta[viewName];
                const viewTitle = meta.title;

                // Update Progress
                base.updateProgress(i + 1, `Capturando: ${viewTitle}`);

                // Format section title
                const sectionTitle = `${meta.level.toUpperCase()} - ${viewTitle}`;

                // Load View
                await App.loadView(viewName);

                // Wait for render
                await new Promise(r => setTimeout(r, 2000));

                // Capture
                const container = document.getElementById('viewContainer');
                if (!container) continue;

                const canvas = await html2canvas(container, {
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    backgroundColor: '#f1f5f9',
                    scrollX: 0,
                    scrollY: 0,
                    width: container.scrollWidth,
                    height: container.scrollHeight
                });

                const imgData = canvas.toDataURL('image/jpeg', 0.95);
                const mmPerCanvasPx = 210 / canvas.width;
                const imgHeightMm = canvas.height * mmPerCanvasPx;

                const containerRect = container.getBoundingClientRect();
                // DOM is measured in CSS pixels, Canvas is scaled (usually 2x). We need a ratio for CSS px.
                const mmPerCssPx = 210 / container.scrollWidth;

                const cards = Array.from(container.querySelectorAll('.card, .chart-card, .alert, .row, h1, h2, h3, h4, .location-source-row, p, ul, .question-section'));
                const cardBoundaries = cards.map(c => {
                    const r = c.getBoundingClientRect();
                    return {
                        top: (r.top - containerRect.top) * mmPerCssPx,
                        bottom: (r.bottom - containerRect.top) * mmPerCssPx
                    };
                }).filter(b => (b.bottom - b.top) > 2); // Ignore tiny elements

                if (i > 0) pdf.addPage();

                const yOffset = 18;
                const footerHeight = 15;
                const availableHeight = 297 - yOffset - footerHeight;

                if (imgHeightMm > availableHeight) {
                    console.log(`View ${viewName} overflow. Smart slicing...`);

                    let heightLeft = imgHeightMm;
                    let currentYMm = 0;
                    let sliceIndex = 0;

                    while (heightLeft > 0.1) {
                        if (sliceIndex > 0) {
                            pdf.addPage();
                            pageCount++;
                        }

                        let sliceHeightMm = Math.min(heightLeft, availableHeight);

                        // Smart Break: Avoid cutting cards or titles
                        if (heightLeft > availableHeight) {
                            const targetCutLine = currentYMm + availableHeight;

                            // 1. First, check for atomic blocks (these MUST NOT be cut)
                            const atomicBlocks = Array.from(container.querySelectorAll('.atomic-block, .chart-card, .matrix-container'));
                            const atomicBoundaries = atomicBlocks.map(c => {
                                const r = c.getBoundingClientRect();
                                return {
                                    top: (r.top - containerRect.top) * mmPerCssPx,
                                    bottom: (r.bottom - containerRect.top) * mmPerCssPx
                                };
                            });

                            const overlappingAtomic = atomicBoundaries.find(b =>
                                b.top < targetCutLine - 2 && b.bottom > targetCutLine + 2
                            );

                            if (overlappingAtomic && overlappingAtomic.top > currentYMm + 10) {
                                // Subtract padding to cut just before the target element
                                sliceHeightMm = Math.max(10, overlappingAtomic.top - currentYMm - 2);
                            } else {
                                // 2. Fallback to standard intelligent breaking
                                const overlappingCard = cardBoundaries.find(b =>
                                    b.top < targetCutLine - 2 && b.bottom > targetCutLine + 2
                                );

                                if (overlappingCard && overlappingCard.top > currentYMm + 25) {
                                    sliceHeightMm = Math.max(10, overlappingCard.top - currentYMm - 2);
                                }
                            }
                        }

                        this.addHeaderV2(pdf, i + 1, sliceIndex === 0 ? sectionTitle : `${sectionTitle} (Cont.)`);
                        this.addFooterV2(pdf, pageCount);

                        // Capture slice
                        const sliceHeightPx = sliceHeightMm / mmPerCanvasPx;
                        const currentYPx = currentYMm / mmPerCanvasPx;

                        const sliceCanvas = document.createElement('canvas');
                        sliceCanvas.width = canvas.width;
                        sliceCanvas.height = sliceHeightPx;
                        const ctx = sliceCanvas.getContext('2d');
                        ctx.drawImage(canvas,
                            0, currentYPx, canvas.width, sliceHeightPx,
                            0, 0, canvas.width, sliceHeightPx
                        );

                        const sliceImg = sliceCanvas.toDataURL('image/jpeg', 0.95);
                        pdf.addImage(sliceImg, 'JPEG', 0, yOffset, 210, sliceHeightMm);

                        heightLeft -= sliceHeightMm;
                        currentYMm += sliceHeightMm;
                        sliceIndex++;
                    }
                } else {
                    // Normal One-Page View
                    this.addHeaderV2(pdf, i + 1, sectionTitle);
                    this.addFooterV2(pdf, pageCount);
                    pdf.addImage(imgData, 'JPEG', 0, yOffset, 210, imgHeightMm);
                }
                pageCount++;
            }

            // 5. Back Cover
            pdf.addPage();
            base.generateBackCover(pdf);

            // Save
            const date = new Date().toISOString().split('T')[0];
            const name = window.STATE_DATA?.comunaName || 'Comuna';
            pdf.save(`Informe_Seguridad_${name}_${date}.pdf`);

        } catch (error) {
            console.error("PDF Export Error:", error);
            alert("Error al generar el PDF. Revise la consola.");
        } finally {
            base.hideEnhancedOverlay();
            App.loadView(originalView);
        }
    },

    /**
     * Custom Executive Summary
     */
    generateExecutiveSummaryV2(pdf) {
        const { pageWidth, pageHeight } = this.config;
        const state = window.STATE_DATA || {};

        // Background
        pdf.setFillColor(255, 255, 255);
        pdf.rect(0, 0, pageWidth, pageHeight, 'F');

        // Header
        pdf.setFillColor(30, 58, 138); // Dark Blue
        pdf.rect(0, 0, pageWidth, 20, 'F');

        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(16);
        pdf.setTextColor(255, 255, 255);
        pdf.text("RESUMEN EJECUTIVO - SEGURIDAD MUNICIPAL", pageWidth / 2, 13, { align: "center" });

        // Content
        let y = 40;

        // 1. Structure Summary
        pdf.setFontSize(12);
        pdf.setTextColor(30, 41, 59);
        pdf.text("Estructura del Informe", 20, y);
        y += 10;

        const views = this.config.views;
        views.forEach(viewName => {
            const meta = this.viewMeta[viewName];
            pdf.setFontSize(10);
            pdf.setTextColor(71, 85, 105);
            pdf.text(`• ${meta.level} — ${meta.title}`, 25, y);
            y += 7;
        });

        // 2. Comuna Data
        y += 10;
        pdf.setFontSize(12);
        pdf.setTextColor(30, 41, 59);
        pdf.text("Datos de la Comuna", 20, y);
        y += 10;

        pdf.setFontSize(10);
        pdf.text(`Comuna: ${state.comunaName || '--'}`, 25, y);
        y += 6;
        pdf.text(`Semana: ${state.semanaDetalle || '--'}`, 25, y);

        // 3. Disclaimer
        y = 250;
        pdf.setFontSize(8);
        pdf.setTextColor(150, 150, 150);
        pdf.text("Este reporte contiene análisis estratégico avanzado basado en modelos matemáticos y estadística delictual.", 20, y);
    },

    /**
     * Table of Contents
     */
    generateTOC(pdf) {
        const { pageWidth } = this.config;

        pdf.setFontSize(20);
        pdf.setTextColor(30, 41, 59);
        pdf.text("Índice de Contenidos", pageWidth / 2, 30, { align: "center" });

        let y = 50;
        const views = this.config.views;

        views.forEach((viewName, index) => {
            const meta = this.viewMeta[viewName];

            // Level Header
            pdf.setFontSize(11);
            pdf.setFont("helvetica", "bold");
            pdf.setTextColor(37, 99, 235);
            pdf.text(meta.level, 20, y);
            y += 6;

            // Item
            pdf.setFontSize(10);
            pdf.setFont("helvetica", "normal");
            pdf.setTextColor(51, 65, 85);
            pdf.text(meta.title, 30, y);

            // Page num
            const pageNum = index + 4; // Cover=1, Exec=2, TOC=3
            pdf.text(String(pageNum), 190, y, { align: "right" });

            // Dotted line
            pdf.setDrawColor(200, 200, 200);
            pdf.setLineDash([0.5, 3], 0);
            pdf.line(30 + pdf.getTextWidth(meta.title) + 2, y - 1, 182, y - 1);

            y += 8;
        });
    },

    addHeaderV2(pdf, viewNum, title) {
        pdf.setFillColor(241, 245, 249);
        pdf.rect(0, 0, 210, 15, 'F');

        pdf.setFontSize(10);
        pdf.setTextColor(100, 116, 139);
        pdf.text(title, 105, 10, { align: 'center' });
    },

    addFooterV2(pdf, pageNum) {
        const y = 290;
        pdf.setFontSize(8);
        pdf.setTextColor(148, 163, 184);
        pdf.text(`Página ${pageNum}`, 195, y, { align: 'right' });
        pdf.text("Confidencial - Uso Exclusivo", 105, y, { align: 'center' });
    }
};

/**
 * Helper: V2 Cover Page
 */
function generateCoverV2(pdf) {
    const state = window.STATE_DATA || {};
    const w = 210, h = 297;

    // Background
    pdf.setFillColor(15, 23, 42); // Slate 900
    pdf.rect(0, 0, w, h, 'F');

    // Title
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(32);
    pdf.setTextColor(255, 255, 255);
    pdf.text("INFORME ESTRATÉGICO", w / 2, 120, { align: "center" });
    pdf.text("DE SEGURIDAD MUNICIPAL", w / 2, 135, { align: "center" });

    // Subtitle
    pdf.setFontSize(18);
    pdf.setTextColor(148, 163, 184);
    pdf.text(state.comunaName ? state.comunaName.toUpperCase() : "COMUNA", w / 2, 160, { align: "center" });

    // Date
    pdf.setFontSize(12);
    pdf.text(state.semanaDetalle || "", w / 2, 175, { align: "center" });

    // Line
    pdf.setDrawColor(59, 130, 246);
    pdf.setLineWidth(1);
    pdf.line(60, 190, 150, 190);

    // Bottom logo
    pdf.setFontSize(10);
    pdf.text("ILUSTRE MUNICIPALIDAD DE ALGARROBO", w / 2, 270, { align: "center" });
    pdf.setFontSize(8);
    pdf.text("SEGURIDAD MUNICIPAL", w / 2, 275, { align: "center" });
}
