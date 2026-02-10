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
        b​​​​​​​​​​​​​​​​
