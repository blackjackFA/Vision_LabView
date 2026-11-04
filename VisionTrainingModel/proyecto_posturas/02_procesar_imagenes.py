from pathlib import Path
import csv
import cv2
import numpy as np

ENTRADA = Path('datos/originales')
SALIDA = Path('datos/procesadas')
EXTENSIONES = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
SALIDA.mkdir(parents=True, exist_ok=True)

# Histogramas: CSV con 256 intensidades y frecuencias por canal.
with (SALIDA / 'resumen.csv').open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['imagen', 'clase', 'alto', 'ancho', 'canales', 'tipo', 'media_gris', 'desviacion_gris', 'pixeles_borde', 'area_contorno_maximo'])
    archivos = sorted(p for p in ENTRADA.rglob('*') if p.is_file() and p.suffix.lower() in EXTENSIONES)
    if not archivos:
        raise SystemExit('No hay fotos: coloca archivos en datos/originales/NOMBRE_POSTURA/')
    for archivo in archivos:
        imagen = cv2.imread(str(archivo))
        if imagen is None:
            print('No se pudo leer:', archivo)
            continue
        # Para conservar identificadores y clases sin colisiones
        relativo = archivo.relative_to(ENTRADA)
        destino = SALIDA / relativo.with_suffix('')
        destino.mkdir(parents=True, exist_ok=True)
        clase = relativo.parts[0] if len(relativo.parts) > 1 else 'sin_etiqueta'
        # 1-3: dimensiones, RGB y canales (OpenCV lee BGR).
        alto, ancho = imagen.shape[:2]
        rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
        b, g, r = cv2.split(imagen)
        for nombre, canal in [('rojo', r), ('verde', g), ('azul', b)]:
            cv2.imwrite(str(destino / f'{nombre}.png'), canal)
        # 4: escala de grises
        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(str(destino / 'grises.png'), gris)
        # 5: histogramas
        with (destino / 'histogramas.csv').open('w', newline='', encoding='utf-8') as hf:
            hw = csv.writer(hf)
            hw.writerow(['intensidad', 'gris', 'rojo', 'verde', 'azul'])
            hists = [cv2.calcHist([canal], [0], None, [256], [0, 256]).ravel() for canal in [gris, r, g, b]]
            for i in range(256):
                hw.writerow([i] + [int(h[i]) for h in hists])
        # Transformacion de intensidad gamma (ejemplo gamma=0.7)
        gamma = 0.7
        tabla = np.array([np.clip(255 * (i / 255) ** gamma, 0, 255) for i in range(256)], dtype=np.uint8)
        cv2.imwrite(str(destino / 'gamma.png'), cv2.LUT(imagen, tabla))
        # 6: binarizacion automatica Otsu (NO equivale a segmentar perfectamente a la persona)
        _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cv2.imwrite(str(destino / 'binaria_otsu.png'), binaria)
        # Ecualizacion adaptativa de contraste (sobre luminancia de LAB)
        lab = cv2.cvtColor(imagen, cv2.COLOR_BGR2LAB)
        l, a, bb = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2, tileGridSize=(8, 8))
        realzada = cv2.cvtColor(cv2.merge([clahe.apply(l), a, bb]), cv2.COLOR_LAB2BGR)
        cv2.imwrite(str(destino / 'ecualizada.png'), realzada)
        # 7: espacios de color
        cv2.imwrite(str(destino / 'hsv.png'), cv2.cvtColor(imagen, cv2.COLOR_BGR2HSV))
        cv2.imwrite(str(destino / 'lab.png'), lab)
        # 8: operaciones: filtro, bordes, contornos (segmentacion exploratoria)
        filtrada = cv2.medianBlur(gris, 5)
        bordes = cv2.Canny(filtrada, 70, 150)
        cv2.imwrite(str(destino / 'filtrada_mediana.png'), filtrada)
        cv2.imwrite(str(destino / 'bordes_canny.png'), bordes)
        contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mayor = max(contornos, key=cv2.contourArea) if contornos else None
        contorno_vis = imagen.copy()
        if mayor is not None:
            cv2.drawContours(contorno_vis, [mayor], -1, (0, 255, 0), 2)
        cv2.imwrite(str(destino / 'contorno_exploratorio.png'), contorno_vis)
        # 9: caracteristicas basicas; requieren puntos corporales para una postura robusta
        writer.writerow([str(relativo), clase, alto, ancho, rgb.shape[2], str(imagen.dtype),
                         round(float(gris.mean()), 3), round(float(gris.std()), 3),
                         int(np.count_nonzero(bordes)),
                         round(float(cv2.contourArea(mayor)), 2) if mayor is not None else 0])
        print('Procesada:', relativo)
print('Listo. Resultados en datos/procesadas; verifica visualmente los resultados.')
