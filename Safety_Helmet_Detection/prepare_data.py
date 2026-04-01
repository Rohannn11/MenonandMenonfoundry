import os
import shutil
import random
import xml.etree.ElementTree as ET

# Paths
BASE_DIR = '/Users/yugandharchawale/Desktop/Work/TY_Project_Foundry_Proj/Trial2'
VOC_DIR = os.path.join(BASE_DIR, 'VOC2028')
IMAGES_DIR = os.path.join(VOC_DIR, 'JPEGImages')
ANNO_DIR = os.path.join(VOC_DIR, 'Annotations')
SETS_DIR = os.path.join(VOC_DIR, 'ImageSets', 'Main')

YOLO_DIR = os.path.join(BASE_DIR, 'yolo_dataset')
os.makedirs(os.path.join(YOLO_DIR, 'images', 'train'), exist_ok=True)
os.makedirs(os.path.join(YOLO_DIR, 'images', 'val'), exist_ok=True)
os.makedirs(os.path.join(YOLO_DIR, 'labels', 'train'), exist_ok=True)
os.makedirs(os.path.join(YOLO_DIR, 'labels', 'val'), exist_ok=True)

# We map 'hat' or 'Helmet' to class 0. Some datasets also have 'person' or 'head' mapped to 1.
# Let's check common labels. If it's 'hat', we map -> 0.
CLASS_DICT = {'hat': 0, 'helmet': 0}

def convert_voc_to_yolo(xml_file, width, height):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Sometimes width/height in XML are 0 or missing, handle it
    size = root.find('size')
    w = int(size.find('width').text) if size is not None and size.find('width') is not None else width
    h = int(size.find('height').text) if size is not None and size.find('height') is not None else height
    
    yolo_lines = []
    
    for obj in root.iter('object'):
        name = obj.find('name').text.lower()
        if name not in CLASS_DICT:
            # For simplicity, if there's other classes, map them to class 1 (e.g. head, person)
            class_id = 1
        else:
            class_id = CLASS_DICT[name]
        
        xmlbox = obj.find('bndbox')
        if xmlbox is None: continue
        
        xmin = float(xmlbox.find('xmin').text)
        ymin = float(xmlbox.find('ymin').text)
        xmax = float(xmlbox.find('xmax').text)
        ymax = float(xmlbox.find('ymax').text)
        
        # YOLO format
        dw = 1.0 / float(w)
        dh = 1.0 / float(h)
        x_center = (xmin + xmax) / 2.0 - 1
        y_center = (ymin + ymax) / 2.0 - 1
        w_box = xmax - xmin
        h_box = ymax - ymin
        
        x_center = x_center * dw
        w_box = w_box * dw
        y_center = y_center * dh
        h_box = h_box * dh
        
        # Clamp to 0-1
        x_center = max(0.0, min(1.0, x_center))
        y_center = max(0.0, min(1.0, y_center))
        w_box = max(0.0, min(1.0, w_box))
        h_box = max(0.0, min(1.0, h_box))
        
        yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {w_box:.6f} {h_box:.6f}")
        
    return yolo_lines

def process_split(split, max_samples, split_name):
    split_file = os.path.join(SETS_DIR, f"{split}.txt")
    if not os.path.exists(split_file):
        print(f"Warning: {split_file} not found.")
        return

    with open(split_file, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        
    # shuffle and subset
    random.seed(42)
    random.shuffle(lines)
    subset = lines[:max_samples]
    
    print(f"Processing {split_name}: {len(subset)} samples...")
    for file_id in subset:
        # Check extensions
        if os.path.exists(os.path.join(IMAGES_DIR, f"{file_id}.jpg")):
            img_ext = ".jpg"
        elif os.path.exists(os.path.join(IMAGES_DIR, f"{file_id}.JPG")):
            img_ext = ".JPG"
        elif os.path.exists(os.path.join(IMAGES_DIR, f"{file_id}.png")):
            img_ext = ".png"
        else:
            continue
            
        src_img = os.path.join(IMAGES_DIR, f"{file_id}{img_ext}")
        src_xml = os.path.join(ANNO_DIR, f"{file_id}.xml")
        
        dst_img = os.path.join(YOLO_DIR, 'images', split_name, f"{file_id}.jpg")
        dst_txt = os.path.join(YOLO_DIR, 'labels', split_name, f"{file_id}.txt")
        
        if not os.path.exists(src_xml):
            continue
            
        shutil.copy2(src_img, dst_img)
        
        # To get proper w,h since PIL is slow, we might just rely on XML, 
        # But if XML has w=0 we have a problem. Let's do a fast read from XML itself
        yolo_lines = convert_voc_to_yolo(src_xml, 1920, 1080)
        
        with open(dst_txt, 'w') as f:
            f.write('\n'.join(yolo_lines))

if __name__ == '__main__':
    # Prepare subsets. Using ~15% for rapid training test
    process_split('train', 4000, 'train')
    process_split('val', 800, 'val')
    
    # Create dataset.yaml
    yaml_content = f"""path: {YOLO_DIR}
train: images/train
val: images/val

names:
  0: hat
  1: person
"""
    with open(os.path.join(YOLO_DIR, 'dataset.yaml'), 'w') as f:
        f.write(yaml_content)
        
    print("Dataset conversion completed.")
