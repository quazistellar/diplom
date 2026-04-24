// функция для отображения уведомлений
function showNotification(message, type = 'error') {
    let messagesContainer = document.querySelector('.messages-container');
    
    if (!messagesContainer) {
        messagesContainer = document.createElement('div');
        messagesContainer.className = 'messages-container container mt-3';
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.insertBefore(messagesContainer, mainContent.firstChild);
        } else {
            document.body.insertBefore(messagesContainer, document.body.firstChild);
        }
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    
    let iconClass = 'fa-info-circle';
    if (type === 'success') iconClass = 'fa-check-circle';
    if (type === 'error') iconClass = 'fa-exclamation-circle';
    if (type === 'warning') iconClass = 'fa-exclamation-triangle';
    
    alertDiv.innerHTML = `
        <i class="fas ${iconClass}"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    messagesContainer.appendChild(alertDiv);
    
    setTimeout(function() {
        alertDiv.style.opacity = '0';
        alertDiv.style.transform = 'translateY(-10px)';
        setTimeout(function() {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 300);
    }, 5000);
}

// функция подтверждения удаления
function confirmDelete(event, itemName, callback) {
    event.preventDefault();
    
    const modal = document.createElement('div');
    modal.className = 'lsn-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    `;
    
    modal.innerHTML = `
        <div class="lsn-modal-content" style="
            background: var(--surface);
            border-radius: var(--radius);
            max-width: 450px;
            width: 90%;
            padding: 30px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            animation: slideIn 0.3s ease;
        ">
            <i class="fas fa-exclamation-triangle" style="font-size: 64px; color: #f1c40f; margin-bottom: 20px;"></i>
            <h3 style="color: var(--text); margin-bottom: 15px;">Подтверждение</h3>
            <p style="color: var(--text-soft); margin-bottom: 10px;">Вы уверены, что хотите удалить</p>
            <strong style="color: var(--primary); font-size: 18px; display: block; margin: 15px 0;">"${itemName}"</strong>
            <p style="color: var(--text-soft); font-size: 14px;">Это действие нельзя отменить.</p>
            <div style="display: flex; gap: 15px; justify-content: center; margin-top: 25px;">
                <button class="lsn-btn lsn-btn-outline" id="cancel-delete" style="padding: 10px 24px;">Отмена</button>
                <button class="lsn-btn lsn-btn-danger" id="confirm-delete" style="padding: 10px 24px;">Удалить</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const cancelBtn = modal.querySelector('#cancel-delete');
    const confirmBtn = modal.querySelector('#confirm-delete');
    
    cancelBtn.addEventListener('click', function() {
        modal.remove();
    });
    
    confirmBtn.addEventListener('click', function() {
        modal.remove();
        if (callback) callback();
    });
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
    
    return false;
}

// функция переключения вкладок
function initTabs() {
    const navLinks = document.querySelectorAll('.lsn-nav-link[data-tab]');
    const tabs = document.querySelectorAll('.lsn-tab');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tabName = this.getAttribute('data-tab');
            
            navLinks.forEach(nav => nav.classList.remove('active'));
            tabs.forEach(tab => tab.classList.remove('active'));
            
            this.classList.add('active');
            const targetTab = document.getElementById(`${tabName}-tab`);
            if (targetTab) {
                targetTab.classList.add('active');
            }
        });
    });
}

// функция добавления в избранное
async function toggleFavorite(courseId, button) {
    try {
        const response = await fetch(`/listener/favorites/toggle/${courseId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.is_favorite) {
            if (button) {
                button.classList.add('active');
                button.querySelector('i').style.color = '#ff4757';
            }
            showNotification('Курс добавлен в избранное', 'success');
        } else {
            if (button) {
                button.classList.remove('active');
                button.querySelector('i').style.color = '';
            }
            showNotification('Курс удален из избранного', 'info');
        }
        
        return data;
    } catch (error) {
        console.error('Error:', error);
        showNotification('Ошибка при изменении избранного', 'error');
    }
}

// функция получения CSRF-токен
function getCSRFToken() {
    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) return csrfToken.value;
    
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue;
}

// функция проверки сертификата
function checkCertificateEligibility(courseId) {
    fetch(`/listener/course/${courseId}/check-certificate/`)
        .then(response => response.json())
        .then(data => {
            const pending = document.getElementById('certificate-pending');
            const eligible = document.getElementById('certificate-eligible');
            const existing = document.getElementById('certificate-existing');
            const errorDiv = document.getElementById('certificate-error');
            
            if (pending) pending.style.display = 'none';
            if (eligible) eligible.style.display = 'none';
            if (existing) existing.style.display = 'none';
            if (errorDiv) errorDiv.style.display = 'none';
            
            if (data.eligible && eligible) {
                eligible.style.display = 'block';
            } else if (data.has_certificate && existing) {
                existing.style.display = 'block';
            } else if (pending) {
                pending.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    const messages = document.querySelectorAll('.alert');
    messages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            message.style.transform = 'translateY(-10px)';
            setTimeout(function() {
                if (message.parentNode) {
                    message.remove();
                }
            }, 300);
        }, 5000);
    });
    
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-30px) scale(0.95);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
        .lsn-btn-danger {
            background: linear-gradient(135deg, #e74c3c, #c0392b);
            color: white;
        }
        .lsn-btn-danger:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(231, 76, 60, 0.3);
        }
    `;
    document.head.appendChild(style);
});

window.showNotification = showNotification;
window.confirmDelete = confirmDelete;
window.toggleFavorite = toggleFavorite;
window.checkCertificateEligibility = checkCertificateEligibility;