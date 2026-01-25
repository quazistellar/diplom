/**
данный файл содержит в себе программный код для работы 
анимации поиска в шапке сайта и его результатов 
 */


document.addEventListener('DOMContentLoaded', function() {
    const searchInputs = document.querySelectorAll('.search-input');
    const searchResults = document.querySelectorAll('.search-results');
    
    const searchData = [
        {
            id: 1,
            title: "Веб-разработка с нуля",
            category: "Программирование",
            icon: "fas fa-code",
            url: "#"
        },
        {
            id: 2,
            title: "Дизайн интерфейсов",
            category: "Дизайн",
            icon: "fas fa-palette",
            url: "#"
        },
        {
            id: 3,
            title: "Анализ данных на Python",
            category: "Аналитика",
            icon: "fas fa-chart-line",
            url: "#"
        },
        {
            id: 4,
            title: "Мобильная разработка",
            category: "Программирование",
            icon: "fas fa-mobile-alt",
            url: "#"
        },
        {
            id: 5,
            title: "Маркетинг в социальных сетях",
            category: "Маркетинг",
            icon: "fas fa-hashtag",
            url: "#"
        }
    ];
    
    function performSearch(query, resultsContainer) {
        if (!query.trim()) {
            resultsContainer.innerHTML = '';
            resultsContainer.classList.remove('active');
            return;
        }
        
        const searchTerm = query.toLowerCase().trim();
        const filteredResults = searchData.filter(item => 
            item.title.toLowerCase().includes(searchTerm) || 
            item.category.toLowerCase().includes(searchTerm)
        );
        
        displayResults(filteredResults, resultsContainer);
    }
    
    function displayResults(results, container) {
        container.innerHTML = '';
        
        if (results.length === 0) {
            container.innerHTML = `
                <div class="search-no-results">
                    <i class="fas fa-search" style="margin-bottom: 10px; font-size: 24px;"></i>
                    <p>Курсы не найдены</p>
                    <small>Попробуйте другие ключевые слова</small>
                </div>
            `;
        } else {
            results.forEach(item => {
                const resultElement = document.createElement('div');
                resultElement.className = 'search-result-item';
                resultElement.innerHTML = `
                    <i class="${item.icon} search-result-icon"></i>
                    <div>
                        <div class="search-result-title">${item.title}</div>
                        <div class="search-result-category">${item.category}</div>
                    </div>
                `;
                
                resultElement.addEventListener('click', function() {
                    window.location.href = item.url;
                    container.classList.remove('active');
                    document.querySelectorAll('.search-input').forEach(input => {
                        input.value = '';
                    });
                });
                
                container.appendChild(resultElement);
            });
        }
        
        container.classList.add('active');
    }
    
    searchInputs.forEach((input, index) => {
        const resultsContainer = searchResults[index];
        
        input.addEventListener('input', function() {
            performSearch(this.value, resultsContainer);
        });
        
        document.addEventListener('click', function(e) {
            if (!input.contains(e.target) && !resultsContainer.contains(e.target)) {
                resultsContainer.classList.remove('active');
            }
        });
        
        input.addEventListener('focus', function() {
            if (this.value.trim()) {
                performSearch(this.value, resultsContainer);
            }
        });
        
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                resultsContainer.classList.remove('active');
            }
        });
    });
});