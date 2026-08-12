# Qwen 3.5 school and life launcher static reconciliation

Date: `2026-08-09`

Status: `STATIC_MOCK_PASS_NO_LIVE_MODEL_OR_LIFE_RUN`

This follows the normal Text + Voice owner-route reconciliation. The eight
current owner-clickable Kira/Lisa school, class, and supervised-life launchers
now select exact tag `qwen3.5:9b`, publish expected digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`,
and explicitly disable both Llama timing-candidate flags. Their five direct
runner defaults now select Qwen 3.5 when no launcher environment is present.

No Llama, Qwen, Ollama server, GPU, voice, camera, microphone, school class,
life loop, browser, or owner conversation was started by this repair. It is
implementation consistency, not latency, hearing, learning, or owner-use
acceptance. The frozen owner-rejected Video Studio source remains unchanged as
historical evidence and was not run.

## Verification

Focused static/mock tests:

```text
15 passed, 38 subtests passed in 0.73s
```

The tests enumerate all eight launchers and all five runner defaults, reject a
Llama model selection or explicit `--model` override, require the exact Qwen
digest on each launcher, require both Llama candidate flags to be off, and
retain the exact Qwen non-thinking/unload request policy. The first combined
run correctly exposed two stale assertions that still described active school
and life launchers as archival Llama routes; those assertions were updated to
current owner authority and the combined suite then passed.

## Exact changed-file identities

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `Activate_Kira_And_Lisa.bat` | 2,759 | `23686a8ebcea197b4359c4ae5680340047d035e6d22560044697b78dd3222d25` |
| `Start_Kira_Miraculous_Continuity_Class.bat` | 592 | `b4716cc481e88fdb1b3a80076a883f2850a87a67dba0ddf6b94bab49dcf59537` |
| `Start_Kira_PreRAM_Micro_School_Test.bat` | 641 | `232bd4ab9d08b24c95e93e5efaaba89b66025748e887f9630789621cc21e0ebd` |
| `Start_Kira_Relationship_Empathy_Class.bat` | 517 | `26eed34010502746ee5c27c2bd53a39f5acd80eb1183fc4d285dab7a0cfc6347` |
| `Start_Kira_School_Control_Center.bat` | 474 | `1922ce83c24683c380f36a61a65b765c5bed22fd728b518d08f0df53097215ed` |
| `start_kira_school_v2_9hour.bat` | 481 | `59d100de5753c91d36d1deafa2a8393bd9d3c02283fbc2f5b9b4b14678c876a1` |
| `Start_Kira_Supervised_6hour_Life_Test.bat` | 530 | `125abf629fa9a2aa8dde6e50960a363accd4e4fe87cffc814749df1c4b0c93a9` |
| `Start_Kira_Supervised_9hour_School_Day.bat` | 1,382 | `ef4156c86fe8d223851ce387d2ace52b540bb31c15008b9341e4be0564a17967` |
| `tools/run_kira_life_day.py` | 76,899 | `eada62f04888d60887665458ad4a2c94b493ff4d0b2747b27ed74ecb59e9500e` |
| `tools/run_kira_miraculous_continuity_class.py` | 20,741 | `c8a4cb4e812bae44bfb7c93c7bebb9035ba21686657e00664b6cb182f162a8fc` |
| `tools/run_kira_relationship_empathy_class.py` | 20,661 | `dbda395cae6b9e465c1f342cf254da9a36cbec738ab63e00a1d2c404d7a29fc7` |
| `tools/run_kira_school_session.py` | 57,820 | `5ce9c542c1d91481a09429a26280c2556db985501dc5a2a2e290ca2145dcfc1b` |
| `tools/run_kira_school_v2.py` | 41,906 | `501f267aa2dfd3c6c181e3f5e1f16c647d7413df38fc94eaf22c625506a557c9` |
| `Testing/test_qwen35_owner_runnable_routes_static.py` | 7,450 | `98ae5e26cb7bf798c2b14a4129e3bedfe7be14b42298a70e080cc4138a524ccb` |
| `Testing/test_current_authority_reconciliation.py` | 7,321 | `b1c572bc1f9bf837576a8d17a71ab66fdbef9c3273710d1b5b7b21c0106d844d` |

## Rollback

Rollback is hunk-level: restore only the model tag/default lines and remove
only the newly added digest and disabled-candidate environment lines, plus the
two corresponding static-test expansions. Do not overwrite whole launchers or
runners. Restoring Llama selection would contradict current owner authority
and therefore is not an automatic rollback.
