import json
import time
import os

def handler(event, context):
    """Main index handler for Vercel"""
    try:
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html',
                'Access-Control-Allow-Origin': '*'
            },
            'body': '''
            <!DOCTYPE html>
            <html lang="fa" dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>ربات استیکرساز تلگرام</title>
                <style>
                    body {
                        font-family: 'Tahoma', sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 20px;
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }
                    .container {
                        background: white;
                        border-radius: 15px;
                        padding: 40px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                        text-align: center;
                        max-width: 500px;
                        width: 100%;
                    }
                    .status {
                        font-size: 48px;
                        margin-bottom: 20px;
                    }
                    h1 {
                        color: #333;
                        margin-bottom: 10px;
                    }
                    .subtitle {
                        color: #666;
                        margin-bottom: 30px;
                    }
                    .info {
                        background: #f8f9fa;
                        border-radius: 10px;
                        padding: 20px;
                        margin: 20px 0;
                        text-align: right;
                    }
                    .info h3 {
                        margin-top: 0;
                        color: #495057;
                    }
                    .info p {
                        margin: 10px 0;
                        color: #6c757d;
                    }
                    .links {
                        margin-top: 30px;
                    }
                    .links a {
                        display: inline-block;
                        margin: 10px;
                        padding: 10px 20px;
                        background: #007bff;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        transition: background 0.3s;
                    }
                    .links a:hover {
                        background: #0056b3;
                    }
                    .footer {
                        margin-top: 30px;
                        color: #999;
                        font-size: 14px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="status">✅</div>
                    <h1>ربات استیکرساز تلگرام</h1>
                    <p class="subtitle">ربات با موفقیت روی Vercel مستقر شده است!</p>
                    
                    <div class="info">
                        <h3>📋 اطلاعات سیستم</h3>
                        <p><strong>وضعیت:</strong> فعال و آماده</p>
                        <p><strong>پلتفرم:</strong> Vercel Serverless</p>
                        <p><strong>زمان:</strong> ''' + time.strftime("%Y-%m-%d %H:%M:%S") + '''</p>
                        <p><strong>ربات تنظیم شده:</strong> ''' + ('بله' if os.environ.get('BOT_TOKEN') else 'خیر') + '''</p>
                    </div>
                    
                    <div class="info">
                        <h3>🚀 مراحل بعدی</h3>
                        <p>1. webhook تلگرام را تنظیم کنید</p>
                        <p>2. متغیرهای محیطی را بررسی کنید</p>
                        <p>3. ربات را در تلگرام تست کنید</p>
                    </div>
                    
                    <div class="links">
                        <a href="/api/health">بررسی سلامت</a>
                        <a href="https://github.com/your-repo" target="_blank">کد منبع</a>
                    </div>
                    
                    <div class="footer">
                        <p>ساخته شده با ❤️ برای Vercel</p>
                    </div>
                </div>
            </body>
            </html>
            '''
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'خطا در بارگذاری صفحه اصلی'
            })
        }