import os
import pandas as pd
import json

def run_eda():
    print("=== BẮT ĐẦU PHÂN TÍCH KHÁM PHÁ DỮ LIỆU (EDA) SVSANTROM ===")
    
    # 1. Đường dẫn tới metadata đã kiểm kê ở W1
    metadata_path = "resources/metadata/svanstrom_files.csv"
    if not os.path.exists(metadata_path):
        print(f"Không tìm thấy file metadata tại {metadata_path}. Vui lòng kiểm tra lại đường dẫn.")
        return

    df = pd.read_csv(metadata_path)
    
    # 2. Thống kê cơ bản
    total_files = len(df)
    print(f"Tổng số file/video trong archive: {total_files}")

    # Thống kê theo cảm biến (IR vs Visible nếu có cột tương ứng)
    if 'modality' in df.columns or 'type' in df.columns:
        col = 'modality' if 'modality' in df.columns else 'type'
        print("\n--- Phân bố theo loại cảm biến ---")
        print(df[col].value_counts())

    # 3. Thống kê phân bố lớp đối tượng (Dựa trên kết quả kiểm kê W1)
    # Các lớp đã chốt: Drone, Bird, Airplane, Helicopter
    class_stats = {
        "Drone": 271,
        "Bird": 130,
        "Airplane": 133,
        "Helicopter": 116
    }
    print("\n--- Phân bố số lượng chuỗi/video theo Class ---")
    for cls, count in class_stats.items():
        print(f"- {cls}: {count} videos")

    print("\n[INFO] Hoàn thành phân tích thống kê thô. Sẵn sàng xuất báo cáo EDA.")

if __name__ == "__main__":
    run_eda()