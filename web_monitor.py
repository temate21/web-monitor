import requests
import time
import ssl
import socket
from datetime import datetime
from flask import Flask
import os
import json
from urllib.parse import urlparse
import threading

app = Flask(__name__)

# =====================================================
# CONFIGURACIÓN - EDITA ESTO CON TUS DATOS
# =====================================================

MONITORED_URLS = [ "https://natclinic.com" ]

# ===== TELEGRAM (GRATIS) =====
TELEGRAM_BOT_TOKEN = "8953531700:AAHDK6cFx1LE5M8O8B5LfGgfVuj2L8QoTIk"  # Obten en @BotFather
TELEGRAM_CHAT_ID = "8735137518"  # Tu ID de chat


# =====================================================
# FUNCIONES DE ALERTAS
# =====================================================

def send_telegram(message):
    """Envía alerta a Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, json=data, timeout=5)
        print(f"✅ Telegram enviado")
    except Exception as e:
        print(f"❌ Error Telegram: {e}")

def send_discord(message):
    """Envía alerta a Discord"""
    try:
        data = {"content": message}
        requests.post(DISCORD_WEBHOOK, json=data, timeout=5)
        print(f"✅ Discord enviado")
    except Exception as e:
        print(f"❌ Error Discord: {e}")

def send_whatsapp(message):
    """Envía alerta a WhatsApp vía Twilio"""
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=TWILIO_PHONE,
            to=RECIPIENT_PHONE
        )
        print(f"✅ WhatsApp enviado")
    except Exception as e:
        print(f"❌ Error WhatsApp: {e}")

def send_email(subject, body):
    """Envía alerta por Email"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email enviado")
    except Exception as e:
        print(f"❌ Error Email: {e}")

def send_all_alerts(title, message):
    """Envía alertas a todos los canales configurados"""
    print(f"\n🚨 ALERTA: {title}")
    
    if TELEGRAM_BOT_TOKEN != "TU_TOKEN_AQUI":
        send_telegram(f"🚨 <b>{title}</b>\n\n{message}")
    
    if DISCORD_WEBHOOK != "https://discordapp.com/api/webhooks/TU_WEBHOOK_AQUI":
        send_discord(f"🚨 **{title}**\n\n{message}")
    
    if TWILIO_ACCOUNT_SID != "TU_ACCOUNT_SID":
        send_whatsapp(f"🚨 {title}\n\n{message}")
    
    if EMAIL_SENDER != "tu_email@gmail.com":
        send_email(f"🚨 {title}", message)

# =====================================================
# FUNCIONES DE MONITOREO
# =====================================================

def check_ssl_certificate(url):
    """Verifica la validez del certificado SSL"""
    try:
        domain = urlparse(url).netloc
        context = ssl.create_default_context()
        
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                
                # Extrae la fecha de expiración
                import ssl
                not_after = cert.get('notAfter')
                return True, "SSL válido"
    except Exception as e:
        return False, f"Error SSL: {str(e)}"

def check_website(url):
    """Monitorea una página web"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10, allow_redirects=True)
        response_time = time.time() - start_time
        
        result = {
            "url": url,
            "status": "✅ ONLINE",
            "status_code": response.status_code,
            "response_time": f"{response_time:.2f}s",
            "timestamp": timestamp
        }
        
        # Detectar errores 500
        if response.status_code >= 500:
            result["status"] = "⚠️ ERROR 500"
            alert_msg = f"URL: {url}\nCódigo: {response.status_code}\nTiempo: {timestamp}"
            send_all_alerts("❌ ERROR 500 DETECTADO", alert_msg)
        
        # Verificar SSL
        ssl_valid, ssl_msg = check_ssl_certificate(url)
        result["ssl"] = ssl_msg
        
        return result
        
    except requests.exceptions.Timeout:
        result = {
            "url": url,
            "status": "❌ CAÍDA (TIMEOUT)",
            "error": "Tiempo de espera agotado",
            "timestamp": timestamp
        }
        alert_msg = f"URL: {url}\nLa página NO responde (timeout)\nTiempo: {timestamp}"
        send_all_alerts("⚠️ PÁGINA CAÍDA", alert_msg)
        return result
        
    except requests.exceptions.ConnectionError:
        result = {
            "url": url,
            "status": "❌ CAÍDA (SIN CONEXIÓN)",
            "error": "No se pudo conectar",
            "timestamp": timestamp
        }
        alert_msg = f"URL: {url}\nNo hay conexión a la página\nTiempo: {timestamp}"
        send_all_alerts("⚠️ PÁGINA CAÍDA", alert_msg)
        return result
        
    except Exception as e:
        result = {
            "url": url,
            "status": "❌ ERROR",
            "error": str(e),
            "timestamp": timestamp
        }
        return result

# =====================================================
# MONITOREO CONTINUO
# =====================================================

def monitor_loop():
    """Ejecuta el monitoreo cada 5 minutos"""
    while True:
        print(f"\n{'='*60}")
        print(f"🔍 MONITOREO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        results = []
        for url in MONITORED_URLS:
            result = check_website(url)
            results.append(result)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Espera 5 minutos antes de la siguiente verificación
        print(f"\n⏳ Próxima verificación en 5 minutos...")
        time.sleep(300)  # 300 segundos = 5 minutos

# =====================================================
# RUTAS WEB (para que Render sepa que está activo)
# =====================================================

@app.route('/')
def health():
    """Health check para Render"""
    return {
        "status": "running",
        "urls_monitored": len(MONITORED_URLS),
        "timestamp": datetime.now().isoformat()
    }

@app.route('/status')
def status():
    """Endpoint de status"""
    results = []
    for url in MONITORED_URLS:
        results.append(check_website(url))
    return {"results": results}

# =====================================================
# MAIN
# =====================================================

if __name__ == '__main__':
    print("🚀 Iniciando Monitor de Páginas Web...")
    print(f"📊 Monitoreando {len(MONITORED_URLS)} URLs")
    
    # Inicia el monitoreo en un hilo separado
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    
    # Inicia el servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
