# ESP32-S3 N16R8 + OV3660: teleoperación MJPEG y YOLOv8 Pose

Proyecto ESP-IDF nativo (sin Arduino). Firmware: PlatformIO Espressif32 6.9.0 / ESP-IDF 5.3.1; cámara gestionada por IDF Component Manager. PC: Python 3.10–3.12 con entorno gráfico y backend FFmpeg de OpenCV.

## Cableado y memoria

**Revisa los GPIO de `src/main.cpp` antes de flashear.** Los pines son un ejemplo tipo ESP32-S3-EYE, no identifican tu placa. El nombre DevKitC-1 no define conexiones de cámara. Alimenta el sensor según su módulo y comparte GND; no conectes señales de 5 V. Consulta el esquema para evitar pines ocupados por Flash/PSRAM, arranque o USB.

N16R8 usa Flash QIO de 16 MB y PSRAM **Octal/OPI de 8 MB**, ambas configuradas aquí a 80 MHz. `BOARD_HAS_PSRAM` es solo un define: las opciones `CONFIG_SPIRAM*` de `sdkconfig.defaults` activan realmente el soporte de ESP-IDF. No añadas esas opciones solo como `-D` ni uses opciones Arduino de memoria.

El firmware exige PSRAM inicializada de al menos 8 MB y registra tamaño y memoria libre. La prueba de PSRAM se ejecuta al arrancar; los dos framebuffers JPEG se solicitan explícitamente en PSRAM. El driver gestiona su tamaño y la devolución de cada framebuffer, también cuando falla una transmisión. Fallos de inicialización detienen el arranque del servicio.

`partitions.csv` ocupa exactamente 16 MB: NVS, PHY, aplicación factory de 4 MB y almacenamiento reservado de 0xBF0000 bytes. No hay OTA ni montaje de SPIFFS en este ejemplo.

## Compilar y cargar

Abre esta carpeta en VS Code con PlatformIO. Desde su terminal:

```sh
pio run
pio run -t upload
pio device monitor -b 115200
```

La primera compilación descarga herramientas y `espressif/esp32-camera` 2.0.15; necesita acceso a los registros de PlatformIO y componentes de Espressif. Conserva el `dependencies.lock` que genere IDF para repetir la resolución. Si ya existía un `sdkconfig.esp32-s3-devkitc-1`, revisa/retira ese archivo generado antes de reconstruir para que se apliquen los defaults nuevos. No borres configuraciones personalizadas sin guardarlas.

## Estación de tierra

Con Internet, antes de conectarte al AP:

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')"
```

Para GPU instala primero la distribución PyTorch compatible con tu CUDA siguiendo la documentación oficial. No instales `opencv-python-headless`: la ventana necesita GUI.

1. Conecta la PC manualmente al SSID **ESP32S3_Teleop_Net**, contraseña **123456789**. El script no cambia la red del sistema.
2. Mantén la conexión aunque el sistema indique que no tiene Internet. El DHCP del ESP32 proporciona dirección en 192.168.4.0/24.
3. Ejecuta `python estacion_tierra.py` (o `python estacion_tierra.py --device 0` para CUDA).
4. Sal con Q, Escape o cerrando la ventana. Ante desconexión, corrige la red y vuelve a ejecutar.

URL completa: **http://192.168.4.1:81/stream**. `http://192.168.4` está incompleta. El servidor admite un consumidor de streaming; cierra el navegador antes de abrir Python.

## Latencia y validación física

La captura usa JPEG VGA 640×480, calidad 12, dos buffers y `CAMERA_GRAB_LATEST`. VGA no es una exigencia de YOLO: `imgsz=640` adapta la entrada con letterbox. `stream=True` devuelve resultados como generador; no elimina por sí mismo buffers de red. El hilo lector descarta los frames sustituidos mientras se realiza inferencia, y solicita `CAP_PROP_BUFFERSIZE=1` (FFmpeg puede ignorarlo). TCP, Wi-Fi, exposición, decodificación e inferencia todavía pueden introducir retraso; no es un sistema de tiempo real garantizado.

El modelo COCO Pose produce 17 puntos por persona (nariz, ojos, orejas, hombros, codos, muñecas, caderas, rodillas y tobillos). `result.plot()` muestra puntos y esqueleto según su confianza. Documentación: https://docs.ultralytics.com/datasets/pose/coco/

Verifica en hardware: prueba PSRAM y tamaño en monitor serie, detección OV3660, imagen correcta y estable, reconexión tras cerrar cliente, y detección humana en la PC. Mide latencia extremo a extremo con un reloj visible en cámara; el tiempo superpuesto por Python mide inferencia y dibujo, no latencia de red. Prueba a corta distancia, un cliente y canal poco congestionado. Una fuente insuficiente o cableado largo pueden causar fallos que ningún flag corrige.

La contraseña pedida es de demostración: cámbiala en el firmware para uso real. Este proyecto transmite vídeo y estima postura; no implementa órdenes de actuadores ni parada de emergencia.

## Comprobaciones en este entorno

`python3 -m py_compile estacion_tierra.py` y `git diff --check` pasaron. No se ha validado la ejecución de OpenCV/YOLO ni el hardware. Se instaló PlatformIO 6.1.18 para intentar `pio run`, pero la descarga de la plataforma quedó bloqueada: el proxy devuelve HTTP 403 para `api.registry.platformio.org`. Por tanto, la compilación C++ queda **pendiente**, no se afirma que haya pasado. Para repetirla aquí se necesita autorizar el registro de PlatformIO y sus destinos de descarga; la resolución posterior también necesita los componentes oficiales de Espressif. No se modificó ni publicó la configuración del entorno.
