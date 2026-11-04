
from ultralytics import YOLO
import torch

# Detectar si tienes GPU NVIDIA compatible
dispositivo = 0 if torch.cuda.is_available() else "cpu"

# Cargar un modelo preentrenado
modelo = YOLO("yolo11n.pt")

# Entrenar con tus propias imágenes y anotaciones
resultados = modelo.train(
    data="dataset_yolo/data.yaml",
    epochs=100,
    imgsz=640,
    batch=8,
    device=dispositivo,
    workers=0,
    project="resultados",
    name="posturas",
    plots=True
)

print("Entrenamiento finalizado")

# Evaluar el modelo entrenado
metricas = modelo.val(data="dataset_yolo/data.yaml")
