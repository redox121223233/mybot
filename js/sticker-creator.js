// Enhanced Sticker Creator JavaScript - Final Version
class StickerCreator {
    constructor() {
        this.canvas = document.createElement('canvas');
        this.canvas.width = 512;
        this.canvas.height = 512;
        this.ctx = this.canvas.getContext('2d');

        this.tg = window.Telegram.WebApp;
        this.userId = this.tg.initDataUnsafe?.user?.id;

        this.currentMode = 'simple';
        this.userQuota = 3;
        this.selectedPosition = 'center';
        this.uploadedImage = null;

        this.loadUserQuota();
        this.setupEventListeners();
        this.tg.ready();
    }

    setupEventListeners() {
        document.getElementById('stickerForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitSticker();
        });

        // Other event listeners
        const fontSlider = document.getElementById('fontSize');
        fontSlider.addEventListener('input', (e) => {
            document.getElementById('fontSizeValue').textContent = e.target.value;
        });

        const colorPicker = document.getElementById('textColor');
        colorPicker.addEventListener('input', (e) => {
            this.updateColorPreview(e.target.value);
        });

        this.setupDragAndDrop();
    }

    setupDragAndDrop() {
        const uploadArea = document.querySelector('.file-upload-label');
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.background = '#f0f0f0';
        });
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.style.background = 'var(--bg-gray)';
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.background = 'var(--bg-gray)';
            if (e.dataTransfer.files.length > 0) {
                this.handleImageFile(e.dataTransfer.files[0]);
            }
        });
    }

    selectMode(mode) {
        this.currentMode = mode;
        document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`.mode-btn[onclick="selectMode('${mode}')"]`).classList.add('active');
        
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
        document.querySelectorAll('.position-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
    }

    handleImageUpload(event) {
        if (event.target.files.length > 0) {
            this.handleImageFile(event.target.files[0]);
        }
    }

    handleImageFile(file) {
        if (!file.type.startsWith('image/')) {
            this.showMessage('لطفاً فقط تصویر آپلود کنید!', 'error');
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            this.uploadedImage = new Image();
            this.uploadedImage.onload = () => {
                this.updateUploadLabel(file.name);
                this.showMessage('تصویر با موفقیت آپلود شد!', 'success');
            };
            this.uploadedImage.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    updateUploadLabel(filename) {
        document.querySelector('.file-upload-label').innerHTML = `✅ ${filename}`;
    }

    updateColorPreview(color) {
        const preview = document.getElementById('colorPreview');
        preview.style.background = color;
        preview.textContent = color.toUpperCase();
        const rgb = parseInt(color.slice(1), 16);
        const brightness = ((rgb >> 16) & 255) * 0.299 + ((rgb >> 8) & 255) * 0.587 + (rgb & 255) * 0.114;
        preview.style.color = brightness > 128 ? '#000' : '#fff';
    }

    async loadUserQuota() {
        // This should be handled by the backend in a real scenario
    }

    checkQuota() {
        // Backend should handle this
        return true;
    }

    async createStickerCanvas() {
        const text = document.getElementById('stickerText').value;
        const settings = (this.currentMode === 'simple')
            ? { fontSize: 60, color: '#FFFFFF', position: 'center' }
            : {
                fontSize: parseInt(document.getElementById('fontSize').value),
                color: document.getElementById('textColor').value,
                position: this.selectedPosition
            };
        
        this.ctx.clearRect(0, 0, 512, 512);

        if (this.uploadedImage) {
            const img = this.uploadedImage;
            const scale = Math.min(400 / img.width, 400 / img.height);
            const w = img.width * scale;
            const h = img.height * scale;
            this.ctx.drawImage(img, (512 - w) / 2, (512 - h) / 2, w, h);
        }

        this.ctx.font = `bold ${settings.fontSize}px 'Vazirmatn', sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        
        // Simple positioning for demo
        const pos = { x: 256, y: 256 };
        
        this.ctx.strokeStyle = '#000';
        this.ctx.lineWidth = 4;
        this.ctx.strokeText(text, pos.x, pos.y);
        this.ctx.fillStyle = settings.color;
        this.ctx.fillText(text, pos.x, pos.y);
    }

    async previewSticker() {
        await this.createStickerCanvas();
        const previewImage = document.getElementById('previewImage');
        previewImage.src = this.canvas.toDataURL('image/webp');
        previewImage.style.display = 'block';
        document.getElementById('previewPlaceholder').style.display = 'none';
        this.showMessage('پیش‌نمایش آماده شد!', 'success');
    }

    async submitSticker() {
        const packName = document.getElementById('packName').value.trim();
        if (!packName) {
            this.showMessage('نام پک استیکر اجباری است!', 'error');
            return;
        }

        this.showMessage('در حال ساخت و ارسال استیکر...', 'warning');
        document.getElementById('createBtn').disabled = true;

        await this.createStickerCanvas();
        const stickerData = this.canvas.toDataURL('image/webp');
        
        try {
            const response = await fetch('/api/add-sticker-to-pack', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    pack_name: packName,
                    sticker: stickerData,
                }),
            });

            if (response.ok) {
                this.showMessage('استیکر با موفقیت به پک شما اضافه شد! پیام تایید در ربات ارسال شد.', 'success');
            } else {
                const error = await response.json();
                this.showMessage(`خطا: ${error.error}`, 'error');
            }
        } catch (error) {
            this.showMessage('خطای ارتباط با سرور!', 'error');
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
});

// Make functions globally accessible for inline HTML calls
function selectMode(mode) { window.creator.selectMode(mode); }
function selectPosition(position) { window.creator.selectPosition(position); }
function handleImageUpload(event) { window.creator.handleImageUpload(event); }
function previewSticker() { window.creator.previewSticker(); }
