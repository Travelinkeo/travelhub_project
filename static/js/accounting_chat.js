document.addEventListener('alpine:init', () => {
    Alpine.data('accountingChat', () => ({
        messages: [
            {
                role: 'assistant',
                content: 'Bienvenido. Soy **Brain**, su asistente inteligente de gestión integral.\n\nPuede consultarme sobre temas variados, tales como:\n* **Operaciones y Reservas:** "¿Cuál es el estado del PNR ABCDEF?"\n* **Requisitos y Logística:** "¿Qué visa necesita un colombiano para viajar a EE. UU.?"\n* **Ventas y Finanzas:** "¿Cuáles son las ventas de los últimos 30 días?" o "¿Saldo total de bancos?"\n* **CMS y Marketing:** "Escriba un artículo sobre las ventajas de viajar a Costa Rica" o "Genere un post de marketing para el Hotel X".',
                time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
            }
        ],
        userInput: '',
        loading: false,
        suggestions: [
            { icon: 'travel_explore', text: '¿Requisitos de viaje y SAIME?' },
            { icon: 'account_balance', text: '¿Saldo consolidado de Bancos?' },
            { icon: 'receipt_long', text: '¿Mis últimas ventas del mes?' },
            { icon: 'campaign', text: 'Generar post de marketing' }
        ],

        init() {
            this._chatUrl = this.$el.dataset.chatUrl || '/api/brain/chat/';
        },

        _getCsrf() {
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value
                || this._getCookie('th_csrftoken')
                || this._getCookie('csrftoken')
                || '';
        },

        _getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        },

        async sendMessage() {
            if (!this.userInput.trim() || this.loading) return;

            const question = this.userInput;
            const timeStr = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            this.messages.push({ role: 'user', content: question, time: timeStr });
            this.userInput = '';
            this.loading = true;
            this.scrollToBottom();

            try {
                const response = await fetch(this._chatUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this._getCsrf()
                    },
                    body: JSON.stringify({ message: question })
                });

                if (!response.ok) throw new Error('API Error');

                const data = await response.json();
                this.messages.push({
                    role: 'assistant',
                    content: data.response,
                    data_found: data.data_found,
                    time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
                });
            } catch (e) {
                this.messages.push({
                    role: 'assistant',
                    content: '⚠️ Lo sentimos, no se pudo establecer conexión con el motor de IA en este momento.',
                    time: timeStr
                });
            } finally {
                this.loading = false;
                this.scrollToBottom();
            }
        },

        formatMessage(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            let escaped = div.innerHTML;

            // Negritas con alto contraste en tema claro y oscuro
            escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-[var(--text-main)]">$1</strong>');

            // Cursivas
            escaped = escaped.replace(/\*(.*?)\*/g, '<em class="italic">$1</em>');

            // Código en línea
            escaped = escaped.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-[var(--surface-3)] font-mono text-xs text-[var(--text-main)] border border-[var(--border-color)]">$1</code>');

            // Listas y viñetas
            escaped = escaped.replace(/^\* (.*?)$/gm, '<div class="flex items-start gap-2 my-1"><span class="text-[var(--primary)] font-bold select-none">•</span><span>$1</span></div>');
            escaped = escaped.replace(/\n/g, '<br>');
            return escaped;
        },

        async clearChat() {
            if(confirm('¿Deseas limpiar el historial?')) {
                this.messages = [this.messages[0]];
                try {
                    await fetch(this._chatUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this._getCsrf()
                        },
                        body: JSON.stringify({ clear: true })
                    });
                } catch (e) {
                    console.error('Error al limpiar el historial:', e);
                }
            }
        },

        scrollToBottom() {
            setTimeout(() => {
                const el = document.getElementById('chat-container');
                el.scrollTop = el.scrollHeight;
                if (window.lucide) window.lucide.createIcons();
            }, 100);
        }
    }));
});
