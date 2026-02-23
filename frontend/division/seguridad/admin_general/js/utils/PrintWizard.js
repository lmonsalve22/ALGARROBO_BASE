
const { jsPDF } = window.jspdf;

export class PrintWizard {
    constructor(pages) {
        this.pages = pages;
        this.capturedImages = {};
        this.isGenerating = false;
        this.progress = 0;
        this.currentAction = '';
        this.overlay = null;
    }

    createOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'print-wizard-overlay';
        overlay.className = 'fixed inset-0 z-[100] bg-slate-900/90 flex flex-col items-center justify-center text-white backdrop-blur-sm transition-opacity duration-300';
        overlay.style.opacity = '0';
        overlay.innerHTML = `
            <div class="w-96 text-center space-y-6">
                <div class="text-4xl animate-bounce">🖨️</div>
                <div>
                    <h3 class="text-2xl font-bold mb-1">Generando PDF</h3>
                    <p id="print-action" class="text-gray-400 text-sm">Iniciando...</p>
                </div>
                <div class="w-full bg-slate-700 rounded-full h-4 overflow-hidden shadow-inner border border-slate-600">
                    <div id="print-progress-bar" class="bg-orange-500 h-full transition-all duration-300 ease-out" style="width: 0%"></div>
                </div>
                <p class="text-xs text-slate-500">Por favor espere, procesando imágenes...</p>
            </div>
        `;
        document.body.appendChild(overlay);
        requestAnimationFrame(() => overlay.style.opacity = '1');
        this.overlay = overlay;
    }

    updateStatus(action, progress) {
        const actionEl = document.getElementById('print-action');
        const progressEl = document.getElementById('print-progress-bar');
        if (actionEl) actionEl.textContent = action;
        if (progressEl) progressEl.style.width = `${progress}%`;
    }

    removeOverlay() {
        if (this.overlay) {
            this.overlay.style.opacity = '0';
            setTimeout(() => this.overlay.remove(), 300);
        }
    }

    async capturePage(pageId, renderer) {
        // Create a hidden container for capture
        const captureContainer = document.createElement('div');
        captureContainer.style.position = 'fixed';
        captureContainer.style.left = '-9999px';
        captureContainer.style.top = '0';
        captureContainer.style.width = '210mm'; // A4 Portrait default
        captureContainer.style.minHeight = '297mm';
        captureContainer.style.backgroundColor = 'white';
        captureContainer.className = 'print-capture-container p-8';
        document.body.appendChild(captureContainer);

        // Render the page content
        await renderer(captureContainer);

        // Wait for potential animations or network loads
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Capture with html2canvas
        const canvas = await html2canvas(captureContainer, {
            scale: 2,
            useCORS: true,
            backgroundColor: '#ffffff',
            width: captureContainer.offsetWidth,
            height: captureContainer.offsetHeight
        });

        const imgData = canvas.toDataURL('image/jpeg', 0.95);
        captureContainer.remove();
        return imgData;
    }

    async start() {
        if (this.isGenerating) return;
        this.isGenerating = true;
        this.createOverlay();

        try {
            const pdf = new jsPDF({
                unit: 'mm',
                format: 'a4',
            });

            for (let i = 0; i < this.pages.length; i++) {
                const page = this.pages[i];
                const progress = Math.round((i / this.pages.length) * 100);
                this.updateStatus(`Procesando: ${page.title}`, progress);

                const imgData = await this.capturePage(page.id, page.render);

                if (i > 0) {
                    pdf.addPage();
                }

                pdf.addImage(imgData, 'JPEG', 0, 0, 210, 297);
            }

            this.updateStatus('Guardando archivo PDF...', 100);
            pdf.save(`Reporte_Seguridad_${new Date().toISOString().split('T')[0]}.pdf`);

        } catch (error) {
            console.error("Print Wizard Error:", error);
            alert("Error al generar el PDF.");
        } finally {
            this.isGenerating = false;
            this.removeOverlay();
        }
    }
}
