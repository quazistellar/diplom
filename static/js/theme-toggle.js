/**
 * данный файл содержит в себе программный код для работы 
 * смены темы приложения по нажатию на кнопку в шапке
 * с сохранением темы в БД для авторизованных пользователей
 */
document.addEventListener('DOMContentLoaded', () => {

    const themeToggles = document.querySelectorAll('.theme-toggle');
    if (themeToggles.length === 0) return;
    
    // функция получения CSRF-токена
    function getCookie(name) {
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
    
    const isAuthenticated = document.documentElement.getAttribute('data-user-authenticated') === 'true';    
    let currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    
    // функция обновления иконок на всех кнопках
    function updateAllThemeIcons() {
        themeToggles.forEach(button => {
            const sunIcon = button.querySelector('.sun-icon');
            const moonIcon = button.querySelector('.moon-icon');
            
            if (sunIcon && moonIcon) {
                if (currentTheme === 'dark') {
                    sunIcon.style.display = 'block';
                    moonIcon.style.display = 'none';
                } else {
                    sunIcon.style.display = 'none';
                    moonIcon.style.display = 'block';
                }
            }
        });
    }
    
    // функция сохранения темы на сервер
    async function saveThemeToServer(theme) {
        if (!isAuthenticated) {
            localStorage.setItem('theme', theme);
            return;
        }
        
        try {
            const response = await fetch('/theme/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ theme: theme })
            });
            
            if (response.ok) {
                localStorage.setItem('theme', theme);
            } else {
                console.error('Failed to save theme to server');
                localStorage.setItem('theme', theme);
            }
        } catch (error) {
            console.error('Error saving theme:', error);
            localStorage.setItem('theme', theme);
        }
    }
    
    // функция переключения темы
    function toggleTheme(event) {
        const clickedButton = event.currentTarget;
        
        const visionMode = localStorage.getItem('visionMode') === 'true';
        if (visionMode) {
            const msg = document.createElement('div');
            msg.textContent = 'Режим для слабовидящих активен. Сначала выключите его для смены темы.';
            msg.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#000;color:#ffd700;padding:10px;border-radius:5px;z-index:10002;font-size:14px;';
            document.body.appendChild(msg);
            setTimeout(() => msg.remove(), 3000);
            return;
        }
        
        clickedButton.style.transform = 'scale(0.9)';
        setTimeout(() => {
            clickedButton.style.transform = '';
        }, 150);
        
        currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', currentTheme);
        
        saveThemeToServer(currentTheme);
        
        updateAllThemeIcons();
        
        if (window.starsAnimation) {
            window.starsAnimation.updateColors();
        }
    }
    
    themeToggles.forEach(button => {
        button.removeEventListener('click', toggleTheme);
        button.addEventListener('click', toggleTheme);
    });
    
    updateAllThemeIcons();
    
    console.log('Theme toggle initialized, found buttons:', themeToggles.length);
});