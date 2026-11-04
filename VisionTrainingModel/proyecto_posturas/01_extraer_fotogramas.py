from pathlib import Path
import cv2

# Cambia estos valores antes de ejecutar
VIDEO = 'video.mp4'
POSTURA = 'sentado'  # de_pie, sentado, acostado, inclinado
PERSONA = 'p01'
INTERVALO_SEG = 2

salida = Path('datos/originales') / POSTURA
salida.mkdir(parents=True, exist_ok=True)
cap = cv2.VideoCapture(VIDEO)
if not cap.isOpened():
    raise SystemExit(f'No se pudo abrir: {VIDEO}')
fps = cap.get(cv2.CAP_PROP_FPS)
if fps <= 0:
    raise SystemExit('El video no informa una tasa de fotogramas valida')
paso = max(1, round(fps * INTERVALO_SEG))
indice = 0
contador = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    if indice % paso == 0:
        archivo = salida / f'{PERSONA}_{POSTURA}_{contador:04d}.jpg'
        cv2.imwrite(str(archivo), frame)
        contador += 1
    indice += 1
cap.release()
print(f'{contador} imagenes guardadas en {salida}')
print('Revisa las imagenes, elimina duplicados y corrige etiquetas manualmente.')
