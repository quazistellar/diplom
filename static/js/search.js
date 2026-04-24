/**
 * данный файл содержит в себе программный код для работы 
 * динамического поиска в шапке сайта через БД
 */

document.addEventListener('DOMContentLoaded', function() {
    const searchInputs = document.querySelectorAll('.search-input');
    const searchResults = document.querySelectorAll('.search-results');
    
    let searchTimer;
    
    async function performSearch(query, resultsContainer) {
        if (!query.trim() || query.length < 2) {
            resultsContainer.innerHTML = '';
            resultsContainer.classList.remove('active');
            return;
        }

        resultsContainer.innerHTML = `
            <div class="search-no-results">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Поиск...</p>
            </div>
        `;
        resultsContainer.classList.add('active');
        
        try {
            const response = await fetch(`/search/?q=${encodeURIComponent(query)}`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Ошибка сети');
            }
            
            const data = await response.json();
            displayResults(data, resultsContainer);
            
        } catch (error) {
            console.error('Ошибка поиска:', error);
            resultsContainer.innerHTML = `
                <div class="search-no-results">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Ошибка при поиске</p>
                    <small>Попробуйте позже</small>
                </div>
            `;
        }
    }
    
    function displayResults(data, container) {
        container.innerHTML = '';
        
        if (data.results.length === 0) {
            if (data.suggestion) {
                container.innerHTML = `
                    <div class="search-no-results">
                        <i class="fas fa-search"></i>
                        <p>Курсы не найдены</p>
                        <small>Возможно вы имели ввиду:</small>
                        <a href="${data.suggestion.url}" class="search-suggestion">
                            ${escapeHtml(data.suggestion.title)}
                        </a>
                    </div>
                `;
            } else {
                container.innerHTML = `
                    <div class="search-no-results">
                        <i class="fas fa-search"></i>
                        <p>Курсы не найдены</p>
                        <small>Попробуйте другие ключевые слова</small>
                    </div>
                `;
            }
        } else {
            data.results.forEach(item => {
                const resultElement = document.createElement('a');
                resultElement.className = 'search-result-item';
                resultElement.href = item.url;
                resultElement.innerHTML = `
                    <i class="${item.icon} search-result-icon"></i>
                    <div>
                        <div class="search-result-title">${escapeHtml(item.title)}</div>
                        <div class="search-result-category">${escapeHtml(item.category)}</div>
                    </div>
                `;
                container.appendChild(resultElement);
            });
        }
        
        container.classList.add('active');
    }
    
    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    searchInputs.forEach((input, index) => {
        const resultsContainer = searchResults[index];
        
        if (!input || !resultsContainer) return;
        
        input.addEventListener('input', function() {
            clearTimeout(searchTimer);
            const query = this.value;
            
            searchTimer = setTimeout(() => {
                performSearch(query, resultsContainer);
            }, 300);
        });
        
        document.addEventListener('click', function(e) {
            if (!input.contains(e.target) && !resultsContainer.contains(e.target)) {
                resultsContainer.classList.remove('active');
            }
        });
        
        input.addEventListener('focus', function() {
            if (this.value.trim().length >= 2) {
                performSearch(this.value, resultsContainer);
            }
        });
        
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                resultsContainer.classList.remove('active');
            }
        });
    });
    
    const mobileSearchInput = document.getElementById('mobileSearchInput');
    const mobileSearchResults = document.getElementById('mobileSearchResults');
    
    if (mobileSearchInput && mobileSearchResults) {
        mobileSearchInput.addEventListener('input', function() {
            clearTimeout(searchTimer);
            const query = this.value;
            
            searchTimer = setTimeout(() => {
                performSearch(query, mobileSearchResults);
            }, 300);
        });
        
        document.addEventListener('click', function(e) {
            if (!mobileSearchInput.contains(e.target) && !mobileSearchResults.contains(e.target)) {
                mobileSearchResults.classList.remove('active');
            }
        });
        
        mobileSearchInput.addEventListener('focus', function() {
            if (this.value.trim().length >= 2) {
                performSearch(this.value, mobileSearchResults);
            }
        });
        
        mobileSearchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                mobileSearchResults.classList.remove('active');
            }
        });
    }
});