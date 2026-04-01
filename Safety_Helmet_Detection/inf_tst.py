import os
import cv2
from ultralytics import YOLO

def process_image(image_path, model_path):
    print(f"Loading model from {model_path}...")
    model = YOLO(model_path)
    
    print(f"Running inference on {image_path} with confidence threshold 0.60...")
    # Run inference on the source with confidence threshold 0.60
    results = model(image_path, conf=0.60)
    
    # Process results list
    for r in results:
        person_boxes = []
        hat_boxes = []
        
        # Extract bounding boxes for persons and hats
        for box, cls_id in zip(r.boxes.xyxy, r.boxes.cls):
            class_name = model.names[int(cls_id)]
            if class_name == 'person':
                person_boxes.append(box.tolist())
            elif class_name == 'hat':
                hat_boxes.append(box.tolist())
        
        # For each person, check if a hat box falls within their bounding box
        missing_hat_count = 0
        for pBox in person_boxes:
            has_hat = False
            for hBox in hat_boxes:
                # Calculate center of the hat box
                hx_center = (hBox[0] + hBox[2]) / 2
                hy_center = (hBox[1] + hBox[3]) / 2
                
                # Check if the hat center falls horizontally and vertically inside the person bounding box
                if pBox[0] <= hx_center <= pBox[2] and pBox[1] <= hy_center <= pBox[3]:
                    has_hat = True
                    break
            
            if not has_hat:
                missing_hat_count += 1
        
        if missing_hat_count > 0:
            print("\n" + "!"*60)
            print(f"🚨 ALERT: {missing_hat_count} PERSON(S) DETECTED WITHOUT SAFETY HELMET! 🚨")
            print("!"*60 + "\n")
        # Plot BGR numpy array of predictions
        im_array = r.plot() 
        
        # Display the image on screen
        cv2.imshow("Inference Output - Press any key to close", im_array)
        cv2.waitKey(0) # Wait for a key press
        cv2.destroyAllWindows()

def process_video(video_source, model_path):
    print(f"Loading model from {model_path}...")
    model = YOLO(model_path)
    
    print(f"Starting video stream from {video_source} with confidence threshold 0.60...")
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print(f"Error opening video stream or file: {video_source}")
        return
        
    alerted_person_ids = set()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Run inference and tracking on the frame
        results = model.track(frame, persist=True, conf=0.60, verbose=False)
        
        for r in results:
            person_boxes = []
            hat_boxes = []
            
            # Ensure tracking IDs are available
            boxes_id = r.boxes.id if r.boxes.id is not None else [None] * len(r.boxes.cls)
            
            # Extract bounding boxes for persons and hats
            for box, cls_id, trk_id in zip(r.boxes.xyxy, r.boxes.cls, boxes_id):
                class_name = model.names[int(cls_id)]
                if class_name == 'person':
                    person_boxes.append({
                        'box': box.tolist(), 
                        'id': int(trk_id) if trk_id is not None else None
                    })
                elif class_name == 'hat':
                    hat_boxes.append(box.tolist())
            
            # For each person, check if a hat box falls within their bounding box
            new_alerts = 0
            for p in person_boxes:
                pBox = p['box']
                pId = p['id']
                
                has_hat = False
                for hBox in hat_boxes:
                    hx_center = (hBox[0] + hBox[2]) / 2
                    hy_center = (hBox[1] + hBox[3]) / 2
                    if pBox[0] <= hx_center <= pBox[2] and pBox[1] <= hy_center <= pBox[3]:
                        has_hat = True
                        break
                
                if not has_hat:
                    if pId is not None:
                        # Only alert if we haven't alerted for this exact person ID yet
                        if pId not in alerted_person_ids:
                            alerted_person_ids.add(pId)
                            new_alerts += 1
                    else:
                        # Fallback if tracking ID somehow failed
                        new_alerts += 1
            
            if new_alerts > 0:
                print(f"🚨 ALERT: {new_alerts} NEW PERSON(S) DETECTED WITHOUT SAFETY HELMET! 🚨")
            
            # Draw predictions on frame
            frame = r.plot()
            
        # Display the frame in real-time
        cv2.imshow('Real-time Inference', frame)
        
        # Press 'q' on keyboard to exit the video window
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    weights_path = '/Users/yugandharchawale/Desktop/Work/TY_Project_Foundry_Proj/Trial2/runs/detect/helmet_detection/yolo_nano_subset5/weights/best.pt'
    
    # --- TEST IMAGE PROCESSING ---
    # input_image = '/Users/yugandharchawale/Desktop/Work/TY_Project_Foundry_Proj/Trial2/Test_Images/T4.jpeg'
    # input_video = '/Users/yugandharchawale/Desktop/Work/TY_Project_Foundry_Proj/Trial2/Test_Images/T_V_1.mov'
    # if os.path.exists(weights_path) and os.path.exists(input_image):
    #     process_image(input_image, weights_path)
    # else:
    #     print(f"Error: Could not find model weights or input image")
        
    # --- TEST REAL-TIME VIDEO PROCESSING (Uncomment to use) ---
    video_source = 0  # 0 for default webcam, or provide a path like 'Test_Video.mp4'
    if os.path.exists(weights_path):
        process_video(video_source, weights_path)
