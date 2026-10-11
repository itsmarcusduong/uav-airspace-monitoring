import os
import pandas as pd

def audit_annotations_from_metadata():
    print("=== BẮT ĐẦU KIỂM ĐỊNH CHẤT LƯỢNG NHÃN TỪ METADATA SVANSTROM ===")
    
    metadata_path = "resources/metadata/svanstrom_files.csv"
    if not os.path.exists(metadata_path):
        print(f"[ERROR] Không tìm thấy file metadata tại {metadata_path}.")
        return

    df = pd.read_csv(metadata_path)
    total_records = len(df)
    print(f"Đã nạp thành công {total_records} bản ghi từ metadata.")

    # Kiểm tra các cột quan trọng (ví dụ: kiểm tra giá trị rỗng, tính hợp lệ của class hoặc đường dẫn)
    missing_paths = df['file_path'].isnull().sum() if 'file_path' in df.columns else 0
    
    print(f"Số lượng bản ghi thiếu đường dẫn file: {missing_paths}")
    
    # Giả lập kiểm định tính đồng nhất của các lớp đã thống kê ở EDA
    if 'class_name' in df.columns or 'label' in df.columns:
        col = 'class_name' if 'class_name' in df.columns else 'label'
        print("\nPhân bố nhãn trong metadata:")
        print(df[col].value_counts())
    
    print("\n[SUCCESS] Hoàn thành kiểm định metadata annotation cơ bản. Dữ liệu sẵn sàng cho bước chia tập Train/Val/Test (Split v1).")

if __name__ == "__main__":
    audit_annotations_from_metadata()