/**
 * Event Listeners Centralizados (CSP-Compliant)
 * Reemplaza eventos inline onclick/onchange/onsubmit para cumplir con Content Security Policy
 * 
 * Este archivo debe cargarse en base_modern.html o base.html
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // =========================================================================
    // 1. window.print() → data-action="print"
    // =========================================================================
    document.querySelectorAll('[data-action="print"]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            e.preventDefault();
            window.print();
        });
    });
    
    // =========================================================================
    // 2. onchange="this.form.submit()" → data-auto-submit
    // =========================================================================
    document.querySelectorAll('[data-auto-submit]').forEach(function(el) {
        el.addEventListener('change', function() {
            this.closest('form').submit();
        });
    });
    
    // =========================================================================
    // 3. onclick="location.href='...'" → data-href
    // =========================================================================
    document.querySelectorAll('[data-href]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            // No navegar si se hizo clic en un elemento con stopPropagation
            if (e.target.closest('[data-stop-propagation]')) {
                return;
            }
            window.location.href = this.dataset.href;
        });
    });
    
    // =========================================================================
    // 4. onclick="event.stopPropagation()" → data-stop-propagation
    // =========================================================================
    // Este se maneja en el listener de data-href arriba
    
    // =========================================================================
    // 5. onclick="closeDetailModal()" → data-action="close-modal"
    // =========================================================================
    document.querySelectorAll('[data-action="close-modal"]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            e.preventDefault();
            const modal = this.closest('.fixed.inset-0') || document.getElementById('detailModal');
            if (modal) {
                modal.classList.add('hidden');
                modal.classList.remove('flex');
            }
        });
    });
    
    // =========================================================================
    // 6. onclick="confirm('...')" → data-confirm (buttons/links)
    //    onsubmit="return confirm('...')" → data-confirm (forms)
    // =========================================================================
    document.querySelectorAll('button[data-confirm], a[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });
    
    document.querySelectorAll('form[data-confirm]').forEach(function(el) {
        el.addEventListener('submit', function(e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });
    
    // =========================================================================
    // 7. onerror="this.src='...'" → data-fallback-src
    // =========================================================================
    document.querySelectorAll('img[data-fallback-src]').forEach(function(img) {
        img.addEventListener('error', function() {
            if (!this.dataset.errorHandled) {
                this.src = this.dataset.fallbackSrc;
                this.dataset.errorHandled = 'true';
            }
        });
    });
    
    // =========================================================================
    // 8. onclick="document.getElementById('...').click()" → data-trigger-click
    // =========================================================================
    document.querySelectorAll('[data-trigger-click]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.getElementById(this.dataset.triggerClick);
            if (target) target.click();
        });
    });
    
    // =========================================================================
    // 9. onclick="window.location.reload()" → data-action="reload"
    // =========================================================================
    document.querySelectorAll('[data-action="reload"]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.reload();
        });
    });
    
    // =========================================================================
    // 10. onclick="scrollToSection('...')" → data-scroll-to
    // =========================================================================
    document.querySelectorAll('[data-scroll-to]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.getElementById(this.dataset.scrollTo);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
    
    // =========================================================================
    // 11. toggleAccordion → data-action="toggle-accordion"
    // =========================================================================
    document.querySelectorAll('[data-action="toggle-accordion"]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            e.preventDefault();
            this.classList.toggle('open');
            const content = this.nextElementSibling;
            if (content) {
                content.classList.toggle('hidden');
            }
        });
    });
    
    console.log('✅ CSP Event Listeners initialized');
});
