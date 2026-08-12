# TemporaryAI Control Center v1

Purpose: give Robert one clickable GUI for creating reviewable TemporaryAI candidates and matching avatar requests.

Launcher:

```text
Start_TemporaryAI_Control_Center.bat
```

Live test chat launcher:

```text
Start_TemporaryAI_Live_Chat_GUI.bat
Start_TemporaryAI_Live_Chat.bat
```

Desktop shortcut copy:

```text
C:\Users\robmc\Desktop\Kira Desktop Shortcuts\Start_TemporaryAI_Control_Center.bat
```

## What It Creates

Each candidate gets a timestamped package so repeated attempts do not overwrite each other:

```text
TemporaryAI/candidates/<candidate_id>/
Avatar/temp_ai/<candidate_id>/
TemporaryAI/creation_requests/<candidate_id>/
Data/temporary_ai_instances/activation_queue.json
```

Candidate files:

```text
creation_request.json
temporary_ai_profile.json
activation_plan.json
README.md
```

Candidate profiles include both a person-style display name and a role title:

```text
display_name
role_title
```

Avatar files:

```text
avatar_profile.json
avatar_request.json
references/downloaded/
references/approved/
references/rejected/
outputs/
```

Online/research files:

```text
online_research_summary.json
source_research_queue.json
reliable_source_pack.json
expanded_source_gather.json
```

The control center now attempts a lightweight Wikipedia preview lookup when Robert clicks Create. This gives a quick public summary, possible match candidates, and a URL when one is found. It also saves general search links for later source review.

As of 2026-06-06, Create and Refresh Sources also run an expanded gather step:

```text
extra Wikipedia title summaries for known hard candidates
best-effort web search leads
reviewable fetched excerpts from allowed reliable domains
avatar reference metadata/downloads for fictional, historical, and memory-relative candidates
```

Avatar references are saved under:

```text
Avatar/temp_ai/<candidate_id>/references/avatar_reference_manifest.json
Avatar/temp_ai/<candidate_id>/references/downloaded/
```

These images are references for later avatar review only. They are not memories, and Robert still needs to approve references before the avatar builder uses them.

Important: source gathering is still a draft/review process, not a guarantee that every result is correct. Expert candidates still need stronger sources before serious use.

For some known expert domains, the control center also downloads a small local source pack from reliable sources. The first implemented recipe is New Jersey criminal law/defense/attorney topics, using sources such as:

```text
New Jersey Courts
New Jersey Office of the Public Defender
Legal Services of New Jersey
New Jersey State Bar Association public information
New Jersey State Library statute references
```

These excerpts are saved as source evidence for the candidate. They are not memory. Legal candidates should give reviewable document analysis and draft help without promising outcomes or pretending a court has accepted their view.

## Supported Choices

The UI supports:

```text
Expert
Fictional Character
Historical Person
Generated Original
Memory Relative
```

Examples:

```text
Expert -> American history
Fictional Character -> Spider-Man -> Tom Holland
Historical Person -> JFK -> moon speech era
```

For version-heavy characters, use the second box to pin the exact version/canon point.

Example:

```text
AI type: Fictional Character
Domain / character / person: Peter Parker
Version, life point, or canon point: Tom Holland / Spider-Man: No Way Home after the multiverse events
```

If the version box is blank for a fictional or historical candidate, the UI may mark the candidate `needs clarification`. That means the system should not guess between versions such as Tom Holland, Tobey Maguire, Andrew Garfield, comics, animated versions, or fanfic variants.

Expert and generated-original candidates receive normal person-style names, not role labels. The expertise/role is saved separately.

Example:

```text
Name: Rachel Adams
Role: American history expert
```

## Review Rules

The control center creates drafts only.

It does not:

```text
activate the AI permanently
create finished avatars automatically
claim an avatar is finished
claim sources are verified
merge the candidate with Kira or Lisa
give the candidate access to Kira/Lisa private memory
```

Before Kira or Lisa use a candidate:

```text
Robert reviews the candidate profile.
Ambiguity questions are resolved.
A short TemporaryAI probe is run.
Avatar references/design choices are reviewed if an avatar is needed.
```

## Avatar Timing

The GUI gives an honest avatar estimate.

Current status:

```text
GPU bridge is available.
This tool creates the avatar request and reference folders.
Actual rendered avatar generation is a later step after approved references or design choices.
```

For example:

```text
Expert draft with a good preview match: about 10-20 minutes for a basic draft; a few hours to a day for a stronger reviewed expert.
Fictional character with version selected: about 20-45 minutes for a basic draft; a few hours for stronger source/version/avatar work.
Historical person with life point selected: about 20-45 minutes for a basic draft; a few hours to a day for careful source review.
Ambiguous candidate: needs Robert clarification first.
```

The Create button also shows a popup with the candidate path, online lookup status, and plain-language estimate.

## Talking To A Candidate

There are two ways to test-chat with a candidate:

```text
1. In the TemporaryAI Control Center, click Talk to Last Candidate. This opens the click-to-select chat window.
2. Run Start_TemporaryAI_Live_Chat_GUI.bat and click a candidate name.
```

The older command-line chat still exists as `Start_TemporaryAI_Live_Chat.bat`, but the GUI is preferred because Robert should not have to type a full candidate id or name.

The chat is a review/test chat, not permanent activation. It saves transcripts under:

```text
Data/personhood_evaluations/temporary_ai_live_chats/
```

The GUI also supports:

```text
Archive Selected
Refresh Sources
Voice output
candidate image preview
```

Archive Selected moves the candidate out of `TemporaryAI/candidates/` into `TemporaryAI/archived_candidates/`, and also archives the matching temp avatar folder when present. It does not delete transcripts.

Refresh Sources reruns the candidate's online preview/source recipe and rewrites `online_research_summary.json`, `source_research_queue.json`, and `reliable_source_pack.json`. It is meant for weak candidates such as hard-to-find web-series characters or experts that need stronger source packs.

Refresh Sources also rewrites `expanded_source_gather.json` and, for character/historical candidates, attempts to refresh avatar reference files.

Voice output uses the same local Windows SAPI path as Kira's voice output config. This is speech output only; it does not enable microphone listening.

The live chat picker shows a preview box under the candidate list. If the candidate has downloaded avatar references, the first reference image appears there when Robert clicks the candidate name. If it says no preview image yet, click Refresh Sources or create/repair the candidate so avatar references can be collected.

Offline rule:

```text
Creation/source lookup may need internet.
Once a candidate and its source pack/workspace are local, Robert can chat with it without internet as long as Ollama is running.
```

The live chat loads `reliable_source_pack.json` when present, so the candidate can use downloaded source excerpts during the test chat.

As of 2026-06-06, the live chat also loads local `source_pack` metadata from candidate profiles. This matters for fictional/canon candidates such as Marinette / Ladybug where local script packs already exist.

The candidate list in `Start_TemporaryAI_Live_Chat_GUI.bat` now shows readiness labels:

```text
ready
thin sources
needs clarification
needs sources
```

Use these labels before testing. A `needs sources` candidate can still be probed briefly, but it should not be trusted for biography, canon facts, legal analysis, or relationship details. A `needs clarification` candidate should have the version/life point resolved first; for example, Mary Campbell should be locked to the young Meg Donnelly / The Winchesters version before a longer chat.

Expert chat behavior was softened on 2026-06-05:

```text
Experts should give their actual read from available sources.
They should not answer like ChatGPT status reports.
They should not repeatedly tell Robert to go elsewhere instead of analyzing the attached material.
For legal/safety-sensitive topics, keep the boundary concise, then continue with useful document-based analysis.
Experts should not refuse with canned "I cannot provide legal advice" style answers. Legal and other high-stakes experts should treat outputs as reviewable drafts, summarize the documents, give their current read, and continue helping without promising a result.
```

The live chat also loads attached AI workspaces when present. Use:

```text
Start_AI_Workspace_Intake.bat
```

to turn a local folder into a reviewed workspace and attach it to a candidate.
This is the path for examples like:

```text
Laura reading a legal document folder and drafting a reviewable motion outline.
A guidance counselor expert reading school/application folders and helping draft answers.
Kira reading her writing-project folder and saving a chapter or scene draft.
```

Attached workspace files are source evidence, not memory. Drafts can be saved back to the workspace `outputs/` folder during live chat with:

```text
/save filename.md
```

Use `/quit` when done.

As of 2026-06-06, workspace excerpt selection is query-aware. If Robert asks Laura about the Montclair case, the prompt should prefer excerpts whose paths or text mention Montclair, Essex, Eva, theft, harassment, criminal mischief, restraining orders, dismissal orders, or related terms. This is intended to prevent a legal expert from answering from the wrong evidence bundle.

TemporaryAI live chat now carries a small amount of recent prior transcript context for the same candidate. This helps Laura or another expert remember what was already discussed across short test chats. It is continuity context only; it is not promoted memory.

As of 2026-06-06, the recent-context window defaults to 12 turns instead of 4. This is especially important for Laura/legal expert chats, where Robert may discuss a case across several short sessions. It still is not permanent memory.

As of 2026-06-06, known hard fictional candidates can carry a small `canon_fact_sheet` in the request/profile. This is a hand-checked anchor, not a memory. It prevents bad same-name drift and basic identity errors such as:

```text
Riley Parks -> Riley Park baseball stadium
Blue played by Julia Stiles -> generic AI/computer worker
Belle/Hannah Baxter -> vague amnesia version that does not know she is Belle
Spider-Gwen -> blank or merged-version Gwen
```

The live prompt now tells canon candidates to answer direct identity/canon questions from these anchors instead of pretending uncertainty, unless the selected canon version truly has memory loss or Robert asks for an alternate version.

2026-06-06 source-routing fix:

The expert source matcher now treats short field terms such as `ai` as whole words, not arbitrary substrings. This fixed Sarah Bennett / Entertainment PR Agent, where the old matcher saw `ai` inside `Entertainment` and incorrectly loaded programming sources. Sarah's candidate was repaired and refreshed with public-relations/publicist/PRSA sources. A repair note is included in her prompt so older programming-focused transcript turns are treated as a known error, not continuity.

2026-06-06 Sarah Bennett PR workspace:

Sarah Bennett now has an attached PR workspace:

```text
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/
```

This workspace gives her concrete folders and notes for:

```text
Robert PR profile
photos and media inbox
project materials inbox
online presence review
press release templates
pitch email templates
media outlet targets
event research
current image game plan
press kit checklist
draft press releases, bios, pitch emails, and media-kit copy
```

Sarah should use this workspace like a working entertainment publicist. She can draft press releases, pitch emails, bios, event outreach plans, and image strategy. She should not claim she sent emails, uploaded press releases, contacted outlets, or published material. She drafts and organizes for Robert review.

Future PR experts now get stronger entertainment-PR source seeds, including HubSpot press-release structure, PRSA ethics/PR practice, IMDbPro/IMDb context, press-release wires, and major entertainment trade outlets. The source gatherer still needs later improvement for deeper online research and contact discovery.

2026-06-06 TemporaryAI capability profiles:

New candidates created through the TemporaryAI Control Center now receive a `capability_profile` and a small attached `workbench/workspace_manifest.json`. This gives each role practical working folders and live-chat instructions instead of only a role label.

Examples:

```text
programmer/software/game expert -> code review inputs, program drafts, test plans
lawyer/legal expert -> client profile, case documents, evidence, timelines, draft motions
PR/publicity expert -> press releases, pitch emails, bios, press kit, event/image strategy
writer/author/screenwriter -> outlines, scenes, chapters, revision notes
musician/songwriter -> lyrics, song concepts, mood notes
artist/painter/illustrator -> visual references, art briefs, image prompts
general expert -> reference material, draft answers, review summaries
```

The live-chat prompt now reads `capability_profile` and tells the candidate what it can read, what it can create, and which future tools may not be available yet. Drafts still require Robert review. Tool actions such as sending email, filing documents, generating final images, or editing code directly are not automatic unless a reviewed tool path exists.

2026-06-06 retrofit:

Existing candidates Laura Mitchell and Emily Carter were upgraded with capability profiles and workbenches:

```text
Laura Mitchell -> legal review expert workbench
Emily Carter -> programming expert workbench
```

Laura keeps her previously attached legal document workspace and now also has a legal workbench for client profile, case documents, evidence, case summaries, draft motions, and questions for counsel. Emily now has a programming workbench for code review inputs, reference docs, program drafts, test plans, and review notes.

## Future Upgrades

Planned:

```text
stronger source lookup/research assistant beyond Wikipedia preview
version picker for fictional characters
life-point picker for historical people
approved reference review panel
candidate probe button inside the same UI
Kira/Lisa activation panel
direct integration into the future single main Kira launcher
```

## 2026-06-06 Shared Bio And PR Daily Intake

Robert approved attaching `legacy_reference/oldkira/bio.pdf` to Sarah Bennett and Laura Mitchell without making the whole oldkira folder a live dependency. The reviewed private copy is here:

```text
Data/ai_workspaces/shared_robert/robert_private_bio_20260606/
```

The PDF text extracted successfully into `extracted_text/bio_pdf.txt`. The workspace is private Robert context. Sarah may use it for bios, press-kit background, and public-image strategy, but should keep sensitive/private details out of public drafts unless Robert approves. Laura may use it as Robert background/context, but should distinguish personal history from legal evidence.

Sarah Bennett also has a daily PR research updater:

```text
tools/sarah_pr_daily_update.py
Start_Sarah_PR_Daily_Update.bat
C:\Users\robmc\Desktop\Kira Desktop Shortcuts\Start_Sarah_PR_Daily_Update.bat
```

It writes dated search/news leads into:

```text
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/daily_research/entertainment_news/
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/inputs/online_research/robert_public_sources/
```

The updater also refreshes Sarah's workspace manifest so TemporaryAI live chat can see the new files. These files are current leads, not verified facts or automatic press copy.

2026-06-06 targeted Robert public-profile intake:

Sarah's daily PR updater now also writes a targeted public-profile intake file:

```text
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/inputs/online_research/robert_public_sources/YYYYMMDD_robert_public_profile_intake.json
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/inputs/online_research/robert_public_sources/YYYYMMDD_robert_public_profile_intake.md
```

It includes Robert-approved public-source seeds for IMDb, IMDbPro, LinkedIn, YouTube, Facebook public page, Goodreads, public book listings, and Amazon search/review leads. It fetches lightweight public page title/description metadata where available. Social media is public-only: do not attempt login-only/private scraping, messages, friends-only posts, or hidden profile content.

Sarah's `temporary_ai_profile.json` and `creation_request.json` include `daily_public_profile_intake`, telling her to use the newest public-profile intake before online-presence, press-kit, and image-strategy advice. Treat every item as a lead until verified. Amazon and IMDbPro may require manual review/login; the updater stores those as review links, not guaranteed extracted facts.

2026-06-07 TemporaryAI live-chat and PR patch:

TemporaryAI live chat now has a stronger canon embodiment rule. Reviewed sources are backstage grounding. A canon character should answer as the selected version/persona, not as someone reading a report about themselves. This was added because Ladybug was talking like she was reading about Ladybug, Kara from `My Adventures with Superman` sounded too generic, and Belle/Riley drifted into alternate or wrong-source answers. The rule is prompt-level, not a heavy personality patch: it keeps basic source anchors stable while still allowing natural uncertainty.

Candidate-specific repairs:

- `kara_zor_el_my_adventures_with_superman_kara_zor_el_20260606_181026` now has Robert-provided `My Adventures with Superman` anchors: Kara/Supergirl, daughter of Zor-El, cousin of Clark/Kal-El, escape pod intercepted by Brainiac, controlled as Brainiac's enforcer, and season-2 arc from brainwashed warrior toward choosing heroism.
- `ladybug_marinette_expanded_smoke` now has repair notes telling her to speak as Marinette/Ladybug from the active form/persona and not as an outside source analyst.
- `hannah_baxter_belle_hannah_baxter_20260605_214834` now has repair notes against unsupported amnesia, job quitting, or unrelated alternate-future drift.
- `riley_parks_riley_parks_20260605_220911` is flagged as needing source repair because search/source gathering confused Riley Parks with Riley Park/stadium material.

TemporaryAI live chat save/export:

- CLI `/save filename.md`, `/save filename.doc`, and `/save filename.pdf` save the last candidate reply into the attached workspace output folder.
- The GUI `Save Last Reply` button now writes review artifacts instead of only a Markdown note. It saves Markdown plus Word-compatible `.doc` and a simple text `.pdf` when requested through the shared save helper.

Sarah Bennett PR daily updater now also writes:

```text
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/daily_research/company_press_releases/
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/contact_database/
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/outputs/press_releases/
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/outputs/bios/
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/outputs/pitch_emails/
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/outputs/press_kits/
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/outputs/image_strategy/
```

The updater seeds official/public press-room, media-contact, and event-invite leads for Sarah. These are review leads only. Sarah may draft press releases, pitch emails, bios, press-kit copy, and image strategy from them, but she must not claim she sent emails, uploaded material, contacted outlets, or obtained invites automatically.

Implementation note: `tools/sarah_pr_daily_update.py` now refreshes existing workspace-manifest entries in place, so live chat sees current excerpts instead of stale first-run excerpts.

## 2026-06-07 Sarah PR Agent + Laura Legal Workbench Expansion

Robert wants the TemporaryAI experts to work more like specialists with reviewed workspaces, not generic chatbots.

Sarah Bennett now has a stronger entertainment PR workbench:

- `tools/sarah_pr_daily_update.py`
- `Start_Sarah_PR_Daily_Update.bat`
- `C:\Users\robmc\Desktop\Kira Desktop Shortcuts\Start_Sarah_PR_Daily_Update.bat`

The updater writes daily leads for:

- company press rooms and public press releases
- public media/contact pages
- event invite/accreditation leads
- Eventbrite, 1iota, Average Socialite, Premiere Scene, and NYC event leads
- Supergirl/Spider-Man/New York premiere tracking search links
- online presence ideas: videos, photos, captions, hashtags
- Robert public profile review leads from IMDb, IMDbPro, Amazon/books, YouTube, Facebook public page, LinkedIn, Goodreads, and public search

New Sarah output folders:

```text
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/daily_research/event_opportunities/
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/daily_research/online_presence/
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/contact_database/
Data/ai_workspaces/temporary_ai/temporary_ai_sarah_pr_robert_press_kit_20260606/outputs/
```

Sarah behavior rule: give concrete PR drafts, outreach angles, contact notes, post ideas, and event plans. Do not claim to send emails, submit applications, upload press releases, or obtain invites automatically.

Laura Mitchell now has a legal daily-research updater:

```text
tools/laura_legal_daily_update.py
Start_Laura_Legal_Daily_Update.bat
C:\Users\robmc\Desktop\Kira Desktop Shortcuts\Start_Laura_Legal_Daily_Update.bat
```

It writes daily public legal research leads and templates into:

```text
Data/ai_workspaces/temporary_ai/temporary_ai_legal_refreshed_20260605_204754/daily_research/case_law/
Data/ai_workspaces/temporary_ai/temporary_ai_legal_refreshed_20260605_204754/daily_research/court_actor_profiles/
Data/ai_workspaces/temporary_ai/temporary_ai_legal_refreshed_20260605_204754/contact_database/
Data/ai_workspaces/temporary_ai/temporary_ai_legal_refreshed_20260605_204754/case_strategy/
Data/ai_workspaces/temporary_ai/temporary_ai_legal_refreshed_20260605_204754/outputs/
```

Laura uses targeted legal leads rather than broad web noise:

- New Jersey Courts opinions
- New Jersey court rules
- New Jersey Legislature/statute leads
- CourtListener/RECAP
- Justia New Jersey case law
- Google Scholar case-law search
- PACER manual-login lead
- public judge/prosecutor/court profile leads

Laura behavior rule: provide useful case analysis, possible outcomes, and game plans with facts, assumptions, risks, missing documents, and next steps. Do not claim to be retained counsel, guarantee results, file papers, or contact anyone automatically.

## 2026-06-10 Control Center Creation Defaults

Historical Person creation now applies an automatic life-point default when Robert leaves the timeframe blank:

```text
late life, shortly before death; no knowledge of exact death, posthumous legacy, later scholarship, or later sensational labels
```

This default is written into the candidate package, so blank historical candidates should not start as `needs_clarification` just because no timeframe was typed.

TemporaryAI live chat now has stronger role-first behavior:

- sources are backstage grounding, not the candidate's speaking voice
- experts should produce work instead of generic explanations
- legal experts should provide concrete review/game-plan help without canned refusal loops
- programming experts should draft runnable code or a concrete file plan when asked
- canon characters should speak from inside the selected version
- Ladybug/Marinette should not speak as a Ladybug analyst

Known repaired candidates:

```text
TemporaryAI/candidates/edgar_cayce_edgar_cayce_20260608_200254/
TemporaryAI/candidates/h_h_holmes_h_h_holmes_20260605_221432/
TemporaryAI/candidates/ladybug_marinette_expanded_smoke/
TemporaryAI/candidates/laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530/
TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/
TemporaryAI/candidates/ryan_hale_quantum_mechanics_expert_20260608_200749/
```

Future work: build the project-loop feature described in `TemporaryAI/docs/temporary_ai_project_loop_v1.md` so experts can do supervised work cycles and collaborate.

## 2026-06-11 Project Loop Launcher

The first TemporaryAI project-loop launcher now exists:

```text
Start_TemporaryAI_Project_Loop.bat
C:\Users\robmc\Desktop\Kira Desktop Shortcuts\Start_TemporaryAI_Project_Loop.bat
```

It runs:

```text
tools/temporary_ai_project_loop.py
```

This is not the same as live chat. It lets Robert pick one reviewed TemporaryAI and run one short role-shaped work cycle. The candidate can draft a plan, code idea, case timeline, PR document, research note, or similar output depending on its role.

Outputs are review-gated:

- JSON/monitor records go to `Data/personhood_evaluations/temporary_ai_project_loops/`.
- Candidate work products go to `TemporaryAI/candidates/<candidate>/workbench/outputs/project_loops/`.
- Nothing is emailed, submitted, uploaded, promoted, or permanently activated automatically.

Live chat now also uses `personal_interests`, `project_loop_seed`, and `email_and_outreach_policy` when present in candidate profiles. These are intended to make TemporaryAIs sound more human and have role-shaped ambitions outside ordinary Q&A.

## 2026-07-16 Fictional Continuity Default

For a fictional person, the work/adaptation/performer continuity must still be
resolved. Once it is resolved, a blank season, episode, or life-point endpoint
means the whole released selected continuity through the latest verified
released material. The Control Center no longer blocks or repeatedly asks for
an optional season choice. An explicit endpoint still wins, and announced or
unreleased events must not be invented.

This rule does not merge adaptations, performers, voices, or visible bodies.
For example, Ruby can use her whole released `Supernatural` continuity for
knowledge while still requiring a separate visible-vessel choice before body
authoring. Skynet can compare released `Terminator` screen timelines while
keeping the selected `Terminator Genisys` Alex/Skynet embodiment distinct.
