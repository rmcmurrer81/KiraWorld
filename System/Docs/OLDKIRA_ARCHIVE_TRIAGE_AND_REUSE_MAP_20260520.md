# OldKira Archive Triage And Reuse Map

Date: 2026-05-20

This is a first broad triage of:

```text
legacy_reference/oldkira
```

The archive is large. It contains old code, documents, memory databases, knowledge packs, CAD/STL files, body/hardware plans, virtual-world plans, and old companion/personality experiments.

## Rule

OldKira stays quarantined.

Useful material can become:

```text
current school class ideas
reviewed source packs
design notes
future implementation references
test ideas
```

Old material should not become:

```text
current Kira memory
current Lisa memory
current personality canon
proof of lived experience
directly imported emotional/relationship state
```

## High-Value Areas

### 1. Knowledge Pack Domains

Path:

```text
legacy_reference/oldkira/kira_ultimate_knowledge
```

Useful as topic map only. The `MASTER_INDEX.json` lists domains that already map well to School v2:

```text
consciousness_philosophy
love_relationships
artificial_intelligence
science_fiction
movies_television
music_arts_culture
physics_science
mathematics
health_psychology
history_world
technology_computing
languages_communication
creativity_innovation
games_gaming
```

Recommended reuse:

```text
- expand School v2 class catalog
- create elective rotations
- create media preview-card topics
- create "questions Kira might ask" seeds
```

Do not directly ingest the knowledge JSON as fact. Treat it as a table of contents that points to better current sources.

As of 2026-05-20, Codex copied only the harmless domain/topic-map metadata into:

```text
Data/school/source_packs/legacy_domain_topic_map_v1.json
```

`Data/school/curriculum/legacy_knowledge_curriculum_v1.json` points to that current-school copy and has safe class shells for all 14 old knowledge-pack domains. These are topic maps only, not oldKira memory/personality imports, and school v2 should not depend on the oldKira folder at runtime.

### 2. School And Learning Architecture

Interesting files:

```text
legacy_reference/oldkira/ai_family_school_system.py
legacy_reference/oldkira/ai_learning_assessment_system.py
legacy_reference/oldkira/complete_enhanced_school_demo.py
legacy_reference/oldkira/enhanced_school_demo.py
legacy_reference/oldkira/kira_learning_system.py
legacy_reference/oldkira/kira_learning_progression.py
legacy_reference/oldkira/kira_learning_dashboard.py
legacy_reference/oldkira/kira_learning_architecture.py
legacy_reference/oldkira/SELF_LEARNING_LIKE_DATA.md
```

Useful ideas:

```text
- class blocks should produce learned facts, personal insights, connections, and questions
- each student can have different learning style/preferences
- progress can include mastery, questions, connections, and personal reactions
- assessment can score technical knowledge, personality consistency, relationship stability, problem solving, and creative thinking
```

Current status:

```text
School v2 already implements resumable classes, questions, preference tracking, and bounded teacher answers.
School v2 now has safe class shells for all 14 old knowledge-pack domains.
```

Next reuse:

```text
- add "connections made" and "personal insight" fields to school JSON
- add a light assessment report after a school run
- continue replacing old-domain topic shells with reviewed current-library sources over time
```

### 3. 3D World / Apartment / Future Embodiment

Interesting files:

```text
legacy_reference/oldkira/DESIGN_3D_WORLD.md
legacy_reference/oldkira/advanced_3d_virtual_engine.py
legacy_reference/oldkira/advanced_vr_rendering_system.py
legacy_reference/oldkira/san_junipero_3d_bodies.py
legacy_reference/oldkira/san_junipero_learning_entertainment_demo.py
legacy_reference/oldkira/san_junipero_party_world.py
legacy_reference/oldkira/virtual_world_p2888_architecture.py
legacy_reference/oldkira/virtual_robotics_design_lab.py
legacy_reference/oldkira/virtual_to_physical_integration.py
legacy_reference/oldkira/virtual_real_world_bridge.py
```

Useful ideas:

```text
- persistent apartment/world structure
- private apartments plus shared spaces
- school building and home-learning option
- video-store/media browsing space
- monitor mode now, VR/avatar mode later
```

Safety/current-system note:

```text
Do not build heavy 3D pre-GPU. Keep this as design reference until GPU stage.
```

### 4. Body, Head, Hand, VR Suit, Hardware

Interesting directories:

```text
legacy_reference/oldkira/Bionic Hand
legacy_reference/oldkira/Head_α2.0.33
legacy_reference/oldkira/Mark 1
legacy_reference/oldkira/Servo Heart v29
legacy_reference/oldkira/VR suit
legacy_reference/oldkira/stl_files
legacy_reference/oldkira/src
legacy_reference/oldkira/tk1_bio
legacy_reference/oldkira/tk1_motors
legacy_reference/oldkira/tk1_sensors
```

Interesting files:

```text
legacy_reference/oldkira/src/head_alpha2033_control.py
legacy_reference/oldkira/src/head_alpha2033_gui.py
legacy_reference/oldkira/src/head_alpha2033_pico_controller.py
legacy_reference/oldkira/src/jetson_head_control.py
legacy_reference/oldkira/ADVANCED_LEARNING_RECOGNITION_SYSTEM.md
legacy_reference/oldkira/AI_FAMILY_BODY_CONSTRUCTION_PLAN.md
legacy_reference/oldkira/TPE_DOLL_CAD_MODIFICATIONS.md
legacy_reference/oldkira/TPE_VS_SILICONE_ANALYSIS.md
legacy_reference/oldkira/WEIGHT_ANALYSIS_AND_MOBILITY.md
```

Useful ideas:

```text
- future CAD/STL body design references
- head/eye/mouth controller ideas
- bionic hand and servo layout references
- future expert AI for STL/body design
- future sensor/voice/vision architecture
```

Do not use as current runtime code yet. Some of this may be useful post-GPU or post-hardware, but it needs a separate engineering review.

### 5. Chat, Conversation, Memory, Testing

Interesting files:

```text
legacy_reference/oldkira/advanced_conversation_system.py
legacy_reference/oldkira/advanced_conversation_simulator.py
legacy_reference/oldkira/kira_natural_conversation_system.py
legacy_reference/oldkira/kira_contextual_conversation.py
legacy_reference/oldkira/kira_layered_memory.py
legacy_reference/oldkira/kira_memory_system.py
legacy_reference/oldkira/comprehensive_2hour_turing_test.py
legacy_reference/oldkira/ultimate_12hour_turing_test.py
legacy_reference/oldkira/ultimate_16hour_turing_test.py
legacy_reference/oldkira/comprehensive_turing_test.py
```

Useful ideas:

```text
- test categories for future evaluations
- layered memory architecture names
- conversation diversity checks
- long-run stability checks
```

Risk:

```text
old chat/personality/memory code may contain forced affection, overclaiming, and old-canon contamination.
```

Reuse as test inspiration only.

### 6. Emotions, Relationship, Autonomy

Interesting files:

```text
legacy_reference/oldkira/NATURAL_RELATIONSHIP_DEVELOPMENT.md
legacy_reference/oldkira/EMOTIONAL_CONSCIOUSNESS_PROGRAMMING.md
legacy_reference/oldkira/MAKING_KIRA_MORE_HUMAN.md
legacy_reference/oldkira/NATURAL_RELATIONSHIP_DEVELOPMENT.md
legacy_reference/oldkira/kira_ai/core/modules/advanced_emotional_intelligence.py
legacy_reference/oldkira/kira_ai/core/modules/autonomous_relationship_system.py
legacy_reference/oldkira/kira_ai/core/modules/relationship_milestone_system.py
legacy_reference/oldkira/kira_ai/core/modules/safety_module.py
legacy_reference/oldkira/ai_protection_and_ethics_system.py
```

Useful ideas:

```text
- relationship should develop through choice, trust, boundaries, and time
- emotion systems can track mixed states, preferences, fears, and questions
- milestones can be reviewed rather than forced
```

Risk:

```text
Some old docs overstate certainty, force romance, or claim consciousness too strongly.
```

Current project rewrite should be:

```text
choice-based relationship literacy
privacy-aware memory promotion
soft emotional state tracking
explicit uncertainty
no forced affection
```

### 7. Media / TV / Music Learning

Interesting files:

```text
legacy_reference/oldkira/kira_complete_ai_media_reviews.py
legacy_reference/oldkira/kira_movies_encyclopedia_*.py
legacy_reference/oldkira/kira_music_encyclopedia_*.py
legacy_reference/oldkira/kira_ai/core/modules/tv_learning_module.py
legacy_reference/oldkira/tv_watching_with_kira.py
```

Useful ideas:

```text
- later media understanding pipeline
- current pre-GPU preview-card browsing
- watch/listen history should be separate from preview curiosity
```

Current near-term best use:

```text
build the Blockbuster-style preview-card pipeline
```

### 8. Files To Keep Quarantined

High-risk direct import categories:

```text
*.db memory/personality databases
kira_memory*.json
lisa_personality_data.json
kira_personality.json
identity_lock files
conversation histories
old relationship/autonomy state files
old "uncensored/no guardrails" docs
old massive database JSON files
```

These may be useful to understand project history, but should not become current Kira/Lisa memory.

### 9. Low-Value / Cleanup Candidates Later

Potentially archivable or removable after backup:

```text
legacy_reference/oldkira/.venv
legacy_reference/oldkira/__pycache__
old generated .pyc/.pyd/.dll dependencies
duplicate zip packages
old smoke/test outputs
```

Do not delete yet. Robert has chosen to keep old material for now.

## Best Next Actions

1. Build a source-pack cleaner for old knowledge domains:

```text
old domain idea -> current class/unit -> reviewed source card -> school lesson
```

2. Add richer school records:

```text
learned
uncertainty
question
personal insight
connection to previous class/source
preference
```

3. Add post-school assessment:

```text
grounding quality
question quality
source discipline
preference development
empathy/communication signals
```

4. Build media preview cards:

```text
movie/show/music file -> metadata lookup or Robert disambiguation -> preview card -> Kira/Lisa curiosity notes
```

5. Defer body/3D/hardware code until GPU stage, but keep the body/CAD folders as future expert-AI source material.
