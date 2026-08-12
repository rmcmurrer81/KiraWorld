# Qwen 3.5 remaining-current-person routes static checkpoint

Date: `2026-08-09`

Status: `STATIC_ONLY_PASS_NO_MODEL_DEVICE_OR_MEDIA_EXECUTION`

This append-only checkpoint supersedes only the scope statements in the first
2026-08-09 route checkpoint that still excluded Lisa, TemporaryAI, classes,
life loops, and auxiliary owner tools. It does not rewrite that earlier
checkpoint or any acceptance evidence.

No Ollama generation, Llama generation, GPU work, voice, camera, microphone,
browser, media playback, or Blender process was started during this pass.

## Current exact identity

- model: `qwen3.5:9b`
- digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
- ordinary requests: top-level `think: false`, `keep_alive: 0`
- alternate, blank, or digest-mismatched person selections: fail closed

`Core/model_request_policy.py` now owns the exact name-and-digest authority.
`Core/conversation_loop.py` validates that identity before every Ollama person
turn, so a stale inherited environment cannot silently select an older model.

## Reconciled current routes

The following reachable/current sources no longer default to Llama:

- Kira direct everyday/custom, life-debrief, future-upgrade, avatar-intake,
  inner-life journal, Chicago, idle-study, humanity, empathy, school, life,
  Robert-presence, and Kira/Robert dialogue paths;
- Lisa memory/privacy and shared Kira/Lisa slumber, mature-book, and adult
  source-discussion paths;
- Advanced AI and TemporaryAI candidate-probe paths;
- optional legal-spa resource smoke model work;
- the live webcam/microphone acceptance text turns;
- the resident-media and separate Turing/psychology acceptance text turns.

The webcam and resident-media harnesses may unload Qwen between serialized GPU
phases, but their later text route is now the same exact Qwen digest. They do
not route text to Llama.

The model-upgrade benchmark now rejects the dormant rollback candidate even
when its candidate id is supplied explicitly. The rollback inventory remains
installed and recorded, but it is not a selectable benchmark, automatic
fallback, or current person route.

`config/model_runtime.json` now lists current Kira, Lisa, TemporaryAI, and
Robert person lanes in production scope. Its exclusions are limited to the
owner-frozen Video Studio, append-only historical evidence, negative/mismatch
fixtures, and the dormant rollback inventory.

## Remaining literal Llama references

A targeted scan of current `Core`, `tools`, and `config` source found no Llama
selection in a current owner launcher or current person runner. Literal
references remain only in:

- `config/model_runtime.json`: the single dormant installed rollback record;
- `config/model_upgrade_candidate_registry.json`: dormant rollback provenance
  and exact inventory metadata; execution is blocked in the benchmark tool;
- `tools/run_kira_text_voice_bounded_owner_acceptance.py`: preserved historical
  pre-Qwen acceptance harness, not linked by a root owner launcher;
- `tools/run_kira_text_voice_two_turn_latency_acceptance.py`: preserved
  historical pre-Qwen latency harness, not linked by a root owner launcher;
- `tools/validate_kira_turing_psych_voice_gate_preparation.py`: static validator
  for the preserved historical package; it performs no model generation.

`tools/run_kira_model_question_series_acceptance.py` remains an indirect
historical consumer of the preserved bounded-harness constants. It has no root
owner launcher and is not a current acceptance route. The current Qwen
Turing/psychology work uses the separate 2026-08-09 exact-Qwen preparation and
runner.

## Static verification

```text
py -B -m py_compile <all reconciled Python sources and focused tests>
PASS

py -B -m unittest -v \
  Testing.test_qwen35_remaining_current_routes_static \
  Testing.test_model_request_policy \
  Testing.test_current_authority_reconciliation \
  Testing.test_qwen_webcam_microphone_live_acceptance \
  Testing.test_resident_media_experience_live_acceptance
47 tests passed

py -B -m unittest -v \
  Testing.test_qwen35_owner_runnable_routes_static \
  Testing.test_qwen35_production_singleton_launcher \
  Testing.test_qwen35_single_generation_route
33 tests passed
```

Total focused static result: `80 passed`.

## Changed-file SHA-256 manifest

| Project-relative path | SHA-256 |
|---|---|
| `Core/model_request_policy.py` | `e3c7cc299dc4967e6eb2bfeb7fe3d4ca9ec8405f30f8071e98d1036d64e45a7c` |
| `Core/conversation_loop.py` | `b2bf956372c55e894020a9fb9d69de276bfc0c8448fac7f26ed5b497f4d7f9db` |
| `Core/qwen35_runtime_identity.py` | `ab8b36d986b94f0e9a0f85d232c6ab08cbb355d65db59dd5815874397f7d2123` |
| `config/model_runtime.json` | `4fa0449b6f91b7df6f207e86d324e893ee244bce9d8d065a3d14bdc8a197f2ae` |
| `tools/create_kira_inner_life_journal_entry.py` | `33b6bbb2763aa867ae24ba9d587a1e4fa319e57723d8adaca93d2509d3575e0b` |
| `tools/run_kira_codex_direct_everyday_chat.py` | `a036886aab70cf68475a04b4eeee59678a41555bfd745cd92202c6521e49ff94` |
| `tools/run_kira_codex_direct_custom_chat.py` | `d946a39555e9e776eed99bf277e95a091a680aaca89681a55e561ba4582d41e5` |
| `tools/run_kira_chicago_holmes_repair_class.py` | `b0512c4eb14c76cc0330184acc9d40b3384278201602f8249b2fee6d8508b013` |
| `tools/run_kira_chicago_archivist_class.py` | `a27d8221df3c1b418f754bacf1b46b15745ee38cd5a44a1a0c5dfb21eb73ed51` |
| `tools/run_kira_idle_study_loop.py` | `a74728067aad73e161ed7c87d54c78ae312aeb50538c143e9632107fa104fe57` |
| `tools/run_kira_humanity_class.py` | `140244a73a22fd81d541d634d0a693d94e1501652dc803efdae3526578f18d2b` |
| `tools/run_kira_communication_empathy_class.py` | `e773cac754ce2e4231e57db8129cf17105870da5fbf46d4e9406074fadce3f5d` |
| `tools/run_kira_avatar_design_intake_chat.py` | `381180f4b5d3cc01ab9167d91e18ad0774a1686fb9cb0d095abe8b6f46630c81` |
| `tools/run_lisa_codex_memory_privacy_review_chat.py` | `020b759e63ad17b1d2ea62477df936ad974e7d919a4870da199e6e2be57e8699` |
| `tools/run_kira_lisa_slumber_party.py` | `713d24099ffd828ea0845855357fb33eea68ce4e8e94a906d81426c4e74558fd` |
| `tools/run_kira_lisa_sex_talk_club.py` | `374e8208ae41508d7b0392d21403ddec70d3c1a71498272ce9ba4336f488756e` |
| `tools/run_kira_lisa_mature_book_club.py` | `d19926111f6ee565661dd395f802b0790a2f9b82a636663b2837d1b398738395` |
| `tools/run_advanced_ai_probe.py` | `1a8b7e8e742772a9c891d373738e3f961cae2edb85536d66ac5bd33d30acd6a1` |
| `tools/run_temporary_ai_candidate_probe.py` | `bee663ae245678ccf32143a4cce4e8690e64e34bf6e33ada58866fd0d5bc79cc` |
| `tools/run_kira_codex_life_test_debrief_chat.py` | `9acbe181138e149ffbf82cc2e7cf01ae583a59654976a3768216cabd7214ce75` |
| `tools/run_kira_codex_future_upgrades_chat.py` | `01f86ef6f49f2df126756bf982ee404579f2e514a634c0604bf46f671b3a93f7` |
| `tools/run_robert_presence_ai_turing_psych_eval.py` | `be721d7d53b5294b0061b6880fc8c104aba47ff5bc6b2bfaa67e502b500d829c` |
| `tools/run_kira_robert_intro_dialogue_20260714.py` | `68723fd851593a8da3cc5fd2694e52f12aa63065e66c10559d980b17cb56fc3f` |
| `tools/run_qwen_webcam_microphone_live_acceptance.py` | `246bd9bebcf3fecf14df86c87eb205bae90d1cb6410eb9ec32118e4b069caf65` |
| `tools/run_resident_media_experience_live_acceptance.py` | `f56927167a92eadf88f2ea9b61ef5a6ece9d8e96bc53f3d696331188e2279e23` |
| `tools/kira_spa_resource_smoke.py` | `42cacb4f3ec41790ed869cf4071a277341219f517f4b0088f3da615df685e409` |
| `tools/new_computer_setup_assistant.py` | `29b1eaa69b87d6db223f507ea43576017827222c576ab1e3863f77ecd22d9a1f` |
| `tools/benchmark_model_upgrade_candidates.py` | `cc8aab1508e61feea12a2277d76132c7bc028bb8c4a61604a24bd3efe4bb1787` |
| `tools/start_humanity_then_adult_slumber_20260516.ps1` | `09b2e460af49cc34369364def2e9d8d296876c9fe2f2891c9cf0598e2c2561f5` |
| `Start_Advanced_AI_Probe.bat` | `3db884e84b55f779b6ed0c02da0dec31f5cadb612eca262ebdbcb65c2a156ca1` |
| `Start_Kira_Avatar_Design_Intake_Chat.bat` | `92c62f9249b56eb15e14d84fee82dc25bee5e466a442db9cb123f318ad466344` |
| `Start_Kira_PreRAM_Quick_School_Test.bat` | `8b1cfbd3053130573ddd1e17144fa641528728c9f2e3d3f4ca10048150f37313` |
| `Start_TemporaryAI_Candidate_Probe.bat` | `c2649a441cb439a75db317da8f8ceed675c8b06b68f69fc3cba8736078501faa` |
| `Start_TemporaryAI_Project_Loop.bat` | `bc04532399709d17ec1e87ed080a48218c6a3869478d342fa042caccce0d86aa` |
| `Testing/test_model_request_policy.py` | `87a78d4c485f49c5f22671104e15cedf935a4655c15183d068d9e2e31efb6849` |
| `Testing/test_current_authority_reconciliation.py` | `76603feacf0af1bf3488eff83ee0dcb0806335c58be7626a29cb95bf85d966ee` |
| `Testing/test_qwen35_owner_runnable_routes_static.py` | `c18be2aaa3a26d678383eea916b17462f1f1d01fc13db63c0c526b370d429eb5` |
| `Testing/test_qwen35_remaining_current_routes_static.py` | `fbb5e68398d166938a95d4c566d833c6909fd831603780f12433193899fccc01` |
| `Testing/test_qwen_webcam_microphone_live_acceptance.py` | `06f1e23f558b3e3cfaf7bc4c87ce85a77b3fd93d94a113000a00b0260b905ea7` |
| `Testing/test_resident_media_experience_live_acceptance.py` | `15ae11fefef541b64d6b2a67dd363f41e38593a6c69b8d25b3bee6486e457d58` |

## Rollback

Rollback is hunk-level and source-specific. Preserve this checkpoint and all
earlier evidence. Revert only the exact route pin or fail-closed check shown to
cause a regression, then rerun the same 80-test static suite. Do not restore
Llama as a selected model, run its historical acceptance harnesses, enable it
as an automatic fallback, or weaken the exact digest gate without a new
explicit owner decision.
