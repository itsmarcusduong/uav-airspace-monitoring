# Dataset survey W1

## Svanstrom Drone-detection-dataset

[WEB SOURCE] The official repository reports 650 videos: 365 IR and 285 visible, with 203,328 annotated images if all frames are extracted. Video labels are Airplane, Bird, Drone and Helicopter. The associated `.mat` labels are MATLAB Video Labeler `groundTruth` MCOS objects; a documented decoder represents each frame as `(x,y,w,h)` or absent. The repository declares CC0-1.0.

[LOCAL INSPECTION, 2026-10-04] The downloaded archive contains all 650 matching video/label pairs, all 203,328 video frames are readable, and the workbook contains 650 data rows. Class counts are Drone 271, Bird 130, Airplane 133 and Helicopter 116. Twelve label sequences contain no positive bbox; no parsed label was malformed. The decoded representation contains bboxes only, so it does not provide a persistent track ID.

## Anti-UAV

[WEB SOURCE] The official repository defines a UAV discovery/detection/recognition/tracking task with RGB and/or thermal IR Full-HD sequences, bboxes, attributes and target-presence flags. It says Anti-UAV300 has RGB+IR while 410/600 are IR-only. This strongly complements tracking/occlusion testing; however, the repository's MIT declaration concerns the project code and must not be misrepresented as a media license.

## VisDrone

[WEB SOURCE] VisDrone2019 has 288 clips, 261,908 frames and 10,209 still images from drone-mounted cameras, with ground-object boxes. It is useful for small-object/MOT protocol study, but target/viewpoint mismatch makes it reference-only.
