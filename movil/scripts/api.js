// ==========================================
// API CLIENT - Comunicación con Backend
// ==========================================

// Backend en servidor público
const API_BASE = 'https://186.67.61.251:8000';

const api = {
    // Token JWT almacenado
    token: localStorage.getItem('token') || null,

    // Configurar token
    setToken(token) {
        this.token = token;
        localStorage.setItem('token', token);
    },

    // Limpiar token
    clearToken() {
        this.token = null;
        localStorage.removeItem('token');
    },

    // Headers base
    getHeaders(includeAuth = true) {
        const headers = {
            'Content-Type': 'application/json'
        };
        if (includeAuth && this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        return headers;
    },

    // Fetch wrapper con manejo de errores
    async request(endpoint, options = {}) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                ...options,
                headers: {
                    ...this.getHeaders(options.auth !== false),
                    ...options.headers
                }
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.msg || data.message || 'Error en la petición');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    // ===== AUTENTICACIÓN =====

    async register(nombre, email, password) {
        return await this.request('/api/mobile/auth/register', {
            method: 'POST',
            auth: false,
            body: JSON.stringify({ nombre, email, password })
        });
    },

    async confirmEmail(token) {
        return await this.request(`/api/mobile/auth/confirm/${token}`, {
            method: 'GET',
            auth: false
        });
    },

    async login(email, password) {
        const data = await this.request('/api/mobile/auth/login', {
            method: 'POST',
            auth: false,
            body: JSON.stringify({ email, password })
        });

        if (data.token) {
            this.setToken(data.token);
        }

        return data;
    },

    // ===== REPORTES =====

    async createReport(reportData) {
        return await this.request('/api/mobile/reportes', {
            method: 'POST',
            body: JSON.stringify(reportData)
        });
    },

    async getMyReports() {
        return await this.request('/api/mobile/reportes/mis-reportes', {
            method: 'GET'
        });
    },

    async getReportDetail(reportId) {
        return await this.request(`/api/mobile/reportes/${reportId}`, {
            method: 'GET'
        });
    },

    async getAllReports() {
        return await this.request('/api/mobile/reportes/todos', {
            method: 'GET',
            auth: false
        });
    },

    // ===== FOTOS =====

    async uploadPhotos(reportId, files, metadata = {}) {
        console.log('Iniciando subida de fotos...', { reportId, cantidad: files.length, metadata }); // DEBUG

        if (!files || files.length === 0) {
            console.warn('No hay archivos para subir');
            return;
        }

        const formData = new FormData();

        // Agregar archivos
        for (let i = 0; i < files.length; i++) {
            console.log(`Adjuntando archivo ${i}:`, files[i].name, files[i].size); // DEBUG
            formData.append('fotos', files[i]);
        }

        // Agregar metadata
        formData.append('metadata', JSON.stringify(metadata));

        try {
            console.log('Enviando petición POST a /fotos...');
            const response = await fetch(`${API_BASE}/api/mobile/reportes/${reportId}/fotos`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`
                },
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.msg || 'Error subiendo fotos');
            }

            return data;
        } catch (error) {
            console.error('Error uploading photos:', error);
            throw error;
        }
    },

    async getPhotos(reportId) {
        return await this.request(`/api/mobile/reportes/${reportId}/fotos`, {
            method: 'GET',
            auth: false
        });
    },

    // ===== VERIFICACIONES =====

    async verifyReport(reportId, resultado) {
        return await this.request(`/api/mobile/reportes/${reportId}/verificar`, {
            method: 'POST',
            body: JSON.stringify({ resultado })
        });
    },

    // ===== COMENTARIOS =====

    async getComments(reportId) {
        return await this.request(`/api/mobile/reportes/${reportId}/comentarios`, {
            method: 'GET',
            auth: false
        });
    },

    async addComment(reportId, comentario) {
        return await this.request(`/api/mobile/reportes/${reportId}/comentarios`, {
            method: 'POST',
            body: JSON.stringify({ comentario })
        });
    }
};

// ==========================================
// UTILIDADES GEOLOCALIZACIÓN
// ==========================================

const geo = {
    async getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocalización no soportada'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    });
                },
                (error) => {
                    reject(error);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        });
    }
};

// ==========================================
// UTILIDADES UI
// ==========================================

const ui = {
    showToast(message, duration = 3000) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.classList.add('show');

        setTimeout(() => {
            toast.classList.remove('show');
        }, duration);
    },

    showLoading() {
        document.getElementById('loading-overlay').classList.add('show');
    },

    hideLoading() {
        document.getElementById('loading-overlay').classList.remove('show');
    },

    formatDate(dateString) {
        if (!dateString) return '';

        // Intentar corregir formato SQL simple (YYYY-MM-DD HH:MM:SS)
        // Algunos navegadores requieren 'T'
        let cleanDate = dateString;
        if (typeof dateString === 'string' && dateString.indexOf('T') === -1 && dateString.indexOf('-') > 0) {
            cleanDate = dateString.replace(' ', 'T');
        }

        const date = new Date(cleanDate);

        // Si es inválida
        if (isNaN(date.getTime())) {
            // Intento secundario: quizás es formato HTTPGMT
            const date2 = new Date(dateString);
            if (!isNaN(date2.getTime())) return this.formatDateRelative(date2);

            return String(dateString).substring(0, 16); // Fallback: mostrar primeros caracteres
        }

        return this.formatDateRelative(date);
    },

    formatDateRelative(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Hace un momento';
        if (diffMins < 60) {
            return `Hace ${diffMins} min`;
        } else if (diffMins < 1440) {
            return `Hace ${Math.floor(diffMins / 60)} horas`;
        } else {
            return date.toLocaleDateString('es-CL', {
                day: '2-digit',
                month: 'short',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }
};
