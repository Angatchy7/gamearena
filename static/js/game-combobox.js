document.addEventListener("DOMContentLoaded", function () {
    const select = document.getElementById("id_game");
    if (!select) return;

    // Build options list from the select element
    function getOptions() {
        const options = [];
        for (let i = 0; i < select.options.length; i++) {
            const opt = select.options[i];
            if (opt.value) {
                options.push({
                    value: opt.value,
                    text: opt.text.trim(),
                });
            }
        }
        return options;
    }

    const gameOptions = getOptions();

    // Create wrapper container
    const wrapper = document.createElement("div");
    wrapper.className = "game-combobox-wrapper position-relative";

    // Create input field
    const input = document.createElement("input");
    input.type = "text";
    input.className = "form-control game-combobox-input";
    input.placeholder = "🎮 Search games...";
    input.autocomplete = "off";
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-autocomplete", "list");

    // Create dropdown menu container
    const dropdown = document.createElement("div");
    dropdown.className = "game-combobox-dropdown d-none position-absolute w-100 shadow-lg mt-1";
    dropdown.style.zIndex = "1050";
    dropdown.style.maxHeight = "240px";
    dropdown.style.overflowY = "auto";
    dropdown.style.background = "#1e293b";
    dropdown.style.border = "1px solid rgba(148, 163, 184, 0.2)";
    dropdown.style.borderRadius = "12px";
    dropdown.style.padding = "6px 0";

    // Insert wrapper into DOM and hide select
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(input);
    wrapper.appendChild(dropdown);

    // Keep select hidden but functional
    select.classList.add("d-none");

    let activeIndex = -1;
    let selectedOption = null;

    // Helper: Find selected option in select
    function syncInitialValue() {
        const currentVal = select.value;
        if (currentVal) {
            const matched = gameOptions.find((o) => o.value === currentVal);
            if (matched) {
                selectedOption = matched;
                input.value = matched.text;
                return;
            }
        }
        selectedOption = null;
        input.value = "";
    }

    syncInitialValue();

    function renderDropdown(filterText = "") {
        dropdown.innerHTML = "";
        activeIndex = -1;

        const query = filterText.toLowerCase().trim();
        const filtered = gameOptions.filter((opt) =>
            opt.text.toLowerCase().includes(query)
        );

        if (filtered.length === 0) {
            const emptyItem = document.createElement("div");
            emptyItem.className = "px-3 py-2 text-muted small text-center";
            emptyItem.textContent = "No games found";
            dropdown.appendChild(emptyItem);
        } else {
            filtered.forEach((opt, idx) => {
                const item = document.createElement("div");
                item.className = "game-combobox-item px-3 py-2 text-light cursor-pointer";
                item.style.cursor = "pointer";
                item.style.transition = "background-color 0.15s ease";
                item.setAttribute("data-value", opt.value);
                item.setAttribute("data-index", idx);
                item.textContent = opt.text;

                if (selectedOption && selectedOption.value === opt.value) {
                    item.style.background = "rgba(37, 99, 235, 0.25)";
                    item.style.fontWeight = "600";
                }

                item.addEventListener("mouseenter", function () {
                    setActiveIndex(idx);
                });

                item.addEventListener("click", function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    selectGame(opt);
                });

                dropdown.appendChild(item);
            });
        }

        dropdown.classList.remove("d-none");
        input.setAttribute("aria-expanded", "true");
    }

    function setActiveIndex(idx) {
        const items = dropdown.querySelectorAll(".game-combobox-item");
        items.forEach((item, i) => {
            if (i === idx) {
                item.style.background = "rgba(37, 99, 235, 0.35)";
                item.scrollIntoView({ block: "nearest" });
            } else {
                const optVal = item.getAttribute("data-value");
                if (selectedOption && selectedOption.value === optVal) {
                    item.style.background = "rgba(37, 99, 235, 0.25)";
                } else {
                    item.style.background = "transparent";
                }
            }
        });
        activeIndex = idx;
    }

    function selectGame(opt) {
        selectedOption = opt;
        select.value = opt.value;
        input.value = opt.text;
        closeDropdown();

        // Dispatch change event on original select for any listener
        const event = new Event("change", { bubbles: true });
        select.dispatchEvent(event);
    }

    function closeDropdown() {
        dropdown.classList.add("d-none");
        dropdown.innerHTML = "";
        input.setAttribute("aria-expanded", "false");
        activeIndex = -1;
    }

    // Input Events
    input.addEventListener("focus", function () {
        renderDropdown(this.value);
    });

    input.addEventListener("input", function () {
        renderDropdown(this.value);
    });

    input.addEventListener("keydown", function (e) {
        const items = dropdown.querySelectorAll(".game-combobox-item");
        if (dropdown.classList.contains("d-none")) {
            if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                renderDropdown(input.value);
                e.preventDefault();
                return;
            }
        }

        if (e.key === "ArrowDown") {
            e.preventDefault();
            if (items.length > 0) {
                const nextIdx = (activeIndex + 1) % items.length;
                setActiveIndex(nextIdx);
            }
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            if (items.length > 0) {
                const prevIdx = activeIndex <= 0 ? items.length - 1 : activeIndex - 1;
                setActiveIndex(prevIdx);
            }
        } else if (e.key === "Enter") {
            if (activeIndex >= 0 && items[activeIndex]) {
                e.preventDefault();
                items[activeIndex].click();
            }
        } else if (e.key === "Escape") {
            e.preventDefault();
            closeDropdown();
            // Revert input text to selected option or clear
            if (selectedOption) {
                input.value = selectedOption.text;
            } else {
                input.value = "";
            }
        }
    });

    // Blur / click outside handler
    document.addEventListener("click", function (e) {
        if (!wrapper.contains(e.target)) {
            if (!dropdown.classList.contains("d-none")) {
                closeDropdown();
                // Ensure text matches selected option to reject arbitrary client text
                if (selectedOption) {
                    input.value = selectedOption.text;
                } else {
                    input.value = "";
                    select.value = "";
                }
            }
        }
    });
});
