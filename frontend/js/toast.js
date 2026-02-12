// js/toast.js
// Modern toast notification system with confirmation modal
// Version 2.0.0

class ToastManager {
  constructor() {
    this.container = null;
    this.defaultDuration = 5000;
    this.position = 'top-right';
    this.toasts = new Map();
    this.counter = 0;
    
    this.init();
  }

  init() {
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

  generateId() {
    return `toast-${++this.counter}-${Date.now()}`;
  }

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

    const icons = {
      success: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
      error: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
      warning: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
      info: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`
    };

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

  show(options) {
    const { toast, toastId } = this.createToast(options);
    const { duration = this.defaultDuration, showProgress = true } = options;

    if (this.container.firstChild) {
      this.container.insertBefore(toast, this.container.firstChild);
    } else {
      this.container.appendChild(toast);
    }

    toast.offsetHeight;
    toast.classList.add('toast--visible');

    let progressBar;
    if (showProgress) {
      progressBar = toast.querySelector('.toast__progress');
      if (progressBar) {
        progressBar.style.animation = `toast-progress ${duration}ms linear forwards`;
      }
    }

    const timeoutId = setTimeout(() => {
      this.dismiss(toastId);
    }, duration);

    this.toasts.set(toastId, {
      element: toast,
      timeoutId,
      progressBar
    });

    const closeBtn = toast.querySelector('.toast__close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        this.dismiss(toastId);
      });
      
      closeBtn.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.dismiss(toastId);
        }
      });
    }

    return toastId;
  }

  dismiss(toastId) {
    const toastData = this.toasts.get(toastId);
    if (!toastData) return;

    const { element, timeoutId } = toastData;

    clearTimeout(timeoutId);

    element.classList.remove('toast--visible');
    element.classList.add('toast--hidden');

    setTimeout(() => {
      if (element && element.parentNode) {
        element.parentNode.removeChild(element);
        this.toasts.delete(toastId);
      }
    }, 300);
  }

  dismissAll() {
    this.toasts.forEach((_, toastId) => {
      this.dismiss(toastId);
    });
  }

  setPosition(position) {
    const validPositions = ['top-right', 'top-left', 'bottom-right', 'bottom-left', 'top-center', 'bottom-center'];
    if (validPositions.includes(position)) {
      this.position = position;
      this.container.className = `toast-container toast-container--${position}`;
    }
  }

  setDefaultDuration(duration) {
    this.defaultDuration = duration;
  }

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

// Confirmation Modal Class
class ConfirmationModal {
  constructor() {
    this.modal = null;
    this.init();
  }

  init() {
    // Create modal if it doesn't exist
    if (!document.getElementById('confirmation-modal')) {
      this.modal = document.createElement('div');
      this.modal.id = 'confirmation-modal';
      this.modal.className = 'confirmation-modal';
      this.modal.setAttribute('role', 'dialog');
      this.modal.setAttribute('aria-modal', 'true');
      this.modal.setAttribute('aria-labelledby', 'confirmation-title');
      this.modal.setAttribute('aria-describedby', 'confirmation-message');
      this.modal.style.display = 'none';
      
      this.modal.innerHTML = `
        <div class="confirmation-modal__overlay"></div>
        <div class="confirmation-modal__container">
          <div class="confirmation-modal__header">
            <h3 id="confirmation-title" class="confirmation-modal__title">Confirm Action</h3>
            <button class="confirmation-modal__close" aria-label="Close">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="confirmation-modal__content">
            <div class="confirmation-modal__icon" id="confirmation-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
            </div>
            <div class="confirmation-modal__message-wrapper">
              <p id="confirmation-message" class="confirmation-modal__message">Are you sure you want to proceed?</p>
            </div>
          </div>
          <div class="confirmation-modal__footer">
            <button class="confirmation-modal__btn confirmation-modal__btn--cancel" id="confirm-cancel">Cancel</button>
            <button class="confirmation-modal__btn confirmation-modal__btn--confirm" id="confirm-ok">Confirm</button>
          </div>
        </div>
      `;
      
      document.body.appendChild(this.modal);
    } else {
      this.modal = document.getElementById('confirmation-modal');
    }
    
    // Add event listeners
    this.attachEventListeners();
  }
  
  attachEventListeners() {
    if (!this.modal) return;
    
    const overlay = this.modal.querySelector('.confirmation-modal__overlay');
    const closeBtn = this.modal.querySelector('.confirmation-modal__close');
    const cancelBtn = this.modal.querySelector('#confirm-cancel');
    
    // Remove existing listeners by cloning and replacing
    const newOverlay = overlay.cloneNode(true);
    const newCloseBtn = closeBtn.cloneNode(true);
    const newCancelBtn = cancelBtn.cloneNode(true);
    
    overlay.parentNode.replaceChild(newOverlay, overlay);
    closeBtn.parentNode.replaceChild(newCloseBtn, closeBtn);
    cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
    
    // Add fresh listeners
    newOverlay.addEventListener('click', () => this.hide());
    newCloseBtn.addEventListener('click', () => this.hide());
    newCancelBtn.addEventListener('click', () => this.hide());
    
    // Close on escape key
    document.removeEventListener('keydown', this.escapeKeyHandler);
    this.escapeKeyHandler = (e) => {
      if (e.key === 'Escape' && this.modal.style.display === 'flex') {
        this.hide();
      }
    };
    document.addEventListener('keydown', this.escapeKeyHandler);
  }

  show(options = {}) {
    return new Promise((resolve) => {
      const {
        title = 'Confirm Action',
        message = 'Are you sure you want to proceed?',
        confirmText = 'Confirm',
        cancelText = 'Cancel',
        type = 'warning'
      } = options;

      // Set title
      const titleEl = this.modal.querySelector('#confirmation-title');
      if (titleEl) titleEl.textContent = title;

      // Set message
      const messageEl = this.modal.querySelector('#confirmation-message');
      if (messageEl) messageEl.textContent = message;

      // Set icon based on type
      const iconEl = this.modal.querySelector('#confirmation-icon');
      const icons = {
        warning: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
        danger: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
        info: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
        success: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`
      };
      if (iconEl) iconEl.innerHTML = icons[type] || icons.warning;
      
      // Set modal class based on type
      this.modal.className = `confirmation-modal confirmation-modal--${type}`;

      // Set button text
      const confirmBtn = this.modal.querySelector('#confirm-ok');
      const cancelBtn = this.modal.querySelector('#confirm-cancel');
      
      if (confirmBtn) confirmBtn.textContent = confirmText;
      if (cancelBtn) cancelBtn.textContent = cancelText;

      // Show modal
      this.modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
      
      // Focus confirm button for accessibility
      setTimeout(() => {
        if (confirmBtn) confirmBtn.focus();
      }, 100);

      // Handle confirm
      const handleConfirm = () => {
        this.hide();
        resolve(true);
        cleanup();
      };

      // Handle cancel
      const handleCancel = () => {
        this.hide();
        resolve(false);
        cleanup();
      };

      // Cleanup event listeners
      const cleanup = () => {
        if (confirmBtn) confirmBtn.removeEventListener('click', handleConfirm);
        if (cancelBtn) cancelBtn.removeEventListener('click', handleCancel);
      };

      if (confirmBtn) confirmBtn.addEventListener('click', handleConfirm);
      if (cancelBtn) cancelBtn.addEventListener('click', handleCancel);
    });
  }

  hide() {
    if (this.modal) {
      this.modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  }
}

// Create global instances
const toast = new ToastManager();
const confirmationModal = new ConfirmationModal();

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { toast, ToastManager, confirmationModal, ConfirmationModal };
}