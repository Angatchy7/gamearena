document.addEventListener("DOMContentLoaded", function () {
    function setupPreview(inputId, previewContainerId, previewImgId, errorId, removeBtnId, placeholderId) {
        const input = document.getElementById(inputId);
        const container = previewContainerId ? document.getElementById(previewContainerId) : null;
        const img = document.getElementById(previewImgId);
        const errorEl = errorId ? document.getElementById(errorId) : null;
        const removeBtn = removeBtnId ? document.getElementById(removeBtnId) : null;
        const placeholder = placeholderId ? document.getElementById(placeholderId) : null;

        if (!input || !img) return;

        let activeObjectUrl = null;
        const initialUrl = input.getAttribute("data-initial-url");

        // Display initial image on edit page if present
        if (initialUrl && initialUrl.trim() !== "") {
            img.src = initialUrl;
            img.classList.remove("d-none");
            if (container) container.classList.remove("d-none");
            if (placeholder) placeholder.classList.add("d-none");
            if (removeBtn) removeBtn.classList.add("d-none");
        }

        function resetToInitial() {
            if (activeObjectUrl) {
                URL.revokeObjectURL(activeObjectUrl);
                activeObjectUrl = null;
            }
            input.value = "";

            if (errorEl) {
                errorEl.textContent = "";
                errorEl.classList.add("d-none");
            }

            if (initialUrl && initialUrl.trim() !== "") {
                img.src = initialUrl;
                img.classList.remove("d-none");
                if (container) container.classList.remove("d-none");
                if (placeholder) placeholder.classList.add("d-none");
            } else {
                img.src = "";
                img.classList.add("d-none");
                if (container) container.classList.add("d-none");
                if (placeholder) placeholder.classList.remove("d-none");
            }

            if (removeBtn) removeBtn.classList.add("d-none");
        }

        input.addEventListener("change", function (e) {
            const file = e.target.files[0];

            if (errorEl) {
                errorEl.textContent = "";
                errorEl.classList.add("d-none");
            }

            if (!file) {
                resetToInitial();
                return;
            }

            // Validate file type
            if (!file.type || !file.type.startsWith("image/")) {
                if (errorEl) {
                    errorEl.textContent = "Selected file is not a valid image. Please select a PNG, JPG, or WEBP file.";
                    errorEl.classList.remove("d-none");
                }
                resetToInitial();
                return;
            }

            // Revoke previous Object URL to avoid memory leaks
            if (activeObjectUrl) {
                URL.revokeObjectURL(activeObjectUrl);
            }

            activeObjectUrl = URL.createObjectURL(file);
            img.src = activeObjectUrl;
            img.classList.remove("d-none");
            if (container) container.classList.remove("d-none");
            if (placeholder) placeholder.classList.add("d-none");

            // Show X remove button for newly selected file
            if (removeBtn) removeBtn.classList.remove("d-none");
        });

        if (removeBtn) {
            removeBtn.addEventListener("click", function (e) {
                e.preventDefault();
                e.stopPropagation();
                resetToInitial();
            });
        }
    }

    setupPreview("id_banner", "banner-preview-container", "banner-preview-img", "banner-preview-error", "banner-remove-btn");
    setupPreview("id_cover_image", "cover-preview-container", "cover-preview-img", "cover-preview-error", "cover-remove-btn");
    setupPreview("id_logo", null, "logo-preview-img", "logo-error", "logo-remove-btn", "logo-placeholder");
});
