/**
 * core/static/core/js/gds_analyzer_logic.js
 * Lógica del GDS Analyzer desacoplada para evitar bloqueos CSP (Content Security Policy).
 * Este archivo se carga como un recurso estático 'self', lo cual es permitido por la mayoría de CSP.
 */

(function() {
    "use strict";

    // Función global para inicializar la lógica después de que HTMX cargue el parcial
    window.inicializarGDSAnalyzer = function() {
        console.log("🚀 [TravelHub] Motor GDS desde archivo estático inicializado.");
        
        const dataNode = document.getElementById('gds-analysis-data');
        if (!dataNode) {
            console.log("⏳ [TravelHub] Esperando datos GDS en el DOM...");
            return;
        }

        let currentGdsData;
        try {
            currentGdsData = JSON.parse(dataNode.textContent);
        } catch (e) {
            console.error("❌ [TravelHub] Error al parsear JSON de datos:", e);
            return;
        }

        console.log("✅ [TravelHub] Datos encontrados. Atando eventos...");

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

        const gdsNet = parseSafeFloat(currentGdsData.TOTAL || currentGdsData.total);

        // --- LÓGICA DE CALCULADORA ---
        function calcularFinanzasGDS() {
            const iProv = document.getElementById('fee-proveedor');
            const iInt = document.getElementById('fee-interno');
            
            const fProv = parseFloat(iProv ? iProv.value : 0) || 0;
            const fInt = parseFloat(iInt ? iInt.value : 0) || 0;

            const sub = gdsNet + fProv + fInt;
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
                console.log("📸 [TravelHub] Capturando cámara...");
                const btn = this;
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="material-symbols-outlined animate-spin">cached</span>';
                btn.disabled = true;

                if (typeof html2canvas === 'undefined') {
                    alert("Cargando motor de imagen. Reintente en 2 segundos.");
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                    return;
                }

                html2canvas(document.getElementById('panel-a-capturar'), {
                    backgroundColor: '#0a0d12',
                    scale: 2,
                    useCORS: true,
                    logging: false
                }).then(canvas => {
                    let a = document.createElement('a');
                    a.download = 'Confirmacion_' + (currentGdsData.CODIGO_RESERVA || 'Reserva') + '.png';
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
                console.log("⚡ [TravelHub] Inyectando al ERP...");
                const btn = this;
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="material-symbols-outlined animate-spin">sync</span>';
                btn.disabled = true;

                const payload = {
                    analysis_data: currentGdsData,
                    user_fees: {
                        fee_proveedor: parseFloat(document.getElementById('fee-proveedor').value) || 0,
                        fee_interno: parseFloat(document.getElementById('fee-interno').value) || 0
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
                            alert("¡Éxito! Venta inyectada.");
                            if(result.redirect_url) window.location.href = result.redirect_url;
                        }
                    } else {
                        alert("Error: " + result.message);
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
