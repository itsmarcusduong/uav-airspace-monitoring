# Quang dataset review

1. Dataset fit: Svanstrom is the primary dataset; it matches sky-monitoring target geometry.
2. License: Svanstrom CC0 is evidenced; Anti-UAV/VisDrone media licensing needs review.
3. Annotation: 650 MCOS label files decode; the 100-frame sanity check passes bbox/frame checks.
4. UAV class: present in Svanstrom and Anti-UAV.
5. Hard negatives: Svanstrom has Bird, Airplane and Helicopter classes.
6. Video: Svanstrom and Anti-UAV are video-based.
7. Tracking: Anti-UAV provides a relevant supplemental tracking task; Svanstrom supports per-frame detection, not identity-supervised tracking in the decoded label representation.
8. Track ID: no persistent ID is exposed by the inspected decoded label representation.
9. Split: must be video/sequence-level; not frozen.
10. Leakage: high risk if random frames are used; mitigated by W2 group split.
11. 100 samples: DONE; 100 readable images from 100 unique videos.
12. Source/frame IDs: DONE; every sample records source/video/frame and label path.
13. Manifest: complete for primary source; unknowns remain explicit for un-downloaded secondary/reference datasets.
14. Proposal consistency: yes for scope and W1 restrictions.
15. Template consistency: primary W1 evidence is consistent; secondary-dataset licensing remains intentionally pending.
