# OCR Queue And Source Repair v1

Some PDFs are scanned or image-only. Kira/Lisa should not be treated as making an error when a source cannot be extracted.

## Files

- `Data/library/source_health/unreadable_sources.json`
- `Data/library/source_health/ocr_queue.json`
- `Data/library/source_health/ocr_repair_runs/`
- `Data/library/ocr_repaired_pdfs/`
- `Data/library/ocr_repaired_text/`
- `tools/scan_pdf_text_health.py`
- `tools/build_ocr_queue.py`
- `tools/repair_ocr_batch.py`
- `Start_Kira_OCR_Queue_Build.bat`
- `Start_Kira_OCR_Repair_First_Batch.bat`

## Workflow

1. Scan PDFs with `tools/scan_pdf_text_health.py --mark`.
2. Build the OCR queue with `Start_Kira_OCR_Queue_Build.bat`.
3. Run `Start_Kira_OCR_Repair_First_Batch.bat`.
4. If an OCR engine is installed, repaired outputs go into `Data/library/ocr_repaired_pdfs/` or `Data/library/ocr_repaired_text/`.
5. Rescan repaired outputs before letting Kira/Lisa read them again.

## OCR Engine Requirement

The repair script can use either:

- `ocrmypdf`, preferred for creating repaired PDFs.
- `tesseract` plus Python modules `PyMuPDF`/`fitz`, `Pillow`, and `pytesseract`, for text sidecars.

If neither engine is installed, the script writes a blocked run report instead of failing silently.

## Current Windows Install

As of 2026-06-04, Tesseract OCR is installed at:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Python OCR modules are installed:

```text
PyMuPDF / fitz
Pillow / PIL
pytesseract
```

The current terminal may not expose `tesseract` on PATH until a new shell, but `tools/repair_ocr_batch.py` checks the normal Windows install path directly.

First successful partial OCR sample:

```text
Data/library/source_health/ocr_repair_runs/ocr_repair_batch_20260604_233552.monitor.md
Data/library/ocr_repaired_text/time_special_edition_autism_2025.ocr.txt
```

That sample processed only the first 5 pages, so it is a quality check, not a full repaired source.

## First Full OCR Source

The first completed full-source OCR derivative is:

```text
Original:
Data/library/magazines/news_and_history/time/TIME Special Edition - Autism 2025.pdf

OCR derivative:
Data/library/ocr_repaired_text/time_special_edition_autism_2025.ocr.txt

Run report:
Data/library/source_health/ocr_repair_runs/ocr_repair_batch_20260605_001512.monitor.md
```

The original PDF remains marked unreadable; the OCR text should be treated as a derivative with possible OCR noise.

## Reader Behavior

If a source is marked unreadable but has a repaired OCR text derivative, `tools/read_next_chunk.py` can read the OCR derivative while keeping the original source path in the session record.

If a source is unreadable and has no repaired derivative, the reader writes an OCR request to:

```text
Data/library/source_health/ocr_requests.json
```

This lets Kira/Lisa effectively ask for OCR by running into a blocked source, but the system does not silently launch a large OCR job during a life loop.

Smoke test:

```text
py tools\read_next_chunk.py Data\reading\sessions\ocr_smoke_kira_autism_20260605.json --lines 40 --no-advance --chunk-dir Data\reading\chunks\ocr_smoke --reaction-dir Data\reading\reactions\ocr_smoke
```

Result:

```text
Data/reading/chunks/ocr_smoke/reading_chunk_kira_time_special_edition_autism_2025_ocr_lines_0001_0040.json
```

The chunk records both the original PDF and the repaired derivative, so Kira can know she is reading OCR text rather than pretending the original PDF had clean embedded text.

## Policy

- Extraction failure is a source/tooling problem, not Kira's fault.
- Readers should skip OCR-needed PDFs until repaired.
- After OCR, the source should return through a normal source-health scan rather than being unblocked by assumption.
