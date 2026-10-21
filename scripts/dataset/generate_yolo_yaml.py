import os
import yaml

def generate_yaml():
    # Định nghĩa cấu hình dataset theo đúng chuẩn Ultralytics YOLO
    dataset_config = {
        'path': '.',   # thư mục gốc của dự án
        'train': 'data/splits/train_v1.csv',   # Hoặc đường dẫn thư mục ảnh train nếu đã trích xuất
        'val': 'data/splits/val_v1.csv',
        'test': 'data/splits/test_v1.csv',
        
        # Số lượng lớp và tên các lớp đã chốt ở W1-W2
        'nc': 4,
        'names': {
            0: 'drone',
            1: 'bird',
            2: 'airplane',
            3: 'helicopter'
        }
    }

    output_path = 'data/splits/dataset_yolo.yaml'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(dataset_config, f, sort_keys=False, allow_unicode=True)
        
    print(f"[SUCCESS] Đã tạo thành công file cấu hình YOLO tại: {output_path}")

if __name__ == "__main__":
    generate_yaml()