
// core/static/core/js/dashboard_upload.js
document.addEventListener('DOMContentLoaded', function () {
    console.log("Dashboard Upload JS Loaded");

    const fileInput = document.getElementById('dropzone-file');
    const uploadForm = document.getElementById('upload-form');
    const btnTop = document.getElementById('btn-upload-ticket');
    const btnQuick = document.getElementById('btn-quick-upload');

    function triggerUpload() {
        if (fileInput) {
            fileInput.value = ''; // Reset to allow re-selecting same file
            fileInput.click();
        } else {
            console.error("File input #dropzone-file not found");
        }
    }

    // Attach listeners
    if (btnTop) {
        btnTop.addEventListener('click', triggerUpload);
    } else {
        console.warn("#btn-upload-ticket not found");
    }

    if (btnQuick) {
        btnQuick.addEventListener('click', triggerUpload);
    } else {
        console.warn("#btn-quick-upload not found");
    }

    // Auto-submit
    if (fileInput && uploadForm) {
        fileInput.addEventListener('change', function () {
            if (this.files.length > 0) {
                console.log("File selected. Submitting via HTMX...");

                // UX: Global Toast Feedback
                window.dispatchEvent(new CustomEvent('notify', {
                    detail: { message: 'Subiendo y Procesando Boleto...', type: 'info' }
                }));

                // Check if htmx is defined
                if (typeof htmx !== 'undefined') {
                    htmx.trigger(uploadForm, 'submit');
                } else {
                    // Fallback for non-HTMX (shouldn't happen in this setup but good hygiene)
                    uploadForm.submit();
                }
            }
        });
    }
});
