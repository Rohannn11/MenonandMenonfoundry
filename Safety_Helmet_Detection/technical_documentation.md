# Safety Helmet Detection System: Technical Architecture and Implementation

## 1. Abstract
The Safety Helmet Detection System is an automated computer vision solution designed to enforce workplace safety compliance. By leveraging the state-of-the-art YOLO (You Only Look Once) object detection architecture, specifically the YOLOv11 Nano variant, the system identifies personnel and safety helmets in real-time. A spatial correlation algorithm is then applied to determine if detected individuals are properly wearing their helmets, raising automated alerts for compliance violations.

## 2. System Architecture

The project is structured into four primary logical components:
1. **Data Preprocessing & Conversion Pipeline** (`prepare_data.py`)
2. **Model Training Module** (`train_yolo.py`)
3. **Evaluation & Verification Module** (`evaluate.py`)
4. **Inference & Alerting Engine** (`inference_test.py`, `detect.py`, `inf_tst.py`)

### 2.1 Hardware and Framework Constraints
- **Deep Learning Framework:** Ultralytics YOLO (`ultralytics` package).
- **Core Model:** YOLOv11 Nano (`yolo11n.pt`), optimized for speed and real-time inference on edge devices.
- **Compute Acceleration:** Apple Metal Performance Shaders (MPS) for optimized execution on macOS (`device='mps'`), ensuring rapid training and inference without requiring discrete Nvidia GPUs.
- **Image Processing:** OpenCV (`cv2`) for video stream handling and real-time bounding box rendering.

## 3. Data Processing Methodology

The system utilizes the PASCAL VOC (Visual Object Classes) annotation format as its source base. The dataset undergoes a transformation process to meet YOLO’s normalized coordinate requirements.

### 3.1 Class Mapping and Normalization
The `prepare_data.py` script parses XML annotations (`xml.etree.ElementTree`) and maps categories to a binary class vector:
- Class `0`: `'hat'` or `'helmet'`
- Class `1`: `'person'` (or other unrecognized classes mapped securely to person/head).

### 3.2 Bounding Box Transformation
PASCAL VOC coordinates $(x_{min}, y_{min}, x_{max}, y_{max})$ are transformed into YOLO's normalized format $(x_{center}, y_{center}, width, height)$:
- $dw = 1.0 / Image_{width}$
- $dh = 1.0 / Image_{height}$
- $x_{center} = ((x_{min} + x_{max}) / 2.0 - 1) * dw$
- $y_{center} = ((y_{min} + y_{max}) / 2.0 - 1) * dh$

Coordinates are explicitly clamped between $0.0$ and $1.0$ to prevent out-of-bounds regression loss during training. Datasets are systematically split into training ($4000$ samples) and validation ($800$ samples) subsets with a deterministic seed to ensure reproducibility.

## 4. Model Training and Optimization

The `train_yolo.py` script orchestrates the fine-tuning of the pre-trained `yolo11n.pt` base model. 

**Hyperparameters and Configuration:**
- **Epochs:** 50
- **Image Size ($imgsz$):** 512x512 pixels
- **Batch Size:** 16
- **Compute Resource:** MPS (Metal Performance Shaders)
- **Project Name:** `helmet_detection` (Run: `yolo_nano_subset`)

By utilizing the nano variation of the model, the architecture strikes an optimal balance between parameter count and spatial precision, allowing for deployment on constrained hardware without a significant drop in Mean Average Precision (mAP).

## 5. Evaluation Metrics

Post-training performance is comprehensively quantified using `evaluate.py`. The system extracts and reports critical object detection metrics:
- **Precision (P) & Recall (R)**
- **F1 Score:** Calculated as $2 * (P * R) / (P + R)$, providing the harmonic mean of precision and recall.
- **mAP@0.50:** Mean Average Precision calculated at an Intersection over Union (IoU) threshold of 0.50.
- **mAP@0.50:0.95:** The strict COCO mAP spanning IoU thresholds from 0.50 to 0.95.

These metrics are resolved per class (`hat`, `person`) to ensure the model does not suffer from class imbalance bias.

## 6. Real-Time Inference and Alerting Engine

The core operational logic resides in `inference_test.py`. This component handles both static images and real-time video streams (`cv2.VideoCapture`).

### 6.1 Inference Thresholding
Model inference is executed with a strict confidence threshold of $0.60$ (`conf=0.60`) to minimize False Positives (FP) in industrial scenarios.

### 6.2 Spatial Correlation Logic
The presence of a hat and a person in a frame does not correlate to safety compliance. The system employs a spatial relationship algorithm to map hats to respective persons.
1. The model outputs decoupled bounding box arrays for `hat` and `person` classes.
2. For every detected `person`, the algorithm iterates through detected `hat` instances.
3. The geometric center of each hat $(hx_{center}, hy_{center})$ is calculated.
4. If the hat's geometric center falls entirely within the $(x_{min}, y_{min}, x_{max}, y_{max})$ boundaries of the person bounding box, the person is flagged as **Compliant** (`has_hat = True`).
5. An inverse accumulator tracks `missing_hat_count`. 

### 6.3 Automated Alerting
If `missing_hat_count > 0` post-frame analysis, the system explicitly raises standard output alerts (`🚨 ALERT: {N} PERSON(S) DETECTED WITHOUT SAFETY HELMET! 🚨`), which can be piped to downstream notification services or webhooks.

## 7. Conclusion
This architecture successfully demonstrates a robust, end-to-end pipeline for automated personal protective equipment (PPE) compliance monitoring. By integrating YOLOv11 Nano with spatial correlation heuristics, the system achieves real-time, highly accurate safety enforcement on standard commercial hardware.
