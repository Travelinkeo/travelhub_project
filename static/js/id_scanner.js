document.addEventListener('alpine:init', () => {
    Alpine.data('idScanner', () => ({
        loading: false,
        droping: false,
        message: '',

        init() {
            const ds = this.$el.dataset;
            this._scanUrl = ds.scanUrl || '/api/crm/cedula-scanner/';
            this._csrf = ds.csrf || '';
        },

        async processImage(file) {
            this.loading = true;
            this.message = '';

            const formData = new FormData();
            formData.append('image', file);

            try {
                const response = await fetch(this._scanUrl, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': this._csrf
                    }
                });

                const result = await response.json();

                if (result.status === 'success') {
                    const d = result.data;

                    const setField = (name, val) => {
                        if (val !== null && val !== undefined && String(val).trim() !== '' && String(val) !== '0') {
                            const el = document.querySelector(`[name="${name}"]`);
                            if (el) el.value = String(val).trim();
                        }
                    };

                    setField('nombres', d.nombres);
                    setField('apellidos', d.apellidos);
                    setField('cedula_identidad', d.cedula);
                    setField('fecha_nacimiento', d.fecha_nacimiento);

                    if (d.foto_url && !d.foto_url.includes('face_None')) {
                        const preview = document.getElementById('preview-image');
                        const placeholder = document.querySelector('.flex-col.items-center.text-text-muted');
                        if (preview) {
                            preview.src = d.foto_url;
                            preview.classList.remove('hidden');
                        }
                        if (placeholder) placeholder.classList.add('hidden');
                    }

                    const filled = [d.nombres, d.apellidos, d.cedula].filter(v => v && String(v).trim() !== '' && String(v) !== '0').length;
                    this.message = filled > 0 ? `¡Datos extraídos: ${filled} campo(s) completado(s)!` : '📷 Foto capturada. Completa los datos manualmente.';
                    setTimeout(() => this.message = '', 5000);
                } else {
                    window.dispatchEvent(new CustomEvent('notify', {
                        detail: { message: 'Error: ' + (result.error || 'No se pudo procesar la imagen'), type: 'error' }
                    }));
                }
            } catch (e) {
                console.error(e);
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: 'Error en la conexión con el servidor de IA.', type: 'error' }
                }));
            } finally {
                this.loading = false;
            }
        },

        handleFile(e) {
            const file = e.target.files[0];
            if (file) this.processImage(file);
        },

        handleDrop(e) {
            this.droping = false;
            const file = e.dataTransfer.files[0];
            if (file) this.processImage(file);
        }
    }));
});
