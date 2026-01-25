/**
данный файл содержит в себе программный код для работы 
меню, которое появляется при увеличении масштаба сайта в его шапке
 */
document.addEventListener('DOMContentLoaded', () => {
    const burgerMenu = document.getElementById('burgerMenu');
    const mobileMenu = document.getElementById('mobileMenu');
    
    if (!burgerMenu || !mobileMenu) return;
    
    function toggleMenu() {
        burgerMenu.classList.toggle('active');
        mobileMenu.classList.toggle('active');
        document.body.style.overflow = mobileMenu.classList.contains('active') ? 'hidden' : '';
    }
    
    function closeMenu() {
        burgerMenu.classList.remove('active');
        mobileMenu.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    burgerMenu.addEventListener('click', toggleMenu);
    
    const mobileLinks = mobileMenu.querySelectorAll('a');
    mobileLinks.forEach(link => {
        link.addEventListener('click', closeMenu);
    });
    
    document.addEventListener('click', (e) => {
        if (!mobileMenu.contains(e.target) && 
            !burgerMenu.contains(e.target) && 
            mobileMenu.classList.contains('active')) {
            closeMenu();
        }
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && mobileMenu.classList.contains('active')) {
            closeMenu();
        }
    });
    
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768 && mobileMenu.classList.contains('active')) {
            closeMenu();
        }
    });
});