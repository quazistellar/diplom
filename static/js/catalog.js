/**
 * данный файл содержит код для работы каталога курсов
 * - плавное переключение между сеткой и списком
 * - работа фильтров и сортировки
 * - поиск с debounce
 */

document.addEventListener('DOMContentLoaded', function() {
    const viewBtns = document.querySelectorAll('.catalog-view-controls .view-btn');
    const coursesContainer = document.getElementById('courses-container');
    
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
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let searchTimer;
        
        searchInput.addEventListener('input', function(e) {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                const url = new URL(window.location.href);
                if (e.target.value) {
                    url.searchParams.set('search', e.target.value);
                } else {
                    url.searchParams.delete('search');
                }
                url.searchParams.delete('page');
                window.location.href = url.toString();
            }, 500);
        });
    }
    
    window.toggleFilters = function() {
        const panel = document.getElementById('filtersPanel');
        if (panel) {
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        }
    };
    
    window.toggleSort = function() {
        const panel = document.getElementById('sortPanel');
        if (panel) {
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        }
    };
    
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
