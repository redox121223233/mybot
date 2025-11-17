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
        trackAction('create_sticker_canvas_start', {
            hasImage: !!this.uploadedImage,
            imageWidth: this.uploadedImage?.width,
            imageHeight: this.uploadedImage?.height
        });
        
        this.ctx.clearRect(0, 0, 512, 512);
        
        // Add default background if no image
        if (!this.uploadedImage) {
            this.ctx.fillStyle = '#f0f0f0';
            this.ctx.fillRect(0, 0, 512, 512);
            console.log('✅ Default background applied');
        } else {
            const img = this.uploadedImage;
            const scale = Math.min(400 / img.width, 400 / img.height);
            this.ctx.drawImage(img, (512 - img.width * scale) / 2, (512 - img.height * scale) / 2, img.width * scale, img.height * scale);
            console.log('✅ Image drawn with scale:', scale);
        }
        
        const text = document.getElementById('stickerText').value;
        const fontSize = document.getElementById('fontSize').value;
        const color = document.getElementById('textColor').value;
        
        trackAction('text_rendering', {
            textLength: text?.length || 0,
            text: text || 'empty',
            fontSize: fontSize,
            color: color
        });
        
        // Only draw text if it's not empty
        if (!text || text.trim() === '') {
            console.log('⚠️ No text to render - skipping text drawing');
            return;
        }

        // Use system fonts for better compatibility
        this.ctx.font = `bold ${fontSize}px 'Arial Black', 'Arial Bold', Arial, sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        
        // Add shadow for better visibility
        this.ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
        this.ctx.shadowBlur = 6;
        this.ctx.shadowOffsetX = 3;
        this.ctx.shadowOffsetY = 3;
        
        console.log('🎨 Drawing text:', text);
        
        // Add shadow for better visibility
        this.ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
        this.ctx.shadowBlur = 6;
        this.ctx.shadowOffsetX = 3;
        this.ctx.shadowOffsetY = 3;
        
        // Draw stroke outline first
        this.ctx.strokeStyle = '#000000';
        this.ctx.lineWidth = 4;
        this.ctx.strokeText(text, 256, 256);
        console.log('✅ Text stroke drawn');
        
        // Draw fill text
        this.ctx.fillStyle = color;
        this.ctx.fillText(text, 256, 256);
        console.log('✅ Text fill drawn with color:', color);
        
        // Reset shadow
        this.ctx.shadowColor = 'transparent';
        this.ctx.shadowBlur = 0;
        this.ctx.shadowOffsetX = 0;
        this.ctx.shadowOffsetY = 0;
    }

    async previewSticker() {
        trackAction('preview_button_clicked');
        console.log('🔍 Preview button clicked');
        
        const text = document.getElementById('stickerText').value;
        const hasImage = !!this.uploadedImage;
        
        console.log('📊 Preview data:', {
            hasImage: hasImage,
            textLength: text?.length || 0,
            text: text || 'empty'
        });
        
        if (!hasImage && !text) {
            trackAction('preview_failed_no_data');
            this.showMessage('لطفاً تصویر یا متنی برای پیش‌نمایش وارد کنید.', 'error');
            console.error('❌ No data for preview');
            return;
        }
        
        try {
            console.log('🎨 Creating sticker canvas...');
            await this.createStickerCanvas();
            
            console.log('📸 Converting canvas to data URL...');
            const dataUrl = this.canvas.toDataURL('image/webp');
            console.log('✅ Canvas converted, data URL length:', dataUrl.length);
            
            const previewImage = document.getElementById('previewImage');
            previewImage.src = dataUrl;
            previewImage.style.display = 'block';
            document.getElementById('previewPlaceholder').style.display = 'none';
            
            this.showMessage('پیش‌نمایش آماده شد!', 'success');
            trackAction('preview_success');
            console.log('✅ Preview completed successfully');
            
        } catch (error) {
            trackError(error, { action: 'preview' });
            this.showMessage('خطا در ساختن پیش‌نمایش', 'error');
            console.error('❌ Preview error:', error);
        }
    }

    async submitSticker() {
        trackAction('submit_button_clicked');
        console.log('🚀 Submit button clicked');
        
        const packName = document.getElementById('packName').value.trim();
        
        if (!packName) {
            trackAction('submit_failed_no_pack_name');
            this.showMessage('نام پک استیکر اجباری است!', 'error');
            console.error('❌ No pack name provided');
            return;
        }

        trackAction('submit_processing', { packName: packName });
        this.showMessage('در حال ارسال استیکر...', 'warning');
        document.getElementById('createBtn').disabled = true;

        try {
            console.log('🎨 Creating sticker canvas for submission...');
            await this.createStickerCanvas();
            
            console.log('📸 Converting canvas to WebP...');
            const stickerData = this.canvas.toDataURL('image/webp');
            console.log('✅ Sticker data created, size:', Math.round(stickerData.length / 1024), 'KB');
            
            trackAction('sending_to_server', { 
                packName: packName,
                dataSize: stickerData.length 
            });
            
            console.log('📡 Sending to server...');
            const response = await fetch('/api/add-sticker-to-pack', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    user_id: this.userId, 
                    pack_name: packName, 
                    sticker: stickerData 
                }),
            });
            
            console.log('📊 Server response status:', response.status);
            
            if (response.ok) {
                const result = await response.json();
                console.log('✅ Server response:', result);
                
                if (result.success) {
                    trackAction('submit_success', { 
                        packName: packName,
                        packUrl: result.pack_url 
                    });
                    
                    this.showMessage('✅ استیکر با موفقیت ساخته شد! لینک پک در تلگرام برای شما ارسال شد.', 'success');
                    console.log('🎉 Sticker pack created successfully!');
                    
                    // Don't close immediately, let user see the message
                    setTimeout(() => {
                        console.log('📱 Closing Telegram WebApp...');
                        this.tg.close();
                    }, 2000);
                } else {
                    trackAction('submit_failed_server_error', { error: result.error });
                    this.showMessage(`خطا: ${result.error}`, 'error');
                    console.error('❌ Server returned error:', result.error);
                }
            } else {
                const error = await response.json();
                trackAction('submit_failed_http_error', { 
                    status: response.status, 
                    error: error.error 
                });
                this.showMessage(`خطا: ${error.error}`, 'error');
                console.error('❌ HTTP error:', response.status, error.error);
            }
        } catch (error) {
            trackError(error, { action: 'submit', packName: packName });
            this.showMessage('خطای ارتباط با سرور!', 'error');
            console.error('❌ Network error:', error);
        } finally {
            document.getElementById('createBtn').disabled = false;
            console.log('🔄 Submit process completed');
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
