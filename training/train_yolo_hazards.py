"""
FreeDom Custom YOLOv8 Training Pipeline
Trains a custom object detection model (models/yolov8n.pt) on Indian footpath & road hazards:
  0: pothole
  1: broken_footpath_tile
  2: open_drain_manhole
  3: waterlogging
  4: footpath_encroachment
  5: missing_curb_ramp
"""
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "dataset_freedom_yolo"
MODELS_DIR = ROOT_DIR / "models"

CLASSES = [
    "pothole",
    "broken_footpath_tile",
    "open_drain_manhole",
    "waterlogging",
    "footpath_encroachment",
    "missing_curb_ramp",
]


def scaffold_yolo_dataset() -> Path:
    for split in ["train", "val"]:
        (DATASET_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    yaml_path = DATASET_DIR / "freedom_hazards.yaml"
    yaml_content = f"""path: {DATASET_DIR.as_posix()}
train: images/train
val: images/val

nc: {len(CLASSES)}
names:
""" + "".join(f"  {idx}: {name}\n" for idx, name in enumerate(CLASSES))

    yaml_path.write_text(yaml_content, encoding="utf-8")
    print(f"[OK] Dataset scaffold created at: {DATASET_DIR}")
    print(f"[OK] YOLO config written to:    {yaml_path}")
    return yaml_path


def train_freedom_yolov8(epochs: int = 50, imgsz: int = 640, batch: int = 16):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] Ultralytics not installed. Run: pip install ultralytics")
        return

    yaml_path = scaffold_yolo_dataset()
    train_imgs = list((DATASET_DIR / "images" / "train").glob("*.*"))
    if not train_imgs:
        print(
            "\n[INFO] No training images found yet!\n"
            f"1. Add annotated JPG/PNG images to: {DATASET_DIR / 'images' / 'train'} (and 'val')\n"
            f"2. Add YOLO .txt labels (class_id x_center y_center width height) to: {DATASET_DIR / 'labels' / 'train'}\n"
            "3. Re-run: python training/train_yolo_hazards.py\n"
        )
        return

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model = YOLO("yolov8n.pt")  # Pretrained COCO nano backbone
    results = model.train(
        data=str(yaml_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        project=str(ROOT_DIR / "runs"),
        name="freedom_yolo_v1",
        exist_ok=True,
    )

    best_weights = ROOT_DIR / "runs" / "freedom_yolo_v1" / "weights" / "best.pt"
    target_weights = MODELS_DIR / "yolov8n.pt"
    if best_weights.exists():
        shutil.copy2(best_weights, target_weights)
        print(f"\n[SUCCESS] Trained FreeDom YOLOv8 weights saved to: {target_weights}")
        print("Your Vision Auditor will now automatically load this custom model!")


if __name__ == "__main__":
    train_freedom_yolov8()
