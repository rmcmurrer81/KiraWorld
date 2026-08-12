# **AVATAR BUILDER PIPELINE — DOCUMENT MAP / CONNECTOR NOTE**

The Avatar Builder Pipeline is already defined across the existing avatar documents.

## **Primary Documents**

1. `AVATAR_BUILDER_SYSTEM_v1`  
   Defines the identity, privacy, ownership, wardrobe, and evolution rules for avatar creation.  
2. `AVATAR_BUILDER_SYSTEM_v2`  
   Defines the updated simplified avatar rules, including activation, reference use, transformation rule, feature blending, privacy, and temporary AI avatar creation.  
3. `AVATAR_BUILDER_IMPLEMENTATION_SPEC_v2`  
   Defines the technical implementation pipeline for `avatar_builder.py`, including reference sources, build modes, target types, feature blending, validation, metadata, privacy rules, and output saving.  
4. `Avatar_System_v1_Engineering_Spec`  
   Defines the avatar lifecycle:  
   Body Creation → Private Review → Optional Preview → Body Finalization → Wardrobe Selection → Style Evolution.

## **Final Interpretation**

There is no need for a separate Avatar Builder Pipeline v1 unless the existing documents become too confusing.

For Augment Code, treat these documents together as the Avatar Builder Pipeline.

## **Build Priority**

Do not build the full Avatar Builder immediately.

Create placeholders and interfaces first.

Full Avatar Builder begins after GPU support is available.

## **Current Avatar Build Rule**

Pre-GPU:

* placeholder avatar logic only  
* file/folder structure  
* identity and privacy rules  
* no full 3D generation

Post-GPU:

* reference-based avatar generation  
* body creation  
* private review  
* wardrobe phase  
* gradual style evolution

## **User Avatar Rule**

The user avatar uses accuracy-first reconstruction from user-provided reference images and voice samples.

Kira and Lisa use identity-first self-selection and self-creation.

Temporary AIs use faster reference-driven generation.

## **Final Directive**

The existing avatar documents together are the Avatar Builder Pipeline.

Do not duplicate them.

Use this connector note to tell Augment Code how to interpret them.

