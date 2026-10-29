# ADR-0007: Chọn detector cho W5 theo luật đặt trước (kết quả run 09)

- Trạng thái: **Accepted** (Quang 28/10/2026, An 29/10/2026).
- Liên quan: #39, #40, #48; giao thức `docs/w4/training_protocol_w4.md` mục 4 (luật đặt trước, commit `2ae4c50`, PR #51, 27/10/2026, trước khi có kết quả); ADR-0005 (chỉ tiêu ≥ 15 FPS); ADR-0006 (dữ liệu `e1-yolo-v1`).

## Bối cảnh
- [Kết quả đo] 5 mô hình mới chạy bằng `w4_run09_train_compare.ipynb` (commit `1a71f5b`), cộng với baseline A của W3 (run 04, commit `9597fce`).
  - Cả 6 mô hình dùng cùng dữ liệu `e1-yolo-v1` (fingerprint `d0ac7e230b385132…`), cùng Ultralytics 8.4.183, torch 2.11.0, Tesla T4, cùng seed, 50 epoch / patience 15.
  - Phiên 1 và 2 Quang chạy; phiên 3 (RT-DETR) An chạy trên tài khoản Kaggle của An.
  - Nguồn: `results/W04/comparison_w4.csv` (tạo bằng `scripts/reporting/build_comparison.py`), bằng chứng gốc `results/W04/kaggle_run_09/phien_{1,2,3}/`. Weights có SHA-256 và link Drive trong `train_*/weights_manifest.json`.
- Mọi số đo trên **val**. Val được dùng để dừng sớm, chọn checkpoint và chọn ngưỡng, nên các số này lạc quan. Test vẫn khóa.

| Mô hình | imgsz | mAP@0.5 | mAP@0.5:0.95 | AP@0.5:0.95 Drone | F1 Drone @ngưỡng | recall hộp nhỏ | ms/ảnh | Train |
|---|---|---|---|---|---|---|---|---|
| baseline_A (YOLOv8n) | 640 | 0.807 | 0.342 | 0.266 | 0.856 | 0.863 | 3.26 | OK |
| baseline_A_aug (scale 0.3) | 640 | 0.739 | 0.331 | 0.249 | 0.807 | 0.800 | 3.14 | OK |
| baseline_A_960 | 960 | 0.723 | 0.323 | 0.248 | 0.815 | 0.855 | 6.86 | OK |
| yolo11n_640 | 640 | 0.831 | 0.347 | 0.277 | 0.880 | 0.882 | 3.28 | OK |
| detector_B (YOLOv8s) | 960 | 0.768 | 0.326 | 0.229 | 0.778 | 0.859 | 20.82 | OK |
| rtdetr_l_640 | 640 | 0.659 | 0.277 | 0.226 | 0.798 | 0.806 | 42.74 | **INVALID** (loss NaN từ epoch 3) |

## Áp dụng luật (đặt trước, không sửa sau khi xem kết quả)
1. **Ràng buộc tốc độ ≤ 25 ms/ảnh:** loại `rtdetr_l_640` (42,7 ms). Mô hình này cũng bị loại vì train lỗi (xem dưới).
2. **mAP@0.5:0.95 cao nhất:** `yolo11n_640` đạt 0,3470; đứng sau là `baseline_A` 0,3421.
3. **Hòa:** chênh 0,0049 < 0,01 nên coi là hòa. Luật nói khi hòa thì chọn mô hình nhanh hơn: `baseline_A` 3,257 ms so với `yolo11n_640` 3,281 ms.

**[DECISION] Theo đúng luật: giữ `baseline_A` (YOLOv8n @640, weights W03) làm detector cho W5 (tích hợp tracker).**

Ghi chú trung thực về cách áp luật:
- Hai mô hình chỉ chênh 0,024 ms/ảnh (0,7%). Mức này nằm trong sai số của một lần đo, và luật không định nghĩa "hòa về tốc độ". Nếu coi tốc độ cũng hòa, tiêu chí phụ (F1 Drone) sẽ chọn `yolo11n_640` (0,880 so với 0,856).
- ADR này **không** đổi luật sau khi đã xem số. Kết luận chỉ là: hai mô hình ngang nhau trong phạm vi một seed. Đổi detector chỉ là thay file weights, không đổi giao diện detector → tracker, nên W5 không bị chặn bởi lựa chọn này.
- Trước khi đóng băng tính năng (W11) phải chạy ≥ 3 seed cho cả `baseline_A` và `yolo11n_640` (hoặc bootstrap theo video) rồi chọn lại theo cùng luật. Việc này cần lập issue W5.

## Luật 4: ưu tiên cải thiện dữ liệu
Luật 4 bị kích hoạt: không mô hình nào cải thiện rõ trên lớp Drone.
- AP@0.5:0.95 lớp Drone của mọi mô hình nằm trong khoảng 0,23–0,28.
- Recall hộp nhỏ chỉ `yolo11n_640` cao hơn A (0,882 so với 0,863), và mức chênh này nhỏ hơn độ nhiễu của val (mục dưới).

[DECISION] Không thử mô hình lớn hơn trước khi cải thiện dữ liệu. Ưu tiên cho W7:
1. Chiều lệch nhãn. ADR-0006 hiện là UNDETERMINED, nhưng hai phương pháp độc lập cùng nghiêng về offset1 cho Drone dư 1 mục. Cần lập ADR mới có luật đặt trước.
2. Sửa hoặc loại các video `SAI_NHAN`, sau khi An và Quang thống nhất tiêu chí review (`results/W04/review_v2_agreement.json`).
3. Độ rộng hộp nhãn. Tập chuẩn CVAT cho thấy hộp nhãn gốc có diện tích khoảng gấp 3 hộp sát vật (`results/W04/cvat_gold/scoring/gold_score.json`). [INFERENCE] Độ rộng không đồng đều kéo AP ở IoU cao xuống; cần đo độ biến thiên tỷ lệ hộp/vật trước khi sửa.
4. Ảnh nền trống và hard negative (đúng kế hoạch W7).

## Các phát hiện khác [Kết quả đo] và [INFERENCE]
- **Độ phân giải 960 không giúp gì.** `baseline_A_960` đạt 0,323, thấp hơn A (0,342), và chậm gấp 2,1 lần. Mọi ảnh trong `e1-yolo-v1` đều có kích thước gốc 640×512 (`yolo_manifest.csv.gz`), nên imgsz 960 chỉ là phóng to ảnh, không thêm chi tiết. [INFERENCE] Muốn tăng độ phân giải thực cho vật nhỏ thì phải dùng nguồn ảnh có độ phân giải cao hơn, không phải tăng imgsz.
- **Cỡ model:** `detector_B` (YOLOv8s @960) đạt 0,326, tương đương `baseline_A_960` (0,323) khi chỉ đổi cỡ model. Helicopter tốt nhất (AP@0.5 0,932) nhưng Drone kém nhất (0,713), lại chậm 20,8 ms.
- **Augmentation `scale: 0.3`:** 0,331, thấp hơn A 0,011 (vượt ngưỡng hòa). AP@0.5 Bird và Airplane giảm rõ. Checkpoint tốt nhất ở epoch 9, dừng sớm ở epoch 24. Không giữ thay đổi này.
- **RT-DETR-l: không hợp lệ.**
  - Loss thành NaN ở epoch 3 (cuối warmup, lr ≈ 1,2·10⁻³, `amp: true`). Từ đó val mAP bằng 0, và checkpoint "tốt nhất" là epoch 2, gần như vẫn là trọng số COCO.
  - Số trong bảng **không** phản ánh năng lực của RT-DETR.
  - Không chạy lại để chọn mô hình vì RT-DETR-l đã vượt ràng buộc 25 ms. Nếu cần cho phần so sánh trong thuyết minh, chạy lại với `amp: false`, `optimizer: AdamW`, `lr0: 1e-4`. Đây là thay đổi config, phải ghi vào giao thức.
- **Độ nhiễu của val.** Độ lệch chuẩn mAP@0.5:0.95 giữa các epoch (bỏ 5 epoch đầu) là 0,020–0,036 tùy mô hình (cột `val_map50_95_epoch_sd`). Val chỉ có 98 video, và chọn "epoch tốt nhất" trên val là lấy max của một đường cong nhiễu. Vì vậy chênh lệch dưới khoảng 0,02 giữa các mô hình không nên diễn giải là khác biệt thật.

## Hệ quả
- W5: tracker (ByteTrack chính, BoT-SORT đối chứng, ADR-0005) dùng `baseline_A` best.pt của W03 (`results/W03/kaggle_run_04/train_evidence/weights_manifest.json`).
- #40 (An): viết phân tích bảng so sánh và model card cho detector B dựa trên bảng này. Phần phân tích phải nói rõ RT-DETR không hợp lệ và val nhiễu.
- Lập issue W5 (#59): chạy 3 seed cho A và YOLO11n (Kaggle run 13), chọn lại theo luật nhiều seed ghi trước ở `docs/w4/training_protocol_w4.md` mục 6 (29/10/2026). Mục 6 định nghĩa thêm "hòa về tốc độ" (< 10%) và tiêu chí phụ F1 Drone. Kết quả sẽ ghi vào bản cập nhật của ADR này.
- #37 đóng: không xuất `e1-yolo-v2` trong W4 (ADR-0006).
