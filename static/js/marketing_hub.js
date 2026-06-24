document.addEventListener('alpine:init', () => {
    Alpine.data('marketingHub', () => ({
        tab: 'copy',
        loading: false,
        copyData: { producto: '', destino: '', detalles: '', tono: 'AVENTURERO' },
        imageData: { hotel_name: '', price: '', style: 'Luxurious', custom_text: '' },
        resultCaption: '',
        resultImage: '',
        resultEmail: '',

        init() {
            const ds = this.$el.dataset;
            this._hubUrl = ds.hubUrl || '';
            this._imageUrl = ds.imageUrl || '';
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

        async generateImage() {
            this.loading = true;
            try {
                const formData = new FormData();
                formData.append('hotel_name', this.imageData.hotel_name);
                formData.append('price', this.imageData.price);
                formData.append('style', this.imageData.style);
                formData.append('custom_text', this.imageData.custom_text);
                formData.append('csrfmiddlewaretoken', this._csrf);

                const resp = await fetch(this._imageUrl, {
                    method: 'POST',
                    body: formData
                });
                const data = await resp.json();
                if(data.status === 'success') {
                    this.resultImage = data.image_b64;
                } else {
                    window.dispatchEvent(new CustomEvent('notify', {
                        detail: { message: 'Error IA: ' + data.error, type: 'error' }
                    }));
                }
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
        },

        downloadImage() {
            const link = document.createElement('a');
            link.href = `data:image/jpeg;base64,${this.resultImage}`;
            link.download = `TH_AI_Post_${Date.now()}.jpg`;
            link.click();
        }
    }));
});
