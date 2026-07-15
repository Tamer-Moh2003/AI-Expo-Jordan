"""Privacy filters applied before a frame is displayed or written."""

from __future__ import annotations

from pathlib import Path

import cv2


class PrivacyBlur:
    """Blur faces and licence plates detected in a frame."""

    def __init__(
        self,
        plate_model_path: str | None = "models/best.pt",
        blur_kernel: int = 51,
        plate_confidence: float = 0.25,
        plate_backend: str = "haar",
        detection_scale: float = 0.35,
    ) -> None:
        self.blur_kernel = self._odd_kernel(blur_kernel)
        self.plate_confidence = plate_confidence
        if not 0 < detection_scale <= 1:
            raise ValueError("detection_scale must be greater than 0 and at most 1")
        self.detection_scale = detection_scale

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_detector = cv2.CascadeClassifier(cascade_path)
        if self.face_detector.empty():
            raise RuntimeError(f"Could not load the face detector: {cascade_path}")

        self.plate_backend = plate_backend
        self.plate_model = None
        self.plate_detector = None
        if plate_backend == "haar":
            plate_cascade = cv2.data.haarcascades + "haarcascade_russian_plate_number.xml"
            self.plate_detector = cv2.CascadeClassifier(plate_cascade)
            if self.plate_detector.empty():
                raise RuntimeError(f"Could not load the plate detector: {plate_cascade}")
        elif plate_backend == "yolo" and plate_model_path:
            model_path = Path(plate_model_path)
            if not model_path.is_file():
                raise FileNotFoundError(f"Plate model not found: {model_path}")
            # This repository's plate weights were produced by YOLOv5. Loading
            # them through the matching runtime avoids cross-version fuse errors.
            import torch
            import yolov5

            # PyTorch 2.6 changed torch.load's default to weights_only=True,
            # while legacy YOLOv5 checkpoints contain their model definition.
            # Limit the compatibility override to loading this local checkpoint.
            original_torch_load = torch.load

            def legacy_torch_load(*args, **kwargs):
                kwargs.setdefault("weights_only", False)
                return original_torch_load(*args, **kwargs)

            torch.load = legacy_torch_load
            try:
                self.plate_model = yolov5.load(str(model_path))
            finally:
                torch.load = original_torch_load
            self.plate_model.conf = plate_confidence

    @staticmethod
    def _odd_kernel(value: int) -> int:
        value = max(3, value)
        return value if value % 2 else value + 1

    def _blur_region(self, frame, x1: int, y1: int, x2: int, y2: int) -> None:
        height, width = frame.shape[:2]
        x1, x2 = sorted((max(0, x1), min(width, x2)))
        y1, y2 = sorted((max(0, y1), min(height, y2)))
        if x2 <= x1 or y2 <= y1:
            return

        region = frame[y1:y2, x1:x2]
        if region.size:
            frame[y1:y2, x1:x2] = cv2.GaussianBlur(
                region, (self.blur_kernel, self.blur_kernel), 0
            )

    def apply(self, frame):
        """Return a copy with every detected face and plate blurred."""
        private_frame = frame.copy()

        small = cv2.resize(
            private_frame,
            None,
            fx=self.detection_scale,
            fy=self.detection_scale,
            interpolation=cv2.INTER_AREA,
        )
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        restore = 1.0 / self.detection_scale
        faces = self.face_detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(12, 12)
        )
        for x, y, width, height in faces:
            self._blur_region(
                private_frame,
                int(x * restore),
                int(y * restore),
                int((x + width) * restore),
                int((y + height) * restore),
            )

        if self.plate_detector is not None:
            plates = self.plate_detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=3, minSize=(15, 5)
            )
            for x, y, width, height in plates:
                self._blur_region(
                    private_frame,
                    int(x * restore),
                    int(y * restore),
                    int((x + width) * restore),
                    int((y + height) * restore),
                )
        elif self.plate_model is not None:
            results = self.plate_model(private_frame)
            for detection in results.xyxy[0].cpu().numpy():
                x1, y1, x2, y2 = map(int, detection[:4])
                self._blur_region(private_frame, x1, y1, x2, y2)

        return private_frame
