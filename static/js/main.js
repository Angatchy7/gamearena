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
