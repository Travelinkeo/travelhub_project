document.addEventListener('alpine:init', () => {
    Alpine.data('proveedorForm', () => ({
        activeTab: 'general',
        proveedorId: null,
        comisionesList: [],
        comisionesIds: [],
        tiposServicio: [],
        monedas: [],
        showModal: false,
        newRegla: {
            tipo_servicio: '',
            comision_porcentaje: '',
            comision_monto_fijo: '',
            moneda: ''
        },

        init() {
            const ds = this.$el.dataset;
            this.proveedorId = ds.proveedorId ? parseInt(ds.proveedorId) : null;
            let url = ds.comisionesUrl || '/api/comisiones/';
            if (!url.endsWith('/')) url += '/';
            this._comisionesUrl = url;
            this._csrf = ds.csrf || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

            const tiposEl = document.getElementById('tipos-servicio');
            const monedasEl = document.getElementById('monedas-data');
            if (tiposEl) this.tiposServicio = JSON.parse(tiposEl.textContent);
            if (monedasEl) this.monedas = JSON.parse(monedasEl.textContent);

            if (this.proveedorId) {
                this.fetchComisiones();
            }
        },

        async fetchComisiones() {
            try {
                const response = await fetch(`${this._comisionesUrl}?proveedor=${this.proveedorId}`);
                if (!response.ok) throw new Error('Error cargando comisiones');
                const data = await response.json();
                this.comisionesList = Array.isArray(data) ? data : (data.results || []);
                this.comisionesIds = this.comisionesList.map(c => c.id_comision);
            } catch (error) {
                console.error(error);
                this.comisionesList = [];
                this.comisionesIds = [];
            }
        },

        openModal() {
            this.newRegla = { tipo_servicio: '', comision_porcentaje: '', comision_monto_fijo: '', moneda: '', proveedor: this.proveedorId };
            this.showModal = true;
        },

        async saveRegla() {
            if (!this.newRegla.tipo_servicio) {
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: 'Seleccione un tipo de servicio', type: 'error' }
                }));
                return;
            }
            const payload = {
                tipo_servicio: this.newRegla.tipo_servicio,
                comision_porcentaje: this.newRegla.comision_porcentaje !== '' && this.newRegla.comision_porcentaje !== null ? parseFloat(this.newRegla.comision_porcentaje) : null,
                comision_monto_fijo: this.newRegla.comision_monto_fijo !== '' && this.newRegla.comision_monto_fijo !== null ? parseFloat(this.newRegla.comision_monto_fijo) : null,
                moneda: this.newRegla.moneda !== '' && this.newRegla.moneda !== null ? parseInt(this.newRegla.moneda) : null,
                notas: this.newRegla.notas || null,
                proveedor: this.proveedorId
            };
            try {
                const response = await fetch(this._comisionesUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this._csrf
                    },
                    body: JSON.stringify(payload)
                });
                if (response.ok) {
                    this.showModal = false;
                    this.fetchComisiones();
                } else {
                    const data = await response.json();
                    window.dispatchEvent(new CustomEvent('notify', {
                        detail: { message: 'Error: ' + JSON.stringify(data), type: 'error' }
                    }));
                }
            } catch (error) {
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: 'Error de red al guardar la regla', type: 'error' }
                }));
            }
        },

        async deleteRegla(id) {
            if (!confirm('¿Seguro que desea eliminar esta regla?')) return;
            try {
                const response = await fetch(`${this._comisionesUrl}${id}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': this._csrf
                    }
                });
                if (response.ok) {
                    this.fetchComisiones();
                }
            } catch (e) {
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: 'Error eliminando', type: 'error' }
                }));
            }
        },

        formatCurrency(val) {
            return parseFloat(val).toFixed(2);
        }
    }));
});
