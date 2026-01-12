
/**
 * API Wrapper - Geoportal Municipal
 * Centraliza las peticiones fetch y el manejo de tokens.
 */

const API_CONFIG = {
    BASE_URL: "https://186.67.61.251:8000",
    get token() {
        return localStorage.getItem('authToken');
    }
};

const api = {
    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${API_CONFIG.BASE_URL}${endpoint}`;

        const headers = {
            'Authorization': API_CONFIG.token ? `Bearer ${API_CONFIG.token}` : ''
        };

        // Si no es FormData, añadir Content-Type por defecto
        if (!(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        const config = {
            ...options,
            headers: {
                ...headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, config);

            // Manejo de expiración de sesión (401 Unauthorized)
            if (response.status === 401) {
                console.warn("Sesión expirada o inválida");
                if (typeof logout === 'function') {
                    logout();
                } else {
                    localStorage.clear();
                    window.location.href = '/ALGARROBO_BASE/frontend/index.html';
                }
                return;
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || errorData.message || `Error ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    },

    get(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'GET' });
    },

    post(endpoint, data, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'POST',
            body: data instanceof FormData ? data : JSON.stringify(data)
        });
    },

    put(endpoint, data, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'PUT',
            body: data instanceof FormData ? data : JSON.stringify(data)
        });
    },

    delete(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'DELETE' });
    }
};
