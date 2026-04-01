from ultralytics import YOLO

# Load the trained model
model = YOLO('/Users/yugandharchawale/Desktop/Work/TY_Project_Foundry_Proj/Trial2/runs/detect/helmet_detection/yolo_nano_subset5/weights/best.pt')

# Validate on the validation dataset
metrics = model.val(data='/Users/yugandharchawale/Desktop/Work/TY_Project_Foundry_Proj/Trial2/yolo_dataset/dataset.yaml')

print("\n" + "="*40)
print("=== FINAL EVALUATION METRICS ===")
print("="*40)

# Overall metrics
p = metrics.box.mp  # mean precision
r = metrics.box.mr  # mean recall
map50 = metrics.box.map50 # mean AP at IoU 0.50
map95 = metrics.box.map   # mean AP at IoU 0.50-0.95
f1 = 2 * (p * r) / (p + r) if (p + r) > 0 else 0

print(f"Overall Precision (~Accuracy): {p:.4f}")
print(f"Overall Recall:              {r:.4f}")
print(f"Overall F1 Score:            {f1:.4f}")
print(f"Overall mAP@50:              {map50:.4f}")
print(f"Overall mAP@50-95:           {map95:.4f}")

print("\n--- PER CLASS METRICS ---")
names = model.names
for i, c in enumerate(metrics.box.ap_class_index):
    name = names[c]
    cp = metrics.box.p[i]
    cr = metrics.box.r[i]
    cf1 = 2 * (cp * cr) / (cp + cr) if (cp + cr) > 0 else 0
    cmap = metrics.box.maps[i] # map50-95 per class (depends on YOLO version, normally map50-95 array)
    
    print(f"Class '{name}':")
    print(f"  Precision: {cp:.4f}")
    print(f"  Recall:    {cr:.4f}")
    print(f"  F1 Score:  {cf1:.4f}")
    print(f"  mAP@50-95: {cmap:.4f}")
print("="*40)
