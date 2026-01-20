// ==========================================
// APP PRINCIPAL - Lógica de la Aplicación
// ==========================================

// Estado global de la aplicación
const appState = {
    currentView: 'welcome',
    user: null,
    currentReport: null,
    selectedPhotos: [],
    maps: {
        picker: null,
        full: null,
        detail: null,
        pickerMarker: null
    }
};

// ==========================================
// NAVEGACIÓN Y VISTAS
// ==========================================

const app = {
    init() {
        // Verificar sesión
        if (!api.token) {
            window.location.href = 'index.html';
            return;
        }

        this.loadUserData();

        document.getElementById('bottom-nav').classList.add('show');
        // Mostrar logout siempre
        const btnLogout = document.getElementById('btn-logout');
        if (btnLogout) btnLogout.style.display = 'block';

        // Determinar vista inicial según modo
        const mode = window.APP_MODE || 'vecino';

        if (mode === 'funcionario') {
            // Inicializar admin
            this.showView('admin');
            // Asegurar que el nav item de gestión sea visible y activo
            const navAdmin = document.getElementById('nav-admin');
            if (navAdmin) {
                navAdmin.style.display = 'flex';
                navAdmin.classList.add('active');
            }
        } else {
            this.showView('home');
        }
    },

    showView(viewName) {
        // Ocultar todas las vistas
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

        // Resetear navegación
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));

        // Mostrar vista seleccionada
        const view = document.getElementById(`view-${viewName}`);
        if (view) {
            view.classList.add('active');
            appState.currentView = viewName;

            // Actualizar header
            this.updateHeader(viewName);

            // Actualizar navegación activa
            const navItem = document.querySelector(`.nav-item[onclick*="${viewName}"]`);
            if (navItem) navItem.classList.add('active');

            // Acciones específicas por vista
            this.onViewChange(viewName);
        }
    },

    updateHeader(viewName) {
        const titles = {
            welcome: 'Reportes Ciudadanos',
            register: 'Registrarse',
            login: 'Iniciar Sesión',
            home: 'Inicio',
            map: 'Mapa',
            profile: 'Mi Perfil',
            'report-form': 'Nuevo Reporte',
            'report-detail': 'Detalle de Reporte'
        };

        document.getElementById('header-title').textContent = titles[viewName] || 'App';

        // Mostrar/ocultar botón atrás
        const showBack = ['register', 'login', 'report-form', 'report-detail'].includes(viewName);
        document.getElementById('btn-back').style.display = showBack ? 'block' : 'none';
    },

    onViewChange(viewName) {
        switch (viewName) {
            case 'home':
                reports.loadMyReports();
                break;
            case 'map':
                setTimeout(() => maps.initFullMap(), 100);
                break;
            case 'profile':
                this.loadProfile();
                break;
            case 'admin':
                admin.init();
                break;
        }
    },

    goBack() {
        // Navegar a vista anterior (por defecto home)
        this.showView('home');
    },

    async loadUserData() {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        appState.user = user;

        // Verificar si es funcionario (nivel_acceso > 0)
        // Vecino = 0 (o null), Funcionario >= 1
        const nivel = parseInt(user.nivel_acceso || 0);

        const navAdmin = document.getElementById('nav-admin');
        if (navAdmin) {
            navAdmin.style.display = (nivel > 0) ? 'flex' : 'none';
        }
    },

    async loadProfile() {
        if (!appState.user) return;

        document.getElementById('profile-name').textContent = appState.user.nombre || 'Usuario';
        document.getElementById('profile-email').textContent = appState.user.email || '';

        // Cargar estadísticas (simuladas por ahora)
        document.getElementById('stat-total').textContent = '0';
        document.getElementById('stat-pending').textContent = '0';
        document.getElementById('stat-resolved').textContent = '0';
    },

    async logout() {
        if (confirm('¿Cerrar sesión?')) {
            api.clearToken();
            localStorage.removeItem('user');
            window.location.href = 'index.html';
        }
    }
};

// ==========================================
// AUTENTICACIÓN
// ==========================================

const auth = {
    async register(event) {
        event.preventDefault();

        const form = event.target;
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);

        ui.showLoading();

        try {
            const result = await api.register(data.nombre, data.email, data.password);

            ui.hideLoading();
            ui.showToast('✓ Registro exitoso!');

            // Redirigir al login después de 1 segundo
            setTimeout(() => {
                app.showView('login');
            }, 1000);

        } catch (error) {
            ui.hideLoading();
            ui.showToast('✗ Error: ' + error.message);
        }
    },

    async login(event) {
        event.preventDefault();

        const form = event.target;
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);

        ui.showLoading();

        try {
            const result = await api.login(data.email, data.password);

            // Guardar datos del usuario
            localStorage.setItem('user', JSON.stringify(result.user));
            appState.user = result.user;

            ui.hideLoading();
            ui.showToast('✓ Bienvenido!');

            // Mostrar navegación y cambiar a home
            document.getElementById('bottom-nav').classList.add('show');
            document.getElementById('btn-logout').style.display = 'block';
            app.showView('home');

        } catch (error) {
            ui.hideLoading();
            ui.showToast('✗ Credenciales inválidas');
        }
    }
};

// ==========================================
// REPORTES
// ==========================================

const reports = {
    openForm(categoryId) {
        app.showView('report-form');
        document.getElementById('report-category-id').value = categoryId;

        // Inicializar mapa pequeño
        setTimeout(() => {
            maps.initPickerMap();
        }, 100);

        // Limpiar formulario
        document.getElementById('report-form').reset();
        appState.selectedPhotos = [];
        document.getElementById('photo-previews').innerHTML = '';
    },

    async useGPS() {
        ui.showLoading();
        try {
            const position = await geo.getCurrentPosition();
            maps.setPickerPosition(position.lat, position.lng);
            ui.hideLoading();
            ui.showToast('✓ Ubicación actualizada');
        } catch (error) {
            ui.hideLoading();
            ui.showToast('✗ No se pudo obtener la ubicación');
        }
    },

    previewPhotos(event) {
        // Obtenemos los nuevos archivos seleccionados
        const newFiles = Array.from(event.target.files);

        // Si no hay archivos nuevos, no hacemos nada (usuario canceló)
        if (newFiles.length === 0) return;

        // Combinamos con los existentes
        // Nota: Esto permite agregar fotos en tandas
        const currentPhotos = appState.selectedPhotos || [];
        const combinedPhotos = [...currentPhotos, ...newFiles];

        // Validar límite (5 fotos)
        if (combinedPhotos.length > 5) {
            ui.showToast('Máximo 5 fotos en total. Se han ignorado algunas.');
            // Cortamos el array para quedarnos con las primeras 5
            appState.selectedPhotos = combinedPhotos.slice(0, 5);
        } else {
            appState.selectedPhotos = combinedPhotos;
        }

        this.renderPhotoPreviews();

        // Limpiamos el input para permitir seleccionar la misma foto de nuevo si se borró
        event.target.value = '';
    },

    renderPhotoPreviews() {
        const container = document.getElementById('photo-previews');
        container.innerHTML = '';

        appState.selectedPhotos.forEach((file, index) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const preview = document.createElement('div');
                preview.className = 'photo-preview';
                preview.innerHTML = `
                    <img src="${e.target.result}" alt="Foto ${index + 1}">
                    <button type="button" class="photo-remove" onclick="reports.removePhoto(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                container.appendChild(preview);
            };
            reader.readAsDataURL(file);
        });
    },

    removePhoto(index) {
        // Borrar del array directamente usando splice
        appState.selectedPhotos.splice(index, 1);
        // Re-renderizar
        this.renderPhotoPreviews();
    },

    async submit(event) {
        event.preventDefault();

        const form = event.target;
        const formData = new FormData(form);

        const position = maps.getPickerPosition();
        if (!position) {
            ui.showToast('Selecciona una ubicación en el mapa');
            return;
        }

        ui.showLoading();

        try {
            // Crear reporte (simulado por ahora, falta endpoint en backend)
            const reportData = {
                categoria_id: parseInt(document.getElementById('report-category-id').value),
                latitud: position.lat,
                longitud: position.lng,
                direccion_referencia: formData.get('direccion_referencia'),
                descripcion: formData.get('descripcion')
            };

            const result = await api.createReport(reportData);

            // Si hay fotos, subirlas
            if (appState.selectedPhotos.length > 0 && result.id) {
                await api.uploadPhotos(result.id, appState.selectedPhotos, {
                    latitud: position.lat,
                    longitud: position.lng
                });
            }

            ui.hideLoading();
            ui.showToast('✓ Reporte enviado exitosamente');

            setTimeout(() => {
                app.showView('home');
            }, 1000);

        } catch (error) {
            ui.hideLoading();
            ui.showToast('✗ Error al enviar: ' + error.message);
        }
    },

    async loadMyReports() {
        const container = document.getElementById('my-reports-list');
        container.innerHTML = '<p style="text-align:center;color:#999;">Cargando...</p>';

        try {
            const reports = await api.getMyReports();

            if (reports.length === 0) {
                container.innerHTML = '<p style="text-align:center;color:#999;">No tienes reportes aún</p>';
                return;
            }

            container.innerHTML = reports.map(r => this.renderReportCard(r)).join('');

        } catch (error) {
            container.innerHTML = '<p style="text-align:center;color:#999;">Error al cargar reportes</p>';
        }
    },

    renderReportCard(report) {
        const categoryClass = report.categoria?.toLowerCase() || 'otro';
        return `
            <div class="report-card ${categoryClass}" onclick="reports.showDetail(${report.id})">
                <div class="report-header">
                    <span class="report-title">${report.categoria || 'Reporte'}</span>
                    <span class="report-status">${report.estado || 'Reportado'}</span>
                </div>
                <div class="report-address">${report.direccion_referencia}</div>
                <div class="report-date">${ui.formatDate(report.fecha_reporte)}</div>
            </div>
        `;
    },

    async showDetail(reportId) {
        app.showView('report-detail');

        const container = document.getElementById('report-detail-content');
        container.innerHTML = '<p style="text-align:center;padding:20px;">Cargando detalle...</p>';

        try {
            const report = await api.getReportDetail(reportId);
            const photos = await api.getPhotos(reportId);
            const comments = await api.getComments(reportId);

            // Construir galería de fotos
            let photosHtml = '';
            if (photos.length > 0) {
                photosHtml = `
                    <div class="detail-section">
                        <h4>Evidencias Fotográficas (${photos.length})</h4>
                        <div class="photo-gallery">
                            ${photos.map(p => `
                                <div class="photo-card" onclick="ui.showImageModal('${API_BASE}${p.ruta_archivo}')">
                                    <div class="photo-wrapper" style="background-image: url('${API_BASE}${p.ruta_archivo}')"></div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            container.innerHTML = `
                <div class="detail-header-card">
                    <div class="detail-top">
                        <span class="badge ${report.categoria?.toLowerCase() || 'otro'}">${report.categoria}</span>
                        <span class="status-badge status-${report.estado?.toLowerCase() || 'pendiente'}">${report.estado}</span>
                    </div>
                    <h2 class="detail-id">Folio #${report.numero_folio || report.id}</h2>
                    <p class="detail-date"><i class="far fa-clock"></i> ${ui.formatDate(report.fecha_reporte)}</p>
                    <p class="detail-address"><i class="fas fa-map-marker-alt"></i> ${report.direccion_referencia}</p>
                    
                    <div class="detail-map-container">
                        <div id="detail-map" style="height: 200px; width: 100%; border-radius: 8px; margin-top: 10px;"></div>
                    </div>
                </div>
                
                <div class="detail-section">
                    <h4>Descripción</h4>
                    <p class="detail-text">${report.descripcion || 'Sin descripción proporcionada.'}</p>
                </div>
                
                ${photosHtml}
                
                <div class="detail-section">
                    <h4>Comentarios y Actualizaciones</h4>
                    <div class="comments-list" id="comments-list">
                        ${comments.length ? comments.map(c => `
                            <div class="comment-item">
                                <div class="comment-avatar"><i class="fas fa-user"></i></div>
                                <div class="comment-content">
                                    <div class="comment-header">
                                        <span class="comment-author">${c.autor || 'Usuario'}</span>
                                        <span class="comment-time">${ui.formatDate(c.creado_en)}</span>
                                    </div>
                                    <p class="comment-text">${c.comentario}</p>
                                </div>
                            </div>
                        `).join('') : '<p class="no-data">No hay comentarios aún.</p>'}
                    </div>
                    
                    <div class="comment-form-container">
                        <input type="text" id="comment-input" placeholder="Escribe un comentario..." />
                        <button onclick="reports.sendComment(${report.id})">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                </div>
            `;

            // Inicializar mapa de detalle si hay coordenadas
            if (report.latitud && report.longitud) {
                setTimeout(() => {
                    maps.initDetailMap(report.latitud, report.longitud);
                }, 100);
            }

        } catch (error) {
            console.error(error);
            container.innerHTML = '<div class="error-msg">No se pudo cargar la información del reporte.</div>';
        }
    },

    async sendComment(reportId) {
        const input = document.getElementById('comment-input');
        const comentario = input.value.trim();

        if (!comentario) return;

        try {
            await api.addComment(reportId, comentario);
            input.value = '';
            ui.showToast('✓ Comentario enviado');
            // Recargar comentarios
            this.showDetail(reportId);
        } catch (error) {
            ui.showToast('✗ Error al enviar comentario');
        }
    }
};

// ==========================================
// MAPAS
// ==========================================

const maps = {
    initPickerMap() {
        if (appState.maps.picker) {
            appState.maps.picker.invalidateSize();
            return;
        }

        const container = document.getElementById('map-picker');
        if (!container) return;

        // Algarrobo, Chile como centro por defecto
        const center = [-33.357, -71.655];

        appState.maps.picker = L.map('map-picker').setView(center, 15);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap'
        }).addTo(appState.maps.picker);

        // Marker arrastrable
        appState.maps.pickerMarker = L.marker(center, { draggable: true })
            .addTo(appState.maps.picker);
    },

    initDetailMap(lat, lng) {
        if (appState.maps.detail) {
            appState.maps.detail.remove();
            appState.maps.detail = null;
        }

        const container = document.getElementById('detail-map');
        if (!container) return;

        appState.maps.detail = L.map('detail-map', {
            zoomControl: false,
            attributionControl: false
        }).setView([lat, lng], 15);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(appState.maps.detail);
        L.marker([lat, lng]).addTo(appState.maps.detail);
    },

    setPickerPosition(lat, lng) {
        if (!appState.maps.picker) return;

        appState.maps.pickerMarker.setLatLng([lat, lng]);
        appState.maps.picker.panTo([lat, lng]);
    },

    getPickerPosition() {
        if (!appState.maps.pickerMarker) return null;
        const pos = appState.maps.pickerMarker.getLatLng();
        return { lat: pos.lat, lng: pos.lng };
    },

    async initFullMap() {
        if (appState.maps.full) {
            appState.maps.full.invalidateSize();
            this.loadMapMarkers();
            return;
        }

        const container = document.getElementById('full-map');
        if (!container) return;

        const center = [-33.357, -71.655];

        appState.maps.full = L.map('full-map').setView(center, 14);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap'
        }).addTo(appState.maps.full);

        // Cargar reportes
        await this.loadMapMarkers();
    },

    async loadMapMarkers() {
        if (!appState.maps.full) return;

        try {
            const reports = await api.getAllReports();

            const colors = {
                1: '#e67e22', // Bache
                2: '#f1c40f', // Luz
                3: '#95a5a6', // Aceras
                4: '#7f8c8d'  // Otro
            };

            reports.forEach(r => {
                const color = colors[r.categoria_id] || '#999';

                const icon = L.divIcon({
                    className: 'custom-marker',
                    html: `<div style="background:${color};width:15px;height:15px;border-radius:50%;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3)"></div>`,
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });

                L.marker([r.latitud, r.longitud], { icon })
                    .addTo(appState.maps.full)
                    .bindPopup(`
                        <strong>${r.categoria}</strong><br>
                        <small>${r.direccion_referencia}</small><br>
                        Estado: ${r.estado}
                    `);
            });

        } catch (error) {
            console.error('Error loading map markers:', error);
        }
    }
};

// ==========================================
// INICIALIZAR APP
// ==========================================

// ============================================
// LÓGICA ADMIN (GESTIÓN)
// ============================================
const admin = {
    reports: [],

    async init() {
        // Cargar reportes al iniciar vista admin
        this.loadReports();
    },

    async loadReports() {
        const container = document.getElementById('admin-reports-list');
        container.innerHTML = '<p style="text-align:center;padding:20px;">Cargando...</p>';
        try {
            const data = await api.getAllReports();
            this.reports = data;
            this.renderList(data);
        } catch (e) {
            console.error(e);
            container.innerHTML = '<p style="text-align:center">Error cargando datos</p>';
        }
    },

    renderList(list) {
        const container = document.getElementById('admin-reports-list');
        if (list.length === 0) {
            container.innerHTML = '<p style="text-align:center; margin-top:40px;">No hay reportes.</p>';
            return;
        }

        container.innerHTML = list.map(r => `
            <div class="report-card-admin ${r.categoria?.toLowerCase()}">
                <div style="display:flex; justify-content:space-between;">
                    <strong>#${r.id} ${r.categoria}</strong>
                    <span style="font-size:0.85em; background:#e2e8f0; padding:2px 8px; border-radius:4px;">
                        ${r.estado || 'Reportado'}
                    </span>
                </div>
                <p style="color:#64748b; font-size:0.9em; margin:5px 0;">${r.direccion_referencia}</p>
                <p style="color:#94a3b8; font-size:0.8em;">${ui.formatDate(r.fecha_reporte)}</p>
                
                <div class="admin-actions">
                    <button onclick="admin.verify(${r.id}, 'CONFIRMADO')" class="btn-action btn-verify">
                        <i class="fas fa-check"></i> Validar
                    </button>
                    <button onclick="admin.verify(${r.id}, 'RECHAZADO')" class="btn-action btn-reject">
                        <i class="fas fa-times"></i> Rechazar
                    </button>
                    <button onclick="reports.showDetail(${r.id})" class="btn-action" style="background:#f1f5f9;">
                        <i class="fas fa-eye"></i> Ver
                    </button>
                </div>
            </div>
        `).join('');
    },

    filter(type, btn) {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        if (type === 'todos') this.renderList(this.reports);
        else if (type === 'pendientes') {
            this.renderList(this.reports.filter(r => r.estado === 'Reportado'));
        } else if (type === 'verificados') {
            this.renderList(this.reports.filter(r => r.estado !== 'Reportado'));
        }
    },

    async verify(id, status) {
        if (!confirm(`¿Estás seguro de marcar como ${status}?`)) return;
        ui.showLoading();
        try {
            await api.verifyReport(id, status);
            ui.showToast('Estado actualizado');
            this.loadReports(); // Recargar
        } catch (e) {
            ui.showToast('Error: ' + e.message);
        } finally {
            ui.hideLoading();
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    app.init();
});


// ==========================================
// UTILS MODAL IMAGEN
// ==========================================
if (typeof ui !== 'undefined') {
    ui.showImageModal = function (url) {
        const modal = document.getElementById('image-modal');
        const img = document.getElementById('modal-image');
        if (modal && img) {
            img.src = url;
            modal.classList.add('show');
        }
    };

    ui.closeImageModal = function () {
        const modal = document.getElementById('image-modal');
        const img = document.getElementById('modal-image');
        if (modal) modal.classList.remove('show');
        if (img) setTimeout(() => img.src = '', 300); // Limpiar después de transición
    };

    // Cerrar al hacer clic fuera de la imagen
    const modal = document.getElementById('image-modal');
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                ui.closeImageModal();
            }
        });
    }
}
