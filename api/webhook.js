// api/webhook.js
export default function handler(req, res) {
  if (req.method === 'POST') {
    // داده‌های ورودی را پردازش کنید
    console.log('Webhook data:', req.body);  // برای مشاهده داده‌های ورودی

    // پاسخ به سرویس دهنده Webhook
    res.status(200).json({ message: 'Webhook received successfully!' });
  } else {
    // اگر درخواست GET یا متد دیگری باشه
    res.status(405).json({ message: 'Method Not Allowed' });
  }
}