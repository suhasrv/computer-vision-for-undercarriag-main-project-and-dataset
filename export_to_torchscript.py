from ultralytics import YOLO
model = YOLO("runs/weights/best.pt")
model.export(format="torchscript")