import os
from ultralytics import YOLO

def run_inference(image_path, model_path):
    print(f"Loading model from {model_path}...")
    model = YOLO(model_path)
    
    print(f"Running inference on {image_path}...")
    # Run inference and save the result image
    results = model(image_path, save=True, project='helmet_detection_inference', name='test_results')
    
    for r in results:
        boxes = r.boxes
        print(f"Detected {len(boxes)} objects")
        for box in boxes:
            class_id = int(box.cls[0])
            conf = float(box.conf[0])
            class_name = model.names[class_id]
            print(f"- {class_name}: {conf:.2f}")

if __name__ == '__main__':
    # Path to the best trained weights
    weights_path = '/Users/yugandharchawale/Desktop/Work/TY_Project_Foundry_Proj/Trial2/runs/detect/helmet_detection/yolo_nano_subset5/weights/best.pt'
    
    # Let's take a sample image from the validation set
    sample_image = '/Users/yugandharchawale/Desktop/Work/TY_Project_Foundry_Proj/Trial2/yolo_dataset/images/val/000000.jpg'
    
    # Using a fallback if that image doesn't exist
    if not os.path.exists(sample_image):
        val_dir = '/Users/yugandharchawale/Desktop/Work/TY_Project_Foundry_Proj/Trial2/yolo_dataset/images/val'
        if os.path.exists(val_dir) and len(os.listdir(val_dir)) > 0:
            sample_image = os.path.join(val_dir, os.listdir(val_dir)[0])
    
    if os.path.exists(weights_path) and os.path.exists(sample_image):
        run_inference(sample_image, weights_path)
    else:
        print("Model weights not ready yet or sample image missing. Wait for training to complete.")
