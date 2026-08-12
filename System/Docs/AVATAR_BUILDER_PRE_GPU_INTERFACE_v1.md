# Avatar Builder Pre-GPU Interface v1

## Purpose

Full Avatar Builder waits until GPU support is available.

Pre-GPU work should create the control layer:

```text
build configs
build requests
reference inventories
privacy states
validation rules
placeholder metadata
```

No full 3D body generation happens in this stage.

## Source Documents

This interface follows:

```text
AVATAR_BUILDER_SYSTEM_v1
AVATAR_BUILDER_SYSTEM_v2
AVATAR_BUILDER_IMPLEMENTATION_SPEC_v2
Avatar_System_v1_Engineering_Spec
VISIBILITY_AND_SHARING_RULES_v1
REFERENCE_LIBRARY_FOLDER_SPEC_v1
REFERENCE_LIBRARY_SYSTEM_v1
VOICE_SYSTEM_SPEC_v1
```

## Core Targets

Avatar Builder supports:

```text
kira
lisa
user
temp_ai
```

## Build Modes

Supported modes:

```text
generated
reconstruction_real
reconstruction_fictional
placeholder
```

Pre-GPU mode should normally use:

```text
placeholder
reconstruction_real metadata only
reconstruction_fictional metadata only
generated metadata only
```

## Lifecycle

Avatar lifecycle:

```text
body_creation
private_review
optional_preview
body_finalization
wardrobe_selection
style_evolution
```

Pre-GPU lifecycle stops at:

```text
draft
reference_collection
metadata_ready
waiting_for_gpu
```

## Privacy Rules

Avatar creation is private by default.

The owner controls:

```text
whether to share
what to share
how much to share
when sharing stops
who may view it
```

Normal visible presentation is clothed.

Private body generation, early base meshes, and unclothed construction stages are not automatically visible.

No one may see an avatar body before the base underwear/clothing gate unless the avatar owner explicitly grants a preview.

Preview choices include:

```text
no_preview
feature_only
shoulders_up
full_body_feedback
clothed_only
```

The avatar owner can ask for help without revealing everything. For example, Kira may ask Lisa or Robert for body-type feedback, or she may choose to show only shoulders-up until clothing is applied. Lisa and Robert have the same control over their own avatar creation.

## Private Body Reference Rule

Body reference photos, including nude reference photos voluntarily provided by the avatar owner for their own avatar, are private modeling sources.

They are used only for:

```text
proportions
body shape
face/body structure
accuracy checking
avatar reconstruction
```

They must not be:

```text
shown to other AIs or people
used as public assets
used for training unrelated identities
copied into temporary AI builds
treated as shareable memory
included in public exports
```

For Robert's avatar, nude/body reference photos are Robert-controlled private sources. They support accuracy-first reconstruction and stay separate from Kira/Lisa/private AI visibility.

## Feature Selection Rule

Kira and Lisa may browse approved reference pictures and select features such as:

```text
eyes
hair
body size
body shape
proportions
cup size
distinctive features
style direction
```

Those choices are preferences and design inputs, not public visibility grants.

After body creation, each avatar chooses starter outfits before normal presentation.

## Target Differences

### Kira and Lisa

Kira and Lisa use identity-first self-selection.

They create who they are; Robert may give input only if invited.

### User Avatar

Robert's user avatar uses accuracy-first reconstruction from Robert-provided references.

The system must distinguish:

```text
real_robert
robert_avatar_autonomous
real_robert_controlling_avatar
```

### Temporary AIs

Temporary AIs use faster, bounded, reference-driven generation.

They must stay linked to version, canon point, variant, and voice/body pairing.

## Pre-GPU Outputs

Pre-GPU outputs may include:

```text
avatar build request JSON
avatar metadata JSON
reference inventory JSON
privacy state JSON
placeholder profile
readiness notes
```

Pre-GPU outputs must not claim a real rendered avatar exists.

## Summary

This phase makes the Avatar Builder ready for the desktop/GPU without pretending the laptop can generate full 3D bodies yet.
