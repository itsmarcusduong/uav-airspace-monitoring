| Tracker | IoU | ID switch / 1000 frame GT | ID switch | track recall (gộp) | trung vị độ phủ ID chính | video 1 ID | fragment | track giả | FPS trung vị |
|---|---|---|---|---|---|---|---|---|---|
| tracker_bytetrack_default | 0.5 | 8.962 | 104 | 0.8577 | 0.823 | 19/38 | 340 | 12 | 106.1 |
| tracker_bytetrack_default | 0.3 | 9.135 | 106 | 0.9499 | 0.9402 | 19/38 | 58 | 12 | 106.1 |
| tracker_botsort_default | 0.5 | 7.756 | 90 | 0.8592 | 0.7801 | 22/38 | 332 | 10 | 74.2 |
| tracker_botsort_default | 0.3 | 7.928 | 92 | 0.951 | 0.9708 | 22/38 | 54 | 10 | 74.2 |

Theo lớp (IoU 0,5): ID switch / 1000 frame GT, trung vị độ phủ ID chính

| Tracker | Airplane | Bird | Drone | Helicopter |
|---|---|---|---|---|
| tracker_bytetrack_default | 19.993 (0.505) | 0.0 (0.9877) | 6.72 (0.8567) | 4.293 (0.8961) |
| tracker_botsort_default | 15.784 (0.505) | 2.667 (0.9908) | 6.72 (0.7632) | 2.862 (1.0) |

Video nhiều ID switch nhất (IoU 0,5): V_AIRPLANE_047 tracker_bytetrack_default 28 IDSW / 2 ID; V_AIRPLANE_047 tracker_botsort_default 19 IDSW / 4 ID; V_DRONE_080 tracker_botsort_default 17 IDSW / 3 ID; V_DRONE_080 tracker_bytetrack_default 16 IDSW / 3 ID; V_AIRPLANE_007 tracker_bytetrack_default 13 IDSW / 7 ID

**Tham khảo (không phải cặp quyết định):** tracker_bytetrack_default — hoa (tuong doi 0.135 < 0.2) -> giu ByteTrack. Theo video (IoU 0,5): {'videos': 38, 'tracker_bytetrack_default_better': 3, 'tracker_botsort_default_better': 6, 'equal': 29}
