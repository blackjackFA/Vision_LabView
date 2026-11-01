"""Conectar primero la PC al Wi-Fi ESP32S3_Teleop_Net. Salir con Q o Esc."""
import argparse
import threading
import time

import cv2
from ultralytics import YOLO


class LatestFrame:
    """Un lector continuo; el consumidor nunca acumula una cola de frames."""

    def __init__(self, url):
        self.cap = cv2.VideoCapture(
            url, cv2.CAP_FFMPEG,
            [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
             cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000],
        )
        if not self.cap.isOpened():
            self.cap.release()
            raise RuntimeError(f"No se pudo abrir {url}; comprueba Wi-Fi y firmware")
        if not self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1):
            print("Backend sin soporte de BUFFERSIZE; se conserva solo el último frame")
        self.condition = threading.Condition()
        self.frame = None
        self.sequence = 0
        self.failed = False
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        try:
            while not self.stop.is_set():
                ok, frame = self.cap.read()
                with self.condition:
                    if not ok:
                        self.failed = True
                        self.condition.notify_all()
                        break
                    self.frame = frame
                    self.sequence += 1
                    self.condition.notify_all()
        finally:
            self.cap.release()

    def latest(self, previous):
        with self.condition:
            self.condition.wait_for(
                lambda: self.sequence != previous or self.failed, timeout=3
            )
            if self.failed or self.sequence == previous:
                raise RuntimeError("Stream interrumpido o sin frames durante 3 segundos")
            return self.sequence, self.frame

    def close(self):
        self.stop.set()
        self.thread.join(timeout=4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://192.168.4.1:81/stream")
    parser.add_argument("--model", default="yolov8n-pose.pt")
    parser.add_argument("--device", default="cpu", help="cpu o 0 para GPU CUDA")
    args = parser.parse_args()
    # Descargar el modelo antes de cambiar al AP, que normalmente no tiene Internet.
    model = YOLO(args.model)
    source = LatestFrame(args.url)
    sequence = 0
    try:
        while True:
            sequence, frame = source.latest(sequence)
            started = time.perf_counter()
            # stream=True devuelve un generador; consumirlo ejecuta la inferencia.
            results = model.predict(source=frame, stream=True, imgsz=640,
                                    conf=0.35, device=args.device, verbose=False)
            for result in results:
                # YOLOv8 COCO Pose: 17 keypoints por persona; plot dibuja puntos
                # visibles según confianza y conexiones del esqueleto.
                annotated = result.plot(kpt_line=True, kpt_radius=3)
                elapsed = (time.perf_counter() - started) * 1000
                cv2.putText(annotated, f"Inferencia+dibujo: {elapsed:.0f} ms",
                            (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                            (0, 255, 0), 1)
                cv2.imshow("ESP32-S3 / YOLOv8 COCO Pose", annotated)
            if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                break
            if cv2.getWindowProperty("ESP32-S3 / YOLOv8 COCO Pose", cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        source.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
