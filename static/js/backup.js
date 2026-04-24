/* класс для работы с бэкапами */
class BackupManager {
    static instance = null;
    
    constructor() {
        if (BackupManager.instance) {
            return BackupManager.instance;
        }
        
        this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (!this.csrfToken) {
            this.csrfToken = this.getCookie('csrftoken');
        }
        
        this.messageContainer = document.getElementById('backupMessageContainer');
        this.backupList = document.getElementById('backupList');
        this.currentBackupFile = null;

        this.hideModals = this.hideModals.bind(this);
        this.showCreateModal = this.showCreateModal.bind(this);
        this.showRestoreModal = this.showRestoreModal.bind(this);
        this.showRestoreFinalModal = this.showRestoreFinalModal.bind(this);
        this.executeCreateBackup = this.executeCreateBackup.bind(this);
        this.executeRestoreBackup = this.executeRestoreBackup.bind(this);
        
        this.initEventListeners();
        
        BackupManager.instance = this;
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    initEventListeners() {
        const showCreateBtn = document.getElementById('showCreateModalBtn');
        if (showCreateBtn) {
            showCreateBtn.addEventListener('click', this.showCreateModal);
        }

        const showRestoreBtn = document.getElementById('showRestoreModalBtn');
        if (showRestoreBtn) {
            showRestoreBtn.addEventListener('click', this.showRestoreModal);
        }

        document.querySelectorAll('.restore-single-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const backupFile = e.currentTarget.dataset.backup;
                this.showRestoreModal(backupFile);
            });
        });

        const confirmCreateBtn = document.getElementById('confirmCreateBtn');
        if (confirmCreateBtn) {
            confirmCreateBtn.addEventListener('click', this.executeCreateBackup);
        }

        const confirmRestoreFirstBtn = document.getElementById('confirmRestoreFirstBtn');
        if (confirmRestoreFirstBtn) {
            confirmRestoreFirstBtn.addEventListener('click', this.showRestoreFinalModal);
        }

        const confirmRestoreFinalBtn = document.getElementById('confirmRestoreFinalBtn');
        if (confirmRestoreFinalBtn) {
            confirmRestoreFinalBtn.addEventListener('click', this.executeRestoreBackup);
        }

        const confirmInput = document.getElementById('confirmText');
        if (confirmInput) {
            confirmInput.addEventListener('input', (e) => {
                const finalBtn = document.getElementById('confirmRestoreFinalBtn');
                if (finalBtn) {
                    finalBtn.disabled = e.target.value !== 'ПОДТВЕРЖДАЮ';
                }
            });
        }

        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', this.hideModals);
        });

        document.querySelectorAll('.modal-btn-secondary').forEach(btn => {
            btn.addEventListener('click', this.hideModals);
        });

        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', this.hideModals);
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideModals();
            }
        });
    }

    showCreateModal() {
        this.hideModals();
        document.getElementById('createBackupModal').classList.add('active');
    }

    showRestoreModal(backupFile = null) {
        const select = document.getElementById('backupFileSelect');
        
        if (backupFile) {
            this.currentBackupFile = backupFile;
        } else if (select && select.value) {
            this.currentBackupFile = select.value;
        } else {
            this.showMessage('Выберите файл для восстановления', 'error');
            return;
        }

        if (!this.currentBackupFile) {
            this.showMessage('Выберите файл для восстановления', 'error');
            return;
        }

        document.getElementById('restoreFileName').textContent = `Файл: ${this.currentBackupFile}`;
        this.hideModals();
        document.getElementById('restoreModalFirst').classList.add('active');
    }

    showRestoreFinalModal() {
        this.hideModals();
        const confirmInput = document.getElementById('confirmText');
        if (confirmInput) {
            confirmInput.value = '';
        }
        const finalBtn = document.getElementById('confirmRestoreFinalBtn');
        if (finalBtn) {
            finalBtn.disabled = true;
        }
        document.getElementById('restoreModalFinal').classList.add('active');
    }

    hideModals() {
        document.querySelectorAll('.backup-modal').forEach(modal => {
            modal.classList.remove('active');
        });
    }

    async executeCreateBackup() {
        this.hideModals();
        
        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', this.csrfToken);
        formData.append('action', 'backup');

        const createBtn = document.getElementById('showCreateModalBtn');
        const originalText = createBtn.innerHTML;
        
        createBtn.disabled = true;
        createBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Создание бэкапа...';

        try {
            const response = await fetch(window.location.href, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.showSuccessMessage(data);
                if (data.backups) {
                    this.updateBackupList(data.backups);
                }
            } else {
                this.showErrorMessage(data);
            }
        } catch (error) {
            this.showMessage('Произошла ошибка при выполнении запроса', 'error');
            console.error('Error:', error);
        } finally {
            createBtn.disabled = false;
            createBtn.innerHTML = originalText;
        }
    }

    async executeRestoreBackup() {
        this.hideModals();

        if (!this.currentBackupFile) {
            this.showMessage('Не указан файл для восстановления', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', this.csrfToken);
        formData.append('action', 'restore');
        formData.append('backup_file', this.currentBackupFile);

        const restoreBtn = document.getElementById('showRestoreModalBtn');
        const originalText = restoreBtn ? restoreBtn.innerHTML : 'Восстановить';
        
        if (restoreBtn) {
            restoreBtn.disabled = true;
            restoreBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Восстановление...';
        }

        try {
            const response = await fetch(window.location.href, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.showSuccessMessage(data);
                if (data.backups) {
                    this.updateBackupList(data.backups);
                }
            } else {
                this.showErrorMessage(data);
            }
        } catch (error) {
            this.showMessage('Произошла ошибка при выполнении запроса', 'error');
            console.error('Error:', error);
        } finally {
            if (restoreBtn) {
                restoreBtn.disabled = false;
                restoreBtn.innerHTML = originalText;
            }
            this.currentBackupFile = null;
        }
    }

    showSuccessMessage(data) {
        let messageHtml = `
            <div class="backup-message success">
                <div class="message-icon">
                    <i class="fas fa-check-circle"></i>
                </div>
                <div class="message-content">
                    <strong>${data.message}</strong>
        `;

        if (data.backup_file) {
            messageHtml += `
                <div class="message-details">
                    <span class="detail-item">
                        <i class="fas fa-file"></i> ${data.backup_file}
                    </span>
            `;
            
            if (data.backup_size) {
                messageHtml += `
                    <span class="detail-item">
                        <i class="fas fa-weight-hanging"></i> ${data.backup_size}
                    </span>
                `;
            }
            
            if (data.backup_time || data.restore_time) {
                const time = data.backup_time || data.restore_time;
                messageHtml += `
                    <span class="detail-item">
                        <i class="far fa-clock"></i> ${time}
                    </span>
                `;
            }
            
            messageHtml += `</div>`;
        }

        if (data.warning) {
            messageHtml += `
                <div class="warning-box">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>${data.warning}</span>
                </div>
            `;
        }

        messageHtml += `</div></div>`;
        
        this.messageContainer.innerHTML = messageHtml;
        this.messageContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        setTimeout(() => {
            const msg = this.messageContainer.querySelector('.backup-message');
            if (msg) {
                msg.style.opacity = '0';
                setTimeout(() => {
                    if (this.messageContainer.innerHTML === messageHtml) {
                        this.messageContainer.innerHTML = '';
                    }
                }, 300);
            }
        }, 5000);
    }

    showErrorMessage(data) {
        let messageHtml = `
            <div class="backup-message error">
                <div class="message-icon">
                    <i class="fas fa-exclamation-circle"></i>
                </div>
                <div class="message-content">
                    <strong>${data.message}</strong>
        `;

        if (data.details) {
            messageHtml += `
                <div class="message-details error-details">
                    ${data.details}
                </div>
            `;
        }

        messageHtml += `</div></div>`;
        
        this.messageContainer.innerHTML = messageHtml;
        this.messageContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        setTimeout(() => {
            const msg = this.messageContainer.querySelector('.backup-message');
            if (msg) {
                msg.style.opacity = '0';
                setTimeout(() => {
                    if (this.messageContainer.innerHTML === messageHtml) {
                        this.messageContainer.innerHTML = '';
                    }
                }, 300);
            }
        }, 5000);
    }

    showMessage(text, type = 'info') {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };

        const messageHtml = `
            <div class="backup-message ${type}">
                <div class="message-icon">
                    <i class="fas ${icons[type]}"></i>
                </div>
                <div class="message-content">
                    <strong>${text}</strong>
                </div>
            </div>
        `;
        
        this.messageContainer.innerHTML = messageHtml;
        this.messageContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        setTimeout(() => {
            const msg = this.messageContainer.querySelector('.backup-message');
            if (msg) {
                msg.style.opacity = '0';
                setTimeout(() => {
                    if (this.messageContainer.innerHTML === messageHtml) {
                        this.messageContainer.innerHTML = '';
                    }
                }, 300);
            }
        }, 5000);
    }

    updateBackupList(backups) {
        if (!backups || backups.length === 0) {
            this.backupList.innerHTML = `
                <div class="backup-empty">
                    <i class="fas fa-database"></i>
                    <h3>Резервные копии отсутствуют</h3>
                    <p>Создайте первую резервную копию для защиты данных</p>
                </div>
            `;
            
            const restoreSelect = document.getElementById('backupFileSelect');
            if (restoreSelect) {
                restoreSelect.innerHTML = '<option value="">-- Нет доступных бэкапов --</option>';
            }
            
            const showRestoreBtn = document.getElementById('showRestoreModalBtn');
            if (showRestoreBtn) {
                showRestoreBtn.disabled = true;
            }
            return;
        }

        let listHtml = '';
        
        backups.forEach(backup => {
            listHtml += `
                <div class="backup-item" data-backup-name="${backup.name}">
                    <div class="backup-info">
                        <div class="backup-name-wrapper">
                            <i class="fas fa-file-archive"></i>
                            <span class="backup-name">${escapeHtml(backup.name)}</span>
                        </div>
                        <div class="backup-details">
                            <span class="detail-badge">
                                <i class="fas fa-weight-hanging"></i>
                                ${backup.formatted_size}
                            </span>
                            <span class="detail-badge">
                                <i class="far fa-calendar-alt"></i>
                                ${backup.formatted_time}
                            </span>
                        </div>
                    </div>
                    <div class="backup-actions">
                        <button type="button" class="btn-backup btn-backup-restore btn-small restore-single-btn" 
                                data-backup="${escapeHtml(backup.name)}">
                            <i class="fas fa-undo-alt"></i>
                            Восстановить
                        </button>
                    </div>
                </div>
            `;
        });

        this.backupList.innerHTML = listHtml;

        const restoreSelect = document.getElementById('backupFileSelect');
        if (restoreSelect) {
            let optionsHtml = '<option value="">-- Выберите файл бэкапа --</option>';
            backups.forEach(backup => {
                optionsHtml += `<option value="${escapeHtml(backup.name)}">${escapeHtml(backup.name)} (${backup.formatted_size}) - ${backup.formatted_time}</option>`;
            });
            restoreSelect.innerHTML = optionsHtml;
            
            const showRestoreBtn = document.getElementById('showRestoreModalBtn');
            if (showRestoreBtn) {
                showRestoreBtn.disabled = false;
            }
        }

        document.querySelectorAll('.restore-single-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const backupFile = e.currentTarget.dataset.backup;
                this.showRestoreModal(backupFile);
            });
        });
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

document.addEventListener('DOMContentLoaded', function() {
    window.BackupManager = BackupManager;
    window.backupManager = new BackupManager();
});