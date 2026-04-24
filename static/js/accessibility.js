/* функции для включения и работы панели доступности
    - включение режима для слабовидящих 
    - включение режима высокого контраста
    - отключение и включение изображений
    - включение черно-белых изображений
*/

(function() {
    'use strict';

    (function() {
        try {
            const highContrast = localStorage.getItem('highContrast') === 'true';
            const visionMode = localStorage.getItem('visionMode') === 'true';
            
            if (highContrast && !visionMode) {
                document.body.classList.add('high-contrast');
            }
        } catch(e) {}
    })();

    function getStoredSettings() {
        try {
            return {
                visionMode: localStorage.getItem('visionMode') === 'true',
                highContrast: localStorage.getItem('highContrast') === 'true',
                imagesDisabled: localStorage.getItem('imagesDisabled') === 'true',
                imagesGrayscale: localStorage.getItem('imagesGrayscale') === 'true'
            };
        } catch(e) {
            return { visionMode: false, highContrast: false, imagesDisabled: false, imagesGrayscale: false };
        }
    }

    function saveSettings(settings) {
        try {
            if (settings.visionMode !== undefined) localStorage.setItem('visionMode', settings.visionMode);
            if (settings.highContrast !== undefined) localStorage.setItem('highContrast', settings.highContrast);
            if (settings.imagesDisabled !== undefined) localStorage.setItem('imagesDisabled', settings.imagesDisabled);
            if (settings.imagesGrayscale !== undefined) localStorage.setItem('imagesGrayscale', settings.imagesGrayscale);
        } catch(e) {}
    }

    function applyAccessibilitySettings(settings) {
        const html = document.documentElement;
        const body = document.body;

        if (settings.visionMode) {
            html.setAttribute('data-theme', 'vision');
            body.classList.add('vision-mode');
            body.classList.remove('high-contrast');
            if (settings.highContrast) settings.highContrast = false;
        } else {
            const savedTheme = localStorage.getItem('theme') || 'dark';
            html.setAttribute('data-theme', savedTheme);
            body.classList.remove('vision-mode');
            if (settings.highContrast) {
                body.classList.add('high-contrast');
            } else {
                body.classList.remove('high-contrast');
            }
        }
        let styleEl = document.getElementById('accessibility-images-style');
        
        if (settings.imagesDisabled) {
            if (!styleEl) {
                styleEl = document.createElement('style');
                styleEl.id = 'accessibility-images-style';
                document.head.appendChild(styleEl);
            }
            styleEl.textContent = 'img { display: none !important; }';
        } else if (settings.imagesGrayscale) {
            if (!styleEl) {
                styleEl = document.createElement('style');
                styleEl.id = 'accessibility-images-style';
                document.head.appendChild(styleEl);
            }
            styleEl.textContent = 'img { filter: grayscale(100%) !important; }';
        } else {
            if (styleEl) styleEl.remove();
        }

        updateButtonsState(settings);
    }

    function updateButtonsState(settings) {
        const visionBtn = document.getElementById('visionModeBtn');
        const highContrastBtn = document.getElementById('highContrastBtn');
        const disableImagesBtn = document.getElementById('disableImagesBtn');
        const grayscaleBtn = document.getElementById('grayscaleBtn');

        if (visionBtn) {
            if (settings.visionMode) {
                visionBtn.classList.add('vision-active');
            } else {
                visionBtn.classList.remove('vision-active');
            }
        }
        if (highContrastBtn) {
            if (settings.highContrast && !settings.visionMode) {
                highContrastBtn.classList.add('active');
            } else {
                highContrastBtn.classList.remove('active');
            }
        }
        if (disableImagesBtn) {
            if (settings.imagesDisabled) {
                disableImagesBtn.classList.add('active');
            } else {
                disableImagesBtn.classList.remove('active');
            }
        }
        if (grayscaleBtn) {
            if (settings.imagesGrayscale) {
                grayscaleBtn.classList.add('active');
            } else {
                grayscaleBtn.classList.remove('active');
            }
        }
    }

    function showMessage(text) {
        let msgDiv = document.getElementById('accessibility-message');
        if (!msgDiv) {
            msgDiv = document.createElement('div');
            msgDiv.id = 'accessibility-message';
            msgDiv.style.cssText = 'position:fixed;bottom:130px;right:20px;background:#000;color:#FFFF00;padding:14px 22px;border-radius:8px;border:3px solid #FFFF00;z-index:10001;font-weight:900;font-size:18px;';
            document.body.appendChild(msgDiv);
        }
        msgDiv.textContent = text;
        msgDiv.style.display = 'block';
        setTimeout(() => { if (msgDiv) msgDiv.style.display = 'none'; }, 2500);
    }

    let currentSettings = getStoredSettings();

    document.addEventListener('DOMContentLoaded', () => {
        const panel = document.getElementById('accessibility-panel');
        const toggleBtn = document.getElementById('openAccessibilityBtn');
        const mobileToggleBtn = document.getElementById('mobileAccessibilityBtn');
        const visionBtn = document.getElementById('visionModeBtn');
        const highContrastBtn = document.getElementById('highContrastBtn');
        const disableImagesBtn = document.getElementById('disableImagesBtn');
        const grayscaleBtn = document.getElementById('grayscaleBtn');
        const resetBtn = document.getElementById('resetAccessibilityBtn');
        
        if (!panel) {
            console.error('Панель доступности не найдена!');
            return;
        }
        
        function togglePanel() {
            panel.classList.toggle('show');
            const isVisible = panel.classList.contains('show');
            showMessage(isVisible ? 'Панель доступности открыта' : 'Панель доступности скрыта');
        }
        
        applyAccessibilitySettings(currentSettings);
        panel.classList.remove('show');

        if (toggleBtn) {
            toggleBtn.addEventListener('click', function(e) {
                e.preventDefault();
                togglePanel();
            });
        }
        
        if (mobileToggleBtn) {
            mobileToggleBtn.addEventListener('click', function(e) {
                e.preventDefault();
                togglePanel();
            });
        }

        if (visionBtn) {
            visionBtn.addEventListener('click', () => {
                currentSettings.visionMode = !currentSettings.visionMode;
                if (currentSettings.visionMode) currentSettings.highContrast = false;
                saveSettings(currentSettings);
                applyAccessibilitySettings(currentSettings);
                showMessage(currentSettings.visionMode ? 'Режим для слабовидящих включён' : 'Обычный режим');
            });
        }

        if (highContrastBtn) {
            highContrastBtn.addEventListener('click', () => {
                if (currentSettings.visionMode) return showMessage('Высокий контраст недоступен в режиме для слабовидящих');
                currentSettings.highContrast = !currentSettings.highContrast;
                saveSettings(currentSettings);
                applyAccessibilitySettings(currentSettings);
                showMessage(currentSettings.highContrast ? 'Высокий контраст включён' : 'Высокий контраст выключен');
            });
        }

        if (disableImagesBtn) {
            disableImagesBtn.addEventListener('click', () => {
                currentSettings.imagesDisabled = !currentSettings.imagesDisabled;
                if (currentSettings.imagesDisabled) currentSettings.imagesGrayscale = false;
                saveSettings(currentSettings);
                applyAccessibilitySettings(currentSettings);
                showMessage(currentSettings.imagesDisabled ? 'Изображения отключены' : 'Изображения включены');
            });
        }

        if (grayscaleBtn) {
            grayscaleBtn.addEventListener('click', () => {
                currentSettings.imagesGrayscale = !currentSettings.imagesGrayscale;
                if (currentSettings.imagesGrayscale) currentSettings.imagesDisabled = false;
                saveSettings(currentSettings);
                applyAccessibilitySettings(currentSettings);
                showMessage(currentSettings.imagesGrayscale ? 'Изображения чёрно-белые' : 'Цветные изображения');
            });
        }

        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                localStorage.removeItem('visionMode');
                localStorage.removeItem('highContrast');
                localStorage.removeItem('imagesDisabled');
                localStorage.removeItem('imagesGrayscale');
                currentSettings = { visionMode: false, highContrast: false, imagesDisabled: false, imagesGrayscale: false };
                applyAccessibilitySettings(currentSettings);
                showMessage('Все настройки доступности сброшены');
            });
        }
    });
})();