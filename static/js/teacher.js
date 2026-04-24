document.addEventListener('DOMContentLoaded', function() {
    const messages = document.querySelectorAll('.profile-message');
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
    
    initTabSwitching();
    restoreLastActiveTab();
    checkFormErrors();
});

// данная функция служит для инициализации навигации вкладок в боковом меню профиля преподавателя
function initTabSwitching() {
    const tabLinks = document.querySelectorAll('.profile-nav-btn[data-tab]');
    
    if (tabLinks.length > 0) {
        tabLinks.forEach(link => {
            link.removeAttribute('onclick');
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const tabId = this.getAttribute('data-tab');
                switchTab(tabId, this);
            });
        });
    }
}

// данная функция переключает вкладки в боковом меню профиля преподавателя
function switchTab(tabId, buttonElement = null) {
    const allNavLinks = document.querySelectorAll('.profile-nav-btn');
    allNavLinks.forEach(nav => {
        nav.classList.remove('active');
    });
    
    if (buttonElement) {
        buttonElement.classList.add('active');
    } else {
        const activeLink = document.querySelector(`.profile-nav-btn[data-tab="${tabId}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
    }
    
    const allTabs = document.querySelectorAll('.profile-tab');
    
    allTabs.forEach(tab => {
        tab.classList.remove('active');
        tab.style.display = 'none'; 
    });
    
    const activeTab = document.getElementById(`tab-${tabId}`);
    if (activeTab) {
        activeTab.classList.add('active');
        activeTab.style.display = 'block'; 
    } 
    localStorage.setItem('activeTeacherProfileTab', tabId);
}

// данная функция необходима для восстановления последней активной вкладки
function restoreLastActiveTab() {
    const passwordTab = document.getElementById('tab-password');
    if (passwordTab && passwordTab.querySelector('.profile-form-error')) {
        const passwordButton = document.querySelector('.profile-nav-btn[data-tab="password"]');
        if (passwordButton) {
            switchTab('password', passwordButton);
            return;
        }
    }
    const profileTab = document.getElementById('tab-profile');
    if (profileTab && profileTab.querySelector('.profile-form-error')) {
        const profileButton = document.querySelector('.profile-nav-btn[data-tab="profile"]');
        if (profileButton) {
            switchTab('profile', profileButton);
            return;
        }
    }
    
    const savedTab = localStorage.getItem('activeTeacherProfileTab');
    if (savedTab && document.getElementById(`tab-${savedTab}`)) {
        const button = document.querySelector(`.profile-nav-btn[data-tab="${savedTab}"]`);
        if (button) {
            switchTab(savedTab, button);
        }
    }
}

// данная функция проверяет наличие ошибок в формах и переключает на нужную вкладку
function checkFormErrors() {
    const passwordTab = document.getElementById('tab-password');
    if (passwordTab && passwordTab.querySelector('.profile-form-error')) {
        const passwordButton = document.querySelector('.profile-nav-btn[data-tab="password"]');
        if (passwordButton) {
            switchTab('password', passwordButton);
            return;
        }
    }
    
    const profileTab = document.getElementById('tab-profile');
    if (profileTab && profileTab.querySelector('.profile-form-error')) {
        const profileButton = document.querySelector('.profile-nav-btn[data-tab="profile"]');
        if (profileButton) {
            switchTab('profile', profileButton);
        }
    }
}

// данная функция подтверждает удаление объекта (курса, лекции и т.д.)
function confirmDelete(event, itemName) {
    if (!confirm(`Вы уверены, что хотите удалить "${itemName}"? Это действие нельзя отменить.`)) {
        event.preventDefault();
        return false;
    }
    return true;
}

// данная функция выполняет валидацию формы курса перед отправкой
function validateCourseForm() {
    const courseName = document.querySelector('input[name="course_name"]');
    const courseHours = document.querySelector('input[name="course_hours"]');
    
    if (courseName && courseName.value.trim().length < 3) {
        alert('Название курса должно содержать минимум 3 символа');
        courseName.focus();
        return false;
    }
    
    if (courseHours && courseHours.value && parseInt(courseHours.value) <= 0) {
        alert('Количество часов должно быть положительным числом');
        courseHours.focus();
        return false;
    }
    
    return true;
}

// данная функция добавляет обработчик на форму создания/редактирования курса
function initCourseFormValidation() {
    const courseForm = document.querySelector('form[action*="course_create"], form[action*="course_edit"]');
    if (courseForm) {
        courseForm.addEventListener('submit', validateCourseForm);
    }
}

window.confirmDelete = confirmDelete;
window.validateCourseForm = validateCourseForm;
window.switchTab = switchTab;
initCourseFormValidation();