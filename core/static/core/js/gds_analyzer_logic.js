/**
 * core/static/core/js/gds_analyzer_logic.js
 * Lógica del GDS Analyzer desacoplada para evitar bloqueos CSP (Content Security Policy).
 * Este archivo se carga como un recurso estático 'self', lo cual es permitido por la mayoría de CSP.
 */

(function() {
    "use strict";

    // Función global para inicializar la lógica después de que HTMX cargue el parcial
    window.inicializarGDSAnalyzer = function() {

        
        const dataNode = document.getElementById('gds-analysis-data');
        if (!dataNode) {

            return;
        }

        let currentGdsData;
        try {
            currentGdsData = JSON.parse(dataNode.textContent);
        } catch (e) {
            console.error("❌ [TravelHub] Error al parsear JSON de datos:", e);
            return;
        }



        function parseSafeFloat(val) {
            if (!val) return 0;
            let strVal = val.toString().trim();
            // Manejo de formatos Latam (1.234,56)
            if (strVal.includes(',') && strVal.includes('.')) {
                strVal = strVal.replace(/\./g, '').replace(',', '.');
            } else if (strVal.includes(',')) {
                strVal = strVal.replace(',', '.');
            }
            return parseFloat(strVal) || 0;
        }

        const boletos = currentGdsData.boletos && Array.isArray(currentGdsData.boletos) 
            ? currentGdsData.boletos 
            : (currentGdsData.itinerario ? [currentGdsData] : []);

        let gdsNet = 0;
        boletos.forEach(b => {
            gdsNet += parseSafeFloat(b.total || b.TOTAL);
        });

        // --- LÓGICA DE CALCULADORA ---
        function calcularFinanzasGDS() {
            const iProv = document.getElementById('fee-proveedor');
            const iInt = document.getElementById('fee-interno');
            
            const fProvPax = parseFloat(iProv ? iProv.value : 0) || 0;
            const fIntPax = parseFloat(iInt ? iInt.value : 0) || 0;

            const numPax = boletos.length || 1;
            const totalFProv = fProvPax * numPax;
            const totalFInt = fIntPax * numPax;

            const sub = gdsNet + totalFProv + totalFInt;
            const igtf = sub * 0.03;
            const total = sub + igtf;

            const fmt = (n) => n.toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

            const elSub = document.getElementById('res-subtotal');
            const elIgtf = document.getElementById('res-igtf');
            const elTot = document.getElementById('res-total-final');

            if(elSub) elSub.innerText = fmt(sub);
            if(elIgtf) elIgtf.innerText = fmt(igtf);
            if(elTot) elTot.innerText = fmt(total);
        }

        const iProv = document.getElementById('fee-proveedor');
        const iInt = document.getElementById('fee-interno');
        if (iProv) {
            iProv.removeEventListener('input', calcularFinanzasGDS);
            iProv.addEventListener('input', calcularFinanzasGDS);
        }
        if (iInt) {
            iInt.removeEventListener('input', calcularFinanzasGDS);
            iInt.addEventListener('input', calcularFinanzasGDS);
        }

        calcularFinanzasGDS(); // Ejecución inicial

        // --- EVENTO: FOTO WHATSAPP ---
        const btnFoto = document.getElementById('btn-descargar-foto');
        if (btnFoto) {
            // Clonamos para limpiar listeners previos de HTMX
            const newBtn = btnFoto.cloneNode(true);
            btnFoto.parentNode.replaceChild(newBtn, btnFoto);
            
            newBtn.addEventListener('click', function() {

                const btn = this;
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="material-symbols-outlined animate-spin">cached</span>';
                btn.disabled = true;

                if (typeof html2canvas === 'undefined') {
                    window.dispatchEvent(new CustomEvent('notify', {
                        detail: { message: 'Cargando motor de imagen. Reintente en 2 segundos.', type: 'info' }
                    }));
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                    return;
                }

                html2canvas(document.getElementById('panel-a-capturar'), {
                    backgroundColor: '#0a0d12',
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    allowTaint: true
                }).then(canvas => {
                    let a = document.createElement('a');
                    const pnr = (boletos[0]?.codigo_reserva || currentGdsData.CODIGO_RESERVA || 'Reserva');
                    a.download = 'Confirmacion_' + pnr + '.png';
                    a.href = canvas.toDataURL('image/png');
                    a.click();
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }).catch(err => {
                    console.error("Error html2canvas:", err);
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                });
            });
        }

        // --- EVENTO: INYECTAR ERP ---
        const btnInyectar = document.getElementById('btn-inyectar-erp');
        if (btnInyectar) {
            const newBtn = btnInyectar.cloneNode(true);
            btnInyectar.parentNode.replaceChild(newBtn, btnInyectar);

            newBtn.addEventListener('click', async function() {

                const btn = this;
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="material-symbols-outlined animate-spin">sync</span>';
                btn.disabled = true;

                const numPax = boletos.length || 1;
                const pagadorInput = document.getElementById('pagador-id-hidden');

                const payload = {
                    analysis_data: currentGdsData,
                    pagador_id: pagadorInput ? pagadorInput.value : null,
                    user_fees: {
                        fee_proveedor: (parseFloat(document.getElementById('fee-proveedor').value) || 0) * numPax,
                        fee_interno: (parseFloat(document.getElementById('fee-interno').value) || 0) * numPax
                    }
                };

                try {
                    const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
                    const res = await fetch('/intelligence/gds-analyzer/inject/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                        body: JSON.stringify(payload)
                    });
                    const result = await res.json();
                    
                    if (result.status === 'success') {
                        if (window.Swal) {
                            Swal.fire({ 
                                icon: 'success', title: '¡Venta Creada!', 
                                background: '#111827', color: '#fff', confirmButtonColor: '#13ec5b'
                            }).then(() => { if(result.redirect_url) window.location.href = result.redirect_url; });
                        } else {
                            window.dispatchEvent(new CustomEvent('notify', {
                                detail: { message: '¡Éxito! Venta inyectada.', type: 'success' }
                            }));
                            if(result.redirect_url) window.location.href = result.redirect_url;
                        }
                    } else {
                        window.dispatchEvent(new CustomEvent('notify', {
                            detail: { message: 'Error: ' + result.message, type: 'error' }
                        }));
                        btn.innerHTML = originalText;
                        btn.disabled = false;
                    }
                } catch(e) {
                    console.error("Error Red:", e);
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            });
        }
    };

    // ESCUCHADOR HTMX PARA CARGAS DINÁMICAS
    document.body.addEventListener('htmx:load', function(evt) {
        if (document.getElementById('gds-analysis-data')) {
            window.inicializarGDSAnalyzer();
        }
    });

    // Ejecución por seguridad (si ya cargó)
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        window.inicializarGDSAnalyzer();
    }
})();
