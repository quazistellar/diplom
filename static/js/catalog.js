/**
 * данный файл содержит код для работы каталога курсов
 * - плавное переключение между сеткой и списком
 * - работа фильтров и сортировки
 * - динамический поиск с выводом полных карточек курсов
 */

document.addEventListener('DOMContentLoaded', function() {
    const viewBtns = document.querySelectorAll('.catalog-view-controls .view-btn');
    const coursesContainer = document.getElementById('courses-container');
    const searchInput = document.querySelector('.catalog-filters .search-input');
    const resultsCountDiv = document.querySelector('.results-count');
    
    // данная функция экранирует HTML специальные символы для безопасного отображения
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // данная функция создает полную карточку курса для режима сетки
    function createGridCard(course) {
        return `
            <div class="course-card grid-card">
                <div class="course-image">
                    ${course.image_url ? `<img src="${course.image_url}" alt="${escapeHtml(course.title)}">` : `
                    <div class="course-image-placeholder">
                        <i class="fas fa-book"></i>
                    </div>
                    `}
                </div>
                
                <div class="course-content">
                    <div class="course-price-section">
                        ${course.price ? `
                        <div class="course-price-main">
                            <span class="course-price-amount">${course.price}</span>
                            <span class="course-price-currency">₽</span>
                            ${course.max_places ? `<span class="course-price-info">/ До ${course.max_places} мест</span>` : ''}
                        </div>
                        ` : `
                        <div class="course-price-free">
                            <span class="free-label">БЕСПЛАТНО</span>
                        </div>
                        `}
                    </div>
                    
                    <div class="course-header">
                        <h3 class="course-title" title="${escapeHtml(course.title)}">
                            ${escapeHtml(course.title)}
                        </h3>
                    </div>
                    
                    <p class="course-description" title="${escapeHtml(course.description || 'Описание курса скоро появится...')}">
                        ${escapeHtml(course.description || 'Описание курса скоро появится...').substring(0, 120)}
                    </p>

                    <div class="course-meta-tags">
                        ${course.category ? `
                        <span class="course-meta-tag category-tag">
                            <i class="fas fa-tag"></i> ${escapeHtml(course.category)}
                        </span>
                        ` : ''}
                        
                        ${course.type ? `
                        <span class="course-meta-tag type-tag">
                            <i class="fas fa-graduation-cap"></i> ${escapeHtml(course.type)}
                        </span>
                        ` : ''}
                    </div>
                    
                    <div class="course-features-grid">
                        <div class="feature-item">
                            <i class="fas fa-clock feature-icon"></i>
                            <div class="feature-info">
                                <span class="feature-label">Длительность</span>
                                <span class="feature-value">${course.hours || 0} ч</span>
                            </div>
                        </div>
                        
                        <div class="feature-item">
                            <i class="fas fa-certificate feature-icon"></i>
                            <div class="feature-info">
                                <span class="feature-label">Сертификат</span>
                                <span class="feature-value">${course.has_certificate ? 'Есть' : 'Нет'}</span>
                            </div>
                        </div>
                        
                        <div class="feature-item">
                            <i class="fas fa-check-circle feature-icon"></i>
                            <div class="feature-info">
                                <span class="feature-label">Материалы</span>
                                <span class="feature-value">${course.is_completed ? 'Готовы' : 'Пополняются'}</span>
                            </div>
                        </div>
                        
                        <div class="feature-item">
                            <i class="fas fa-star feature-icon" style="color: #ffc107;"></i>
                            <div class="feature-info">
                                <span class="feature-label">Рейтинг</span>
                                <span class="feature-value">${course.avg_rating || '0.0'}</span>
                            </div>
                        </div>
                        
                        ${course.max_places ? `
                        <div class="feature-item">
                            <i class="fas fa-users feature-icon"></i>
                            <div class="feature-info">
                                <span class="feature-label">Ограничение мест</span>
                                <span class="feature-value">До ${course.max_places}</span>
                            </div>
                        </div>
                        ` : ''}
                        
                        <div class="feature-item">
                            <i class="fas fa-user-graduate feature-icon"></i>
                            <div class="feature-info">
                                <span class="feature-label">Слушателей</span>
                                <span class="feature-value">${course.student_count || 0}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="course-actions">
                        <a href="${course.url}" class="btn btn-register btn-block">
                            <i class="fas fa-eye" style="margin-right: 6px;"></i>Подробнее
                        </a>
                    </div>
                </div>
            </div>
        `;
    }
    
    // данная функция создает полную карточку курса для режима списка
    function createListCard(course) {
        return `
            <div class="course-card list-card">
                <div class="course-image">
                    ${course.image_url ? `<img src="${course.image_url}" alt="${escapeHtml(course.title)}">` : `
                    <div class="course-image-placeholder">
                        <i class="fas fa-book"></i>
                    </div>
                    `}
                    
                    ${course.category ? `
                    <span class="course-category-badge">
                        ${escapeHtml(course.category)}
                    </span>
                    ` : ''}
                </div>
                
                <div class="course-content">
                    <div class="course-header">
                        <h3 class="course-title" title="${escapeHtml(course.title)}">
                            ${escapeHtml(course.title)}
                        </h3>
                    </div>
                    
                    <div class="course-tags">
                        <span class="course-tag">
                            <i class="fas fa-clock"></i> ${course.hours || 0} ч
                        </span>
                        
                        <span class="course-tag">
                            <i class="fas fa-certificate"></i> ${course.has_certificate ? 'Сертификат' : 'Без сертификата'}
                        </span>
                        
                        <span class="course-tag">
                            <i class="fas fa-check-circle"></i> ${course.is_completed ? 'Готов' : 'В разработке'}
                        </span>
                        
                        ${course.max_places ? `
                        <span class="course-tag">
                            <i class="fas fa-users"></i> До ${course.max_places} мест
                        </span>
                        ` : ''}
                        
                        ${course.type ? `
                        <span class="course-tag">
                            <i class="fas fa-graduation-cap"></i> ${escapeHtml(course.type)}
                        </span>
                        ` : ''}
                    </div>
                    
                    <p class="course-description-list" title="${escapeHtml(course.description || 'Описание курса скоро появится...')}">
                        ${escapeHtml(course.description || 'Описание курса скоро появится...')}
                    </p>
                    
                    <div class="course-details-row">
                        <div class="detail-item">
                            <i class="fas fa-calendar"></i>
                            <span class="detail-label">${course.created_date || ''}</span>
                        </div>
                        
                        ${course.author ? `
                        <div class="detail-item">
                            <i class="fas fa-user-tie"></i>
                            <span class="detail-label">${escapeHtml(course.author.substring(0, 15))}</span>
                        </div>
                        ` : ''}
                        
                        <div class="detail-item">
                            <i class="fas fa-star" style="color: #ffc107;"></i>
                            <span class="detail-label">${course.avg_rating || '0.0'}</span>
                        </div>
                        
                        <div class="detail-item">
                            <i class="fas fa-user-graduate"></i>
                            <span class="detail-label">${course.student_count || 0}</span>
                        </div>
                    </div>
                </div>
                
                <div class="course-sidebar">
                    <div class="course-price-section">
                        ${course.price ? `
                        <div class="course-price-main">
                            <div class="price-wrapper">
                                <span class="course-price-amount">${course.price}</span>
                                <span class="course-price-currency">₽</span>
                            </div>
                        </div>
                        ` : `
                        <div class="course-price-free">
                            <span class="free-label-list">БЕСПЛАТНО</span>
                        </div>
                        `}
                    </div>
                    
                    <div class="course-actions">
                        <a href="${course.url}" class="btn btn-register btn-block">
                            <i class="fas fa-eye" style="margin-right: 6px;"></i>Подробнее
                        </a>
                    </div>
                </div>
            </div>
        `;
    }
    
    // данная функция обновляет отображение результатов поиска на странице с полными карточками
    function updateSearchResults(data, query, currentView) {
        if (data.results && data.results.length > 0) {
            if (resultsCountDiv) {
                resultsCountDiv.innerHTML = `Найдено курсов: ${data.results.length}`;
            }
            
            let html = '';
            if (currentView === 'grid') {
                html = data.results.map(course => createGridCard(course)).join('');
                coursesContainer.innerHTML = html;
                coursesContainer.classList.add('grid-view');
                document.querySelectorAll('.list-card').forEach(card => card.style.display = 'none');
                document.querySelectorAll('.grid-card').forEach(card => card.style.display = 'flex');
            } else {
                html = data.results.map(course => createListCard(course)).join('');
                coursesContainer.innerHTML = html;
                coursesContainer.classList.add('list-view');
                document.querySelectorAll('.grid-card').forEach(card => card.style.display = 'none');
                document.querySelectorAll('.list-card').forEach(card => card.style.display = 'flex');
            }
        } else if (data.suggestion) {
            if (resultsCountDiv) {
                resultsCountDiv.innerHTML = `Найдено курсов: 0`;
            }
            coursesContainer.innerHTML = `
                <div class="search-suggestion" style="text-align: center; padding: 40px; grid-column: 1/-1;">
                    <p>Ничего не найдено по запросу "${escapeHtml(query)}"</p>
                    <p>Возможно, вы имели в виду: 
                        <a href="${data.suggestion.url}" style="color: var(--primary); text-decoration: underline;">
                            ${escapeHtml(data.suggestion.title)}
                        </a>
                    </p>
                </div>
            `;
        } else {
            if (resultsCountDiv) {
                resultsCountDiv.innerHTML = `Найдено курсов: 0`;
            }
            coursesContainer.innerHTML = `
                <div class="no-results" style="text-align: center; padding: 40px; grid-column: 1/-1;">
                    <i class="fas fa-search" style="font-size: 48px; opacity: 0.5;"></i>
                    <p>Ничего не найдено по запросу "${escapeHtml(query)}"</p>
                </div>
            `;
        }
    }
    
    // данная функция выполняет AJAX запрос для поиска курсов
    function performSearch(query, currentView) {
        fetch(`/search/?q=${encodeURIComponent(query)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Ошибка сервера');
                }
                return response.json();
            })
            .then(data => {
                updateSearchResults(data, query, currentView);
            })
            .catch(error => {
                console.error('Ошибка поиска:', error);
                const url = new URL(window.location.href);
                if (query) {
                    url.searchParams.set('search', query);
                } else {
                    url.searchParams.delete('search');
                }
                url.searchParams.delete('page');
                window.location.href = url.toString();
            });
    }
    
    // данная функция инициализирует поиск в каталоге с debounce (задержкой 300 мс)
    function initCatalogSearch() {
        if (!searchInput) return;
        
        const newSearchField = searchInput.cloneNode(true);
        searchInput.parentNode.replaceChild(newSearchField, searchInput);
        
        let searchTimer;
        
        newSearchField.addEventListener('input', function(e) {
            clearTimeout(searchTimer);
            const query = e.target.value.trim();
            
            if (query.length === 0) {
                const url = new URL(window.location.href);
                if (url.searchParams.has('search')) {
                    url.searchParams.delete('search');
                    window.location.href = url.toString();
                }
                return;
            }
            
            if (query.length < 2) return;
            
            searchTimer = setTimeout(() => {
                const currentView = coursesContainer.classList.contains('grid-view') ? 'grid' : 'list';
                performSearch(query, currentView);
            }, 300);
        });
    }
    
    // данная функция переключает вид отображения курсов (сетка/список)
    function switchView(view) {
        const activeBtn = document.querySelector('.catalog-view-controls .view-btn.active');
        if (activeBtn && activeBtn.dataset.view === view) return;

        coursesContainer.classList.add('view-transition');

        viewBtns.forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.view === view) {
                btn.classList.add('active');
            }
        });
        
        setTimeout(() => {
            coursesContainer.classList.remove('grid-view', 'list-view');
            coursesContainer.classList.add(view + '-view');
            document.querySelectorAll('.grid-card').forEach(card => {
                card.style.display = view === 'grid' ? 'flex' : 'none';
            });
            
            document.querySelectorAll('.list-card').forEach(card => {
                card.style.display = view === 'list' ? 'flex' : 'none';
            });
            
            setTimeout(() => {
                coursesContainer.classList.remove('view-transition');
            }, 50);
        }, 150);
        
        localStorage.setItem('coursesView', view);
        const url = new URL(window.location.href);
        url.searchParams.set('view', view);
        window.history.pushState({}, '', url);
    }
    
    // данная функция открывает/закрывает панель фильтров
    window.toggleFilters = function() {
        const panel = document.getElementById('filtersPanel');
        const sortPanel = document.getElementById('sortPanel');
        if (panel) {
            if (sortPanel && sortPanel.style.display === 'block') {
                sortPanel.style.display = 'none';
            }
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        }
    };
    
    // данная функция открывает/закрывает панель сортировки
    window.toggleSort = function() {
        const panel = document.getElementById('sortPanel');
        const filtersPanel = document.getElementById('filtersPanel');
        if (panel) {
            if (filtersPanel && filtersPanel.style.display === 'block') {
                filtersPanel.style.display = 'none';
            }
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        }
    };
    
    // инициализация стилей для анимации переключения вида
    if (viewBtns.length && coursesContainer) {
        if (!document.getElementById('catalog-animation-styles')) {
            const style = document.createElement('style');
            style.id = 'catalog-animation-styles';
            style.textContent = `
                .courses-container {
                    transition: opacity 0.3s ease;
                }
                .courses-container.view-transition {
                    opacity: 0.6;
                }
                .grid-card, .list-card {
                    transition: opacity 0.2s ease;
                }
            `;
            document.head.appendChild(style);
        }
        
        viewBtns.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const view = this.dataset.view;
                switchView(view);
            });
        });
        
        const savedView = localStorage.getItem('coursesView');
        if (savedView && (savedView === 'grid' || savedView === 'list')) {
            const urlParams = new URLSearchParams(window.location.search);
            const urlView = urlParams.get('view');
            if (!urlView || urlView !== savedView) {
                switchView(savedView);
            }
        }
    }
    
    // инициализация поиска в каталоге
    initCatalogSearch();
    
    // данная функция закрывает панели при клике вне их области
    document.addEventListener('click', function(e) {
        const filtersPanel = document.getElementById('filtersPanel');
        const sortPanel = document.getElementById('sortPanel');
        const filterBtn = document.querySelector('.filter-btn');
        const sortBtn = document.querySelector('.sort-btn');
        
        if (filtersPanel && filtersPanel.style.display === 'block' && 
            !filtersPanel.contains(e.target) && 
            filterBtn && !filterBtn.contains(e.target)) {
            filtersPanel.style.display = 'none';
        }
        
        if (sortPanel && sortPanel.style.display === 'block' && 
            !sortPanel.contains(e.target) && 
            sortBtn && !sortBtn.contains(e.target)) {
            sortPanel.style.display = 'none';
        }
    });
    
    // данная функция обрабатывает клики по опциям сортировки
    const sortOptions = document.querySelectorAll('.sort-option');
    if (sortOptions.length) {
        sortOptions.forEach(option => {
            option.addEventListener('click', function(e) {
                e.preventDefault();
                const href = this.getAttribute('href');
                if (href) {
                    window.location.href = href;
                }
            });
        });
    }
});

// данная функция очищает все фильтры и поиск
function clearAllFilters() {
    const url = new URL(window.location.href);
    url.search = ''; 
    url.searchParams.delete('page');
    window.location.href = url.toString();
}

// данная функция очищает только поиск
function clearSearch() {
    const url = new URL(window.location.href);
    url.searchParams.delete('search');
    url.searchParams.delete('page');
    window.location.href = url.toString();
}