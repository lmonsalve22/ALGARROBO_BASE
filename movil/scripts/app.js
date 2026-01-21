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
            admin: 'Panel de Control',
            map: 'Mapa',
            profile: 'Mi Perfil',
            'report-form': 'Nuevo Reporte',
            'report-detail': 'Detalle de Reporte',
            'edit-report': 'Editar Reporte'
        };

        document.getElementById('header-title').textContent = titles[viewName] || 'App';

        // Mostrar/ocultar botón atrás
        const showBack = ['register', 'login', 'report-form', 'report-detail', 'edit-report'].includes(viewName);
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

            // Obtener dirección automáticamente
            const address = await geo.getAddress(position.lat, position.lng);
            // Usar ID para mayor especificidad (asegurarse de agregar id="direccion_referencia" en el HTML)
            // O buscar dentro del formulario activo
            const activeForm = document.querySelector('.view.active form');
            if (activeForm) {
                const input = activeForm.querySelector('input[name="direccion_referencia"]');
                if (input) input.value = address;
            }
        } catch (error) {
            ui.hideLoading();
            ui.showToast('✗ No se pudo obtener la ubicación');
        }
    },

    previewPhotos(eventOrFiles) {
        // Obtenemos los nuevos archivos seleccionados
        let newFiles = [];
        if (eventOrFiles.target && eventOrFiles.target.files) {
            newFiles = Array.from(eventOrFiles.target.files);
            // Limpiamos el input para permitir seleccionar la misma foto de nuevo si se borró
            eventOrFiles.target.value = '';
        } else { // Asumimos que es FileList o Array
            newFiles = Array.from(eventOrFiles);
        }

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
            // Obtener el ID de categoría del input que está dentro del formulario que disparó el evento
            const categoryInput = form.querySelector('#report-category-id') || document.getElementById('report-category-id');
            const categoryId = parseInt(categoryInput.value);

            // Crear reporte en el backend
            const reportData = {
                categoria_id: categoryId,
                gravedad_id: parseInt(formData.get('gravedad_id')) || 1,
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

        // Permitir mover el marcador haciendo click/tap en el mapa
        appState.maps.picker.on('click', async (e) => {
            appState.maps.pickerMarker.setLatLng(e.latlng);
            // Actualizar dirección
            const address = await geo.getAddress(e.latlng.lat, e.latlng.lng);

            const activeForm = document.querySelector('.view.active form');
            if (activeForm) {
                const input = activeForm.querySelector('input[name="direccion_referencia"]');
                if (input) input.value = address;
            }
        });

        // Evento dragend para actualizar dirección al soltar el marcador
        appState.maps.pickerMarker.on('dragend', async (e) => {
            const latlng = e.target.getLatLng();
            const address = await geo.getAddress(latlng.lat, latlng.lng);

            const activeForm = document.querySelector('.view.active form');
            if (activeForm) {
                const input = activeForm.querySelector('input[name="direccion_referencia"]');
                if (input) input.value = address;
            }
        });
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
        // Cargar estados dinámicamente si no existen
        if (!appState.estados) {
            try {
                appState.estados = await api.getEstados();
            } catch (e) {
                console.error('Error cargando estados', e);
                appState.estados = [
                    { id: 1, nombre: 'Reportado' }, { id: 2, nombre: 'Verificado' },
                    { id: 3, nombre: 'Programado' }, { id: 4, nombre: 'Reparado' }, { id: 5, nombre: 'Descartado' }
                ];
            }
        }
        // Cargar gravedades
        if (!appState.gravedades) {
            try {
                appState.gravedades = await api.getGravedades();
            } catch (e) {
                console.error('Error cargando gravedades', e);
                appState.gravedades = [
                    { id: 1, nombre: 'Bajo' }, { id: 2, nombre: 'Moderado' },
                    { id: 3, nombre: 'Grave' }, { id: 4, nombre: 'Muy Grave' }
                ];
            }
        }
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

        container.innerHTML = list.map(r => {
            const currentStatusId = r.estado_id || 1;
            const currentGravedadId = r.gravedad_id || 1;

            return `
            <div class="report-card-admin ${r.categoria?.toLowerCase()}">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <strong>#${r.id} ${r.categoria}</strong>
                        <p style="color:#64748b; font-size:0.85em; margin:2px 0;">
                            <i class="fas fa-user" style="margin-right:4px;"></i>${r.reportado_por_nombre || 'Usuario'}
                        </p>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:0.85em; background:#e2e8f0; padding:2px 8px; border-radius:4px;">
                            ${r.estado || 'Reportado'}
                        </span>
                        <span style="font-size:0.75em; display:block; margin-top:4px; color:#64748b;">
                            ${r.gravedad || 'Bajo'}
                        </span>
                    </div>
                </div>
                <p style="color:#64748b; font-size:0.9em; margin:5px 0;">${r.direccion_referencia}</p>
                <p style="color:#94a3b8; font-size:0.8em;">${ui.formatDate(r.fecha_reporte)}</p>
                
                <div class="admin-actions" style="flex-direction: column; align-items: stretch; gap: 10px;">
                    <div style="display:flex; gap:8px;">
                        <button onclick="reports.showDetail(${r.id})" class="btn-action" style="background:#f1f5f9; flex:1;">
                            <i class="fas fa-eye"></i> Ver
                        </button>
                        <button onclick="admin.openEdit(${r.id})" class="btn-action" style="background:#3b82f6; color:white; flex:1;">
                            <i class="fas fa-edit"></i> Editar
                        </button>
                    </div>
                    
                    <div style="display:flex; gap:10px; flex-wrap:wrap;">
                        <div style="flex:1; min-width:120px; background:#f8fafc; padding:8px; border-radius:6px;">
                            <label style="font-size:0.75rem; color:#64748b; display:block; margin-bottom:4px;">Estado:</label>
                            <select onchange="admin.updateReport(${r.id}, 'estado_id', this.value)" style="width:100%; padding:6px; border-radius:4px; border:1px solid #cbd5e1;">
                                ${appState.estados.map(est => `
                                    <option value="${est.id}" ${currentStatusId == est.id ? 'selected' : ''}>${est.nombre}</option>
                                `).join('')}
                            </select>
                        </div>
                        <div style="flex:1; min-width:120px; background:#f8fafc; padding:8px; border-radius:6px;">
                            <label style="font-size:0.75rem; color:#64748b; display:block; margin-bottom:4px;">Gravedad:</label>
                            <select onchange="admin.updateReport(${r.id}, 'gravedad_id', this.value)" style="width:100%; padding:6px; border-radius:4px; border:1px solid #cbd5e1;">
                                ${appState.gravedades.map(g => `
                                    <option value="${g.id}" ${currentGravedadId == g.id ? 'selected' : ''}>${g.nombre}</option>
                                `).join('')}
                            </select>
                        </div>
                    </div>
                    
                    <label style="display:flex; align-items:center; gap:8px; background:#f0fdf4; padding:8px; border-radius:6px; cursor:pointer;">
                        <input type="checkbox" ${r.revisado ? 'checked' : ''} onchange="admin.updateReport(${r.id}, 'revisado', this.checked)">
                        <span style="font-size:0.85rem; color:#16a34a;">Revisado</span>
                    </label>
                </div>
            </div>
            `;
        }).join('');
    },

    filter(type, btn) {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        let filtered = this.reports;
        switch (type) {
            case 'pendientes':
                filtered = this.reports.filter(r => r.estado_id === 1);
                break;
            case 'en_proceso':
                filtered = this.reports.filter(r => [2, 3].includes(r.estado_id));
                break;
            case 'resueltos':
                filtered = this.reports.filter(r => r.estado_id === 4);
                break;
            case 'descartados':
                filtered = this.reports.filter(r => r.estado_id === 5);
                break;
            case 'no_revisados':
                filtered = this.reports.filter(r => !r.revisado);
                break;
            case 'graves':
                filtered = this.reports.filter(r => r.gravedad_id >= 3);
                break;
            // Categorías
            case 'cat_bache':
                filtered = this.reports.filter(r => r.categoria_id === 1 || r.categoria?.toLowerCase() === 'bache');
                break;
            case 'cat_luz':
                filtered = this.reports.filter(r => r.categoria_id === 2 || r.categoria?.toLowerCase() === 'luz');
                break;
            case 'cat_aceras':
                filtered = this.reports.filter(r => r.categoria_id === 3 || r.categoria?.toLowerCase() === 'aceras');
                break;
            case 'cat_otro':
                filtered = this.reports.filter(r => r.categoria_id === 4 || r.categoria?.toLowerCase() === 'otro');
                break;
            // Tiempo
            case 'hoy':
                const hoy = new Date().toISOString().split('T')[0];
                filtered = this.reports.filter(r => r.fecha_reporte?.startsWith(hoy));
                break;
            case 'semana':
                const ahora = new Date();
                const hace7Dias = new Date(ahora.getTime() - 7 * 24 * 60 * 60 * 1000);
                filtered = this.reports.filter(r => {
                    if (!r.fecha_reporte) return false;
                    const fechaReporte = new Date(r.fecha_reporte);
                    return fechaReporte >= hace7Dias;
                });
                break;
            default:
                filtered = this.reports;
        }
        this.renderList(filtered);
    },

    async updateReport(id, field, value) {
        ui.showLoading();
        try {
            const data = {};
            data[field] = value;

            // Auto-marcar como revisado cuando se cambia estado o gravedad
            if (field === 'estado_id' || field === 'gravedad_id') {
                data.revisado = true;
            }

            await api.updateReport(id, data);
            ui.showToast('✓ Actualizado');
            this.loadReports();
        } catch (e) {
            ui.showToast('✗ Error: ' + e.message);
            this.loadReports();
        } finally {
            ui.hideLoading();
        }
    },

    // Abrir vista de edición completa
    async openEdit(reportId) {
        ui.showLoading();
        try {
            const report = await api.getReportDetail(reportId);
            this.populateEditForm(report);
            app.showView('edit-report');
        } catch (e) {
            ui.showToast('✗ Error cargando reporte');
        } finally {
            ui.hideLoading();
        }
    },

    populateEditForm(report) {
        document.getElementById('edit-report-id').value = report.id;
        document.getElementById('edit-direccion').value = report.direccion_referencia || '';
        document.getElementById('edit-descripcion').value = report.descripcion || '';
        document.getElementById('edit-categoria').value = report.categoria_id || 1;
        document.getElementById('edit-revisado').checked = report.revisado || false;

        // Poblar selectores dinámicos
        const estadoSelect = document.getElementById('edit-estado');
        estadoSelect.innerHTML = appState.estados.map(e =>
            `<option value="${e.id}" ${report.estado_id == e.id ? 'selected' : ''}>${e.nombre}</option>`
        ).join('');

        const gravedadSelect = document.getElementById('edit-gravedad');
        gravedadSelect.innerHTML = appState.gravedades.map(g =>
            `<option value="${g.id}" ${report.gravedad_id == g.id ? 'selected' : ''}>${g.nombre}</option>`
        ).join('');
    },

    async saveEdit(event) {
        event.preventDefault();
        const form = event.target;
        const reportId = document.getElementById('edit-report-id').value;

        ui.showLoading();
        try {
            const data = {
                direccion_referencia: document.getElementById('edit-direccion').value,
                descripcion: document.getElementById('edit-descripcion').value,
                categoria_id: parseInt(document.getElementById('edit-categoria').value),
                estado_id: parseInt(document.getElementById('edit-estado').value),
                gravedad_id: parseInt(document.getElementById('edit-gravedad').value),
                revisado: document.getElementById('edit-revisado').checked
            };

            await api.updateReport(reportId, data);
            ui.showToast('✓ Reporte actualizado');
            app.showView('admin');
            this.loadReports();
        } catch (e) {
            ui.showToast('✗ Error: ' + e.message);
        } finally {
            ui.hideLoading();
        }
    },

    // Mantener por compatibilidad
    async changeStatus(id, newStatusId) {
        await this.updateReport(id, 'estado_id', parseInt(newStatusId));
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
