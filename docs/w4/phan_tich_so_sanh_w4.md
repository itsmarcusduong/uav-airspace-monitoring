# Phân tích bảng so sánh W4

## Phạm vi và cách đọc

Bảng dùng chung dữ liệu `e1-yolo-v1` (fingerprint bắt đầu `d0ac7e230b385132`), cùng seed, Ultralytics 8.4.183 và GPU Tesla T4; các lần train có ngân sách tối đa 50 epoch và patience 15. Toàn bộ kết quả là trên validation: tập này đã dùng để dừng sớm, chọn checkpoint và chọn ngưỡng, nên các số có thể lạc quan; test vẫn khóa. Nguồn: `results/W04/comparison_w4.csv`, `results/W04/kaggle_run_09/phien_1/train_yolo11n_640/env.json`, `results/W04/kaggle_run_09/phien_2/train_detector_B/env.json`, `results/W04/kaggle_run_09/phien_3/train_rtdetr_l_640/env.json`, `docs/decisions/ADR-0007-w4-model-selection.md`.

Hai hình và bảng nguồn:

- Độ chính xác – thời gian: `![Độ chính xác so với độ trễ](../../results/W04/fig_w4_accuracy_vs_latency.png)`. Số liệu nền của hình: `results/W04/comparison_w4.csv`.
- AP@0.5 theo lớp: `![AP@0.5 theo lớp](../../results/W04/fig_w4_ap_by_class.png)`. Số liệu nền của hình: `results/W04/comparison_w4.csv`.
- Bảng đầy đủ: `results/W04/comparison_w4.md` và `results/W04/comparison_w4.csv`.

## So sánh theo lớp

AP@0.5 theo lớp (cao hơn là tốt hơn). RT-DETR được giữ trong bảng để minh bạch số đã ghi, nhưng **không hợp lệ** do loss NaN trong lúc train; không xếp hạng hoặc diễn giải nó như kết quả năng lực của mô hình. Nguồn tất cả ô: `results/W04/comparison_w4.csv` (các cột `ap50_*`); trạng thái train: cột `train_health` trong cùng file.

| Lớp | baseline_A | baseline_A_aug | baseline_A_960 | yolo11n_640 | detector_B | rtdetr_l_640* |
|---|---:|---:|---:|---:|---:|---:|
| Airplane | 0,677 | 0,551 | 0,715 | 0,716 | **0,756** | 0,618 |
| Bird | **0,865** | 0,745 | 0,638 | 0,863 | 0,671 | 0,374 |
| Drone | 0,809 | 0,795 | 0,742 | **0,842** | 0,713 | 0,738 |
| Helicopter | 0,879 | 0,865 | 0,798 | 0,902 | **0,932** | 0,908 |

`detector_B` nổi bật ở Helicopter và Airplane, nhưng AP@0.5 Drone thấp nhất trong các lần train hợp lệ. Với B, AP@0.5 Drone là 0,713 trong khi AP@0.5:0.95 Drone là 0,229; điều này phù hợp với định vị hộp Drone kém ổn định ở các ngưỡng IoU cao hơn. Nguồn: `results/W04/comparison_w4.csv` (`ap50_Drone`, `source`); chi tiết B: `results/W04/kaggle_run_09/phien_2/train_detector_B/detector_B_val_metrics.json` và `detector_B_val_per_class.csv`.

So sánh B với `baseline_A_960` (cùng imgsz 960 theo ma trận thử nghiệm) cho thấy AP@0.5 của B tăng ở Airplane (0,715 → 0,756), Bird (0,638 → 0,671) và Helicopter (0,798 → 0,932), nhưng giảm ở Drone (0,742 → 0,713). Tuy nhiên, mAP@0.5:0.95 chỉ tăng từ 0,323 lên 0,326 — nhỏ hơn mức nhiễu validation nêu dưới đây. Nguồn: `results/W04/comparison_w4.csv`; giao thức xác định B và A_960 là cặp đối chiếu cỡ mô hình: `docs/w4/training_protocol_w4.md`, mục 4.

## Recall theo cỡ hộp

Recall tổng hợp ở ngưỡng vận hành đã chọn trên validation cho từng run. Mỗi ô là recall (TP/GT); mẫu số tương ứng là 475 hộp nhỏ, 574 hộp vừa và 113 hộp lớn. Bốn run trong W4 lấy từ `results/W04/kaggle_run_09/phien_1/analysis_*/recall_by_size.csv` và `results/W04/kaggle_run_09/phien_2/analysis_detector_B/recall_by_size.csv`; baseline A lấy từ `results/W03/kaggle_run_05/analysis/recall_by_size.csv`.

| Mô hình | Nhỏ (<32²) | Vừa (32²–96²) | Lớn (≥96²) | Nguồn |
|---|---:|---:|---:|---|
| baseline_A | 0,863 (410/475) | 0,803 (461/574) | 0,903 (102/113) | `results/W03/kaggle_run_05/analysis/recall_by_size.csv` |
| baseline_A_aug | 0,800 (380/475) | 0,671 (385/574) | 0,823 (93/113) | `results/W04/kaggle_run_09/phien_1/analysis_baseline_A_aug/recall_by_size.csv` |
| baseline_A_960 | 0,855 (406/475) | 0,707 (406/574) | 0,965 (109/113) | `results/W04/kaggle_run_09/phien_1/analysis_baseline_A_960/recall_by_size.csv` |
| yolo11n_640 | **0,882 (419/475)** | **0,772 (443/574)** | 0,858 (97/113) | `results/W04/kaggle_run_09/phien_1/analysis_yolo11n_640/recall_by_size.csv` |
| detector_B | 0,859 (408/475) | 0,723 (415/574) | **0,982 (111/113)** | `results/W04/kaggle_run_09/phien_2/analysis_detector_B/recall_by_size.csv` |
| rtdetr_l_640* | 0,806 (383/475) | 0,733 (421/574) | 0,982 (111/113) | `results/W04/kaggle_run_09/phien_3/analysis_rtdetr_l_640/recall_by_size.csv` |

*Run RT-DETR không hợp lệ, nên không dùng các recall này để kết luận.*

Ở B, recall hộp nhỏ là 0,859, thấp hơn một chút so với baseline A (0,863) và yolo11n_640 (0,882); recall hộp lớn cao nhưng chỉ dựa trên 113 hộp GT. Theo lớp, B phát hiện 235/263 Drone nhỏ (0,894) nhưng 186/252 Drone vừa (0,738); Airplane vừa là điểm yếu nhất với 86/174 (0,494). Nguồn: `results/W04/kaggle_run_09/phien_2/analysis_detector_B/recall_by_size.csv`.

## Từng video và nhầm lớp của detector B

Kết quả B tại ngưỡng vận hành `conf=0,30` được chọn để tối đa F1 Drone trên validation (hòa thì lấy ngưỡng cao hơn). Drone P/R/F1 là 0,743/0,818/0,778; F1 macro là 0,780. Nguồn: `results/W04/kaggle_run_09/phien_2/analysis_detector_B/analysis_summary.json` (`operating_points`) và `operating_points.csv`.

Recall Airplane thay đổi rõ theo video: `V_AIRPLANE_027` đạt 0/33 (0,000), `V_AIRPLANE_005` đạt 10/33 (0,303), trong khi `V_AIRPLANE_030` đạt 32/32 (1,000). Vì vậy kết quả gộp theo lớp hoặc cỡ hộp che khuất khác biệt cảnh/video; không nên quy toàn bộ lỗi Airplane cho kích thước hộp. Nguồn: `results/W04/kaggle_run_09/phien_2/analysis_detector_B/recall_by_video.csv`.

Ma trận nhầm lớp của B ghi nhận bỏ sót 80 Airplane, 1 Bird, 91 Drone và 25 Helicopter. Nhầm chéo lớn nhất là Airplane → Drone (23); các trường hợp còn lại gồm Airplane → Helicopter (9), Airplane → Bird (4), Drone → Airplane (3), Drone → Bird (3), Helicopter → Airplane (3). Đây là số đếm tại `conf=0,30`, không phải tỷ lệ độc lập với thành phần dữ liệu. Nguồn: `results/W04/kaggle_run_09/phien_2/analysis_detector_B/class_confusion.csv`; ngưỡng: `analysis_summary.json`.

Có 39/40 ảnh được đánh dấu không có hộp trong tập phân tích B có dự đoán tại `conf=0,30`. Không diễn giải con số này thành 39 false positive trên nền trống: các ảnh không hộp không được xác nhận là cảnh âm tính thật, và frame ngoài phạm vi nhãn là UNKNOWN theo audit dữ liệu. Nguồn: `results/W04/kaggle_run_09/phien_2/analysis_detector_B/negatives_fp.json`; giới hạn dữ liệu: `docs/w2/annotation_audit_w2.md`.

## Đánh đổi độ chính xác – thời gian

| Mô hình | mAP@0.5:0.95 | ms/ảnh | Độ lệch chuẩn mAP@0.5:0.95 giữa epoch | Train |
|---|---:|---:|---:|---|
| baseline_A | 0,342 | 3,26 | 0,0277 | OK |
| baseline_A_aug | 0,331 | 3,14 | 0,0312 | OK |
| baseline_A_960 | 0,323 | 6,86 | 0,0269 | OK |
| yolo11n_640 | **0,347** | 3,28 | 0,0361 | OK |
| detector_B | 0,326 | 20,82 | 0,0196 | OK |
| rtdetr_l_640* | 0,277 | 42,74 | 0,0000 | **INVALID: loss NaN** |

Nguồn tất cả số: `results/W04/comparison_w4.csv` (các cột `map50_95`, `inference_ms`, `val_map50_95_epoch_sd`, `train_health`).

- Thời gian là inference trong bước validation theo batch trên T4, không phải FPS pipeline; nguồn: `results/W04/comparison_w4.csv` và `results/W04/kaggle_run_09/phien_2/train_detector_B/detector_B_val_metrics.json`.
- B đạt 0,326 mAP@0.5:0.95 nhưng tốn 20,82 ms/ảnh, so với 3,26 ms/ảnh của A; lợi thế so với A_960 chỉ là 0,003 mAP@0.5:0.95 trong khi thời gian tăng từ 6,86 lên 20,82 ms/ảnh. Nguồn: `results/W04/comparison_w4.csv`.
- Bảng ghi nhận độ lệch chuẩn theo epoch khoảng 0,020–0,036 ở các lần train hợp lệ (chính xác 0,0196–0,0361); đây là độ dao động giữa epoch, **không phải** khoảng tin cậy giữa nhiều seed. Với validation dùng cả để chọn checkpoint, chênh lệch mAP@0.5:0.95 dưới khoảng 0,02 không nên xem là bằng chứng mô hình khác nhau thật. Nguồn: `results/W04/comparison_w4.csv`; cách diễn giải cũng được ghi tại `docs/decisions/ADR-0007-w4-model-selection.md`.
- **RT-DETR không hợp lệ:** train health là INVALID do loss NaN từ epoch 3. Các metric bảng lưu không đại diện cho năng lực RT-DETR và không được dùng xếp hạng. Nguồn: `results/W04/comparison_w4.csv`, `results/W04/kaggle_run_09/phien_3/train_rtdetr_l_640/train/results.csv`, `docs/decisions/ADR-0007-w4-model-selection.md`.
- **imgsz 960 không đem lại cải thiện tổng thể** trong đối chứng YOLOv8n: A_960 đạt 0,323 mAP@0.5:0.95 so với A ở 0,342, trong khi inference tăng từ 3,26 lên 6,86 ms/ảnh. Ảnh Visible gốc là 640×512; imgsz 960 phóng to ảnh, không thêm chi tiết nguồn. Nguồn kết quả: `results/W04/comparison_w4.csv`; độ phân giải: `docs/w2/annotation_audit_w2.md` và `docs/decisions/ADR-0007-w4-model-selection.md`.

## Kết luận

`yolo11n_640` có mAP@0.5:0.95 cao nhất trong các lần train hợp lệ (0,347), nhưng cách A chỉ 0,005; mức chênh này nhỏ hơn quy tắc nhiễu khoảng 0,02. A nhanh hơn một chút trong phép đo đơn lẻ (3,26 so với 3,28 ms/ảnh), nhưng khác biệt tốc độ cũng rất nhỏ. Theo luật chọn đã đặt trước, ADR-0007 giữ baseline A cho W5 và ưu tiên xử lý dữ liệu trước khi thử mô hình lớn hơn. B không có lợi thế rõ về chất lượng tổng thể để bù thời gian suy luận cao; điểm mạnh theo lớp của B là Helicopter/Airplane, điểm yếu là Drone và Airplane cỡ vừa. Nguồn: `results/W04/comparison_w4.csv`, `results/W04/kaggle_run_09/phien_2/analysis_detector_B/recall_by_size.csv`, `docs/decisions/ADR-0007-w4-model-selection.md`.

Các kết quả chỉ áp dụng cho validation `e1-yolo-v1`, một lần chạy/seed và điều kiện đo đã ghi; không phải kết quả test độc lập hay thông số FPS của pipeline. Xem giới hạn dữ liệu và quyết định chọn model trong `docs/decisions/ADR-0007-w4-model-selection.md`.
