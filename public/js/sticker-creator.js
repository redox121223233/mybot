// Final, Overhauled Sticker Creator JavaScript
class StickerCreator {
    constructor() {
        this.tg = window.Telegram.WebApp;
        this.userId = this.tg.initDataUnsafe?.user?.id;

        this.canvas = document.createElement('canvas');
        this.canvas.width = 512;
        this.canvas.height = 512;
        this.ctx = this.canvas.getContext('2d');

        this.uploadedImage = null;

        this.setupEventListeners();
        this.tg.ready();
        this.logToServer('info', 'Mini App Initialized');
    }

    async logToServer(level, message) {
        try {
            await fetch('/api/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ level, message: `[UserID: ${this.userId}] ${message}` }),
            });
        } catch (error) {
            console.error("Failed to log to server:", error);
        }
    }

    setupEventListeners() {
        document.getElementById('stickerForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitSticker();
        });

        document.getElementById('previewBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.previewSticker();
        });

        document.getElementById('imageUpload').addEventListener('change', (e) => {
            this.handleImageUpload(e);
        });

        // Other listeners
        document.getElementById('fontSize').addEventListener('input', (e) => {
            document.getElementById('fontSizeValue').textContent = e.target.value;
        });

        document.getElementById('textColor').addEventListener('input', (e) => {
            this.updateColorPreview(e.target.value);
        });
    }

    selectMode(mode) {
        // Simplified for now
    }

    selectPosition(position) {
        // Simplified for now
    }

    handleImageUpload(event) {
        if (event.target.files && event.target.files[0]) {
            this.handleImageFile(event.target.files[0]);
        }
    }

    handleImageFile(file) {
        if (!file.type.startsWith('image/')) {
            this.showMessage('لطفاً فقط تصویر آپلود کنید!', 'error');
            this.logToServer('error', `Invalid file type: ${file.type}`);
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            this.uploadedImage = new Image();
            this.uploadedImage.onload = () => {
                this.updateUploadLabel(file.name);
                this.showMessage('تصویر با موفقیت آپلود شد!', 'success');
                this.logToServer('info', `Image "${file.name}" uploaded.`);
            };
            this.uploadedImage.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    updateUploadLabel(filename) {
        document.querySelector('.file-upload-label span').textContent = `✅ ${filename}`;
    }

    updateColorPreview(color) {
        const preview = document.getElementById('colorPreview');
        preview.style.background = color;
        preview.textContent = color.toUpperCase();
        const rgb = parseInt(color.slice(1), 16);
        const brightness = ((rgb >> 16) & 0xFF) * 0.299 + ((rgb >> 8) & 0xFF) * 0.587 + (rgb & 0xFF) * 0.114;
        preview.style.color = brightness > 128 ? '#000' : '#fff';
    }

    async createStickerCanvas() {
        this.ctx.clearRect(0, 0, 512, 512);
        if (this.uploadedImage) {
            const img = this.uploadedImage;
            const scale = Math.min(400 / img.width, 400 / img.height);
            this.ctx.drawImage(img, (512 - img.width * scale) / 2, (512 - img.height * scale) / 2, img.width * scale, img.height * scale);
        }
        const text = document.getElementById('stickerText').value;
        const fontSize = document.getElementById('fontSize').value;
        const color = document.getElementById('textColor').value;

        this.ctx.font = `bold ${fontSize}px 'Vazirmatn', sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.strokeStyle = '#000';
        this.ctx.lineWidth = 4;
        this.ctx.strokeText(text, 256, 256);
        this.ctx.fillStyle = color;
        this.ctx.fillText(text, 256, 256);
    }

    async previewSticker() {
        this.logToServer('info', 'Preview button clicked');
        if (!this.uploadedImage && !document.getElementById('stickerText').value) {
            this.showMessage('لطفاً تصویر یا متنی برای پیش‌نمایش وارد کنید.', 'error');
            return;
        }
        await this.createStickerCanvas();
        document.getElementById('previewImage').src = this.canvas.toDataURL('image/webp');
        document.getElementById('previewImage').style.display = 'block';
        document.getElementById('previewPlaceholder').style.display = 'none';
        this.showMessage('پیش‌نمایش آماده شد!', 'success');
    }

    async submitSticker() {
        this.logToServer('info', 'Submit button clicked');
        const packName = document.getElementById('packName').value.trim();
        if (!packName) {
            this.showMessage('نام پک استیکر اجباری است!', 'error');
            this.logToServer('error', 'Submission failed: Pack name is required.');
            return;
        }

        this.showMessage('در حال ارسال استیکر...', 'warning');
        document.getElementById('createBtn').disabled = true;

        await this.createStickerCanvas();
        const stickerData = this.canvas.toDataURL('image/webp');

        try {
            const response = await fetch('/api/add-sticker-to-pack', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.userId, pack_name: packName, sticker: stickerData }),
            });
            if (response.ok) {
                this.showMessage('استیکر با موفقیت اضافه شد! پیام در تلگرام ارسال شد.', 'success');
                this.logToServer('info', `Sticker added to pack "${packName}".`);
                this.tg.close();
            } else {
                const error = await response.json();
                this.showMessage(`خطا: ${error.error}`, 'error');
                this.logToServer('error', `Server error: ${error.error}`);
            }
        } catch (error) {
            this.showMessage('خطای ارتباط با سرور!', 'error');
            this.logToServer('error', `Network error: ${error.message}`);
        } finally {
            document.getElementById('createBtn').disabled = false;
        }
    }

    showMessage(message, type) {
        const statusDiv = document.getElementById('statusMessage');
        statusDiv.textContent = message;
        statusDiv.className = `status-message status-${type}`;
        statusDiv.style.display = 'block';
        setTimeout(() => statusDiv.style.display = 'none', 5000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.creator = new StickerCreator();
    // Make functions globally available
    window.selectMode = (mode) => window.creator.selectMode(mode);
    window.selectPosition = (position) => window.creator.selectPosition(position);
    window.handleImageUpload = (event) => window.creator.handleImageUpload(event);
    window.previewSticker = () => window.creator.previewSticker();
});
