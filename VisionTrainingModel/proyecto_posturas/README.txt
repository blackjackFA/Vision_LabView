PROYECTO: BASE DE DATOS Y PROCESAMIENTO DIGITAL DE POSTURAS

1. Instala Python y ejecuta: pip install opencv-python numpy
2. Ejecuta desde la carpeta proyecto_posturas.
3. Organiza tus fotografías originales en:
   datos/originales/de_pie/
   datos/originales/sentado/
   datos/originales/acostado/
   datos/originales/inclinado/
4. Opcional: guarda un video como video.mp4, configura 01_extraer_fotogramas.py
   (clase, identificador de persona e intervalo) y ejecútalo.
5. Ejecuta: python 02_procesar_imagenes.py
6. Abre datos/procesadas/resumen.csv y las carpetas de resultados por foto.

Este procesamiento cubre etapas demostrativas del material de clase.
No entrena ni evalua un clasificador. No presupongas que Otsu separa personas del fondo.
Para reconocer posturas con mayor robustez, usa puntos corporales con MediaPipe Pose
Landmarker y entrena un clasificador con sus coordenadas y angulos, o usa un detector
preentrenado y ajústalo con tus datos.

IMPORTANTE: Divide entrenamiento/validacion/prueba por PERSONA antes de entrenar.
No publiques caras sin consentimiento. Registra la fuente/licencia de datos externos.
