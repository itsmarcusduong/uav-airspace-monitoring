import os
import random
import pandas as pd
import json

def create_dataset_split():
    print("=== BẮT ĐẦU XÂY DỰNG KỊCH BẢN CHIA TẬP (TRAIN/VAL/TEST SPLIT) ===")
    
    metadata_path = "resources/metadata/svanstrom_files.csv"
    if not os.path.exists(metadata_path):
        print(f"[ERROR] Không tìm thấy file metadata tại {metadata_path}.")
        return

    df = pd.read_csv(metadata_path)
    
    # Đặt seed cố định để tái lập kết quả (Reproducibility)
    random.seed(20261010)
    
    # Kiểm tra xem metadata có cột phân loại class hay không để phân tầng
    class_col = None
    for col in ['class_name', 'label', 'category', 'class']:
        if col in df.columns:
            class_col = col
            break

    train_records, val_records, test_records = [], [], []

    if class_col:
        # Phân chia theo từng nhóm lớp để đảm bảo cân bằng tỷ lệ (Stratified split theo video)
        grouped = df.groupby(class_col)
        for cls_name, group in grouped:
            videos = group.to_dict('records')
            random.shuffle(videos)
            
            n_total = len(videos)
            n_train = int(0.70 * n_total)
            n_val = int(0.15 * n_total)
            
            train_records.extend(videos[:n_train])
            val_records.extend(videos[n_train:n_train + n_val])
            test_records.extend(videos[n_train + n_val:])
    else:
        # Nếu không tìm thấy cột class, chia ngẫu nhiên toàn bộ danh sách theo video
        videos = df.to_dict('records')
        random.shuffle(videos)
        n_total = len(videos)
        n_train = int(0.70 * n_total)
        n_val = int(0.15 * n_total)
        
        train_records = videos[:n_train]
        val_records = videos[n_train:n_train + n_val]
        test_records = videos[n_train + n_val:]

    # Tạo thư mục lưu kết quả split nếu chưa có
    os.makedirs("data/splits", exist_ok=True)
    
    # Lưu danh sách file/video tương ứng vào các tệp manifest/txt
    split_summary = {
        "train_count": len(train_records),
        "val_count": len(val_records),
        "test_count": len(test_records),
        "total": len(df),
        "split_ratio": "70/15/15",
        "method": "Video-based Group Split (Anti Data Leakage)"
    }
    
    # Xuất file JSON manifest cho split
    manifest_path = "data/splits/split_v1_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(split_summary, f, indent=4, ensure_ascii=False)

    # Lưu danh sách file cho từng tập (phục vụ training ở W3 và đóng băng test set cho W11)
    pd.DataFrame(train_records).to_csv("data/splits/train_v1.csv", index=False)
    pd.DataFrame(val_records).to_csv("data/splits/val_v1.csv", index=False)
    pd.DataFrame(test_records).to_csv("data/splits/test_v1.csv", index=False)

    print("Phân chia dữ liệu hoàn tất:")
    print(f"  - Tập Train (70%): {len(train_records)} chuỗi")
    print(f"  - Tập Validation (15%): {len(val_records)} chuỗi")
    print(f"  - Tập Test (15% - Frozen): {len(test_records)} chuỗi")
    print(f"Đã lưu các file phân chia và manifest tại thư mục: data/splits/")
    print("[SUCCESS] Hoàn thành Tuần 2: EDA, Annotation Audit và Split v1 thành công!")

if __name__ == "__main__":
    create_dataset_split()