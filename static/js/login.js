document.addEventListener('DOMContentLoaded', function() {
    initializeInputIcons();
    initializeBlockTimer();
    initializePasswordToggle();
});

/**
 * данная функция выполняет анимации иконок в полях ввода
 */
function initializeInputIcons() {
    const inputs = document.querySelectorAll('.auth-input');
    
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            const icon = this.parentElement?.querySelector('.auth-input-icon');
            if (icon) {
                icon.style.color = 'var(--primary)';
            }
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                const icon = this.parentElement?.querySelector('.auth-input-icon');
                if (icon) {
                    icon.style.color = 'var(--text-soft)';
                }
            }
        });
    });
}

/**
 * данная функция инициализирует таймер блокировки аккаунта
 */
function initializeBlockTimer() {
    const timerElement = document.getElementById('blockTimer');
    if (!timerElement) return;
    
    let minutes = parseInt(timerElement.dataset.minutes);
    const blockUntilTimestamp = parseInt(timerElement.dataset.blockUntil);
    
    let blockEndTime = localStorage.getItem('blockEndTime');
    const now = Date.now();
    
    if (blockEndTime) {
        const remainingMs = parseInt(blockEndTime) - now;
        if (remainingMs > 0) {
            minutes = Math.ceil(remainingMs / 60000);
        } else {
            localStorage.removeItem('blockEndTime');
            if (blockUntilTimestamp) {
                blockEndTime = blockUntilTimestamp * 1000;
                localStorage.setItem('blockEndTime', blockEndTime);
                const remainingMs = blockEndTime - now;
                minutes = Math.ceil(remainingMs / 60000);
            }
        }
    } else {
        if (blockUntilTimestamp) {
            blockEndTime = blockUntilTimestamp * 1000;
            localStorage.setItem('blockEndTime', blockEndTime);
        } else {
            blockEndTime = now + (minutes * 60000);
            localStorage.setItem('blockEndTime', blockEndTime);
        }
    }
    
    let seconds = 0;
    const timerDisplay = document.getElementById('timerDisplay');
    
    /**
     * данная функция запускает и обновляет таймер
     */
    function updateTimer() {
        const storedEndTime = localStorage.getItem('blockEndTime');
        if (storedEndTime) {
            const remainingMs = parseInt(storedEndTime) - Date.now();
            if (remainingMs <= 0) {
                localStorage.removeItem('blockEndTime');
                location.reload();
                return;
            }
            
            minutes = Math.floor(remainingMs / 60000);
            seconds = Math.floor((remainingMs % 60000) / 1000);
        } else {
            if (minutes === 0 && seconds === 0) {
                location.reload();
                return;
            }
            
            if (seconds === 0) {
                minutes--;
                seconds = 59;
            } else {
                seconds--;
            }
        }
        
        const minutesStr = minutes.toString().padStart(2, '0');
        const secondsStr = seconds.toString().padStart(2, '0');
        if (timerDisplay) {
            timerDisplay.textContent = `${minutesStr}:${secondsStr}`;
        }
    }
    
    setInterval(updateTimer, 1000);
    updateTimer();
}

/**
 * данная функция инициализирует показ/скрытие пароля (глазок)
 */
function initializePasswordToggle() {
    const togglePasswordBtn = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password');
    
    if (togglePasswordBtn && passwordInput) {
        togglePasswordBtn.addEventListener('click', function() {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            const icon = this.querySelector('i');
            if (icon) {
                if (type === 'text') {
                    icon.classList.remove('fa-eye-slash');
                    icon.classList.add('fa-eye');
                } else {
                    icon.classList.remove('fa-eye');
                    icon.classList.add('fa-eye-slash');
                }
            }
        });
        
        const form = togglePasswordBtn.closest('form');
        if (form) {
            form.addEventListener('submit', function() {
                passwordInput.setAttribute('type', 'password');
            });
        }
    }
}