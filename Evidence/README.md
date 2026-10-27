# Evidence theo tuần

Cấu trúc thống nhất theo yêu cầu của GVHD (áp dụng từ W4, bổ sung lại W01–W03 từ bằng chứng đã có):

```
Evidence/WXX/
├── README.md        # phạm vi tuần, liên kết Issue/PR/tag, danh sách hình, artefact ngoài Git
├── metrics.csv      # week, metric, value, unit, split, model, source, producer, run_commit
├── test-results.*   # test-results.json (kiểm tra dữ liệu/run chạy lại lúc tạo) + test-results.xml (pytest, JUnit)
├── figures/         # hình dùng trong báo cáo tuần
└── manifest.json    # SHA-256 của mọi tệp trong thư mục và của tệp nguồn
```

Tạo lại toàn bộ (không nhập tay số liệu; mọi số đọc từ `results/`, `data/`, `docs/`):

```
python -m pip install -r requirements-dev.txt
python -m pytest -q tests --junitxml=junit.xml
python scripts/reporting/build_evidence.py --weeks W01 W02 W03 W04 --pytest-xml junit.xml
```

GitHub mỗi tuần: milestone `TuanN`; mỗi Issue một sinh viên và một kết quả (`WN-xx – <Họ tên> – <kết quả>`); PR có reviewer là thành viên còn lại; tag cuối tuần `wNN` (ví dụ `w04`).
