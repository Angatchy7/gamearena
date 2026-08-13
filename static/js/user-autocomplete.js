document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("id_user_search_input");
    const receiverSelect = document.getElementById("id_receiver");
    const teamSlugContainer = document.getElementById("team-invite-container");

    if (!searchInput || !receiverSelect || !teamSlugContainer) return;

    const teamSlug = teamSlugContainer.getAttribute("data-team-slug");
    if (!teamSlug) return;

    const wrapper = searchInput.parentElement;
    wrapper.style.position = "relative";

    // Create dropdown element
    const dropdown = document.createElement("div");
    dropdown.className = "user-autocomplete-dropdown d-none position-absolute w-100 shadow-lg mt-1";
    dropdown.style.zIndex = "1050";
    dropdown.style.maxHeight = "240px";
    dropdown.style.overflowY = "auto";
    dropdown.style.background = "#1e293b";
    dropdown.style.border = "1px solid rgba(148, 163, 184, 0.2)";
    dropdown.style.borderRadius = "12px";
    dropdown.style.padding = "6px 0";

    wrapper.appendChild(dropdown);

    let debounceTimer = null;
    let activeIndex = -1;
    let currentResults = [];

    function renderLoading() {
        dropdown.innerHTML = `
            <div class="px-3 py-2 text-muted small text-center">
                <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                Searching...
            </div>
        `;
        dropdown.classList.remove("d-none");
    }

    function renderResults(users) {
        dropdown.innerHTML = "";
        currentResults = users;
        activeIndex = -1;

        if (users.length === 0) {
            dropdown.innerHTML = `
                <div class="px-3 py-2 text-muted small text-center">
                    No users found
                </div>
            `;
        } else {
            users.forEach((user, idx) => {
                const item = document.createElement("div");
                item.className = "user-autocomplete-item px-3 py-2.5 text-light d-flex align-items-center cursor-pointer";
                item.style.cursor = "pointer";
                item.style.transition = "background-color 0.15s ease";
                item.setAttribute("data-index", idx);

                item.innerHTML = `
                    <div class="avatar-circle me-2.5 d-flex align-items-center justify-content-center fw-bold text-white rounded-circle" style="width: 32px; height: 32px; background: linear-gradient(135deg, #2563eb, #60a5fa); font-size: 0.85rem;">
                        ${user.username.charAt(0).toUpperCase()}
                    </div>
                    <span class="fw-semibold" style="font-size: 0.95rem;">${user.username}</span>
                `;

                item.addEventListener("mouseenter", function () {
                    setActiveIndex(idx);
                });

                item.addEventListener("click", function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    selectUser(user);
                });

                dropdown.appendChild(item);
            });
        }

        dropdown.classList.remove("d-none");
    }

    function setActiveIndex(idx) {
        const items = dropdown.querySelectorAll(".user-autocomplete-item");
        items.forEach((item, i) => {
            if (i === idx) {
                item.style.background = "rgba(37, 99, 235, 0.35)";
                item.scrollIntoView({ block: "nearest" });
            } else {
                item.style.background = "transparent";
            }
        });
        activeIndex = idx;
    }

    function selectUser(user) {
        searchInput.value = user.username;

        // Ensure receiver select has an option with user.id and select it
        let option = Array.from(receiverSelect.options).find(o => o.value == user.id);
        if (!option) {
            option = new Option(user.username, user.id, true, true);
            receiverSelect.add(option);
        } else {
            option.selected = true;
        }

        receiverSelect.value = user.id;
        closeDropdown();

        const event = new Event("change", { bubbles: true });
        receiverSelect.dispatchEvent(event);
    }

    function closeDropdown() {
        dropdown.classList.add("d-none");
        dropdown.innerHTML = "";
        activeIndex = -1;
        currentResults = [];
    }

    function performSearch(query) {
        if (!query || query.length < 1) {
            closeDropdown();
            return;
        }

        renderLoading();

        const url = `/teams/${encodeURIComponent(teamSlug)}/invite/autocomplete/?q=${encodeURIComponent(query)}`;

        fetch(url, {
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        })
            .then(res => {
                if (!res.ok) throw new Error("Search error");
                return res.json();
            })
            .then(data => {
                renderResults(data.users || []);
            })
            .catch(() => {
                renderResults([]);
            });
    }

    // Event listeners
    searchInput.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        const q = this.value.trim();

        if (q.length < 1) {
            closeDropdown();
            receiverSelect.value = "";
            return;
        }

        debounceTimer = setTimeout(() => {
            performSearch(q);
        }, 250);
    });

    searchInput.addEventListener("focus", function () {
        const q = this.value.trim();
        if (q.length >= 1) {
            performSearch(q);
        }
    });

    searchInput.addEventListener("keydown", function (e) {
        const items = dropdown.querySelectorAll(".user-autocomplete-item");

        if (dropdown.classList.contains("d-none")) {
            if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                const q = searchInput.value.trim();
                if (q.length >= 1) performSearch(q);
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
            if (activeIndex >= 0 && currentResults[activeIndex]) {
                e.preventDefault();
                selectUser(currentResults[activeIndex]);
            }
        } else if (e.key === "Escape") {
            e.preventDefault();
            closeDropdown();
        }
    });

    document.addEventListener("click", function (e) {
        if (!wrapper.contains(e.target)) {
            closeDropdown();
        }
    });
});
