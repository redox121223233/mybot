// Enhanced Sticker Creator JavaScript - Fixed Version
class StickerCreator {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.currentMode = 'simple';
        this.userQuota = 3;
        this.selectedPosition = 'center';
        this.uploadedImage = null;
        this.font = null;
        this.initializeCanvas();
        this.loadUserQuota();
        this.setupEventListeners();
        this.loadFont();
    }

    async loadFont() {
        // Load Persian font
        try {
            const fontFace = new FontFace('Vazirmatn', 'url(https://fonts.googleapis.com/css2?family=Vazirmatn:wght@700&display=swap)');
            await fontFace.load();
            document.fonts.add(fontFace);
            this.font = 'bold 40px Vazirmatn';
        } catch (error) {
            console.log('Could not load Persian font, using default');
            this.font = 'bold 40px Arial';
        }
    }

    initializeCanvas() {
        this.canvas = document.createElement('canvas');
        this.canvas.width = 512;
        this.canvas.height = 512;
        this.ctx = this.canvas.getContext('2d');
    }

    setupEventListeners() {
        // Form submission
        document.getElementById('stickerForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createSticker();
        });

        // Font size slider
        const fontSlider = document.getElementById('fontSize');
        fontSlider.addEventListener('input', (e) => {
            document.getElementById('fontSizeValue').textContent = e.target.value;
        });

        // Color picker
        const colorPicker = document.getElementById('textColor');
        colorPicker.addEventListener('input', (e) => {
            this.updateColorPreview(e.target.value);
        });

        // Drag and drop
        this.setupDragAndDrop();
    }

    setupDragAndDrop() {
        const uploadArea = document.querySelector('.file-upload-label');
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.styleUploadArea(e.target, true);
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            this.styleUploadArea(e.target, false);
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.styleUploadArea(e.target, false);
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleImageFile(files[0]);
            }
        });
    }

    styleUploadArea(element, isHovering) {
        if (isHovering) {
            element.style.background = '#f0f0f0';
            element.style.borderColor = '#764ba2';
        } else {
            element.style.background = 'var(--bg-gray)';
            element.style.borderColor = '#667eea';
        }
    }

    selectMode(mode) {
        this.currentMode = mode;
        
        // Update UI
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.closest('.mode-btn').classList.add('active');

        // Show/hide advanced options
        const advancedOptions = document.getElementById('advancedOptions');
        const quotaInfo = document.getElementById('quotaInfo');
        
        if (mode === 'advanced') {
            advancedOptions.classList.add('show');
            quotaInfo.style.display = 'block';
            this.checkQuota();
        } else {
            advancedOptions.classList.remove('show');
            quotaInfo.style.display = 'none';
        }
    }

    selectPosition(position) {
        this.selectedPosition = position;
        document.querySelectorAll('.position-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
    }

    handleImageUpload(event) {
        const file = event.target.files[0];
        if (file) {
            this.handleImageFile(file);
        }
    }

    handleImageFile(file) {
        if (!file.type.startsWith('image/')) {
            this.showMessage('لطفاً فقط تصویر آپلود کنید!', 'error');
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            this.showMessage('حجم تصویر نباید بیشتر از 10MB باشد!', 'error');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                this.uploadedImage = img;
                this.updateUploadLabel(file.name);
                this.showMessage('تصویر با موفقیت آپلود شد!', 'success');
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    updateUploadLabel(filename) {
        const label = document.querySelector('.file-upload-label');
        label.innerHTML = `
            <span class='upload-icon'>✅</span>
            <span>${filename}</span>
        `;
    }

    updateColorPreview(color) {
        const preview = document.getElementById('colorPreview');
        preview.style.background = color;
        preview.textContent = color.toUpperCase();
        
        // Adjust text color for readability
        const rgb = parseInt(color.slice(1), 16);
        const r = (rgb >> 16) & 255;
        const g = (rgb >> 8) & 255;
        const b = rgb & 255;
        const brightness = (r * 299 + g * 587 + b * 114) / 1000;
        preview.style.color = brightness > 128 ? '#000' : '#fff';
    }

    async loadUserQuota() {
        try {
            const response = await fetch('/api/check-quota');
            if (response.ok) {
                const data = await response.json();
                this.userQuota = data.remaining;
                document.getElementById('remainingQuota').textContent = this.userQuota;
            }
        } catch (error) {
            console.log('Could not load quota, using default');
        }
    }

    checkQuota() {
        if (this.currentMode === 'advanced' && this.userQuota <= 0) {
            this.showMessage('سهمیه پیشرفته شما تمام شده است! لطفاً فردا مراجعه کنید یا از حالت ساده استفاده کنید.', 'warning');
            document.getElementById('createBtn').disabled = true;
            return false;
        }
        document.getElementById('createBtn').disabled = false;
        return true;
    }

    async previewSticker() {
        const text = document.getElementById('stickerText').value;
        
        if (!this.uploadedImage && !text) {
            this.showMessage('لطفاً حداقل تصویر یا متن وارد کنید!', 'error');
            return;
        }

        this.showMessage('در حال ساخت پیش‌نمایش...', 'warning');

        try {
            await this.createStickerCanvas(false);
            this.showPreview();
            this.showMessage('پیش‌نمایش آماده شد!', 'success');
        } catch (error) {
            this.showMessage('خطا در ساخت پیش‌نمایش!', 'error');
            console.error(error);
        }
    }

    async createSticker() {
        if (this.currentMode === 'advanced' && !this.checkQuota()) {
            return;
        }

        const packName = document.getElementById('packName').value;
        const text = document.getElementById('stickerText').value;

        if (!text) {
            this.showMessage('لطفاً متن استیکر را وارد کنید!', 'error');
            return;
        }

        if (packName && !this.validatePackName(packName)) {
            this.showMessage('نام پک نامعتبر است! لطفاً قوانین را مطالعه کنید.', 'error');
            return;
        }

        // Show loading
        this.showMessage('در حال ساخت استیکر...', 'warning');
        document.getElementById('createBtn').disabled = true;

        try {
            await this.createStickerCanvas(true);
            
            // Update quota for advanced mode
            if (this.currentMode === 'advanced') {
                this.userQuota--;
                document.getElementById('remainingQuota').textContent = this.userQuota;
            }

            // Download sticker
            this.downloadSticker();
            this.showMessage('استیکر با موفقیت ساخته شد! 🎉', 'success');
            
        } catch (error) {
            this.showMessage('خطا در ساخت استیکر!', 'error');
            console.error(error);
        } finally {
            document.getElementById('createBtn').disabled = false;
        }
    }

    async createStickerCanvas(final = false) {
        const text = document.getElementById('stickerText').value;
        const settings = this.getAdvancedSettings();

        // Clear canvas
        this.ctx.clearRect(0, 0, 512, 512);
        
        // Draw background
        this.drawBackground(settings.background);

        // Draw image if uploaded
        if (this.uploadedImage) {
            this.drawImage();
        }

        // Draw text
        await this.drawText(text, settings);
    }

    drawBackground(background) {
        if (!background) return;

        if (background.startsWith('gradient')) {
            const gradient = this.ctx.createLinearGradient(0, 0, 0, 512);
            
            switch (background) {
                case 'gradient1':
                    gradient.addColorStop(0, '#667eea');
                    gradient.addColorStop(1, '#764ba2');
                    break;
                case 'gradient2':
                    gradient.addColorStop(0, '#f093fb');
                    gradient.addColorStop(1, '#f5576c');
                    break;
                case 'gradient3':
                    gradient.addColorStop(0, '#f5576c');
                    gradient.addColorStop(1, '#4facfe');
                    break;
            }
            
            this.ctx.fillStyle = gradient;
            this.ctx.fillRect(0, 0, 512, 512);
        } else {
            const solidColors = {
                'solid1': '#ffffff',
                'solid2': '#000000',
                'solid3': '#4682b4'
            };
            
            this.ctx.fillStyle = solidColors[background] || '#ffffff';
            this.ctx.fillRect(0, 0, 512, 512);
        }
    }

    drawImage() {
        const img = this.uploadedImage;
        
        // Calculate dimensions to fit image in center while maintaining aspect ratio
        const maxWidth = 400;
        const maxHeight = 400;
        
        let width = img.width;
        let height = img.height;
        
        // Scale down if necessary
        if (width > maxWidth) {
            height = (maxWidth / width) * height;
            width = maxWidth;
        }
        
        if (height > maxHeight) {
            width = (maxHeight / height) * width;
            height = maxHeight;
        }
        
        // Center the image
        const x = (512 - width) / 2;
        const y = (512 - height) / 2;
        
        this.ctx.drawImage(img, x, y, width, height);
    }

    async drawText(text, settings) {
        // Set font properties
        const fontSize = settings.fontSize;
        this.font = `bold ${fontSize}px 'Vazirmatn', sans-serif`;
        this.ctx.font = this.font;
        this.ctx.fillStyle = settings.color;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';

        // Add shadow for better visibility
        this.ctx.shadowColor = settings.color === '#000000' ? '#ffffff' : '#000000';
        this.ctx.shadowBlur = 4;
        this.ctx.shadowOffsetX = 2;
        this.ctx.shadowOffsetY = 2;

        // Calculate position
        const positions = {
            "top-left": { x: 100, y: 100 },
            "top-center": { x: 256, y: 100 },
            "top-right": { x: 412, y: 100 },
            "center-left": { x: 100, y: 256 },
            "center": { x: 256, y: 256 },
            "center-right": { x: 412, y: 256 },
            "bottom-left": { x: 100, y: 412 },
            "bottom-center": { x: 256, y: 412 },
            "bottom-right": { x: 412, y: 412 }
        };

        const pos = positions[this.selectedPosition] || positions.center;
        
        // Check if text contains Persian/Arabic characters
        const isPersian = /[\u0600-\u06FF]/.test(text);
        
        if (isPersian) {
            // For Persian text, we need to handle RTL properly
            this.ctx.textAlign = 'center';
            // Persian text processing would need additional libraries
            // For now, we'll render as is (Telegram will handle RTL)
        }
        
        // Draw main text
        this.ctx.fillText(text, pos.x, pos.y);
        
        // Reset shadow
        this.ctx.shadowColor = 'transparent';
        this.ctx.shadowBlur = 0;
        this.ctx.shadowOffsetX = 0;
        this.ctx.shadowOffsetY = 0;
    }

    getAdvancedSettings() {
        if (this.currentMode === 'simple') {
            return {
                position: 'center',
                fontSize: 40,
                color: '#ffffff',
                background: null
            };
        }

        return {
            position: this.selectedPosition,
            fontSize: parseInt(document.getElementById('fontSize').value),
            color: document.getElementById('textColor').value,
            background: document.getElementById('defaultBackground').value || null
        };
    }

    showPreview() {
        const previewImage = document.getElementById('previewImage');
        const dataUrl = this.canvas.toDataURL('image/webp', 0.9);
        
        // Add has-image class for styling
        document.querySelector('.preview-area').classList.add('has-image');
        
        document.getElementById('previewPlaceholder').style.display = 'none';
        previewImage.src = dataUrl;
        previewImage.style.display = 'block';
    }

    downloadSticker() {
        const dataUrl = this.canvas.toDataURL('image/webp', 0.9);
        const link = document.createElement('a');
        link.href = dataUrl;
        link.download = `sticker_${Date.now()}.webp`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    validatePackName(packName) {
        if (!packName || packName.trim().length === 0) {
            return true; // No pack is valid
        }
        
        packName = packName.trim();
        
        if (packName.length > 64) {
            return false;
        }

        const validPattern = /^[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFFa-zA-Z0-9_]+$/;
        if (!validPattern.test(packName)) {
            return false;
        }

        return true;
    }

    showMessage(message, type) {
        const statusDiv = document.getElementById('statusMessage');
        statusDiv.textContent = message;
        statusDiv.className = `status-message status-${type}`;
        statusDiv.style.display = 'block';

        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.stickerCreator = new StickerCreator();
    
    // Make functions globally available
    window.selectMode = (mode) => window.stickerCreator.selectMode(mode);
    window.selectPosition = (position) => window.stickerCreator.selectPosition(position);
    window.handleImageUpload = (event) => window.stickerCreator.handleImageUpload(event);
    window.previewSticker = () => window.stickerCreator.previewSticker();
    window.createSticker = () => window.stickerCreator.createSticker();
    window.updateDefaultBackground = () => window.stickerCreator.updateDefaultBackground();
    window.showHelp = () => document.getElementById('helpModal').classList.add('show');
    window.closeHelp = () => document.getElementById('helpModal').classList.remove('show');
});