import cv2
import numpy as np
from ultralytics import YOLO
import yt_dlp
import requests
import torch
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FiltroInteligencia:
    def __init__(self):
        # OPTIMIZACIÓN: Carga el modelo en modo de inferencia rápida
        self.model = YOLO("yolov8x-oiv7.pt")
        # Forzar uso de hilos para mayor velocidad en CPU/GPU
        self.model.to('cuda' if torch.cuda.is_available() else 'cpu')
        
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

    def analizar_entorno(self, img):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        bajo_sierra = np.array([10, 20, 20])
        alto_sierra = np.array([30, 255, 200])
        mask_sierra = cv2.inRange(hsv, bajo_sierra, alto_sierra)
        return (cv2.countNonZero(mask_sierra) / (img.shape[0]*img.shape[1])) * 100

    def obtener_imagen(self, entrada):
        headers = {'User-Agent': 'Mozilla/5.0'}
        if os.path.exists(entrada): return cv2.imread(entrada)
        
        extensiones_img = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
        if entrada.lower().split('?')[0].endswith(extensiones_img):
            img_raw = requests.get(entrada, headers=headers, verify=False, timeout=5).content
            return cv2.imdecode(np.frombuffer(img_raw, np.uint8), cv2.IMREAD_COLOR)
        
        # OPTIMIZACIÓN: ydl_opts más ligeros 
        ydl_opts = {'skip_download': True, 'quiet': True, 'no_warnings': True, 'extract_flat': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(entrada, download=False)
            img_url = info.get('thumbnail')
            img_raw = requests.get(img_url, headers=headers, verify=False, timeout=5).content
            return cv2.imdecode(np.frombuffer(img_raw, np.uint8), cv2.IMREAD_COLOR)

    def triage_final(self, entrada):
        try:
            img = self.obtener_imagen(entrada)
            if img is None: return
        except Exception as e:
            print(f"Error: {e}"); return

        elementos_detectados = []
        justificaciones = {}
        
        # OPTIMIZACIÓN: Inferencia con parámetros de velocidad
        results = self.model.predict(img, conf=0.15, verbose=False, imgsz=640)
        img_dibujada = img.copy()
        
        arma_detectada = False
        vehiculo_detectado = False

        for r in results:
            for box in r.boxes:
                label_en = self.model.names[int(box.cls)]
                if label_en in self.pesos:
                    label_es = self.traduccion.get(label_en, label_en)
                    elementos_detectados.append(label_es)
                    
                    if label_en in ['Weapon', 'Rifle']: arma_detectada = True
                    if label_en in ['Armored vehicle', 'Truck', 'Land vehicle', 'Van']: vehiculo_detectado = True
                    
                    b = box.xyxy[0].cpu().numpy().astype(int)
                    cv2.rectangle(img_dibujada, (b[0], b[1]), (b[2], b[3]), (0, 0, 255), 3)

        sierra_perc = self.analizar_entorno(img)
        es_sierra = sierra_perc > 15
        if es_sierra: elementos_detectados.append("Zona de Sierra/Rural")

        categorias = []
        if arma_detectada: 
            categorias.append("ARMAMENTO")
            justificaciones["RIESGO BALÍSTICO"] = "Presencia de armas de fuego: Amenaza directa a la vida."
        if vehiculo_detectado: 
            categorias.append("MOVILIDAD")
            justificaciones["RIESGO LOGÍSTICO"] = "Uso de vehículos tácticos: Indica transporte de células armadas."
        if es_sierra: 
            categorias.append("GEOGRAFÍA")
            justificaciones["RIESGO GEOGRÁFICO"] = "Entorno de difícil acceso: Facilita el ocultamiento ilícito."

        conteo_riesgos = len(categorias)

        if conteo_riesgos >= 2:
            nivel, color = "ALTA", (0, 0, 255)
        elif conteo_riesgos == 1:
            nivel, color = "MEDIA", (0, 165, 255)
        else:
            nivel, color = "BAJA", (0, 255, 255)

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

        print(f"{'='*65}\n")
        
        # Mostrar interfaz
        cv2.rectangle(img_dibujada, (0,0), (img.shape[1], 65), (0,0,0), -1)
        cv2.putText(img_dibujada, f"AMENAZA {nivel} ({conteo_riesgos} FACTORES)", (15, 45), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)
        
        cv2.imshow("Monitor de Riesgo Táctico", img_dibujada)
        cv2.waitKey(0) 
        cv2.destroyAllWindows()

if __name__ == "__main__":
    #cambios de manera manual
    link = "https://img.gruporeforma.com/ImagenesIpad/6/417/5416921.jpg"
    app = FiltroInteligencia()
    app.triage_final(link)