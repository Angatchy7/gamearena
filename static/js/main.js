/* ==========================================================
   GAMEARENA — Auth Modal Controller (Safe UI-Only Modal)
   ========================================================== */

(function () {
    'use strict';

    /* ── State ─────────────────────────────────────────────── */
    var backdrop      = null;
    var loginPanel    = null;
    var registerPanel = null;
    var currentPanel  = null;
    var openerButton  = null;   // button that opened the modal (for focus restore)

    /* ── Boot (runs after DOM ready) ───────────────────────── */
    document.addEventListener('DOMContentLoaded', function () {
        backdrop      = document.getElementById('ga-auth-backdrop');
        loginPanel    = document.getElementById('ga-login-panel');
        registerPanel = document.getElementById('ga-register-panel');

        if (!backdrop) return;   // modal not on this page – exit silently

        /* Trigger buttons anywhere on the page */
        document.addEventListener('click', function (e) {

            /* Open triggers */
            var trigger = e.target.closest('[data-auth-modal]');
            if (trigger) {
                e.preventDefault();
                openerButton = trigger;
                openModal(trigger.getAttribute('data-auth-modal'));
                return;
            }

            /* Click on backdrop (outside the card) */
            if (e.target === backdrop) {
                closeModal();
            }
        });

        /* ESC key */
        document.addEventListener('keydown', function (e) {
            if ((e.key === 'Escape' || e.key === 'Esc') && backdrop.classList.contains('is-open')) {
                closeModal();
            }
        });

        /* Close buttons inside modal */
        backdrop.querySelectorAll('[data-auth-close]').forEach(function (btn) {
            btn.addEventListener('click', closeModal);
        });

        /* Switch links inside modal */
        backdrop.querySelectorAll('[data-auth-switch]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                switchPanel(btn.getAttribute('data-auth-switch'));
            });
        });
    });

    /* ── Open ───────────────────────────────────────────────── */
    function openModal(which) {
        which = which || 'login';

        if (which === 'register') {
            show(registerPanel);
            hide(loginPanel);
        } else {
            show(loginPanel);
            hide(registerPanel);
        }

        currentPanel = (which === 'register') ? registerPanel : loginPanel;
        backdrop.classList.add('is-open');
        backdrop.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';

        /* Focus first input */
        setTimeout(function () {
            var first = currentPanel && currentPanel.querySelector('input:not([type=hidden])');
            if (first) first.focus();
        }, 100);
    }

    /* ── Close ──────────────────────────────────────────────── */
    function closeModal() {
        backdrop.classList.remove('is-open');
        backdrop.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';

        /* Restore focus */
        if (openerButton) {
            openerButton.focus();
            openerButton = null;
        }
    }

    /* ── Switch between panels ──────────────────────────────── */
    function switchPanel(which) {
        if (which === 'register') {
            hide(loginPanel);
            show(registerPanel);
            currentPanel = registerPanel;
        } else {
            hide(registerPanel);
            show(loginPanel);
            currentPanel = loginPanel;
        }

        var first = currentPanel && currentPanel.querySelector('input:not([type=hidden])');
        if (first) first.focus();
    }

    /* ── Helpers ─────────────────────────────────────────────── */
    function show(el) { if (el) el.style.display = 'block'; }
    function hide(el) { if (el) el.style.display = 'none'; }

})();

/* ==========================================================
   GAMEARENA — Centralized Theme Controller
   ========================================================== */
(function () {
    'use strict';

    function getSavedTheme() {
        return localStorage.getItem('gamearena-theme') || localStorage.getItem('ga_theme') || 'dark';
    }

    function resolveSystemTheme() {
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }

    function updateActiveThemeButtons(themeChoice) {
        var buttons = document.querySelectorAll('[data-theme-val]');
        buttons.forEach(function (btn) {
            var val = btn.getAttribute('data-theme-val');
            if (val === themeChoice) {
                btn.classList.add('active');
                btn.setAttribute('aria-pressed', 'true');
            } else {
                btn.classList.remove('active');
                btn.setAttribute('aria-pressed', 'false');
            }
        });
    }

    function applyTheme(choice) {
        var effectiveTheme = choice;
        if (choice === 'system') {
            effectiveTheme = resolveSystemTheme();
        }
        document.documentElement.setAttribute('data-theme', effectiveTheme);
        try {
            localStorage.setItem('gamearena-theme', choice);
            localStorage.setItem('ga_theme', choice);
        } catch (e) {
            // Silently handle quota or disabled localStorage
        }
        updateActiveThemeButtons(choice);
    }

    // Initialize theme state on DOM ready
    document.addEventListener('DOMContentLoaded', function () {
        var currentChoice = getSavedTheme();
        applyTheme(currentChoice);

        // Bind theme selector clicks
        document.addEventListener('click', function (e) {
            var themeBtn = e.target.closest('[data-theme-val]');
            if (themeBtn) {
                var choice = themeBtn.getAttribute('data-theme-val');
                applyTheme(choice);
            }
        });

        // Listen for OS color scheme changes if system mode is selected
        if (window.matchMedia) {
            var mediaQuery = window.matchMedia('(prefers-color-scheme: light)');
            var handleMediaChange = function () {
                if (getSavedTheme() === 'system') {
                    applyTheme('system');
                }
            };
            if (mediaQuery.addEventListener) {
                mediaQuery.addEventListener('change', handleMediaChange);
            } else if (mediaQuery.addListener) {
                mediaQuery.addListener(handleMediaChange);
            }
        }
    });
})();

