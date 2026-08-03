document.addEventListener('alpine:init', () => {
    Alpine.data('marketingHub', () => ({
        tab: 'copy',
        loading: false,
        copyData: { producto: '', destino: '', detalles: '', tono: 'AVENTURERO' },
        resultCaption: '',
        resultEmail: '',

        init() {
            const ds = this.$el.dataset;
            this._hubUrl = ds.hubUrl || '';
            this._csrf = ds.csrf || '';
        },

        async generateCaption() {
            this.loading = true;
            try {
                const formData = new FormData();
                formData.append('action', 'generate_caption');
                formData.append('producto', this.copyData.producto);
                formData.append('destino', this.copyData.destino);
                formData.append('detalles', this.copyData.detalles);
                formData.append('tono', this.copyData.tono);
                formData.append('csrfmiddlewaretoken', this._csrf);

                const resp = await fetch(this._hubUrl, {
                    method: 'POST',
                    body: formData
                });
                const data = await resp.json();
                this.resultCaption = data.caption;
            } catch (e) {
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: 'Error: ' + e, type: 'error' }
                }));
            } finally {
                this.loading = false;
            }
        },

        async generateNewsletter() {
            this.loading = true;
            try {
                const formData = new FormData();
                formData.append('action', 'generate_newsletter');
                formData.append('csrfmiddlewaretoken', this._csrf);

                const resp = await fetch(this._hubUrl, {
                    method: 'POST',
                    body: formData
                });
                const data = await resp.json();
                this.resultEmail = data.html_content;

                this.$nextTick(() => {
                    const doc = this.$refs.emailPreview.contentWindow.document;
                    doc.open();
                    doc.write(this.resultEmail);
                    doc.close();
                });
            } catch (e) {
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: 'Error: ' + e, type: 'error' }
                }));
            } finally {
                this.loading = false;
            }
        },

        copyToClipboard(text) {
            navigator.clipboard.writeText(text);
            window.dispatchEvent(new CustomEvent('notify', {
                detail: { message: 'Copiado al portapapeles', type: 'success' }
            }));
        }
    }));
});
