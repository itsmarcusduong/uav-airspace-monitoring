| Detector | Lớp | ID switch / 1000 frame GT | ID switch | Track recall | Trung vị độ phủ ID chính | Video 1 ID | Đứt track |
|---|---|---|---|---|---|---|---|
| baseline_A | all | 8.962 | 104 | 0.8577 | 0.823 | 19/38 | 340 |
| yolo11n_s20261030 | all | 18.011 | 209 | 0.8425 | 0.7534 | 12/38 | 295 |
| baseline_A | Airplane | 19.993 | 57 | 0.7671 | 0.505 | 1/9 | 58 |
| yolo11n_s20261030 | Airplane | 17.538 | 50 | 0.7941 | 0.48 | 0/9 | 52 |
| baseline_A | Bird | 0.0 | 0 | 0.988 | 0.9877 | 3/3 | 4 |
| yolo11n_s20261030 | Bird | 2.667 | 2 | 0.7867 | 0.978 | 2/3 | 6 |
| baseline_A | Drone | 6.72 | 35 | 0.8752 | 0.8567 | 11/17 | 234 |
| yolo11n_s20261030 | Drone | 24.002 | 125 | 0.8763 | 0.8317 | 7/17 | 200 |
| baseline_A | Helicopter | 4.293 | 12 | 0.8826 | 0.8961 | 4/9 | 44 |
| yolo11n_s20261030 | Helicopter | 11.449 | 32 | 0.8436 | 0.9286 | 3/9 | 37 |

Theo video: yolo11n_s20261030 nhiều ID switch hơn ở 16 video, ít hơn ở 7, bằng ở 15. Frame có hai track chồng nhau (IoU ≥ 0,3): {'baseline_A': {'videos': 15, 'frames': 416}, 'yolo11n_s20261030': {'videos': 25, 'frames': 2012}}.
