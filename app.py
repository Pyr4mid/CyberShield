from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random
import time

app = Flask(__name__)
CORS(app)  # للسماح بالطلبات من الواجهة

# ============================================================
# إعدادات Tor (SOCKS5)
# ============================================================
TOR_PROXY = {
    'http': 'socks5://127.0.0.1:9050',
    'https': 'socks5://127.0.0.1:9050'
}

# ============================================================
# دالة إرسال الطلب عبر Tor
# ============================================================
def send_via_tor(url, mode='get', timeout=10):
    """
    إرسال طلب HTTP عبر Tor (SOCKS5)
    - url: الرابط المطلوب
    - mode: طريقة الطلب (get, post, slow)
    - timeout: مهلة الطلب بالثواني
    """
    try:
        session = requests.Session()
        session.proxies.update(TOR_PROXY)

        # User-Agent عشوائي
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        session.headers.update({
            'User-Agent': random.choice(user_agents),
            'Accept': '*/*',
            'Accept-Language': 'ar,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1',
            'Connection': 'keep-alive'
        })

        # تحضير الرابط مع timestamp عشوائي
        if '?' not in url:
            url += f"?_={int(time.time()*1000)}&r={random.randint(1,999999)}"
        else:
            url += f"&_={int(time.time()*1000)}&r={random.randint(1,999999)}"

        # تنفيذ الطلب حسب الوضع
        if mode == 'post':
            response = session.post(url, json={'x': random.random()}, timeout=timeout)
        elif mode == 'slow':
            session.headers['Connection'] = 'keep-alive'
            session.headers['Keep-Alive'] = 'timeout=9999, max=1000'
            response = session.get(url, timeout=timeout)
        else:
            response = session.get(url, timeout=timeout)

        # نجاح إذا كان الـ status code في القائمة
        return response.status_code in [200, 403, 404, 500, 502, 503]

    except Exception as e:
        print(f"[TOR ERROR] {e}")
        return False

# ============================================================
# Routes API
# ============================================================

@app.route('/api/send-request', methods=['POST'])
def send_request():
    """
    يستقبل طلب من الواجهة لارسال طلب HTTP عبر Tor
    """
    data = request.json
    url = data.get('url')
    mode = data.get('mode', 'get')

    if not url:
        return jsonify({'success': False, 'error': 'URL مطلوب'}), 400

    try:
        result = send_via_tor(url, mode)
        return jsonify({'success': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-tor', methods=['GET'])
def check_tor():
    """
    فحص الاتصال بـ Tor عن طريق محاولة الاتصال بالمنفذ 9050
    """
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(('127.0.0.1', 9050))
        sock.close()
        return jsonify({'connected': True, 'message': 'Tor متصل'})
    except:
        return jsonify({'connected': False, 'message': 'Tor غير متصل'})

@app.route('/api/status', methods=['GET'])
def status():
    """
    حالة الخادم
    """
    return jsonify({'status': 'online', 'service': 'CyberShield Backend'})

# ============================================================
# تشغيل الخادم
# ============================================================
if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════╗
    ║   🛡️ CyberShield Backend - Tor Proxy        ║
    ║   يعمل عبر Tor (SOCKS5)                     ║
    ║   http://localhost:5000                     ║
    ╚══════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=5000, debug=True)