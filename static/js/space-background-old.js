class SpaceBackground {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.stars = [];
        this.animating = true;
        
        this.init();
        this.animate();
        this.setupResize();
    }
    
    init() {
        this.resizeCanvas();
        this.createStars();
    }
    
    resizeCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }
    
    createStars() {
        const starCount = Math.min(100, Math.floor((window.innerWidth * window.innerHeight) / 10000));
        this.stars = [];
        
        for (let i = 0; i < starCount; i++) {
            this.stars.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                size: Math.random() * 2 + 0.5,
                speed: Math.random() * 0.5 + 0.1,
                opacity: Math.random() * 0.5 + 0.3,
                directionX: (Math.random() - 0.5) * 0.3,
                directionY: (Math.random() - 0.5) * 0.3
            });
        }
    }
    
    drawStars() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        const currentTheme = document.documentElement.getAttribute('data-theme');
        let starColor = currentTheme === 'dark' ? 'rgba(255, 255, 255, 0.9)' : 'rgba(124, 58, 237, 0.7)';
        
        this.stars.forEach(star => {
            this.ctx.beginPath();
            this.ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
            this.ctx.fillStyle = starColor.replace('0.9', star.opacity.toString());
            this.ctx.fill();
            
            const gradient = this.ctx.createRadialGradient(
                star.x, star.y, 0,
                star.x, star.y, star.size * 3
            );
            gradient.addColorStop(0, starColor.replace('0.9', (star.opacity * 0.3).toString()));
            gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
            
            this.ctx.beginPath();
            this.ctx.arc(star.x, star.y, star.size * 3, 0, Math.PI * 2);
            this.ctx.fillStyle = gradient;
            this.ctx.fill();
            
            star.x += star.directionX * star.speed;
            star.y += star.directionY * star.speed;
            
            if (star.x < -50) star.x = this.canvas.width + 50;
            if (star.x > this.canvas.width + 50) star.x = -50;
            if (star.y < -50) star.y = this.canvas.height + 50;
            if (star.y > this.canvas.height + 50) star.y = -50;
            
            if (Math.random() < 0.005) {
                star.directionX = (Math.random() - 0.5) * 0.3;
                star.directionY = (Math.random() - 0.5) * 0.3;
            }
        });
    }
    
    animate() {
        if (!this.animating) return;
        
        this.drawStars();
        requestAnimationFrame(() => this.animate());
    }
    
    setupResize() {
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.resizeCanvas();
                this.createStars();
            }, 250);
        });
    }
    
    destroy() {
        this.animating = false;
        window.removeEventListener('resize', this.setupResize);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const spaceCanvas = document.getElementById('spaceCanvas');
    if (spaceCanvas) {
        new SpaceBackground('spaceCanvas');
    }
});