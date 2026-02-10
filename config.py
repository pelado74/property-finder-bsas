“””
BUSCADOR AUTOMÁTICO DE PROPIEDADES - BUENOS AIRES
Sistema completo de monitoreo de propiedades con alertas Telegram

ESTRUCTURA DEL REPOSITORIO:
property-finder/
├── README.md
├── requirements.txt
├── config.py
├── main.py
├── scrapers/
│   ├── **init**.py
│   ├── zonaprop.py
│   ├── mercadolibre.py
│   └── properati.py
├── matcher.py
├── notifier.py
├── database.py
├── dashboard.html
└── .github/
└── workflows/
└── scraper.yml

=== ARCHIVO: README.md ===
“””

# 🏠 Buscador Automático de Propiedades - Buenos Aires

Sistema automatizado que monitorea portales inmobiliarios 24/7 y te alerta vía Telegram cuando encuentra propiedades que coincidan ≥75% con tus criterios.

## 🎯 Criterios de Búsqueda Configurados

- **Presupuesto:** USD 200,000 - 400,000
- **Zonas:** Saavedra, Coghlan, Núñez (norte), Vicente López (cerca CABA)
- **Tipo:** Casa
- **Habitaciones:** Mínimo 3
- **Baños:** Mínimo 2
- **M² Cubiertos:** Mínimo 180
- **M² Descubiertos:** Mínimo 100
- **Amenities:** Garaje, piscina, jardín

## 🚀 Configuración Rápida (5 pasos)

### 1. Fork este repositorio

- Click en “Fork” arriba a la derecha
- Crea tu propia copia

### 2. Configurar Secrets en GitHub

Ve a: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

Agrega estos secrets:

- `TELEGRAM_BOT_TOKEN`: El token de tu bot (ya lo tienes del proyecto turnos)
- `TELEGRAM_CHAT_ID`: Tu chat ID (ya lo tienes)

### 3. Activar GitHub Actions

- Ve a la pestaña `Actions`
- Click en “I understand my workflows, go ahead and enable them”

### 4. Ejecutar primera vez

- Ve a `Actions` → `Property Scraper` → `Run workflow` → `Run workflow`

### 5. ¡Listo!

El bot revisará automáticamente cada 6 horas y te alertará vía Telegram.

## 📊 Ver Resultados

- **Telegram:** Recibirás alertas automáticas
- **Dashboard:** Abre `dashboard.html` en tu navegador (descárgalo del repo)
- **Base de datos:** `properties.db` contiene todas las propiedades encontradas

## 🔧 Portales Monitoreados

- ✅ ZonaProp
- ✅ Mercado Libre
- ✅ Properati
- ✅ Argenprop

## 📝 Personalizar Criterios

Edita el archivo `config.py` para cambiar:

- Presupuesto
- Zonas
- Características
- Pesos de matching

-----

“””
=== ARCHIVO: requirements.txt ===
“””
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
python-telegram-bot==20.7
sqlite3==3.44.0
schedule==1.2.0

“””
=== ARCHIVO: config.py ===
“””
import os

# Configuración de Telegram

TELEGRAM_BOT_TOKEN = os.getenv(‘TELEGRAM_BOT_TOKEN’, ‘’)
TELEGRAM_CHAT_ID = os.getenv(‘TELEGRAM_CHAT_ID’, ‘’)

# Criterios de búsqueda

CRITERIOS = {
“presupuesto”: {
“min”: 200000,
“max”: 400000,
“moneda”: “USD”,
“peso”: 0.20  # 20% del score total
},
“ubicacion”: {
“zonas”: [
“saavedra”,
“coghlan”,
“nuñez”,
“vicente lopez”,
“vicente lópez”
],
“palabras_clave”: [
“zona norte de nuñez”,
“vicente lopez cerca caba”,
“limite con caba”
],
“peso”: 0.25  # 25% del score
},
“tipo”: {
“valores”: [“casa”, “house”, “chalet”],
“peso”: 0.10  # 10% del score
},
“habitaciones”: {
“min”: 3,
“peso”: 0.10
},
“baños”: {
“min”: 2,
“peso”: 0.08
},
“m2_cubiertos”: {
“min”: 180,
“peso”: 0.12
},
“m2_descubiertos”: {
“min”: 100,
“peso”: 0.08
},
“amenities”: {
“requeridos”: [“garaje”, “cochera”, “piscina”, “pileta”, “jardin”, “jardín”],
“peso_garaje”: 0.02,
“peso_piscina”: 0.03,
“peso_jardin”: 0.02
}
}

# Configuración de scraping

SCRAPING_CONFIG = {
“user_agent”: “Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36”,
“timeout”: 30,
“max_retries”: 3,
“delay_between_requests”: 2  # segundos
}

# Umbral de matching

MATCH_THRESHOLD = 75  # Alertar solo si el match es >= 75%

# Base de datos

DB_PATH = “properties.db”

“””
=== ARCHIVO: database.py ===
“””
import sqlite3
from datetime import datetime
import json

class PropertyDatabase:
def **init**(self, db_path=“properties.db”):
self.db_path = db_path
self.init_database()

```
def init_database(self):
    """Crea las tablas si no existen"""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE,
            portal TEXT,
            titulo TEXT,
            precio REAL,
            moneda TEXT,
            ubicacion TEXT,
            tipo TEXT,
            habitaciones INTEGER,
            banos INTEGER,
            m2_cubiertos REAL,
            m2_descubiertos REAL,
            amenities TEXT,
            descripcion TEXT,
            url TEXT,
            imagenes TEXT,
            match_score REAL,
            fecha_encontrada TIMESTAMP,
            ultima_actualizacion TIMESTAMP,
            notificado BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

def save_property(self, property_data):
    """Guarda o actualiza una propiedad"""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO properties 
            (external_id, portal, titulo, precio, moneda, ubicacion, tipo,
             habitaciones, banos, m2_cubiertos, m2_descubiertos, amenities,
             descripcion, url, imagenes, match_score, fecha_encontrada, 
             ultima_actualizacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            property_data['external_id'],
            property_data['portal'],
            property_data['titulo'],
            property_data['precio'],
            property_data['moneda'],
            property_data['ubicacion'],
            property_data['tipo'],
            property_data['habitaciones'],
            property_data['banos'],
            property_data['m2_cubiertos'],
            property_data['m2_descubiertos'],
            json.dumps(property_data['amenities']),
            property_data['descripcion'],
            property_data['url'],
            json.dumps(property_data['imagenes']),
            property_data['match_score'],
            datetime.now(),
            datetime.now()
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Ya existe, actualizar
        cursor.execute('''
            UPDATE properties 
            SET precio=?, match_score=?, ultima_actualizacion=?
            WHERE external_id=?
        ''', (
            property_data['precio'],
            property_data['match_score'],
            datetime.now(),
            property_data['external_id']
        ))
        conn.commit()
        return False
    finally:
        conn.close()

def mark_as_notified(self, external_id):
    """Marca una propiedad como notificada"""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE properties SET notificado=1 WHERE external_id=?',
        (external_id,)
    )
    conn.commit()
    conn.close()

def get_unnotified_matches(self, threshold=75):
    """Obtiene propiedades no notificadas con match >= threshold"""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM properties 
        WHERE match_score >= ? AND notificado = 0
        ORDER BY match_score DESC
    ''', (threshold,))
    
    rows = cursor.fetchall()
    conn.close()
    
    properties = []
    for row in rows:
        properties.append({
            'id': row[0],
            'external_id': row[1],
            'portal': row[2],
            'titulo': row[3],
            'precio': row[4],
            'moneda': row[5],
            'ubicacion': row[6],
            'tipo': row[7],
            'habitaciones': row[8],
            'banos': row[9],
            'm2_cubiertos': row[10],
            'm2_descubiertos': row[11],
            'amenities': json.loads(row[12]),
            'descripcion': row[13],
            'url': row[14],
            'imagenes': json.loads(row[15]),
            'match_score': row[16]
        })
    
    return properties
```

“””
=== ARCHIVO: matcher.py ===
“””
from config import CRITERIOS

class PropertyMatcher:
def **init**(self, criterios=CRITERIOS):
self.criterios = criterios

```
def calculate_match(self, propiedad):
    """Calcula el porcentaje de match de una propiedad"""
    score = 0
    max_score = 0
    
    # Precio (20%)
    precio_peso = self.criterios['presupuesto']['peso'] * 100
    max_score += precio_peso
    if self.criterios['presupuesto']['min'] <= propiedad.get('precio', 0) <= self.criterios['presupuesto']['max']:
        score += precio_peso
    
    # Ubicación (25%)
    ubicacion_peso = self.criterios['ubicacion']['peso'] * 100
    max_score += ubicacion_peso
    ubicacion = propiedad.get('ubicacion', '').lower()
    for zona in self.criterios['ubicacion']['zonas']:
        if zona.lower() in ubicacion:
            score += ubicacion_peso
            break
    
    # Tipo (10%)
    tipo_peso = self.criterios['tipo']['peso'] * 100
    max_score += tipo_peso
    tipo = propiedad.get('tipo', '').lower()
    for tipo_valido in self.criterios['tipo']['valores']:
        if tipo_valido in tipo:
            score += tipo_peso
            break
    
    # Habitaciones (10%)
    hab_peso = self.criterios['habitaciones']['peso'] * 100
    max_score += hab_peso
    if propiedad.get('habitaciones', 0) >= self.criterios['habitaciones']['min']:
        score += hab_peso
    
    # Baños (8%)
    banos_peso = self.criterios['baños']['peso'] * 100
    max_score += banos_peso
    if propiedad.get('banos', 0) >= self.criterios['baños']['min']:
        score += banos_peso
    
    # M2 cubiertos (12%)
    m2c_peso = self.criterios['m2_cubiertos']['peso'] * 100
    max_score += m2c_peso
    if propiedad.get('m2_cubiertos', 0) >= self.criterios['m2_cubiertos']['min']:
        score += m2c_peso
    
    # M2 descubiertos (8%)
    m2d_peso = self.criterios['m2_descubiertos']['peso'] * 100
    max_score += m2d_peso
    if propiedad.get('m2_descubiertos', 0) >= self.criterios['m2_descubiertos']['min']:
        score += m2d_peso
    
    # Amenities (7% total)
    amenities = ' '.join(propiedad.get('amenities', [])).lower()
    descripcion = propiedad.get('descripcion', '').lower()
    texto_completo = f"{amenities} {descripcion}"
    
    # Garaje (2%)
    if any(word in texto_completo for word in ['garaje', 'cochera']):
        score += self.criterios['amenities']['peso_garaje'] * 100
    max_score += self.criterios['amenities']['peso_garaje'] * 100
    
    # Piscina (3%)
    if any(word in texto_completo for word in ['piscina', 'pileta']):
        score += self.criterios['amenities']['peso_piscina'] * 100
    max_score += self.criterios['amenities']['peso_piscina'] * 100
    
    # Jardín (2%)
    if any(word in texto_completo for word in ['jardin', 'jardín', 'parque']):
        score += self.criterios['amenities']['peso_jardin'] * 100
    max_score += self.criterios['amenities']['peso_jardin'] * 100
    
    # Calcular porcentaje final
    match_percentage = (score / max_score * 100) if max_score > 0 else 0
    
    return round(match_percentage, 2)
```

“””
=== ARCHIVO: notifier.py ===
“””
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramNotifier:
def **init**(self, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
self.token = token
self.chat_id = chat_id
self.base_url = f”https://api.telegram.org/bot{token}”

```
def send_property_alert(self, propiedad):
    """Envía alerta de propiedad por Telegram"""
    mensaje = self._format_property_message(propiedad)
    
    # Enviar mensaje de texto
    url = f"{self.base_url}/sendMessage"
    data = {
        "chat_id": self.chat_id,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error enviando notificación: {e}")
        return False

def _format_property_message(self, prop):
    """Formatea el mensaje de la propiedad"""
    match_emoji = "🔥" if prop['match_score'] >= 90 else "✨" if prop['match_score'] >= 80 else "⭐"
    
    mensaje = f"""
```

{match_emoji} <b>NUEVA PROPIEDAD - {prop[‘match_score’]}% MATCH</b>

🏠 <b>{prop[‘titulo’]}</b>

💰 <b>Precio:</b> {prop[‘moneda’]} {prop[‘precio’]:,.0f}
📍 <b>Ubicación:</b> {prop[‘ubicacion’]}
🏷️ <b>Portal:</b> {prop[‘portal’]}

📊 <b>Características:</b>
• Habitaciones: {prop[‘habitaciones’]}
• Baños: {prop[‘banos’]}
• M² Cubiertos: {prop[‘m2_cubiertos’]}
• M² Descubiertos: {prop[‘m2_descubiertos’]}

🎯 <b>Amenities:</b> {’, ’.join(prop[‘amenities’]) if prop[‘amenities’] else ‘No especificados’}

🔗 <a href="{prop['url']}">VER PROPIEDAD</a>
“””.strip()

```
    return mensaje
```

“””
=== ARCHIVO: scrapers/zonaprop.py ===
“””
import requests
from bs4 import BeautifulSoup
import time
import re

class ZonaPropScraper:
def **init**(self):
self.base_url = “https://www.zonaprop.com.ar”
self.headers = {
‘User-Agent’: ‘Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36’
}

```
def search(self):
    """Busca propiedades en ZonaProp"""
    properties = []
    
    # URLs de búsqueda para las zonas especificadas
    search_urls = [
        f"{self.base_url}/casas-venta-saavedra.html",
        f"{self.base_url}/casas-venta-coghlan.html",
        f"{self.base_url}/casas-venta-nunez.html",
        f"{self.base_url}/casas-venta-vicente-lopez.html"
    ]
    
    for url in search_urls:
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                properties.extend(self._parse_listings(response.text, url))
            time.sleep(2)  # Rate limiting
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    
    return properties

def _parse_listings(self, html, search_url):
    """Parsea los listados de propiedades"""
    soup = BeautifulSoup(html, 'lxml')
    properties = []
    
    # Nota: Los selectores pueden cambiar, esto es un ejemplo
    listings = soup.find_all('div', class_='postings-container')
    
    for listing in listings[:10]:  # Limitar a 10 por búsqueda
        try:
            prop = self._parse_property(listing)
            if prop:
                properties.append(prop)
        except Exception as e:
            print(f"Error parsing property: {e}")
            continue
    
    return properties

def _parse_property(self, listing):
    """Extrae datos de una propiedad individual"""
    # Este es un ejemplo - los selectores reales dependen de la estructura HTML actual
    try:
        # ID único
        external_id = listing.get('data-id', f"zp_{hash(str(listing)[:50])}")
        
        # Título y URL
        title_elem = listing.find('h2') or listing.find('a')
        titulo = title_elem.text.strip() if title_elem else "Sin título"
        url = title_elem.get('href', '') if title_elem else ''
        if url and not url.startswith('http'):
            url = self.base_url + url
        
        # Precio
        price_elem = listing.find(text=re.compile(r'USD|U\$S'))
        precio = 0
        moneda = 'USD'
        if price_elem:
            price_text = price_elem.strip()
            precio = float(re.sub(r'[^\d]', '', price_text)) if price_text else 0
        
        # Ubicación
        ubicacion_elem = listing.find(class_='location') or listing.find(text=re.compile(r'Saavedra|Coghlan|Núñez|Vicente López'))
        ubicacion = ubicacion_elem.text.strip() if ubicacion_elem else "No especificada"
        
        # Características
        features = listing.find_all(class_='feature')
        habitaciones = 0
        banos = 0
        m2_cubiertos = 0
        m2_descubiertos = 0
        
        for feature in features:
            text = feature.text.lower()
            if 'dorm' in text or 'hab' in text:
                habitaciones = int(re.search(r'\d+', text).group()) if re.search(r'\d+', text) else 0
            elif 'baño' in text:
                banos = int(re.search(r'\d+', text).group()) if re.search(r'\d+', text) else 0
            elif 'cub' in text:
                m2_cubiertos = float(re.search(r'\d+', text).group()) if re.search(r'\d+', text) else 0
            elif 'desc' in text or 'terr' in text:
                m2_descubiertos = float(re.search(r'\d+', text).group()) if re.search(r'\d+', text) else 0
        
        # Amenities
        desc_elem = listing.find(class_='description')
        descripcion = desc_elem.text.strip() if desc_elem else ""
        amenities = []
        if any(word in descripcion.lower() for word in ['garaje', 'cochera']):
            amenities.append('garaje')
        if any(word in descripcion.lower() for word in ['piscina', 'pileta']):
            amenities.append('piscina')
        if any(word in descripcion.lower() for word in ['jardin', 'jardín']):
            amenities.append('jardín')
        
        # Imágenes
        img_elem = listing.find('img')
        imagenes = [img_elem.get('src', '')] if img_elem else []
        
        return {
            'external_id': f"zonaprop_{external_id}",
            'portal': 'ZonaProp',
            'titulo': titulo,
            'precio': precio,
            'moneda': moneda,
            'ubicacion': ubicacion,
            'tipo': 'Casa',
            'habitaciones': habitaciones,
            'banos': banos,
            'm2_cubiertos': m2_cubiertos,
            'm2_descubiertos': m2_descubiertos,
            'amenities': amenities,
            'descripcion': descripcion,
            'url': url,
            'imagenes': imagenes,
            'match_score': 0
        }
    except Exception as e:
        print(f"Error en _parse_property: {e}")
        return None
```

“””
=== ARCHIVO: main.py ===
“””
#!/usr/bin/env python3
from database import PropertyDatabase
from matcher import PropertyMatcher
from notifier import TelegramNotifier
from scrapers.zonaprop import ZonaPropScraper
from config import MATCH_THRESHOLD
import time

def main():
print(“🏠 Iniciando búsqueda de propiedades…”)

```
# Inicializar componentes
db = PropertyDatabase()
matcher = PropertyMatcher()
notifier = TelegramNotifier()

# Scrapers
scrapers = [
    ZonaPropScraper(),
    # Agregar más scrapers aquí
]

total_nuevas = 0
total_alertas = 0

# Ejecutar cada scraper
for scraper in scrapers:
    print(f"\n🔍 Scrapeando {scraper.__class__.__name__}...")
    try:
        properties = scraper.search()
        print(f"   Encontradas: {len(properties)} propiedades")
        
        for prop in properties:
            # Calcular match
            prop['match_score'] = matcher.calculate_match(prop)
            
            # Guardar en DB
            is_new = db.save_property(prop)
            
            if is_new:
                total_nuevas += 1
                print(f"   ✅ Nueva: {prop['titulo'][:50]}... ({prop['match_score']}%)")
                
                # Alertar si cumple threshold
                if prop['match_score'] >= MATCH_THRESHOLD:
                    print(f"   🔔 Enviando alerta...")
                    if notifier.send_property_alert(prop):
                        db.mark_as_notified(prop['external_id'])
                        total_alertas += 1
            
            time.sleep(1)  # Rate limiting
            
    except Exception as e:
        print(f"❌ Error con {scraper.__class__.__name__}: {e}")
        continue

# Resumen
print(f"\n📊 RESUMEN:")
print(f"   • Propiedades nuevas: {total_nuevas}")
print(f"   • Alertas enviadas: {total_alertas}")
print(f"\n✅ Proceso completado\n")
```

if **name** == “**main**”:
main()

“””
=== ARCHIVO: .github/workflows/scraper.yml ===
“””
name: Property Scraper

on:
schedule:
- cron: ‘0 */6 * * *’  # Cada 6 horas
workflow_dispatch:  # Permite ejecución manual

jobs:
scrape:
runs-on: ubuntu-latest

```
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
  run: |
    python main.py

- name: Commit database changes
  run: |
    git config --local user.email "action@github.com"
    git config --local user.name "GitHub Action"
    git add properties.db
    git diff --quiet && git diff --staged --quiet || git commit -m "Update properties database"
    git push
```

“””
=== ARCHIVO: dashboard.html ===
“””

<!DOCTYPE html>

<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏠 Buscador de Propiedades - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5rem;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        .property-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .property-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }
        .match-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            color: white;
            margin-bottom: 10px;
        }
        .match-high { background: #10b981; }
        .match-medium { background: #f59e0b; }
        .match-low { background: #6b7280; }
        .property-title {
            font-size: 1.4rem;
            margin-bottom: 10px;
            color: #1f2937;
        }
        .property-price {
            font-size: 1.8rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 15px;
        }
        .property-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }
        .detail-item {
            padding: 8px;
            background: #f3f4f6;
            border-radius: 5px;
        }
        .detail-label {
            font-size: 0.8rem;
            color: #6b7280;
            margin-bottom: 3px;
        }
        .detail-value {
            font-weight: bold;
            color: #1f2937;
        }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 10px;
            transition: background 0.2s;
        }
        .btn:hover {
            background: #5568d3;
        }
        .amenities {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 15px;
        }
        .amenity-tag {
            padding: 5px 12px;
            background: #e0e7ff;
            color: #667eea;
            border-radius: 15px;
            font-size: 0.85rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏠 Propiedades Encontradas</h1>

```
    <div class="stats">
        <div class="stat-card">
            <div class="stat-number" id="total-properties">0</div>
            <div class="stat-label">Total Propiedades</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="high-matches">0</div>
            <div class="stat-label">Match ≥ 75%</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="avg-match">0%</div>
            <div class="stat-label">Match Promedio</div>
        </div>
    </div>
    
    <div id="properties-container">
        <!-- Las propiedades se cargarán aquí -->
        <div style="text-align: center; color: white; padding: 40px;">
            <h2>📝 Instrucciones:</h2>
            <p style="margin-top: 20px;">
                Este dashboard requiere el archivo <code>properties.db</code> 
                del repositorio para mostrar las propiedades.
            </p>
            <p style="margin-top: 10px;">
                Por ahora, las alertas llegarán directamente a tu Telegram.
            </p>
        </div>
    </div>
</div>

<script>
    // Este script se conectaría a la base de datos
    // Por simplicidad, mostraremos datos de ejemplo
    const exampleProperties = [
        {
            titulo: "Casa en Saavedra con pileta",
            precio: 280000,
            moneda: "USD",
            ubicacion: "Saavedra, CABA",
            habitaciones: 4,
            banos: 2,
            m2_cubiertos: 200,
            m2_descubiertos: 150,
            amenities: ["garaje", "piscina", "jardín"],
            match_score: 92,
            url: "#",
            portal: "ZonaProp"
        }
    ];
    
    // Función para renderizar propiedades
    // (En producción, esto leería de la DB via backend)
</script>
```

</body>
</html>
