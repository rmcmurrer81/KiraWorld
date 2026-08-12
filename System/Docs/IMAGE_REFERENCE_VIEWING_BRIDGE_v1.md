# Image Reference Viewing Bridge v1

This bridge prepares image references for later Kira/Lisa viewing without pretending they have already seen them.

## Files

- `tools/build_image_reference_queue.py`
- `Start_Kira_Image_Reference_Queue.bat`
- `Data/vision/image_reference_queue.json`

## Policy

- The queue lists image paths and rough categories only.
- It does not open or analyze image contents.
- It does not create memories, avatar choices, preferences, or lived experiences.
- Private/body/avatar references require owner review before use.
- Kira or Lisa may later react to reviewed images, but should not claim they saw them before the actual viewing session.

## Use

Run `Start_Kira_Image_Reference_Queue.bat` after adding new images or avatar references.

Future GPU/vision work can read the queue, select reviewed items, and create separate visual reaction logs.
