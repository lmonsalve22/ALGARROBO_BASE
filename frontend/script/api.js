

const API_CONFIG = {
    BASE_URL: "https://186.67.61.251:8000",
    get token() {
        return localStorage.getItem('authToken');
    }
};

const api = {
    async request(endpoint, options = {}, responseType = 'json') {
        const url = endpoint.startsWith('http') ? endpoint : `${API_CONFIG.BASE_URL}${endpoint}`;

        const headers = {
            'Authorization': API_CONFIG.token ? `Bearer ${API_CONFIG.token}` : ''
        };

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
                const errorText = await response.text().catch(() => '');
                console.error(`[API ${response.status}] ${endpoint} Response:`, errorText);
                let errorData = {};
                try { errorData = JSON.parse(errorText); } catch (e) { }
                throw new Error(errorData.detail || errorData.error || errorData.message || `Error ${response.status}`);
            }

            if (responseType === 'blob') {
                return await response.blob();
            }
            if (responseType === 'text') {
                return await response.text();
            }
            if (responseType === 'raw') {
                return response;
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

    getBlob(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'GET' }, 'blob');
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
