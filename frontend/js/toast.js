// js/toast.js
// Modern toast notification system
// Version 1.0.0

class ToastManager {
  constructor() {
    this.container = null;
    this.defaultDuration = 5000; // 5 seconds
    this.position = 'top-right';
    this.toasts = new Map(); // Store toast elements and their timeouts
    this.counter = 0;
    
    this.init();
  }

  init() {
    // Create toast container if it doesn't exist
    if (!document.getElementById('toast-container')) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      this.container.className = `toast-container toast-container--${this.position}`;
      this.container.setAttribute('aria-live', 'polite');
      this.container.setAttribute('aria-atomic', 'false');
      document.body.appendChild(this.container);
    } else {
      this.container = document.getElementById('toast-container');
    }
  }

  // Generate unique ID for each toast
  generateId() {
    return `toast-${++this.counter}-${Date.now()}`;
  }

  // Create toast element
  createToast(options) {
    const {
      type = 'info',
      message = '',
      duration = this.defaultDuration,
      showProgress = true,
      showClose = true
    } = options;

    const toastId = this.generateId();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast toast--${type}`;
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.setAttribute('aria-describedby', `${toastId}-message`);

    // Icons for different toast types
    const icons = {
      success: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
      error: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
      warning: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
      info: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`
    };

    // Toast structure
    toast.innerHTML = `
      <div class="toast__content">
        <div class="toast__icon" aria-hidden="true">
          ${icons[type] || icons.info}
        </div>
        <div class="toast__message" id="${toastId}-message">
          ${message}
        </div>
        ${showClose ? `
          <button class="toast__close" aria-label="Close notification">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        ` : ''}
      </div>
      ${showProgress ? '<div class="toast__progress"></div>' : ''}
    `;

    return { toast, toastId };
  }

  // Show toast notification
  show(options) {
    const { toast, toastId } = this.createToast(options);
    const { duration = this.defaultDuration, showProgress = true } = options;

    // Add to container (newest on top)
    if (this.container.firstChild) {
      this.container.insertBefore(toast, this.container.firstChild);
    } else {
      this.container.appendChild(toast);
    }

    // Trigger reflow for animation
    toast.offsetHeight;
    toast.classList.add('toast--visible');

    // Setup progress bar animation
    let progressBar, progressInterval;
    if (showProgress) {
      progressBar = toast.querySelector('.toast__progress');
      if (progressBar) {
        progressBar.style.animation = `toast-progress ${duration}ms linear forwards`;
      }
    }

    // Auto-dismiss timeout
    const timeoutId = setTimeout(() => {
      this.dismiss(toastId);
    }, duration);

    // Store toast data
    this.toasts.set(toastId, {
      element: toast,
      timeoutId,
      progressInterval
    });

    // Close button handler
    const closeBtn = toast.querySelector('.toast__close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        this.dismiss(toastId);
      });
    }

    // Keyboard accessibility: auto-focus close button for screen readers
    if (closeBtn) {
      closeBtn.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.dismiss(toastId);
        }
      });
    }

    return toastId;
  }

  // Dismiss specific toast
  dismiss(toastId) {
    const toastData = this.toasts.get(toastId);
    if (!toastData) return;

    const { element, timeoutId, progressInterval } = toastData;

    // Clear timeout and interval
    clearTimeout(timeoutId);
    if (progressInterval) clearInterval(progressInterval);

    // Remove visible class to trigger exit animation
    element.classList.remove('toast--visible');
    element.classList.add('toast--hidden');

    // Remove from DOM after animation
    setTimeout(() => {
      if (element && element.parentNode) {
        element.parentNode.removeChild(element);
        this.toasts.delete(toastId);
      }
    }, 300); // Match CSS transition duration
  }

  // Dismiss all toasts
  dismissAll() {
    this.toasts.forEach((_, toastId) => {
      this.dismiss(toastId);
    });
  }

  // Set position
  setPosition(position) {
    const validPositions = ['top-right', 'top-left', 'bottom-right', 'bottom-left', 'top-center', 'bottom-center'];
    if (validPositions.includes(position)) {
      this.position = position;
      this.container.className = `toast-container toast-container--${position}`;
    }
  }

  // Set default duration
  setDefaultDuration(duration) {
    this.defaultDuration = duration;
  }

  // Convenience methods
  success(message, options = {}) {
    return this.show({ ...options, type: 'success', message });
  }

  error(message, options = {}) {
    return this.show({ ...options, type: 'error', message });
  }

  warning(message, options = {}) {
    return this.show({ ...options, type: 'warning', message });
  }

  info(message, options = {}) {
    return this.show({ ...options, type: 'info', message });
  }
}

// Create global toast instance
const toast = new ToastManager();

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { toast, ToastManager };
}