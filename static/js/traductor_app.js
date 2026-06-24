document.addEventListener('alpine:init', () => {
    Alpine.data('traductorApp', () => ({
        inputText: '',
        translatedHtml: '',
        loading: false,
        activeTab: 'itinerario',
        tasaBcv: '0.00',
        calc: {
            tarifa: 0,
            feeConsolidador: 0,
            feeInterno: 0,
            porcentaje: 0
        },
        resultadoCalc: {
            subtotal: 0,
            igtf: 0,
            total: 0
        },
        structuredData: [],
        creatingQuote: false,

        init() {
            const ds = this.$el.dataset;
            this.tasaBcv = ds.tasaBcv || '0.00';
            this._translateUrl = ds.translateUrl || '/api/translator/itinerary/';
            this._createQuoteUrl = ds.createQuoteUrl || '/api/translator/create-quote/';
            this._csrf = ds.csrf || '';
        },

        sanitizeHtml(html) {
            const div = document.createElement('div');
            div.innerHTML = html;
            div.querySelectorAll('script, iframe, object, embed, form, input, button, textarea, select').forEach(el => el.remove());
            div.querySelectorAll('*').forEach(el => {
                Array.from(el.attributes).forEach(attr => {
                    if (attr.name.startsWith('on')) {
                        el.removeAttribute(attr.name);
                    }
                });
            });
            return div.innerHTML;
        },

        async traducir() {
            if (!this.inputText.trim()) return;

            this.loading = true;
            try {
                const response = await fetch(this._translateUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this._csrf
                    },
                    body: JSON.stringify({ itinerary: this.inputText })
                });

                const data = await response.json();
                if (data.success) {
                    this.translatedHtml = this.sanitizeHtml(data.translated_itinerary);
                    this.structuredData = data.structured_data || [];
                    this.activeTab = 'itinerario';
                } else {
                    window.dispatchEvent(new CustomEvent('notify', {
                        detail: { message: 'Error: ' + (data.error || 'No se pudo traducir'), type: 'error' }
                    }));
                }
            } catch (e) {
                console.error(e);
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: 'Error de conexión', type: 'error' }
                }));
            } finally {
                this.loading = false;
            }
        },

        async crearCotizacion() {
            if (!this.structuredData || this.structuredData.length === 0) {
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: 'No hay datos estructurados disponibles. Por favor traduzca un itinerario válido primero.', type: 'error' }
                }));
                return;
            }

            this.creatingQuote = true;
            try {
                const response = await fetch(this._createQuoteUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this._csrf
                    },
                    body: JSON.stringify({ structured_data: this.structuredData })
                });

                const data = await response.json();
                if (data.success) {
                    window.location.href = data.redirect_url;
                } else {
                    window.dispatchEvent(new CustomEvent('notify', {
                        detail: { message: 'Error: ' + (data.error || 'No se pudo crear la cotización'), type: 'error' }
                    }));
                }
            } catch (e) {
                console.error(e);
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: 'Error al conectar con el servidor', type: 'error' }
                }));
            } finally {
                this.creatingQuote = false;
            }
        },

        calcular() {
            const base = this.calc.tarifa + this.calc.feeConsolidador + this.calc.feeInterno;
            const ganancia = base * (this.calc.porcentaje / 100);
            const subtotal = base + ganancia;
            const igtf = subtotal * 0.03;

            this.resultadoCalc = {
                subtotal: subtotal,
                igtf: igtf,
                total: subtotal + igtf
            };
        },

        formatMoney(amount) {
            return '$' + amount.toFixed(2);
        },

        limpiar() {
            this.inputText = '';
            this.translatedHtml = '';
            this.structuredData = [];
            this.calc = { tarifa: 0, feeConsolidador: 0, feeInterno: 0, porcentaje: 0 };
            this.calcular();
        },

        copiarItinerario(e) {
            const btn = e.currentTarget;
            const el = document.getElementById('resultado-itinerario');
            const range = document.createRange();
            range.selectNode(el);
            window.getSelection().removeAllRanges();
            window.getSelection().addRange(range);
            document.execCommand('copy');
            window.getSelection().removeAllRanges();

            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check mr-1"></i>Copiado';
            setTimeout(() => {
                btn.innerHTML = originalText;
            }, 2000);
        }
    }));
});
