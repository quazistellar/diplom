document.addEventListener('DOMContentLoaded', function() {
    initializePasswordToggles();      
    initializeCheckboxValidation();   
    initializeRoleValidation();      
    initializeInputIcons();           
});

/**
 * инициализация иконка глаза для показа/скрытия пароля
 */
function initializePasswordToggles() {
    const passwordFields = document.querySelectorAll('.password-field');
    
    passwordFields.forEach(field => {
        const wrapper = field.closest('.auth-input-wrapper');
        if (!wrapper) return;
        
        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'password-toggle-btn';
        toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i>';
        
        wrapper.appendChild(toggleBtn);
        
        toggleBtn.addEventListener('click', function() {
            const type = field.getAttribute('type') === 'password' ? 'text' : 'password';
            field.setAttribute('type', type);
            
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
    });
}

/**
 * валидация чекбокса согласия
 */
function initializeCheckboxValidation() {
    const forms = document.querySelectorAll('.auth-form');
    
    forms.forEach(form => {
        const checkbox = form.querySelector('#accept_policies');
        const checkboxError = document.getElementById('checkbox-error-message');
        
        if (!checkbox || !checkboxError) return;
        
        form.addEventListener('submit', function(e) {
            if (!checkbox.checked) {
                e.preventDefault();
                checkboxError.style.display = 'flex';
                checkboxError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
        
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                checkboxError.style.display = 'none';
            }
        });
    });
}

/**
 * валидация выбора роли (для преподаватель/методист)
 */
function initializeRoleValidation() {
    const roleRadios = document.querySelectorAll('input[name="role_choice"]');
    const roleError = document.getElementById('role-error-message');
    
    if (!roleRadios.length || !roleError) return;
    
    function isRoleSelected() {
        return Array.from(roleRadios).some(radio => radio.checked);
    }
    
    const form = document.getElementById('registrationForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!isRoleSelected()) {
                e.preventDefault();
                roleError.style.display = 'flex';
                roleError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    }
    
    roleRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            roleError.style.display = 'none';
        });
    });
}

/**
 * анимация иконок в полях ввода
 */
function initializeInputIcons() {
    const inputs = document.querySelectorAll('.auth-input');
    
    inputs.forEach(input => {
        if (input.type === 'file') return;
        
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