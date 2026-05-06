/**
 * Sprecher Toast Notifications
 *
 * Listens for custom 'showToast' events on document.body
 * Event detail: { message: string, type: 'success'|'error'|'info', duration?: number }
 *
 * Usage:
 *   document.body.dispatchEvent(new CustomEvent('showToast', {
 *     detail: { message: 'Operation successful!', type: 'success' }
 *   }));
 */

(function() {
    'use strict';

    const TOAST_CONTAINER_ID = 'toast-container';
    const DEFAULT_DURATION = 4000; // 4 seconds

    // Get or create toast container
    function getToastContainer() {
        let container = document.getElementById(TOAST_CONTAINER_ID);
        if (!container) {
            container = document.createElement('div');
            container.id = TOAST_CONTAINER_ID;
            container.className = 'fixed top-6 right-6 z-50 space-y-3';
            document.body.appendChild(container);
        }
        return container;
    }

    // Create toast element
    function createToast(message, type, duration) {
        const container = getToastContainer();

        // Icon mapping
        const icons = {
            success: 'bx-check-circle',
            error: 'bx-x-circle',
            info: 'bx-info-circle',
            warning: 'bx-warning'
        };

        // Color classes
        const colorClasses = {
            success: 'border-[var(--sp-success)] text-[var(--sp-success)]',
            error: 'border-[var(--sp-danger)] text-[var(--sp-danger)]',
            info: 'border-[var(--sp-accent)] text-[var(--sp-accent)]',
            warning: 'border-[var(--sp-warning)] text-[var(--sp-warning)]'
        };

        const toast = document.createElement('div');
        toast.className = `toast-enter flex items-center gap-3 p-4 rounded-xl border-l-4 bg-[var(--sp-surface)] ${colorClasses[type] || colorClasses.info} shadow-lg max-w-sm`;
        toast.innerHTML = `
            <i class='bx ${icons[type] || icons.info} text-xl flex-shrink-0'></i>
            <p class="flex-1 text-sm text-[var(--sp-text)]">${escapeHtml(message)}</p>
            <button
                class="flex-shrink-0 text-[var(--sp-muted)] hover:text-[var(--sp-text)] transition-colors"
                onclick="this.parentElement.remove()"
                aria-label="Dismiss"
            >
                <i class='bx bx-x text-lg'></i>
            </button>
        `;

        container.appendChild(toast);

        // Auto-dismiss
        if (duration > 0) {
            setTimeout(() => {
                dismissToast(toast);
            }, duration);
        }

        return toast;
    }

    // Dismiss toast with animation
    function dismissToast(toast) {
        if (!toast || !toast.parentElement) return;

        toast.classList.remove('toast-enter');
        toast.classList.add('toast-exit');

        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 300); // Match CSS animation duration
    }

    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Handle showToast events
    document.body.addEventListener('showToast', function(event) {
        const { message, type = 'info', duration = DEFAULT_DURATION } = event.detail || {};

        if (message) {
            createToast(message, type, duration);
        }
    });

    // Also expose globally for direct calls
    window.showToast = function(message, type, duration) {
        createToast(message, type || 'info', duration || DEFAULT_DURATION);
    };

    // Log initialization
    console.log('[Sprecher] Toast notification system initialized');
})();