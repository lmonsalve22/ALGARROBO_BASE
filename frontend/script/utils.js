
/**
 * Utility Functions - Geoportal Municipal
 * Formateo de datos, validaciones y manipulación de DOM común.
 */

const utils = {
    /**
     * Formatea un número a moneda CLP
     */
    formatCurrency(value) {
        if (!value && value !== 0) return '$0';
        return new Intl.NumberFormat('es-CL', {
            style: 'currency',
            currency: 'CLP',
            minimumFractionDigits: 0
        }).format(value);
    },

    /**
     * Formatea una fecha ISO a formato local DD/MM/YYYY
     */
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('es-CL', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });
        } catch (e) {
            return dateString;
        }
    },

    /**
     * Genera un color/clase de badge basado en un estado
     */
    getStatusClass(status) {
        const s = String(status).toLowerCase();
        if (s.includes('aprobado') || s.includes('finalizado') || s.includes('ejecución')) return 'badge-success';
        if (s.includes('proceso') || s.includes('licitación') || s.includes('diseño')) return 'badge-info';
        if (s.includes('pendiente') || s.includes('espera')) return 'badge-warning';
        if (s.includes('rechazado') || s.includes('cancelado')) return 'badge-danger';
        return 'badge-gray';
    },

    /**
     * Serializa un formulario a objeto
     */
    serializeForm(formElement) {
        const formData = new FormData(formElement);
        const obj = {};
        formData.forEach((value, key) => {
            obj[key] = value;
        });
        return obj;
    },

    /**
     * Formatea un número a formato compacto (K, M, B)
     */
    formatCompactNumber(number) {
        if (!number) return '0';
        if (number >= 1000000000) return '$' + (number / 1000000000).toFixed(1) + 'B';
        if (number >= 1000000) return '$' + (number / 1000000).toFixed(1) + 'M';
        if (number >= 1000) return '$' + (number / 1000).toFixed(1) + 'K';
        return '$' + number.toString();
    },

    /**
     * Llena un select con datos dinámicos
     */
    fillSelect(elementId, items, valueField, textField, placeholder = 'Seleccione una opción') {
        const select = document.getElementById(elementId);
        if (!select) return;

        const currentValue = select.value;
        select.innerHTML = `<option value="">${placeholder}</option>`;

        items.forEach(item => {
            const option = document.createElement('option');
            option.value = item[valueField];
            option.textContent = item[textField];
            if (String(item[valueField]) === String(currentValue)) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    }
};
