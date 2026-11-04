
import json
import shutil
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parent
ORIGEN = BASE / "dataset"
DESTINO = BASE / "dataset_yolo"

DIVISIONES = ["train", "valid", "test"]
EXTENSIONES = {".jpg", ".jpeg", ".png", ".bmp"}

# Leer categorías reales del dataset
archivo_train = ORIGEN / "train" / "_annotations.coco.json"

if not archivo_train.exists():
    raise FileNotFoundError(f"No existe: {archivo_train}")

with open(archivo_train, encoding="utf-8") as f:
    datos_train = json.load(f)

categorias = sorted(
    datos_train["categories"],
    key=lambda c: c["id"]
)

mapa_ids = {
    cat["id"]: i for i, cat in enumerate(categorias)
}

nombres = [cat["name"] for cat in categorias]
print("Clases encontradas:", nombres)

total_etiquetas = 0

for division in DIVISIONES:
    origen = ORIGEN / division
    json_path = origen / "_annotations.coco.json"

    if not json_path.exists():
        print("Omitiendo:", division)
        continue

    with open(json_path, encoding="utf-8") as f:
        datos = json.load(f)

    carpeta_img = DESTINO / division / "images"
    carpeta_lbl = DESTINO / division / "labels"

    carpeta_img.mkdir(parents=True, exist_ok=True)
    carpeta_lbl.mkdir(parents=True, exist_ok=True)

    # Agrupar anotaciones por imagen
    anotaciones = {}
    for ann in datos["annotations"]:
        anotaciones.setdefault(
            ann["image_id"], []
        ).append(ann)

    for imagen in datos["images"]:
        nombre = imagen["file_name"]
        archivo_origen = origen / nombre

        if not archivo_origen.exists():
            print("Imagen no encontrada:", nombre)
            continue

        ancho = imagen["width"]
        alto = imagen["height"]

        if ancho <= 0 or alto <= 0:
            continue

        # Conservar nombres y rutas relativas
        archivo_destino = carpeta_img / nombre
        archivo_destino.parent.mkdir(
            parents=True, exist_ok=True
        )
        shutil.copy2(archivo_origen, archivo_destino)

        lineas = []

        for ann in anotaciones.get(imagen["id"], []):
            if ann.get("iscrowd", 0):
                continue

            categoria = ann["category_id"]
            if categoria not in mapa_ids:
                continue

            x, y, w, h = ann["bbox"]

            # Limitar el rectángulo a la imagen
            x1 = max(0, min(float(x), ancho))
            y1 = max(0, min(float(y), alto))
            x2 = max(0, min(float(x + w), ancho))
            y2 = max(0, min(float(y + h), alto))

            if x2 <= x1 or y2 <= y1:
                continue

            xc = (x1 + x2) / (2 * ancho)
            yc = (y1 + y2) / (2 * alto)
            wn = (x2 - x1) / ancho
            hn = (y2 - y1) / alto

            clase = mapa_ids[categoria]

            lineas.append(
                f"{clase} {xc:.6f} {yc:.6f} "
                f"{wn:.6f} {hn:.6f}"
            )
            total_etiquetas += 1

        etiqueta = (
            carpeta_lbl /
            Path(nombre).with_suffix(".txt")
        )
        etiqueta.parent.mkdir(
            parents=True, exist_ok=True
        )
        etiqueta.write_text(
            "\n".join(lineas),
            encoding="utf-8"
        )

# Crear YAML
config = {
    "path": str(DESTINO.resolve()),
    "train": "train/images",
    "val": "valid/images",
    "test": "test/images",
    "names": {i: n for i, n in enumerate(nombres)}
}

DESTINO.mkdir(parents=True, exist_ok=True)

with open(
    DESTINO / "data.yaml", "w", encoding="utf-8"
) as f:
    yaml.safe_dump(
        config, f,
        allow_unicode=True,
        sort_keys=False
    )

print("Conversión completada.")
print("Etiquetas generadas:", total_etiquetas)
print("Dataset YOLO:", DESTINO)
