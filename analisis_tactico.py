import cv2
import numpy as np
from ultralytics import YOLO
import yt_dlp
import requests
import torch
import os
import subprocess
import sys
import re
import tempfile
import urllib3
from urllib.parse import urljoin, urlparse
import easyocr

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FiltroInteligencia:
    def __init__(self):
        self.model = YOLO("yolov8x-oiv7.pt")
        # uso de hilos para mayor velocidad en CPU/GPU
        self.model.to('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Inicializar lector OCR (español e inglés)
        print("[*] Inicializando motor OCR (EasyOCR)...")
        self.ocr_reader = easyocr.Reader(['es', 'en'], gpu=torch.cuda.is_available(), verbose=False)
        
        self.pesos = {
            'Land vehicle': 8, 'Truck': 9, 'Van': 7, 'Armored vehicle': 12,
            'Weapon': 15, 'Rifle': 15, 'Person': 2
        }
        
        self.traduccion = {
            'Land vehicle': 'Vehículo Blindado',
            'Truck': 'Camioneta de Combate',
            'Armored vehicle': 'Monstruo Blindado',
            'Weapon': 'Armamento',
            'Rifle': 'Fusil de Asalto',
            'Person': 'Sujeto Detectado'
        }
        
        # Palabras clave de reclutamiento 
        self.palabras_reclutamiento = [
            # Ofertas de dinero / beneficios
            'sueldo', 'salario', 'pago', 'ganas', 'ganar', 'dinero', 'lana', 'feria',
            'billetes', 'dolares', 'pesos', 'quincena', 'quincenal', 'semanal',
            'mensual', 'bono', 'prestaciones', 'utilidades',
            # Montos atractivos de dinero
            '10,000', '15,000', '20,000', '25,000', '30,000', '40,000', '50,000',
            '10mil', '15mil', '20mil', '25mil', '30mil', '50mil',
            '10 mil', '15 mil', '20 mil', '25 mil', '30 mil', '50 mil',
            # Facilidades / sin requisitos
            'sin experiencia', 'no experiencia', 'no necesitas', 'sin estudios',
            'cualquier edad', 'hombre o mujer', 'ambos sexos', 'medio tiempo',
            'tiempo completo', 'horario flexible', 'disponibilidad inmediata',
            'contratacion inmediata', 'contratación inmediata', 'empleo inmediato',
            'inicio inmediato', 'vacante', 'vacantes', 'se busca', 'se buscan',
            'se solicita', 'se solicitan', 'se necesita', 'se necesitan',
            'se requiere', 'se requieren', 'se ocupa', 'se ocupan',
            'unete', 'únete', 'forma parte', 'trabaja con nosotros',
            'oportunidad', 'oportunidades',
            # Trabajo sospechoso / eufemismos
            'seguridad privada', 'escolta', 'escoltas', 'guardia', 'guardias',
            'proteccion', 'protección', 'vigilancia', 'vigilante',
            'halcon', 'halcón', 'halcones', 'puntero', 'punteros',
            'plaza', 'plazas', 'jale', 'jales', 'chamba', 'chambas',
            'operador', 'operadores', 'sicario', 'sicarios',
            'soldado', 'soldados', 'reclutamiento', 'recluta',
            # Contacto
            'whatsapp', 'telegram', 'contacto', 'comunicate', 'comunícate',
            'manda mensaje', 'llama', 'marca', 'interesados',
            # Amenazas / control territorial
            'territorio', 'cartel', 'grupo', 'organización', 'organizacion',
            'patron', 'patrón', 'jefe', 'comandante', 'lider', 'líder',
            # Promesas
            'beneficios', 'seguro de vida', 'casa', 'carro', 'camioneta', 'transporte',
            'armas', 'equipo', 'uniforme', 'chaleco', 'radio', 'vehiculo', 'vehículo'
        ]

    def analizar_texto_reclutamiento(self, img):
        """
        EasyOCR para extraer texto de la imagen y buscar palabras clave
        asociadas a reclutamiento del crimen organizado.
        Retorna: (texto_detectado: bool, texto_completo: str, palabras_encontradas: list, regiones: list)
        """
        try:
            resultados_ocr = self.ocr_reader.readtext(img, paragraph=False)
        except Exception as e:
            print(f"  [!] Error en OCR: {e}")
            return False, '', [], []
        
        if not resultados_ocr:
            return False, '', [], []
        
        # Concatenar todo el texto detectado
        textos = []
        regiones = []
        for (bbox, texto, confianza) in resultados_ocr:
            if confianza > 0.25:  # Umbral mínimo de confianza
                textos.append(texto)
                # bbox es una lista de 4 puntos [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                xs = [int(p[0]) for p in bbox]
                ys = [int(p[1]) for p in bbox]
                regiones.append({
                    'texto': texto,
                    'confianza': confianza,
                    'bbox': (min(xs), min(ys), max(xs), max(ys))
                })
        
        texto_completo = ' '.join(textos).lower()
        
        # Buscar palabras clave de reclutamiento
        palabras_encontradas = []
        for palabra in self.palabras_reclutamiento:
            if palabra.lower() in texto_completo:
                if palabra not in palabras_encontradas:
                    palabras_encontradas.append(palabra)
        
        texto_detectado = len(palabras_encontradas) > 0
        return texto_detectado, ' '.join(textos), palabras_encontradas, regiones

    def analizar_entorno(self, img):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        bajo_sierra = np.array([10, 20, 20])
        alto_sierra = np.array([30, 255, 200])
        mask_sierra = cv2.inRange(hsv, bajo_sierra, alto_sierra)
        return (cv2.countNonZero(mask_sierra) / (img.shape[0]*img.shape[1])) * 100

    def _descargar_imagen_desde_url(self, url):
        """Descarga una imagen  desde una URL y la decodifica."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
        }
        resp = requests.get(url, headers=headers, verify=False, timeout=10)
        arr = np.frombuffer(resp.content, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img

    def _extraer_imagen_de_pagina(self, url):
        """Descarga la página HTML y extrae la imagen principal."""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            resp = requests.get(url, headers=headers, verify=False, timeout=10)
            html = resp.text
        except Exception as e:
            print(f"[-] No se pudo descargar la página: {e}")
            return None

        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        extensiones_img = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif')

        # 1) og:image (Open Graph) - la más confiable para redes sociales y foros
        og = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if not og:
            og = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
        if og:
            img_url = og.group(1)
            if img_url.startswith('//'): img_url = 'https:' + img_url
            elif img_url.startswith('/'): img_url = base + img_url
            print(f"[*] Imagen OG encontrada: {img_url}")
            try:
                return self._descargar_imagen_desde_url(img_url)
            except Exception:
                pass

        # 2) Twitter Card image
        tc = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if tc:
            img_url = tc.group(1)
            if img_url.startswith('//'): img_url = 'https:' + img_url
            elif img_url.startswith('/'): img_url = base + img_url
            print(f"[*] Imagen Twitter Card encontrada: {img_url}")
            try:
                return self._descargar_imagen_desde_url(img_url)
            except Exception:
                pass

        # 3) Etiquetas <img> con src directa a imagen
        imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I)
        for src in imgs:
            clean = src.lower().split('?')[0]
            if any(clean.endswith(ext) for ext in extensiones_img):
                if src.startswith('//'): src = 'https:' + src
                elif src.startswith('/'): src = base + src
                elif not src.startswith('http'): src = urljoin(url, src)
                try:
                    img = self._descargar_imagen_desde_url(src)
                    if img is not None and img.shape[0] > 50 and img.shape[1] > 50:
                        print(f"[*] Imagen <img> encontrada: {src}")
                        return img
                except Exception:
                    continue

        print("[-] No se encontró ninguna imagen utilizable en la página.")
        return None

    def obtener_imagen(self, entrada):
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Archivo local
        if os.path.exists(entrada):
            return cv2.imread(entrada)
        
        extensiones_img = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
        # URL directa a un archivo de imagen
        if entrada.lower().split('?')[0].endswith(extensiones_img):
            return self._descargar_imagen_desde_url(entrada)
        
        # URL de página web genérica: extraer imagen embebida del HTML
        if entrada.startswith('http://') or entrada.startswith('https://'):
            return self._extraer_imagen_de_pagina(entrada)
        
        return None

    def es_video(self, entrada):
        if not isinstance(entrada, str):
            return False
        clean = entrada.lower().split('?')[0]
        exts_video = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.3gp', '.flv')
        if clean.endswith(exts_video):
            return True
        # Plataformas de video conocidas
        plataformas_video = ['youtube.com/watch', 'youtu.be/', 'tiktok.com', 'facebook.com/watch',
                             'dailymotion.com', 'vimeo.com', 'twitch.tv']
        if any(p in clean for p in plataformas_video):
            return True
        return False

    def obtener_video_cap(self, entrada):
        # Archivo local: abrir directamente
        if os.path.exists(entrada):
            cap = cv2.VideoCapture(entrada)
            if cap.isOpened():
                return cap, None  # No hay archivo temporal que limpiar
        
        # URL remota: descargar a un archivo temporal para que OpenCV pueda abrirlo
        try:
            tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            tmp_path = tmp.name
            tmp.close()
            
            print("[*] Descargando video... (esto puede tardar unos segundos)")
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
                'outtmpl': tmp_path,
                'overwrites': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([entrada])
            
            # yt_dlp puede añadir extensión; buscar el archivo descargado
            if not os.path.exists(tmp_path):
                for ext in ['.mp4', '.webm', '.mkv']:
                    candidate = tmp_path.replace('.mp4', ext)
                    if os.path.exists(candidate):
                        tmp_path = candidate
                        break
            
            cap = cv2.VideoCapture(tmp_path)
            if cap.isOpened():
                print(f"[+] Video descargado y listo para analizar.")
                return cap, tmp_path  # Devolver ruta para poder borrarla al terminar
            else:
                os.unlink(tmp_path)
        except Exception as e:
            print(f"[-] Error al descargar video: {e}")
        return None, None

    def analizar_color_vehiculo(self, crop):
        if crop is None or crop.size == 0:
            return 'civil'
        
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        total_pixels = crop.shape[0] * crop.shape[1]
        
        # Verde olivo militar amplio (SEDENA)
        bajo_verde = np.array([25, 10, 10])
        alto_verde = np.array([85, 255, 140])
        
        # Arena/Desierto (Ejército/Guardia Nacional)
        bajo_arena = np.array([10, 15, 60])
        alto_arena = np.array([25, 140, 200])
        
        # Blanco oficial (Guardia Nacional / Policía)
        bajo_blanco = np.array([0, 0, 160])
        alto_blanco = np.array([180, 25, 255])
        
        # Gris militar/naval (Marina)
        bajo_gris = np.array([0, 0, 45])
        alto_gris = np.array([180, 20, 180])
        
        mask_verde = cv2.inRange(hsv, bajo_verde, alto_verde)
        perc_verde = (cv2.countNonZero(mask_verde) / total_pixels) * 100
        
        mask_arena = cv2.inRange(hsv, bajo_arena, alto_arena)
        perc_arena = (cv2.countNonZero(mask_arena) / total_pixels) * 100
        
        mask_blanco = cv2.inRange(hsv, bajo_blanco, alto_blanco)
        perc_blanco = (cv2.countNonZero(mask_blanco) / total_pixels) * 100
        
        mask_gris = cv2.inRange(hsv, bajo_gris, alto_gris)
        perc_gris = (cv2.countNonZero(mask_gris) / total_pixels) * 100
        
        if perc_verde > 15:
            return 'verde_militar'
        elif perc_arena > 15:
            return 'arena_militar'
        elif perc_gris > 20:
            return 'gris_militar'
        elif perc_blanco > 30:
            return 'blanco_oficial'
        else:
            return 'civil'

    def _detectar_insignias_mexicanas(self, crop):
        """
        Analiza el tercio superior del crop (pecho, hombros, brazos) para buscar:
        - Bandera de México (verde, blanco y rojo en proximidad).
        - Brazalete DN-III-E / Plan Marina (amarillo/naranja brillante).
        - Brazalete Guardia Nacional (negro/azul oscuro con letras de alto contraste blanco/gris).
        """
        h, w = crop.shape[:2]
        if h < 45 or w < 25:
            return False, 'ninguna'
            
        # El tercio superior es la zona donde están los parches y brazaletes (hombros, pecho)
        upper_zone = crop[0:int(h * 0.45), :]
        hsv_uz = cv2.cvtColor(upper_zone, cv2.COLOR_BGR2HSV)
        total_pixels = upper_zone.shape[0] * upper_zone.shape[1]
        
        # 1. Bandera de México (Verde, Blanco, Rojo cercanos horizontalmente)
        # Rango Verde: H [35, 85], S [50, 255], V [30, 255]
        bajo_verde = np.array([35, 50, 30])
        alto_verde = np.array([85, 255, 255])
        # Rango Rojo: H [0, 50] o H [170, 180], S [70, 255], V [50, 255]
        bajo_rojo1 = np.array([0, 70, 50])
        alto_rojo1 = np.array([12, 255, 255])
        bajo_rojo2 = np.array([168, 70, 50])
        alto_rojo2 = np.array([180, 255, 255])
        # Rango Blanco (alto valor, baja saturación): H [0, 180], S [0, 40], V [180, 255]
        bajo_blanco = np.array([0, 0, 175])
        alto_blanco = np.array([180, 45, 255])
        
        mask_v = cv2.inRange(hsv_uz, bajo_verde, alto_verde)
        mask_r1 = cv2.inRange(hsv_uz, bajo_rojo1, alto_rojo1)
        mask_r2 = cv2.inRange(hsv_uz, bajo_rojo2, alto_rojo2)
        mask_r = cv2.bitwise_or(mask_r1, mask_r2)
        mask_w = cv2.inRange(hsv_uz, bajo_blanco, alto_blanco)
        
        pv = (cv2.countNonZero(mask_v) / total_pixels) * 100
        pr = (cv2.countNonZero(mask_r) / total_pixels) * 100
        pw = (cv2.countNonZero(mask_w) / total_pixels) * 100
        
        if pv > 1.0 and pr > 1.0 and pw > 1.2:
            return True, 'Bandera de Mexico'
            
        # 2. Brazalete Plan DN-III-E (SEDENA/Ejército) / Plan Marina: Amarillo/naranja de alta visibilidad
        bajo_amarillo = np.array([18, 110, 110])
        alto_amarillo = np.array([32, 255, 255])
        mask_y = cv2.inRange(hsv_uz, bajo_amarillo, alto_amarillo)
        py = (cv2.countNonZero(mask_y) / total_pixels) * 100
        if py > 2.0:
            return True, 'Brazalete DN-III-E'
            
        return False, 'ninguna'

    def _analizar_calzado(self, crop):
        """
        Analiza la zona de calzado (15% inferior) para detectar tenis vs botas militares.
        Cualquier calzado que NO sea bota reglamentaria uniforme (negra o café militar) 
        se cataloga como tenis/calzado civil.
        """
        h, w = crop.shape[:2]
        if h < 40:
            return 'indeterminado'
        
        # Zona de calzado: último 17% del recorte, franja central
        w_start = int(w * 0.15)
        w_end   = int(w * 0.85)
        feet = crop[int(h * 0.83):h, w_start:w_end]
        
        if feet.size == 0 or feet.shape[0] < 3:
            return 'indeterminado'
        
        hsv_feet = cv2.cvtColor(feet, cv2.COLOR_BGR2HSV)
        total = feet.shape[0] * feet.shape[1]
        
        # 1. Firmas de Botas Oficiales (Deben ser oscuras y uniformes)
        # Botas negras: H: cualquier, S: baja-media, V: muy baja (oscuridad)
        bajo_bota_negra = np.array([0, 0, 0])
        alto_bota_negra = np.array([180, 70, 60])
        mask_bn = cv2.inRange(hsv_feet, bajo_bota_negra, alto_bota_negra)
        perc_bota_negra = (cv2.countNonZero(mask_bn) / total) * 100
        
        # Botas café Coyote / Tan (militar): H: [8, 22], S: [30, 150], V: [35, 130]
        bajo_bota_cafe = np.array([8, 30, 35])
        alto_bota_cafe = np.array([22, 160, 130])
        mask_bc = cv2.inRange(hsv_feet, bajo_bota_cafe, alto_bota_cafe)
        perc_bota_cafe = (cv2.countNonZero(mask_bc) / total) * 100
        
        perc_botas_reglamentarias = perc_bota_negra + perc_bota_cafe
        
        # 2. Firmas de Tenis/Calzado Civil (Brillos, suelas claras o colores saturados)
        # Suelas blancas/claras o tenis blancos: H: cualquier, S: muy baja, V: alta (brillante)
        bajo_blanco_suela = np.array([0, 0, 155])
        alto_blanco_suela = np.array([180, 60, 255])
        mask_tb = cv2.inRange(hsv_feet, bajo_blanco_suela, alto_blanco_suela)
        perc_blanco_suela = (cv2.countNonZero(mask_tb) / total) * 100
        
        # Colores civiles (cualquier color que no sea el verde/marrón/negro opaco reglamentario)
        # Alta saturación (> 70) y brillo medio-alto (> 85)
        bajo_tenis_color = np.array([0, 70, 85])
        alto_tenis_color = np.array([180, 255, 255])
        mask_tc = cv2.inRange(hsv_feet, bajo_tenis_color, alto_tenis_color)
        perc_tenis_color = (cv2.countNonZero(mask_tc) / total) * 100
        
        gray_feet = cv2.cvtColor(feet, cv2.COLOR_BGR2GRAY)
        std_dev = np.std(gray_feet)
        
        # 3. Decisiones de Clasificación General
        # Si hay elementos claros de tenis (como suela blanca o colores llamativos)
        if (perc_blanco_suela > 5) or (perc_tenis_color > 4) or (std_dev > 35):
            return 'tenis'
            
        # Si NO tiene un porcentaje significativo de bota reglamentaria uniforme en la base
        if perc_botas_reglamentarias < 45:
            # Si no es bota oficial, por descarte es calzado deportivo/civil (tenis)
            return 'tenis'
            
        return 'botas_militares'

    def analizar_uniforme_persona(self, crop):
        if crop is None or crop.size == 0:
            return 'desconocido', 0.0, 'ninguna'
            
        h, w = crop.shape[:2]
        if h < 30 or w < 15:
            return 'desconocido', 0.0, 'ninguna'
            
        upper = crop[0:int(h*0.5), :]
        w_start = int(w * 0.25)
        w_end = int(w * 0.75)
        lower_center = crop[int(h*0.5):h, w_start:w_end]
        
        if upper.size == 0 or lower_center.size == 0:
            return 'desconocido', 0.0, 'ninguna'
            
        hsv_upper = cv2.cvtColor(upper, cv2.COLOR_BGR2HSV)
        hsv_lower = cv2.cvtColor(lower_center, cv2.COLOR_BGR2HSV)
        
        bajo_verde = np.array([25, 10, 10])
        alto_verde = np.array([85, 255, 140])
        
        bajo_arena = np.array([10, 15, 60])
        alto_arena = np.array([25, 140, 200])
        
        bajo_azul_oficial = np.array([95, 35, 15])
        alto_azul_oficial = np.array([130, 255, 110])
        
        mask_v_up = cv2.inRange(hsv_upper, bajo_verde, alto_verde)
        mask_v_lo = cv2.inRange(hsv_lower, bajo_verde, alto_verde)
        perc_v_up = (cv2.countNonZero(mask_v_up) / (upper.shape[0] * upper.shape[1])) * 100
        perc_v_lo = (cv2.countNonZero(mask_v_lo) / (lower_center.shape[0] * lower_center.shape[1])) * 100
        
        mask_a_up = cv2.inRange(hsv_upper, bajo_arena, alto_arena)
        mask_a_lo = cv2.inRange(hsv_lower, bajo_arena, alto_arena)
        perc_a_up = (cv2.countNonZero(mask_a_up) / (upper.shape[0] * upper.shape[1])) * 100
        perc_a_lo = (cv2.countNonZero(mask_a_lo) / (lower_center.shape[0] * lower_center.shape[1])) * 100
 
        mask_az_up = cv2.inRange(hsv_upper, bajo_azul_oficial, alto_azul_oficial)
        mask_az_lo = cv2.inRange(hsv_lower, bajo_azul_oficial, alto_azul_oficial)
        perc_az_up = (cv2.countNonZero(mask_az_up) / (upper.shape[0] * upper.shape[1])) * 100
        perc_az_lo = (cv2.countNonZero(mask_az_lo) / (lower_center.shape[0] * lower_center.shape[1])) * 100
 
        es_camo_verde = perc_v_up > 15 and perc_v_lo > 15
        es_camo_arena = perc_a_up > 15 and perc_a_lo > 15
        es_uniforme_azul = perc_az_up > 20 and perc_az_lo > 20
        
        tiene_insignia, tipo_insignia = self._detectar_insignias_mexicanas(crop)
        
        tiene_camo_arriba = perc_v_up > 15 or perc_a_up > 15
        tiene_camo_abajo = perc_v_lo > 12 or perc_a_lo > 12
        
        calzado = self._analizar_calzado(crop)
        
        # Caso 1: Camuflaje arriba pero ropa civil abajo
        if tiene_camo_arriba and not tiene_camo_abajo:
            return 'sicario_uniforme_incompleto', max(perc_v_up, perc_a_up), tipo_insignia
            
        # Caso 2: Uniforme militar completo detectado
        if es_camo_verde or es_camo_arena:
            if calzado == 'tenis':
                return 'sicario_camo_tenis', max(perc_v_up, perc_v_lo, perc_a_up, perc_a_lo), tipo_insignia
            elif calzado == 'botas_militares':
                if tiene_insignia:
                    if es_camo_verde:
                        return 'uniforme_militar_verde_oficial', max(perc_v_up, perc_v_lo), tipo_insignia
                    else:
                        return 'uniforme_militar_arena_oficial', max(perc_a_up, perc_a_lo), tipo_insignia
                else:
                    if es_camo_verde:
                        return 'militar_sin_insignias_verde', max(perc_v_up, perc_v_lo), 'ninguna'
                    else:
                        return 'militar_sin_insignias_arena', max(perc_a_up, perc_a_lo), 'ninguna'
            else: # Calzado indeterminado
                if tiene_insignia:
                    if es_camo_verde:
                        return 'uniforme_militar_verde_oficial', max(perc_v_up, perc_v_lo), tipo_insignia
                    else:
                        return 'uniforme_militar_arena_oficial', max(perc_a_up, perc_a_lo), tipo_insignia
                else:
                    if es_camo_verde:
                        return 'militar_no_verificado_verde', max(perc_v_up, perc_v_lo), 'ninguna'
                    else:
                        return 'militar_no_verificado_arena', max(perc_a_up, perc_a_lo), 'ninguna'

        if es_uniforme_azul:
            if calzado == 'tenis':
                return 'sicario_camo_tenis', max(perc_az_up, perc_az_lo), tipo_insignia
            return 'uniforme_policia_azul', max(perc_az_up, perc_az_lo), tipo_insignia

        bajo_azul_jeans = np.array([95, 40, 50])
        alto_azul_jeans = np.array([130, 255, 240])
        mask_jeans = cv2.inRange(hsv_lower, bajo_azul_jeans, alto_azul_jeans)
        perc_jeans = (cv2.countNonZero(mask_jeans) / (lower_center.shape[0] * lower_center.shape[1])) * 100
        if perc_jeans > 15:
            return 'sicario_jeans', perc_jeans, 'ninguna'
            
        mean_upper = cv2.mean(hsv_upper)[:3]
        mean_lower = cv2.mean(hsv_lower)[:3]
        dist_color = np.sqrt((mean_upper[0]-mean_lower[0])**2 + 
                             (mean_upper[1]-mean_lower[1])**2 + 
                             (mean_upper[2]-mean_lower[2])**2)
        if dist_color > 45:
            return 'civil_mismatch', dist_color, 'ninguna'
            
        return 'casual_uniforme_desconocido', dist_color, 'ninguna'

    def analizar_frame(self, img):
        results = self.model.predict(img, conf=0.15, verbose=False, imgsz=640)
        img_dibujada = img.copy()
        
        arma_detectada = False
        vehiculo_detectado = False
        
        sicarios_detectados = 0
        oficiales_detectados = 0
        vehiculos_oficiales = 0
        vehiculos_sospechosos = 0
        
        personas = []
        armas = []
        
        # Primera pasada: Clasificar vehículos
        for r in results:
            for box in r.boxes:
                label_en = self.model.names[int(box.cls)]
                if label_en in self.pesos:
                    b = box.xyxy[0].cpu().numpy().astype(int)
                    if label_en == 'Person':
                        personas.append(b)
                    elif label_en in ['Weapon', 'Rifle']:
                        arma_detectada = True
                        armas.append(b)
                    elif label_en in ['Armored vehicle', 'Truck', 'Land vehicle', 'Van']:
                        vehiculo_detectado = True
                        crop_veh = img[max(0, b[1]):min(img.shape[0], b[3]), max(0, b[0]):min(img.shape[1], b[2])]
                        color_veh = self.analizar_color_vehiculo(crop_veh)
                        
                        if color_veh in ['verde_militar', 'arena_militar', 'gris_militar', 'blanco_oficial']:
                            vehiculos_oficiales += 1
                            cv2.rectangle(img_dibujada, (b[0], b[1]), (b[2], b[3]), (0, 255, 0), 3)
                            cv2.putText(img_dibujada, f"Vehiculo Oficial ({color_veh})", (b[0], b[1]-10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        else:
                            vehiculos_sospechosos += 1
                            cv2.rectangle(img_dibujada, (b[0], b[1]), (b[2], b[3]), (0, 0, 255), 3)
                            cv2.putText(img_dibujada, "Vehiculo Civil", (b[0], b[1]-10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Segunda pasada: Clasificar personas armadas
        impostores_detectados = 0
        uniformes_incompletos = 0
        militares_no_verificados = 0
        drawn_label_positions = []

        for p_box in personas:
            tiene_arma_cerca = False
            for a_box in armas:
                p_center = ((p_box[0]+p_box[2])/2, (p_box[1]+p_box[3])/2)
                a_center = ((a_box[0]+a_box[2])/2, (a_box[1]+a_box[3])/2)
                dist = np.sqrt((p_center[0]-a_center[0])**2 + (p_center[1]-a_center[1])**2)
                p_width = p_box[2] - p_box[0]
                if dist < p_width * 2.5:
                    tiene_arma_cerca = True
                    break
            
            crop_p = img[max(0, p_box[1]):min(img.shape[0], p_box[3]), max(0, p_box[0]):min(img.shape[1], p_box[2])]
            tipo_vestimenta, score, tipo_insignia = self.analizar_uniforme_persona(crop_p)
            
            # Calcular posición inicial del texto del tag
            x_pos = p_box[0]
            y_pos = p_box[1] - 8
            
            # Algoritmo anti-solapamiento de etiquetas (stacking vertical)
            attempts = 0
            while attempts < 8:
                overlap = False
                for prev_x, prev_y in drawn_label_positions:
                    # Si están muy cerca en X y en Y, desplazamos Y hacia arriba
                    if abs(x_pos - prev_x) < 160 and abs(y_pos - prev_y) < 18:
                        y_pos -= 18
                        overlap = True
                        break
                if not overlap:
                    break
                attempts += 1
            y_pos = max(15, y_pos)
            drawn_label_positions.append((x_pos, y_pos))

            # Caso crítico: Impostores y uniformes incompletos se marcan como peligro SIEMPRE (estén armados o no)
            if tipo_vestimenta == 'sicario_camo_tenis':
                sicarios_detectados += 1
                impostores_detectados += 1
                cv2.rectangle(img_dibujada, (p_box[0], p_box[1]), (p_box[2], p_box[3]), (0, 0, 255), 2)
                cv2.putText(img_dibujada, "ALERTA: Camo+Tenis (Impostor)", (x_pos, y_pos), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            elif tipo_vestimenta == 'sicario_uniforme_incompleto':
                sicarios_detectados += 1
                uniformes_incompletos += 1
                cv2.rectangle(img_dibujada, (p_box[0], p_box[1]), (p_box[2], p_box[3]), (0, 0, 255), 2)
                cv2.putText(img_dibujada, "ALERTA: Uniforme Incompleto", (x_pos, y_pos), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            elif tiene_arma_cerca:
                if tipo_vestimenta in ['uniforme_militar_verde_oficial', 'uniforme_militar_arena_oficial', 'uniforme_policia_azul']:
                    oficiales_detectados += 1
                    cv2.rectangle(img_dibujada, (p_box[0], p_box[1]), (p_box[2], p_box[3]), (0, 255, 0), 2)
                    lbl = f"Oficial ({tipo_insignia})" if tipo_insignia != 'ninguna' else "Oficial (Uniforme)"
                    cv2.putText(img_dibujada, lbl, (x_pos, y_pos), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                elif tipo_vestimenta in ['militar_sin_insignias_verde', 'militar_sin_insignias_arena']:
                    sicarios_detectados += 1
                    militares_no_verificados += 1
                    cv2.rectangle(img_dibujada, (p_box[0], p_box[1]), (p_box[2], p_box[3]), (0, 165, 255), 2)
                    cv2.putText(img_dibujada, "Advertencia: Sin Insignias", (x_pos, y_pos), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                elif tipo_vestimenta in ['militar_no_verificado_verde', 'militar_no_verificado_arena']:
                    sicarios_detectados += 1
                    militares_no_verificados += 1
                    cv2.rectangle(img_dibujada, (p_box[0], p_box[1]), (p_box[2], p_box[3]), (0, 165, 255), 2)
                    cv2.putText(img_dibujada, "Sospechoso: Calzado/Insignia Dudo", (x_pos, y_pos), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                elif tipo_vestimenta in ['sicario_jeans', 'civil_mismatch']:
                    sicarios_detectados += 1
                    cv2.rectangle(img_dibujada, (p_box[0], p_box[1]), (p_box[2], p_box[3]), (0, 0, 255), 2)
                    cv2.putText(img_dibujada, "Sospechoso (Jeans/Civil)", (x_pos, y_pos), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                else:
                    sicarios_detectados += 1
                    cv2.rectangle(img_dibujada, (p_box[0], p_box[1]), (p_box[2], p_box[3]), (0, 165, 255), 2)
                    cv2.putText(img_dibujada, "Sujeto Armado", (x_pos, y_pos), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
            else:
                # Persona no armada (o sin arma detectada) con uniforme aparentemente oficial o completo
                if tipo_vestimenta in ['uniforme_militar_verde_oficial', 'uniforme_militar_arena_oficial', 'uniforme_policia_azul']:
                    oficiales_detectados += 1
                    cv2.rectangle(img_dibujada, (p_box[0], p_box[1]), (p_box[2], p_box[3]), (0, 255, 0), 2)
                    cv2.putText(img_dibujada, "Oficial", (x_pos, y_pos), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                elif tipo_vestimenta in ['militar_no_verificado_verde', 'militar_no_verificado_arena', 'militar_sin_insignias_verde', 'militar_sin_insignias_arena']:
                    militares_no_verificados += 1
                    cv2.rectangle(img_dibujada, (p_box[0], p_box[1]), (p_box[2], p_box[3]), (0, 165, 255), 2)
                    cv2.putText(img_dibujada, "Militar No Verificado", (x_pos, y_pos), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                else:
                    cv2.rectangle(img_dibujada, (p_box[0], p_box[1]), (p_box[2], p_box[3]), (255, 255, 0), 1)

        # Dibujar armas
        for a_box in armas:
            cv2.rectangle(img_dibujada, (a_box[0], a_box[1]), (a_box[2], a_box[3]), (0, 0, 255), 2)

        sierra_perc = self.analizar_entorno(img)
        es_sierra = sierra_perc > 15
        
        return {
            'arma_detectada': arma_detectada,
            'vehiculo_detectado': vehiculo_detectado,
            'es_sierra': es_sierra,
            'sicarios_detectados': sicarios_detectados,
            'oficiales_detectados': oficiales_detectados,
            'impostores_detectados': impostores_detectados,
            'uniformes_incompletos': uniformes_incompletos,
            'militares_no_verificados': militares_no_verificados,
            'vehiculos_oficiales': vehiculos_oficiales,
            'vehiculos_sospechosos': vehiculos_sospechosos,
            'img_dibujada': img_dibujada
        }

    def triage_final(self, entrada):
        is_vid = self.es_video(entrada)
        tmp_path = None
        
        if is_vid:
            cap, tmp_path = self.obtener_video_cap(entrada)
            if cap is None:
                print(f"[-] No se pudo abrir el video. Intentando extraer imagen...")
                is_vid = False
            
            if is_vid:
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps <= 0 or np.isnan(fps): fps = 30
                intervalo_frames = max(1, int(fps))
                
                frame_idx = 0
                arma_detectada = False
                vehiculo_detectado = False
                es_sierra = False
                sicarios_detectados = 0
                oficiales_detectados = 0
                impostores_detectados = 0
                uniformes_incompletos = 0
                militares_no_verificados = 0
                vehiculos_oficiales = 0
                vehiculos_sospechosos = 0
                
                img_representativa = None
                max_sicarios = -1
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    h, w = frame.shape[:2]
                    if w > 1280:
                        scale = 1280.0 / w
                        frame = cv2.resize(frame, (1280, int(h * scale)))
                    
                    if frame_idx % intervalo_frames == 0:
                        res = self.analizar_frame(frame)
                        
                        arma_detectada = arma_detectada or res['arma_detectada']
                        vehiculo_detectado = vehiculo_detectado or res['vehiculo_detectado']
                        es_sierra = es_sierra or res['es_sierra']
                        
                        sicarios_detectados = max(sicarios_detectados, res['sicarios_detectados'])
                        oficiales_detectados = max(oficiales_detectados, res['oficiales_detectados'])
                        impostores_detectados = max(impostores_detectados, res['impostores_detectados'])
                        uniformes_incompletos = max(uniformes_incompletos, res['uniformes_incompletos'])
                        militares_no_verificados = max(militares_no_verificados, res['militares_no_verificados'])
                        vehiculos_oficiales = max(vehiculos_oficiales, res['vehiculos_oficiales'])
                        vehiculos_sospechosos = max(vehiculos_sospechosos, res['vehiculos_sospechosos'])
                        
                        if res['sicarios_detectados'] > max_sicarios or img_representativa is None:
                            max_sicarios = res['sicarios_detectados']
                            img_representativa = res['img_dibujada']
                        
                        if total_frames > 0:
                            progreso = int((frame_idx / total_frames) * 100)
                            print(f"\r[*] Analizando video... {progreso}%", end='', flush=True)

                    frame_idx += 1
                    
                cap.release()
                print()  # Nueva línea después del progreso
                
                # Limpiar archivo temporal
                if tmp_path and os.path.exists(tmp_path):
                    try: os.unlink(tmp_path)
                    except Exception: pass
                
                if img_representativa is None:
                    print("Error: No se pudieron procesar fotogramas del video.")
                    return
                
                img_final_dibujada = img_representativa
        
        texto_reclutamiento = False
        texto_completo = ''
        palabras_sospechosas = []
        regiones_texto = []

        if not is_vid:
            try:
                img = self.obtener_imagen(entrada)
                if img is None:
                    print("Error: No se pudo cargar la imagen.")
                    return
            except Exception as e:
                print(f"Error al cargar imagen: {e}")
                return
                
            res = self.analizar_frame(img)
            arma_detectada = res['arma_detectada']
            vehiculo_detectado = res['vehiculo_detectado']
            es_sierra = res['es_sierra']
            sicarios_detectados = res['sicarios_detectados']
            oficiales_detectados = res['oficiales_detectados']
            impostores_detectados = res['impostores_detectados']
            uniformes_incompletos = res['uniformes_incompletos']
            militares_no_verificados = res['militares_no_verificados']
            vehiculos_oficiales = res['vehiculos_oficiales']
            vehiculos_sospechosos = res['vehiculos_sospechosos']
            img_final_dibujada = res['img_dibujada']
            
            # Análisis de texto OCR en imagen
            print("[*] Analizando texto en la imagen (OCR)...")
            texto_reclutamiento, texto_completo, palabras_sospechosas, regiones_texto = self.analizar_texto_reclutamiento(img)
            
            # Dibujar regiones de texto detectadas sobre la imagen
            if regiones_texto:
                for reg in regiones_texto:
                    bx = reg['bbox']
                    # Determinar si la palabra es sospechosa
                    es_sospechosa = any(p.lower() in reg['texto'].lower() for p in palabras_sospechosas)
                    color_txt = (0, 0, 255) if es_sospechosa else (255, 200, 0)
                    cv2.rectangle(img_final_dibujada, (bx[0], bx[1]), (bx[2], bx[3]), color_txt, 1)
                    if es_sospechosa:
                        cv2.putText(img_final_dibujada, reg['texto'], (bx[0], bx[1] - 4),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # LOGICA DE CLASIFICACIÓN DE ALERTA Y REPORTE
        categorias = []
        justificaciones = {}
        
        # Análisis de texto de reclutamiento
        if texto_reclutamiento:
            categorias.append("RECLUTAMIENTO")
            palabras_str = ', '.join(palabras_sospechosas[:10])
            justificaciones["PROPAGANDA DE RECLUTAMIENTO"] = f"Texto sospechoso de reclutamiento detectado. Palabras clave: [{palabras_str}]."
        
        # Una patrulla oficial predomina en la escena para prevenir falsos positivos con operativos oficiales.
        # Pero si hay impostores vestidos de militar con tenis o uniformes incompletos, esto anula la clasificación oficial del grupo.
        es_oficial = (oficiales_detectados >= 1 and vehiculos_oficiales >= 1 and impostores_detectados == 0 and uniformes_incompletos == 0) or \
                     (oficiales_detectados > 0 and sicarios_detectados == 0 and vehiculos_sospechosos == 0)
        
        if es_oficial and not texto_reclutamiento:
            categorias.append("FUERZAS OFICIALES")
            justificaciones["PRESENCIA OFICIAL"] = f"Se identificó personal militar/policial uniformado ({oficiales_detectados}) junto a transporte institucional oficial ({vehiculos_oficiales})."
            nivel = "BAJA"
            color = (0, 255, 0)
        else:
            if impostores_detectados > 0:
                categorias.append("USO DE IMPOSTORES")
                justificaciones["IMPOSTOR DETECTADO"] = f"Sujeto(s) armados con ropa de camuflaje militar usando calzado deportivo/tenis ({impostores_detectados})."
            if uniformes_incompletos > 0:
                categorias.append("UNIFORME INCOMPLETO")
                justificaciones["UNIFORME MIXTO"] = f"Sujeto(s) armados vistiendo uniforme militar combinado con jeans u otra ropa civil ({uniformes_incompletos})."
            if militares_no_verificados > 0:
                categorias.append("IDENTIDAD EN DUDA")
                justificaciones["MILITAR NO VERIFICADO"] = f"Sujeto(s) con uniforme táctico pero sin parches/insignias oficiales mexicanas o calzado no visible ({militares_no_verificados})."

            if arma_detectada: 
                categorias.append("ARMAMENTO")
                if sicarios_detectados > 0:
                    justificaciones["RIESGO BALÍSTICO"] = f"Presencia de {sicarios_detectados} sujetos armados con vestimenta civil o irregular."
                else:
                    justificaciones["RIESGO BALÍSTICO"] = "Presencia de armas de fuego detectadas en el entorno."
            if vehiculo_detectado: 
                categorias.append("MOVILIDAD")
                if vehiculos_sospechosos > 0:
                    justificaciones["RIESGO LOGÍSTICO"] = "Uso de vehículos civiles o camionetas sin insignias oficiales junto a actividad sospechosa."
                else:
                    justificaciones["RIESGO LOGÍSTICO"] = "Uso de vehículos de transporte en zona de análisis."
            if es_sierra: 
                categorias.append("GEOGRAFÍA")
                justificaciones["RIESGO GEOGRÁFICO"] = "Entorno rural o de sierra de difícil acceso que facilita el ocultamiento."

            conteo_riesgos = len(categorias)
            
            if texto_reclutamiento and len(palabras_sospechosas) >= 3:
                nivel = "CRÍTICA"
                color = (0, 0, 255)
            elif (impostores_detectados > 0 or uniformes_incompletos > 0) and (arma_detectada or es_sierra):
                nivel = "CRÍTICA"
                color = (0, 0, 255)
            elif texto_reclutamiento or (impostores_detectados > 0 or uniformes_incompletos > 0) or sicarios_detectados > 0 or conteo_riesgos >= 2:
                nivel = "ALTA"
                color = (0, 0, 255)
            elif conteo_riesgos == 1:
                nivel = "MEDIA"
                color = (0, 165, 255)
            else:
                nivel = "BAJA"
                color = (0, 255, 255)

        conteo_riesgos = len(categorias)

        # REPORTE A CONSOLA
        print(f"\n{'='*65}")
        print(f" REPORTE DE INTELIGENCIA TÁCTICA | NIVEL: {nivel}")
        print(f"{'='*65}")
        print(f"Factores de Riesgo Hallados ({conteo_riesgos}): {', '.join(categorias) if categorias else 'Ninguno'}")
        
        print("\nDESGLOSE DE AMENAZA:")
        if not justificaciones:
            print("  [*] Situación estable.")
        else:
            for tipo, desc in justificaciones.items():
                print(f"  [!] {tipo}: {desc}")
        
        # Mostrar texto OCR detectado si existe
        if texto_completo:
            print(f"\nTEXTO DETECTADO EN IMAGEN:")
            print(f"  {texto_completo[:500]}")
            if palabras_sospechosas:
                print(f"  PALABRAS CLAVE SOSPECHOSAS: {', '.join(palabras_sospechosas)}")

        print(f"{'='*65}\n")
        
        # Mostrar interfaz final
        cv2.rectangle(img_final_dibujada, (0, 0), (img_final_dibujada.shape[1], 65), (0, 0, 0), -1)
        
        titulo_text = f"AMENAZA {nivel} ({conteo_riesgos} FACTORES)"
        font_scale = 1.0
        font_thickness = 2
        
        # Ajustar escala de fuente dinámicamente para que quepa en el ancho de la imagen
        while True:
            text_size = cv2.getTextSize(titulo_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)[0]
            if text_size[0] < img_final_dibujada.shape[1] - 40 or font_scale <= 0.4:
                break
            font_scale -= 0.05
            
        cv2.putText(img_final_dibujada, titulo_text, (15, 45), 
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, font_thickness)
        
        if is_vid:
            cv2.putText(img_final_dibujada, "FRAME MAS CRITICO", (img_final_dibujada.shape[1] - 220, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Guardar imagen de resultado y abrirla con el visor del sistema
        ruta_salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultado_analisis.png")
        cv2.imwrite(ruta_salida, img_final_dibujada)
        print(f"  [+] Imagen de análisis guardada en: {ruta_salida}")
        
        # Abrir la imagen con el visor predeterminado del sistema
        try:
            if sys.platform == 'win32':
                os.startfile(ruta_salida)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', ruta_salida])
            else:
                subprocess.Popen(['xdg-open', ruta_salida])
            print("  [+] Abriendo imagen en el visor del sistema...")
        except Exception as e:
            print(f"  [!] No se pudo abrir automáticamente: {e}")
            print(f"  [*] Abra manualmente el archivo: {ruta_salida}")


if __name__ == "__main__":
    print("\n" + "="*65)
    print("      SISTEMA DE ANÁLISIS TÁCTICO Y DETECCIÓN DE AMENAZAS")
    print("="*65)
    
    app = FiltroInteligencia()
    
    while True:
        print("\nIngrese el enlace (URL) o ruta local de la imagen/video a analizar")
        print("(o escriba 'salir' para finalizar):")
        entrada = input("> ").strip()
        
        if not entrada or entrada.lower() in ['salir', 'exit', 'q']:
            print("[-] Finalizando monitor táctico...")
            break
            
        print(f"\n[*] Procesando entrada: {entrada}")
        app.triage_final(entrada)
