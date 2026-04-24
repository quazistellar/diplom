/**
 * перехватчик ошибок API
 * перенаправляет пользователя на страницу ошибки при проблемах с API
 */

(function() {
    'use strict';

    const isDevelopment = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost';
    

    function redirectToErrorPage(statusCode) {
        if (window.location.pathname === '/error-page/') {
            return;
        }
        
        sessionStorage.setItem('error_redirect_url', window.location.href);
        window.location.href = `/error-page/?code=${statusCode}`;
    }
    
    function showErrorMessage(statusCode) {
        const errorMessages = {
            400: 'Неверный запрос. Пожалуйста, проверьте введенные данные.',
            401: 'Необходимо авторизоваться.',
            403: 'Доступ запрещен. У вас недостаточно прав.',
            404: 'Запрашиваемый ресурс не найден.',
            405: 'Метод запроса не поддерживается.',
            408: 'Время запроса истекло. Попробуйте еще раз.',
            429: 'Слишком много запросов. Подождите немного.',
            500: 'Ошибка на сервере. Мы уже работаем над этим.',
            502: 'Ошибка шлюза. Попробуйте позже.',
            503: 'Сервис временно недоступен.',
            504: 'Время ожидания ответа истекло.'
        };
        
        const message = errorMessages[statusCode] || `Ошибка ${statusCode}. Попробуйте позже.`;
        
        let notification = document.getElementById('api-error-notification');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'api-error-notification';
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                background: #ef4444;
                color: white;
                padding: 15px 20px;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                animation: slideInRight 0.3s ease;
                max-width: 350px;
                font-family: sans-serif;
            `;
            document.body.appendChild(notification);
            
            if (!document.querySelector('#error-notification-styles')) {
                const style = document.createElement('style');
                style.id = 'error-notification-styles';
                style.textContent = `
                    @keyframes slideInRight {
                        from {
                            transform: translateX(100%);
                            opacity: 0;
                        }
                        to {
                            transform: translateX(0);
                            opacity: 1;
                        }
                    }
                `;
                document.head.appendChild(style);
            }
        }
        
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-exclamation-circle" style="font-size: 20px;"></i>
                <span style="flex: 1;">${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" 
                        style="background: none; border: none; color: white; cursor: pointer; font-size: 18px;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        setTimeout(() => {
            if (notification && notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
    
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        try {
            const response = await originalFetch.apply(this, args);
            
            if (!response.ok && response.status >= 400) {
                const url = args[0];
                const isApiRequest = url.includes('/api/') || url.includes('/api');
                
                if (isApiRequest) {
                    redirectToErrorPage(response.status);
                    return response;
                } else if (response.status === 403 || response.status === 401) {
                    redirectToErrorPage(response.status);
                }
            }
            
            return response;
        } catch (error) {
            console.error('Network error:', error);
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                redirectToErrorPage(503);
            }
            throw error;
        }
    };
    
    const originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        this.addEventListener('load', function() {
            if (this.status >= 400) {
                const isApiRequest = url.includes('/api/') || url.includes('/api');
                
                if (isApiRequest) {
                    redirectToErrorPage(this.status);
                } else if (this.status === 403 || this.status === 401) {
                    redirectToErrorPage(this.status);
                }
            }
        });
        
        this.addEventListener('error', function() {
            redirectToErrorPage(503);
        });
        
        return originalOpen.call(this, method, url, ...rest);
    };

    if (window.location.pathname === '/error-page/') {
        const urlParams = new URLSearchParams(window.location.search);
        const errorCode = urlParams.get('code');
        
        document.addEventListener('DOMContentLoaded', function() {
            const backButton = document.querySelector('.auth-btn[onclick*="history.back"]');
            if (backButton) {
                const previousUrl = sessionStorage.getItem('error_redirect_url');
                if (previousUrl && previousUrl.includes('/api/')) {
                    backButton.onclick = () => {
                        window.location.href = '/';
                    };
                }
            }
        });
    }
    
    window.addEventListener('online', function() {
        const notification = document.getElementById('api-error-notification');
        if (notification) {
            notification.remove();
        }
    });
    
    window.addEventListener('offline', function() {
        redirectToErrorPage(503);
    });

    if (!navigator.onLine) {
        redirectToErrorPage(503);
    }
})();