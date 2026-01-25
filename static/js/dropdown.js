/**
данный файл содержит в себе программный код для работы 
анимации выпадающего меню в шапке сайта (header)
 */

document.addEventListener('DOMContentLoaded', function() {
    const dropdowns = document.querySelectorAll('.dropdown');
    
    dropdowns.forEach(dropdown => {
        const toggle = dropdown.querySelector('.dropdown-toggle');
        const menu = dropdown.querySelector('.dropdown-menu');
        
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            dropdowns.forEach(otherDropdown => {
                if (otherDropdown !== dropdown) {
                    otherDropdown.classList.remove('open');
                }
            });
            
            dropdown.classList.toggle('open');
        });
        
        document.addEventListener('click', function(e) {
            if (!dropdown.contains(e.target)) {
                dropdown.classList.remove('open');
            }
        });
        
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && dropdown.classList.contains('open')) {
                dropdown.classList.remove('open');
            }
        });
    });
    
    const style = document.createElement('style');
    style.textContent = `
        .dropdown.open .dropdown-menu {
            opacity: 1 !important;
            visibility: visible !important;
            transform: translateY(0) !important;
        }
        
        .dropdown.open .dropdown-icon {
            transform: rotate(180deg) !important;
        }
    `;
    document.head.appendChild(style);
});