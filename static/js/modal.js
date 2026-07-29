/**
 * Custom Modal System API
 * Replaces native alert(), confirm(), prompt(), and Swal.fire()
 */

class CustomModalSystem {
    constructor() {
        this.createContainer();
        this.activeModals = [];
        this.loadingModal = null;
        
        // Bind escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.activeModals.length > 0) {
                const topModal = this.activeModals[this.activeModals.length - 1];
                // Prevent closing loading modal with escape
                if (!topModal.isLoading && topModal.options.allowOutsideClick !== false) {
                    this.closeModal(topModal.id);
                }
            }
        });
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'custom-modal-container';
        document.body.appendChild(this.container);
    }

    generateId() {
        return 'modal-' + Math.random().toString(36).substr(2, 9);
    }

    createModalHTML(options) {
        const id = this.generateId();
        const typeClass = `custom-modal-${options.type}`;
        
        let iconHTML = '';
        if (options.type === 'success') iconHTML = '<i class="fa-solid fa-circle-check"></i>';
        else if (options.type === 'error') iconHTML = '<i class="fa-solid fa-circle-xmark"></i>';
        else if (options.type === 'warning') iconHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
        else if (options.type === 'info') iconHTML = '<i class="fa-solid fa-circle-info"></i>';
        else if (options.type === 'confirm') iconHTML = '<i class="fa-solid fa-circle-question"></i>';
        
        if (options.iconHTMLOverride) iconHTML = options.iconHTMLOverride;

        let contentHTML = `
            <div class="custom-modal-backdrop" id="backdrop-${id}">
                <div class="custom-modal ${typeClass}" id="${id}" role="dialog" aria-modal="true">
                    ${options.type === 'loading' ? '<div class="custom-modal-spinner"></div>' : `<div class="custom-modal-icon">${iconHTML}</div>`}
                    
                    ${options.title ? `<h3 class="custom-modal-title">${options.title}</h3>` : ''}
                    ${options.message ? `<p class="custom-modal-desc" id="desc-${id}">${options.message}</p>` : ''}
                    
                    ${options.details ? `
                        <button class="custom-modal-details-btn" onclick="document.getElementById('details-${id}').classList.toggle('show')">Toggle Technical Details</button>
                        <div class="custom-modal-details" id="details-${id}">${options.details}</div>
                    ` : ''}

                    ${options.inputType ? `
                        ${options.inputType === 'textarea' 
                            ? `<textarea class="custom-modal-input custom-modal-textarea" id="input-${id}" placeholder="Type here..."></textarea>`
                            : `<input type="${options.inputType}" class="custom-modal-input" id="input-${id}" placeholder="Type here...">`
                        }
                    ` : ''}

                    ${options.type !== 'loading' ? `
                    <div class="custom-modal-buttons">
                        ${options.showCancelButton ? `<button class="custom-modal-btn custom-modal-btn-secondary" id="cancel-${id}">${options.cancelText || 'Cancel'}</button>` : ''}
                        <button class="custom-modal-btn ${options.confirmBtnClass || 'custom-modal-btn-primary'}" id="confirm-${id}">${options.confirmText || 'OK'}</button>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;

        this.container.insertAdjacentHTML('beforeend', contentHTML);
        
        return id;
    }

    openModal(options) {
        return new Promise((resolve) => {
            const id = this.createModalHTML(options);
            const backdrop = document.getElementById(`backdrop-${id}`);
            const modal = document.getElementById(id);
            
            const modalObj = { id, options, resolve, isLoading: options.type === 'loading' };
            this.activeModals.push(modalObj);

            // Force reflow for animation
            void backdrop.offsetWidth;
            backdrop.classList.add('modal-show');

            // Setup listeners
            if (options.type !== 'loading') {
                const confirmBtn = document.getElementById(`confirm-${id}`);
                const cancelBtn = document.getElementById(`cancel-${id}`);
                const inputEl = document.getElementById(`input-${id}`);

                if (confirmBtn) {
                    confirmBtn.addEventListener('click', () => {
                        let result = true;
                        if (options.inputType && inputEl) {
                            result = inputEl.value;
                        }
                        this.closeModal(id, result);
                    });
                }

                if (cancelBtn) {
                    cancelBtn.addEventListener('click', () => {
                        this.closeModal(id, false);
                    });
                }

                // Outside click
                if (options.allowOutsideClick !== false) {
                    backdrop.addEventListener('mousedown', (e) => {
                        if (e.target === backdrop) {
                            this.closeModal(id, options.inputType ? null : false);
                        }
                    });
                }

                // Focus input if exists
                if (inputEl) {
                    setTimeout(() => inputEl.focus(), 100);
                } else if (confirmBtn) {
                    setTimeout(() => confirmBtn.focus(), 100);
                }
            }
        });
    }

    closeModal(id, resolveValue = null) {
        const index = this.activeModals.findIndex(m => m.id === id);
        if (index > -1) {
            const modalObj = this.activeModals[index];
            const backdrop = document.getElementById(`backdrop-${id}`);
            
            backdrop.classList.remove('modal-show');
            
            setTimeout(() => {
                backdrop.remove();
                this.activeModals.splice(index, 1);
                
                if (modalObj.options.onConfirm && resolveValue) modalObj.options.onConfirm(resolveValue);
                if (modalObj.options.onCancel && !resolveValue && resolveValue !== "") modalObj.options.onCancel();
                
                modalObj.resolve(resolveValue);
            }, 250);
        }
    }

    // Public API
    showSuccess(title, message) {
        return this.openModal({ type: 'success', title, message, allowOutsideClick: true });
    }

    showError(title, message, details = null) {
        return this.openModal({ type: 'error', title, message, details, confirmBtnClass: 'custom-modal-btn-danger', allowOutsideClick: true });
    }

    showWarning(title, message) {
        return this.openModal({ type: 'warning', title, message, showCancelButton: true, confirmBtnClass: 'custom-modal-btn-danger' });
    }

    showInfo(title, message) {
        return this.openModal({ type: 'info', title, message, allowOutsideClick: true });
    }

    showConfirm({ title, message, confirmText = 'Confirm', cancelText = 'Cancel', confirmColor = 'primary', onConfirm, onCancel }) {
        const btnClass = confirmColor === 'danger' ? 'custom-modal-btn-danger' : 'custom-modal-btn-primary';
        return this.openModal({ type: 'confirm', title, message, confirmText, cancelText, showCancelButton: true, confirmBtnClass: btnClass, onConfirm, onCancel, allowOutsideClick: false });
    }

    showPrompt({ title, message, inputType = 'text', confirmText = 'Submit', cancelText = 'Cancel' }) {
        return this.openModal({ type: 'info', title, message, inputType, confirmText, cancelText, showCancelButton: true, allowOutsideClick: false });
    }

    showLoading(message) {
        if (this.loadingModal) return; // Prevent multiple loading
        const id = this.createModalHTML({ type: 'loading', title: 'Loading', message, allowOutsideClick: false });
        const backdrop = document.getElementById(`backdrop-${id}`);
        
        const modalObj = { id, options: { type: 'loading' }, resolve: () => {}, isLoading: true };
        this.activeModals.push(modalObj);
        this.loadingModal = modalObj;
        
        void backdrop.offsetWidth;
        backdrop.classList.add('modal-show');
    }

    updateLoading(message) {
        if (this.loadingModal) {
            const desc = document.getElementById(`desc-${this.loadingModal.id}`);
            if (desc) desc.innerText = message;
        }
    }

    hideLoading() {
        if (this.loadingModal) {
            this.closeModal(this.loadingModal.id);
            this.loadingModal = null;
        }
    }
}

// Global instance
window.CustomModal = new CustomModalSystem();

// Shorthands
window.showSuccess = (title, msg) => window.CustomModal.showSuccess(title, msg);
window.showError = (title, msg, details) => window.CustomModal.showError(title, msg, details);
window.showWarning = (title, msg) => window.CustomModal.showWarning(title, msg);
window.showInfo = (title, msg) => window.CustomModal.showInfo(title, msg);
window.showConfirm = (options) => window.CustomModal.showConfirm(options);
window.showPrompt = (options) => window.CustomModal.showPrompt(options);
window.showLoading = (msg) => window.CustomModal.showLoading(msg);
window.updateLoading = (msg) => window.CustomModal.updateLoading(msg);
window.hideLoading = () => window.CustomModal.hideLoading();
