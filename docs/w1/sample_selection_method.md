# Sample selection method

Completed target: exactly 100 readable frames, selected deterministically from 100 distinct Svanstrom source videos. The strata are visible/IR modality, Drone class, Bird/Airplane/Helicopter hard negatives, source video ID and valid bbox trajectory position. Frames are deduplicated by `(dataset_id, video_id, frame_index)`.

Each image records its source video and label filename, frame index, dimensions, class, bbox and official repository URL. `extract_samples.py` uses seed `20261003`, rejects invalid/all-absent labels, interleaves IR and visible sources, and refuses to replace output unless exactly 100 images exist.

Observed distribution: 50 Drone, 20 Bird, 15 Airplane and 15 Helicopter frames; 51 IR and 49 visible frames; 100 unique videos. Bbox area ranges from 72.0 to 37,225.886 pixels squared (median 551.0); 73 samples are smaller than 32×32 pixels, 21 are 32×32–96×96, and 6 are larger.
