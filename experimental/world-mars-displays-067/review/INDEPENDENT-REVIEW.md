# Independent CPU review — Mars displays 067

The current v3 candidate passes all nine focused CPU checks. The exact files and input evidence are pinned in REVIEW.json.

Three issues found during review were corrected by the root agent: the map now uses the existing circulation role fallback; window directions require a real matching observation viewport; and the observation plaque retains its actual room name when the geometry cannot accommodate a viewport. The last regression uses a 2.3 m observation room and confirms that neither data nor the plaque promises a Mars view.

The tests load the actual seven-room 063 geometry and bound presentation manifest. They compare preview and export functions, recorded canvas drawing commands, equipment geometry and full world transforms, and the complete authored scene assembled on the CPU. The data remains an explicitly fictional, static scenario. The geometry and equipment positions are unchanged.

No browser, GPU, UI, GLB exporter, model or canonical installation ran for this review. The recording canvas checks text and commands; it does not establish visual readability or realism. The root agent's separate browser review and any later export or install must retain their own evidence.

TEST-OUTPUT-001 is preserved as an early harness mismatch during the changing function signature. TEST-OUTPUT-002 passed the initial eight checks. TEST-OUTPUT-003 passed all nine after the plaque correction.
