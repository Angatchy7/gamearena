document.addEventListener("DOMContentLoaded", function () {
    function setupPreview(inputId, previewContainerId, previewImgId, errorId) {
        const input = document.getElementById(inputId);
        const container = document.getElementById(previewContainerId);
        const img = document.getElementById(previewImgId);
        const errorEl = document.getElementById(errorId);

        if (!input || !container || !img) return;

        let activeObjectUrl = null;
        const initialUrl = input.getAttribute("data-initial-url");

        // Display initial image on edit page if present
        if (initialUrl && initialUrl.trim() !== "") {
            img.src = initialUrl;
            container.classList.remove("d-none");
        }

        input.addEventListener("change", function (e) {
            const file = e.target.files[0];

            if (errorEl) {
                errorEl.textContent = "";
                errorEl.classList.add("d-none");
            }

            if (!file) {
                // If user cancelled file dialog, restore initial image or hide
                if (initialUrl && initialUrl.trim() !== "") {
                    img.src = initialUrl;
                    container.classList.remove("d-none");
                } else {
                    img.src = "";
                    container.classList.add("d-none");
                }
                return;
            }

            // Validate file type
            if (!file.type || !file.type.startsWith("image/")) {
                if (errorEl) {
                    errorEl.textContent = "Selected file is not a valid image. Please select a PNG, JPG, or WEBP file.";
                    errorEl.classList.remove("d-none");
                }
                // Do not display broken image preview
                if (initialUrl && initialUrl.trim() !== "") {
                    img.src = initialUrl;
                    container.classList.remove("d-none");
                } else {
                    img.src = "";
                    container.classList.add("d-none");
                }
                return;
            }

            // Revoke previous Object URL to avoid memory leaks
            if (activeObjectUrl) {
                URL.revokeObjectURL(activeObjectUrl);
            }

            activeObjectUrl = URL.createObjectURL(file);
            img.src = activeObjectUrl;
            container.classList.remove("d-none");
        });
    }

    setupPreview("id_banner", "banner-preview-container", "banner-preview-img", "banner-preview-error");
    setupPreview("id_cover_image", "cover-preview-container", "cover-preview-img", "cover-preview-error");
});
