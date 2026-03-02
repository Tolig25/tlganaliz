// TLG Analiz Pro - Ana JavaScript Dosyası

// Global fonksiyonlar
const TLG = {
    // API çağrıları için yardımcı fonksiyon
    async api(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };
        
        const response = await fetch(url, { ...defaultOptions, ...options });
        return response.json();
    },
    
    // Bildirim göster
    notify(message, type = 'info') {
        const container = document.querySelector('.flash-messages') || document.createElement('div');
        container.className = 'flash-messages';
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" class="close-alert">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        container.appendChild(alert);
        document.body.appendChild(container);
        
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100%)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    },
    
    // Confirm dialog
    confirm(message) {
        return window.confirm(message);
    },
    
    // Format number
    formatNumber(num, decimals = 2) {
        return Number(num).toFixed(decimals);
    },
    
    // Format date
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('tr-TR');
    },
    
    // Debounce fonksiyonu
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Sayfa yüklendiğinde
document.addEventListener('DOMContentLoaded', () => {
    console.log('TLG Analiz Pro yüklendi');
});
