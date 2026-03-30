from ultralytics import YOLO

# Load a model
model = YOLO('yolo11n.pt') 

# Train the model
results = model.train(
    data='/Users/yugandharchawale/Desktop/Work/TY_Project_Foundry_Proj/Trial2/yolo_dataset/dataset.yaml', 
    epochs=50, 
    imgsz=512,
    batch=16,
    device='mps',
    project='helmet_detection',
    name='yolo_nano_subset'
)


# Evaluate the model on the validation set
metrics = model.val()
print(f"mAP50-95: {metrics.box.map}")
print(f"mAP50: {metrics.box.map50}")
