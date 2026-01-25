/**
 * данный файл содержит в себе программный код для работы 
 * отображения списка курсов в сетке по карточкам или по одному элементу
 */

document.addEventListener('DOMContentLoaded', function() {
    const viewBtns = document.querySelectorAll('.view-btn');
    const coursesContainer = document.getElementById('courses-container');
    
    if (!coursesContainer) {
        console.log('Контейнер курсов не найден');
        return;
    }
    
    function applyView(viewType) {
        coursesContainer.classList.remove('grid-view', 'list-view');
        coursesContainer.classList.add(viewType + '-view');
        viewBtns.forEach(btn => {
            if (btn.dataset.view === viewType) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        localStorage.setItem('coursesView', viewType);
        
    }
    

    function handleViewButtonClick(e) {
        e.stopPropagation();
        
        const clickedBtn = this;
        
        if (clickedBtn.classList.contains('active')) {
            return;
        }
        
        const viewType = clickedBtn.dataset.view || 'grid';
        
        applyView(viewType);
    }
    
    viewBtns.forEach(btn => {
        btn.addEventListener('click', handleViewButtonClick);
    });
    
    const savedView = localStorage.getItem('coursesView');
    
    if (savedView === 'list' || savedView === 'grid') {
        applyView(savedView);
    } else {
        applyView('grid');
    }
    
    function handleResize() {
        const currentView = localStorage.getItem('coursesView') || 'grid';
        
        if (window.innerWidth <= 768 && currentView === 'list') {
            const mobileListChoice = localStorage.getItem('mobileListView');
            if (!mobileListChoice) {
                applyView('grid');
                localStorage.setItem('mobileListView', 'auto');
            }
        } else if (window.innerWidth > 768) {
            localStorage.removeItem('mobileListView');
        }
    }
    
    window.addEventListener('resize', handleResize);
    
    handleResize();
    
    window.viewToggle = {
        setView: function(viewType) {
            if (viewType === 'grid' || viewType === 'list') {
                applyView(viewType);
                return true;
            }
            console.error('Неверный тип вида. Используйте "grid" или "list"');
            return false;
        },
        getCurrentView: function() {
            return localStorage.getItem('coursesView') || 'grid';
        }
    };
});