import os

def create_file(path, content):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Creado: {path}")

def setup_project():
    print("🚀 Iniciando instalación de Property Finder...")
    
    # Config.py
    create_file('config.py', '''import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

CRITERIOS = {
    "presupuesto": {"min": 200000, "max": 400000, "moneda": "USD", "peso": 0.20},
    "ubicacion": {"zonas": ["saavedra", "coghlan", "nuñez", "nunez", "vicente lopez", "vicente lópez"], "peso": 0.25},
    "tipo": {"valores": ["casa", "house", "chalet"], "peso": 0.10},
    "habitaciones": {"min": 3, "peso": 0.10},
    "baños": {"min": 2, "peso": 0.08},
    "m2_cubiertos": {"min": 180, "peso": 0.12},
    "m2_descubiertos": {"min": 100, "peso": 0.08},
    "amenities": {"requeridos": ["garaje", "cochera", "piscina", "pileta", "jardin", "jardín"], "peso_garaje": 0.02, "peso_piscina": 0.03, "peso_jardin": 0.02}
}

SCRAPING_CONFIG = {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "timeout": 30, "max_retries": 3, "delay_between_requests": 2}
MATCH_THRESHOLD = 75
DB_PATH = "properties.db"
''')
    
    # Database.py
    create_file('database.py', '''import sqlite3
from datetime import datetime
import json

class PropertyDatabase:
    def __init__(self, db_path="properties.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS properties (id INTEGER PRIMARY KEY AUTOINCREMENT, external_id TEXT UNIQUE, portal TEXT, titulo TEXT, precio REAL, moneda TEXT, ubicacion TEXT, tipo TEXT, habitaciones INTEGER, banos INTEGER, m2_cubiertos REAL, m2_descubiertos REAL, amenities TEXT, descripcion TEXT, url TEXT, imagenes TEXT, match_score REAL, fecha_encontrada TIMESTAMP, ultima_actualizacion TIMESTAMP, notificado BOOLEAN DEFAULT 0)""")
        conn.commit()
        conn.close()
    
    def save_property(self, property_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""INSERT INTO properties (external_id, portal, titulo, precio, moneda, ubicacion, tipo, habitaciones, banos, m2_cubiertos, m2_descubiertos, amenities, descripcion, url, imagenes, match_score, fecha_encontrada, ultima_actualizacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (property_data['external_id'], property_data['portal'], property_data['titulo'], property_data['precio'], property_data['moneda'], property_data['ubicacion'], property_data['tipo'], property_data['habitaciones'], property_data['banos'], property_data['m2_cubiertos'], property_data['m2_descubiertos'], json.dumps(property_data['amenities']), property_data['descripcion'], property_data['url'], json.dumps(property_data['imagenes']), property_data['match_score'], datetime.now(), datetime.now()))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            cursor.execute("""UPDATE properties SET precio=?, match_score=?, ultima_actualizacion=? WHERE external_id=?""", (property_data['precio'], property_data['match_score'], datetime.now(), property_data['external_id']))
            conn.commit()
            return False
        finally:
            conn.close()
    
    def mark_as_notified(self, external_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE properties SET notificado=1 WHERE external_id=?', (external_id,))
        conn.commit()
        conn.close()
    
    def get_unnotified_matches(self, threshold=75):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM properties WHERE match_score >= ? AND notificado = 0 ORDER BY match_score DESC""", (threshold,))
        rows = cursor.fetchall()
        conn.close()
        properties = []
        for row in rows:
            properties.append({'id': row[0], 'external_id': row[1], 'portal': row[2], 'titulo': row[3], 'precio': row[4], 'moneda': row[5], 'ubicacion': row[6], 'tipo': row[7], 'habitaciones': row[8], 'banos': row[9], 'm2_cubiertos': row[10], 'm2_descubiertos': row[11], 'amenities': json.loads(row[12]) if row[12] else [], 'descripcion': row[13], 'url': row[14], 'imagenes': json.loads(row[15]) if row[15] else [], 'match_score': row[16]})
        return properties
''')
    
    # Matcher.py
    create_file('matcher.py', '''from config import CRITERIOS

class PropertyMatcher:
    def __init__(self, criterios=CRITERIOS):
        self.criterios = criterios
    
    def calculate_match(self, propiedad):
        score = 0
        max_score = 0
        precio_peso = self.criterios['presupuesto']['peso'] * 100
        max_score += precio_peso
        if self.criterios['presupuesto']['min'] <= propiedad.get('precio', 0) <= self.criterios['presupuesto']['max']:
            score += precio_peso
        ubicacion_peso = self.criterios['ubicacion']['peso'] * 100
        max_score += ubicacion_peso
        ubicacion = propiedad.get('ubicacion', '').lower()
        for zona in self.criterios['ubicacion']['zonas']:
            if zona.lower() in ubicacion:
                score += ubicacion_peso
                break
        tipo_peso = self.criterios['tipo']['peso'] * 100
        max_score += tipo_peso
        tipo = propiedad.get('tipo', '').lower()
        for tipo_valido in self.criterios['tipo']['valores']:
            if tipo_valido in tipo:
                score += tipo_peso
                break
        hab_peso = self.criterios['habitaciones']['peso'] * 100
        max_score += hab_peso
        if propiedad.get('habitaciones', 0) >= self.criterios['habitaciones']['min']:
            score += hab_peso
        banos_peso = self.criterios['baños']['peso'] * 100
        max_score += banos_peso
        if propiedad.get('banos', 0) >= self.criterios['baños']['min']:
            score += banos_peso
        m2c_peso = self.criterios['m2_cubiertos']['peso'] * 100
        max_score += m2c_peso
        if propiedad.get('m2_cubiertos', 0) >= self.criterios['m2_cubiertos']['min']:
            score += m2c_peso
        m2d_peso = self.criterios['m2_descubiertos']['peso'] * 100
        max_score += m2d_peso
        if propiedad.get('m2_descubiertos', 0) >= self.criterios['m2_descubiertos']['min']:
            score += m2d_peso
        amenities = ' '.join(propiedad.get('amenities', [])).lower()
        descripcion = propiedad.get('descripcion', '').lower()
        texto_completo = f"{amenities} {descripcion}"
        if any(word in texto_completo for word in ['garaje', 'cochera']):
            score += self.criterios['amenities']['peso_garaje'] * 100
        max_score += self.criterios['amenities']['peso_garaje'] * 100
        if any(word in texto_completo for word in ['piscina', 'pileta']):
            score += self.criterios['amenities']['peso_piscina'] * 100
        max_score += self.criterios['amenities']['peso_piscina'] * 100
        if any(word in texto_completo for word in ['jardin', 'jardín', 'parque']):
            score += self.criterios['amenities']['peso_jardin'] * 100
        max_score += self.criterios['amenities']['peso_jardin'] * 100
        match_percentage = (score / max_score * 100) if max_score > 0 else 0
        return round(match_percentage, 2)
''')
    
    # Notifier.py
    create_file('notifier.py', '''import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramNotifier:
    def __init__(self, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_property_alert(self, propiedad):
        mensaje = self._format_property_message(propiedad)
        url = f"{self.base_url}/sendMessage"
        data = {"chat_id": self.chat_id, "text": mensaje, "parse_mode": "HTML", "disable_web_page_preview": False}
        try:
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Error enviando notificación: {e}")
            return False
    
    def _format_property_message(self, prop):
        match_emoji = "🔥" if prop['match_score'] >= 90 else "✨" if prop['match_score'] >= 80 else "⭐"
        mensaje = f"""
{match_emoji} <b>NUEVA PROPIEDAD - {prop['match_score']}% MATCH</b>

🏠 <b>{prop['titulo']}</b>

💰 <b>Precio:</b> {prop['moneda']} {prop['precio']:,.0f}
📍 <b>Ubicación:</b> {prop['ubicacion']}
🏷️ <b>Portal:</b> {prop['portal']}

📊 <b>Características:</b>
   • Habitaciones: {prop['habitaciones']}
   • Baños: {prop['banos']}
   • M² Cubiertos: {prop['m2_cubiertos']}
   • M² Descubiertos: {prop['m2_descubiertos']}

🎯 <b>Amenities:</b> {', '.join(prop['amenities']) if prop['amenities'] else 'No especificados'}

🔗 <a href="{prop['url']}">VER PROPIEDAD</a>
        """.strip()
        return mensaje
''')
    
    # Scrapers
    os.makedirs('scrapers', exist_ok=True)
    create_file('scrapers/__init__.py', '')
    create_file('scrapers/zonaprop.py', '''import requests
from bs4 import BeautifulSoup
import time
import re

class ZonaPropScraper:
    def __init__(self):
        self.base_url = "https://www.zonaprop.com.ar"
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    def search(self):
        properties = []
        search_urls = [f"{self.base_url}/casas-venta-saavedra.html", f"{self.base_url}/casas-venta-coghlan.html", f"{self.base_url}/casas-venta-nunez.html", f"{self.base_url}/casas-venta-vicente-lopez.html"]
        for url in search_urls:
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                if response.status_code == 200:
                    properties.extend(self._parse_listings(response.text, url))
                time.sleep(2)
            except Exception as e:
                print(f"Error scraping {url}: {e}")
        return properties
    
    def _parse_listings(self, html, search_url):
        soup = BeautifulSoup(html, 'html.parser')
        properties = []
        listings = soup.find_all('div', {'data-qa': 'posting PROPERTY'})
        if not listings:
            listings = soup.find_all('div', class_=re.compile('CardContainer'))
        for listing in listings[:10]:
            try:
                prop = self._parse_property(listing)
                if prop:
                    properties.append(prop)
            except Exception as e:
                continue
        return properties
    
    def _parse_property(self, listing):
        try:
            external_id = listing.get('data-id', listing.get('id', f"zp_{hash(str(listing)[:50])}"))
            title_elem = listing.find('h2') or listing.find('a')
            titulo = title_elem.text.strip() if title_elem else "Sin título"
            link_elem = listing.find('a', href=True)
            url = link_elem.get('href', '') if link_elem else ''
            if url and not url.startswith('http'):
                url = self.base_url + url
            price_elem = listing.find('div', {'data-qa': 'POSTING_CARD_PRICE'})
            precio = 0
            moneda = 'USD'
            if price_elem:
                price_text = price_elem.text.strip()
                numbers = re.findall(r'[\\d\\.]+', price_text.replace('.', '').replace(',', ''))
                precio = float(numbers[0]) if numbers else 0
                moneda = 'USD' if 'USD' in price_text or 'U$S' in price_text else 'ARS'
            ubicacion_elem = listing.find('div', {'data-qa': 'POSTING_CARD_LOCATION'})
            ubicacion = ubicacion_elem.text.strip() if ubicacion_elem else "No especificada"
            features = listing.find_all('span', {'data-qa': re.compile('POSTING_CARD_FEATURES')})
            habitaciones = 0
            banos = 0
            m2_cubiertos = 0
            for feature in features:
                text = feature.text.lower()
                if 'dorm' in text or 'hab' in text:
                    num = re.search(r'\\d+', text)
                    habitaciones = int(num.group()) if num else 0
                elif 'baño' in text:
                    num = re.search(r'\\d+', text)
                    banos = int(num.group()) if num else 0
                elif 'm²' in text or 'm2' in text:
                    num = re.search(r'\\d+', text)
                    m2_val = float(num.group()) if num else 0
                    if m2_cubiertos == 0:
                        m2_cubiertos = m2_val
            desc_elem = listing.find('div', class_=re.compile('description'))
            descripcion = desc_elem.text.strip() if desc_elem else titulo
            amenities = []
            texto_completo = (titulo + " " + descripcion).lower()
            if any(word in texto_completo for word in ['garaje', 'cochera']):
                amenities.append('garaje')
            if any(word in texto_completo for word in ['piscina', 'pileta']):
                amenities.append('piscina')
            if any(word in texto_completo for word in ['jardin', 'jardín']):
                amenities.append('jardín')
            img_elem = listing.find('img')
            imagenes = [img_elem.get('src', '')] if img_elem else []
            return {'external_id': f"zonaprop_{external_id}", 'portal': 'ZonaProp', 'titulo': titulo, 'precio': precio, 'moneda': moneda, 'ubicacion': ubicacion, 'tipo': 'Casa', 'habitaciones': habitaciones, 'banos': banos, 'm2_cubiertos': m2_cubiertos, 'm2_descubiertos': 0, 'amenities': amenities, 'descripcion': descripcion, 'url': url, 'imagenes': imagenes, 'match_score': 0}
        except:
            return None
''')
    
    # Main.py
    create_file('main.py', '''#!/usr/bin/env python3
from database import PropertyDatabase
from matcher import PropertyMatcher
from notifier import TelegramNotifier
from scrapers.zonaprop import ZonaPropScraper
from config import MATCH_THRESHOLD
import time

def main():
    print("🏠 Iniciando búsqueda de propiedades...")
    db = PropertyDatabase()
    matcher = PropertyMatcher()
    notifier = TelegramNotifier()
    scrapers = [ZonaPropScraper()]
    total_nuevas = 0
    total_alertas = 0
    for scraper in scrapers:
        print(f"\\n🔍 Scrapeando {scraper.__class__.__name__}...")
        try:
            properties = scraper.search()
            print(f"   Encontradas: {len(properties)} propiedades")
            for prop in properties:
                prop['match_score'] = matcher.calculate_match(prop)
                is_new = db.save_property(prop)
                if is_new:
                    total_nuevas += 1
                    print(f"   ✅ Nueva: {prop['titulo'][:50]}... ({prop['match_score']}%)")
                    if prop['match_score'] >= MATCH_THRESHOLD:
                        print(f"   🔔 Enviando alerta...")
                        if notifier.send_property_alert(prop):
                            db.mark_as_notified(prop['external_id'])
                            total_alertas += 1
                time.sleep(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    print(f"\\n📊 RESUMEN: {total_nuevas} nuevas | {total_alertas} alertas\\n")

if __name__ == "__main__":
    main()
''')
    
    # Workflow
    os.makedirs('.github/workflows', exist_ok=True)
    create_file('.github/workflows/scraper.yml', '''name: Property Scraper
on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:
jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run scraper
      env:
        TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      run: python main.py
    - name: Commit changes
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add -A
        git diff --quiet && git diff --staged --quiet || git commit -m "Update [skip ci]"
        git push
''')
    
    print("✅ ¡Instalación completada!")

if __name__ == "__main__":
    setup_project()
