# First-person consumer of an exported World package

The local inventory found no Godot, Unity or Unreal executable in PATH or the
standard Program Files / Local Programs installation locations, and no matching
engine project in Kira. This is a scoped inventory, not proof that no portable
engine exists anywhere. Blender 5.1 is installed, but is not a game runtime.

The smallest useful local slice uses the already pinned Three 0.180 runtime and
GLTFLoader. It imports the actual scene.glb and its bound scene.json, independently
of Kira's research, geometry compiler, equipment builder and native workspace.
It must never reconstruct visible equipment from collision or metadata boxes.

The isolated consumer will implement supported horizontal first-person walking,
wall/furniture/closed-leaf collision, bounded hinge motion, occupied-swing holds,
reach checks and mutual exclusion for explicitly paired airlock doors. A door
intent changes its imported hinge and its collision bounds together; the frames
remain fixed. Source worlds and the package remain immutable. Session state is
discarded on reload. This adds no pressure cycle, science equipment behavior,
native game-engine physics, stairs, jumping, networking or VR support.

The browser entry point selects the five files of one explicit exported package.
It checks their manifest hashes and rejects external GLB resources before import.
No globally newest project, original source path, dependency download or model
call is involved. The runtime and interaction tests are callable in Node without
WebGL or a browser. A small loopback server may later serve only this prototype;
it will not be started during this task.

Acceptance: import the installed042 Mars GLB with all 565 meshes, 67 embedded
textures, 141 semantic nodes and 134 collider links; compare six closed/half/open
leaf transforms to the sidecar and fixed frames; reject tampered/missing files,
wrong hinge/owner/pair associations and unsupported contracts; walk up to a
closed door, open and cross it, close it, then exercise its peer. Check supported
floor edges and furniture obstruction. Record CPU resource use and all 116
protected originals unchanged. Visual review and ordinary input usability remain
pending because no UI interaction is authorized in this task.
