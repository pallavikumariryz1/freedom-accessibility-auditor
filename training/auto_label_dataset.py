import random
import shutil
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_IMAGES_DIR = PROJECT_ROOT / "raw_images"
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"
DATASET_DIR = PROJECT_ROOT / "dataset_freedom_yolo"

CLASSES = [
    "pothole",               # 0
    "broken_footpath_tile",  # 1
    "open_drain_manhole",    # 2
    "waterlogging",          # 3
    "footpath_encroachment", # 4
    "missing_curb_ramp",     # 5
]


def setup_directories() -> None:
    RAW_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val"):
        (DATASET_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    yaml_lines = [
        f"path: {DATASET_DIR.as_posix()}",
        "train: images/train",
        "val: images/val",
        f"nc: {len(CLASSES)}",
        "names:",
    ]
    for idx, name in enumerate(CLASSES):
        yaml_lines.append(f"  {idx}: {name}")

    yaml_path = DATASET_DIR / "freedom_hazards.yaml"
    yaml_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")


def generate_pseudo_labels(img_bgr: np.ndarray) -> List[Tuple[int, float, float, float, float]]:
    h, w, _ = img_bgr.shape
    labels: List[Tuple[int, float, float, float, float]] = []

    # 1. Use pretrained YOLOv8n if available to auto-label footpath encroachments (parked cars/bikes/carts)
    try:
        from ultralytics import YOLO

        base_model = YOLO("yolov8n.pt")
        preds = base_model.predict(img_bgr, conf=0.35, verbose=False)
        encroachment_coco_ids = {1, 2, 3, 5, 7}  # bicycle, car, motorcycle, bus, truck
        for res in preds:
            if res.boxes is None:
                continue
            for box in res.boxes:
                cls_id = int(box.cls.item())
                if cls_id in encroachment_coco_ids:
                    x1, y1, x2, y2 = box.xyxy.tolist()
                    xc = ((x1 + x2) / 2.0) / w
                    yc = ((y1 + y2) / 2.0) / h
                    bw = (x2 - x1) / w
                    bh = (y2 - y1) / h
                    labels.append((4, round(xc, 6), round(yc, 6), round(bw, 6), round(bh, 6)))
    except Exception:
        pass

    # 2. Structural OpenCV detector for potholes (0), waterlogging (3), and broken tiles/cracks (1)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blurred, 45, 135)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = (w * h) * 0.01
    max_area = (w * h) * 0.70

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)
        roi_gray = gray[y : y + bh, x : x + bw]
        roi_sat = hsv[y : y + bh, x : x + bw, 1]
        mean_val = float(np.mean(roi_gray)) if roi_gray.size > 0 else 128.0
        mean_sat = float(np.mean(roi_sat)) if roi_sat.size > 0 else 50.0
        area_ratio = area / float(w * h)

        if mean_sat < 42 and area_ratio > 0.05 and mean_val > 110:
            class_id = 3  # waterlogging
        elif area_ratio > 0.045 or mean_val < 78:
            class_id = 0  # pothole
        else:
            class_id = 1  # broken_footpath_tile

        xc = (x + bw / 2.0) / w
        yc = (y + bh / 2.0) / h
        nw = bw / float(w)
        nh = bh / float(h)
        labels.append((class_id, round(xc, 6), round(yc, 6), round(nw, 6), round(nh, 6)))

    return labels[:8]


def build_dataset() -> None:
    setup_directories()

    image_paths: List[Path] = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        image_paths.extend(RAW_IMAGES_DIR.glob(ext))
    if UPLOADS_DIR.exists():
        image_paths.extend(UPLOADS_DIR.glob("*_original.jpg"))

    if not image_paths:
        print(f"No images found yet. Place road/footpath photos inside '{RAW_IMAGES_DIR}' and re-run.")
        return

    random.shuffle(image_paths)
    split_idx = max(1, int(len(image_paths) * 0.8)) if len(image_paths) > 1 else 1

    labeled_count = 0
    for idx, img_path in enumerate(image_paths):
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        split = "train" if idx < split_idx else "val"
        if len(image_paths) == 1:
            split = "train"

        stem = f"freedom_{idx:04d}_{img_path.stem}"
        out_img = DATASET_DIR / "images" / split / f"{stem}.jpg"
        out_lbl = DATASET_DIR / "labels" / split / f"{stem}.txt"

        cv2.imwrite(str(out_img), img)
        boxes = generate_pseudo_labels(img)
        lines = [f"{c} {xc} {yc} {bw} {bh}" for c, xc, yc, bw, bh in boxes]
        out_lbl.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

        if len(image_paths) == 1:
            val_img = DATASET_DIR / "images" / "val" / f"{stem}.jpg"
            val_lbl = DATASET_DIR / "labels" / "val" / f"{stem}.txt"
            shutil.copy2(out_img, val_img)
            shutil.copy2(out_lbl, val_lbl)

        labeled_count += 1

    print(f"Auto-labeled {labeled_count} images into '{DATASET_DIR}'.")
    print(f"Dataset YAML ready at: '{DATASET_DIR / 'freedom_hazards.yaml'}'")


if __name__ == "__main__":
    build_dataset()
