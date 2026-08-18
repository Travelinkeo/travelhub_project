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

                if (result.status === 'success' || result.success === true) {
                    const d = result.data || {};

                    const setField = (name, val) => {
                        if (val !== null && val !== undefined && String(val).trim() !== '' && String(val) !== '0') {
                            const el = document.querySelector(`[name="${name}"]`);
                            if (el) {
                                el.value = String(val).trim();
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }
                    };

                    const setSelectField = (name, valId, valName) => {
                        const el = document.querySelector(`select[name="${name}"]`);
                        if (!el) return;
                        if (valId) {
                            el.value = String(valId);
                            if (el.value === String(valId)) {
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                                return;
                            }
                        }
                        if (valName) {
                            const opt = Array.from(el.options).find(o =>
                                o.text.toLowerCase().includes(String(valName).toLowerCase()) ||
                                o.value.toLowerCase() === String(valName).toLowerCase()
                            );
                            if (opt) {
                                el.value = opt.value;
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }
                    };

                    setField('nombres', d.nombres);
                    setField('apellidos', d.apellidos);
                    setField('cedula_identidad', d.cedula_identidad || d.cedula);
                    setField('numero_pasaporte', d.numero_pasaporte);
                    setField('fecha_nacimiento', d.fecha_nacimiento);
                    setField('fecha_vencimiento_documento', d.fecha_vencimiento_documento || d.fecha_vencimiento || d.fecha_vencimiento_pasaporte);

                    setSelectField('nacionalidad', d.nacionalidad_id || d.nacionalidad, d.nacionalidad_nombre || d.nacionalidad);
                    setSelectField('pais_emision_documento', d.pais_emision_id || d.pais_emision, d.pais_emision_nombre || d.pais_emision);
                    if (d.sexo || d.genero) {
                        setSelectField('genero', d.sexo || d.genero, d.sexo || d.genero);
                    }

                    if (d.foto_url && !d.foto_url.includes('face_None')) {
                        const preview = document.getElementById('preview-image');
                        const placeholder = document.querySelector('.flex-col.items-center.text-text-muted');
                        if (preview) {
                            preview.src = d.foto_url;
                            preview.classList.remove('hidden');
                        }
                        if (placeholder) placeholder.classList.add('hidden');
                    }

                    const filled = [d.nombres, d.apellidos, d.cedula_identidad || d.cedula, d.numero_pasaporte].filter(v => v && String(v).trim() !== '' && String(v) !== '0').length;
                    this.message = filled > 0 ? `¡Documento escaneado: ${filled} campo(s) autocompletado(s)!` : '📷 Foto capturada. Completa los datos requeridos.';
                    setTimeout(() => this.message = '', 6000);
                } else {
                    const errMsg = result.error || 'No se pudo procesar la imagen del documento.';
                    window.dispatchEvent(new CustomEvent('notify', {
                        detail: { message: 'Error OCR: ' + errMsg, type: 'error' }
                    }));
                    this.message = '❌ ' + errMsg;
                    setTimeout(() => this.message = '', 6000);
                }
            } catch (e) {
                console.error('Error procesando OCR:', e);
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: 'Error de comunicación al escanear el documento.', type: 'error' }
                }));
                this.message = '❌ Error al comunicar con el servidor de escaneo.';
                setTimeout(() => this.message = '', 6000);
            }
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
