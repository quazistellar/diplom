// данный класс представляет движение звезд на заднем плане сайта
class StarsAnimation {
    constructor() {
        this.canvas = document.getElementById('stars-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.stars = [];
        this.animationId = null;
        
        this.init();
        this.startAnimation();
        
        window.addEventListener('resize', () => this.handleResize());
        window.starsAnimation = this;
    }

    init() {
        this.setCanvasSize();
        this.createStars();
        this.updateColors();
    }

    setCanvasSize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    createStars() {
        const starCount = Math.min(60, Math.floor(window.innerWidth * window.innerHeight / 20000));
        this.stars = [];
        
        for (let i = 0; i < starCount; i++) {
            this.stars.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                size: Math.random() * 1.2 + 0.5,
                speed: Math.random() * 0.2 + 0.05,
                opacity: Math.random() * 0.5 + 0.3,
                directionX: (Math.random() - 0.5) * 0.3,
                directionY: (Math.random() - 0.5) * 0.3
            });
        }
    }

    updateColors() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (isDark) {
            this.starColor = 'rgba(255, 255, 255, 0.9)';
        } else {
            this.starColor = 'rgba(239, 221, 162, 0.8)';
        }
    }

    drawStars() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.stars.forEach(star => {
            this.ctx.beginPath();
            this.ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
            this.ctx.fillStyle = this.starColor.replace('0.9', star.opacity.toString()).replace('0.7', star.opacity.toString());
            this.ctx.fill();
            
            const gradient = this.ctx.createRadialGradient(
                star.x, star.y, 0,
                star.x, star.y, star.size * 4
            );
            gradient.addColorStop(0, this.starColor.replace('0.9', (star.opacity * 0.5).toString()).replace('0.7', (star.opacity * 0.5).toString()));
            gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
            
            this.ctx.beginPath();
            this.ctx.arc(star.x, star.y, star.size * 4, 0, Math.PI * 2);
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
        this.drawStars();
        this.animationId = requestAnimationFrame(() => this.animate());
    }

    startAnimation() {
        if (!this.animationId) {
            this.animate();
        }
    }

    handleResize() {
        this.setCanvasSize();
        this.createStars();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const starsAnimation = new StarsAnimation();
    
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'data-theme') {
                starsAnimation.updateColors();
            }
        });
    });
    
    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
    });
});