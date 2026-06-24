document.addEventListener('alpine:init', () => {
    Alpine.data('magicApp', () => ({
        rawText: '',
        fee: 50,
        showVes: false,
        includeIgtf: false,
        tasaBcv: 0,
        loading: false,
        sharing: false,
        error: '',
        result: null,

        init() {
            const ds = this.$el.dataset;
            this.tasaBcv = parseFloat((ds.tasaBcv || '0').replace(',', '.'));
            this._aiUrl = ds.aiUrl || '';
            this._saveUrl = ds.saveUrl || '';
            this._csrf = ds.csrf || '';
        },

        get displayPrice() {
            if (!this.result) return '0.00';
            let total = (parseFloat(this.result.totalPrice) || 0) + (parseFloat(this.fee) || 0);
            if (this.includeIgtf) total = total * 1.03;
            return total.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        },

        get displayPriceVes() {
            if (!this.result || !this.tasaBcv) return '0,00';
            let totalUsd = (parseFloat(this.result.totalPrice) || 0) + (parseFloat(this.fee) || 0);
            if (this.includeIgtf) totalUsd = totalUsd * 1.03;
            return (totalUsd * this.tasaBcv).toLocaleString('es-VE', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        },

        pasteTest() {
            this.rawText = "1 TK 224E 20APR CCSIST 2310 1750\n2 TK 225E 30APR ISTCCS 0210 0815\nTOTAL USD 1450.00";
        },

        async generate() {
            this.loading = true;
            this.error = '';
            this.result = null;
            try {
                const res = await fetch(this._aiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this._csrf
                    },
                    body: JSON.stringify({
                        raw_text: this.rawText,
                        agency_fee: this.fee
                    })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Error en el motor de IA');
                this.result = data;
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },

        async share() {
            this.sharing = true;
            try {
                let totalFinal = (parseFloat(this.result.totalPrice) || 0) + (parseFloat(this.fee) || 0);
                if (this.includeIgtf) totalFinal = totalFinal * 1.03;

                const res = await fetch(this._saveUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this._csrf },
                    body: JSON.stringify({
                        ai_data: { ...this.result, totalPriceWithFee: totalFinal },
                        raw_text: this.rawText,
                        agency_fee: this.fee,
                        include_igtf: this.includeIgtf
                    })
                });
                const data = await res.json();
                if (data.success) {
                    window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(data.whatsapp_msg)}`, '_blank');
                } else {
                    throw new Error(data.error);
                }
            } catch (e) {
                window.dispatchEvent(new CustomEvent('notify', { detail: { message: 'Error: ' + e.message, type: 'error' } }));
            } finally {
                this.sharing = false;
            }
        }
    }));
});
