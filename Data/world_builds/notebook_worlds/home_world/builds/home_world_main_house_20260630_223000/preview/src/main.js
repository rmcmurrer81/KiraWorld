import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { Reflector } from "three/examples/jsm/objects/Reflector.js";
import {
  advanceLocomotionBlend,
  buildCenteredDoorwayCorridor,
  planCollisionFreeGridRoute,
  selectCollisionFreeHeading,
  shortestYawDelta as movementShortestYawDelta,
  stepAcceleratedYaw,
  translationScaleForTurn,
  updateRouteProgressWatch,
} from "./movement_realism.js";
import {
  KIRA_DOCTOR_BODY_EXAM_VERSION,
  KIRA_DOCTOR_JOINT_PHASES,
  buildKiraDoctorStructuralReport,
  comfortIdleOffsets,
  summarizeExecutedExam,
} from "./body_control_exam.js";
import {
  ambientMicroMovementFrame,
  buildAmbientMicroMovementProfile,
} from "./ambient_micro_movements.js";
import {
  KIRA_EYE_CONTROL_EXAM_VERSION,
  KIRA_EYE_CONTROL_PHASES,
  buildKiraEyeStructuralReport,
  kiraEyeExamPhaseAt,
  kiraEyeSideTargets,
} from "./eye_control_exam.js";
import {
  auditExistingMouthVertexRegions,
  createExistingMouthLipSyncRig,
  existingMouthLipSyncProbe,
  findExistingMouthVertexRegion,
  restoreExistingMouthLipSyncRig,
  updateExistingMouthLipSyncRig,
} from "./existing_mouth_lipsync.js";
import {
  isCurrentAvatarModelLoad,
  shouldRevokeKiraRuntimeModel,
} from "./active_avatar_model_guard.js";

const params = new URLSearchParams(window.location.search);
const startArea = params.get("area") || "home";
const HOME_WORLD_PRE_RAM_LIGHT_MODE = params.get("fullWorld") !== "1";
const KIRA_STAGED_EYE_RIG_REQUEST = params.get("kiraEyeRig");
const KIRA_STAGED_EYE_RIG_VERSION = KIRA_STAGED_EYE_RIG_REQUEST === null ? "v3.3" : KIRA_STAGED_EYE_RIG_REQUEST;
const KIRA_LIVE_EYE_RIG_ENABLED = KIRA_STAGED_EYE_RIG_VERSION === "v3.3";
const KIRA_CENTERED_IDLE_EYE_FIT_ENABLED = params.get("kiraEyeIdleFit") !== "off";
// Diagnostic-only root binding lets the isolated browser review compare the
// authored model-space socket placement with the skin-corrected head-bone
// binding. Normal owner/runtime launches use the same inverse-bind transform
// as the R6 head skin, so the reviewed eyes stay in the moving sockets.
const KIRA_EYE_BINDING_REQUEST = params.get("kiraEyeBinding");
const KIRA_EYE_BINDING_MODE = ["root", "skin"].includes(KIRA_EYE_BINDING_REQUEST)
  ? KIRA_EYE_BINDING_REQUEST
  : "skin";
const KIRA_EYE_IRIS_DEPTH_DIAGNOSTIC = params.get("kiraEyeIrisDepthTest") === "off";
// R7-v3.3 was authored and reviewed directly in the measured R6 socket.  Do
// not apply the older runtime scale, yaw, or globe-position compensation: it
// is what drove the previous eyes behind/outside the eyelids in live views.
const KIRA_RUNTIME_IRIS_DIAMETER_SCALE = 1.0;
const KIRA_RUNTIME_CORNEA_DIAMETER_SCALE = 1.0;
const KIRA_R6_EYE_VISUAL_FIT = Object.freeze({
  forwardOffset: 0,
  verticalOffset: 0,
  horizontalOffset: 0,
  commonHorizontalOffset: 0,
  neutralYawDegrees: 0,
  irisHorizontalOffset: 0,
  irisVerticalOffset: 0,
  irisDepthOffset: 0,
  // Browser-validated R6 socket correction. The v3.3 eye asset remains
  // byte-for-byte unchanged; these reversible millimetre offsets compensate
  // for the R6 skin bind pose in Three.js.
  socketVerticalOffset: -0.008,
  socketDepthOffset: -0.002,
});
const HOME_WORLD_LEGACY_STRIP_MALL_ENABLED = params.get("stripMall") === "1";
const HEADLESS_MOTION_SMOKE_ENABLED = params.get("motionSmoke") === "1";
if (HEADLESS_MOTION_SMOKE_ENABLED) {
  let deterministicSmokeSeed = 0x4b495241;
  Math.random = () => {
    deterministicSmokeSeed = (1664525 * deterministicSmokeSeed + 1013904223) >>> 0;
    return deterministicSmokeSeed / 0x100000000;
  };
}
const LEGACY_STRIP_MALL_STATIC_COST = Object.freeze({
  measurementKind: "source_expansion_estimate_not_live_gpu_measurement",
  proceduralMeshObjects: 128,
  boxGeometryObjects: 122,
  planeGeometryObjects: 5,
  cylinderGeometryObjects: 1,
  canvasTextures: 5,
  canvasTextureBaseRgbaBytes: 2949120,
  canvasTextureEstimatedMipmappedBytes: 3932160,
  colliders: 37,
  doorColliders: 5,
  interactionZones: 6,
  importedGlbRequests: 0,
  drawCallNote: "At least one main-pass submission per visible mesh; double-sided transparent panes/signs and shadow passes can add more.",
  memoryNote: "The five sign canvases dominate feature-specific texture memory. Runtime process RAM/VRAM deltas require a controlled browser A/B and are not inferred from this estimate.",
});

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xb8c9d5);
scene.fog = new THREE.Fog(0xb8c9d5, 120, 360);

const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.05, 450);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const toast = document.querySelector("#toast");
const blueprintPanel = document.querySelector("#blueprint");
const hudLocationTitle = document.querySelector("#hud-location-title");

const player = {
  position: new THREE.Vector3(0, 1.65, 7.2),
  yaw: Math.PI,
  pitch: 0,
  floor: startArea === "upstairs" ? 1 : 0,
  radius: 0.32,
};
let playerStairTraversalActive = false;
let playerStairTraversalDirection = null;

const keys = new Set();
const colliders = [];
const doorColliders = [];
const interactZones = [];
const activityTruthProps = [];
const clock = new THREE.Clock();
let activeShellState = null;
let frontDoorOpen = false;
let frontDoorLeft = null;
let frontDoorRight = null;
let frontDoorLeftClosed = null;
let frontDoorRightClosed = null;
let backDoorOpen = false;
let backDoorLeaf = null;
let libraryDoorOpen = false;
let libraryDoorLeaf = null;
let homeTardisGroup = null;
let homeTardisCollider = null;
let homeTardisDoorOpen = false;
let homeTardisLeftDoor = null;
let homeTardisRightDoor = null;
let homeTardisInteriorPreview = null;
let libraryCatalogCursor = 0;
const stripMallDoorOpen = new Map();
const stripMallDoorLeaves = new Map();
let activeMarker = null;
const groupPresenceOrbs = new Map();
const gltfLoader = new GLTFLoader();
const textureLoader = new THREE.TextureLoader();
let activeAvatarMixer = null;
let activeAvatarRoot = null;
let activeAvatarModelUrl = "";
let activeAvatarModelLoadGeneration = 0;
let activeAvatarAction = "idle";
let activeAvatarActionStarted = 0;
let activeAvatarForm = "civilian";
let activeAvatarHomePosition = new THREE.Vector3(5.7, 3.32, -4.65);
let activeAvatarMovePhase = 0;
let lastActiveAvatarSnapshotPostAt = -Infinity;
let activeAvatarSnapshotSequence = 0;
let activeAvatarProceduralRig = null;
let activeAvatarAmbientMicroMovementFrame = null;
let lastMindBodyTruthRecordAt = -Infinity;
let activeDoorInteraction = null;
let activeDoorReachRig = null;
let activeDoorReachHiddenNodes = [];
const activeDoorFailureCooldowns = new Map();
let activePostureInteraction = null;
let activeFurnitureInteraction = null;
let activeSkillInteraction = null;
let ladybugBedSleepCover = null;
let ladybugDeskChairGroup = null;
const ACTIVE_AVATAR_GROUND_Y = 0.05;
const ACTIVE_AVATAR_SECOND_FLOOR_Y = 3.32;
const ACTIVE_AVATAR_WALK_STRIDE_METERS = 0.85;
const ACTIVE_AVATAR_WALK_SPEED_GROUND = 0.52;
const ACTIVE_AVATAR_WALK_SPEED_UPSTAIRS = 0.42;
const ACTIVE_AVATAR_JOG_SPEED_GROUND = 1.12;
const ACTIVE_AVATAR_RUN_SPEED_GROUND = 2.05;
const ACTIVE_AVATAR_SWIM_SPEED = 0.68;
const ACTIVE_AVATAR_STAIR_PRACTICE_SPEED = 0.68;
const ACTIVE_AVATAR_MIN_WALK_TIME_SCALE = 0.62;
const ACTIVE_AVATAR_MAX_WALK_TIME_SCALE = 2.35;
const ACTIVE_AVATAR_WALK_PHASE_LOCKED = true;
const ACTIVE_AVATAR_DOOR_REACH_SECONDS = 0.95;
const ACTIVE_AVATAR_DOOR_FINISH_SECONDS = 2.35;
const ACTIVE_AVATAR_DOOR_HAND_TOUCH_METERS = 0.48;
const ACTIVE_AVATAR_DOOR_IK_START_SECONDS = 0.08;
const ACTIVE_AVATAR_DOOR_IK_ITERATIONS = 9;
const ACTIVE_AVATAR_USE_PROCEDURAL_DOOR_ARM = false;
const ACTIVE_AVATAR_FOOT_IK_ITERATIONS = 5;
const ACTIVE_AVATAR_FOOT_CONTACT_HEIGHT = 0.035;
const ACTIVE_AVATAR_VISUAL_GROUND_CLEARANCE = 0.008;
const ACTIVE_AVATAR_VISUAL_GROUND_CALIBRATION_SECONDS = 0.1;
const ACTIVE_AVATAR_COLLISION_RADIUS = 0.46;
const ACTIVE_AVATAR_COLLISION_LOOKAHEAD_METERS = 0.62;
const ACTIVE_AVATAR_MAX_TURN_RADIANS_PER_SECOND = 2.65;
const ACTIVE_AVATAR_MAX_TURN_ACCELERATION_RADIANS_PER_SECOND_SQUARED = 6.4;
const ACTIVE_AVATAR_TURN_BEFORE_TRANSLATE_RADIANS = 1.05;
const ACTIVE_AVATAR_TURN_FULL_TRANSLATE_RADIANS = 0.16;
const ACTIVE_AVATAR_RECOVERY_MAX_DISTANCE_METERS = 1.25;
const ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS = Object.freeze({
  // Kira's current adult base has a nonstandard bind pose.  The July 7
  // fixed-view contact sheet established that local Y, not a large local Z
  // rotation, is the shoulder axis that brings her arms naturally down.
  upperZ: Object.freeze([0.06, 0.16]),
  upperY: Object.freeze([0.95, 1.18]),
  upperX: Object.freeze([-0.34, 0.34]),
  lowerX: Object.freeze([0.06, 0.22]),
  handZ: Object.freeze([-0.08, 0.08]),
});
// The adult Kira mesh can need more than eight centimetres of root correction
// after retargeting.  Calibration still moves only by the measured foot/bounds
// gap, so the wider guard permits contact without forcing the feet underground.
const ACTIVE_AVATAR_VISUAL_GROUND_CORRECTION_MIN = -0.25;
const ACTIVE_AVATAR_VISUAL_GROUND_CORRECTION_MAX = 0.12;
const ACTIVE_AVATAR_STAIR_STEPS = 16;
const ACTIVE_AVATAR_STAIR_BOTTOM_Z = 2.95;
const ACTIVE_AVATAR_STAIR_TOP_Z = -1.65;
const ACTIVE_AVATAR_STAIR_BOTTOM_Y = ACTIVE_AVATAR_GROUND_Y;
const ACTIVE_AVATAR_STAIR_TOP_Y = ACTIVE_AVATAR_SECOND_FLOOR_Y;
const ACTIVE_AVATAR_STAIR_HALF_WIDTH = 0.98;
const ACTIVE_AVATAR_UNSUPPORTED_FALL_METERS_PER_SECOND = 3.6;
const ACTIVE_AVATAR_SUPPORT_SNAP_RANGE = 0.42;
const ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY = Object.freeze({
  initialReviewSeconds: 8 * 60 * 60,
  continuationReviewSeconds: 4 * 60 * 60,
  minimumSelfChosenSeconds: 4 * 60 * 60,
  chatDoesNotEndActivity: true,
  exitMode: "explicit_new_embodied_intent_or_voluntary_exit_only",
  continuationMode: "continue_when_no_exit_intent_instead_of_forced_roaming",
});
const ACTIVE_AVATAR_SUPPORT_SURFACES = [
  {
    id: "outside_ground",
    xMin: HOME_WORLD_PRE_RAM_LIGHT_MODE ? -64 : -156,
    xMax: HOME_WORLD_PRE_RAM_LIGHT_MODE ? 98 : 276,
    zMin: HOME_WORLD_PRE_RAM_LIGHT_MODE ? -32 : -96,
    zMax: HOME_WORLD_PRE_RAM_LIGHT_MODE ? 74 : 288,
    y: ACTIVE_AVATAR_GROUND_Y,
  },
  { id: "first_floor_slab", xMin: -8, xMax: 8, zMin: -7.75, zMax: 7.75, y: ACTIVE_AVATAR_GROUND_Y },
  { id: "second_floor_west_bedrooms", xMin: -8, xMax: 0.55, zMin: -7.75, zMax: 7.75, y: ACTIVE_AVATAR_SECOND_FLOOR_Y },
  { id: "second_floor_east_bedrooms", xMin: 3.25, xMax: 8, zMin: -7.75, zMax: 7.75, y: ACTIVE_AVATAR_SECOND_FLOOR_Y },
  { id: "second_floor_front_hall", xMin: 0.55, xMax: 3.25, zMin: 2.95, zMax: 7.75, y: ACTIVE_AVATAR_SECOND_FLOOR_Y },
  { id: "second_floor_rear_hall", xMin: 0.55, xMax: 3.25, zMin: -7.75, zMax: -2.35, y: ACTIVE_AVATAR_SECOND_FLOOR_Y },
  { id: "second_floor_stair_landing", xMin: 0.62, xMax: 3.18, zMin: -2.45, zMax: 0.2, y: ACTIVE_AVATAR_SECOND_FLOOR_Y },
  { id: "strip_mall_capture_flag_parking_lot", xMin: 34, xMax: 58, zMin: 31, zMax: 54, y: ACTIVE_AVATAR_GROUND_Y },
  { id: "future_park_basketball_court", xMin: 44, xMax: 86, zMin: 48, zMax: 88, y: ACTIVE_AVATAR_GROUND_Y },
  { id: "home_world_school_classroom", xMin: 66, xMax: 90, zMin: 9, zMax: 35, y: ACTIVE_AVATAR_GROUND_Y },
  { id: "capture_flag_battlefield", xMin: 80, xMax: 238, zMin: 82, zMax: 248, y: ACTIVE_AVATAR_GROUND_Y },
].filter((surface) => {
  if ([
    "strip_mall_capture_flag_parking_lot",
    "capture_flag_battlefield",
  ].includes(surface.id)) return false;
  return !HOME_WORLD_PRE_RAM_LIGHT_MODE || ![
  "future_park_basketball_court",
  ].includes(surface.id);
});
const ACTIVE_AVATAR_POSTURE_TESTS = {
  sit_couch: {
    action: "sit",
    label: "living room couch",
    position: new THREE.Vector3(-5.15, ACTIVE_AVATAR_GROUND_Y, 2.56),
    standPosition: new THREE.Vector3(-4.05, ACTIVE_AVATAR_GROUND_Y, 1.82),
    yaw: 0,
    seconds: 4.8,
    posture: "sit",
    rootYOffset: -0.32,
  },
  lie_grass: {
    action: "lie_down",
    label: "front lawn grass",
    position: new THREE.Vector3(-1.0, ACTIVE_AVATAR_GROUND_Y, 13.3),
    yaw: Math.PI,
    seconds: 3.6,
    posture: "lie",
    rootTiltX: Math.PI / 2,
    rootYOffset: 0.16,
  },
  lie_bed: {
    action: "lie_down",
    label: "Marinette temporary bed",
    position: new THREE.Vector3(5.85, ACTIVE_AVATAR_SECOND_FLOOR_Y, -5.9),
    yaw: Math.PI / 2,
    seconds: 3.6,
    posture: "lie",
    rootTiltX: Math.PI / 2,
    rootYOffset: 0.42,
  },
  sleep_bed: {
    action: "lie_down",
    label: "Marinette temporary bed sleep",
    position: new THREE.Vector3(5.85, ACTIVE_AVATAR_SECOND_FLOOR_Y, -5.9),
    standPosition: new THREE.Vector3(6.62, ACTIVE_AVATAR_SECOND_FLOOR_Y, -4.16),
    yaw: Math.PI / 2,
    seconds: 6.2,
    posture: "sleep",
    rootTiltX: Math.PI / 2,
    rootYOffset: 0.42,
    sleepCover: true,
  },
  duck: {
    action: "duck",
    label: "duck and keep balance",
    seconds: 2.2,
    posture: "duck",
    rootTiltX: 0.12,
    rootYOffset: -0.46,
  },
};
let activePoseSprite = null;
let activePoseMaterial = null;
let activePoseTextures = new Map();
let activePoseManifestUrl = "";
let activePoseKey = "";
const REALISTIC_HOUSE_MODEL_URL = "/models/56_harbour_terrace.glb";
const REALISTIC_TOILET_MODEL_URL = "/models/toilet_002_rigged.glb";
const REALISTIC_SOFA_MODEL_URL = "/models/home_world/modern_sofa_reference_light.glb";
const REALISTIC_BOOKSHELF_MODEL_URL = "/models/home_world/book_shelf_reference.glb";
const KIRA_SHARED_PHONE_MODEL_URL = "/models/home_world/samsung_galaxy_s25_edge.glb";
const NEIGHBOR_ENTRY_DOOR_MODEL_URL = "/models/home_world/entry_door_with_sidelights.glb";
const NEIGHBOR_HOUSE_REFERENCE_MODEL_URL = "/models/home_world/enterable_panel_house_light.glb";
const KIRA_DOWNLOADED_HOUSE_GROUND_FLOOR_URL = "/models/home_world/kira_downloaded_house_ground_floor.glb";
const NEIGHBOR_BED_SOURCE_MODEL_URL = "/models/home_world/apartment_layout_dream_house_reference.glb";
const NEIGHBOR_LIVING_ROOM_FURNITURE_MODEL_URL = "/models/home_world/living_room_furniture_chairs_sofa_props.glb";
const NEIGHBOR_PREFAB_BED_FRAME_MODEL_URL = "/models/home_world/neighbor_bed_full.glb";
const NEIGHBOR_PREFAB_MATTRESS_MODEL_URL = "/models/home_world/neighbor_bed_mattress.glb";
const NEIGHBOR_PREFAB_PILLOW_MODEL_URL = "/models/home_world/neighbor_bed_pillow.glb";
const NEIGHBOR_PREFAB_BOOK_MODEL_URL = "/models/home_world/neighbor_book_reference.glb";
const HOME_WORLD_STARBUCKS_MODEL_URL = "/models/home_world/activities/starbucks_coffee_house_cafe_v2.glb";
const HOME_WORLD_COFFEE_CUP_MODEL_URL = "/models/home_world/activities/coffee_shop_cup.glb";
const HOME_WORLD_BASKETBALL_COURT_MODEL_URL = "/models/home_world/activities/basket_ball_court_game_ready_asset.glb";
const HOME_WORLD_BASKETBALL_MODEL_URL = "/models/home_world/activities/basketball.glb";
const HOME_WORLD_SUN_MODEL_URL = "/models/home_world/activities/sun.glb";
const HOME_WORLD_MOON_MODEL_URL = "/models/home_world/activities/moon.glb";
const HOME_WORLD_ANIMATED_DOOR_WINDOW_MODEL_URL = "/models/home_world/activities/animated_doors_and_a_window_demo.glb";
const HOME_WORLD_REAL_GRASS_PATCH_MODEL_URL = "/models/home_world/real_acting/patch_of_grass.glb";
const KIRA_STAGED_EYE_RIG_MODEL_URL = "/models/home_world/kira/kira_socket_eye_rig_v3_3.glb";
const KIRA_STAGED_EYE_RIG_SHA256 = "b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5";
const KIRA_HAND_ANIMATION_REFERENCE_MODEL_URL = "/models/home_world/real_acting/hand_animation_test.glb";
const HOME_WORLD_SCHOOL_CLASSROOM_MODEL_URL = "/models/home_world/school/classroom_model_1.glb";
const HOME_WORLD_SCHOOL_CHAIR_MODEL_URL = "/models/home_world/school/school_chair.glb";
const HOME_WORLD_SCHOOL_TABLE_MODEL_URL = "/models/home_world/school/old_metal_table_low_poly.glb";
const HOME_WORLD_SCHOOL_SIDE_TABLE_MODEL_URL = "/models/home_world/school/frame_2_side_table.glb";
const HOME_WORLD_SCHOOL_WORLD_MAP_MODEL_URL = "/models/home_world/school/world_map_color_3d_scan.glb";
const HOME_WORLD_SCHOOL_BOARD_MODEL_URL = "/models/home_world/school/school_board.glb";
const HOME_WORLD_SCHOOL_LOCKERS_MODEL_URL = "/models/home_world/school/metal_school_lockers.glb";
const HOME_WORLD_SCHOOL_CLOCK_MODEL_URL = "/models/home_world/school/classic_school_clock.glb";
const HOME_WORLD_SCHOOL_PENCILS_MODEL_URL = "/models/home_world/school/low_poly_pencils.glb";
const HOME_WORLD_SCHOOL_SCRAPBOOK_MODEL_URL = "/models/home_world/school/scrapbook_trinket_-_dandys_world.glb";
const KIRA_REDDISH_HAIR_MODEL_URL = "/models/home_world/kira/long_reddish_hair_for_game.glb";
const KIRA_REDDISH_HAIR_ENABLED = false;
const KIRA_ADULT_SKIN_COLOR = 0xe6c0a9;
const KIRA_ADULT_EYELID_COLOR = 0xd8ad99;
const HOME_WORLD_HIGH_DETAIL_GRASS_PATCHES = params.get("highGrass") === "1" && !HOME_WORLD_PRE_RAM_LIGHT_MODE;
const HOME_WORLD_GRASS_DENSITY_SCALE = HOME_WORLD_HIGH_DETAIL_GRASS_PATCHES ? 1.0 : HOME_WORLD_PRE_RAM_LIGHT_MODE ? 0.12 : 0.46;
const MAIN_TWO_STORY_HOUSE_ENABLED = false;
const NEIGHBOR_BLUEPRINT_HOUSE_ENABLED = false;
const ONE_BEDROOM_BLUEPRINT_HOUSE_ENABLED = true;
const ONE_BEDROOM_HOUSE_CENTER = new THREE.Vector3(-23.0, ACTIVE_AVATAR_GROUND_Y, 3.1);
const ONE_BEDROOM_HOUSE_WIDTH = 18.2;
const ONE_BEDROOM_HOUSE_DEPTH = 13.0;
const ONE_BEDROOM_HOUSE_LEFT_X = ONE_BEDROOM_HOUSE_CENTER.x - ONE_BEDROOM_HOUSE_WIDTH / 2;
const ONE_BEDROOM_HOUSE_RIGHT_X = ONE_BEDROOM_HOUSE_CENTER.x + ONE_BEDROOM_HOUSE_WIDTH / 2;
const ONE_BEDROOM_HOUSE_BACK_Z = ONE_BEDROOM_HOUSE_CENTER.z - ONE_BEDROOM_HOUSE_DEPTH / 2;
const ONE_BEDROOM_HOUSE_FRONT_Z = ONE_BEDROOM_HOUSE_CENTER.z + ONE_BEDROOM_HOUSE_DEPTH / 2;
const ONE_BEDROOM_INTERIOR_ROUTE_BOUNDS = Object.freeze({
  minX: ONE_BEDROOM_HOUSE_LEFT_X + 0.65,
  maxX: ONE_BEDROOM_HOUSE_RIGHT_X - 0.65,
  minZ: ONE_BEDROOM_HOUSE_BACK_Z + 0.65,
  maxZ: ONE_BEDROOM_HOUSE_FRONT_Z - 0.65,
});
const ONE_BEDROOM_INTERIOR_ROUTE_CELL_METERS = 0.28;
const ACTIVE_AVATAR_INTERIOR_REPLAN_LIMIT = 3;
const ONE_BEDROOM_HOUSE_ENTRY = new THREE.Vector3(ONE_BEDROOM_HOUSE_LEFT_X + ONE_BEDROOM_HOUSE_WIDTH * 0.39 + 1.15, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_HOUSE_FRONT_Z + 0.95);
const ONE_BEDROOM_ROOM_SPLIT_X = ONE_BEDROOM_HOUSE_LEFT_X + ONE_BEDROOM_HOUSE_WIDTH * 0.39;
const ONE_BEDROOM_BATH_FRONT_Z = ONE_BEDROOM_HOUSE_BACK_Z + ONE_BEDROOM_HOUSE_DEPTH * 0.36;
const ONE_BEDROOM_FRONT_ROOM_CENTER_Z = (ONE_BEDROOM_BATH_FRONT_Z + ONE_BEDROOM_HOUSE_FRONT_Z) * 0.5;
const ONE_BEDROOM_BED_CENTER = new THREE.Vector3(ONE_BEDROOM_HOUSE_LEFT_X + 1.38, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_FRONT_ROOM_CENTER_Z + 0.05);
const KIRA_ONE_BEDROOM_HOME_SPAWN = new THREE.Vector3(ONE_BEDROOM_HOUSE_RIGHT_X - 5.25, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_HOUSE_FRONT_Z - 4.55);
const KIRA_ONE_BEDROOM_HOME_FRONT_OUTSIDE = ONE_BEDROOM_HOUSE_ENTRY.clone();
const ONE_BEDROOM_HOUSE_COPY_SPACING = 21.8;
const ONE_BEDROOM_HOUSE_COPY_CONFIGS = [
  { id: "lisa_home", owner: "Lisa", title: "Lisa's Home", offsetX: ONE_BEDROOM_HOUSE_COPY_SPACING, offsetZ: 0 },
  { id: "marinette_home", owner: "Marinette", title: "Marinette's Home", offsetX: ONE_BEDROOM_HOUSE_COPY_SPACING * 2, offsetZ: 0 },
  { id: "peter_home", owner: "Peter", title: "Peter's Home", offsetX: ONE_BEDROOM_HOUSE_COPY_SPACING * 3, offsetZ: 0 },
  { id: "gwen_home", owner: "Gwen", title: "Gwen's Home", offsetX: ONE_BEDROOM_HOUSE_COPY_SPACING * 4, offsetZ: 0 },
  { id: "for_rent_home", owner: "For Rent", title: "For Rent", offsetX: ONE_BEDROOM_HOUSE_COPY_SPACING * 5, offsetZ: 0, empty: true },
];
const ONE_BEDROOM_ALL_HOUSE_CONFIGS = [
  { id: "kira_home", owner: "Kira", title: "Kira's Home", offsetX: 0, offsetZ: 0 },
  ...ONE_BEDROOM_HOUSE_COPY_CONFIGS,
];
const ONE_BEDROOM_HOME_WORLD_ACTIVE_COPY_IDS = new Set([]);
const ONE_BEDROOM_HOME_WORLD_COPY_CONFIGS = ONE_BEDROOM_HOUSE_COPY_CONFIGS.filter((config) => ONE_BEDROOM_HOME_WORLD_ACTIVE_COPY_IDS.has(config.id));
const ONE_BEDROOM_HOME_WORLD_CONFIGS = [
  ONE_BEDROOM_ALL_HOUSE_CONFIGS[0],
  ...ONE_BEDROOM_HOME_WORLD_COPY_CONFIGS,
];
const SAVED_PLACES_NOTEBOOK_WORLD_TEMPLATE = {
  worldId: "saved_places_notebook_world",
  buildId: "saved_places_one_bedroom_house_template_20260711",
  title: "Saved Places - One-Bedroom House Template",
  sourceHome: "Kira's accepted one-bedroom house",
  liveInHomeWorld: false,
  path: "Data/world_builds/notebook_worlds/saved_places_notebook_world/builds/saved_places_one_bedroom_house_template_20260711",
};
const ONE_BEDROOM_RIGHT_ROOM_CENTER_X = (ONE_BEDROOM_ROOM_SPLIT_X + ONE_BEDROOM_HOUSE_RIGHT_X) * 0.5;
const ONE_BEDROOM_COUCH_SPOT = new THREE.Vector3(ONE_BEDROOM_RIGHT_ROOM_CENTER_X - 0.55, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_HOUSE_FRONT_Z - 1.08);
const ONE_BEDROOM_COFFEE_TABLE_SPOT = new THREE.Vector3(ONE_BEDROOM_RIGHT_ROOM_CENTER_X - 0.45, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_HOUSE_FRONT_Z - 3.35);
function oneBedroomCouchSeatSpot() {
  // The imported sofa owns a solid collision volume.  The old point was
  // inside that volume, so a person could never physically reach it.  This is
  // the collision-safe front edge where the seated posture is grounded.
  return ONE_BEDROOM_COUCH_SPOT.clone().add(new THREE.Vector3(0, 0, -1.32));
}

function oneBedroomHomeEntryCorridorWaypoints() {
  return buildCenteredDoorwayCorridor({
    entryX: ONE_BEDROOM_HOUSE_ENTRY.x,
    wallZ: ONE_BEDROOM_HOUSE_FRONT_Z,
    y: ACTIVE_AVATAR_GROUND_Y,
    outsideSign: 1,
    outsideDistance: 1.08,
    insideDistance: 1.08,
  }).map((point) => {
    const waypoint = new THREE.Vector3(point.x, point.y, point.z);
    waypoint.userData = { doorwayPhase: point.id };
    return waypoint;
  });
}

function activeAvatarInsideOneBedroomHome(position = activeMarker?.position) {
  if (!position || Math.abs(position.y - ACTIVE_AVATAR_GROUND_Y) > 0.3) return false;
  return pointInsideArea2D(position, {
    minX: ONE_BEDROOM_HOUSE_LEFT_X + 0.2,
    maxX: ONE_BEDROOM_HOUSE_RIGHT_X - 0.2,
    minZ: ONE_BEDROOM_HOUSE_BACK_Z + 0.2,
    // A body on the porch is outside.  Do not let a broad area label skip the
    // centered doorway corridor.
    maxZ: ONE_BEDROOM_HOUSE_FRONT_Z - 0.2,
  });
}
const ONE_BEDROOM_BATHROOM_SINK_SPOT = new THREE.Vector3(ONE_BEDROOM_ROOM_SPLIT_X - 1.85, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_HOUSE_BACK_Z + 1.08);
const ONE_BEDROOM_BATH_SHOWER_SPOT = new THREE.Vector3(ONE_BEDROOM_HOUSE_LEFT_X + 2.25, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_BATH_FRONT_Z - 0.25);
const ONE_BEDROOM_TOILET_SPOT = new THREE.Vector3(ONE_BEDROOM_HOUSE_LEFT_X + 1.05, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_HOUSE_BACK_Z + 1.35);
const ONE_BEDROOM_COFFEE_STATION_COUNTER_SPOT = new THREE.Vector3(
  ONE_BEDROOM_HOUSE_RIGHT_X - 4.05,
  1.08,
  ONE_BEDROOM_HOUSE_BACK_Z + 2.34,
);
const ONE_BEDROOM_COFFEE_STATION_USE_SPOT = new THREE.Vector3(
  ONE_BEDROOM_COFFEE_STATION_COUNTER_SPOT.x,
  ACTIVE_AVATAR_GROUND_Y,
  ONE_BEDROOM_COFFEE_STATION_COUNTER_SPOT.z + 0.84,
);
const ONE_BEDROOM_FRIDGE_MODEL_URL = "/models/home_world/inventory/shabby_fridge.glb";
const ONE_BEDROOM_BATHROOM_SINK_MODEL_URL = "/models/home_world/inventory/bathroom_sink_cabinet.glb";
const ONE_BEDROOM_KITCHEN_CABINET_MODEL_URL = "/models/home_world/inventory/corner_kitchen_cabinet.glb";
const ONE_BEDROOM_WOOD_BED_FRAME_MODEL_URL = "/models/home_world/inventory/black_wooden_bed_frames.glb";
const ONE_BEDROOM_TV_MODEL_URL = "/models/home_world/inventory/game_ready_uhd_curved_tv.glb";
const ONE_BEDROOM_TV_CABINET_MODEL_URL = "/models/home_world/inventory/tv_cabinet.glb";
const ONE_BEDROOM_COFFEE_TABLE_MODEL_URL = "/models/home_world/inventory/low_height_coffee_table.glb";
const ONE_BEDROOM_TV_REMOTE_MODEL_URL = "/models/home_world/inventory/samsung_tv_remote_control.glb";
const ONE_BEDROOM_BATH_SHOWER_MODEL_URL = "/models/home_world/inventory/bath_tub_shower_combo.glb";
const ONE_BEDROOM_SIDE_TABLE_MODEL_URL = "/models/home_world/school/frame_2_side_table.glb";
const ONE_BEDROOM_BOOK_MODEL_URL = "/models/home_world/neighbor_book_reference.glb";
const ONE_BEDROOM_LIBRARY_BOOK_MODEL_URL = "/models/home_world/inventory/book.glb";
const ONE_BEDROOM_LIBRARY_BOOK_SELECTION = [
  { title: "Alice's Adventures in Wonderland", source: "Data/library/novels/11_alice_s_adventures_in_wonderland_author_lewis_carroll.pdf" },
  { title: "The Adventures of Sherlock Holmes", source: "Data/library/novels/12_the_adventures_of_sherlock_holmes_author_arthur_conan_doyle.pdf" },
  { title: "Frankenstein", source: "Data/library/novels/frankenstein_mary_shelley.pdf" },
  { title: "The Hobbit", source: "Data/library/novels/science_fiction_and_fantasy/the_hobbit_by_j_r_r_tolkein.pdf" },
  { title: "Project Hail Mary", source: "Data/library/novels/science_fiction_and_fantasy/project_hail_mary.pdf" },
  { title: "The Martian", source: "Data/library/novels/science_fiction_and_fantasy/the_martian_by_andy_weir.pdf" },
  { title: "Doctor Who and the Three Doctors", source: "Data/library/novels/doctor_who/target_books/doctor_who_target_book_064_doctor_who_and_the_three_doctors.pdf" },
  { title: "The Time Machine", source: "Data/library/novels/science_fiction_and_fantasy/h_g_wells/h_g_wells_the_time_machine.pdf" },
];
const KIRA_BUNGALOW_ENABLED = false;
const KIRA_BUNGALOW_CENTER = ONE_BEDROOM_HOUSE_CENTER.clone();
const KIRA_BUNGALOW_INTERIOR_MODEL_URL = "";
const KIRA_BUNGALOW_EXTERIOR_MODEL_URL = "";
const KIRA_BUNGALOW_WIDTH = ONE_BEDROOM_HOUSE_WIDTH;
const KIRA_BUNGALOW_DEPTH = ONE_BEDROOM_HOUSE_DEPTH;
const KIRA_BUNGALOW_LEFT_X = KIRA_BUNGALOW_CENTER.x - KIRA_BUNGALOW_WIDTH / 2;
const KIRA_BUNGALOW_RIGHT_X = KIRA_BUNGALOW_CENTER.x + KIRA_BUNGALOW_WIDTH / 2;
const KIRA_BUNGALOW_FRONT_Z = KIRA_BUNGALOW_CENTER.z + KIRA_BUNGALOW_DEPTH / 2;
const KIRA_BUNGALOW_BACK_Z = KIRA_BUNGALOW_CENTER.z - KIRA_BUNGALOW_DEPTH / 2;
const KIRA_BUNGALOW_SPAWN = KIRA_ONE_BEDROOM_HOME_SPAWN.clone();
const KIRA_BUNGALOW_FRONT_OUTSIDE = KIRA_ONE_BEDROOM_HOME_FRONT_OUTSIDE.clone();
const KIRA_BED_SLEEP_SPOT = ONE_BEDROOM_BED_CENTER.clone();
const KIRA_BED_STAND_SPOT = new THREE.Vector3(ONE_BEDROOM_BED_CENTER.x + 1.15, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_BED_CENTER.z + 1.25);
const GARMENT_STATES = Object.freeze({
  InCloset: "InCloset",
  OnHanger: "OnHanger",
  Held: "Held",
  Dressing: "Dressing",
  PartiallyWorn: "PartiallyWorn",
  WornOpen: "WornOpen",
  Fastening: "Fastening",
  WornClosed: "WornClosed",
  Removing: "Removing",
  Dropped: "Dropped",
  Laundry: "Laundry",
});
const DRESS_SHIRT_CLOSET_POSITION = new THREE.Vector3(ONE_BEDROOM_ROOM_SPLIT_X - 0.48, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_HOUSE_FRONT_Z - 1.55);
const DRESS_SHIRT_CLOSET_YAW = -Math.PI / 2;
const STARBUCKS_CENTER = new THREE.Vector3(-26.4, ACTIVE_AVATAR_GROUND_Y, 43.2);
const STARBUCKS_WIDTH = 18.6;
const STARBUCKS_DEPTH = 12.8;
const STARBUCKS_FRONT_Z = STARBUCKS_CENTER.z + STARBUCKS_DEPTH / 2;
const STARBUCKS_REAR_Z = STARBUCKS_CENTER.z - STARBUCKS_DEPTH / 2;
const STARBUCKS_PUBLIC_FRONT_Z = STARBUCKS_REAR_Z;
const STARBUCKS_ENTRY = new THREE.Vector3(STARBUCKS_CENTER.x, ACTIVE_AVATAR_GROUND_Y, STARBUCKS_PUBLIC_FRONT_Z - 0.95);
const STARBUCKS_COUNTER_SPOT = new THREE.Vector3(STARBUCKS_CENTER.x + 1.15, ACTIVE_AVATAR_GROUND_Y, STARBUCKS_CENTER.z + 2.35);
const STARBUCKS_SEAT_SPOT = new THREE.Vector3(STARBUCKS_CENTER.x - 2.65, ACTIVE_AVATAR_GROUND_Y, STARBUCKS_PUBLIC_FRONT_Z + 5.15);
const PARK_BASKETBALL_CENTER = new THREE.Vector3(64.0, ACTIVE_AVATAR_GROUND_Y, 67.0);
const PARK_BASKETBALL_COURT_WIDTH = 19.0;
const PARK_BASKETBALL_COURT_DEPTH = 25.5;
const BASKETBALL_BALL_REST_SPOT = new THREE.Vector3(PARK_BASKETBALL_CENTER.x - 1.35, ACTIVE_AVATAR_GROUND_Y, PARK_BASKETBALL_CENTER.z - 1.1);
const BASKETBALL_DRIBBLE_SPOT = new THREE.Vector3(PARK_BASKETBALL_CENTER.x - 1.0, ACTIVE_AVATAR_GROUND_Y, PARK_BASKETBALL_CENTER.z - 1.2);
const BASKETBALL_SHOT_TARGET = new THREE.Vector3(PARK_BASKETBALL_CENTER.x - 8.2, ACTIVE_AVATAR_GROUND_Y + 3.05, PARK_BASKETBALL_CENTER.z - 10.1);
const BASKETBALL_BENCH_SIT_SPOT = new THREE.Vector3(PARK_BASKETBALL_CENTER.x - 5.9, ACTIVE_AVATAR_GROUND_Y, PARK_BASKETBALL_CENTER.z + 10.35);
const SCHOOL_CENTER = new THREE.Vector3(78.0, ACTIVE_AVATAR_GROUND_Y, 22.0);
const SCHOOL_WIDTH = 14.0;
const SCHOOL_DEPTH = 10.5;
const SCHOOL_FRONT_Z = SCHOOL_CENTER.z - SCHOOL_DEPTH / 2;
const SCHOOL_ENTRY = new THREE.Vector3(SCHOOL_CENTER.x, ACTIVE_AVATAR_GROUND_Y, SCHOOL_FRONT_Z - 1.15);
const SCHOOL_DESK_SPOT = new THREE.Vector3(SCHOOL_CENTER.x - 2.2, ACTIVE_AVATAR_GROUND_Y, SCHOOL_CENTER.z + 0.6);
const SCHOOL_SEAT_SPOT = new THREE.Vector3(SCHOOL_DESK_SPOT.x, ACTIVE_AVATAR_GROUND_Y, SCHOOL_DESK_SPOT.z - 0.95);
const SCHOOL_SEAT_YAW = 0;
let importedHouseReference = null;
let importedHouseReferenceStatus = {
  loaded: false,
  url: REALISTIC_HOUSE_MODEL_URL,
  disabled: !MAIN_TWO_STORY_HOUSE_ENABLED,
  disabledReason: "Two-story main house removed from the active one-bedroom repair pass.",
};
let realisticToiletSource = null;
let realisticToiletLoading = false;
const pendingRealisticToilets = [];
let realisticSofaStatus = { loaded: false, url: REALISTIC_SOFA_MODEL_URL };
let realisticBookshelfStatus = { loaded: false, url: REALISTIC_BOOKSHELF_MODEL_URL };
let realisticHomeBookshelf = null;
let neighborEntryDoorReference = null;
let neighborHouseDoorOpen = false;
let neighborFallbackDoorGroup = null;
let neighborHouseDoorLeaf = null;
let neighborBedReferenceSource = null;
let neighborApartmentReferenceScene = null;
let neighborBedReferenceLoading = false;
const pendingNeighborBedPlacements = [];
const pendingNeighborApartmentNodePlacements = [];
const pendingNeighborDoorPanelPlacements = [];
const neighborImportedFrontDoorVisuals = [];
const neighborPrefabSourceCache = new Map();
const pendingNeighborPrefabPlacements = new Map();
const oneBedroomPrefabSourceCache = new Map();
const pendingOneBedroomPrefabPlacements = new Map();
const kiraBungalowSourceCache = new Map();
const pendingKiraBungalowPlacements = new Map();
const homeWorldActivitySourceCache = new Map();
const pendingHomeWorldActivityPlacements = new Map();
let kiraBungalowDoorOpen = true;
let kiraBungalowDoorLeaf = null;
let starbucksDoorOpen = true;
let starbucksDoorLeaf = null;
let basketballBallRoot = null;
let basketballBallBaseY = 0.28;
let basketballBounceUntil = 0;
let basketballPracticeState = null;
let homeWorldSunRoot = null;
let homeWorldMoonRoot = null;
let homeWorldSkyMixer = null;
let homeWorldSkyMode = "day";
let activeKiraEyeRig = null;
let activeKiraEyeTestState = null;
let activeKiraMouthLipSyncRig = null;
let activeVoicePlaybackState = {
  revision: 0,
  active: false,
  playing: false,
  phase: "idle",
  candidate: "",
  label: "",
  chunkIndex: null,
};
let activeKiraMouthPlaybackEvidence = {
  matchedPlaybackSegments: 0,
  matchedPlaybackFrames: 0,
  currentPlaybackFrames: 0,
  lastMatchedRevision: 0,
  lastCompletedPlaybackFrames: 0,
  lastPlaybackPeakAmount: 0,
  lastPlaybackPeakOpeningDistance: 0,
};
let activeVoiceExpressionOwnsTalkingAction = false;
let activeVoiceExpressionReleaseAt = -Infinity;
let activeKiraArmTestState = null;
let activeKiraDoctorExamState = null;
let activeKiraDreamState = null;
let kiraStagedEyeRigSource = null;
let kiraStagedEyeRigLoading = false;
let activeKiraHairRig = null;
let kiraHairReferenceSource = null;
let kiraHairReferenceLoading = false;
let prototypeCloset = null;
let prototypeDressShirt = null;
let avatarDressingController = null;
const starbucksTemporaryCups = [];
let kiraBungalowStatus = {
  enabled: KIRA_BUNGALOW_ENABLED,
  interiorUrl: KIRA_BUNGALOW_INTERIOR_MODEL_URL,
  exteriorUrl: KIRA_BUNGALOW_EXTERIOR_MODEL_URL,
  position: { x: KIRA_BUNGALOW_CENTER.x, z: KIRA_BUNGALOW_CENTER.z },
  room: "Kira moved into the one-bedroom home; the old temporary studio is deleted from the runtime scene and no longer spawns.",
  phone: "Kira's temporary tablet and Samsung remote are on the one-bedroom coffee table.",
};
let neighborHouseReferenceStatus = {
  loaded: false,
  disabled: !NEIGHBOR_BLUEPRINT_HOUSE_ENABLED,
  disabledReason: "World builder paused after Robert rejected the generated neighbor house; no generated neighbor house should spawn now.",
  houseReferenceUrl: NEIGHBOR_HOUSE_REFERENCE_MODEL_URL,
  entryDoorUrl: NEIGHBOR_ENTRY_DOOR_MODEL_URL,
  bedSourceUrl: NEIGHBOR_BED_SOURCE_MODEL_URL,
  livingRoomFurnitureUrl: NEIGHBOR_LIVING_ROOM_FURNITURE_MODEL_URL,
  prefabBedFrameUrl: NEIGHBOR_PREFAB_BED_FRAME_MODEL_URL,
  prefabMattressUrl: NEIGHBOR_PREFAB_MATTRESS_MODEL_URL,
  prefabPillowUrl: NEIGHBOR_PREFAB_PILLOW_MODEL_URL,
  prefabBookUrl: NEIGHBOR_PREFAB_BOOK_MODEL_URL,
};
let oneBedroomBlueprintHouseStatus = {
  enabled: ONE_BEDROOM_BLUEPRINT_HOUSE_ENABLED,
  source: "Robert supplied 26x19 one-bedroom blueprint screenshot",
  position: { x: ONE_BEDROOM_HOUSE_CENTER.x, z: ONE_BEDROOM_HOUSE_CENTER.z },
  rule: "No door leaves yet and no glass panes in windows; openings are intentionally empty for inspection.",
  exteriorMaterial: "Starbucks-style red brick test material using saved brick/courses.",
  importedFurniture: {
    sofa: REALISTIC_SOFA_MODEL_URL,
    bedFrame: ONE_BEDROOM_WOOD_BED_FRAME_MODEL_URL,
    mattress: "temporary white procedural mattress placeholder; imported mattress GLB rendered invisible in this bed",
    pillow: "temporary procedural pillow blocks oriented across the headboard",
    tv: ONE_BEDROOM_TV_MODEL_URL,
    tvRemote: ONE_BEDROOM_TV_REMOTE_MODEL_URL,
    bathShower: ONE_BEDROOM_BATH_SHOWER_MODEL_URL,
    libraryBook: ONE_BEDROOM_LIBRARY_BOOK_MODEL_URL,
  },
};
let oneBedroomBedroomDresserOpen = false;
let oneBedroomBedroomDresserParts = null;
let oneBedroomHangingClosetOpen = false;
let oneBedroomHangingClosetParts = null;
let oneBedroomFridgeOpen = false;
let oneBedroomFridgeDoorGroup = null;
let oneBedroomFridgeInteriorParts = [];
let oneBedroomTvMusicPlaying = false;
let oneBedroomCopyReplicationArmed = false;
let captureFlagParkingLotBuilt = false;
let homeWorldActivityStatus = {
  preRamLightMode: {
    enabled: HOME_WORLD_PRE_RAM_LIGHT_MODE,
    restoreSwitch: "add ?fullWorld=1 after confirming the added RAM is installed and Windows reads both sticks",
  },
  starbucks: { loaded: false, url: HOME_WORLD_STARBUCKS_MODEL_URL, position: { x: STARBUCKS_CENTER.x, z: STARBUCKS_CENTER.z } },
  coffeeCup: { loaded: true, url: "procedural Starbucks counter cup placeholder; imported cup model origin/placement was unreliable" },
  basketballCourt: { loaded: false, url: HOME_WORLD_BASKETBALL_COURT_MODEL_URL, position: { x: PARK_BASKETBALL_CENTER.x, z: PARK_BASKETBALL_CENTER.z } },
  basketball: { loaded: false, url: HOME_WORLD_BASKETBALL_MODEL_URL },
  schoolClassroom: { loaded: false, url: HOME_WORLD_SCHOOL_CLASSROOM_MODEL_URL, position: { x: SCHOOL_CENTER.x, z: SCHOOL_CENTER.z } },
  schoolDeskTable: { loaded: false, url: HOME_WORLD_SCHOOL_TABLE_MODEL_URL },
  schoolChair: { loaded: false, url: HOME_WORLD_SCHOOL_CHAIR_MODEL_URL },
  schoolWorldMap: { loaded: false, url: HOME_WORLD_SCHOOL_WORLD_MAP_MODEL_URL },
  schoolBoard: { loaded: false, url: HOME_WORLD_SCHOOL_BOARD_MODEL_URL },
  schoolLockers: { loaded: false, url: HOME_WORLD_SCHOOL_LOCKERS_MODEL_URL },
  schoolClock: { loaded: false, url: HOME_WORLD_SCHOOL_CLOCK_MODEL_URL },
  schoolPencils: { loaded: false, url: HOME_WORLD_SCHOOL_PENCILS_MODEL_URL },
  schoolScrapbook: { loaded: false, url: HOME_WORLD_SCHOOL_SCRAPBOOK_MODEL_URL },
  realGrassPatches: { loaded: false, enabled: HOME_WORLD_HIGH_DETAIL_GRASS_PATCHES, url: HOME_WORLD_REAL_GRASS_PATCH_MODEL_URL },
  kiraReddishHair: { loaded: false, url: KIRA_REDDISH_HAIR_MODEL_URL },
  sun: { loaded: false, url: HOME_WORLD_SUN_MODEL_URL },
  moon: { loaded: false, url: HOME_WORLD_MOON_MODEL_URL },
  animatedDoorWindowReference: { loaded: false, url: HOME_WORLD_ANIMATED_DOOR_WINDOW_MODEL_URL },
  legacyStripMall: {
    enabled: HOME_WORLD_LEGACY_STRIP_MALL_ENABLED,
    loaded: false,
    mode: HOME_WORLD_LEGACY_STRIP_MALL_ENABLED ? "legacy_opt_in" : "empty_lot_default",
    sourceDeleted: false,
    spaPlacedHere: false,
    restoreSwitch: "add ?stripMall=1 to the Home World URL for the preserved legacy strip-mall scene",
    staticCost: LEGACY_STRIP_MALL_STATIC_COST,
  },
};

function markPreRamAssetSkipped(role, details = {}) {
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    [role]: {
      ...(homeWorldActivityStatus[role] || {}),
      loaded: false,
      skipped: true,
      disabledReason: "pre-RAM light mode keeps VRAM/RAM available for Kira's mind and Chatterbox voice",
      restoreSwitch: "open Home World with ?fullWorld=1 after confirming the RAM upgrade",
      ...details,
    },
  };
}
let neighborDoorStatus = {
  initialized: false,
  position: { x: 0, z: 0 },
};
let vanityWaterOn = false;
let tubWaterOn = false;
let downstairsPowderSinkWaterOn = false;
const vanityWaterMeshes = [];
const tubWaterMeshes = [];
const downstairsPowderSinkWaterMeshes = [];
let lisaBathDoorLocked = false;
let ladybugBathDoorLocked = false;
let lisaBathDoorOpen = false;
let ladybugBathDoorOpen = false;
let lisaBathDoorGroup = null;
let ladybugBathDoorGroup = null;
let kitchenFridgeDoorGroup = null;
let kitchenFridgeDoorOpen = false;
const interiorDoorOpen = new Map();
const interiorDoorGroups = new Map();
let activeHeldProp = null;
let activeHeldPropKind = "";
let backyardPoolWater = null;
let backyardPoolSplash = null;
const backyardPoolBounds = { xMin: -4.82, xMax: 4.82, zMin: -21.58, zMax: -15.42 };
const marinetteRoamWaypoints = [
  new THREE.Vector3(-1.2, ACTIVE_AVATAR_GROUND_Y, 4.85),
  new THREE.Vector3(-4.25, ACTIVE_AVATAR_GROUND_Y, 1.85),
  new THREE.Vector3(-4.2, ACTIVE_AVATAR_GROUND_Y, -4.35),
  new THREE.Vector3(0.15, ACTIVE_AVATAR_GROUND_Y, 8.45),
  new THREE.Vector3(0.0, ACTIVE_AVATAR_GROUND_Y, 16.6),
  new THREE.Vector3(24.0, ACTIVE_AVATAR_GROUND_Y, 29.4),
  new THREE.Vector3(24.0, ACTIVE_AVATAR_GROUND_Y, 37.6),
  new THREE.Vector3(24.0, ACTIVE_AVATAR_GROUND_Y, 40.7),
  new THREE.Vector3(22.4, ACTIVE_AVATAR_GROUND_Y, 45.2),
  new THREE.Vector3(24.0, ACTIVE_AVATAR_GROUND_Y, 40.7),
  new THREE.Vector3(24.0, ACTIVE_AVATAR_GROUND_Y, 37.6),
  new THREE.Vector3(0.0, ACTIVE_AVATAR_GROUND_Y, 16.6),
  new THREE.Vector3(-1.2, ACTIVE_AVATAR_GROUND_Y, 4.85),
];
const marinetteStairPracticeWaypoints = [
  new THREE.Vector3(1.9, ACTIVE_AVATAR_GROUND_Y, 2.95),
  new THREE.Vector3(1.9, ACTIVE_AVATAR_SECOND_FLOOR_Y, -1.65),
  new THREE.Vector3(2.55, ACTIVE_AVATAR_SECOND_FLOOR_Y, -1.95),
];
const marinetteUpstairsWaypoints = [
  new THREE.Vector3(2.55, ACTIVE_AVATAR_SECOND_FLOOR_Y, -1.95),
  new THREE.Vector3(2.55, ACTIVE_AVATAR_SECOND_FLOOR_Y, -4.85),
  new THREE.Vector3(3.65, ACTIVE_AVATAR_SECOND_FLOOR_Y, -5.35),
  new THREE.Vector3(5.35, ACTIVE_AVATAR_SECOND_FLOOR_Y, -5.35),
  new THREE.Vector3(6.62, ACTIVE_AVATAR_SECOND_FLOOR_Y, -4.16),
  new THREE.Vector3(6.34, ACTIVE_AVATAR_SECOND_FLOOR_Y, -4.12),
  new THREE.Vector3(5.35, ACTIVE_AVATAR_SECOND_FLOOR_Y, -5.35),
  new THREE.Vector3(3.65, ACTIVE_AVATAR_SECOND_FLOOR_Y, -5.35),
  new THREE.Vector3(2.55, ACTIVE_AVATAR_SECOND_FLOOR_Y, -4.85),
];
const kiraUpstairsWaypoints = [
  new THREE.Vector3(-4.08, ACTIVE_AVATAR_SECOND_FLOOR_Y, 4.16),
  new THREE.Vector3(-3.02, ACTIVE_AVATAR_SECOND_FLOOR_Y, 5.12),
  new THREE.Vector3(-1.44, ACTIVE_AVATAR_SECOND_FLOOR_Y, 5.12),
  new THREE.Vector3(-1.44, ACTIVE_AVATAR_SECOND_FLOOR_Y, 5.12),
  new THREE.Vector3(-3.02, ACTIVE_AVATAR_SECOND_FLOOR_Y, 5.12),
];
const kiraBungalowWaypoints = [
  KIRA_BUNGALOW_SPAWN.clone(),
  KIRA_BED_STAND_SPOT.clone(),
  KIRA_BUNGALOW_FRONT_OUTSIDE.clone(),
  KIRA_BUNGALOW_SPAWN.clone(),
];
const kiraHomeWorldWaypoints = [
  KIRA_BUNGALOW_SPAWN.clone(),
  KIRA_BUNGALOW_FRONT_OUTSIDE.clone(),
  new THREE.Vector3(24.0, ACTIVE_AVATAR_GROUND_Y, 16.8),
  new THREE.Vector3(16.5, ACTIVE_AVATAR_GROUND_Y, 27.4),
  new THREE.Vector3(22.4, ACTIVE_AVATAR_GROUND_Y, 33.4),
  new THREE.Vector3(24.2, ACTIVE_AVATAR_GROUND_Y, 41.6),
  new THREE.Vector3(18.5, ACTIVE_AVATAR_GROUND_Y, 29.2),
  new THREE.Vector3(-7.5, ACTIVE_AVATAR_GROUND_Y, 27.4),
  new THREE.Vector3(-20.4, ACTIVE_AVATAR_GROUND_Y, STARBUCKS_PUBLIC_FRONT_Z - 1.0),
  STARBUCKS_ENTRY.clone(),
  STARBUCKS_SEAT_SPOT.clone(),
  STARBUCKS_ENTRY.clone(),
  new THREE.Vector3(16.5, ACTIVE_AVATAR_GROUND_Y, 27.4),
  KIRA_BUNGALOW_FRONT_OUTSIDE.clone(),
  KIRA_BUNGALOW_SPAWN.clone(),
];
const activeAvatarCafeCoffeeWaypoints = [
  KIRA_BUNGALOW_SPAWN.clone(),
  KIRA_BUNGALOW_FRONT_OUTSIDE.clone(),
  new THREE.Vector3(24.0, ACTIVE_AVATAR_GROUND_Y, 16.8),
  new THREE.Vector3(16.5, ACTIVE_AVATAR_GROUND_Y, 27.4),
  new THREE.Vector3(-7.5, ACTIVE_AVATAR_GROUND_Y, 27.4),
  new THREE.Vector3(-20.4, ACTIVE_AVATAR_GROUND_Y, STARBUCKS_PUBLIC_FRONT_Z - 1.0),
  STARBUCKS_ENTRY.clone(),
  STARBUCKS_COUNTER_SPOT.clone(),
];

function pointInsideHudRegion(position, cx, cz, sx, sz, margin = 0) {
  return position.x >= cx - sx / 2 - margin
    && position.x <= cx + sx / 2 + margin
    && position.z >= cz - sz / 2 - margin
    && position.z <= cz + sz / 2 + margin;
}

function homeWorldHudTitleForPosition(position = player.position) {
  for (const config of ONE_BEDROOM_HOME_WORLD_CONFIGS) {
    if (pointInsideHudRegion(position, ONE_BEDROOM_HOUSE_CENTER.x + config.offsetX, ONE_BEDROOM_HOUSE_CENTER.z + (config.offsetZ || 0), ONE_BEDROOM_HOUSE_WIDTH, ONE_BEDROOM_HOUSE_DEPTH, 1.4)) {
      return config.title;
    }
  }
  if (pointInsideHudRegion(position, 24.2, 41.2, 15.0, 15.0, 1.5)) return "Library";
  if (pointInsideHudRegion(position, STARBUCKS_CENTER.x, STARBUCKS_CENTER.z, STARBUCKS_WIDTH, STARBUCKS_DEPTH, 3.0)) return "Starbucks";
  if (pointInsideHudRegion(position, SCHOOL_CENTER.x, SCHOOL_CENTER.z, SCHOOL_WIDTH, SCHOOL_DEPTH, 2.2)) return "Home World School";
  if (captureFlagPointInBounds(position)) return "Capture The Flag World";
  return "Home World";
}

function updateHomeWorldHudLocationTitle() {
  if (!hudLocationTitle) return;
  const nextTitle = homeWorldHudTitleForPosition(player.position);
  if (hudLocationTitle.textContent !== nextTitle) hudLocationTitle.textContent = nextTitle;
}
const activeAvatarBasketballPracticeWaypoints = [
  KIRA_BUNGALOW_SPAWN.clone(),
  KIRA_BUNGALOW_FRONT_OUTSIDE.clone(),
  new THREE.Vector3(42.0, ACTIVE_AVATAR_GROUND_Y, 29.2),
  new THREE.Vector3(60.0, ACTIVE_AVATAR_GROUND_Y, 35.6),
  new THREE.Vector3(PARK_BASKETBALL_CENTER.x - 4.6, ACTIVE_AVATAR_GROUND_Y, PARK_BASKETBALL_CENTER.z - 9.4),
  BASKETBALL_DRIBBLE_SPOT.clone(),
];
const activeAvatarSchoolStudyWaypoints = [
  KIRA_BUNGALOW_SPAWN.clone(),
  KIRA_BUNGALOW_FRONT_OUTSIDE.clone(),
  new THREE.Vector3(42.0, ACTIVE_AVATAR_GROUND_Y, 24.4),
  new THREE.Vector3(60.5, ACTIVE_AVATAR_GROUND_Y, 24.0),
  SCHOOL_ENTRY.clone(),
  SCHOOL_SEAT_SPOT.clone(),
];
const genericHomeRoamWaypoints = [
  new THREE.Vector3(-0.6, ACTIVE_AVATAR_GROUND_Y, 8.8),
  new THREE.Vector3(-2.7, ACTIVE_AVATAR_GROUND_Y, 11.2),
  new THREE.Vector3(1.9, ACTIVE_AVATAR_GROUND_Y, 13.3),
  new THREE.Vector3(7.8, ACTIVE_AVATAR_GROUND_Y, 18.8),
  new THREE.Vector3(15.5, ACTIVE_AVATAR_GROUND_Y, 26.2),
  new THREE.Vector3(23.6, ACTIVE_AVATAR_GROUND_Y, 34.4),
  new THREE.Vector3(24.0, ACTIVE_AVATAR_GROUND_Y, 39.7),
  new THREE.Vector3(18.8, ACTIVE_AVATAR_GROUND_Y, 31.6),
  new THREE.Vector3(8.5, ACTIVE_AVATAR_GROUND_Y, 20.4),
];
const spiderHeroRoamWaypoints = [
  new THREE.Vector3(0.9, ACTIVE_AVATAR_GROUND_Y, 5.8),
  new THREE.Vector3(-2.4, ACTIVE_AVATAR_GROUND_Y, 4.1),
  new THREE.Vector3(-4.2, ACTIVE_AVATAR_GROUND_Y, 1.85),
  new THREE.Vector3(-1.0, ACTIVE_AVATAR_GROUND_Y, 8.8),
  new THREE.Vector3(2.2, ACTIVE_AVATAR_GROUND_Y, 12.8),
  new THREE.Vector3(6.8, ACTIVE_AVATAR_GROUND_Y, 17.0),
  new THREE.Vector3(12.6, ACTIVE_AVATAR_GROUND_Y, 22.4),
  new THREE.Vector3(18.2, ACTIVE_AVATAR_GROUND_Y, 27.8),
  new THREE.Vector3(13.6, ACTIVE_AVATAR_GROUND_Y, 24.1),
  new THREE.Vector3(4.4, ACTIVE_AVATAR_GROUND_Y, 15.8),
];
const spiderIndoorRoamWaypoints = [
  new THREE.Vector3(-4.92, ACTIVE_AVATAR_SECOND_FLOOR_Y, -4.95),
  new THREE.Vector3(-2.65, ACTIVE_AVATAR_SECOND_FLOOR_Y, -4.62),
  new THREE.Vector3(-1.45, ACTIVE_AVATAR_SECOND_FLOOR_Y, -1.32),
  new THREE.Vector3(-4.9, ACTIVE_AVATAR_SECOND_FLOOR_Y, 4.72),
  new THREE.Vector3(-6.12, ACTIVE_AVATAR_SECOND_FLOOR_Y, 5.65),
  new THREE.Vector3(-3.25, ACTIVE_AVATAR_SECOND_FLOOR_Y, 0.65),
  new THREE.Vector3(0.4, ACTIVE_AVATAR_SECOND_FLOOR_Y, 0.2),
];
const libraryVisitorRoamWaypoints = [
  new THREE.Vector3(24.2, ACTIVE_AVATAR_GROUND_Y, 39.2),
  new THREE.Vector3(22.4, ACTIVE_AVATAR_GROUND_Y, 45.2),
  new THREE.Vector3(24.7, ACTIVE_AVATAR_GROUND_Y, 43.0),
  new THREE.Vector3(26.2, ACTIVE_AVATAR_GROUND_Y, 40.0),
  new THREE.Vector3(23.5, ACTIVE_AVATAR_GROUND_Y, 37.2),
];
const captureFlagRoamWaypoints = [
  new THREE.Vector3(108, ACTIVE_AVATAR_GROUND_Y, 96),
  new THREE.Vector3(114, ACTIVE_AVATAR_GROUND_Y, 101),
  new THREE.Vector3(116, ACTIVE_AVATAR_GROUND_Y, 113),
  new THREE.Vector3(108, ACTIVE_AVATAR_GROUND_Y, 106),
];
const activeAvatarJogPracticeWaypoints = [
  new THREE.Vector3(-1.1, ACTIVE_AVATAR_GROUND_Y, 11.8),
  new THREE.Vector3(3.0, ACTIVE_AVATAR_GROUND_Y, 14.8),
  new THREE.Vector3(7.6, ACTIVE_AVATAR_GROUND_Y, 18.6),
  new THREE.Vector3(3.2, ACTIVE_AVATAR_GROUND_Y, 15.0),
  new THREE.Vector3(-1.1, ACTIVE_AVATAR_GROUND_Y, 11.8),
];
const activeAvatarRunPracticeWaypoints = [
  new THREE.Vector3(-3.5, ACTIVE_AVATAR_GROUND_Y, 15.8),
  new THREE.Vector3(4.8, ACTIVE_AVATAR_GROUND_Y, 18.1),
  new THREE.Vector3(12.4, ACTIVE_AVATAR_GROUND_Y, 22.8),
  new THREE.Vector3(18.6, ACTIVE_AVATAR_GROUND_Y, 27.8),
  new THREE.Vector3(10.2, ACTIVE_AVATAR_GROUND_Y, 22.4),
  new THREE.Vector3(1.4, ACTIVE_AVATAR_GROUND_Y, 16.0),
];
const activeAvatarLibraryReadWaypoints = [
  new THREE.Vector3(23.1, ACTIVE_AVATAR_GROUND_Y, 41.8),
  new THREE.Vector3(21.8, ACTIVE_AVATAR_GROUND_Y, 44.05),
];
const activeAvatarSwimPracticeWaypoints = [
  new THREE.Vector3(-3.4, 0.12, -16.2),
  new THREE.Vector3(3.4, 0.12, -16.2),
  new THREE.Vector3(3.4, 0.12, -20.7),
  new THREE.Vector3(-3.4, 0.12, -20.7),
  new THREE.Vector3(-3.4, 0.12, -16.2),
];
const MARINETTE_SKIN_COLOR = 0xf0c7ba;
const marinetteRoamPracticeStops = new Map();
const marinetteUpstairsPracticeStops = new Map();
let activeAvatarSelfTest = null;
let activeAvatarSelfTestAutoStarted = false;
const ACTIVE_AVATAR_AUTO_SELF_TEST = params.get("selftest") === "1";
const ACTIVE_AVATAR_AUTO_PRACTICE_STOPS = params.get("practice") === "1" || ACTIVE_AVATAR_AUTO_SELF_TEST;
const HOME_TARDIS_ARRIVED =
  params.get("arrival") === "tardis" || params.get("tardis") === "arrived" || startArea === "tardis_arrival";
const CAPTURE_FLAG_STORMTROOPER_MODEL_URL = "/models/capture_flag/stormtrooper_rigged_game_ready.glb";
const CAPTURE_FLAG_DALEK_MODEL_URL = "/models/capture_flag/bronze_new_series_dalek_-_rigged.glb";
const CAPTURE_FLAG_TIME_CAR_MODEL_URL = "/models/capture_flag/back_to_the_future_time_machine_reference.glb";
const CAPTURE_FLAG_SEPARATE_NOTEBOOK_WORLD_PENDING = true;
const CAPTURE_FLAG_WORLD_ENABLED = false;
const captureFlagWorld = {
  homePortal: new THREE.Vector3(54.05, ACTIVE_AVATAR_GROUND_Y, 42.2),
  homeArrival: new THREE.Vector3(45.4, 1.65, 41.8),
  battlefieldArrival: new THREE.Vector3(100, 1.65, 96),
  activeBase: new THREE.Vector3(100, ACTIVE_AVATAR_GROUND_Y, 96),
  base: new THREE.Vector3(100, ACTIVE_AVATAR_GROUND_Y, 96),
  returnPortal: new THREE.Vector3(89.5, ACTIVE_AVATAR_GROUND_Y, 91.8),
  bounds: { xMin: 80, xMax: 238, zMin: 82, zMax: 248 },
  flagSpots: [
    new THREE.Vector3(190, ACTIVE_AVATAR_GROUND_Y, 212),
    new THREE.Vector3(220, ACTIVE_AVATAR_GROUND_Y, 226),
    new THREE.Vector3(206, ACTIVE_AVATAR_GROUND_Y, 184),
    new THREE.Vector3(174, ACTIVE_AVATAR_GROUND_Y, 232),
    new THREE.Vector3(229, ACTIVE_AVATAR_GROUND_Y, 166),
    new THREE.Vector3(182, ACTIVE_AVATAR_GROUND_Y, 194),
    new THREE.Vector3(212, ACTIVE_AVATAR_GROUND_Y, 238),
  ],
};
let captureFlagState = {
  actor: null,
  phase: "idle",
  flagIndex: -1,
  flagCarried: false,
  captures: 0,
  tags: 0,
  bestSeconds: null,
  startedAt: 0,
  lastEvent: "not_started",
  dodges: 0,
};
let captureFlagFlagGroup = null;
let captureFlagFlagLight = null;
let captureFlagHomePortalCooldownUntil = 0;
let captureFlagReturnPortalCooldownUntil = 0;
let captureFlagBattlefieldGroup = null;
const captureFlagNpcs = [];
const captureFlagNpcModels = { stormtrooper: null, dalek: null };
const captureFlagNpcLoading = { stormtrooper: false, dalek: false };
let captureFlagTimeCarSource = null;
let captureFlagTimeCarLoading = false;
const pendingCaptureFlagTimeCars = [];
let observeFollowEnabled = false;
let observeFollowButton = null;
let observationReportState = {
  running: false,
  startedAt: 0,
  intervalSeconds: 60,
  nextAt: 0,
  samples: [],
};

function makeProceduralBrickTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#7f3f34";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const brickH = 28;
  const brickW = 92;
  for (let y = 0; y < canvas.height; y += brickH) {
    const row = Math.floor(y / brickH);
    const offset = row % 2 ? -brickW * 0.5 : 0;
    ctx.fillStyle = "#b6a995";
    ctx.fillRect(0, y, canvas.width, 3);
    for (let x = offset; x < canvas.width + brickW; x += brickW) {
      const shade = 92 + ((row * 17 + Math.floor(x / brickW) * 23) % 36);
      ctx.fillStyle = `rgb(${shade + 34}, ${Math.max(44, shade - 12)}, ${Math.max(34, shade - 22)})`;
      ctx.fillRect(x + 3, y + 4, brickW - 6, brickH - 7);
      ctx.fillStyle = "rgba(255,255,255,0.08)";
      ctx.fillRect(x + 8, y + 6, brickW - 18, 3);
      ctx.fillStyle = "#b6a995";
      ctx.fillRect(x, y, 3, brickH);
    }
  }
  ctx.fillStyle = "rgba(45,20,16,0.18)";
  for (let i = 0; i < 90; i += 1) {
    const x = (i * 71) % canvas.width;
    const y = (i * 37) % canvas.height;
    ctx.fillRect(x, y, 2 + (i % 4), 1 + (i % 3));
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(3.2, 1.5);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

const proceduralRedBrickTexture = makeProceduralBrickTexture();

const materials = {
  grass: new THREE.MeshStandardMaterial({ color: 0x5f8b4f, roughness: 0.96 }),
  asphalt: new THREE.MeshStandardMaterial({ color: 0x4b5356, roughness: 0.88 }),
  sidewalk: new THREE.MeshStandardMaterial({ color: 0xb7b3a8, roughness: 0.78 }),
  exterior: new THREE.MeshStandardMaterial({ color: 0xe7ddc8, roughness: 0.72 }),
  wall: new THREE.MeshStandardMaterial({ color: 0xf3ebdd, roughness: 0.74 }),
  schoolWall: new THREE.MeshStandardMaterial({ color: 0xdad5c8, roughness: 0.86 }),
  schoolAccent: new THREE.MeshStandardMaterial({ color: 0x34434a, roughness: 0.72 }),
  kiraHairAuburn: new THREE.MeshStandardMaterial({ color: 0x7d3026, roughness: 0.58 }),
  trim: new THREE.MeshStandardMaterial({ color: 0x35424c, roughness: 0.72 }),
  floor: new THREE.MeshStandardMaterial({ color: 0xd8c5a2, roughness: 0.68 }),
  secondFloor: new THREE.MeshStandardMaterial({ color: 0xc9d7e1, roughness: 0.72 }),
  glass: new THREE.MeshStandardMaterial({
    color: 0xaed3dc,
    transparent: true,
    opacity: 0.08,
    roughness: 0.08,
    metalness: 0.02,
    depthWrite: false,
    side: THREE.DoubleSide,
  }),
  transomGlass: new THREE.MeshStandardMaterial({
    color: 0xbfe8f0,
    transparent: true,
    opacity: 0.12,
    roughness: 0.05,
    metalness: 0.01,
    depthWrite: false,
    side: THREE.DoubleSide,
  }),
  door: new THREE.MeshStandardMaterial({ color: 0x41555c, roughness: 0.42 }),
  windowFrame: new THREE.MeshStandardMaterial({ color: 0x26333a, roughness: 0.55 }),
  handle: new THREE.MeshStandardMaterial({ color: 0xd6b24c, metalness: 0.45, roughness: 0.38 }),
  fixture: new THREE.MeshStandardMaterial({ color: 0xf1f4f2, roughness: 0.45 }),
  counter: new THREE.MeshStandardMaterial({ color: 0xc3a77c, roughness: 0.58 }),
  cabinet: new THREE.MeshStandardMaterial({ color: 0x927a55, roughness: 0.62 }),
  mirror: new THREE.MeshStandardMaterial({ color: 0xdde8ea, metalness: 0.72, roughness: 0.04 }),
  water: new THREE.MeshStandardMaterial({ color: 0x8ecfe7, transparent: true, opacity: 0.38, roughness: 0.08, metalness: 0.02 }),
  coffeeLiquid: new THREE.MeshStandardMaterial({ color: 0x2a0f07, transparent: true, opacity: 0.88, roughness: 0.28 }),
  coffeeGrounds: new THREE.MeshStandardMaterial({ color: 0x4a2414, roughness: 0.92 }),
  poolWater: new THREE.MeshStandardMaterial({ color: 0x5cc8dc, roughness: 0.12, metalness: 0.0, transparent: true, opacity: 0.78 }),
  curtain: new THREE.MeshStandardMaterial({ color: 0xd8e8ef, roughness: 0.72 }),
  wood: new THREE.MeshStandardMaterial({ color: 0x7a5133, roughness: 0.66 }),
  mattress: new THREE.MeshStandardMaterial({ color: 0xf3eff2, roughness: 0.62 }),
  blanketBlue: new THREE.MeshStandardMaterial({ color: 0x5f7fa8, roughness: 0.7 }),
  blanketPink: new THREE.MeshStandardMaterial({ color: 0xd79aaa, roughness: 0.72 }),
  paper: new THREE.MeshStandardMaterial({ color: 0xfffbef, roughness: 0.85 }),
  notebookCover: new THREE.MeshStandardMaterial({ color: 0x284d73, roughness: 0.7 }),
  designBoard: new THREE.MeshStandardMaterial({ color: 0xb99a72, roughness: 0.82 }),
  sketchInk: new THREE.MeshStandardMaterial({ color: 0x344456, roughness: 0.75 }),
  pencilWood: new THREE.MeshStandardMaterial({ color: 0xd5a45f, roughness: 0.58 }),
  screen: new THREE.MeshStandardMaterial({ color: 0x07111c, emissive: 0x102b45, emissiveIntensity: 0.45, roughness: 0.2 }),
  pursePink: new THREE.MeshStandardMaterial({ color: 0xf0a7c8, roughness: 0.5 }),
  purseInterior: new THREE.MeshStandardMaterial({ color: 0x8a1722, roughness: 0.58 }),
  purseBlack: new THREE.MeshStandardMaterial({ color: 0x09090b, roughness: 0.46 }),
  purseDot: new THREE.MeshStandardMaterial({ color: 0xfff4fb, roughness: 0.35 }),
  purseInk: new THREE.MeshStandardMaterial({ color: 0x171015, roughness: 0.55 }),
  purseRed: new THREE.MeshStandardMaterial({ color: 0xc5162a, roughness: 0.36 }),
  phoneBody: new THREE.MeshStandardMaterial({ color: 0x10151d, roughness: 0.32 }),
  phoneScreen: new THREE.MeshStandardMaterial({ color: 0x071522, emissive: 0x0d5a83, emissiveIntensity: 0.28, roughness: 0.16 }),
  spaWall: new THREE.MeshStandardMaterial({ color: 0xd8edf0, roughness: 0.66 }),
  spaAccent: new THREE.MeshStandardMaterial({ color: 0x8fb9c1, roughness: 0.55 }),
  mall: new THREE.MeshStandardMaterial({ color: 0xd6d0bf, roughness: 0.77 }),
  mallFront: new THREE.MeshStandardMaterial({ color: 0x627880, roughness: 0.5 }),
  line: new THREE.MeshBasicMaterial({ color: 0x304a5b }),
  activeBlue: new THREE.MeshStandardMaterial({ color: 0x18345a, roughness: 0.55 }),
  activeSkin: new THREE.MeshStandardMaterial({ color: 0xf2c5b5, roughness: 0.52 }),
  rugWarm: new THREE.MeshStandardMaterial({ color: 0x9b5f55, roughness: 0.86 }),
  rugBorder: new THREE.MeshStandardMaterial({ color: 0xf1d8a6, roughness: 0.82 }),
  livingWood: new THREE.MeshStandardMaterial({ color: 0x8a6845, roughness: 0.62 }),
  plantLeaf: new THREE.MeshStandardMaterial({ color: 0x3f7a4c, roughness: 0.78 }),
  lampShade: new THREE.MeshStandardMaterial({ color: 0xffe6a0, emissive: 0x5a4418, emissiveIntensity: 0.18, roughness: 0.5 }),
  pillowGold: new THREE.MeshStandardMaterial({ color: 0xdbb86a, roughness: 0.68 }),
  pillowCoral: new THREE.MeshStandardMaterial({ color: 0xc9746e, roughness: 0.7 }),
  artCanvas: new THREE.MeshStandardMaterial({ color: 0xe4dfd3, roughness: 0.74 }),
  fridgeWhite: new THREE.MeshStandardMaterial({ color: 0xf6f7f2, roughness: 0.42 }),
  brushedSteel: new THREE.MeshStandardMaterial({ color: 0x8f989b, metalness: 0.35, roughness: 0.34 }),
  burnerBlack: new THREE.MeshStandardMaterial({ color: 0x171b1d, roughness: 0.42 }),
  warmCabinet: new THREE.MeshStandardMaterial({ color: 0xa67f52, roughness: 0.64 }),
  produceRed: new THREE.MeshStandardMaterial({ color: 0xb84b42, roughness: 0.62 }),
  produceGreen: new THREE.MeshStandardMaterial({ color: 0x6f9b61, roughness: 0.72 }),
  produceYellow: new THREE.MeshStandardMaterial({ color: 0xe0bf55, roughness: 0.62 }),
  basketballOrange: new THREE.MeshStandardMaterial({ color: 0xc76a24, roughness: 0.72 }),
  basketballSeam: new THREE.MeshStandardMaterial({ color: 0x101010, roughness: 0.58 }),
  libraryWall: new THREE.MeshStandardMaterial({ color: 0xd9d2c2, roughness: 0.68 }),
  libraryStone: new THREE.MeshStandardMaterial({ color: 0xc8c0af, roughness: 0.76 }),
  libraryTrim: new THREE.MeshStandardMaterial({ color: 0x273942, roughness: 0.58 }),
  libraryWood: new THREE.MeshStandardMaterial({ color: 0x6d472d, roughness: 0.63 }),
  libraryCarpet: new THREE.MeshStandardMaterial({ color: 0x45696d, roughness: 0.86 }),
  bookRed: new THREE.MeshStandardMaterial({ color: 0x8f3542, roughness: 0.74 }),
  bookBlue: new THREE.MeshStandardMaterial({ color: 0x31597e, roughness: 0.74 }),
  bookGreen: new THREE.MeshStandardMaterial({ color: 0x4f7657, roughness: 0.74 }),
  bookGold: new THREE.MeshStandardMaterial({ color: 0xc2a35d, roughness: 0.65 }),
  mediaCase: new THREE.MeshStandardMaterial({ color: 0x1f252c, roughness: 0.54 }),
  pathGravel: new THREE.MeshStandardMaterial({ color: 0xb8b0a2, roughness: 0.9 }),
  tardisBlue: new THREE.MeshStandardMaterial({ color: 0x12395c, roughness: 0.55 }),
  tardisDark: new THREE.MeshStandardMaterial({ color: 0x071421, roughness: 0.6 }),
  tardisGlow: new THREE.MeshStandardMaterial({ color: 0xcdeeff, emissive: 0x91d8ff, emissiveIntensity: 0.35, roughness: 0.18 }),
  parkingStripe: new THREE.MeshBasicMaterial({ color: 0xece7d5 }),
  retroCarSteel: new THREE.MeshStandardMaterial({ color: 0xaeb8bb, metalness: 0.38, roughness: 0.32 }),
  retroCarGlass: new THREE.MeshStandardMaterial({ color: 0x8ed4ee, transparent: true, opacity: 0.38, roughness: 0.08, metalness: 0.12 }),
  ctfConcrete: new THREE.MeshStandardMaterial({ color: 0xa8a49a, roughness: 0.88 }),
  ctfAsphalt: new THREE.MeshStandardMaterial({ color: 0x343a3d, roughness: 0.92 }),
  ctfBrick: new THREE.MeshStandardMaterial({ color: 0x7c5448, roughness: 0.84 }),
  ctfRubble: new THREE.MeshStandardMaterial({ color: 0x77726a, roughness: 0.9 }),
  ctfBase: new THREE.MeshStandardMaterial({ color: 0x2f6f82, roughness: 0.72 }),
  ctfFlagGlow: new THREE.MeshStandardMaterial({ color: 0xffdf58, emissive: 0xffc400, emissiveIntensity: 1.45, roughness: 0.28 }),
  ctfFlagCloth: new THREE.MeshStandardMaterial({ color: 0xf7e66f, emissive: 0xffcf33, emissiveIntensity: 0.75, roughness: 0.4, side: THREE.DoubleSide }),
  ctfStormtrooper: new THREE.MeshStandardMaterial({ color: 0xf4f5ef, roughness: 0.48 }),
  ctfNpcBlack: new THREE.MeshStandardMaterial({ color: 0x15171a, roughness: 0.46 }),
  ctfDalekBronze: new THREE.MeshStandardMaterial({ color: 0x9b7043, metalness: 0.28, roughness: 0.38 }),
  ctfAlert: new THREE.MeshStandardMaterial({ color: 0xc02d2d, emissive: 0x5a0c0c, emissiveIntensity: 0.35, roughness: 0.56 }),
  neighborStone: new THREE.MeshStandardMaterial({ color: 0x8f897b, roughness: 0.88 }),
  neighborSiding: new THREE.MeshStandardMaterial({ color: 0xd8d0c2, roughness: 0.76 }),
  neighborSidingWarm: new THREE.MeshStandardMaterial({ color: 0xc8b58d, roughness: 0.78 }),
  neighborBrick: new THREE.MeshStandardMaterial({ color: 0xffffff, map: proceduralRedBrickTexture, roughness: 0.86 }),
  neighborRoof: new THREE.MeshStandardMaterial({ color: 0x25313a, roughness: 0.7 }),
  neighborShutter: new THREE.MeshStandardMaterial({ color: 0x233a42, roughness: 0.62 }),
  neighborDoorWood: new THREE.MeshStandardMaterial({ color: 0x6f472b, roughness: 0.58 }),
  neighborWarmLight: new THREE.MeshStandardMaterial({ color: 0xf8df95, emissive: 0xd49f37, emissiveIntensity: 0.24, roughness: 0.4 }),
  neighborWindowShade: new THREE.MeshStandardMaterial({ color: 0xf2e8d8, roughness: 0.82 }),
  shirtCotton: new THREE.MeshStandardMaterial({ color: 0xf3f7fb, roughness: 0.82 }),
  shirtInside: new THREE.MeshStandardMaterial({ color: 0xdfe8ef, roughness: 0.86, side: THREE.DoubleSide }),
  shirtSeam: new THREE.MeshStandardMaterial({ color: 0xa9b6c1, roughness: 0.78 }),
  shirtButton: new THREE.MeshStandardMaterial({ color: 0xfaf5df, roughness: 0.42 }),
  shirtButtonhole: new THREE.MeshStandardMaterial({ color: 0x4f5c65, roughness: 0.7 }),
  closetWood: new THREE.MeshStandardMaterial({ color: 0x856549, roughness: 0.7 }),
  closetInterior: new THREE.MeshStandardMaterial({ color: 0xead9c4, roughness: 0.78 }),
  closetRail: new THREE.MeshStandardMaterial({ color: 0xb6b1a6, metalness: 0.34, roughness: 0.38 }),
  hangerWire: new THREE.MeshStandardMaterial({ color: 0x4b5960, metalness: 0.28, roughness: 0.42 }),
  laundryBasket: new THREE.MeshStandardMaterial({ color: 0xb9a076, roughness: 0.78 }),
};

const PUBLIC_LIBRARY_CATALOG = [
  { kind: "book", title: "Alice's Adventures in Wonderland", source: "Data/library/novels" },
  { kind: "book", title: "The Adventures of Sherlock Holmes", source: "Data/library/novels" },
  { kind: "book", title: "The Time Machine", source: "Data/library/novels/science_fiction_and_fantasy" },
  { kind: "book", title: "The Hobbit", source: "Data/library/novels/science_fiction_and_fantasy" },
  { kind: "book", title: "Project Hail Mary", source: "Data/library/novels/science_fiction_and_fantasy" },
  { kind: "book", title: "The Martian", source: "Data/library/novels/science_fiction_and_fantasy" },
  { kind: "book", title: "The Odyssey", source: "Data/library/novels" },
  { kind: "book", title: "Pride and Prejudice", source: "Data/library/novels" },
  { kind: "book", title: "The Story of Coding", source: "Data/library/reference/artificial_intelligence_and_computing" },
  { kind: "book", title: "DK Eyewitness Computer", source: "Data/library/reference/artificial_intelligence_and_computing" },
  { kind: "book", title: "The Computer Book", source: "Data/library/reference/artificial_intelligence_and_computing" },
  { kind: "book", title: "AI With Python", source: "Data/library/reference/artificial_intelligence_and_computing" },
  { kind: "book", title: "Fashion Studies Guide", source: "Data/library/reference/fashion_and_style" },
  { kind: "book", title: "Creating Stylish", source: "Data/library/reference/fashion_and_style" },
  { kind: "book", title: "How Cooking Works", source: "Data/library/cooking/reference" },
  { kind: "book", title: "Mastering the Art of French Cooking", source: "Data/library/cooking/reference" },
  { kind: "book", title: "Nikola Tesla", source: "Data/library/biographies" },
  { kind: "book", title: "Complete Poems of Emily Dickinson", source: "Data/library/novels/poetry_and_plays" },
  { kind: "media", title: "Building an Artificial Intelligence Personal Assistant", source: "Data/library/documentaries" },
  { kind: "media", title: "Infinite Worlds: A Journey Through Parallel Universes", source: "Data/library/documentaries" },
  { kind: "media", title: "The LEGO Story: How It All Started", source: "Data/library/documentaries" },
  { kind: "media", title: "3 Time Travel Paradoxes", source: "Data/library/documentaries" },
];

function show(message) {
  toast.textContent = message;
}

function addBox(name, x, y, z, sx, sy, sz, material, collider = false, floor = null) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), material);
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  scene.add(mesh);
  if (collider) colliders.push({ x, z, sx, sz, floor });
  return mesh;
}

function addColliderOnly(x, z, sx, sz, floor, active = null) {
  doorColliders.push({ x, z, sx, sz, floor, active });
}

function floorBase(floor) {
  return floor ? 3.25 : 0.05;
}

function addCylinder(name, x, y, z, radius, height, material, collider = false, floor = null) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, height, 24), material);
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  scene.add(mesh);
  if (collider) colliders.push({ x, z, sx: radius * 2, sz: radius * 2, floor });
  return mesh;
}

function markTruthProp(obj, kind, label, floor = null, actionHints = []) {
  if (!obj) return obj;
  obj.userData = obj.userData || {};
  obj.userData.truthProp = {
    kind,
    label: label || obj.name || kind,
    floor,
    actionHints,
  };
  activityTruthProps.push(obj);
  return obj;
}

function garmentMesh(parent, name, x, y, z, sx, sy, sz, material, rotation = {}) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), material);
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.rotation.set(rotation.x || 0, rotation.y || 0, rotation.z || 0);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function garmentButton(parent, name, x, y, z, radius = 0.018) {
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius, 14, 8), materials.shirtButton);
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function garmentButtonhole(parent, name, x, y, z) {
  return garmentMesh(parent, name, x, y, z, 0.048, 0.007, 0.006, materials.shirtButtonhole);
}

function addDressShirtButtonSet(parent, z, closed = false) {
  const buttons = [];
  const buttonholes = [];
  for (let i = 0; i < 5; i += 1) {
    const y = 1.31 - i * 0.105;
    buttons.push(garmentButton(parent, `dress shirt ${closed ? "closed" : "open"} button ${i + 1}`, closed ? 0.0 : -0.045, y, z));
    buttonholes.push(garmentButtonhole(parent, `dress shirt ${closed ? "closed" : "open"} buttonhole ${i + 1}`, closed ? 0.035 : 0.055, y, z - 0.002));
  }
  return { buttons, buttonholes };
}

function addDressShirtCollar(parent, z, y = 1.39, spread = 0.085) {
  garmentMesh(parent, "dress shirt left collar leaf", -spread, y, z, 0.17, 0.04, 0.03, materials.shirtCotton, { z: -0.34 });
  garmentMesh(parent, "dress shirt right collar leaf", spread, y, z, 0.17, 0.04, 0.03, materials.shirtCotton, { z: 0.34 });
  garmentMesh(parent, "dress shirt rear collar band", 0, y + 0.018, z + 0.035, 0.28, 0.045, 0.028, materials.shirtSeam);
}

function createDressShirtVariant(name, mode) {
  const group = new THREE.Group();
  group.name = name;
  group.visible = false;
  group.userData.garmentVariantMode = mode;
  const anchors = {
    leftSleeveEntry: new THREE.Vector3(-0.36, 1.14, 0.42),
    rightSleeveEntry: new THREE.Vector3(0.36, 1.14, 0.42),
    collarOpening: new THREE.Vector3(0, 1.39, 0.42),
    frontPlacketLeft: new THREE.Vector3(-0.045, 1.18, 0.44),
    frontPlacketRight: new THREE.Vector3(0.055, 1.18, 0.44),
    handHoldPoint: new THREE.Vector3(0.24, 0.88, 0.28),
    chestTorsoFitTarget: new THREE.Vector3(0, 1.16, 0.13),
    hangerHook: new THREE.Vector3(0, 0.08, 0),
    buttonPoints: [
      new THREE.Vector3(-0.045, 1.31, 0.44),
      new THREE.Vector3(-0.045, 1.205, 0.44),
      new THREE.Vector3(-0.045, 1.1, 0.44),
      new THREE.Vector3(-0.045, 0.995, 0.44),
      new THREE.Vector3(-0.045, 0.89, 0.44),
    ],
    buttonholePoints: [
      new THREE.Vector3(0.055, 1.31, 0.44),
      new THREE.Vector3(0.055, 1.205, 0.44),
      new THREE.Vector3(0.055, 1.1, 0.44),
      new THREE.Vector3(0.055, 0.995, 0.44),
      new THREE.Vector3(0.055, 0.89, 0.44),
    ],
  };

  if (mode === "hanging") {
    anchors.leftSleeveEntry.set(-0.32, -0.22, -0.03);
    anchors.rightSleeveEntry.set(0.32, -0.22, -0.03);
    anchors.collarOpening.set(0, -0.06, -0.035);
    anchors.hangerHook.set(0, 0.08, 0);
    anchors.handHoldPoint.set(0.02, -0.27, -0.05);
    garmentMesh(group, "Shirt_Hanging back panel", 0, -0.34, 0.018, 0.5, 0.62, 0.026, materials.shirtInside);
    garmentMesh(group, "Shirt_Hanging left front panel", -0.13, -0.34, -0.018, 0.24, 0.61, 0.026, materials.shirtCotton);
    garmentMesh(group, "Shirt_Hanging right front panel", 0.13, -0.34, -0.018, 0.24, 0.61, 0.026, materials.shirtCotton);
    garmentMesh(group, "Shirt_Hanging left sleeve opening", -0.36, -0.26, -0.012, 0.17, 0.48, 0.03, materials.shirtCotton, { z: -0.45 });
    garmentMesh(group, "Shirt_Hanging right sleeve opening", 0.36, -0.26, -0.012, 0.17, 0.48, 0.03, materials.shirtCotton, { z: 0.45 });
    garmentMesh(group, "Shirt_Hanging front opening left placket", -0.012, -0.33, -0.045, 0.018, 0.56, 0.02, materials.shirtSeam);
    garmentMesh(group, "Shirt_Hanging front opening right placket", 0.012, -0.33, -0.045, 0.018, 0.56, 0.02, materials.shirtSeam);
    garmentMesh(group, "Shirt_Hanging collar band", 0, -0.04, -0.02, 0.28, 0.045, 0.032, materials.shirtCotton);
    garmentMesh(group, "Shirt_Hanging hanger left arm", -0.13, 0.0, 0.005, 0.31, 0.018, 0.018, materials.hangerWire, { z: -0.34 });
    garmentMesh(group, "Shirt_Hanging hanger right arm", 0.13, 0.0, 0.005, 0.31, 0.018, 0.018, materials.hangerWire, { z: 0.34 });
    garmentMesh(group, "Shirt_Hanging hanger hook", 0, 0.08, 0.005, 0.035, 0.11, 0.018, materials.hangerWire);
  } else if (mode === "held") {
    anchors.leftSleeveEntry.set(0.02, 0.9, 0.32);
    anchors.rightSleeveEntry.set(0.22, 0.9, 0.32);
    anchors.collarOpening.set(0.12, 0.98, 0.31);
    anchors.handHoldPoint.set(0.23, 0.89, 0.28);
    garmentMesh(group, "Shirt_Held folded body", 0.24, 0.88, 0.29, 0.42, 0.16, 0.12, materials.shirtCotton, { z: 0.08 });
    garmentMesh(group, "Shirt_Held visible collar", 0.16, 0.97, 0.32, 0.18, 0.045, 0.04, materials.shirtSeam, { z: -0.18 });
    garmentMesh(group, "Shirt_Held folded left sleeve", 0.02, 0.83, 0.29, 0.22, 0.07, 0.08, materials.shirtInside, { z: -0.28 });
    garmentMesh(group, "Shirt_Held folded right sleeve", 0.38, 0.84, 0.29, 0.22, 0.07, 0.08, materials.shirtInside, { z: 0.28 });
  } else {
    const z = mode === "dressingOpen" ? 0.42 : 0.13;
    const backZ = mode === "dressingOpen" ? 0.31 : -0.085;
    const sideZ = mode === "dressingOpen" ? 0.36 : 0.02;
    const open = mode !== "wornClosed";
    const sleeveZ = mode === "dressingOpen" ? 0.4 : 0.035;
    const sleeveY = mode === "dressingOpen" ? 1.15 : 1.1;
    const leftX = open ? -0.13 : -0.07;
    const rightX = open ? 0.13 : 0.07;
    const panelWidth = open ? 0.22 : 0.31;
    const gapTilt = mode === "dressingOpen" ? 0.16 : open ? 0.08 : 0;
    garmentMesh(group, `${name} left front panel`, leftX, 1.11, z, panelWidth, 0.62, 0.032, materials.shirtCotton, { y: -gapTilt });
    garmentMesh(group, `${name} right front panel`, rightX, 1.11, z, panelWidth, 0.62, 0.032, materials.shirtCotton, { y: gapTilt });
    garmentMesh(group, `${name} back cloth panel`, 0, 1.11, backZ, 0.5, 0.64, 0.026, materials.shirtInside);
    garmentMesh(group, `${name} left torso side wrap`, -0.265, 1.11, sideZ, 0.03, 0.6, 0.25, materials.shirtCotton);
    garmentMesh(group, `${name} right torso side wrap`, 0.265, 1.11, sideZ, 0.03, 0.6, 0.25, materials.shirtCotton);
    garmentMesh(group, `${name} left shoulder wrap`, -0.17, 1.39, 0.01, 0.23, 0.042, 0.24, materials.shirtCotton, { z: -0.12 });
    garmentMesh(group, `${name} right shoulder wrap`, 0.17, 1.39, 0.01, 0.23, 0.042, 0.24, materials.shirtCotton, { z: 0.12 });
    garmentMesh(group, `${name} left sleeve tube`, -0.37, sleeveY, sleeveZ, 0.18, 0.45, 0.075, materials.shirtCotton, { z: -0.16 });
    garmentMesh(group, `${name} right sleeve tube`, 0.37, sleeveY, sleeveZ, 0.18, 0.45, 0.075, materials.shirtCotton, { z: 0.16 });
    garmentMesh(group, `${name} left cuff opening`, -0.43, 0.88, sleeveZ, 0.16, 0.04, 0.085, materials.shirtSeam);
    garmentMesh(group, `${name} right cuff opening`, 0.43, 0.88, sleeveZ, 0.16, 0.04, 0.085, materials.shirtSeam);
    garmentMesh(group, `${name} left front placket`, open ? -0.025 : 0.0, 1.105, z + 0.025, 0.018, 0.58, 0.025, materials.shirtSeam);
    garmentMesh(group, `${name} right front placket`, open ? 0.025 : 0.0, 1.105, z + 0.03, 0.018, 0.58, 0.025, materials.shirtSeam);
    addDressShirtCollar(group, z + 0.02, 1.42, open ? 0.09 : 0.07);
    addDressShirtButtonSet(group, z + 0.052, !open);
  }

  group.userData.anchors = anchors;
  scene.add(group);
  return group;
}

class GarmentComponent {
  constructor({ id, label, variants }) {
    this.id = id;
    this.label = label;
    this.variants = variants;
    this.state = GARMENT_STATES.OnHanger;
    this.lifecycle = "HUNG_IN_CLOSET";
    this.buttoned = false;
    this.selected = false;
    this.dropPosition = null;
    this.history = [];
    for (const group of Object.values(this.variants || {})) {
      group.userData.garmentComponent = {
        id: this.id,
        label: this.label,
      };
    }
    this.setState(GARMENT_STATES.OnHanger, { lifecycle: "HUNG_IN_CLOSET" });
  }

  visibleVariantKey() {
    if (this.state === GARMENT_STATES.OnHanger || this.state === GARMENT_STATES.InCloset) return "hanging";
    if (this.state === GARMENT_STATES.Held || this.state === GARMENT_STATES.Dropped || this.state === GARMENT_STATES.Laundry) return "held";
    if (this.state === GARMENT_STATES.Dressing || this.state === GARMENT_STATES.PartiallyWorn || this.state === GARMENT_STATES.Removing) return "dressingOpen";
    if (this.state === GARMENT_STATES.WornOpen || this.state === GARMENT_STATES.Fastening) return "wornOpen";
    if (this.state === GARMENT_STATES.WornClosed) return "wornClosed";
    return "hanging";
  }

  setState(state, detail = {}) {
    this.state = state;
    this.lifecycle = detail.lifecycle || this.lifecycle || state;
    if (typeof detail.buttoned === "boolean") this.buttoned = detail.buttoned;
    if (detail.dropPosition) this.dropPosition = detail.dropPosition.clone ? detail.dropPosition.clone() : detail.dropPosition;
    const visibleKey = this.visibleVariantKey();
    for (const [key, group] of Object.entries(this.variants || {})) {
      group.visible = key === visibleKey;
      group.userData.garmentState = this.state;
      group.userData.garmentLifecycle = this.lifecycle;
      group.userData.buttoned = this.buttoned;
    }
    this.history.push({
      at: Number(clock.elapsedTime.toFixed(3)),
      state: this.state,
      lifecycle: this.lifecycle,
      buttoned: this.buttoned,
    });
    if (this.history.length > 48) this.history.shift();
    homeWorldActivityStatus = {
      ...homeWorldActivityStatus,
      dressShirtPrototype: this.toJSON(),
    };
  }

  toJSON() {
    const snapshot = {
      id: this.id,
      label: this.label,
      state: this.state,
      lifecycle: this.lifecycle,
      buttoned: this.buttoned,
      selected: this.selected,
      visibleVariant: this.visibleVariantKey(),
      history: this.history.slice(-8),
    };
    if (this.dropPosition) {
      snapshot.dropPosition = {
        x: Number(this.dropPosition.x.toFixed(3)),
        y: Number(this.dropPosition.y.toFixed(3)),
        z: Number(this.dropPosition.z.toFixed(3)),
      };
    }
    return snapshot;
  }
}

class ClosetComponent {
  constructor({ id, label, root, hanger }) {
    this.id = id;
    this.label = label;
    this.root = root;
    this.hanger = hanger;
    this.garments = [];
  }

  store(garment) {
    if (!this.garments.includes(garment)) this.garments.push(garment);
    garment.selected = false;
    garment.setState(GARMENT_STATES.OnHanger, { lifecycle: "HUNG_IN_CLOSET", buttoned: false });
    syncPrototypeDressShirtPlacement(clock.elapsedTime);
    return garment;
  }

  selectGarment(id) {
    const garment = this.garments.find((item) => item.id === id) || this.garments[0] || null;
    if (garment) garment.selected = true;
    return garment;
  }

  detachGarment(garment) {
    if (!garment) return null;
    garment.selected = true;
    garment.setState(GARMENT_STATES.Held, { lifecycle: "TAKEN_FROM_CLOSET", buttoned: false });
    return garment;
  }

  startDressing(garment = this.selectGarment("dress_shirt_001")) {
    if (!avatarDressingController || !garment) return false;
    this.detachGarment(garment);
    return avatarDressingController.startPutOn(garment);
  }

  toJSON() {
    return {
      id: this.id,
      label: this.label,
      garmentCount: this.garments.length,
      garments: this.garments.map((item) => item.toJSON()),
    };
  }
}

class AvatarDressingController {
  constructor() {
    this.mode = null;
    this.garment = null;
    this.startedAt = 0;
    this.destination = "closet";
    this.phase = null;
  }

  startPutOn(garment) {
    if (!activeMarker || !garment) return false;
    this.mode = "put_on";
    this.garment = garment;
    this.startedAt = clock.elapsedTime;
    this.destination = "body";
    this.phase = { lifecycle: "TAKEN_FROM_CLOSET", state: GARMENT_STATES.Held, progress: 0 };
    activeSkillInteraction = {
      id: "dress_shirt_put_on",
      kind: "dress_shirt",
      action: "putting_on_shirt",
      label: "prototype dress shirt dressing sequence",
      startedAt: this.startedAt,
      seconds: 6.6,
      phase: this.phase.lifecycle,
    };
    activeMarker.userData.skillInteraction = activeSkillInteraction.id;
    activeMarker.userData.practiceRoute = null;
    activeMarker.userData.postureState = null;
    activeMarker.userData.isMoving = false;
    activeMarker.userData.garmentState = garment.toJSON();
    setActiveAvatarAction("putting_on_shirt");
    return true;
  }

  startRemove(destination = "closet") {
    if (!activeMarker || !this.garment) return false;
    this.mode = "remove";
    this.startedAt = clock.elapsedTime;
    this.destination = destination;
    this.phase = { lifecycle: "UNBUTTONING", state: GARMENT_STATES.Fastening, progress: 0 };
    activeSkillInteraction = {
      id: "dress_shirt_remove",
      kind: "dress_shirt",
      action: "removing_shirt",
      label: "prototype dress shirt removal sequence",
      startedAt: this.startedAt,
      seconds: 4.6,
      phase: this.phase.lifecycle,
    };
    activeMarker.userData.skillInteraction = activeSkillInteraction.id;
    activeMarker.userData.practiceRoute = null;
    activeMarker.userData.postureState = null;
    activeMarker.userData.isMoving = false;
    setActiveAvatarAction("removing_shirt");
    return true;
  }

  dropHeldGarment() {
    if (!activeMarker || !this.garment) return false;
    this.mode = null;
    const dropPosition = activeAvatarWorldOffset(0.38, 0.02, 0.62);
    this.garment.setState(GARMENT_STATES.Dropped, { lifecycle: "DROPPED", buttoned: false, dropPosition });
    clearDressShirtSkillInteraction();
    syncPrototypeDressShirtPlacement(clock.elapsedTime);
    return true;
  }

  sendToLaundry() {
    if (!this.garment) return false;
    this.mode = null;
    this.garment.setState(GARMENT_STATES.Laundry, { lifecycle: "LAUNDRY", buttoned: false });
    clearDressShirtSkillInteraction();
    syncPrototypeDressShirtPlacement(clock.elapsedTime);
    return true;
  }

  phaseForAge(age) {
    if (this.mode === "put_on") {
      if (age < 0.75) return { lifecycle: "TAKEN_FROM_CLOSET", state: GARMENT_STATES.Held, progress: age / 0.75, buttoned: false };
      if (age < 1.45) return { lifecycle: "HELD", state: GARMENT_STATES.Held, progress: (age - 0.75) / 0.7, buttoned: false };
      if (age < 2.3) return { lifecycle: "PUTTING_ON", state: GARMENT_STATES.Dressing, progress: (age - 1.45) / 0.85, buttoned: false };
      if (age < 3.25) return { lifecycle: "LEFT_ARM_IN", state: GARMENT_STATES.PartiallyWorn, progress: (age - 2.3) / 0.95, buttoned: false };
      if (age < 4.2) return { lifecycle: "RIGHT_ARM_IN", state: GARMENT_STATES.PartiallyWorn, progress: (age - 3.25) / 0.95, buttoned: false };
      if (age < 5.05) return { lifecycle: "ON_BODY_OPEN", state: GARMENT_STATES.WornOpen, progress: (age - 4.2) / 0.85, buttoned: false };
      if (age < 6.45) return { lifecycle: "BUTTONING", state: GARMENT_STATES.Fastening, progress: (age - 5.05) / 1.4, buttoned: false };
      return { lifecycle: "WORN_CLOSED", state: GARMENT_STATES.WornClosed, progress: 1, buttoned: true, done: true };
    }
    if (this.mode === "remove") {
      if (age < 1.0) return { lifecycle: "UNBUTTONING", state: GARMENT_STATES.Fastening, progress: age / 1.0, buttoned: false };
      if (age < 1.8) return { lifecycle: "WORN_OPEN", state: GARMENT_STATES.WornOpen, progress: (age - 1.0) / 0.8, buttoned: false };
      if (age < 3.15) return { lifecycle: "REMOVING_ARMS", state: GARMENT_STATES.Removing, progress: (age - 1.8) / 1.35, buttoned: false };
      if (age < 4.0) return { lifecycle: "HELD", state: GARMENT_STATES.Held, progress: (age - 3.15) / 0.85, buttoned: false };
      return { lifecycle: this.destination === "laundry" ? "LAUNDRY" : this.destination === "dropped" ? "DROPPED" : "HUNG_IN_CLOSET", state: GARMENT_STATES.Held, progress: 1, buttoned: false, done: true };
    }
    return null;
  }

  update(t) {
    if (!this.mode || !this.garment) return;
    const age = Math.max(0, t - this.startedAt);
    this.phase = this.phaseForAge(age);
    if (!this.phase) return;
    this.garment.setState(this.phase.state, { lifecycle: this.phase.lifecycle, buttoned: this.phase.buttoned });
    if (activeSkillInteraction?.kind === "dress_shirt") activeSkillInteraction.phase = this.phase.lifecycle;
    if (activeMarker) activeMarker.userData.garmentState = this.garment.toJSON();
    if (!this.phase.done) return;
    if (this.mode === "put_on") {
      this.garment.setState(GARMENT_STATES.WornClosed, { lifecycle: "WORN_CLOSED", buttoned: true });
    } else if (this.destination === "laundry") {
      this.garment.setState(GARMENT_STATES.Laundry, { lifecycle: "LAUNDRY", buttoned: false });
    } else if (this.destination === "dropped") {
      const dropPosition = activeAvatarWorldOffset(0.38, 0.02, 0.62);
      this.garment.setState(GARMENT_STATES.Dropped, { lifecycle: "DROPPED", buttoned: false, dropPosition });
    } else if (prototypeCloset) {
      prototypeCloset.store(this.garment);
    } else {
      this.garment.setState(GARMENT_STATES.OnHanger, { lifecycle: "HUNG_IN_CLOSET", buttoned: false });
    }
    this.mode = null;
    this.phase = null;
    clearDressShirtSkillInteraction();
  }

  buttonShirt() {
    if (!this.garment) return false;
    this.garment.setState(GARMENT_STATES.WornClosed, { lifecycle: "WORN_CLOSED", buttoned: true });
    syncPrototypeDressShirtPlacement(clock.elapsedTime);
    return true;
  }

  unbuttonShirt() {
    if (!this.garment) return false;
    this.garment.setState(GARMENT_STATES.WornOpen, { lifecycle: "WORN_OPEN", buttoned: false });
    syncPrototypeDressShirtPlacement(clock.elapsedTime);
    return true;
  }

  toJSON() {
    return {
      active: !!this.mode,
      mode: this.mode,
      phase: this.phase,
      destination: this.destination,
      garment: this.garment ? this.garment.toJSON() : null,
    };
  }
}

function clearDressShirtSkillInteraction() {
  if (activeSkillInteraction?.kind === "dress_shirt") activeSkillInteraction = null;
  if (activeMarker?.userData?.skillInteraction === "dress_shirt_put_on" || activeMarker?.userData?.skillInteraction === "dress_shirt_remove") {
    activeMarker.userData.skillInteraction = null;
  }
  if (activeAvatarAction === "putting_on_shirt" || activeAvatarAction === "removing_shirt") setActiveAvatarAction("idle");
}

function addClosetBox(parent, name, x, y, z, sx, sy, sz, material) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), material);
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function addPrototypeGarmentCloset({ includeClosetShell = true } = {}) {
  if (prototypeCloset || prototypeDressShirt) return;
  const root = new THREE.Group();
  root.name = "Prototype clothing closet with one real dress shirt";
  root.position.copy(DRESS_SHIRT_CLOSET_POSITION);
  root.rotation.y = DRESS_SHIRT_CLOSET_YAW;
  scene.add(root);

  let rail = null;
  if (includeClosetShell) {
    addClosetBox(root, "prototype closet back panel", 0, 1.05, 0.22, 1.15, 2.05, 0.08, materials.closetWood);
    addClosetBox(root, "prototype closet left side panel", -0.6, 1.05, 0, 0.08, 2.05, 0.52, materials.closetWood);
    addClosetBox(root, "prototype closet right side panel", 0.6, 1.05, 0, 0.08, 2.05, 0.52, materials.closetWood);
    addClosetBox(root, "prototype closet top panel", 0, 2.09, 0, 1.25, 0.08, 0.56, materials.closetWood);
    addClosetBox(root, "prototype closet floor shelf", 0, 0.08, 0, 1.25, 0.08, 0.56, materials.closetWood);
    addClosetBox(root, "prototype closet warm interior backing", 0, 1.05, 0.174, 1.02, 1.82, 0.035, materials.closetInterior);
    rail = addClosetBox(root, "prototype closet hanger rail", 0, 1.68, -0.015, 0.94, 0.045, 0.045, materials.closetRail);
    const hanger = addClosetBox(root, "prototype closet empty hanger reference", 0, 1.57, -0.045, 0.46, 0.025, 0.025, materials.hangerWire);
    hanger.rotation.z = 0.18;
    const hamper = addClosetBox(root, "prototype closet laundry basket target", 0.34, 0.28, -0.12, 0.28, 0.28, 0.28, materials.laundryBasket);
    markTruthProp(root, "closet", "prototype clothing closet", 0, ["select_garment", "take_from_closet", "hang_garment"]);
    markTruthProp(hamper, "laundry", "prototype laundry basket for removed shirt", 0, ["laundry"]);
  }

  const variants = {
    hanging: createDressShirtVariant("Shirt_Hanging", "hanging"),
    held: createDressShirtVariant("Shirt_Held", "held"),
    dressingOpen: createDressShirtVariant("Shirt_Dressing_Open", "dressingOpen"),
    wornOpen: createDressShirtVariant("Shirt_Worn_Open", "wornOpen"),
    wornClosed: createDressShirtVariant("Shirt_Worn_Closed", "wornClosed"),
  };
  prototypeDressShirt = new GarmentComponent({
    id: "dress_shirt_001",
    label: "prototype dress shirt",
    variants,
  });
  prototypeCloset = new ClosetComponent({
    id: "kira_one_bedroom_prototype_closet",
    label: "Kira one-bedroom prototype closet",
    root,
    hanger: rail,
  });
  prototypeCloset.store(prototypeDressShirt);
  avatarDressingController = new AvatarDressingController();
  markTruthProp(variants.hanging, "garment", "prototype dress shirt on hanger", 0, ["take_from_closet", "put_on_shirt"]);
  markTruthProp(variants.held, "garment", "prototype dress shirt held in hands", 0, ["hold_garment", "put_on_shirt", "drop_garment"]);
  markTruthProp(variants.wornOpen, "garment", "prototype dress shirt worn open", 0, ["button_shirt", "remove_shirt"]);
  markTruthProp(variants.wornClosed, "garment", "prototype dress shirt worn closed", 0, ["unbutton_shirt", "remove_shirt"]);
  syncPrototypeDressShirtPlacement(clock.elapsedTime);
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    dressShirtPrototype: prototypeDressShirt.toJSON(),
    closetPrototype: prototypeCloset.toJSON(),
  };
}

function syncPrototypeDressShirtPlacement(t) {
  if (!prototypeDressShirt) return;
  const garment = prototypeDressShirt;
  const variants = garment.variants || {};
  if (variants.hanging) {
    variants.hanging.position.set(DRESS_SHIRT_CLOSET_POSITION.x, 1.66 + Math.sin(t * 1.2) * 0.002, DRESS_SHIRT_CLOSET_POSITION.z);
    variants.hanging.rotation.set(0, DRESS_SHIRT_CLOSET_YAW, 0);
  }
  const activeQuat = activeMarker ? activeMarker.getWorldQuaternion(new THREE.Quaternion()) : new THREE.Quaternion();
  const activePos = activeMarker?.position || KIRA_BUNGALOW_SPAWN;
  for (const key of ["held", "dressingOpen", "wornOpen", "wornClosed"]) {
    if (!variants[key]) continue;
    variants[key].position.copy(activePos);
    variants[key].quaternion.copy(activeQuat);
  }
  if (garment.state === GARMENT_STATES.Dropped && variants.held) {
    const drop = garment.dropPosition || activeAvatarWorldOffset(0.38, 0.02, 0.62);
    variants.held.position.set(drop.x, drop.y - 0.82, drop.z);
    variants.held.rotation.set(-Math.PI / 2, activeMarker?.rotation?.y || 0, 0);
  }
  if (garment.state === GARMENT_STATES.Laundry && variants.held) {
    variants.held.position.set(DRESS_SHIRT_CLOSET_POSITION.x + 0.22, -0.58, DRESS_SHIRT_CLOSET_POSITION.z - 0.14);
    variants.held.rotation.set(-Math.PI / 2, DRESS_SHIRT_CLOSET_YAW, 0);
  }
}

function updateAvatarDressingController(t) {
  if (!prototypeDressShirt) return;
  avatarDressingController?.update(t);
  syncPrototypeDressShirtPlacement(t);
}

function activeAvatarWardrobeSnapshot() {
  const garments = prototypeCloset?.garments || (prototypeDressShirt ? [prototypeDressShirt] : []);
  const records = garments.map((garment) => {
    const state = garment.toJSON();
    return {
      id: state.id,
      label: state.label,
      state: state.state,
      lifecycle: state.lifecycle,
      buttoned: !!state.buttoned,
      selected: !!state.selected,
      ...(state.dropPosition ? { dropPosition: state.dropPosition } : {}),
    };
  });
  return {
    schemaVersion: 1,
    garments: records,
    equippedGarmentIds: records
      .filter((item) => [
        GARMENT_STATES.Dressing,
        GARMENT_STATES.PartiallyWorn,
        GARMENT_STATES.WornOpen,
        GARMENT_STATES.Fastening,
        GARMENT_STATES.WornClosed,
        GARMENT_STATES.Removing,
      ].includes(item.state))
      .map((item) => item.id),
    resumePolicy: "restore_same_visible_garment_state_without_replaying_dressing_animation",
  };
}

function applyActiveAvatarWardrobeResumeState(wardrobeState) {
  if (!prototypeDressShirt || !prototypeCloset || !avatarDressingController) return false;
  const allowedStates = new Set(Object.values(GARMENT_STATES));
  const savedGarments = Array.isArray(wardrobeState?.garments) ? wardrobeState.garments : [];
  const saved = savedGarments.find((item) => item?.id === prototypeDressShirt.id) || null;
  avatarDressingController.mode = null;
  avatarDressingController.phase = null;
  avatarDressingController.destination = "closet";
  clearDressShirtSkillInteraction();
  if (!saved || !allowedStates.has(saved.state)) {
    prototypeCloset.store(prototypeDressShirt);
    if (activeMarker) activeMarker.userData.garmentState = prototypeDressShirt.toJSON();
    return false;
  }
  let dropPosition = null;
  if (saved.dropPosition) {
    const x = Number(saved.dropPosition.x);
    const y = Number(saved.dropPosition.y);
    const z = Number(saved.dropPosition.z);
    if (Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)) {
      dropPosition = new THREE.Vector3(x, y, z);
    }
  }
  prototypeDressShirt.selected = !!saved.selected;
  prototypeDressShirt.dropPosition = dropPosition;
  prototypeDressShirt.setState(saved.state, {
    lifecycle: String(saved.lifecycle || saved.state),
    buttoned: !!saved.buttoned,
    ...(dropPosition ? { dropPosition } : {}),
  });
  if ([
    GARMENT_STATES.Dressing,
    GARMENT_STATES.PartiallyWorn,
    GARMENT_STATES.WornOpen,
    GARMENT_STATES.Fastening,
    GARMENT_STATES.WornClosed,
    GARMENT_STATES.Removing,
  ].includes(saved.state)) {
    avatarDressingController.garment = prototypeDressShirt;
  } else {
    avatarDressingController.garment = null;
  }
  if (activeMarker) activeMarker.userData.garmentState = prototypeDressShirt.toJSON();
  syncPrototypeDressShirtPlacement(clock.elapsedTime);
  return true;
}

function dressShirtHandTargetsForPhase(phase) {
  const lifecycle = String(phase?.lifecycle || "").toUpperCase();
  const wobble = Math.sin(clock.elapsedTime * 4.2) * 0.018;
  if (lifecycle === "TAKEN_FROM_CLOSET" || lifecycle === "HELD") {
    return {
      left: activeAvatarWorldOffset(-0.05, 0.9, 0.24),
      right: activeAvatarWorldOffset(0.28, 0.9 + wobble, 0.28),
      curlLeft: 0.45,
      curlRight: 0.72,
    };
  }
  if (lifecycle === "PUTTING_ON") {
    return {
      left: activeAvatarWorldOffset(-0.34, 1.14, 0.42),
      right: activeAvatarWorldOffset(0.34, 1.14, 0.42),
      curlLeft: 0.58,
      curlRight: 0.58,
    };
  }
  if (lifecycle === "LEFT_ARM_IN") {
    return {
      left: activeAvatarWorldOffset(-0.44 + phase.progress * 0.22, 1.1, 0.4),
      right: activeAvatarWorldOffset(0.22, 1.16, 0.43),
      curlLeft: 0.34,
      curlRight: 0.62,
    };
  }
  if (lifecycle === "RIGHT_ARM_IN") {
    return {
      left: activeAvatarWorldOffset(-0.18, 1.12, 0.34),
      right: activeAvatarWorldOffset(0.44 - phase.progress * 0.22, 1.1, 0.4),
      curlLeft: 0.52,
      curlRight: 0.34,
    };
  }
  if (lifecycle === "BUTTONING" || lifecycle === "UNBUTTONING") {
    const y = 1.25 - THREE.MathUtils.clamp(phase.progress || 0, 0, 1) * 0.3;
    return {
      left: activeAvatarWorldOffset(-0.05, y, 0.28),
      right: activeAvatarWorldOffset(0.07, y + 0.015, 0.3),
      curlLeft: 0.64,
      curlRight: 0.76,
    };
  }
  if (lifecycle === "REMOVING_ARMS") {
    return {
      left: activeAvatarWorldOffset(-0.42 + phase.progress * 0.18, 1.1, 0.4),
      right: activeAvatarWorldOffset(0.42 - phase.progress * 0.18, 1.1, 0.4),
      curlLeft: 0.52,
      curlRight: 0.52,
    };
  }
  return {
    left: activeAvatarWorldOffset(-0.14, 0.84, 0.08),
    right: activeAvatarWorldOffset(0.14, 0.84, 0.08),
    curlLeft: 0.26,
    curlRight: 0.26,
  };
}

function applyAvatarDressingPose(rig, t) {
  const phase = avatarDressingController?.phase;
  if (!phase || !activeMarker || activeSkillInteraction?.kind !== "dress_shirt") return false;
  if (rig.bones.spine) rig.bones.spine.rotation.x += 0.07 + Math.sin(t * 2.2) * 0.015;
  if (rig.bones.neck) rig.bones.neck.rotation.x -= 0.035;
  if (rig.bones.head) rig.bones.head.rotation.x -= 0.03;
  const targets = dressShirtHandTargetsForPhase(phase);
  const armSpecs = [
    {
      side: "L",
      upper: rig.bones.leftUpperArm,
      lower: rig.bones.leftForearm,
      hand: rig.bones.leftHand,
      target: targets.left,
      curl: targets.curlLeft,
      sideSign: 1,
    },
    {
      side: "R",
      upper: rig.bones.rightUpperArm,
      lower: rig.bones.rightForearm,
      hand: rig.bones.rightHand,
      target: targets.right,
      curl: targets.curlRight,
      sideSign: -1,
    },
  ];
  for (const item of armSpecs) {
    if (item.upper) {
      item.upper.rotation.z += item.sideSign * 0.34;
      item.upper.rotation.x -= 0.08;
    }
    if (item.lower) item.lower.rotation.x += 0.18;
    solveActiveAvatarProceduralLimb(item.upper, item.lower, item.hand, item.target, 0.42);
    curlActiveAvatarProceduralFingers(rig, item.side, item.curl);
  }
  if (activeMarker) {
    activeMarker.userData.proceduralRig = rig.id;
    activeMarker.userData.proceduralRigDriving = true;
    activeMarker.userData.proceduralGaitMode = `dress_shirt_${phase.lifecycle}`;
  }
  return true;
}

function truthPropSnapshot(obj, avatarPosition = null) {
  const truth = obj?.userData?.truthProp;
  if (!truth) return null;
  if (obj.visible === false || (!obj.parent && obj !== scene)) return null;
  const pos = new THREE.Vector3();
  obj.getWorldPosition(pos);
  const distanceMeters = avatarPosition ? pos.distanceTo(avatarPosition) : null;
  return {
    kind: truth.kind,
    label: truth.label,
    floor: truth.floor,
    actionHints: truth.actionHints || [],
    x: Number(pos.x.toFixed(3)),
    y: Number(pos.y.toFixed(3)),
    z: Number(pos.z.toFixed(3)),
    distanceMeters: distanceMeters === null ? null : Number(distanceMeters.toFixed(3)),
  };
}

const ACTIVITY_TRUTH_RULES = [
  {
    id: "project_work",
    tests: [/project/, /creative[_ ]?writ/, /take[_ ]?notes?/, /write[_ ]?tablet/, /work(?:ing)?[_ ]?on/],
    kinds: ["computer", "keyboard", "mouse", "phone", "tablet", "notebook", "sketchbook"],
    requirement: "an actively reached and used tablet, phone, notebook, sketchbook, or computer",
  },
  {
    id: "read_book",
    tests: [/read/, /book/, /magazine/, /study/],
    kinds: ["book", "notebook", "sketchbook", "computer", "phone", "tablet"],
    requirement: "a visible book, notebook, sketchbook, computer, phone, or tablet near the body",
  },
  {
    id: "sketch_design",
    tests: [/sketch/, /draw/, /design/, /fashion/],
    kinds: ["sketchbook", "notebook", "pencil", "design_wall", "computer"],
    requirement: "a visible sketchbook, pencil, design wall, or computer near the body",
  },
  {
    id: "use_computer",
    tests: [/computer/, /keyboard/, /type/, /program/, /research/, /email/],
    kinds: ["computer", "keyboard", "mouse", "phone", "tablet", "notebook"],
    requirement: "a visible computer, phone, tablet, or notebook near the body",
  },
  {
    id: "use_phone",
    tests: [/phone/, /tablet/, /ebook/, /e-book/, /online/, /web/, /browse/, /photo/, /picture/, /camera/, /notes?/],
    kinds: ["phone", "tablet", "computer", "notebook"],
    requirement: "a visible phone, tablet, computer, or notebook near the body",
  },
  {
    id: "drink",
    tests: [/drink/, /water/, /milk/, /bottle/],
    kinds: ["coffee_cup", "cup", "milk"],
    requirement: "a visible cup, bottle, or milk carton nearby or in the hand",
  },
  {
    id: "drink_coffee",
    tests: [/coffee/, /tea/, /cafe/, /starbucks/],
    kinds: ["coffee_cup", "cup"],
    requirement: "a visible cup nearby or in the hand",
  },
  {
    id: "play_basketball",
    tests: [/basketball/, /dribble/, /court/, /shoot hoops/],
    kinds: ["basketball", "court"],
    requirement: "a visible basketball or court near the body",
  },
  {
    id: "attend_school",
    tests: [/school/, /class/, /lesson/, /study/, /subject/, /teacher/],
    kinds: ["classroom", "desk", "chair", "notebook", "phone", "book"],
    requirement: "a visible classroom, desk, chair, notebook, phone, or book near the body",
  },
  {
    id: "eat_food",
    tests: [/eat/, /food/, /snack/, /meal/, /fruit/, /breakfast/, /lunch/, /dinner/],
    kinds: ["food", "fruit", "milk", "dining_table", "counter", "fridge", "refrigerator"],
    requirement: "visible food, fruit, milk, a dining table, counter, or refrigerator near the body",
  },
];

function activityTruthForAction(action = activeAvatarAction) {
  const normalized = String(action || "idle").toLowerCase();
  const rule = ACTIVITY_TRUTH_RULES.find((item) => item.id === normalized || item.tests.some((test) => test.test(normalized)));
  if (!rule) {
    return {
      action: normalized,
      grounded: true,
      requirement: "no prop gate for this action",
      reason: "This action does not claim a specific held or nearby object.",
      evidence: [],
    };
  }
  if (!activeMarker) {
    return {
      action: normalized,
      grounded: false,
      requirement: rule.requirement,
      reason: "No active body is present to compare against physical props.",
      evidence: [],
    };
  }

  const avatarPos = activeMarker.position.clone();
  const avatarFloor = avatarPos.y > 2 ? 1 : 0;
  const evidence = activityTruthProps
    .map((obj) => truthPropSnapshot(obj, avatarPos))
    .filter(Boolean)
    .filter((prop) => rule.kinds.includes(prop.kind))
    .filter((prop) => prop.floor === null || prop.floor === avatarFloor)
    .sort((a, b) => (a.distanceMeters ?? 999) - (b.distanceMeters ?? 999));
  const nearby = evidence.filter((prop) => {
    if (prop.kind === "design_wall") return (prop.distanceMeters ?? 999) <= 4.6;
    return (prop.distanceMeters ?? 999) <= 2.25;
  });
  if (rule.id === "attend_school" && pointInsideHudRegion(avatarPos, SCHOOL_CENTER.x, SCHOOL_CENTER.z, SCHOOL_WIDTH, SCHOOL_DEPTH, 2.2)) {
    nearby.unshift({
      kind: "classroom",
      label: HOME_WORLD_PRE_RAM_LIGHT_MODE ? "empty school learning room" : "school classroom",
      floor: avatarFloor,
      distanceMeters: 0,
      actionHints: ["attend_school", "lesson", "study"],
    });
  }
  if (rule.id === "project_work") {
    const interactionAction = `${activeSkillInteraction?.action || ""} ${activeSkillInteraction?.truthAction || ""}`.toLowerCase();
    const interactionUsesProjectTool = activeSkillInteraction?.kind === "hold"
      && rule.tests.some((test) => test.test(interactionAction));
    const heldToolIsVisible = !!activeHeldProp?.visible && rule.kinds.includes(activeHeldPropKind);
    const inUse = interactionUsesProjectTool && heldToolIsVisible;
    return {
      action: normalized,
      rule: rule.id,
      grounded: nearby.length > 0 && inUse,
      requirement: rule.requirement,
      reason: !nearby.length
        ? `No matching physical work tool is close enough for ${normalized}.`
        : !inUse
          ? `${nearby[0].label} exists nearby, but the body has not reached and begun using it.`
          : `The body is actively using ${nearby[0].label}.`,
      evidence: nearby.slice(0, 5),
      nearestEvidence: evidence[0] || null,
      activeUse: inUse,
    };
  }
  return {
    action: normalized,
    rule: rule.id,
    grounded: nearby.length > 0,
    requirement: rule.requirement,
    reason: nearby.length
      ? `Physical evidence found: ${nearby[0].label}.`
      : `No matching physical prop is close enough for ${normalized}.`,
    evidence: nearby.slice(0, 5),
    nearestEvidence: evidence[0] || null,
  };
}

function addFrontWindowOpening(name, x, y, width = 1.05, height = 1.2, floor = 0) {
  const trimZ = 7.885;
  addBox(`${name} glass`, x, y, 7.875, width, height, 0.04, materials.glass, false);
  addBox(`${name} outer casing top`, x, y + height * 0.5 + 0.16, trimZ, width + 0.38, 0.1, 0.09, materials.windowFrame, false);
  addBox(`${name} outer casing bottom`, x, y - height * 0.5 - 0.16, trimZ, width + 0.38, 0.1, 0.09, materials.windowFrame, false);
  addBox(`${name} outer casing left`, x - width * 0.5 - 0.16, y, trimZ, 0.1, height + 0.42, 0.09, materials.windowFrame, false);
  addBox(`${name} outer casing right`, x + width * 0.5 + 0.16, y, trimZ, 0.1, height + 0.42, 0.09, materials.windowFrame, false);
  addBox(`${name} mullion v`, x, y, 7.93, 0.065, height + 0.16, 0.045, materials.trim, false);
  addBox(`${name} mullion h`, x, y, 7.935, width + 0.12, 0.065, 0.045, materials.trim, false);
}

function addBackWindowOpening(name, x, y, width = 1.05, height = 1.2, floor = 0) {
  const trimZ = -7.885;
  addBox(`${name} glass`, x, y, -7.875, width, height, 0.04, materials.glass, false);
  addBox(`${name} outer casing top`, x, y + height * 0.5 + 0.16, trimZ, width + 0.38, 0.1, 0.09, materials.windowFrame, false);
  addBox(`${name} outer casing bottom`, x, y - height * 0.5 - 0.16, trimZ, width + 0.38, 0.1, 0.09, materials.windowFrame, false);
  addBox(`${name} outer casing left`, x - width * 0.5 - 0.16, y, trimZ, 0.1, height + 0.42, 0.09, materials.windowFrame, false);
  addBox(`${name} outer casing right`, x + width * 0.5 + 0.16, y, trimZ, 0.1, height + 0.42, 0.09, materials.windowFrame, false);
  addBox(`${name} mullion v`, x, y, -7.93, 0.065, height + 0.16, 0.045, materials.trim, false);
  addBox(`${name} mullion h`, x, y, -7.935, width + 0.12, 0.065, 0.045, materials.trim, false);
}

function addSideWindowOpening(name, side, y, z, width = 1.05, height = 1.2, floor = 0) {
  const x = side < 0 ? -7.875 : 7.875;
  const trimX = side < 0 ? -7.885 : 7.885;
  addBox(`${name} glass`, x, y, z, 0.035, height, width, materials.glass, false);
  addBox(`${name} outer casing top`, trimX, y + height * 0.5 + 0.16, z, 0.09, 0.1, width + 0.38, materials.windowFrame, false);
  addBox(`${name} outer casing bottom`, trimX, y - height * 0.5 - 0.16, z, 0.09, 0.1, width + 0.38, materials.windowFrame, false);
  addBox(`${name} outer casing front`, trimX, y, z + width * 0.5 + 0.16, 0.09, height + 0.42, 0.1, materials.windowFrame, false);
  addBox(`${name} outer casing rear`, trimX, y, z - width * 0.5 - 0.16, 0.09, height + 0.42, 0.1, materials.windowFrame, false);
  addBox(`${name} mullion v`, side < 0 ? -7.93 : 7.93, y, z, 0.045, height + 0.16, 0.065, materials.trim, false);
  addBox(`${name} mullion h`, side < 0 ? -7.935 : 7.935, y, z, 0.045, 0.065, width + 0.12, materials.trim, false);
}

function addFrontWallSegmented(name, xMin, xMax, yCenter, height, windows, floor = 0) {
  const z = 7.75;
  const depth = 0.22;
  const wallTop = yCenter + height / 2;
  const wallBottom = yCenter - height / 2;
  const windowRects = windows.map((w) => ({
    x: w.x,
    width: w.width ?? 1.05,
    y: w.y ?? yCenter,
    height: w.height ?? 1.2,
  }));
  const xCuts = [xMin, xMax];
  for (const w of windowRects) {
    xCuts.push(w.x - w.width / 2 - 0.22, w.x + w.width / 2 + 0.22);
  }
  xCuts.sort((a, b) => a - b);
  for (let i = 0; i < xCuts.length - 1; i++) {
    const a = Math.max(xMin, xCuts[i]);
    const b = Math.min(xMax, xCuts[i + 1]);
    if (b <= a) continue;
    const overlapsWindow = windowRects.some((w) => a >= w.x - w.width / 2 - 0.23 && b <= w.x + w.width / 2 + 0.23);
    if (!overlapsWindow) addBox(`${name} wall vertical segment`, (a + b) / 2, yCenter, z, b - a, height, depth, materials.exterior, false);
  }
  for (const w of windowRects) {
    const left = Math.max(xMin, w.x - w.width / 2 - 0.22);
    const right = Math.min(xMax, w.x + w.width / 2 + 0.22);
    const topY = w.y + w.height / 2 + 0.22;
    const bottomY = w.y - w.height / 2 - 0.22;
    if (wallTop > topY) addBox(`${name} wall above window`, (left + right) / 2, (wallTop + topY) / 2, z, right - left, wallTop - topY, depth, materials.exterior, false);
    if (bottomY > wallBottom) addBox(`${name} wall below window`, (left + right) / 2, (bottomY + wallBottom) / 2, z, right - left, bottomY - wallBottom, depth, materials.exterior, false);
    addFrontWindowOpening(`${name} window ${w.x}`, w.x, w.y, w.width, w.height, floor);
  }
}

function addBackWallSegmented(name, xMin, xMax, yCenter, height, windows, floor = 0) {
  const z = -7.75;
  const depth = 0.22;
  const wallTop = yCenter + height / 2;
  const wallBottom = yCenter - height / 2;
  const openings = windows.map((w) => ({
    x: w.x,
    width: w.width ?? 1.05,
    y: w.y ?? yCenter,
    height: w.height ?? 1.2,
    type: w.type ?? "window",
  }));
  const xCuts = [xMin, xMax];
  for (const w of openings) xCuts.push(w.x - w.width / 2 - 0.22, w.x + w.width / 2 + 0.22);
  xCuts.sort((a, b) => a - b);
  for (let i = 0; i < xCuts.length - 1; i++) {
    const a = Math.max(xMin, xCuts[i]);
    const b = Math.min(xMax, xCuts[i + 1]);
    if (b <= a) continue;
    const overlaps = openings.some((w) => a >= w.x - w.width / 2 - 0.23 && b <= w.x + w.width / 2 + 0.23);
    if (!overlaps) addBox(`${name} wall vertical segment`, (a + b) / 2, yCenter, z, b - a, height, depth, materials.exterior, false);
  }
  for (const w of openings) {
    const left = Math.max(xMin, w.x - w.width / 2 - 0.22);
    const right = Math.min(xMax, w.x + w.width / 2 + 0.22);
    const topY = w.y + w.height / 2 + 0.22;
    const bottomY = w.y - w.height / 2 - 0.22;
    if (wallTop > topY) addBox(`${name} wall above opening`, (left + right) / 2, (wallTop + topY) / 2, z, right - left, wallTop - topY, depth, materials.exterior, false);
    if (bottomY > wallBottom) addBox(`${name} wall below opening`, (left + right) / 2, (bottomY + wallBottom) / 2, z, right - left, bottomY - wallBottom, depth, materials.exterior, false);
    if (w.type === "door") {
      addBackDoorFrame(name, w.x, w.width);
      if (floor === 0) backDoorLeaf = createBackDoorLeaf(`${name} back door`, w.x, w.width);
    } else {
      addBackWindowOpening(`${name} window ${w.x}`, w.x, w.y, w.width, w.height, floor);
    }
  }
}

function addSideWallSegmented(name, side, zMin, zMax, yCenter, height, windows, floor = 0) {
  const x = side < 0 ? -8 : 8;
  const depth = 0.22;
  const wallTop = yCenter + height / 2;
  const wallBottom = yCenter - height / 2;
  const openings = windows.map((w) => ({
    z: w.z,
    width: w.width ?? 1.05,
    y: w.y ?? yCenter,
    height: w.height ?? 1.2,
  }));
  const zCuts = [zMin, zMax];
  for (const w of openings) zCuts.push(w.z - w.width / 2 - 0.22, w.z + w.width / 2 + 0.22);
  zCuts.sort((a, b) => a - b);
  for (let i = 0; i < zCuts.length - 1; i++) {
    const a = Math.max(zMin, zCuts[i]);
    const b = Math.min(zMax, zCuts[i + 1]);
    if (b <= a) continue;
    const overlaps = openings.some((w) => a >= w.z - w.width / 2 - 0.23 && b <= w.z + w.width / 2 + 0.23);
    if (!overlaps) addBox(`${name} wall vertical segment`, x, yCenter, (a + b) / 2, depth, height, b - a, materials.exterior, false);
  }
  for (const w of openings) {
    const front = Math.max(zMin, w.z - w.width / 2 - 0.22);
    const rear = Math.min(zMax, w.z + w.width / 2 + 0.22);
    const topY = w.y + w.height / 2 + 0.22;
    const bottomY = w.y - w.height / 2 - 0.22;
    if (wallTop > topY) addBox(`${name} wall above window`, x, (wallTop + topY) / 2, (front + rear) / 2, depth, wallTop - topY, rear - front, materials.exterior, false);
    if (bottomY > wallBottom) addBox(`${name} wall below window`, x, (bottomY + wallBottom) / 2, (front + rear) / 2, depth, bottomY - wallBottom, rear - front, materials.exterior, false);
    addSideWindowOpening(`${name} window ${w.z}`, side, w.y, w.z, w.width, w.height, floor);
  }
}

function createFrontDoorLeaf(name, side) {
  const group = new THREE.Group();
  group.name = name;
  const panelWidth = 0.98;
  const hingeX = side < 0 ? -0.98 : 0.98;
  const centerOffset = side < 0 ? panelWidth / 2 : -panelWidth / 2;
  group.position.set(hingeX, 1.2, 7.98);

  const panel = new THREE.Mesh(new THREE.BoxGeometry(panelWidth, 2.25, 0.08), materials.door);
  panel.name = `${name} panel`;
  panel.position.set(centerOffset, 0, 0);
  panel.castShadow = true;
  panel.receiveShadow = true;
  group.add(panel);

  const pullX = side < 0 ? centerOffset + panelWidth * 0.34 : centerOffset - panelWidth * 0.34;
  const pull = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.42, 0.07), materials.handle);
  pull.name = `${name} exterior pull handle`;
  pull.position.set(pullX, -0.02, 0.075);
  pull.castShadow = true;
  group.add(pull);

  const insidePull = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.42, 0.07), materials.handle);
  insidePull.name = `${name} interior pull handle`;
  insidePull.position.set(pullX, -0.02, -0.075);
  insidePull.castShadow = true;
  group.add(insidePull);

  const knob = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.055, 24), materials.handle);
  knob.name = `${name} exterior knob`;
  knob.rotation.x = Math.PI / 2;
  knob.position.set(pullX, -0.02, 0.13);
  knob.castShadow = true;
  group.add(knob);

  const insideKnob = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.055, 24), materials.handle);
  insideKnob.name = `${name} interior knob`;
  insideKnob.rotation.x = Math.PI / 2;
  insideKnob.position.set(pullX, -0.02, -0.13);
  insideKnob.castShadow = true;
  group.add(insideKnob);

  scene.add(group);
  return group;
}

function addBackDoorFrame(name, x, width) {
  addBox(`${name} back door left jamb`, x - width * 0.48, 1.34, -7.62, 0.1, 2.55, 0.14, materials.windowFrame, false);
  addBox(`${name} back door right jamb`, x + width * 0.48, 1.34, -7.62, 0.1, 2.55, 0.14, materials.windowFrame, false);
  addBox(`${name} back door header`, x, 2.62, -7.62, width + 0.16, 0.12, 0.14, materials.windowFrame, false);
  addBox(`${name} back door threshold`, x, 0.08, -7.55, width + 0.18, 0.14, 0.44, materials.sidewalk, false);
}

function createBackDoorLeaf(name, x, width) {
  const group = new THREE.Group();
  group.name = name;
  const panelWidth = width * 0.82;
  const hingeX = x - panelWidth / 2;
  group.position.set(hingeX, 1.22, -7.66);

  const panel = new THREE.Mesh(new THREE.BoxGeometry(panelWidth, 2.25, 0.08), materials.door);
  panel.name = `${name} panel`;
  panel.position.set(panelWidth / 2, 0, 0);
  panel.castShadow = true;
  panel.receiveShadow = true;
  group.add(panel);

  for (const sideZ of [-0.075, 0.075]) {
    const handle = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.34, 0.055), materials.handle);
    handle.name = `${name} ${sideZ < 0 ? "outside" : "inside"} handle`;
    handle.position.set(panelWidth * 0.75, -0.02, sideZ);
    handle.castShadow = true;
    group.add(handle);

    const knob = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.065, 0.05, 20), materials.handle);
    knob.name = `${name} ${sideZ < 0 ? "outside" : "inside"} knob`;
    knob.rotation.x = Math.PI / 2;
    knob.position.set(panelWidth * 0.75, -0.02, sideZ * 1.6);
    knob.castShadow = true;
    group.add(knob);
  }

  scene.add(group);
  return group;
}

function createBathroomDoorLeaf(name, hingeX, z, swingSign) {
  const y = floorBase(1);
  const group = new THREE.Group();
  group.name = name;
  group.position.set(hingeX, 0, z);

  const panel = new THREE.Mesh(new THREE.BoxGeometry(1.0, 2.05, 0.08), materials.wood);
  panel.name = `${name} panel`;
  panel.position.set(0.5, y + 1.08, 0);
  panel.castShadow = true;
  panel.receiveShadow = true;
  group.add(panel);

  for (const sideZ of [-0.075, 0.075]) {
    const handle = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.16, 0.055), materials.handle);
    handle.name = `${name} ${sideZ < 0 ? "inside" : "outside"} handle`;
    handle.position.set(0.84, y + 1.05, sideZ);
    handle.castShadow = true;
    group.add(handle);
  }

  group.userData.closedRotation = 0;
  group.userData.openRotation = swingSign * Math.PI / 2;
  scene.add(group);
  return group;
}

function addBathroomDoorFrame(name, hingeX, z, floor) {
  const y = floorBase(floor);
  const centerX = hingeX + 0.5;
  addBox(`${name} left jamb`, hingeX - 0.06, y + 1.12, z, 0.12, 2.32, 0.16, materials.windowFrame, false, floor);
  addBox(`${name} right jamb`, hingeX + 1.06, y + 1.12, z, 0.12, 2.32, 0.16, materials.windowFrame, false, floor);
  addBox(`${name} header casing`, centerX, y + 2.31, z, 1.26, 0.16, 0.18, materials.windowFrame, false, floor);
  addBox(`${name} threshold`, centerX, y + 0.035, z, 1.22, 0.07, 0.2, materials.counter, false, floor);
}

function addReflectiveMirror(name, x, y, z, width, height, floor, normalSign = 1) {
  const mirror = new Reflector(new THREE.PlaneGeometry(width, height), {
    clipBias: 0.003,
    textureWidth: Math.min(window.innerWidth * window.devicePixelRatio, 2048),
    textureHeight: Math.min(window.innerHeight * window.devicePixelRatio, 2048),
    color: 0x9fb2bc,
  });
  mirror.name = name;
  mirror.position.set(x, y, z);
  mirror.rotation.y = normalSign >= 0 ? Math.PI / 2 : -Math.PI / 2;
  scene.add(mirror);
  const frameX = x + normalSign * 0.01;
  addBox(`${name} frame top`, frameX, y + height * 0.5 + 0.04, z, 0.05, 0.08, width + 0.1, materials.windowFrame, false, floor);
  addBox(`${name} frame bottom`, frameX, y - height * 0.5 - 0.04, z, 0.05, 0.08, width + 0.1, materials.windowFrame, false, floor);
  addBox(`${name} frame left`, frameX, y, z - width * 0.5 - 0.04, 0.05, height + 0.16, 0.08, materials.windowFrame, false, floor);
  addBox(`${name} frame right`, frameX, y, z + width * 0.5 + 0.04, 0.05, height + 0.16, 0.08, materials.windowFrame, false, floor);
  colliders.push({ x, z, sx: 0.14, sz: width + 0.18, floor });
  return mirror;
}

function addBackWallReflectiveMirror(name, x, y, z, width, height, floor = 0, normalSign = 1) {
  const mirror = new Reflector(new THREE.PlaneGeometry(width, height), {
    clipBias: 0.003,
    textureWidth: Math.min(window.innerWidth * window.devicePixelRatio, 2048),
    textureHeight: Math.min(window.innerHeight * window.devicePixelRatio, 2048),
    color: 0x9fb2bc,
  });
  mirror.name = name;
  mirror.position.set(x, y, z);
  if (normalSign < 0) mirror.rotation.y = Math.PI;
  scene.add(mirror);
  markTruthProp(mirror, "mirror", name, floor, ["wash_hands", "brush_teeth", "inspect_avatar"]);
  const frameZ = z + normalSign * 0.025;
  addBox(`${name} frame top`, x, y + height * 0.5 + 0.04, frameZ, width + 0.1, 0.08, 0.05, materials.windowFrame, false, floor);
  addBox(`${name} frame bottom`, x, y - height * 0.5 - 0.04, frameZ, width + 0.1, 0.08, 0.05, materials.windowFrame, false, floor);
  addBox(`${name} frame left`, x - width * 0.5 - 0.04, y, frameZ, 0.08, height + 0.16, 0.05, materials.windowFrame, false, floor);
  addBox(`${name} frame right`, x + width * 0.5 + 0.04, y, frameZ, 0.08, height + 0.16, 0.05, materials.windowFrame, false, floor);
  colliders.push({ x, z, sx: width + 0.18, sz: 0.14, floor });
  return mirror;
}

function setBathroomDoorOpen(group, open) {
  if (!group) return;
  group.rotation.y = open ? group.userData.openRotation : group.userData.closedRotation;
}

function setFrontDoorOpen(open) {
  frontDoorOpen = open;
  if (frontDoorLeft && frontDoorRight) {
    frontDoorLeft.rotation.y = frontDoorOpen ? Math.PI / 2 : 0;
    frontDoorRight.rotation.y = frontDoorOpen ? -Math.PI / 2 : 0;
    if (frontDoorLeftClosed) frontDoorLeft.position.copy(frontDoorLeftClosed);
    if (frontDoorRightClosed) frontDoorRight.position.copy(frontDoorRightClosed);
  }
}

function setBackDoorOpen(open) {
  backDoorOpen = open;
  if (backDoorLeaf) backDoorLeaf.rotation.y = backDoorOpen ? -Math.PI / 2 : 0;
}

function setNeighborHouseDoorOpen(open) {
  neighborHouseDoorOpen = !!open;
  const hasImportedFrontDoorVisual = neighborImportedFrontDoorVisuals.some((door) => door?.parent);
  if (neighborHouseDoorLeaf) {
    neighborHouseDoorLeaf.visible = !hasImportedFrontDoorVisual && (neighborHouseDoorOpen || !neighborEntryDoorReference);
    neighborHouseDoorLeaf.rotation.y = neighborHouseDoorOpen ? Math.PI / 2 : 0;
  }
  if (neighborEntryDoorReference) neighborEntryDoorReference.visible = !neighborHouseDoorOpen;
  for (const door of neighborImportedFrontDoorVisuals) {
    if (door) door.visible = !neighborHouseDoorOpen;
  }
  if (neighborFallbackDoorGroup) neighborFallbackDoorGroup.visible = !neighborEntryDoorReference && !neighborHouseDoorLeaf && !neighborHouseDoorOpen;
}

function setKitchenFridgeOpen(open) {
  kitchenFridgeDoorOpen = open;
  if (kitchenFridgeDoorGroup) {
    kitchenFridgeDoorGroup.rotation.y = kitchenFridgeDoorOpen ? -Math.PI / 2 : 0;
  }
}

function smoothStep01(value) {
  const t = THREE.MathUtils.clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
}

function faceActiveAvatarToward(x, z, dt = 1 / 60) {
  if (!activeMarker) return;
  const dx = x - activeMarker.position.x;
  const dz = z - activeMarker.position.z;
  if (Math.hypot(dx, dz) < 0.001) return;
  return turnActiveAvatarTowardYaw(Math.atan2(dx, dz) + Math.PI, dt);
}

function activeAvatarMovementSnapshot(extra = {}) {
  return {
    source: "home_world_runtime",
    avatar: activeMarker?.userData?.label || "active avatar",
    action: activeAvatarAction,
    activeShellClaim: activeShellClaimSnapshot(),
    mindBodyTruth: activeMindBodyTruthSnapshot(extra?.phase || extra?.reason || "movement_snapshot", extra?.claimedAction || activeShellState?.active_action || activeAvatarAction),
    position: activeMarker ? {
      x: Number(activeMarker.position.x.toFixed(3)),
      y: Number(activeMarker.position.y.toFixed(3)),
      z: Number(activeMarker.position.z.toFixed(3)),
    } : null,
    walkCyclePhase: Number((activeMarker?.userData?.walkCyclePhase ?? activeAvatarMovePhase).toFixed(3)),
    ...extra,
  };
}

function activeShellClaimSnapshot() {
  if (!activeShellState) return null;
  return {
    candidate: activeShellState.active_candidate || null,
    label: activeShellState.active_label || null,
    action: activeShellState.active_action || null,
    location: activeShellState.location || null,
    model: activeShellState.model || null,
  };
}

function activeAvatarPracticeRouteProgressSnapshot() {
  if (!activeMarker) return null;
  const route = activeMarker.userData?.practiceRoute;
  if (!route?.waypoints?.length) return null;
  const index = Math.min(
    Math.max(Number(activeMarker.userData.roamIndex || 0), 0),
    route.waypoints.length - 1,
  );
  const target = route.waypoints[index];
  const distanceMeters = target
    ? Math.hypot(target.x - activeMarker.position.x, target.z - activeMarker.position.z)
    : null;
  const waypointLabel = route.waypointLabels?.[index] || `waypoint_${index}`;
  const status = activeMarker.userData.navigationRecovery
    ? "collision_recovery"
    : activeMarker.userData.isMoving
      ? "walking"
      : clock.elapsedTime < Number(activeMarker.userData.waitUntil || 0)
        ? "brief_transition_pause"
        : "paused_while_route_remains_active";
  return {
    id: route.id,
    status,
    waypointIndex: index,
    waypointCount: route.waypoints.length,
    waypointLabel,
    target: target ? {
      x: Number(target.x.toFixed(3)),
      y: Number(target.y.toFixed(3)),
      z: Number(target.z.toFixed(3)),
    } : null,
    distanceMeters: Number.isFinite(distanceMeters) ? Number(distanceMeters.toFixed(3)) : null,
    requiresHomeEntry: !!route.requiresHomeEntry,
    homeEntryReplanCount: Number(route.homeEntryReplanCount || 0),
    interiorRoute: !!route.interiorRoute,
    interiorPlanMode: route.interiorPlanMode || null,
    interiorReplanCount: Number(route.interiorReplanCount || 0),
    coalescedIntentCount: Number(route.coalescedIntentCount || 0),
    progressWatch: route.progressWatch ? {
      status: route.progressWatch.status || "progressing",
      pathLengthMeters: Number((route.progressWatch.pathLengthMeters || 0).toFixed(3)),
      netMeters: Number((route.progressWatch.netMeters || 0).toFixed(3)),
      stalled: !!route.progressWatch.stalled,
      oscillating: !!route.progressWatch.oscillating,
    } : null,
    personOwnedIntent: !!route.selfChosen,
    teleported: false,
  };
}

function activeBodyEvidenceSnapshot() {
  return {
    modelLoaded: !!activeAvatarRoot,
    moving: !!activeMarker?.userData?.isMoving,
    postureState: activeMarker?.userData?.postureState?.id || activeMarker?.userData?.postureState?.action || activeMarker?.userData?.postureState || null,
    supportState: activeMarker?.userData?.supportState || null,
    walkSpeed: Number((activeMarker?.userData?.walkSpeed || 0).toFixed(3)),
    walkTimeScale: Number((activeMarker?.userData?.walkTimeScale || 0).toFixed(3)),
    footContacts: activeMarker?.userData?.footContacts || null,
    fingerContacts: activeMarker?.userData?.fingerContacts || [],
    transitionEvidence: activeMarker?.userData?.transitionEvidence || null,
    navigationRecovery: activeMarker?.userData?.navigationRecovery || null,
    localSteeringEvidence: activeMarker?.userData?.localSteeringEvidence || null,
    locomotionTransition: activeMarker?.userData?.locomotionTransition || null,
    turnEvidence: activeMarker?.userData?.turnEvidence || null,
    routeProgress: activeAvatarPracticeRouteProgressSnapshot(),
    currentPlace: activeMarker ? activeAvatarNamedPlaceSnapshot() : null,
    lastEmbodimentCapabilityBlock: activeMarker?.userData?.lastEmbodimentCapabilityBlock || null,
    lastRouteFailureTruth: activeMarker?.userData?.lastRouteFailureTruth || null,
    doorInteraction: activeDoorInteraction ? {
      id: activeDoorInteraction.id,
      opened: !!activeDoorInteraction.opened,
      gripped: !!activeDoorInteraction.gripped,
      ikSolved: !!activeDoorInteraction.ikSolved,
      ikGripLocked: !!activeDoorInteraction.ikGripLocked,
      handContact: activeDoorInteraction.handContact || null,
    } : null,
    furnitureInteraction: activeFurnitureInteraction ? {
      id: activeFurnitureInteraction.id,
      stage: activeFurnitureInteraction.stage,
    } : null,
    position: activeMarker ? {
      x: Number(activeMarker.position.x.toFixed(3)),
      y: Number(activeMarker.position.y.toFixed(3)),
      z: Number(activeMarker.position.z.toFixed(3)),
    } : null,
  };
}

function activeMindBodyTruthSnapshot(reason = "runtime_check", claimedAction = activeAvatarAction) {
  const shellClaim = activeShellClaimSnapshot();
  const runtimeAction = activeAvatarAction || "idle";
  const claimAction = String(claimedAction || shellClaim?.action || runtimeAction || "idle").toLowerCase();
  const runtimeActionLower = String(runtimeAction || "idle").toLowerCase();
  const body = activeBodyEvidenceSnapshot();
  const truth = activityTruthForAction(claimAction);
  const mismatchReasons = [];

  if (shellClaim?.action && String(shellClaim.action).toLowerCase() !== runtimeActionLower) {
    mismatchReasons.push(`shell claims ${shellClaim.action} while body action is ${runtimeAction}`);
  }
  if (truth.grounded === false) {
    mismatchReasons.push(truth.reason || `no grounded evidence for ${claimAction}`);
  }
  if (/walk|move|go|roam|stairs|cross|travel/.test(claimAction) && !body.moving && body.walkSpeed < 0.02) {
    mismatchReasons.push("motion claim but body is not moving");
  }
  if (/sit|sleep|lay|lie/.test(claimAction) && !body.postureState && runtimeActionLower !== "sit") {
    mismatchReasons.push("posture claim but no posture state is active on the body");
  }
  if (/door|open|handle/.test(claimAction) && body.doorInteraction && !body.doorInteraction.gripped && !body.doorInteraction.handContact) {
    mismatchReasons.push("door claim but no hand contact is registered");
  }

  return {
    reason,
    checkedAtSeconds: Number(clock.elapsedTime.toFixed(3)),
    shellClaim,
    runtimeAction,
    body,
    truth,
    agrees: mismatchReasons.length === 0,
    mismatchReasons,
  };
}

function recordMovementLearningAttempt(attempt) {
  try {
    const item = activeAvatarMovementSnapshot(attempt);
    window.kiraMovementLearning?.recordAttempt?.(item);
    if (attempt?.skill && attempt?.phase) window.kiraMovementLearning?.recordMomentDraft?.(item);
  } catch (err) {
    // Learning notes are helpful, but motion should never fail if storage is unavailable.
  }
}

function recordMindBodyTruthSnapshot(t) {
  if (!activeMarker) return;
  if (t - lastMindBodyTruthRecordAt < 5) return;
  lastMindBodyTruthRecordAt = t;
  const snapshot = activeMindBodyTruthSnapshot("periodic_runtime_truth", activeShellState?.active_action || activeAvatarAction);
  activeMarker.userData.lastMindBodyTruth = snapshot;
  try {
    window.localStorage.setItem("kira.avatar.mindBodyTruth.latest", JSON.stringify(snapshot));
  } catch (err) {
    // The shell can run without localStorage; truth data is still available live.
  }
  recordMovementLearningAttempt({
    skill: "mind_body_truth",
    phase: "periodic_runtime_truth",
    claimedAction: activeShellState?.active_action || activeAvatarAction,
  });
}

function activeAvatarWorldOffset(x, y, z) {
  if (!activeMarker) return new THREE.Vector3(x, y, z);
  return activeMarker.localToWorld(new THREE.Vector3(x, y, z));
}

function activeAvatarWorldDirection(x, y, z) {
  if (!activeMarker) return new THREE.Vector3(x, y, z).normalize();
  const origin = activeAvatarWorldOffset(0, 0, 0);
  return activeAvatarWorldOffset(x, y, z).sub(origin).normalize();
}

function placeCapsuleBetween(mesh, start, end) {
  const direction = end.clone().sub(start);
  const length = Math.max(0.001, direction.length());
  mesh.position.copy(start).addScaledVector(direction, 0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
  mesh.scale.set(1, length, 1);
}

function setDoorReachArmHidden(hidden) {
  if (!activeAvatarRoot) return;
  if (!hidden) {
    for (const item of activeDoorReachHiddenNodes) item.node.visible = item.visible;
    activeDoorReachHiddenNodes = [];
    return;
  }
  if (activeDoorReachHiddenNodes.length) return;
  const rightArmPattern = /(upper_arm_bone_visible|forearm_bone_visible|wrist_joint_visible|palm_visible|hand_proxy_|thumb_|index_|middle_|ring_|pinky_).*\.R$/i;
  activeAvatarRoot.traverse((node) => {
    if (!node.isMesh || !rightArmPattern.test(node.name || "")) return;
    activeDoorReachHiddenNodes.push({ node, visible: node.visible });
    node.visible = false;
  });
}

function ensureDoorReachRig() {
  if (activeDoorReachRig) return activeDoorReachRig;
  const boneMat = materials.boneProxy || materials.fixture;
  const skinMat = materials.skinProxy || materials.blanketPink;
  const jointMat = materials.jointProxy || materials.activeBlue;
  const group = new THREE.Group();
  group.name = "active_avatar_door_reach_procedural_arm";
  group.userData.upper = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.026, 1, 12), boneMat);
  group.userData.forearm = new THREE.Mesh(new THREE.CylinderGeometry(0.023, 0.023, 1, 12), boneMat);
  group.userData.elbow = new THREE.Mesh(new THREE.SphereGeometry(0.035, 14, 10), jointMat);
  group.userData.hand = new THREE.Mesh(new THREE.SphereGeometry(0.052, 14, 10), skinMat);
  group.userData.hand.scale.set(0.8, 1.05, 0.55);
  group.add(group.userData.upper, group.userData.forearm, group.userData.elbow, group.userData.hand);
  group.userData.fingers = [];
  for (let i = 0; i < 5; i += 1) {
    const finger = new THREE.Mesh(new THREE.CylinderGeometry(0.0065, 0.0075, 1, 8), skinMat);
    group.userData.fingers.push(finger);
    group.add(finger);
  }
  scene.add(group);
  activeDoorReachRig = group;
  return group;
}

function clearDoorReachRig() {
  setDoorReachArmHidden(false);
  if (activeDoorReachRig) {
    scene.remove(activeDoorReachRig);
    activeDoorReachRig = null;
  }
}

function updateDoorReachRig(age) {
  if (!activeDoorInteraction || !activeMarker) return;
  if (!ACTIVE_AVATAR_USE_PROCEDURAL_DOOR_ARM) {
    clearDoorReachRig();
    return;
  }
  setDoorReachArmHidden(true);
  const rig = ensureDoorReachRig();
  const reachK = smoothStep01(age / ACTIVE_AVATAR_DOOR_REACH_SECONDS);
  const shoulder = activeAvatarWorldOffset(0.18, 1.26, -0.02);
  const handle = activeDoorInteraction.handle.clone();
  const right = activeAvatarWorldDirection(1, 0, 0);
  const down = new THREE.Vector3(0, -1, 0);
  const hand = shoulder.clone().lerp(handle, 0.32 + reachK * 0.68);
  const elbow = shoulder.clone().lerp(hand, 0.53)
    .addScaledVector(right, 0.18 * (1 - reachK * 0.35))
    .addScaledVector(down, 0.10 + reachK * 0.10);

  placeCapsuleBetween(rig.userData.upper, shoulder, elbow);
  placeCapsuleBetween(rig.userData.forearm, elbow, hand);
  rig.userData.elbow.position.copy(elbow);
  rig.userData.hand.position.copy(hand);
  rig.userData.hand.lookAt(handle.clone().add(activeAvatarWorldDirection(0, 0, -1).multiplyScalar(0.2)));

  const gripK = activeDoorInteraction.gripped ? 1 : smoothStep01(Math.max(0, age - 0.55) / 0.35);
  const fingerForward = handle.clone().sub(hand).normalize();
  const fingerSide = right.clone().multiplyScalar(0.011);
  const fingerDown = new THREE.Vector3(0, -0.012, 0);
  rig.userData.fingers.forEach((finger, i) => {
    const spread = i - 2;
    const start = hand.clone()
      .addScaledVector(right, spread * 0.012)
      .add(new THREE.Vector3(0, -0.012 - Math.abs(spread) * 0.003, 0));
    const length = i === 0 ? 0.045 : 0.058 - Math.abs(spread) * 0.004;
    const curledEnd = start.clone()
      .addScaledVector(fingerForward, length * (1 - gripK * 0.38))
      .addScaledVector(fingerSide, -spread * gripK * 0.35)
      .addScaledVector(fingerDown, gripK * 2.4);
    placeCapsuleBetween(finger, start, curledEnd);
  });
}

function activeAvatarRigNameKey(name) {
  return String(name || "").toLowerCase().replace(/[._\-\s]/g, "");
}

function activeAvatarRigAliasKeys(name) {
  const raw = String(name || "").toLowerCase();
  const compact = activeAvatarRigNameKey(raw);
  const aliases = new Set([compact]);
  const side = raw.includes("left") || compact.includes("left") || /(^|[^a-z])l($|[^a-z])/.test(raw) ? "l"
    : raw.includes("right") || compact.includes("right") || /(^|[^a-z])r($|[^a-z])/.test(raw) ? "r"
      : "";
  if (!side) return aliases;

  const sideTitle = side === "l" ? "L" : "R";
  const add = (...names) => {
    for (const alias of names) aliases.add(activeAvatarRigNameKey(alias));
  };

  if ((compact.includes("upleg") || compact.includes("thigh")) && !compact.includes("lower")) add(`thigh.${sideTitle}`);
  if ((compact.includes("lowerleg") || compact.includes("shin") || compact.includes("calf") || compact.includes("leftleg") || compact.includes("rightleg")) && !compact.includes("upleg")) add(`shin.${sideTitle}`);
  if (compact.includes("foot") && !compact.includes("toe")) add(`foot.${sideTitle}`);
  if ((compact.includes("upperarm") || compact.includes(`${side === "l" ? "left" : "right"}arm`) || compact.includes("arm")) && !compact.includes("forearm") && !compact.includes("lower") && !compact.includes("hand")) add(`upper_arm.${sideTitle}`);
  if (compact.includes("forearm") || compact.includes("lowerarm")) add(`forearm.${sideTitle}`);
  if (compact.includes("hand") && !compact.includes("thumb") && !compact.includes("index") && !compact.includes("middle") && !compact.includes("ring") && !compact.includes("pinky")) add(`hand.${sideTitle}`);

  for (const finger of ["thumb", "index", "middle", "ring", "pinky"]) {
    const match = compact.match(new RegExp(`${finger}(\\d+)`));
    if (!match) continue;
    const digit = Number(match[1].slice(0, 1));
    if (Number.isFinite(digit) && digit > 0) add(`${finger}.${String(digit).padStart(2, "0")}.${sideTitle}`);
  }
  return aliases;
}

function activeAvatarRigNameMatchesWanted(nodeName, wanted) {
  for (const key of activeAvatarRigAliasKeys(nodeName)) {
    if (wanted.has(key)) return true;
  }
  return false;
}

function activeAvatarHandContactNames(preferredSide = null) {
  const sides = preferredSide ? [preferredSide] : ["R", "L"];
  const fingers = ["thumb", "index", "middle", "ring", "pinky"];
  const names = [];
  for (const side of sides) {
    const s = String(side || "R").toUpperCase();
    names.push(`hand.${s}`, `palm_visible.${s}`, `skinned_hand_mesh.${s}`);
    for (const finger of fingers) {
      names.push(
        `hand_contact_collider_${finger}_tip.${s}`,
        `hand_proxy_${finger}_tip.${s}`,
        `${finger}.03.${s}`,
      );
    }
  }
  return names;
}

function activeAvatarFindRigNode(names, options = {}) {
  if (!activeAvatarRoot) return null;
  const wanted = new Set(names.map(activeAvatarRigNameKey));
  let fallback = null;
  activeAvatarRoot.traverse((node) => {
    if (fallback) return;
    if (options.boneOnly && !node.isBone) return;
    if (options.meshOnly && !node.isMesh) return;
    if (!activeAvatarRigNameMatchesWanted(node.name, wanted)) return;
    fallback = node;
  });
  return fallback;
}

function activeAvatarClosestHandContact(target, preferredSide = null) {
  if (!activeAvatarRoot || !target) return null;
  if (activeMarker) activeMarker.updateMatrixWorld(true);
  activeAvatarRoot.updateMatrixWorld(true);
  const wanted = new Set(activeAvatarHandContactNames(preferredSide).map(activeAvatarRigNameKey));
  let best = null;
  const position = new THREE.Vector3();
  activeAvatarRoot.traverse((node) => {
    if (!activeAvatarRigNameMatchesWanted(node.name, wanted)) return;
    node.getWorldPosition(position);
    const distance = position.distanceTo(target);
    if (!best || distance < best.distance) {
      best = {
        node: node.name,
        distance,
        position: position.clone(),
      };
    }
  });
  return best;
}

function rotateActiveAvatarBoneTowardTarget(bone, effector, target, strength = 0.4) {
  if (!bone || !effector || !target) return;
  activeAvatarRoot.updateMatrixWorld(true);
  const bonePosition = bone.getWorldPosition(new THREE.Vector3());
  const effectorPosition = effector.getWorldPosition(new THREE.Vector3());
  const toEffector = effectorPosition.sub(bonePosition).normalize();
  const toTarget = target.clone().sub(bonePosition).normalize();
  if (toEffector.lengthSq() < 0.0001 || toTarget.lengthSq() < 0.0001) return;
  const deltaWorld = new THREE.Quaternion().setFromUnitVectors(toEffector, toTarget);
  const boneWorld = bone.getWorldQuaternion(new THREE.Quaternion());
  const desiredWorld = deltaWorld.multiply(boneWorld);
  const parentWorld = bone.parent?.getWorldQuaternion(new THREE.Quaternion()) || new THREE.Quaternion();
  const desiredLocal = parentWorld.invert().multiply(desiredWorld);
  bone.quaternion.slerp(desiredLocal, THREE.MathUtils.clamp(strength, 0, 1));
  bone.updateMatrixWorld(true);
}

const ACTIVE_AVATAR_RELAXED_HAND_CURLS = {
  thumb: [-18, -15, -8],
  index: [-36, -26, -15],
  middle: [-40, -29, -17],
  ring: [-38, -27, -16],
  pinky: [-34, -24, -14],
};
const ACTIVE_AVATAR_GRIP_HAND_CURLS = {
  thumb: [-38, -28, -16],
  index: [-58, -44, -28],
  middle: [-62, -47, -30],
  ring: [-54, -41, -26],
  pinky: [-44, -33, -21],
};

function applyActiveAvatarFingerPose(side, curls, amount, options = {}) {
  const s = String(side || "R").toUpperCase();
  const poseAmount = THREE.MathUtils.clamp(amount, 0, 1);
  for (const [finger, values] of Object.entries(curls)) {
    values.forEach((degrees, index) => {
      const bone = activeAvatarFindRigNode([`${finger}.${String(index + 1).padStart(2, "0")}.${s}`], { boneOnly: true });
      if (!bone) return;
      bone.rotation.x = THREE.MathUtils.lerp(bone.rotation.x, THREE.MathUtils.degToRad(degrees), poseAmount * (options.xStrength ?? 0.72));
      if (finger === "thumb" && index === 0 && Number.isFinite(options.thumbOpposeDegrees)) {
        const oppose = s === "R" ? -options.thumbOpposeDegrees : options.thumbOpposeDegrees;
        bone.rotation.z = THREE.MathUtils.lerp(bone.rotation.z, THREE.MathUtils.degToRad(oppose), poseAmount * (options.zStrength ?? 0.6));
      }
    });
  }
}

function applyActiveAvatarRelaxedHands() {
  if (!activeAvatarRoot) return;
  if (activeDoorInteraction) return;
  const posture = activeMarker?.userData?.postureState;
  const amount = posture ? 0.9 : activeAvatarAction === "walk" ? 0.72 : 0.82;
  applyActiveAvatarFingerPose("L", ACTIVE_AVATAR_RELAXED_HAND_CURLS, amount, { thumbOpposeDegrees: 18, xStrength: 0.55, zStrength: 0.42 });
  applyActiveAvatarFingerPose("R", ACTIVE_AVATAR_RELAXED_HAND_CURLS, amount, { thumbOpposeDegrees: 18, xStrength: 0.55, zStrength: 0.42 });
}

function applyActiveAvatarFingerGrip(side, amount) {
  applyActiveAvatarFingerPose(side, ACTIVE_AVATAR_GRIP_HAND_CURLS, amount, { thumbOpposeDegrees: 22, xStrength: 0.74, zStrength: 0.62 });
}

function updateActiveAvatarObjectFingerContacts() {
  if (!activeMarker || !activeAvatarRoot) return;
  const contacts = [];
  if (activeDoorInteraction?.handle) {
    const contact = activeAvatarClosestHandContact(activeDoorInteraction.handle, activeDoorInteraction.preferredHand);
    if (contact) {
      contacts.push({
        object: activeDoorInteraction.id,
        kind: "door_handle",
        node: contact.node,
        distance: Number(contact.distance.toFixed(3)),
        touching: contact.distance <= ACTIVE_AVATAR_DOOR_HAND_TOUCH_METERS,
      });
    }
  }
  activeMarker.userData.fingerContacts = contacts;
}

function activeAvatarFootPhase(side) {
  const offset = String(side || "L").toUpperCase() === "R" ? 0.5 : 0;
  return (activeAvatarWalkPhase01() + offset) % 1;
}

function applyActiveAvatarFootContactLocks() {
  if (!activeAvatarRoot || !activeMarker) return;
  const locomotionBlend = THREE.MathUtils.clamp(Number(activeMarker.userData.locomotionBlend || 0), 0, 1);
  if ((!activeAvatarActionIsGroundedLocomotion() && locomotionBlend < 0.08) || locomotionBlend < 0.025) {
    activeMarker.userData.footContacts = null;
    activeMarker.userData.footPlantTargets = null;
    activeMarker.userData.footPlantWasPlanted = null;
    return;
  }
  if (activeMarker.userData.postureState || activeDoorInteraction || activeFurnitureInteraction) {
    activeMarker.userData.footContacts = null;
    activeMarker.userData.footPlantTargets = null;
    activeMarker.userData.footPlantWasPlanted = null;
    return;
  }
  const support = activeMarker.userData.supportState;
  if (!support || support.falling || !Number.isFinite(support.y)) {
    activeMarker.userData.footContacts = null;
    activeMarker.userData.footPlantTargets = null;
    activeMarker.userData.footPlantWasPlanted = null;
    return;
  }

  const plantTargets = activeMarker.userData.footPlantTargets || {};
  const previousPlantState = activeMarker.userData.footPlantWasPlanted || {};
  const contactState = {};
  for (const side of ["L", "R"]) {
    const foot = activeAvatarFindRigNode([`foot.${side}`], { boneOnly: true });
    const shin = activeAvatarFindRigNode([`shin.${side}`], { boneOnly: true });
    const thigh = activeAvatarFindRigNode([`thigh.${side}`], { boneOnly: true });
    if (!foot || !shin || !thigh) continue;
    activeAvatarRoot.updateMatrixWorld(true);
    const footWorld = foot.getWorldPosition(new THREE.Vector3());
    const phase = activeAvatarFootPhase(side);
    const planted = phase < 0.58;
    if (planted && (!previousPlantState[side] || !plantTargets[side])) {
      plantTargets[side] = {
        x: footWorld.x,
        y: support.y + ACTIVE_AVATAR_FOOT_CONTACT_HEIGHT,
        z: footWorld.z,
      };
    } else if (!planted) {
      delete plantTargets[side];
    }
    let target = planted && plantTargets[side]
      ? new THREE.Vector3(plantTargets[side].x, plantTargets[side].y, plantTargets[side].z)
      : footWorld.clone().setY(support.y + ACTIVE_AVATAR_FOOT_CONTACT_HEIGHT);
    const targetDrift = Math.hypot(target.x - footWorld.x, target.z - footWorld.z);
    if (planted && targetDrift > 0.55) {
      target = footWorld.clone().setY(support.y + ACTIVE_AVATAR_FOOT_CONTACT_HEIGHT);
      plantTargets[side] = { x: target.x, y: target.y, z: target.z };
    }
    const verticalError = footWorld.y - target.y;
    if (planted || Math.abs(verticalError) > 0.018 || support.isStair) {
      const strength = support.isStair ? 0.44 : 0.34;
      for (let i = 0; i < ACTIVE_AVATAR_FOOT_IK_ITERATIONS; i += 1) {
        rotateActiveAvatarBoneTowardTarget(shin, foot, target, strength);
        rotateActiveAvatarBoneTowardTarget(thigh, foot, target, strength * 0.62);
      }
    }
    activeAvatarRoot.updateMatrixWorld(true);
    const measuredFootWorld = foot.getWorldPosition(new THREE.Vector3());
    const horizontalResidual = Math.hypot(measuredFootWorld.x - target.x, measuredFootWorld.z - target.z);
    const verticalResidual = measuredFootWorld.y - target.y;
    contactState[side] = {
      locked: planted,
      worldLocked: planted,
      y: Number(measuredFootWorld.y.toFixed(3)),
      targetY: Number(target.y.toFixed(3)),
      targetX: Number(target.x.toFixed(3)),
      targetZ: Number(target.z.toFixed(3)),
      error: Number(verticalResidual.toFixed(3)),
      horizontalResidualMeters: Number(horizontalResidual.toFixed(3)),
      verticalResidualMeters: Number(verticalResidual.toFixed(3)),
      phase: Number(phase.toFixed(3)),
      visuallyReviewedThisSession: false,
    };
    previousPlantState[side] = planted;
  }
  activeMarker.userData.footPlantTargets = plantTargets;
  activeMarker.userData.footPlantWasPlanted = previousPlantState;
  activeMarker.userData.footContacts = contactState;
}

function activeAvatarVisualGroundCalibrationEligible() {
  if (!activeAvatarRoot || !activeMarker || !activeAvatarIsKiraLike()) return false;
  if (activeMarker.userData.postureState || activeDoorInteraction || activeFurnitureInteraction) return false;
  const support = activeMarker.userData.supportState;
  if (!support || support.falling || support.supported === false || !Number.isFinite(support.y)) return false;
  const action = String(activeAvatarAction || "idle").toLowerCase();
  return activeAvatarActionIsGroundedLocomotion(action)
    || ["idle", "talking", "wave", "arm_control_test"].includes(action);
}

function applyActiveAvatarVisualGroundContactCalibration(t, force = false) {
  if (!activeAvatarVisualGroundCalibrationEligible()) return null;
  const lastAt = Number(activeAvatarRoot.userData.lastVisualGroundCalibrationAt ?? -Infinity);
  if (!force && t - lastAt < ACTIVE_AVATAR_VISUAL_GROUND_CALIBRATION_SECONDS) {
    return activeMarker.userData.visualGroundContact || null;
  }
  activeAvatarRoot.userData.lastVisualGroundCalibrationAt = t;
  activeMarker.updateMatrixWorld(true);
  const bounds = new THREE.Box3().setFromObject(activeAvatarRoot, true);
  if (bounds.isEmpty() || !Number.isFinite(bounds.min.y)) return null;

  const supportY = Number(activeMarker.userData.supportState.y);
  const desiredMinY = supportY + ACTIVE_AVATAR_VISUAL_GROUND_CLEARANCE;
  const beforeGap = bounds.min.y - desiredMinY;
  const currentCorrection = Number(activeAvatarRoot.userData.visualGroundCorrectionY || 0);
  const maxCorrectionStep = force ? 0.08 : 0.025;
  const requestedDelta = THREE.MathUtils.clamp(-beforeGap, -maxCorrectionStep, maxCorrectionStep);
  const nextCorrection = THREE.MathUtils.clamp(
    currentCorrection + requestedDelta,
    ACTIVE_AVATAR_VISUAL_GROUND_CORRECTION_MIN,
    ACTIVE_AVATAR_VISUAL_GROUND_CORRECTION_MAX,
  );
  const appliedDelta = nextCorrection - currentCorrection;
  activeAvatarRoot.userData.visualGroundCorrectionY = nextCorrection;
  activeAvatarRoot.position.y += appliedDelta;
  activeAvatarRoot.updateMatrixWorld(true);
  const visualMinY = bounds.min.y + appliedDelta;
  const contact = {
    mode: "precise_deformed_mesh_ground_contact_v1",
    calibrated: true,
    supportY: Number(supportY.toFixed(4)),
    desiredMinY: Number(desiredMinY.toFixed(4)),
    visualMinY: Number(visualMinY.toFixed(4)),
    gapMeters: Number((visualMinY - desiredMinY).toFixed(4)),
    withinTolerance: Math.abs(visualMinY - desiredMinY) <= 0.006,
    correctionY: Number(nextCorrection.toFixed(4)),
    correctionClamped: nextCorrection === ACTIVE_AVATAR_VISUAL_GROUND_CORRECTION_MIN
      || nextCorrection === ACTIVE_AVATAR_VISUAL_GROUND_CORRECTION_MAX,
    modelUrl: activeAvatarModelUrl || null,
  };
  activeAvatarRoot.userData.visualGroundContact = contact;
  activeMarker.userData.visualGroundContact = contact;
  return contact;
}

function applyActiveDoorGripIK(t) {
  if (!activeDoorInteraction || !activeAvatarRoot || !activeMarker) return;
  const age = t - activeDoorInteraction.startedAt;
  const side = String(activeDoorInteraction.preferredHand || "R").toUpperCase();
  const handle = activeDoorInteraction.handle;
  if (activeMarker) activeMarker.updateMatrixWorld(true);
  activeAvatarRoot.updateMatrixWorld(true);

  const hand = activeAvatarFindRigNode([`hand.${side}`], { boneOnly: true });
  const forearm = activeAvatarFindRigNode([`forearm.${side}`], { boneOnly: true });
  const upperArm = activeAvatarFindRigNode([`upper_arm.${side}`], { boneOnly: true });
  const reachK = smoothStep01((age - ACTIVE_AVATAR_DOOR_IK_START_SECONDS) / Math.max(0.1, ACTIVE_AVATAR_DOOR_REACH_SECONDS - ACTIVE_AVATAR_DOOR_IK_START_SECONDS));
  if (hand && forearm && upperArm && reachK > 0) {
    const strength = 0.28 + reachK * 0.34;
    for (let i = 0; i < ACTIVE_AVATAR_DOOR_IK_ITERATIONS; i += 1) {
      rotateActiveAvatarBoneTowardTarget(forearm, hand, handle, strength);
      rotateActiveAvatarBoneTowardTarget(upperArm, hand, handle, strength * 0.78);
    }
    applyActiveAvatarFingerGrip(side, smoothStep01((age - 0.48) / 0.34));
    activeDoorInteraction.ikSolved = true;
  }

  const contact = activeAvatarClosestHandContact(handle, side);
  if (contact) {
    activeDoorInteraction.handContact = {
      node: contact.node,
      distance: Number(contact.distance.toFixed(3)),
      x: Number(contact.position.x.toFixed(3)),
      y: Number(contact.position.y.toFixed(3)),
      z: Number(contact.position.z.toFixed(3)),
      ik: !!activeDoorInteraction.ikSolved,
    };
    if (contact.distance <= ACTIVE_AVATAR_DOOR_HAND_TOUCH_METERS) {
      activeDoorInteraction.ikGripLocked = true;
    }
  }
}

function activeDoorCooldownId(id) {
  return String(id || "door").replace(/_debug$/, "");
}

function startActiveAvatarDoorInteraction(spec) {
  if (!activeMarker || !spec?.open) return false;
  if (activeDoorInteraction) return activeDoorInteraction.id === spec.id;
  const now = clock.elapsedTime;
  if (String(spec.id || "").endsWith("_debug")) activeDoorFailureCooldowns.delete(activeDoorCooldownId(spec.id));
  const cooldownUntil = activeDoorFailureCooldowns.get(activeDoorCooldownId(spec.id)) || 0;
  if (now < cooldownUntil) return false;
  const approach = spec.approach ? spec.approach.clone() : null;
  if (approach) approach.y = activeMarker.position.y;
  const handle = spec.handle ? spec.handle.clone() : new THREE.Vector3(spec.x || 0, activeMarker.position.y + 1.08, spec.z || 0);
  activeDoorInteraction = {
    id: spec.id,
    label: spec.label || "door",
    startedAt: now,
    opened: false,
    gripped: false,
    initialPosition: activeMarker.position.clone(),
    approach,
    handle,
    open: spec.open,
    throughPosition: spec.throughPosition ? spec.throughPosition.clone() : null,
    failed: false,
    handContact: null,
    preferredHand: spec.preferredHand || "R",
    ikSolved: false,
    ikGripLocked: false,
    trainingAssist: !!spec.trainingAssist,
    trainingAssistGrip: false,
  };
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  activeMarker.userData.doorInteraction = activeDoorInteraction.id;
  faceActiveAvatarToward(handle.x, handle.z, 0);
  clearDoorReachRig();
  if (ACTIVE_AVATAR_USE_PROCEDURAL_DOOR_ARM) setDoorReachArmHidden(true);
  setActiveAvatarAction("door_open_reach");
  show(`${activeAvatarDisplayName()} reaches for the ${activeDoorInteraction.label} handle.`);
  recordMovementLearningAttempt({
    skill: "door_open_reach",
    phase: "reach_started",
    target: activeDoorInteraction.label,
    handle: { x: Number(handle.x.toFixed(3)), y: Number(handle.y.toFixed(3)), z: Number(handle.z.toFixed(3)) },
  });
  return true;
}

function updateActiveDoorInteraction(t, dt = 1 / 60) {
  if (!activeDoorInteraction || !activeMarker) return false;
  const age = t - activeDoorInteraction.startedAt;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  activeMarker.userData.doorInteraction = activeDoorInteraction.id;

  if (activeDoorInteraction.approach) {
    const k = smoothStep01(age / 0.34);
    activeMarker.position.lerpVectors(activeDoorInteraction.initialPosition, activeDoorInteraction.approach, k);
  }
  faceActiveAvatarToward(activeDoorInteraction.handle.x, activeDoorInteraction.handle.z, dt);
  updateDoorReachRig(age);
  const handContact = activeAvatarClosestHandContact(activeDoorInteraction.handle, activeDoorInteraction.preferredHand);
  if (handContact) {
    activeDoorInteraction.handContact = {
      node: handContact.node,
      distance: Number(handContact.distance.toFixed(3)),
      x: Number(handContact.position.x.toFixed(3)),
      y: Number(handContact.position.y.toFixed(3)),
      z: Number(handContact.position.z.toFixed(3)),
    };
  }
  const effectiveHandDistance = activeDoorInteraction.handContact?.distance ?? handContact?.distance ?? Infinity;
  const handTouchesHandle = activeDoorInteraction.ikGripLocked || effectiveHandDistance <= ACTIVE_AVATAR_DOOR_HAND_TOUCH_METERS;

  if (!activeDoorInteraction.gripped && age >= 0.82 && handTouchesHandle) {
    activeDoorInteraction.gripped = true;
    recordMovementLearningAttempt({
      skill: "door_open_reach",
      phase: "handle_gripped",
      target: activeDoorInteraction.label,
      handContact: activeDoorInteraction.handContact,
    });
  }

  if (!activeDoorInteraction.gripped && activeDoorInteraction.trainingAssist && age >= 1.05) {
    activeDoorInteraction.gripped = true;
    activeDoorInteraction.trainingAssistGrip = true;
    recordMovementLearningAttempt({
      skill: "door_open_reach",
      phase: "training_assist_grip",
      target: activeDoorInteraction.label,
      handContact: activeDoorInteraction.handContact,
    });
  }

  if (!activeDoorInteraction.gripped && !activeDoorInteraction.failed && age >= 1.65) {
    activeDoorInteraction.failed = true;
    show(`${activeAvatarDisplayName()} missed the ${activeDoorInteraction.label} handle. Door stays closed for IK retraining.`);
    recordMovementLearningAttempt({
      skill: "door_open_reach",
      phase: "handle_missed_no_contact",
      target: activeDoorInteraction.label,
      requiredMeters: ACTIVE_AVATAR_DOOR_HAND_TOUCH_METERS,
      handContact: activeDoorInteraction.handContact,
    });
  }

  if (
    !activeDoorInteraction.opened &&
    activeDoorInteraction.gripped &&
    (handTouchesHandle || activeDoorInteraction.trainingAssistGrip) &&
    age >= ACTIVE_AVATAR_DOOR_REACH_SECONDS
  ) {
    activeDoorInteraction.opened = true;
    activeDoorInteraction.open();
    show(`${activeAvatarDisplayName()} pulls the ${activeDoorInteraction.label} open.`);
    recordMovementLearningAttempt({
      skill: "door_open_reach",
      phase: activeDoorInteraction.trainingAssistGrip ? "door_opened_after_training_assist" : "door_opened_after_grip",
      target: activeDoorInteraction.label,
      handContact: activeDoorInteraction.handContact,
    });
  }

  const finishSeconds = activeDoorInteraction.trainingAssist ? 1.18 : ACTIVE_AVATAR_DOOR_FINISH_SECONDS;
  if (age >= (activeDoorInteraction.failed ? 1.75 : finishSeconds)) {
    const failed = !!activeDoorInteraction.failed;
    recordMovementLearningAttempt({
      skill: "door_open_reach",
      phase: failed ? "reach_finished_failed" : "reach_finished",
      target: activeDoorInteraction.label,
      opened: !!activeDoorInteraction.opened,
      handContact: activeDoorInteraction.handContact,
    });
    if (failed) {
      activeDoorFailureCooldowns.set(activeDoorCooldownId(activeDoorInteraction.id), t + 12);
      activeMarker.userData.roamIndex += 1;
    } else if (activeDoorInteraction.throughPosition) {
      const through = activeDoorInteraction.throughPosition;
      activeMarker.userData.autonomousRoamTarget = {
        id: `${activeDoorInteraction.label} inside threshold`,
        reason: "door_opened_continue_inside",
        x: through.x,
        y: through.y,
        z: through.z,
        pickedAt: t,
        attempt: 0,
      };
      activeMarker.userData.autonomousGaitMode = "walk";
      activeMarker.userData.roamPolicy = "door_follow_through_after_open";
      recordMovementLearningAttempt({
        skill: "door_open_reach",
        phase: "follow_through_target_set",
        target: activeDoorInteraction.label,
        throughPosition: {
          x: Number(through.x.toFixed(3)),
          y: Number(through.y.toFixed(3)),
          z: Number(through.z.toFixed(3)),
        },
      });
    }
    activeMarker.userData.waitUntil = t + (failed ? 1.1 : 0.25);
    activeMarker.userData.doorInteraction = null;
    activeDoorInteraction = null;
    clearDoorReachRig();
    setActiveAvatarAction("idle");
    return false;
  }
  return true;
}

function startActiveAvatarPostureTest(name) {
  if (!activeMarker) return false;
  const spec = ACTIVE_AVATAR_POSTURE_TESTS[name];
  if (!spec) return false;
  if (activeAvatarIsKiraLike() && (name === "sleep_bed" || name === "lie_bed")) return startActiveAvatarKiraSleepPractice();
  activePostureInteraction = {
    id: name,
    label: spec.label,
    action: spec.action,
    startedAt: clock.elapsedTime,
    seconds: spec.seconds,
    startPosition: activeMarker.position.clone(),
    targetPosition: spec.position.clone(),
    standPosition: spec.standPosition ? spec.standPosition.clone() : null,
    yaw: spec.yaw,
    posture: spec.posture,
    rootTiltX: spec.rootTiltX || 0,
    rootYOffset: spec.rootYOffset || 0,
    sleepCover: !!spec.sleepCover,
  };
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  activeMarker.userData.waitUntil = clock.elapsedTime + spec.seconds + 0.2;
  activeMarker.userData.postureState = {
    id: name,
    posture: spec.posture,
    rootTiltX: spec.rootTiltX || 0,
    rootYOffset: spec.rootYOffset || 0,
  };
  if (ladybugBedSleepCover) ladybugBedSleepCover.visible = !!spec.sleepCover;
  setActiveAvatarAction(spec.action);
  const postureLabel = spec.posture === "lie" || spec.posture === "sleep" ? "lie-down" : "sit";
  const displayName = activeMarker?.userData?.label || "Active avatar";
  show(`${displayName} practices ${spec.label} ${postureLabel} control.`);
  recordMovementLearningAttempt({
    skill: name,
    phase: "started",
    target: spec.label,
  });
  return true;
}

function updateActivePostureInteraction(t) {
  if (!activePostureInteraction || !activeMarker) return false;
  const age = t - activePostureInteraction.startedAt;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  const settle = smoothStep01(age / 0.55);
  activeMarker.position.lerpVectors(activePostureInteraction.startPosition, activePostureInteraction.targetPosition, settle);
  activeMarker.rotation.y = activePostureInteraction.yaw;
  activeMarker.userData.postureState = {
    id: activePostureInteraction.id,
    posture: activePostureInteraction.posture,
    rootTiltX: activePostureInteraction.rootTiltX,
    rootYOffset: activePostureInteraction.rootYOffset,
  };
  if (ladybugBedSleepCover && activePostureInteraction.sleepCover) ladybugBedSleepCover.visible = true;
  if (age >= activePostureInteraction.seconds) {
    const finishedPosition = activeMarker.position.clone();
    recordMovementLearningAttempt({
      skill: activePostureInteraction.id,
      phase: "finished",
      target: activePostureInteraction.label,
      position: {
        x: Number(finishedPosition.x.toFixed(3)),
        y: Number(finishedPosition.y.toFixed(3)),
        z: Number(finishedPosition.z.toFixed(3)),
      },
      durationSeconds: Number(age.toFixed(2)),
    });
    if (activePostureInteraction.standPosition) activeMarker.position.copy(activePostureInteraction.standPosition);
    if (ladybugBedSleepCover && activePostureInteraction.sleepCover) ladybugBedSleepCover.visible = false;
    activeMarker.userData.postureState = null;
    activeMarker.userData.waitUntil = t + 0.65;
    activePostureInteraction = null;
    setActiveAvatarAction("idle");
    return false;
  }
  return true;
}

function frontDoorInteractionSpec(y, nextX = 0, nextZ = 7.95, id = "front_door") {
  const currentZ = activeMarker?.position.z ?? nextZ;
  const currentX = activeMarker?.position.x ?? nextX;
  const fromOutside = currentZ > 7.95 || nextZ > 7.95;
  const handleX = currentX < 0 ? -0.16 : 0.16;
  return {
    id,
    label: "front door",
    handle: new THREE.Vector3(handleX, 1.06, fromOutside ? 8.11 : 7.84),
    approach: new THREE.Vector3(handleX * 1.45, y, fromOutside ? 8.36 : 7.42),
    throughPosition: new THREE.Vector3(handleX * 0.7, y, fromOutside ? 7.18 : 8.72),
    preferredHand: handleX < 0 ? "L" : "R",
    open: () => setFrontDoorOpen(true),
  };
}

function backDoorInteractionSpec(y, nextZ = -7.75, id = "back_door") {
  const currentZ = activeMarker?.position.z ?? nextZ;
  const fromOutside = currentZ < -7.75 || nextZ < -7.75;
  return {
    id,
    label: "back door",
    handle: new THREE.Vector3(2.08, 1.04, fromOutside ? -7.82 : -7.56),
    approach: new THREE.Vector3(1.88, y, fromOutside ? -8.16 : -7.22),
    throughPosition: new THREE.Vector3(1.9, y, fromOutside ? -7.18 : -8.72),
    preferredHand: "R",
    open: () => setBackDoorOpen(true),
  };
}

function libraryDoorInteractionSpec(y, nextZ = 38.42, id = "library_door") {
  const currentZ = activeMarker?.position.z ?? nextZ;
  const fromOutside = currentZ < 38.42 || nextZ < 38.42;
  return {
    id,
    label: "public library door",
    handle: new THREE.Vector3(24.18, 1.05, fromOutside ? 38.28 : 38.55),
    approach: new THREE.Vector3(24.0, y, fromOutside ? 37.72 : 39.08),
    throughPosition: new THREE.Vector3(24.0, y, fromOutside ? 39.55 : 37.22),
    preferredHand: "R",
    open: () => setLibraryDoorOpen(true),
  };
}

function zWallInteriorDoorInteractionSpec(key, label, doorX, doorZ, width, floor = 1, roomSideSign = -1) {
  const currentX = activeMarker?.position.x ?? doorX;
  const fromRoom = roomSideSign < 0 ? currentX < doorX : currentX > doorX;
  const sideSign = fromRoom ? roomSideSign : -roomSideSign;
  const y = floorBase(floor);
  return {
    id: key,
    label,
    handle: new THREE.Vector3(doorX + sideSign * 0.08, y + 1.06, doorZ + width * 0.12),
    approach: new THREE.Vector3(doorX + sideSign * 0.74, y, doorZ + width * 0.08),
    preferredHand: roomSideSign < 0 ? "R" : "L",
    trainingAssist: activeAvatarIsKiraLike() && key === "empty upstairs guest room hinged door",
    open: () => setInteriorDoorOpen(key, true),
  };
}

function neighborHouseDoorInteractionSpec(y, nextX, nextZ, id = "neighbor_house_front_door") {
  const doorX = neighborDoorStatus.position.x;
  const doorZ = neighborDoorStatus.position.z;
  const currentZ = activeMarker?.position.z ?? nextZ;
  const fromOutside = currentZ > doorZ || nextZ > doorZ;
  return {
    id,
    label: "neighbor house front door",
    handle: new THREE.Vector3(doorX + 0.36, 1.05, fromOutside ? doorZ + 0.08 : doorZ - 0.22),
    approach: new THREE.Vector3(doorX + 0.18, y, fromOutside ? doorZ + 0.58 : doorZ - 0.82),
    preferredHand: "R",
    open: () => setNeighborHouseDoorOpen(true),
  };
}

function setLadybugDeskChairOffset(offsetX) {
  if (!ladybugDeskChairGroup) return;
  ladybugDeskChairGroup.position.x = offsetX;
}

function deskSequenceTarget(name) {
  const y = ACTIVE_AVATAR_SECOND_FLOOR_Y;
  const targets = {
    standOut: new THREE.Vector3(6.08, y, -4.35),
    sitOut: new THREE.Vector3(6.42, y, -4.35),
    sitIn: new THREE.Vector3(6.72, y, -4.35),
  };
  return targets[name]?.clone() || targets.standOut.clone();
}

function startActiveAvatarDeskComputerSequence() {
  if (!activeMarker) return false;
  activeFurnitureInteraction = {
    id: "desk_computer",
    label: "Ladybug computer desk",
    startedAt: clock.elapsedTime,
    stage: "",
    startPosition: activeMarker.position.clone(),
    yaw: -Math.PI / 2,
  };
  activePostureInteraction = null;
  activeDoorInteraction = null;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  activeMarker.userData.waitUntil = clock.elapsedTime + 7.6;
  activeMarker.userData.furnitureInteraction = activeFurnitureInteraction.id;
  setLadybugDeskChairOffset(0);
  setActiveAvatarAction("walk");
  show("Marinette practices chair scoot, sit, computer use, and stand.");
  recordMovementLearningAttempt({
    skill: "desk_computer",
    phase: "started",
    target: activeFurnitureInteraction.label,
  });
  return true;
}

function activeFurnitureStage(stage, action, message) {
  if (!activeFurnitureInteraction || activeFurnitureInteraction.stage === stage) return;
  activeFurnitureInteraction.stage = stage;
  if (action) setActiveAvatarAction(action);
  if (message) show(message);
  recordMovementLearningAttempt({
    skill: activeFurnitureInteraction.id,
    phase: stage,
    target: activeFurnitureInteraction.label,
  });
}

function updateActiveFurnitureInteraction(t) {
  if (!activeFurnitureInteraction || !activeMarker) return false;
  const age = t - activeFurnitureInteraction.startedAt;
  const standOut = deskSequenceTarget("standOut");
  const sitOut = deskSequenceTarget("sitOut");
  const sitIn = deskSequenceTarget("sitIn");
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  activeMarker.userData.furnitureInteraction = activeFurnitureInteraction.id;
  activeMarker.rotation.y = activeFurnitureInteraction.yaw;
  activeMarker.position.y = ACTIVE_AVATAR_SECOND_FLOOR_Y;

  if (age < 0.85) {
    activeFurnitureStage("approach_and_pull_chair_out", "walk", "Marinette pulls the desk chair out before sitting.");
    const k = smoothStep01(age / 0.85);
    activeMarker.position.lerpVectors(activeFurnitureInteraction.startPosition, standOut, k);
    setLadybugDeskChairOffset(THREE.MathUtils.lerp(0, -0.42, k));
  } else if (age < 1.85) {
    activeFurnitureStage("sit_on_chair", "sit", "Marinette sits on the pulled-out chair.");
    const k = smoothStep01((age - 0.85) / 1.0);
    activeMarker.position.lerpVectors(standOut, sitOut, k);
    setLadybugDeskChairOffset(-0.42);
    activeMarker.userData.postureState = {
      id: "desk_computer",
      posture: "sit",
      rootTiltX: 0,
      rootYOffset: -0.12,
    };
  } else if (age < 2.7) {
    activeFurnitureStage("scoot_chair_in", "sit", "Marinette scoots the chair in toward the computer.");
    const k = smoothStep01((age - 1.85) / 0.85);
    activeMarker.position.lerpVectors(sitOut, sitIn, k);
    setLadybugDeskChairOffset(THREE.MathUtils.lerp(-0.42, 0, k));
    activeMarker.userData.postureState = {
      id: "desk_computer",
      posture: "sit",
      rootTiltX: 0,
      rootYOffset: -0.12,
    };
  } else if (age < 5.55) {
    activeFurnitureStage("work_on_computer", "use_computer", "Marinette works at the computer from the chair.");
    activeMarker.position.copy(sitIn);
    setLadybugDeskChairOffset(0);
    activeMarker.userData.postureState = {
      id: "desk_computer",
      posture: "sit",
      rootTiltX: 0,
      rootYOffset: -0.12,
    };
  } else if (age < 6.45) {
    activeFurnitureStage("scoot_chair_out", "sit", "Marinette scoots the chair out before standing.");
    const k = smoothStep01((age - 5.55) / 0.9);
    activeMarker.position.lerpVectors(sitIn, sitOut, k);
    setLadybugDeskChairOffset(THREE.MathUtils.lerp(0, -0.42, k));
    activeMarker.userData.postureState = {
      id: "desk_computer",
      posture: "sit",
      rootTiltX: 0,
      rootYOffset: -0.12,
    };
  } else if (age < 7.2) {
    activeFurnitureStage("stand_from_chair", "idle", "Marinette stands after scooting the chair out.");
    const k = smoothStep01((age - 6.45) / 0.75);
    activeMarker.position.lerpVectors(sitOut, standOut, k);
    setLadybugDeskChairOffset(-0.42);
    activeMarker.userData.postureState = null;
  } else {
    recordMovementLearningAttempt({
      skill: activeFurnitureInteraction.id,
      phase: "finished",
      target: activeFurnitureInteraction.label,
      chairOffsetX: Number((ladybugDeskChairGroup?.position.x || 0).toFixed(3)),
    });
    activeMarker.userData.furnitureInteraction = null;
    activeMarker.userData.postureState = null;
    activeMarker.userData.waitUntil = t + 0.6;
    activeFurnitureInteraction = null;
    setActiveAvatarAction("idle");
    return false;
  }
  return true;
}

const ACTIVE_AVATAR_SELF_TEST_STEPS = [
  {
    id: "sit_couch",
    label: "sit on the living room couch",
    skill: "sit_couch",
    timeoutSeconds: 7.0,
    successPhases: ["finished"],
    setup: () => {
      activeMarker.userData.roamZone = "downstairs";
      window.kiraHomeWorldDebug.setActiveAvatarPosition({ x: -4.05, y: ACTIVE_AVATAR_GROUND_Y, z: 1.82, roamZone: "downstairs" });
    },
    start: () => startActiveAvatarPostureTest("sit_couch"),
  },
  {
    id: "front_door_reach",
    label: "reach, grip, and open the front door",
    skill: "door_open_reach",
    timeoutSeconds: 4.6,
    successPhases: ["door_opened_after_grip"],
    failurePhases: ["handle_missed_no_contact", "reach_finished_failed"],
    setup: () => {
      setFrontDoorOpen(false);
      activeDoorFailureCooldowns.delete("front_door");
      activeMarker.userData.roamZone = "downstairs";
      window.kiraHomeWorldDebug.setActiveAvatarPosition({ x: 0.18, y: ACTIVE_AVATAR_GROUND_Y, z: 7.22, roamZone: "downstairs" });
    },
    start: () => startActiveAvatarDoorInteraction(frontDoorInteractionSpec(ACTIVE_AVATAR_GROUND_Y, 0.18, 7.22, "front_door_self_test")),
  },
  {
    id: "stairs_step",
    label: "climb the main stairs one tread at a time",
    skill: "stairs_step",
    timeoutSeconds: 10.5,
    successPhases: ["route_finished"],
    setup: () => {
      activeMarker.userData.roamZone = "downstairs";
      window.kiraHomeWorldDebug.setActiveAvatarPosition({ x: 1.9, y: ACTIVE_AVATAR_GROUND_Y, z: 2.95, roamZone: "downstairs" });
    },
    start: () => startActiveAvatarStairPracticeRoute(false),
  },
  {
    id: "sleep_bed",
    label: "lie in Marinette's temporary bed and pull the blanket up",
    skill: "sleep_bed",
    timeoutSeconds: 7.4,
    successPhases: ["finished"],
    setup: () => {
      activeMarker.userData.roamZone = "upstairs";
      window.kiraHomeWorldDebug.setActiveAvatarPosition({ x: 6.62, y: ACTIVE_AVATAR_SECOND_FLOOR_Y, z: -4.16, roamZone: "upstairs" });
    },
    start: () => startActiveAvatarPostureTest("sleep_bed"),
  },
  {
    id: "desk_computer",
    label: "pull the chair out, sit, scoot in, use the computer, and stand",
    skill: "desk_computer",
    timeoutSeconds: 9.0,
    successPhases: ["finished"],
    setup: () => {
      activeMarker.userData.roamZone = "upstairs";
      window.kiraHomeWorldDebug.setActiveAvatarPosition({ x: 6.08, y: ACTIVE_AVATAR_SECOND_FLOOR_Y, z: -4.35, roamZone: "upstairs" });
    },
    start: () => startActiveAvatarDeskComputerSequence(),
  },
  {
    id: "back_door_reach",
    label: "reach, grip, and open the back door",
    skill: "door_open_reach",
    timeoutSeconds: 4.6,
    successPhases: ["door_opened_after_grip"],
    failurePhases: ["handle_missed_no_contact", "reach_finished_failed"],
    setup: () => {
      setBackDoorOpen(false);
      activeDoorFailureCooldowns.delete("back_door");
      activeMarker.userData.roamZone = "downstairs";
      window.kiraHomeWorldDebug.setActiveAvatarPosition({ x: 1.88, y: ACTIVE_AVATAR_GROUND_Y, z: -7.22, roamZone: "downstairs" });
    },
    start: () => startActiveAvatarDoorInteraction(backDoorInteractionSpec(ACTIVE_AVATAR_GROUND_Y, -7.22, "back_door_self_test")),
  },
];

function activeAvatarSelfTestAttempts(step) {
  const attempts = window.kiraMovementLearning?.memory?.attempts || [];
  const startedMs = Date.parse(activeAvatarSelfTest?.stepStartedAtIso || "");
  return attempts.filter((attempt) => {
    if (!attempt || attempt.skill !== step.skill) return false;
    const atMs = Date.parse(attempt.at || "");
    return Number.isFinite(atMs) && (!Number.isFinite(startedMs) || atMs >= startedMs);
  });
}

function scoreActiveAvatarSelfTestStep(step, timedOut = false) {
  const attempts = activeAvatarSelfTestAttempts(step);
  const phases = new Set(attempts.map((attempt) => attempt.phase));
  const passed = !timedOut && step.successPhases.some((phase) => phases.has(phase));
  const failed = timedOut || (step.failurePhases || []).some((phase) => phases.has(phase));
  let reward = passed ? 1.0 : failed ? 0.0 : 0.35;
  if (step.skill === "door_open_reach" && !passed && phases.has("reach_started")) reward = 0.2;
  const result = {
    id: step.id,
    label: step.label,
    testedSkill: step.skill,
    passed,
    reward,
    timedOut,
    phases: Array.from(phases).sort(),
  };
  recordMovementLearningAttempt({
    skill: "body_self_test",
    phase: "step_scored",
    target: step.label,
    testedSkill: step.skill,
    passed,
    reward,
    timedOut,
    observedPhases: result.phases,
  });
  return result;
}

function finishActiveAvatarSelfTestStep(t, timedOut = false) {
  if (!activeAvatarSelfTest?.currentStep) return;
  const step = activeAvatarSelfTest.currentStep;
  if (timedOut) {
    activePostureInteraction = null;
    activeDoorInteraction = null;
    activeFurnitureInteraction = null;
    clearDoorReachRig();
    if (activeMarker) {
      activeMarker.userData.practiceRoute = null;
      activeMarker.userData.stairTraversalActive = false;
      activeMarker.userData.postureState = null;
      activeMarker.userData.doorInteraction = null;
      activeMarker.userData.furnitureInteraction = null;
      activeMarker.userData.waitUntil = t + 0.5;
      setActiveAvatarAction("idle");
    }
  }
  activeAvatarSelfTest.results.push(scoreActiveAvatarSelfTestStep(step, timedOut));
  activeAvatarSelfTest.currentStep = null;
  activeAvatarSelfTest.index += 1;
  activeAvatarSelfTest.waitUntil = t + 0.85;
}

function finishActiveAvatarSelfTest(t) {
  if (!activeAvatarSelfTest) return false;
  const results = activeAvatarSelfTest.results || [];
  const totalReward = results.reduce((sum, result) => sum + (result.reward || 0), 0);
  const averageReward = results.length ? totalReward / results.length : 0;
  const summary = {
    stepCount: results.length,
    passed: results.filter((result) => result.passed).length,
    failed: results.filter((result) => !result.passed).length,
    averageReward: Number(averageReward.toFixed(3)),
    results,
  };
  recordMovementLearningAttempt({
    skill: "body_self_test",
    phase: "battery_finished",
    target: "foundation skeleton avatar-builder validation",
    averageReward: summary.averageReward,
    passed: summary.passed,
    failed: summary.failed,
  });
  if (window.kiraMovementLearning?.memory) {
    window.kiraMovementLearning.memory.selfPractice = window.kiraMovementLearning.memory.selfPractice || [];
    window.kiraMovementLearning.memory.selfPractice.push({
      at: new Date().toISOString(),
      version: "2026-07-04.self-body-test-v1",
      summary,
    });
    if (window.kiraMovementLearning.memory.selfPractice.length > 30) window.kiraMovementLearning.memory.selfPractice.shift();
    window.kiraMovementLearning.recordAttempt?.({
      skill: "body_self_test",
      phase: "self_practice_saved",
      target: "avatar builder movement memory",
      averageReward: summary.averageReward,
      passed: summary.passed,
      failed: summary.failed,
    });
  }
  if (activeMarker) {
    activeMarker.userData.selfTestState = { running: false, summary };
    activeMarker.userData.roamZone = "upstairs";
    activeMarker.userData.roamIndex = 5;
    activeMarker.userData.waitUntil = Number.POSITIVE_INFINITY;
    window.kiraHomeWorldDebug.setActiveAvatarPosition({
      x: 6.34,
      y: ACTIVE_AVATAR_SECOND_FLOOR_Y,
      z: -4.12,
      roamZone: "upstairs",
      roamIndex: 5,
      waitSeconds: Number.POSITIVE_INFINITY,
    });
    activeMarker.userData.waitUntil = Number.POSITIVE_INFINITY;
  }
  show(`Marinette self-test finished: ${summary.passed}/${summary.stepCount} skills passed, reward ${summary.averageReward}. She is waiting at the design workbench instead of pacing the living room.`);
  activeAvatarSelfTest = null;
  return true;
}

function startActiveAvatarSelfTest(options = {}) {
  if (!activeMarker || activeAvatarSelfTest) return false;
  activePostureInteraction = null;
  activeDoorInteraction = null;
  activeFurnitureInteraction = null;
  clearDoorReachRig();
  activeAvatarSelfTest = {
    version: "2026-07-04.self-body-test-v1",
    auto: !!options.auto,
    index: 0,
    currentStep: null,
    startedAt: clock.elapsedTime,
    waitUntil: clock.elapsedTime,
    results: [],
    stepStartedAtIso: "",
  };
  activeMarker.userData.selfTestState = {
    running: true,
    version: activeAvatarSelfTest.version,
    auto: activeAvatarSelfTest.auto,
  };
  recordMovementLearningAttempt({
    skill: "body_self_test",
    phase: "battery_started",
    target: "foundation skeleton avatar-builder validation",
    auto: activeAvatarSelfTest.auto,
    steps: ACTIVE_AVATAR_SELF_TEST_STEPS.map((step) => step.id),
  });
  show("Marinette starts a body self-test for the avatar builder.");
  return true;
}

function maybeAutoStartActiveAvatarSelfTest(t) {
  if (activeAvatarSelfTestAutoStarted || activeAvatarSelfTest || !activeMarker?.userData?.roamReady) return false;
  if (!ACTIVE_AVATAR_AUTO_SELF_TEST) return false;
  if (t < 3.0) return false;
  activeAvatarSelfTestAutoStarted = true;
  return startActiveAvatarSelfTest({ auto: true });
}

function updateActiveAvatarSelfTest(t) {
  if (!activeAvatarSelfTest || !activeMarker) return false;
  if (activeMarker.userData.practiceRoute) {
    if (activeAvatarSelfTest.currentStep && t - activeAvatarSelfTest.stepStartedAt > activeAvatarSelfTest.currentStep.timeoutSeconds) {
      finishActiveAvatarSelfTestStep(t, true);
      return true;
    }
    return false;
  }
  if (activePostureInteraction || activeDoorInteraction || activeFurnitureInteraction) {
    if (activeAvatarSelfTest.currentStep && t - activeAvatarSelfTest.stepStartedAt > activeAvatarSelfTest.currentStep.timeoutSeconds) {
      finishActiveAvatarSelfTestStep(t, true);
    }
    return true;
  }
  if (activeAvatarSelfTest.currentStep) {
    finishActiveAvatarSelfTestStep(t, false);
    return true;
  }
  if (t < activeAvatarSelfTest.waitUntil) return true;
  if (activeAvatarSelfTest.index >= ACTIVE_AVATAR_SELF_TEST_STEPS.length) return finishActiveAvatarSelfTest(t);
  const step = ACTIVE_AVATAR_SELF_TEST_STEPS[activeAvatarSelfTest.index];
  step.setup();
  activeAvatarSelfTest.currentStep = step;
  activeAvatarSelfTest.stepStartedAt = t;
  activeAvatarSelfTest.stepStartedAtIso = new Date().toISOString();
  activeMarker.userData.selfTestState = {
    running: true,
    step: step.id,
    label: step.label,
    index: activeAvatarSelfTest.index + 1,
    total: ACTIVE_AVATAR_SELF_TEST_STEPS.length,
  };
  recordMovementLearningAttempt({
    skill: "body_self_test",
    phase: "step_started",
    target: step.label,
    testedSkill: step.skill,
  });
  const started = step.start();
  if (!started) finishActiveAvatarSelfTestStep(t, true);
  return true;
}

function openDoorForActiveAvatar(nextX, nextZ, y) {
  const floor = y > 1.8 ? 1 : 0;
  const allowBathroomPractice = !!activeMarker?.userData?.allowBathroomPractice;
  if (tryEnterHomeTardisForActiveAvatar(nextX, nextZ, y)) return true;
  if (floor === 0 && !frontDoorOpen && Math.hypot(nextX - 0, nextZ - 7.95) < 1.55) {
    return startActiveAvatarDoorInteraction(frontDoorInteractionSpec(y, nextX, nextZ));
  }
  if (floor === 0 && !backDoorOpen && Math.hypot(nextX - 1.9, nextZ + 7.75) < 1.55) {
    return startActiveAvatarDoorInteraction(backDoorInteractionSpec(y, nextZ));
  }
  if (floor === 0 && !libraryDoorOpen && Math.hypot(nextX - 24.0, nextZ - 38.42) < 1.55) {
    return startActiveAvatarDoorInteraction(libraryDoorInteractionSpec(y, nextZ));
  }
  if (
    floor === 0 &&
    neighborDoorStatus.initialized &&
    !neighborHouseDoorOpen &&
    Math.hypot(nextX - neighborDoorStatus.position.x, nextZ - neighborDoorStatus.position.z) < 1.55
  ) {
    return startActiveAvatarDoorInteraction(neighborHouseDoorInteractionSpec(y, nextX, nextZ));
  }
  if (allowBathroomPractice && floor === 1 && !ladybugBathDoorLocked && !ladybugBathDoorOpen && Math.hypot(nextX - 5.65, nextZ + 2.78) < 1.35) {
    return startActiveAvatarDoorInteraction({
      id: "ladybug_bathroom_door",
      label: "bathroom door",
      handle: new THREE.Vector3(5.96, floorBase(1) + 1.05, -2.70),
      approach: new THREE.Vector3(5.18, y, -2.32),
      open: () => {
        ladybugBathDoorOpen = true;
        setBathroomDoorOpen(ladybugBathDoorGroup, true);
      },
    });
  }
  if (allowBathroomPractice && floor === 1 && !lisaBathDoorLocked && !lisaBathDoorOpen && Math.hypot(nextX - 5.65, nextZ - 2.78) < 1.35) {
    return startActiveAvatarDoorInteraction({
      id: "lisa_bathroom_door",
      label: "bathroom door",
      handle: new THREE.Vector3(5.96, floorBase(1) + 1.05, 2.86),
      approach: new THREE.Vector3(5.18, y, 2.34),
      open: () => {
        lisaBathDoorOpen = true;
        setBathroomDoorOpen(lisaBathDoorGroup, true);
      },
    });
  }
  if (floor === 1) {
    const upstairsInteriorDoors = [
      { key: "empty upstairs guest room hinged door", label: "empty upstairs guest room door", x: -2.25, z: 5.25, width: 1.28, roomSideSign: -1 },
      { key: "peter parker temporary room hinged door", label: "Peter Parker temporary room door", x: -2.25, z: 0.05, width: 1.18, roomSideSign: -1 },
      { key: "gwen stacy temporary room hinged door", label: "Gwen Stacy temporary room door", x: -2.25, z: -5.25, width: 1.28, roomSideSign: -1 },
      { key: "lisa bedroom hinged door", label: "Lisa bedroom door", x: 3.25, z: 5.25, width: 1.28, roomSideSign: 1 },
      { key: "marinette temporary room hinged door", label: "Marinette temporary room door", x: 3.25, z: -5.25, width: 1.28, roomSideSign: 1 },
    ];
    for (const door of upstairsInteriorDoors) {
      if (interiorDoorOpen.get(door.key)) continue;
      if (Math.hypot(nextX - door.x, nextZ - door.z) < 1.22) {
        return startActiveAvatarDoorInteraction(zWallInteriorDoorInteractionSpec(
          door.key,
          door.label,
          door.x,
          door.z,
          door.width,
          floor,
          door.roomSideSign,
        ));
      }
    }
  }
  for (const [key, leaf] of stripMallDoorLeaves) {
    if (stripMallDoorOpen.get(key)) continue;
    const x = leaf.position.x + 0.5;
    const z = leaf.position.z;
    if (Math.hypot(nextX - x, nextZ - z) < 1.35) {
      return startActiveAvatarDoorInteraction({
        id: `strip_mall_${key}_door`,
        label: `${key} shop door`,
        handle: new THREE.Vector3(x + 0.35, 1.08, z - 0.08),
        approach: new THREE.Vector3(x + 0.12, y, z - 0.78),
        throughPosition: new THREE.Vector3(x, y, z + 1.85),
        open: () => toggleStripMallDoor(key, key),
      });
    }
  }
  return false;
}

function seededRandom(seed) {
  let value = seed >>> 0;
  return () => {
    value = (value * 1664525 + 1013904223) >>> 0;
    return value / 4294967296;
  };
}

function createGrassBladeGeometry() {
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array([
    -0.012, 0, 0,
    0.012, 0, 0,
    -0.01, 0.055, 0.004,
    0.01, 0.055, 0.004,
    0, 0.12, 0.018,
  ]);
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setIndex([0, 1, 2, 1, 3, 2, 2, 3, 4]);
  geometry.computeVertexNormals();
  return geometry;
}

function isInsideAvoidArea(x, z, area) {
  let dx = x - area.x;
  let dz = z - area.z;
  if (area.yaw) {
    const c = Math.cos(-area.yaw);
    const s = Math.sin(-area.yaw);
    const rx = dx * c - dz * s;
    const rz = dx * s + dz * c;
    dx = rx;
    dz = rz;
  }
  return Math.abs(dx) < area.sx / 2 && Math.abs(dz) < area.sz / 2;
}

function addGrassBladeField({ name, x, z, width, depth, count, y = 0.035, seed = 1, avoid = [] }) {
  const geometry = createGrassBladeGeometry();
  const material = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.86,
    side: THREE.DoubleSide,
    vertexColors: true,
    emissive: 0x102900,
    emissiveIntensity: 0.08,
  });
  const mesh = new THREE.InstancedMesh(geometry, material, count);
  mesh.name = name;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.frustumCulled = false;

  const rand = seededRandom(seed);
  const dummy = new THREE.Object3D();
  const color = new THREE.Color();
  let placed = 0;
  let attempts = 0;
  while (placed < count && attempts < count * 10) {
    attempts += 1;
    const px = x + (rand() - 0.5) * width;
    const pz = z + (rand() - 0.5) * depth;
    if (avoid.some((area) => isInsideAvoidArea(px, pz, area))) continue;
    dummy.position.set(px, y, pz);
    dummy.rotation.set((rand() - 0.5) * 0.24, rand() * Math.PI * 2, (rand() - 0.5) * 0.18);
    const bladeScale = 0.55 + rand() * 0.85;
    dummy.scale.set(0.75 + rand() * 0.8, bladeScale, 0.75 + rand() * 0.8);
    dummy.updateMatrix();
    mesh.setMatrixAt(placed, dummy.matrix);
    color.setHSL(0.25 + rand() * 0.07, 0.42 + rand() * 0.18, 0.28 + rand() * 0.18);
    mesh.setColorAt(placed, color);
    placed += 1;
  }
  mesh.count = placed;
  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  scene.add(mesh);
  return mesh;
}

function addBed(name, x, z, width, depth, floor, blanketMaterial = materials.blanketBlue, facing = "back") {
  const y = floorBase(floor);
  const headSign = facing === "front" ? 1 : -1;
  const footSign = -headSign;
  addBox(`${name} bed frame`, x, y + 0.25, z, width + 0.25, 0.32, depth + 0.25, materials.wood, true, floor);
  addBox(`${name} mattress`, x, y + 0.48, z, width, 0.24, depth, materials.mattress, false);
  addSoftPillow(`${name} soft duvet`, x, y + 0.64, z + footSign * depth * 0.1, blanketMaterial, 0, width * 0.55, 0.09, depth * 0.34);
  addBox(`${name} headboard`, x, y + 0.9, z + headSign * (depth * 0.5 + 0.08), width + 0.25, 1.0, 0.18, materials.wood, false);
  addSoftPillow(`${name} pillow left rounded`, x - width * 0.22, y + 0.75, z + headSign * depth * 0.34, materials.fixture, 0, width * 0.22, 0.11, depth * 0.11);
  addSoftPillow(`${name} pillow right rounded`, x + width * 0.22, y + 0.75, z + headSign * depth * 0.34, materials.fixture, 0, width * 0.22, 0.11, depth * 0.11);
  if (name === "ladybug guest full" || name === "marinette temporary full bed") {
    addBox(`${name} pillow front edge`, x, y + 0.78, z + headSign * depth * 0.25, width * 0.82, 0.06, depth * 0.05, materials.fixture, false);
    ladybugBedSleepCover = addSoftPillow(`${name} pulled sleep blanket`, x, y + 0.86, z + footSign * depth * 0.08, blanketMaterial, 0, width * 0.5, 0.12, depth * 0.38);
    ladybugBedSleepCover.visible = false;
    ladybugBedSleepCover.userData.sleepCover = true;
  }
}

function addBedroomDetails(name, x, z, floor, accentMaterial = materials.blanketBlue) {
  const y = floorBase(floor);
  addFloorTile(`${name} woven bedside rug`, x, z, 2.55, 1.55, materials.rugBorder, y + 0.045);
  addBox(`${name} left nightstand`, x - 1.28, y + 0.34, z, 0.5, 0.62, 0.42, materials.livingWood, true, floor);
  addBox(`${name} right nightstand`, x + 1.28, y + 0.34, z, 0.5, 0.62, 0.42, materials.livingWood, true, floor);
  for (const side of [-1, 1]) {
    addBox(`${name} nightstand drawer ${side}`, x + side * 1.28, y + 0.42, z + 0.23, 0.42, 0.16, 0.035, materials.counter, false, floor);
    addCylinder(`${name} lamp base ${side}`, x + side * 1.28, y + 0.72, z - 0.06, 0.07, 0.08, materials.handle, false, floor);
    addCylinder(`${name} lamp shade ${side}`, x + side * 1.28, y + 0.94, z - 0.06, 0.16, 0.24, materials.lampShade, false, floor);
  }
  addBox(`${name} dresser body`, x - 1.72, y + 0.45, z + 1.72, 1.15, 0.78, 0.44, materials.warmCabinet, true, floor);
  for (const dz of [1.6, 1.78]) {
    addBox(`${name} dresser brass pull`, x - 1.72, y + 0.55, z + dz, 0.72, 0.045, 0.04, materials.handle, false, floor);
  }
  addBox(`${name} framed art`, x + 1.72, y + 1.45, z + 1.74, 0.9, 0.62, 0.04, accentMaterial, false, floor);
  addBox(`${name} art frame`, x + 1.72, y + 1.45, z + 1.765, 1.02, 0.72, 0.035, materials.windowFrame, false, floor);
}

function addDeskComputer(name, x, z, floor) {
  const y = floorBase(floor);
  addBox(`${name} desk`, x, y + 0.45, z, 1.45, 0.18, 0.58, materials.counter, false, floor);
  addBox(`${name} desk leg a`, x - 0.85, y + 0.22, z - 0.28, 0.08, 0.42, 0.08, materials.trim, false);
  addBox(`${name} desk leg b`, x + 0.85, y + 0.22, z - 0.28, 0.08, 0.42, 0.08, materials.trim, false);
  markTruthProp(addBox(`${name} monitor`, x, y + 0.92, z - 0.22, 0.7, 0.46, 0.06, materials.screen, false), "computer", `${name} monitor`, floor, ["use_computer", "read_book", "research"]);
  addBox(`${name} monitor stand`, x, y + 0.63, z - 0.28, 0.12, 0.28, 0.08, materials.trim, false);
  markTruthProp(addBox(`${name} keyboard`, x + 0.25, y + 0.58, z + 0.08, 0.48, 0.04, 0.18, materials.trim, false), "keyboard", `${name} keyboard`, floor, ["use_computer"]);
  markTruthProp(addBox(`${name} open notebook`, x - 0.38, y + 0.58, z + 0.08, 0.42, 0.035, 0.3, materials.paper, false), "notebook", `${name} open notebook`, floor, ["read_book", "sketch_design"]);
  markTruthProp(addBox(`${name} pencil`, x - 0.16, y + 0.62, z + 0.23, 0.04, 0.04, 0.5, materials.pencilWood, false), "pencil", `${name} pencil`, floor, ["sketch_design"]);
}

function addWallDeskComputer(name, x, z, floor) {
  const y = floorBase(floor);
  addBox(`${name} wall desk`, x, y + 0.45, z, 1.25, 0.18, 0.56, materials.counter, false, floor);
  addBox(`${name} wall desk left leg`, x - 0.48, y + 0.22, z + 0.18, 0.08, 0.42, 0.08, materials.trim, false, floor);
  addBox(`${name} wall desk right leg`, x + 0.48, y + 0.22, z + 0.18, 0.08, 0.42, 0.08, materials.trim, false, floor);
  markTruthProp(addBox(`${name} monitor`, x, y + 0.92, z - 0.25, 0.74, 0.48, 0.06, materials.screen, false, floor), "computer", `${name} monitor`, floor, ["use_computer", "read_book", "research"]);
  addBox(`${name} monitor stand`, x, y + 0.63, z - 0.18, 0.12, 0.28, 0.08, materials.trim, false, floor);
  markTruthProp(addBox(`${name} keyboard`, x + 0.14, y + 0.58, z + 0.08, 0.52, 0.04, 0.18, materials.trim, false, floor), "keyboard", `${name} keyboard`, floor, ["use_computer"]);
  markTruthProp(addBox(`${name} notebook reader`, x - 0.36, y + 0.58, z + 0.08, 0.36, 0.035, 0.28, materials.paper, false, floor), "notebook", `${name} notebook reader`, floor, ["read_book", "sketch_design"]);
  addBox(`${name} chair seat`, x, y + 0.34, z + 0.86, 0.62, 0.16, 0.56, materials.trim, false, floor);
  addBox(`${name} chair back`, x, y + 0.78, z + 1.14, 0.64, 0.72, 0.12, materials.trim, false, floor);
  addBox(`${name} chair left leg`, x - 0.24, y + 0.16, z + 0.68, 0.07, 0.32, 0.07, materials.trim, false, floor);
  addBox(`${name} chair right leg`, x + 0.24, y + 0.16, z + 0.68, 0.07, 0.32, 0.07, materials.trim, false, floor);
}

function addSideWallDeskComputer(name, x, z, floor, facing = "left") {
  const y = floorBase(floor);
  const dir = facing === "left" ? -1 : 1;
  const chairParts = [];
  const addChairPart = (...args) => {
    const mesh = addBox(...args);
    chairParts.push(mesh);
    return mesh;
  };
  addBox(`${name} side wall desk`, x, y + 0.45, z, 0.56, 0.18, 1.25, materials.counter, false, floor);
  addBox(`${name} side wall desk front leg`, x - dir * 0.18, y + 0.22, z - 0.48, 0.08, 0.42, 0.08, materials.trim, false, floor);
  addBox(`${name} side wall desk rear leg`, x - dir * 0.18, y + 0.22, z + 0.48, 0.08, 0.42, 0.08, materials.trim, false, floor);
  markTruthProp(addBox(`${name} monitor`, x + dir * 0.24, y + 0.92, z, 0.06, 0.48, 0.74, materials.screen, false, floor), "computer", `${name} monitor`, floor, ["use_computer", "read_book", "sketch_design"]);
  addBox(`${name} rear monitor arm`, x + dir * 0.31, y + 0.72, z, 0.08, 0.28, 0.12, materials.trim, false, floor);
  addBox(`${name} monitor base foot`, x + dir * 0.2, y + 0.58, z, 0.18, 0.045, 0.32, materials.trim, false, floor);
  markTruthProp(addBox(`${name} keyboard`, x - dir * 0.06, y + 0.58, z + 0.18, 0.18, 0.04, 0.52, materials.trim, false, floor), "keyboard", `${name} keyboard`, floor, ["use_computer"]);
  markTruthProp(addBox(`${name} notebook reader`, x - dir * 0.06, y + 0.58, z - 0.34, 0.28, 0.035, 0.36, materials.paper, false, floor), "notebook", `${name} notebook reader`, floor, ["read_book", "sketch_design"]);
  addChairPart(`${name} chair seat`, x - dir * 0.78, y + 0.34, z, 0.56, 0.16, 0.62, materials.trim, false, floor);
  addChairPart(`${name} chair back`, x - dir * 1.05, y + 0.78, z, 0.12, 0.72, 0.64, materials.trim, false, floor);
  addChairPart(`${name} chair front leg`, x - dir * 0.64, y + 0.16, z - 0.24, 0.07, 0.32, 0.07, materials.trim, false, floor);
  addChairPart(`${name} chair rear leg`, x - dir * 0.64, y + 0.16, z + 0.24, 0.07, 0.32, 0.07, materials.trim, false, floor);
  if (name === "ladybug temporary workbench" || name === "marinette temporary workbench") {
    ladybugDeskChairGroup = new THREE.Group();
    ladybugDeskChairGroup.name = "marinette temporary workbench movable chair";
    scene.add(ladybugDeskChairGroup);
    for (const part of chairParts) ladybugDeskChairGroup.attach(part);
  }
}

function addCloset(name, x, z, floor, facing = "front", accent = materials.blanketBlue) {
  const y = floorBase(floor);
  const depth = 0.5;
  const width = 1.55;
  addBox(`${name} closet back`, x, y + 1.05, z, width, 2.0, 0.08, materials.wood, false, floor);
  addBox(`${name} closet left side`, x - width * 0.5, y + 1.05, z + depth * 0.24, 0.08, 2.0, depth, materials.wood, false, floor);
  addBox(`${name} closet right side`, x + width * 0.5, y + 1.05, z + depth * 0.24, 0.08, 2.0, depth, materials.wood, false, floor);
  addBox(`${name} closet rail`, x, y + 1.52, z + depth * 0.18, width * 0.78, 0.05, 0.05, materials.handle, false, floor);
  addBox(`${name} folded clothes a`, x - 0.36, y + 0.72, z + depth * 0.2, 0.38, 0.1, 0.26, accent, false, floor);
  addBox(`${name} folded clothes b`, x + 0.24, y + 0.72, z + depth * 0.2, 0.38, 0.1, 0.26, materials.blanketPink, false, floor);
  addBox(`${name} hanging outfit blue`, x - 0.28, y + 1.1, z + depth * 0.2, 0.28, 0.8, 0.04, materials.blanketBlue, false, floor);
  addBox(`${name} hanging outfit pink`, x + 0.2, y + 1.1, z + depth * 0.2, 0.28, 0.8, 0.04, materials.blanketPink, false, floor);
  if (facing === "back") {
    for (const child of scene.children.filter((mesh) => mesh.name?.startsWith(`${name} closet`))) child.rotation.y = Math.PI;
  }
}

function addWallCloset(name, x, z, floor, width, facing = "front", accent = materials.blanketBlue) {
  const y = floorBase(floor);
  const sign = facing === "back" ? -1 : 1;
  addBox(`${name} built in closet back panel`, x, y + 1.0, z - sign * 0.02, width, 1.86, 0.06, materials.wood, false, floor);
  addBox(`${name} built in closet left jamb`, x - width * 0.5, y + 1.0, z + sign * 0.14, 0.08, 1.86, 0.38, materials.wood, false, floor);
  addBox(`${name} built in closet right jamb`, x + width * 0.5, y + 1.0, z + sign * 0.14, 0.08, 1.86, 0.38, materials.wood, false, floor);
  addBox(`${name} built in closet header`, x, y + 2.0, z, width, 0.16, 0.16, materials.wood, false, floor);
  addBox(`${name} closet rail`, x, y + 1.45, z + sign * 0.08, width * 0.82, 0.05, 0.05, materials.handle, false, floor);
  addBox(`${name} sliding door left`, x - width * 0.22, y + 1.0, z + sign * 0.18, width * 0.44, 1.7, 0.045, materials.wood, false, floor);
  addBox(`${name} sliding door right`, x + width * 0.22, y + 1.0, z + sign * 0.22, width * 0.44, 1.7, 0.045, materials.wood, false, floor);
  addBox(`${name} hanging outfit blue`, x - width * 0.22, y + 1.08, z - sign * 0.02, 0.28, 0.78, 0.04, materials.blanketBlue, false, floor);
  addBox(`${name} hanging outfit pink`, x + width * 0.18, y + 1.08, z - sign * 0.02, 0.28, 0.78, 0.04, accent, false, floor);
  addBox(`${name} lower shelf`, x, y + 0.42, z + sign * 0.08, width * 0.8, 0.08, 0.32, materials.counter, false, floor);
}

function addWalkInCloset(name, x, z, floor, accent = materials.blanketPink) {
  const y = floorBase(floor);
  addBox(`${name} rear wall closet panel`, x, y + 1.08, z, 1.65, 2.05, 0.08, materials.wood, false, floor);
  addBox(`${name} left closet return`, x - 0.82, y + 1.08, z + 0.42, 0.08, 2.05, 0.84, materials.wood, false, floor);
  addBox(`${name} right closet return`, x + 0.82, y + 1.08, z + 0.42, 0.08, 2.05, 0.84, materials.wood, false, floor);
  addBox(`${name} rail`, x, y + 1.5, z + 0.22, 1.35, 0.05, 0.05, materials.handle, false, floor);
  addBox(`${name} hanging blue outfit`, x - 0.32, y + 1.08, z + 0.24, 0.28, 0.78, 0.04, materials.blanketBlue, false, floor);
  addBox(`${name} hanging pink outfit`, x + 0.24, y + 1.08, z + 0.24, 0.28, 0.78, 0.04, accent, false, floor);
}

function addFrontWallWalkInCloset(name, x, z, floor, accent = materials.blanketBlue) {
  const y = floorBase(floor);
  const width = 2.55;
  addBox(`${name} outer wall closet back`, x, y + 1.08, z, width, 2.05, 0.08, materials.wood, false, floor);
  addBox(`${name} left return`, x - width * 0.5, y + 1.08, z - 0.55, 0.08, 2.05, 1.1, materials.wood, false, floor);
  addBox(`${name} right return`, x + width * 0.5, y + 1.08, z - 0.55, 0.08, 2.05, 1.1, materials.wood, false, floor);
  addBox(`${name} rail`, x, y + 1.5, z - 0.25, width * 0.8, 0.05, 0.05, materials.handle, false, floor);
  addBox(`${name} shelf`, x, y + 1.78, z - 0.28, width * 0.82, 0.08, 0.32, materials.counter, false, floor);
  addBox(`${name} folded clothes stack blue`, x - 0.45, y + 0.52, z - 0.4, 0.48, 0.18, 0.34, materials.blanketBlue, false, floor);
  addBox(`${name} folded clothes stack accent`, x + 0.35, y + 0.52, z - 0.4, 0.48, 0.18, 0.34, accent, false, floor);
  addBox(`${name} hanging garment placeholder blue`, x - 0.34, y + 1.08, z - 0.26, 0.28, 0.78, 0.04, materials.blanketBlue, false, floor);
  addBox(`${name} hanging garment placeholder accent`, x + 0.26, y + 1.08, z - 0.26, 0.28, 0.78, 0.04, accent, false, floor);
}

function addSideWallWalkInCloset(name, side, z, floor, accent = materials.blanketBlue) {
  const y = floorBase(floor);
  const wallX = side < 0 ? -7.5 : 7.5;
  const openX = side < 0 ? -6.35 : 6.35;
  const sign = side < 0 ? -1 : 1;
  addBox(`${name} back wall panel`, wallX, y + 1.08, z, 0.08, 2.05, 1.85, materials.wood, false, floor);
  addBox(`${name} front return`, (wallX + openX) * 0.5, y + 1.08, z + 0.92, 1.15, 2.05, 0.08, materials.wood, false, floor);
  addBox(`${name} rear return`, (wallX + openX) * 0.5, y + 1.08, z - 0.92, 1.15, 2.05, 0.08, materials.wood, false, floor);
  addBox(`${name} clothing rail`, wallX - sign * 0.08, y + 1.5, z, 0.05, 0.05, 1.42, materials.handle, false, floor);
  addBox(`${name} upper shelf`, wallX - sign * 0.18, y + 1.78, z, 0.34, 0.08, 1.5, materials.counter, false, floor);
  addBox(`${name} hanging clothes blue`, wallX - sign * 0.2, y + 1.08, z - 0.32, 0.04, 0.78, 0.28, materials.blanketBlue, false, floor);
  addBox(`${name} hanging clothes accent`, wallX - sign * 0.2, y + 1.08, z + 0.32, 0.04, 0.78, 0.28, accent, false, floor);
  addBox(`${name} walk-in footprint`, (wallX + openX) * 0.5, y + 0.01, z, 1.15, 0.02, 1.85, materials.secondFloor, false, floor);
}

function addCenterWalkInCloset(name, side, z, floor, accent = materials.blanketBlue) {
  const y = floorBase(floor);
  const roomSideWallX = side < 0 ? -2.2 : 2.35;
  const centerDividerX = 0.08;
  const closetCenterX = (roomSideWallX + centerDividerX) * 0.5;
  const width = Math.abs(roomSideWallX - centerDividerX) - 0.28;
  const depth = 1.78;
  addBox(`${name} back storage wall`, closetCenterX, y + 1.08, z + 0.86, width, 2.05, 0.08, materials.wood, true, floor);
  addBox(`${name} bedroom-side return`, roomSideWallX, y + 1.08, z + 0.02, 0.08, 2.05, depth, materials.wood, false, floor);
  addBox(`${name} center divider return`, centerDividerX, y + 1.08, z + 0.02, 0.08, 2.05, depth, materials.wood, true, floor);
  addBox(`${name} upper shelf`, closetCenterX, y + 1.78, z + 0.66, width * 0.82, 0.08, 0.32, materials.counter, false, floor);
  addBox(`${name} middle shelf`, closetCenterX, y + 1.18, z + 0.66, width * 0.72, 0.06, 0.28, materials.counter, false, floor);
  addBox(`${name} lower shoe shelf`, closetCenterX, y + 0.42, z + 0.64, width * 0.82, 0.08, 0.4, materials.counter, false, floor);
  addBox(`${name} hanging rail`, closetCenterX, y + 1.5, z + 0.66, width * 0.78, 0.05, 0.05, materials.handle, false, floor);
  for (const [i, dz] of [-0.2, 0.1, 0.4].entries()) {
    const mat = i % 2 ? accent : materials.blanketBlue;
    addBox(`${name} hanging garment ${i}`, closetCenterX - side * 0.08, y + 1.08, z + dz, 0.05, 0.78, 0.24, mat, false, floor);
  }
  addBox(`${name} walk-in floor`, closetCenterX, y + 0.01, z, width, 0.02, depth, materials.secondFloor, false, floor);
}

function addWallSketches() {
  const floor = 1;
  const y = 4.85;
  const x = 3.36;
  const board = markTruthProp(
    addBox("marinette bedroom fashion design pin board", x, y + 0.12, -6.92, 0.03, 1.05, 1.45, materials.designBoard, false, floor),
    "design_wall",
    "Marinette fashion design pin board",
    floor,
    ["sketch_design", "read_book"],
  );
  board.userData.roomRole = "temporary home workbench design wall";
  for (const [i, z] of [-7.32, -6.98, -6.62, -6.28].entries()) {
    const sketch = markTruthProp(
      addBox(`marinette fashion sketch ${i}`, x - 0.025, y + (i % 2) * 0.22, z, 0.025, 0.48, 0.28, materials.paper, false, floor),
      "design_wall",
      `Marinette pinned fashion sketch ${i}`,
      floor,
      ["sketch_design"],
    );
    sketch.userData.roomRole = "temporary home workbench design wall";
    addBox(`marinette sketch line ${i} bodice`, x - 0.05, y + (i % 2) * 0.22 + 0.07, z, 0.014, 0.025, 0.16, materials.sketchInk, false, floor);
    addBox(`marinette sketch line ${i} fabric swatch`, x - 0.052, y + (i % 2) * 0.22 - 0.09, z + 0.04, 0.014, 0.035, 0.1, i % 2 ? materials.blanketPink : materials.blanketBlue, false, floor);
  }
}

function addMarinetteDesignWorkbenchProps() {
  const floor = 1;
  const y = floorBase(floor);
  markTruthProp(addBox("marinette workbench closed sketchbook cover", 7.18, y + 0.60, -4.88, 0.34, 0.028, 0.44, materials.notebookCover, false, floor), "sketchbook", "Marinette sketchbook", floor, ["sketch_design", "read_book"]);
  markTruthProp(addBox("marinette workbench open sketch page", 7.12, y + 0.625, -4.88, 0.27, 0.018, 0.36, materials.paper, false, floor), "sketchbook", "open page in Marinette sketchbook", floor, ["sketch_design", "read_book"]);
  addBox("marinette workbench sketch seam line", 7.12, y + 0.64, -4.88, 0.035, 0.012, 0.34, materials.sketchInk, false, floor);
  markTruthProp(addBox("marinette workbench pencil", 7.34, y + 0.64, -4.72, 0.045, 0.035, 0.42, materials.pencilWood, false, floor), "pencil", "Marinette drawing pencil", floor, ["sketch_design"]);
  addBox("marinette workbench fabric swatch blue", 7.34, y + 0.62, -4.18, 0.24, 0.024, 0.28, materials.blanketBlue, false, floor);
  addBox("marinette workbench fabric swatch pink", 7.06, y + 0.625, -4.18, 0.24, 0.024, 0.28, materials.blanketPink, false, floor);
  addCylinder("marinette workbench pencil cup", 7.36, y + 0.66, -4.05, 0.08, 0.2, materials.counter, false, floor);
  for (const [i, dx] of [-0.035, 0, 0.035].entries()) {
    const pencil = addBox(`marinette workbench upright pencil ${i}`, 7.36 + dx, y + 0.8, -4.05, 0.018, 0.28, 0.018, materials.pencilWood, false, floor);
    pencil.rotation.z = i === 1 ? 0.08 : -0.06;
  }
}

function addMarinetteWardrobePrototypeProps() {
  const floor = 1;
  const y = floorBase(floor);
  const rackX = 4.04;
  const rackZ = -6.38;
  addBox("marinette prototype wardrobe rack left upright", rackX - 0.58, y + 1.02, rackZ, 0.05, 1.52, 0.05, materials.handle, false, floor);
  addBox("marinette prototype wardrobe rack right upright", rackX + 0.58, y + 1.02, rackZ, 0.05, 1.52, 0.05, materials.handle, false, floor);
  addBox("marinette prototype wardrobe rack rail", rackX, y + 1.72, rackZ, 1.25, 0.05, 0.05, materials.handle, false, floor);
  addBox("marinette prototype wardrobe lower shelf", rackX, y + 0.32, rackZ + 0.02, 1.34, 0.08, 0.34, materials.counter, false, floor);
  for (const [i, dx, mat] of [
    [0, -0.38, materials.blanketPink],
    [1, -0.12, materials.blanketBlue],
    [2, 0.16, materials.produceRed],
    [3, 0.42, materials.trim],
  ]) {
    addBox(`marinette prototype hanging garment hanger ${i}`, rackX + dx, y + 1.58, rackZ, 0.24, 0.035, 0.035, materials.handle, false, floor);
    markTruthProp(
      addBox(`marinette prototype wearable garment ${i}`, rackX + dx, y + 1.15, rackZ, 0.25, 0.78, 0.045, mat, false, floor),
      "wearable_clothing",
      `Marinette prototype wearable garment ${i}`,
      floor,
      ["change_clothes", "sketch_design"],
    );
  }
  markTruthProp(addBox("marinette folded civilian base underlayer", 3.72, y + 0.42, -6.12, 0.44, 0.11, 0.32, materials.fixture, false, floor), "wearable_clothing", "Marinette folded fitting underlayer", floor, ["change_clothes"]);
  markTruthProp(addBox("marinette folded red spotted suit cloth", 4.36, y + 0.42, -6.12, 0.44, 0.11, 0.32, materials.produceRed, false, floor), "wearable_clothing", "Marinette folded red suit cloth prototype", floor, ["change_clothes", "sketch_design"]);
  addBox("marinette black spot swatch a", 4.22, y + 0.49, -6.12, 0.08, 0.018, 0.08, materials.trim, false, floor);
  addBox("marinette black spot swatch b", 4.42, y + 0.49, -6.03, 0.08, 0.018, 0.08, materials.trim, false, floor);
  addBox("marinette black spot swatch c", 4.48, y + 0.49, -6.22, 0.08, 0.018, 0.08, materials.trim, false, floor);
}

function addMarinettePurseSet() {
  const floor = 1;
  const y = floorBase(floor);
  const x = 7.12;
  const z = -6.74;

  addBox("marinette nightstand", x, y + 0.34, z, 0.55, 0.68, 0.46, materials.wood, true, floor);
  addBox("marinette nightstand drawer", x, y + 0.46, z + 0.29, 0.52, 0.22, 0.035, materials.counter, false, floor);
  addBox("marinette nightstand knob", x, y + 0.46, z + 0.33, 0.06, 0.06, 0.035, materials.handle, false, floor);

  const purse = new THREE.Group();
  purse.name = "marinette optional purse";
  purse.position.set(x - 0.04, y + 0.84, z + 0.03);
  purse.rotation.set(0.06, -0.18, -Math.PI / 2.15);
  purse.scale.setScalar(0.46);
  purse.userData = {
    type: "personal_item",
    owner: "Ladybug Marinette Expanded Smoke",
    itemId: "marinette_purse",
    portable: true,
    optionalCarry: true,
    currentLocation: "Home World Marinette temporary room nightstand",
    canStore: ["marinette_phone"],
    futureBehavior: "Marinette may carry this, leave it here, redesign it, sew a replacement, or buy a different purse later.",
  };

  const body = new THREE.Mesh(new THREE.SphereGeometry(0.28, 32, 18), materials.pursePink);
  body.name = "pink polka dot purse body";
  body.scale.set(1.05, 0.78, 0.34);
  body.castShadow = true;
  body.receiveShadow = true;
  purse.add(body);

  const opening = new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.11, 0.16), materials.purseInterior);
  opening.name = "red purse interior";
  opening.position.set(0, 0.18, 0.02);
  opening.castShadow = true;
  purse.add(opening);

  const rimTop = new THREE.Mesh(new THREE.BoxGeometry(0.58, 0.035, 0.07), materials.handle);
  rimTop.name = "gold purse rim";
  rimTop.position.set(0, 0.22, 0.02);
  purse.add(rimTop);

  for (const sx of [-0.31, 0.31]) {
    const sideRim = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.26, 0.06), materials.handle);
    sideRim.name = "gold purse side rim";
    sideRim.position.set(sx, 0.07, 0.02);
    sideRim.rotation.z = sx < 0 ? -0.18 : 0.18;
    purse.add(sideRim);

    const clasp = new THREE.Mesh(new THREE.SphereGeometry(0.055, 16, 12), materials.purseRed);
    clasp.name = "red purse clasp bead";
    clasp.position.set(sx * 0.32, 0.31, 0.04);
    purse.add(clasp);
  }

  const strapPoints = [
    [-0.34, 0.08, 0.0],
    [-0.3, 0.25, 0.03],
    [-0.18, 0.42, 0.06],
    [0, 0.48, 0.08],
    [0.18, 0.42, 0.06],
    [0.3, 0.25, 0.03],
    [0.34, 0.08, 0.0],
  ];
  for (let i = 0; i < strapPoints.length - 1; i++) {
    const a = new THREE.Vector3(...strapPoints[i]);
    const b = new THREE.Vector3(...strapPoints[i + 1]);
    const mid = a.clone().add(b).multiplyScalar(0.5);
    const length = a.distanceTo(b);
    const link = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, length, 8), materials.purseBlack);
    link.name = "soft segmented purse strap link";
    link.position.copy(mid);
    link.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
    purse.add(link);
  }

  const dotPositions = [
    [-0.2, -0.1], [-0.07, -0.16], [0.1, -0.11], [0.22, -0.02],
    [-0.24, 0.04], [-0.1, 0.02], [0.05, 0.05], [0.18, 0.12],
  ];
  for (const [dx, dy] of dotPositions) {
    const dot = new THREE.Mesh(new THREE.SphereGeometry(0.015, 8, 6), materials.purseDot);
    dot.name = "purse white dot";
    dot.position.set(dx, dy, 0.102);
    dot.scale.z = 0.28;
    purse.add(dot);
  }

  const monogram = new THREE.Mesh(new THREE.TorusGeometry(0.09, 0.01, 8, 24), materials.purseInk);
  monogram.name = "purse monogram circle";
  monogram.position.set(-0.08, -0.06, 0.105);
  monogram.rotation.x = Math.PI / 2;
  purse.add(monogram);

  const flowerCenter = new THREE.Mesh(new THREE.SphereGeometry(0.022, 10, 8), materials.purseInk);
  flowerCenter.name = "purse flower center";
  flowerCenter.position.set(0.14, -0.02, 0.112);
  purse.add(flowerCenter);
  for (let i = 0; i < 5; i++) {
    const petal = new THREE.Mesh(new THREE.SphereGeometry(0.026, 10, 8), materials.purseDot);
    petal.name = "purse flower petal";
    const a = (Math.PI * 2 * i) / 5;
    petal.position.set(0.14 + Math.cos(a) * 0.045, -0.02 + Math.sin(a) * 0.045, 0.108);
    petal.scale.z = 0.25;
    purse.add(petal);
  }
  scene.add(purse);

  const phone = new THREE.Group();
  phone.name = "marinette phone";
  phone.position.set(x - 0.16, y + 0.705, z - 0.1);
  phone.rotation.y = -0.35;
  phone.userData = {
    type: "personal_item",
    owner: "Ladybug Marinette Expanded Smoke",
    itemId: "marinette_phone",
    portable: true,
    storableIn: "marinette_purse",
    currentLocation: "Home World Marinette temporary room nightstand beside purse",
    abilities: ["calls", "messages", "future_music_playback"],
  };
  const phoneBody = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.018, 0.17), materials.phoneBody);
  phoneBody.name = "phone body";
  phoneBody.castShadow = true;
  phone.add(phoneBody);
  const phoneScreen = new THREE.Mesh(new THREE.BoxGeometry(0.074, 0.008, 0.135), materials.phoneScreen);
  phoneScreen.name = "phone lit screen";
  phoneScreen.position.y = 0.024;
  phone.add(phoneScreen);
  scene.add(phone);

  interactZones.push({
    name: "marinette purse and phone",
    x,
    z,
    floor,
    radius: 1.15,
    action: () => show("Marinette's purse and phone are on the nightstand. They are optional carry items for her life loop."),
  });
}

function addPeterTemporaryWorkspaceProps() {
  const floor = 1;
  const y = floorBase(floor);
  markTruthProp(
    addBox("peter parker temporary desk camera body", -6.68, y + 0.62, -1.62, 0.22, 0.14, 0.14, materials.phoneBody, false, floor),
    "camera",
    "Peter Parker camera",
    floor,
    ["research", "photography"],
  );
  const lens = addCylinder("peter parker temporary desk camera lens", -6.68, y + 0.62, -1.51, 0.055, 0.12, materials.brushedSteel, false, floor);
  lens.rotation.x = Math.PI / 2;
  addBox("peter parker temporary desk photo contact sheet", -6.08, y + 0.59, -1.58, 0.36, 0.022, 0.28, materials.paper, false, floor);
  addBox("peter parker temporary wall photo print 1", -7.06, y + 1.45, -1.24, 0.035, 0.36, 0.28, materials.paper, false, floor);
  addBox("peter parker temporary wall photo print 2", -7.06, y + 1.82, -1.72, 0.035, 0.36, 0.28, materials.paper, false, floor);
  addCylinder("peter parker temporary web cartridge a", -5.92, y + 0.63, -1.83, 0.04, 0.2, materials.brushedSteel, false, floor);
  addCylinder("peter parker temporary web cartridge b", -5.78, y + 0.63, -1.83, 0.04, 0.2, materials.brushedSteel, false, floor);
  addBox("peter parker temporary science notes", -6.22, y + 0.62, -1.95, 0.34, 0.024, 0.26, materials.notebookCover, false, floor);
}

function addDiningRoom() {
  const floor = 0;
  const y = floorBase(floor);
  addFloorTile("front dining room woven rug", 5.28, 4.52, 3.25, 2.35, materials.rugWarm, y + 0.045);
  addBox("front dining room rectangular table top", 5.28, y + 0.74, 4.52, 2.08, 0.16, 0.98, materials.livingWood, true, floor);
  addBox("front dining room table left leg", 4.5, y + 0.38, 4.18, 0.12, 0.68, 0.12, materials.wood, false, floor);
  addBox("front dining room table right leg", 6.06, y + 0.38, 4.18, 0.12, 0.68, 0.12, materials.wood, false, floor);
  addBox("front dining room table front left leg", 4.5, y + 0.38, 4.86, 0.12, 0.68, 0.12, materials.wood, false, floor);
  addBox("front dining room table front right leg", 6.06, y + 0.38, 4.86, 0.12, 0.68, 0.12, materials.wood, false, floor);
  for (const [i, x, z, yaw] of [
    [0, 4.5, 5.22, Math.PI],
    [1, 5.28, 5.22, Math.PI],
    [2, 6.06, 5.22, Math.PI],
    [3, 4.5, 3.82, 0],
    [4, 5.28, 3.82, 0],
    [5, 6.06, 3.82, 0],
  ]) {
    addBox(`front dining room chair ${i} seat`, x, y + 0.38, z, 0.46, 0.14, 0.46, materials.trim, true, floor);
    addBox(`front dining room chair ${i} back`, x, y + 0.78, z + Math.cos(yaw) * 0.27, 0.5, 0.66, 0.1, materials.trim, false, floor);
  }
  addCylinder("front dining room pendant light shade", 5.28, y + 2.15, 4.52, 0.28, 0.22, materials.lampShade, false, floor);
  addBox("front dining room place setting left", 4.74, y + 0.84, 4.52, 0.3, 0.035, 0.22, materials.fixture, false, floor);
  addBox("front dining room place setting center", 5.28, y + 0.84, 4.52, 0.3, 0.035, 0.22, materials.fixture, false, floor);
  addBox("front dining room place setting right", 5.82, y + 0.84, 4.52, 0.3, 0.035, 0.22, materials.fixture, false, floor);
}

function addGwenUpstairsBedroomProps() {
  const floor = 1;
  const y = floorBase(floor);
  addWallDeskComputer("gwen stacy temporary music science desk", -6.45, -3.65, floor);
  addCylinder("gwen stacy upstairs snare drum", -4.25, y + 0.42, -4.22, 0.24, 0.2, materials.fixture, false, floor);
  addCylinder("gwen stacy upstairs cymbal stand", -3.92, y + 0.68, -4.55, 0.025, 0.82, materials.brushedSteel, false, floor);
  const cymbal = addCylinder("gwen stacy upstairs cymbal", -3.92, y + 1.1, -4.55, 0.2, 0.032, materials.handle, false, floor);
  cymbal.scale.y = 0.35;
  markTruthProp(addBox("gwen stacy upstairs notebook", -6.34, y + 0.62, -3.52, 0.34, 0.035, 0.3, materials.paper, false, floor), "notebook", "Gwen Stacy upstairs notebook", floor, ["read_book", "sketch_design"]);
}

function isSuppressedDownstairsToilet(name, floor) {
  if (floor !== 0) return false;
  const label = String(name || "").toLowerCase();
  if (/one-bedroom|neighbor|starbucks|kira bungalow|bungalow|school/.test(label)) return false;
  return true;
}

function addToilet(name, x, z, floor) {
  if (isSuppressedDownstairsToilet(name, floor)) return;
  const y = floorBase(floor);
  const bowl = addCylinder(`${name} toilet bowl fallback`, x, y + 0.34, z, 0.22, 0.22, materials.fixture, true, floor);
  const tank = addBox(`${name} toilet tank fallback`, x, y + 0.62, z - 0.24, 0.52, 0.42, 0.18, materials.fixture, true, floor);
  addRealisticToiletModel(name, x, z, floor, 0, [bowl, tank]);
  addColliderOnly(x, z, 0.72, 0.72, floor);
  interactZones.push({
    name: `${name} toilet`,
    x,
    z,
    floor,
    radius: 0.9,
    action: () => show(`${name} toilet is usable. Plumbing simulation is marked for the next functional pass.`),
  });
}

function addSideFacingToilet(name, x, z, floor, facing = "left") {
  if (isSuppressedDownstairsToilet(name, floor)) return;
  const y = floorBase(floor);
  const sign = facing === "left" ? 1 : -1;
  const bowl = addCylinder(`${name} toilet bowl fallback`, x, y + 0.34, z, 0.22, 0.22, materials.fixture, false, floor);
  const tank = addBox(`${name} toilet tank fallback`, x + sign * 0.24, y + 0.62, z, 0.18, 0.42, 0.52, materials.fixture, true, floor);
  const lid = addBox(`${name} toilet lid fallback`, x, y + 0.59, z, 0.38, 0.05, 0.46, materials.fixture, false, floor);
  const lever = addBox(`${name} toilet flush lever fallback`, x + sign * 0.34, y + 0.78, z - 0.18, 0.12, 0.045, 0.08, materials.handle, false, floor);
  addRealisticToiletModel(name, x, z, floor, facing === "left" ? Math.PI / 2 : -Math.PI / 2, [bowl, tank, lid, lever]);
  addColliderOnly(x, z, 0.72, 0.72, floor);
  interactZones.push({
    name: `${name} toilet controls`,
    x,
    z,
    floor,
    radius: 0.9,
    action: () => show("Toilet lid, seat, flush, and water movement are staged for the plumbing animation pass. The fixture is now placed for usable clearance."),
  });
}

function addSink(name, x, z, floor) {
  const y = floorBase(floor);
  addBox(`${name} vanity`, x, y + 0.38, z, 0.72, 0.65, 0.44, materials.fixture, false);
  addBox(`${name} basin`, x, y + 0.74, z, 0.54, 0.08, 0.32, materials.glass, false);
}

function addSoftPillow(name, x, y, z, material, rotationY = 0, sx = 0.46, sy = 0.22, sz = 0.18) {
  const pillow = new THREE.Mesh(new THREE.SphereGeometry(0.5, 24, 14), material);
  pillow.name = name;
  pillow.position.set(x, y, z);
  pillow.scale.set(sx, sy, sz);
  pillow.rotation.set(-0.08, rotationY, 0.04);
  pillow.castShadow = true;
  pillow.receiveShadow = true;
  scene.add(pillow);
  return pillow;
}

function addInteractiveRefrigerator() {
  const fridgeX = -7.08;
  const fridgeZ = -6.72;
  const fridgeDoorZ = -6.34;
  addBox("kitchen recessed refrigerator alcove side", -6.58, 1.04, fridgeZ, 0.08, 1.98, 0.86, materials.wall, false, 0);
  addBox("kitchen refrigerator cabinet", fridgeX, 1.06, fridgeZ, 0.84, 1.98, 0.74, materials.fridgeWhite, true, 0);
  addBox("kitchen refrigerator side shadow", -6.63, 1.06, fridgeZ, 0.04, 1.94, 0.7, materials.brushedSteel, false, 0);
  addBox("kitchen refrigerator toe kick", fridgeX, 0.16, fridgeDoorZ + 0.04, 0.68, 0.08, 0.08, materials.burnerBlack, false, 0);
  addBox("kitchen refrigerator interior back", fridgeX, 1.08, fridgeDoorZ - 0.01, 0.68, 1.64, 0.035, materials.glass, false, 0);
  for (const y of [0.72, 1.08, 1.44]) {
    addBox("kitchen refrigerator glass shelf", fridgeX, y, fridgeDoorZ + 0.03, 0.62, 0.026, 0.08, materials.glass, false, 0);
  }
  addBox("kitchen refrigerator produce drawer", fridgeX, 0.46, fridgeDoorZ + 0.04, 0.56, 0.18, 0.12, materials.glass, false, 0);

  kitchenFridgeDoorGroup = new THREE.Group();
  kitchenFridgeDoorGroup.name = "kitchen refrigerator hinged door";
  kitchenFridgeDoorGroup.position.set(-7.5, 0.08, fridgeDoorZ);

  const panel = new THREE.Mesh(new THREE.BoxGeometry(0.84, 1.86, 0.07), materials.fridgeWhite);
  panel.name = "kitchen refrigerator door panel";
  panel.position.set(0.42, 0.98, 0);
  panel.castShadow = true;
  panel.receiveShadow = true;
  kitchenFridgeDoorGroup.add(panel);

  const freezerLine = new THREE.Mesh(new THREE.BoxGeometry(0.78, 0.028, 0.078), materials.brushedSteel);
  freezerLine.name = "kitchen refrigerator freezer seam";
  freezerLine.position.set(0.42, 1.36, 0.044);
  freezerLine.castShadow = true;
  kitchenFridgeDoorGroup.add(freezerLine);

  const handle = new THREE.Mesh(new THREE.BoxGeometry(0.055, 0.72, 0.07), materials.brushedSteel);
  handle.name = "kitchen refrigerator pull handle";
  handle.position.set(0.72, 0.94, 0.07);
  handle.castShadow = true;
  kitchenFridgeDoorGroup.add(handle);

  scene.add(kitchenFridgeDoorGroup);
  setKitchenFridgeOpen(false);

  interactZones.push({
    name: "kitchen refrigerator",
    x: -7.0,
    z: -6.2,
    floor: 0,
    radius: 1.15,
    action: () => {
      setKitchenFridgeOpen(!kitchenFridgeDoorOpen);
      show(kitchenFridgeDoorOpen ? "Kitchen refrigerator open." : "Kitchen refrigerator closed.");
    },
  });
}

function addKitchenDetails() {
  addBox("kitchen warm backsplash", -5.7, 1.18, -6.98, 4.7, 0.86, 0.055, materials.rugBorder, false, 0);
  addBox("kitchen upper cabinet left", -6.42, 1.82, -6.96, 1.22, 0.56, 0.18, materials.warmCabinet, false, 0);
  addBox("kitchen upper cabinet center", -5.15, 1.82, -6.96, 1.0, 0.56, 0.18, materials.warmCabinet, false, 0);
  addBox("kitchen upper cabinet right", -3.88, 1.82, -6.96, 1.22, 0.56, 0.18, materials.warmCabinet, false, 0);
  for (const x of [-6.72, -6.12, -5.4, -4.9, -4.18, -3.58]) {
    addBox("kitchen cabinet pull", x, 1.82, -6.84, 0.035, 0.32, 0.045, materials.handle, false, 0);
  }
  for (const [x, y] of [
    [-6.2, 0.58],
    [-5.32, 0.58],
    [-4.84, 0.58],
    [-4.28, 0.72],
    [-4.28, 0.44],
  ]) {
    addBox("kitchen lower cabinet pull", x, y, -6.31, 0.28, 0.035, 0.045, materials.handle, false, 0);
  }

  addInteractiveRefrigerator();

  addBox("kitchen farmhouse sink basin", -5.0, 0.98, -6.34, 0.78, 0.16, 0.48, materials.fixture, false, 0);
  addBox("kitchen sink water dark well", -5.0, 1.05, -6.34, 0.58, 0.035, 0.32, materials.glass, false, 0);
  addBox("kitchen sink faucet neck", -5.0, 1.24, -6.58, 0.055, 0.34, 0.055, materials.brushedSteel, false, 0);
  addBox("kitchen sink faucet spout", -5.0, 1.39, -6.43, 0.055, 0.055, 0.28, materials.brushedSteel, false, 0);
  addCylinder("kitchen sink hot knob", -5.28, 1.12, -6.38, 0.035, 0.035, materials.handle, false, 0);
  addCylinder("kitchen sink cold knob", -4.72, 1.12, -6.38, 0.035, 0.035, materials.handle, false, 0);

  addBox("kitchen range oven body", -3.65, 0.58, -6.52, 0.92, 0.82, 0.58, materials.brushedSteel, true, 0);
  addBox("kitchen oven glass door", -3.65, 0.56, -6.2, 0.66, 0.38, 0.045, materials.screen, false, 0);
  addBox("kitchen oven handle", -3.65, 0.84, -6.16, 0.62, 0.055, 0.055, materials.handle, false, 0);
  addBox("kitchen cooktop slab", -3.65, 1.02, -6.52, 0.94, 0.045, 0.58, materials.burnerBlack, false, 0);
  for (const [x, z, r] of [
    [-3.9, -6.68, 0.105],
    [-3.42, -6.68, 0.105],
    [-3.9, -6.38, 0.085],
    [-3.42, -6.38, 0.085],
  ]) {
    addCylinder("kitchen cooktop burner", x, 1.065, z, r, 0.026, materials.brushedSteel, false, 0);
    addCylinder("kitchen burner cap", x, 1.086, z, r * 0.52, 0.03, materials.burnerBlack, false, 0);
  }
  addBox("kitchen range hood", -3.65, 1.64, -6.78, 1.02, 0.18, 0.48, materials.brushedSteel, false, 0);
  addBox("kitchen range hood vent", -3.65, 1.83, -6.82, 0.68, 0.28, 0.22, materials.brushedSteel, false, 0);

  addBox("kitchen island butcher-block top", -4.2, 0.94, -4.2, 2.32, 0.12, 1.08, materials.livingWood, true, 0);
  addBox("kitchen island softened front lip", -4.2, 1.01, -3.62, 2.28, 0.075, 0.075, materials.livingWood, false, 0);
  addBox("kitchen island softened back lip", -4.2, 1.01, -4.78, 2.28, 0.075, 0.075, materials.livingWood, false, 0);
  addBox("kitchen island drawer left", -4.72, 0.67, -3.62, 0.44, 0.22, 0.045, materials.warmCabinet, false, 0);
  addBox("kitchen island drawer right", -3.68, 0.67, -3.62, 0.44, 0.22, 0.045, materials.warmCabinet, false, 0);
  addBox("kitchen island drawer left pull", -4.72, 0.68, -3.57, 0.28, 0.035, 0.045, materials.handle, false, 0);
  addBox("kitchen island drawer right pull", -3.68, 0.68, -3.57, 0.28, 0.035, 0.045, materials.handle, false, 0);
  addBox("kitchen island dish towel", -3.22, 0.62, -4.18, 0.055, 0.48, 0.28, materials.blanketBlue, false, 0);
  addBox("kitchen toaster body", -5.96, 1.1, -6.44, 0.36, 0.22, 0.24, materials.brushedSteel, false, 0);
  addBox("kitchen toaster slot", -5.96, 1.225, -6.44, 0.26, 0.025, 0.15, materials.burnerBlack, false, 0);
  addBox("kitchen cutting board", -4.16, 1.03, -4.2, 0.46, 0.035, 0.34, materials.wood, false, 0);
  addCylinder("kitchen fruit bowl", -4.58, 1.06, -4.24, 0.22, 0.08, materials.fixture, false, 0);
  for (const [x, z, mat] of [
    [-4.62, -4.26, materials.produceRed],
    [-4.51, -4.2, materials.produceYellow],
    [-4.7, -4.15, materials.produceGreen],
  ]) {
    const fruit = new THREE.Mesh(new THREE.SphereGeometry(0.06, 14, 10), mat);
    fruit.name = "kitchen bowl fruit";
    fruit.position.set(x, 1.14, z);
    fruit.castShadow = true;
    fruit.receiveShadow = true;
    scene.add(fruit);
  }
}

function addLivingRoomDecor() {
  addBox("living room warm area rug", -5.15, 0.075, 2.05, 3.25, 0.035, 2.05, materials.rugWarm, false, 0);
  addBox("living room rug front border", -5.15, 0.096, 1.03, 3.18, 0.018, 0.045, materials.rugBorder, false, 0);
  addBox("living room rug back border", -5.15, 0.096, 3.07, 3.18, 0.018, 0.045, materials.rugBorder, false, 0);
  addBox("living room rug left border", -6.76, 0.096, 2.05, 0.045, 0.018, 1.92, materials.rugBorder, false, 0);
  addBox("living room rug right border", -3.54, 0.096, 2.05, 0.045, 0.018, 1.92, materials.rugBorder, false, 0);

  addBox("living room oval coffee table", -5.15, 0.31, 1.92, 1.22, 0.16, 0.46, materials.livingWood, true, 0);
  addBox("living room coffee table magazine", -5.38, 0.41, 1.86, 0.32, 0.025, 0.24, materials.paper, false, 0);
  addBox("living room remote control", -4.88, 0.43, 1.97, 0.24, 0.025, 0.07, materials.phoneBody, false, 0);

  addBox("living room left side table", -6.56, 0.42, 2.02, 0.48, 0.48, 0.48, materials.livingWood, true, 0);
  addCylinder("living room floor lamp pole", -6.76, 1.02, 1.28, 0.025, 1.55, materials.handle, false, 0);
  addCylinder("living room floor lamp shade", -6.76, 1.78, 1.28, 0.18, 0.28, materials.lampShade, false, 0);

  addSoftPillow("living room folded throw blanket soft edge", -5.12, 0.675, 2.55, materials.blanketPink, 0.02, 0.76, 0.08, 0.34);
  addBox("living room small book stack", -6.56, 0.69, 2.02, 0.32, 0.055, 0.24, materials.paper, false, 0);
  addBox("living room book cover blue", -6.56, 0.735, 2.02, 0.34, 0.025, 0.25, materials.blanketBlue, false, 0);

  addCylinder("living room plant pot", -7.15, 0.36, 1.12, 0.18, 0.34, materials.livingWood, true, 0);
  const plantLeafPositions = [
    [-7.22, 0.68, 1.06],
    [-7.08, 0.78, 1.15],
    [-7.23, 0.86, 1.2],
    [-7.04, 0.64, 1.02],
  ];
  for (const [x, y, z] of plantLeafPositions) {
    const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.11, 16, 10), materials.plantLeaf);
    leaf.name = "living room plant leaf";
    leaf.position.set(x, y, z);
    leaf.scale.set(0.75, 1.25, 0.42);
    leaf.castShadow = true;
    leaf.receiveShadow = true;
    scene.add(leaf);
  }
}

function addHomeBookshelf() {
  const shelfX = -7.6;
  const shelfZ = 4.82;
  const shelfY = 0.98;
  markTruthProp(
    addBox("home living room freestanding bookcase back panel", shelfX, shelfY, shelfZ, 0.12, 1.82, 2.18, materials.livingWood, true, 0),
    "shelf",
    "home living room bookshelf",
    0,
    ["browse_books", "read_book"],
  );

  const frontX = shelfX + 0.16;
  addBox("home bookshelf left side panel", frontX, 0.98, shelfZ - 1.12, 0.28, 1.92, 0.1, materials.wood, false, 0);
  addBox("home bookshelf right side panel", frontX, 0.98, shelfZ + 1.12, 0.28, 1.92, 0.1, materials.wood, false, 0);
  addBox("home bookshelf top crown rail", frontX, 1.96, shelfZ, 0.32, 0.12, 2.32, materials.wood, false, 0);
  addBox("home bookshelf bottom plinth rail", frontX, 0.11, shelfZ, 0.34, 0.16, 2.34, materials.trim, false, 0);
  addBox("home bookshelf lower cabinet left door", frontX + 0.03, 0.36, shelfZ - 0.52, 0.11, 0.42, 0.72, materials.warmCabinet, false, 0);
  addBox("home bookshelf lower cabinet right door", frontX + 0.03, 0.36, shelfZ + 0.52, 0.11, 0.42, 0.72, materials.warmCabinet, false, 0);
  addBox("home bookshelf left cabinet knob", frontX + 0.11, 0.42, shelfZ - 0.14, 0.035, 0.055, 0.035, materials.handle, false, 0);
  addBox("home bookshelf right cabinet knob", frontX + 0.11, 0.42, shelfZ + 0.14, 0.035, 0.055, 0.035, materials.handle, false, 0);

  for (const y of [0.64, 0.98, 1.32, 1.66]) {
    addBox("home bookshelf thick shelf plank", frontX, y, shelfZ, 0.34, 0.075, 2.16, materials.wood, false, 0);
  }

  const bookMats = [materials.notebookCover, materials.paper, materials.blanketBlue, materials.produceGreen, materials.produceYellow, materials.purseRed];
  const titles = [
    "home shelf adventure novel",
    "home shelf fashion history book",
    "home shelf robotics guide",
    "home shelf science notebook",
    "home shelf sketch reference",
    "home shelf library paperback",
  ];
  for (let row = 0; row < 3; row += 1) {
    const baseY = 0.685 + row * 0.34;
    let cursorZ = shelfZ - 0.96 + row * 0.035;
    for (let i = 0; i < 15; i += 1) {
      const title = titles[i % titles.length];
      const bookWidth = 0.06 + ((i + row) % 4) * 0.014;
      const z = cursorZ + bookWidth * 0.5;
      const height = 0.24 + ((i + row) % 5) * 0.032;
      const book = addBox(
        `${title} row ${row + 1} volume ${i + 1}`,
        frontX + 0.16,
        baseY + height * 0.5,
        z,
        0.08,
        height,
        bookWidth,
        bookMats[(i + row) % bookMats.length],
        false,
        0,
      );
      book.rotation.x = ((i + row) % 5 === 0 ? 0.035 : (i % 7 === 0 ? -0.025 : 0));
      markTruthProp(book, "book", title, 0, ["read_book", "browse_books"]);
      cursorZ += bookWidth + 0.018;
    }
  }

  for (let row = 0; row < 2; row += 1) {
    const y = 1.04 + row * 0.34;
    for (let i = 0; i < 3; i += 1) {
      const stack = addBox(
        `home bookshelf horizontal stack row ${row + 1} book ${i + 1}`,
        frontX + 0.16,
        y + i * 0.04,
        shelfZ + 0.72 + i * 0.02,
        0.09,
        0.035,
        0.34,
        bookMats[(i + row + 2) % bookMats.length],
        false,
        0,
      );
      markTruthProp(stack, "book", stack.name, 0, ["read_book", "browse_books"]);
    }
  }

  addCylinder("home bookshelf small ceramic vase", frontX + 0.16, 1.49, shelfZ - 0.78, 0.08, 0.22, materials.fixture, false, 0);
  addBox("home bookshelf framed photo", frontX + 0.18, 1.47, shelfZ + 0.42, 0.06, 0.24, 0.34, materials.screen, false, 0);

  const openBook = markTruthProp(
    addBox("home bookshelf open book on side table", -6.5, 0.78, 2.28, 0.42, 0.035, 0.28, materials.paper, false, 0),
    "book",
    "open book from the home bookshelf",
    0,
    ["read_book"],
  );
  openBook.rotation.y = -0.08;
  interactZones.push({
    name: "home living room bookshelf",
    x: -7.15,
    z: 4.82,
    floor: 0,
    radius: 1.25,
    action: () => show("Home bookshelf: books are available here for reading without walking to the public library."),
  });
}

function addEnclosedDownstairsPowderRoom() {
  // Robert asked to remove the downstairs bathroom entirely. Keep this builder
  // disabled until the first floor is redesigned with a proper dining/common layout.
  return;
  addBox("downstairs powder room rear wall", 6.88, 1.58, -7.08, 2.12, 3.05, 0.14, materials.wall, true, 0);
  addBox("downstairs powder room front wall", 6.88, 1.58, -5.22, 2.12, 3.05, 0.14, materials.wall, true, 0);
  addBox("downstairs powder room right interior wall", 7.78, 1.58, -6.15, 0.14, 3.05, 1.9, materials.wall, true, 0);
  addZWallWithGaps("downstairs powder room side entry wall", 5.9, -7.08, -5.22, [{ center: -6.0, width: 0.94 }], 1.58, 3.05, materials.wall, 0);
  addZWallDoorTrim("downstairs powder room side entry trim", 5.9, -6.0, 0.94, 0);
  addFloorThreshold("downstairs powder room threshold", 5.9, -6.0, 0.34, 0.82, 0);
  createZWallInteriorDoor("downstairs powder room hinged privacy door", 5.9, -6.0, 0.94, 0, -1, "downstairs powder room privacy door");
  addSink("downstairs powder room", 6.24, -5.54, 0);
  addBox("downstairs powder room faucet riser", 6.24, 1.0, -5.77, 0.055, 0.28, 0.055, materials.handle, false, 0);
  addBox("downstairs powder room faucet spout", 6.24, 1.14, -5.65, 0.055, 0.055, 0.24, materials.handle, false, 0);
  addCylinder("downstairs powder room hot knob", 6.08, 0.9, -5.62, 0.035, 0.035, materials.handle, false, 0);
  addCylinder("downstairs powder room cold knob", 6.4, 0.9, -5.62, 0.035, 0.035, materials.handle, false, 0);
  const powderSinkStream = addBox("downstairs powder room sink water stream", 6.24, 0.9, -5.56, 0.035, 0.24, 0.035, materials.water, false, 0);
  powderSinkStream.visible = false;
  downstairsPowderSinkWaterMeshes.push(powderSinkStream);
  addReflectiveMirror("downstairs powder room mirror", 6.24, 1.45, -5.3, 0.58, 0.76, 0);
  addBox("downstairs powder room linen storage cabinet", 7.38, 0.78, -6.68, 0.58, 1.26, 0.46, materials.warmCabinet, true, 0);
  addBox("downstairs powder room folded towel shelf top", 7.38, 1.33, -6.4, 0.5, 0.08, 0.16, materials.paper, false, 0);
  addBox("downstairs powder room folded towel shelf middle", 7.38, 1.05, -6.4, 0.5, 0.08, 0.16, materials.paper, false, 0);
  addBox("downstairs powder room bath mat", 6.64, 0.09, -5.92, 0.72, 0.035, 0.52, materials.rugBorder, false, 0);
  interactZones.push({
    name: "downstairs powder room sink faucet",
    x: 6.24,
    z: -5.54,
    floor: 0,
    radius: 0.85,
    action: () => {
      downstairsPowderSinkWaterOn = !downstairsPowderSinkWaterOn;
      for (const mesh of downstairsPowderSinkWaterMeshes) mesh.visible = downstairsPowderSinkWaterOn;
      show(downstairsPowderSinkWaterOn ? "Downstairs powder-room sink is running." : "Downstairs powder-room sink is off.");
    },
  });
}

function addShower(name, x, z, floor) {
  const y = floorBase(floor);
  addBox(`${name} shower pan`, x, y + 0.08, z, 1.05, 0.12, 1.05, materials.fixture, false);
  addBox(`${name} glass wall`, x - 0.52, y + 0.9, z, 0.05, 1.65, 1.0, materials.glass, false);
  addBox(`${name} glass door`, x, y + 0.9, z + 0.52, 1.0, 1.65, 0.05, materials.glass, false);
}

function addBathtubShower(name, x, z, floor) {
  const y = floorBase(floor);
  addBox(`${name} tub outer shell`, x, y + 0.28, z, 2.25, 0.46, 0.92, materials.fixture, false, floor);
  addBox(`${name} tub inner basin`, x, y + 0.55, z, 1.84, 0.12, 0.58, materials.water, false, floor);
  addBox(`${name} tub front lip`, x, y + 0.66, z + 0.48, 2.28, 0.18, 0.08, materials.fixture, false, floor);
  addBox(`${name} tub back lip`, x, y + 0.66, z - 0.48, 2.28, 0.18, 0.08, materials.fixture, false, floor);
  addBox(`${name} tub left lip`, x - 1.13, y + 0.66, z, 0.08, 0.18, 0.92, materials.fixture, false, floor);
  addBox(`${name} tub right lip`, x + 1.13, y + 0.66, z, 0.08, 0.18, 0.92, materials.fixture, false, floor);
  addBox(`${name} shower curtain rod`, x, y + 1.95, z + 0.53, 2.18, 0.045, 0.045, materials.handle, false, floor);
  addBox(`${name} shower privacy curtain`, x - 0.35, y + 1.22, z + 0.55, 1.05, 1.36, 0.045, materials.curtain, false, floor);
  addBox(`${name} shower pipe`, x - 0.86, y + 1.4, z - 0.48, 0.045, 1.0, 0.045, materials.handle, false, floor);
  addCylinder(`${name} shower head`, x - 0.86, y + 1.9, z - 0.37, 0.09, 0.04, materials.handle, false, floor);
  addBox(`${name} tub faucet`, x - 0.62, y + 0.83, z - 0.44, 0.24, 0.06, 0.08, materials.handle, false, floor);
  addCylinder(`${name} hot knob`, x - 0.28, y + 0.84, z - 0.47, 0.045, 0.035, materials.handle, false, floor);
  addCylinder(`${name} cold knob`, x - 0.08, y + 0.84, z - 0.47, 0.045, 0.035, materials.handle, false, floor);
  const tubStream = addBox(`${name} faucet water stream`, x - 0.47, y + 0.71, z - 0.42, 0.04, 0.26, 0.035, materials.water, false, floor);
  const showerStream = addBox(`${name} shower spray placeholder`, x - 0.86, y + 1.45, z - 0.33, 0.28, 0.68, 0.035, materials.water, false, floor);
  tubStream.visible = false;
  showerStream.visible = false;
  tubWaterMeshes.push(tubStream, showerStream);
}

function addUpstairsSharedBathroom() {
  addBathtubShower("upstairs shared bath", 6.55, -0.05, 1);
  addSideFacingToilet("upstairs shared bath", 7.42, 0.78, 1, "left");

  addBox("upstairs shared bath double vanity base", 3.64, floorBase(1) + 0.42, 0.55, 0.54, 0.72, 2.25, materials.cabinet, true, 1);
  addBox("upstairs shared bath counter top", 3.62, floorBase(1) + 0.82, 0.55, 0.6, 0.08, 2.35, materials.counter, true, 1);
  addBox("upstairs shared bath left sink basin", 3.47, floorBase(1) + 0.87, 0.02, 0.32, 0.055, 0.54, materials.fixture, false, 1);
  addBox("upstairs shared bath right sink basin", 3.47, floorBase(1) + 0.87, 1.0, 0.32, 0.055, 0.54, materials.fixture, false, 1);
  addBox("upstairs shared bath left faucet", 3.36, floorBase(1) + 1.0, 0.02, 0.18, 0.08, 0.08, materials.handle, false, 1);
  addBox("upstairs shared bath right faucet", 3.36, floorBase(1) + 1.0, 1.0, 0.18, 0.08, 0.08, materials.handle, false, 1);
  for (const [name, z] of [["left", 0.02], ["right", 1.0]]) {
    const stream = addBox(`upstairs shared bath ${name} sink water stream`, 3.43, floorBase(1) + 0.94, z, 0.035, 0.22, 0.035, materials.water, false, 1);
    stream.visible = false;
    vanityWaterMeshes.push(stream);
  }
  addReflectiveMirror("upstairs shared bath mirror", 3.305, floorBase(1) + 1.55, 0.55, 2.15, 1.0, 1);
  addBox("upstairs shared bath under sink cabinet left", 3.33, floorBase(1) + 0.36, 0.02, 0.05, 0.46, 0.72, materials.wood, false, 1);
  addBox("upstairs shared bath under sink cabinet right", 3.33, floorBase(1) + 0.36, 1.0, 0.05, 0.46, 0.72, materials.wood, false, 1);
  addBox("upstairs shared bath privacy curtain left window panel", 5.05, floorBase(1) + 1.52, 3.01, 0.72, 1.45, 0.05, materials.curtain, false, 1);
  addBox("upstairs shared bath privacy curtain right window panel", 5.95, floorBase(1) + 1.52, 3.01, 0.72, 1.45, 0.05, materials.curtain, false, 1);
  addBox("upstairs shared bath second privacy curtain left panel", 6.82, floorBase(1) + 1.52, 3.01, 0.72, 1.45, 0.05, materials.curtain, false, 1);
  addBox("upstairs shared bath second privacy curtain right panel", 7.68, floorBase(1) + 1.52, 3.01, 0.72, 1.45, 0.05, materials.curtain, false, 1);

  lisaBathDoorGroup = createBathroomDoorLeaf("upstairs shared bath lisa privacy door", 5.12, 2.78, -1);
  ladybugBathDoorGroup = createBathroomDoorLeaf("upstairs shared bath ladybug privacy door", 5.12, -2.78, 1);
  addBathroomDoorFrame("upstairs shared bath lisa privacy door frame", 5.12, 2.78, 1);
  addBathroomDoorFrame("upstairs shared bath ladybug privacy door frame", 5.12, -2.78, 1);
  addColliderOnly(5.65, 2.78, 1.15, 0.22, 1, () => !lisaBathDoorOpen);
  addColliderOnly(5.65, -2.78, 1.15, 0.22, 1, () => !ladybugBathDoorOpen);
  interactZones.push({
    name: "upstairs bath tub controls",
    x: 6.55,
    z: -0.05,
    floor: 1,
    radius: 1.05,
    action: () => {
      tubWaterOn = !tubWaterOn;
      for (const mesh of tubWaterMeshes) mesh.visible = tubWaterOn;
      show(tubWaterOn ? "Tub and shower water is running. Drain and water-level physics are still placeholder." : "Tub and shower water is off.");
    },
  });
  interactZones.push({
    name: "upstairs shared bath vanity",
    x: 3.65,
    z: 0.55,
    floor: 1,
    radius: 1.1,
    action: () => {
      vanityWaterOn = !vanityWaterOn;
      for (const mesh of vanityWaterMeshes) mesh.visible = vanityWaterOn;
      show(vanityWaterOn ? "Bathroom sink faucets are running." : "Bathroom sink faucets are off.");
    },
  });
  interactZones.push({
    name: "lisa bathroom privacy door",
    x: 5.65,
    z: 2.78,
    floor: 1,
    radius: 0.85,
    action: () => {
      if (lisaBathDoorLocked) {
        show("Lisa-side bathroom door is locked for privacy.");
        return;
      }
      lisaBathDoorOpen = !lisaBathDoorOpen;
      setBathroomDoorOpen(lisaBathDoorGroup, lisaBathDoorOpen);
      show(lisaBathDoorOpen ? "Lisa-side bathroom door open." : "Lisa-side bathroom door closed.");
    },
  });
  interactZones.push({
    name: "ladybug bathroom privacy door",
    x: 5.65,
    z: -2.78,
    floor: 1,
    radius: 0.85,
    action: () => {
      if (ladybugBathDoorLocked) {
        show("Marinette temporary-room bathroom door is locked for privacy.");
        return;
      }
      ladybugBathDoorOpen = !ladybugBathDoorOpen;
      setBathroomDoorOpen(ladybugBathDoorGroup, ladybugBathDoorOpen);
      show(ladybugBathDoorOpen ? "Marinette temporary-room bathroom door open." : "Marinette temporary-room bathroom door closed.");
    },
  });
}

function addFloorTile(name, x, z, sx, sz, material, y = 0) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(sx, 0.05, sz), material);
  mesh.name = name;
  mesh.position.set(x, y - 0.025, z);
  mesh.receiveShadow = true;
  scene.add(mesh);
  return mesh;
}

function addFloorThreshold(name, x, z, sx, sz, floor = 1) {
  addFloorTile(name, x, z, sx, sz, materials.sidewalk, floorBase(floor) + 0.02);
}

function addZWallWithGaps(name, x, zMin, zMax, gaps, yCenter, height, material, floor = 1) {
  const sorted = gaps
    .map((gap) => ({ min: gap.center - gap.width / 2, max: gap.center + gap.width / 2 }))
    .sort((a, b) => a.min - b.min);
  let cursor = zMin;
  for (const gap of sorted) {
    const a = Math.max(zMin, cursor);
    const b = Math.min(zMax, gap.min);
    if (b - a > 0.08) addBox(`${name} segment`, x, yCenter, (a + b) / 2, 0.14, height, b - a, material, true, floor);
    cursor = Math.max(cursor, gap.max);
  }
  if (zMax - cursor > 0.08) addBox(`${name} segment`, x, yCenter, (cursor + zMax) / 2, 0.14, height, zMax - cursor, material, true, floor);
}

function addXWallWithGaps(name, z, xMin, xMax, gaps, yCenter, height, material, floor = 1) {
  const sorted = gaps
    .map((gap) => ({ min: gap.center - gap.width / 2, max: gap.center + gap.width / 2 }))
    .sort((a, b) => a.min - b.min);
  let cursor = xMin;
  for (const gap of sorted) {
    const a = Math.max(xMin, cursor);
    const b = Math.min(xMax, gap.min);
    if (b - a > 0.08) addBox(`${name} segment`, (a + b) / 2, yCenter, z, b - a, height, 0.14, material, true, floor);
    cursor = Math.max(cursor, gap.max);
  }
  if (xMax - cursor > 0.08) addBox(`${name} segment`, (cursor + xMax) / 2, yCenter, z, xMax - cursor, height, 0.14, material, true, floor);
}

function addZWallDoorTrim(name, x, z, width, floor = 1) {
  const y = floorBase(floor);
  addBox(`${name} hinge jamb`, x, y + 1.12, z - width * 0.5, 0.18, 2.32, 0.1, materials.windowFrame, false, floor);
  addBox(`${name} latch jamb`, x, y + 1.12, z + width * 0.5, 0.18, 2.32, 0.1, materials.windowFrame, false, floor);
  addBox(`${name} header`, x, y + 2.31, z, 0.2, 0.16, width + 0.18, materials.windowFrame, false, floor);
}

function addXWallDoorTrim(name, z, x, width, floor = 1) {
  const y = floorBase(floor);
  addBox(`${name} hinge jamb`, x - width * 0.5, y + 1.12, z, 0.1, 2.32, 0.18, materials.windowFrame, false, floor);
  addBox(`${name} latch jamb`, x + width * 0.5, y + 1.12, z, 0.1, 2.32, 0.18, materials.windowFrame, false, floor);
  addBox(`${name} header`, x, y + 2.31, z, width + 0.18, 0.16, 0.2, materials.windowFrame, false, floor);
}

function setInteriorDoorOpen(key, open) {
  const group = interiorDoorGroups.get(key);
  interiorDoorOpen.set(key, !!open);
  if (group) group.rotation.y = open ? group.userData.openRotation : group.userData.closedRotation;
}

function toggleInteriorDoor(key, label) {
  const isOpen = !interiorDoorOpen.get(key);
  setInteriorDoorOpen(key, isOpen);
  show(isOpen ? `${label} open.` : `${label} closed.`);
}

function registerInteriorDoor(key, group, x, z, sx, sz, floor, label) {
  interiorDoorGroups.set(key, group);
  interiorDoorOpen.set(key, false);
  addColliderOnly(x, z, sx, sz, floor, () => !interiorDoorOpen.get(key));
  interactZones.push({
    name: label,
    x,
    z,
    floor,
    radius: 0.95,
    action: () => toggleInteriorDoor(key, label),
  });
  return group;
}

function createZWallInteriorDoor(name, x, z, width, floor = 1, swingSign = 1, label = name) {
  const y = floorBase(floor);
  const panelWidth = width * 0.82;
  const group = new THREE.Group();
  group.name = name;
  group.position.set(x, 0, z - width * 0.5);
  group.userData.closedRotation = 0;
  group.userData.openRotation = swingSign * Math.PI / 2;

  const panel = new THREE.Mesh(new THREE.BoxGeometry(0.075, 2.05, panelWidth), materials.wood);
  panel.name = `${name} paneled door slab`;
  panel.position.set(0, y + 1.08, panelWidth * 0.5);
  panel.castShadow = true;
  panel.receiveShadow = true;
  group.add(panel);

  for (const railZ of [panelWidth * 0.18, panelWidth * 0.82]) {
    const rail = new THREE.Mesh(new THREE.BoxGeometry(0.09, 1.74, 0.045), materials.windowFrame);
    rail.name = `${name} raised vertical rail`;
    rail.position.set(0.045, y + 1.08, railZ);
    rail.castShadow = true;
    group.add(rail);
  }
  for (const railY of [y + 0.43, y + 1.08, y + 1.73]) {
    const rail = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.045, panelWidth * 0.58), materials.windowFrame);
    rail.name = `${name} raised horizontal rail`;
    rail.position.set(0.045, railY, panelWidth * 0.5);
    rail.castShadow = true;
    group.add(rail);
  }
  for (const sideX of [-0.065, 0.065]) {
    const knob = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.065, 0.055, 20), materials.handle);
    knob.name = `${name} ${sideX < 0 ? "hall" : "room"} knob`;
    knob.rotation.z = Math.PI / 2;
    knob.position.set(sideX, y + 1.06, panelWidth * 0.76);
    knob.castShadow = true;
    group.add(knob);
  }

  scene.add(group);
  return registerInteriorDoor(name, group, x, z, 0.24, panelWidth, floor, label);
}

function createXWallInteriorDoor(name, z, x, width, floor = 1, swingSign = 1, label = name) {
  const y = floorBase(floor);
  const panelWidth = width * 0.82;
  const group = new THREE.Group();
  group.name = name;
  group.position.set(x - width * 0.5, 0, z);
  group.userData.closedRotation = 0;
  group.userData.openRotation = swingSign * Math.PI / 2;

  const panel = new THREE.Mesh(new THREE.BoxGeometry(panelWidth, 2.05, 0.075), materials.wood);
  panel.name = `${name} paneled door slab`;
  panel.position.set(panelWidth * 0.5, y + 1.08, 0);
  panel.castShadow = true;
  panel.receiveShadow = true;
  group.add(panel);

  for (const railX of [panelWidth * 0.18, panelWidth * 0.82]) {
    const rail = new THREE.Mesh(new THREE.BoxGeometry(0.045, 1.74, 0.09), materials.windowFrame);
    rail.name = `${name} raised vertical rail`;
    rail.position.set(railX, y + 1.08, 0.045);
    rail.castShadow = true;
    group.add(rail);
  }
  for (const railY of [y + 0.43, y + 1.08, y + 1.73]) {
    const rail = new THREE.Mesh(new THREE.BoxGeometry(panelWidth * 0.58, 0.045, 0.09), materials.windowFrame);
    rail.name = `${name} raised horizontal rail`;
    rail.position.set(panelWidth * 0.5, railY, 0.045);
    rail.castShadow = true;
    group.add(rail);
  }
  for (const sideZ of [-0.065, 0.065]) {
    const knob = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.065, 0.055, 20), materials.handle);
    knob.name = `${name} ${sideZ < 0 ? "front" : "back"} knob`;
    knob.rotation.x = Math.PI / 2;
    knob.position.set(panelWidth * 0.76, y + 1.06, sideZ);
    knob.castShadow = true;
    group.add(knob);
  }

  scene.add(group);
  return registerInteriorDoor(name, group, x, z, panelWidth, 0.24, floor, label);
}

function makeImportedAssetMaterials(root, options = {}) {
  const opacity = options.opacity ?? 1;
  let meshCount = 0;
  root.traverse((node) => {
    if (!node.isMesh) return;
    meshCount += 1;
    node.castShadow = true;
    node.receiveShadow = true;
    if (opacity < 1) {
      const cloneMaterial = (mat) => {
        if (!mat) return mat;
        const next = mat.clone();
        next.transparent = true;
        next.opacity = opacity;
        next.depthWrite = false;
        return next;
      };
      node.material = Array.isArray(node.material) ? node.material.map(cloneMaterial) : cloneMaterial(node.material);
      node.renderOrder = -1;
    }
  });
  return meshCount;
}

function fitObjectToBox(root, target) {
  root.updateMatrixWorld(true);
  const bounds = new THREE.Box3().setFromObject(root);
  const size = bounds.getSize(new THREE.Vector3());
  const scaleX = size.x > 0 ? target.width / size.x : 1;
  const scaleY = size.y > 0 ? target.height / size.y : scaleX;
  const scaleZ = size.z > 0 ? target.depth / size.z : scaleX;
  if (target.uniform) {
    const uniform = Math.min(scaleX, scaleY, scaleZ);
    root.scale.multiplyScalar(uniform);
  } else {
    root.scale.set(root.scale.x * scaleX, root.scale.y * scaleY, root.scale.z * scaleZ);
  }
  root.updateMatrixWorld(true);
  const scaledBounds = new THREE.Box3().setFromObject(root);
  const center = scaledBounds.getCenter(new THREE.Vector3());
  root.position.add(new THREE.Vector3(target.x - center.x, target.y - scaledBounds.min.y, target.z - center.z));
  root.updateMatrixWorld(true);
  return scaledBounds.getSize(new THREE.Vector3());
}

function meshOnlyWorldBounds(root) {
  root.updateMatrixWorld(true);
  const bounds = new THREE.Box3();
  const meshBounds = new THREE.Box3();
  let found = false;
  root.traverse((node) => {
    if (!node.isMesh || !node.geometry) return;
    if (!node.geometry.boundingBox) node.geometry.computeBoundingBox();
    if (!node.geometry.boundingBox) return;
    meshBounds.copy(node.geometry.boundingBox).applyMatrix4(node.matrixWorld);
    if (!Number.isFinite(meshBounds.min.x) || !Number.isFinite(meshBounds.max.x)) return;
    if (!found) {
      bounds.copy(meshBounds);
      found = true;
    } else {
      bounds.union(meshBounds);
    }
  });
  return found ? bounds : null;
}

function fitObjectToMeshBox(root, target) {
  root.updateMatrixWorld(true);
  const bounds = meshOnlyWorldBounds(root) || new THREE.Box3().setFromObject(root);
  const size = bounds.getSize(new THREE.Vector3());
  const scaleX = size.x > 0 ? target.width / size.x : 1;
  const scaleY = size.y > 0 ? target.height / size.y : scaleX;
  const scaleZ = size.z > 0 ? target.depth / size.z : scaleX;
  if (target.uniform) {
    const uniform = Math.min(scaleX, scaleY, scaleZ);
    root.scale.multiplyScalar(uniform);
  } else {
    root.scale.set(root.scale.x * scaleX, root.scale.y * scaleY, root.scale.z * scaleZ);
  }
  root.updateMatrixWorld(true);
  const scaledBounds = meshOnlyWorldBounds(root) || new THREE.Box3().setFromObject(root);
  const center = scaledBounds.getCenter(new THREE.Vector3());
  root.position.add(new THREE.Vector3(target.x - center.x, target.y - scaledBounds.min.y, target.z - center.z));
  root.updateMatrixWorld(true);
  const finalBounds = meshOnlyWorldBounds(root) || new THREE.Box3().setFromObject(root);
  return finalBounds.getSize(new THREE.Vector3());
}

function loadImportedHouseReference() {
  gltfLoader.load(
    REALISTIC_HOUSE_MODEL_URL,
    (gltf) => {
      const root = gltf.scene;
      root.name = "imported realistic Harbour Terrace house reference shell";
      const meshCount = makeImportedAssetMaterials(root, { opacity: 0.18 });
      scene.add(root);
      const fittedSize = fitObjectToBox(root, {
        x: 0,
        y: 0.02,
        z: 0,
        width: 17.4,
        height: 6.1,
        depth: 16.6,
        uniform: false,
      });
      importedHouseReference = root;
      importedHouseReferenceStatus = {
        loaded: true,
        url: REALISTIC_HOUSE_MODEL_URL,
        meshCount,
        fittedSize: {
          x: Number(fittedSize.x.toFixed(2)),
          y: Number(fittedSize.y.toFixed(2)),
          z: Number(fittedSize.z.toFixed(2)),
        },
      };
      removeSuppressedDownstairsToiletObjects();
    },
    undefined,
    (error) => {
      importedHouseReferenceStatus = {
        loaded: false,
        url: REALISTIC_HOUSE_MODEL_URL,
        error: error?.message || String(error),
      };
      console.warn("Could not load imported house reference model", error);
    },
  );
}

function addGableRoof(name, x, y, z, width, depth, height, material) {
  const halfW = width / 2;
  const halfD = depth / 2;
  const positions = new Float32Array([
    -halfW, 0, -halfD,
    halfW, 0, -halfD,
    0, height, -halfD,
    -halfW, 0, halfD,
    halfW, 0, halfD,
    0, height, halfD,
  ]);
  const indices = [
    0, 1, 2,
    3, 5, 4,
    0, 3, 1,
    1, 3, 4,
    0, 2, 3,
    2, 5, 3,
    1, 4, 2,
    2, 4, 5,
  ];
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  const roof = new THREE.Mesh(geometry, material);
  roof.name = name;
  roof.position.set(x, y, z);
  roof.castShadow = true;
  roof.receiveShadow = true;
  scene.add(roof);
  return roof;
}

function addNeighborFacadeWindow(name, x, y, z, width = 1.22, height = 1.22, zSign = 1) {
  const surfaceZ = z + zSign * 0.035;
  addBox(`${name} glass pane`, x, y, surfaceZ + zSign * 0.015, width, height, 0.035, materials.glass, false);
  addBox(`${name} left casing`, x - width * 0.5 - 0.055, y, surfaceZ + zSign * 0.035, 0.07, height + 0.22, 0.08, materials.windowFrame, false);
  addBox(`${name} right casing`, x + width * 0.5 + 0.055, y, surfaceZ + zSign * 0.035, 0.07, height + 0.22, 0.08, materials.windowFrame, false);
  addBox(`${name} top casing`, x, y + height * 0.5 + 0.055, surfaceZ + zSign * 0.035, width + 0.22, 0.07, 0.08, materials.windowFrame, false);
  addBox(`${name} bottom casing`, x, y - height * 0.5 - 0.055, surfaceZ + zSign * 0.035, width + 0.22, 0.07, 0.08, materials.windowFrame, false);
  addBox(`${name} mullion vertical`, x, y, surfaceZ + zSign * 0.052, 0.055, height * 0.96, 0.07, materials.windowFrame, false);
  addBox(`${name} mullion horizontal`, x, y, surfaceZ + zSign * 0.052, width * 0.96, 0.055, 0.07, materials.windowFrame, false);
  addBox(`${name} sill`, x, y - height * 0.5 - 0.17, surfaceZ + zSign * 0.08, width + 0.38, 0.09, 0.22, materials.neighborStone, false);
  addBox(`${name} left shutter`, x - width * 0.5 - 0.24, y, surfaceZ + zSign * 0.055, 0.18, height + 0.05, 0.075, materials.neighborShutter, false);
  addBox(`${name} right shutter`, x + width * 0.5 + 0.24, y, surfaceZ + zSign * 0.055, 0.18, height + 0.05, 0.075, materials.neighborShutter, false);
}

function addNeighborSideWindow(name, x, y, z, width = 1.1, height = 1.18, xSign = 1) {
  const surfaceX = x + xSign * 0.035;
  addBox(`${name} glass pane`, surfaceX + xSign * 0.015, y, z, 0.035, height, width, materials.glass, false);
  addBox(`${name} left casing`, surfaceX + xSign * 0.035, y, z - width * 0.5 - 0.055, 0.08, height + 0.22, 0.07, materials.windowFrame, false);
  addBox(`${name} right casing`, surfaceX + xSign * 0.035, y, z + width * 0.5 + 0.055, 0.08, height + 0.22, 0.07, materials.windowFrame, false);
  addBox(`${name} top casing`, surfaceX + xSign * 0.035, y + height * 0.5 + 0.055, z, 0.08, 0.07, width + 0.22, materials.windowFrame, false);
  addBox(`${name} bottom casing`, surfaceX + xSign * 0.035, y - height * 0.5 - 0.055, z, 0.08, 0.07, width + 0.22, materials.windowFrame, false);
  addBox(`${name} mullion vertical`, surfaceX + xSign * 0.052, y, z, 0.07, height * 0.96, 0.055, materials.windowFrame, false);
  addBox(`${name} mullion horizontal`, surfaceX + xSign * 0.052, y, z, 0.07, 0.055, width * 0.96, materials.windowFrame, false);
  addBox(`${name} sill`, surfaceX + xSign * 0.08, y - height * 0.5 - 0.17, z, 0.22, 0.09, width + 0.38, materials.neighborStone, false);
}

function addNeighborSidingBands(label, cx, cz, width, depth) {
  const frontZ = cz + depth / 2 + 0.045;
  const backZ = cz - depth / 2 - 0.045;
  const leftX = cx - width / 2 - 0.045;
  const rightX = cx + width / 2 + 0.045;
  for (let y = 0.98; y <= 4.95; y += 0.36) {
    addBox(`${label} front horizontal siding band`, cx, y, frontZ, width + 0.1, 0.035, 0.035, materials.neighborSidingWarm, false);
    addBox(`${label} rear horizontal siding band`, cx, y, backZ, width + 0.1, 0.035, 0.035, materials.neighborSidingWarm, false);
    addBox(`${label} left horizontal siding band`, leftX, y, cz, 0.035, 0.035, depth + 0.1, materials.neighborSidingWarm, false);
    addBox(`${label} right horizontal siding band`, rightX, y, cz, 0.035, 0.035, depth + 0.1, materials.neighborSidingWarm, false);
  }
}

function addNeighborMasonryBase(label, cx, cz, width, depth) {
  const frontZ = cz + depth / 2 + 0.07;
  const backZ = cz - depth / 2 - 0.07;
  addBox(`${label} stone base front`, cx, 0.34, frontZ, width + 0.22, 0.54, 0.14, materials.neighborStone, false);
  addBox(`${label} stone base rear`, cx, 0.34, backZ, width + 0.22, 0.54, 0.14, materials.neighborStone, false);
  addBox(`${label} stone base left`, cx - width / 2 - 0.07, 0.34, cz, 0.14, 0.54, depth + 0.22, materials.neighborStone, false);
  addBox(`${label} stone base right`, cx + width / 2 + 0.07, 0.34, cz, 0.14, 0.54, depth + 0.22, materials.neighborStone, false);
  for (let i = 0; i < 12; i += 1) {
    const x = cx - width / 2 + 0.62 + i * 0.86;
    addBox(`${label} front individual stone joint`, x, 0.34, frontZ + 0.075, 0.045, 0.46, 0.025, materials.windowFrame, false);
  }
}

function addNeighborLongWallWithOpenings(name, z, leftX, rightX, baseY, height, thickness, material, openings = [], floor = 0) {
  const topY = baseY + height;
  const sorted = openings
    .map((opening) => ({
      ...opening,
      left: Math.max(leftX, opening.x - opening.width * 0.5),
      right: Math.min(rightX, opening.x + opening.width * 0.5),
      bottom: Math.max(baseY, opening.bottom ?? baseY),
      top: Math.min(topY, opening.top ?? topY),
    }))
    .filter((opening) => opening.right > opening.left)
    .sort((a, b) => a.left - b.left);
  let cursor = leftX;
  const addSegment = (label, x1, x2, y1, y2, collider = true) => {
    if (x2 - x1 < 0.04 || y2 - y1 < 0.04) return;
    addBox(`${name} ${label}`, (x1 + x2) * 0.5, (y1 + y2) * 0.5, z, x2 - x1, y2 - y1, thickness, material, collider, floor);
  };
  sorted.forEach((opening, index) => {
    addSegment(`solid bay ${index + 1}`, cursor, opening.left, baseY, topY);
    addSegment(`below opening ${index + 1}`, opening.left, opening.right, baseY, opening.bottom, false);
    addSegment(`above opening ${index + 1}`, opening.left, opening.right, opening.top, topY, false);
    if (opening.blockCollider) colliders.push({ x: opening.x, z, sx: opening.width, sz: thickness + 0.24, floor });
    cursor = Math.max(cursor, opening.right);
  });
  addSegment("solid bay final", cursor, rightX, baseY, topY);
}

function addNeighborSideWallWithOpenings(name, x, backZ, frontZ, baseY, height, thickness, material, openings = [], floor = 0) {
  const topY = baseY + height;
  const sorted = openings
    .map((opening) => ({
      ...opening,
      back: Math.max(backZ, opening.z - opening.width * 0.5),
      front: Math.min(frontZ, opening.z + opening.width * 0.5),
      bottom: Math.max(baseY, opening.bottom ?? baseY),
      top: Math.min(topY, opening.top ?? topY),
    }))
    .filter((opening) => opening.front > opening.back)
    .sort((a, b) => a.back - b.back);
  let cursor = backZ;
  const addSegment = (label, z1, z2, y1, y2, collider = true) => {
    if (z2 - z1 < 0.04 || y2 - y1 < 0.04) return;
    addBox(`${name} ${label}`, x, (y1 + y2) * 0.5, (z1 + z2) * 0.5, thickness, y2 - y1, z2 - z1, material, collider, floor);
  };
  sorted.forEach((opening, index) => {
    addSegment(`solid bay ${index + 1}`, cursor, opening.back, baseY, topY);
    addSegment(`below opening ${index + 1}`, opening.back, opening.front, baseY, opening.bottom, false);
    addSegment(`above opening ${index + 1}`, opening.back, opening.front, opening.top, topY, false);
    if (opening.blockCollider) colliders.push({ x, z: opening.z, sx: thickness + 0.24, sz: opening.width, floor });
    cursor = Math.max(cursor, opening.front);
  });
  addSegment("solid bay final", cursor, frontZ, baseY, topY);
}

function addNeighborInteriorWall(name, x, z, sx, sz) {
  addBox(name, x, 1.3, z, sx, 2.35, sz, materials.wall, false);
  addBox(`${name} base trim`, x, 0.18, z, sx + (sx < sz ? 0.02 : 0), 0.08, sz + (sx >= sz ? 0.02 : 0), materials.windowFrame, false);
  addBox(`${name} crown trim`, x, 2.52, z, sx + (sx < sz ? 0.02 : 0), 0.08, sz + (sx >= sz ? 0.02 : 0), materials.windowFrame, false);
}

function addNeighborInteriorDoor(name, x, z, axis = "z") {
  const alongX = axis === "x";
  addBox(`${name} panel`, x, 1.03, z, alongX ? 0.88 : 0.055, 1.92, alongX ? 0.055 : 0.88, materials.neighborDoorWood, false);
  addBox(`${name} frame top`, x, 2.04, z, alongX ? 1.02 : 0.08, 0.08, alongX ? 0.08 : 1.02, materials.windowFrame, false);
  addBox(`${name} left frame`, x + (alongX ? -0.5 : 0), 1.08, z + (alongX ? 0 : -0.5), alongX ? 0.07 : 0.08, 2.0, alongX ? 0.08 : 0.07, materials.windowFrame, false);
  addBox(`${name} right frame`, x + (alongX ? 0.5 : 0), 1.08, z + (alongX ? 0 : 0.5), alongX ? 0.07 : 0.08, 2.0, alongX ? 0.08 : 0.07, materials.windowFrame, false);
  addBox(`${name} brass handle`, x + (alongX ? 0.3 : 0.045), 1.03, z + (alongX ? 0.045 : 0.3), 0.06, 0.16, 0.06, materials.handle, false);
}

function addNeighborBookRow(prefix, x, y, z, count = 12) {
  const bookMaterials = [materials.bookRed, materials.bookBlue, materials.bookGreen, materials.bookGold, materials.mediaCase];
  let cursor = x - (count * 0.13) / 2;
  for (let i = 0; i < count; i += 1) {
    const w = 0.07 + (i % 4) * 0.018;
    const h = 0.34 + (i % 3) * 0.04;
    const book = addBox(`${prefix} book ${i + 1}`, cursor, y + h * 0.5, z, w, h, 0.16, bookMaterials[i % bookMaterials.length], false);
    markTruthProp(book, "book", `${prefix} readable book ${i + 1}`, 0, ["read", "carry"]);
    cursor += w + 0.035;
  }
}

function addNeighborBookshelf(name, x, z) {
  addBox(`${name} wood back`, x, 1.05, z, 1.45, 1.9, 0.16, materials.libraryWood, false);
  addBox(`${name} left side`, x - 0.77, 1.05, z, 0.08, 1.95, 0.28, materials.libraryWood, false);
  addBox(`${name} right side`, x + 0.77, 1.05, z, 0.08, 1.95, 0.28, materials.libraryWood, false);
  for (let shelf = 0; shelf < 5; shelf += 1) {
    const y = 0.28 + shelf * 0.37;
    addBox(`${name} shelf ${shelf + 1}`, x, y, z - 0.02, 1.55, 0.06, 0.32, materials.libraryWood, false);
    if (shelf < 4) addNeighborBookRow(`${name} shelf ${shelf + 1}`, x, y + 0.04, z + 0.08, shelf === 0 ? 10 : 12);
  }
}

function addNeighborBed(name, x, z, accentMaterial = materials.blanketBlue) {
  addFloorTile(`${name} bedside rug`, x, z + 0.15, 2.15, 2.6, materials.rugWarm, 0.081);
  addBox(`${name} wood bed frame`, x, 0.25, z, 1.55, 0.34, 2.2, materials.livingWood, false);
  addBox(`${name} mattress`, x, 0.47, z + 0.08, 1.42, 0.26, 1.95, materials.mattress, false);
  addBox(`${name} blanket`, x, 0.63, z + 0.32, 1.32, 0.12, 1.15, accentMaterial, false);
  addBox(`${name} headboard`, x, 0.82, z - 1.05, 1.64, 1.08, 0.12, materials.livingWood, false);
  addBox(`${name} left pillow`, x - 0.36, 0.68, z - 0.67, 0.48, 0.15, 0.34, materials.paper, false);
  addBox(`${name} right pillow`, x + 0.36, 0.68, z - 0.67, 0.48, 0.15, 0.34, materials.paper, false);
  addBox(`${name} nightstand`, x - 1.05, 0.38, z - 0.64, 0.46, 0.55, 0.46, materials.warmCabinet, false);
  addBox(`${name} lamp shade`, x - 1.05, 0.86, z - 0.64, 0.32, 0.28, 0.32, materials.lampShade, false);
  addCylinder(`${name} lamp stem`, x - 1.05, 0.66, z - 0.64, 0.035, 0.38, materials.handle, false);
}

function addNeighborSofaGroup(x, z) {
  addFloorTile("neighbor living room woven rug", x, z - 0.2, 3.15, 2.05, materials.rugWarm, 0.081);
  addBox("neighbor living room sofa seat cushion base", x, 0.43, z, 2.55, 0.36, 0.82, materials.neighborShutter, false);
  addBox("neighbor living room sofa back", x, 0.85, z + 0.42, 2.65, 1.0, 0.18, materials.neighborShutter, false);
  addBox("neighbor living room sofa left arm", x - 1.42, 0.66, z, 0.22, 0.78, 0.92, materials.neighborShutter, false);
  addBox("neighbor living room sofa right arm", x + 1.42, 0.66, z, 0.22, 0.78, 0.92, materials.neighborShutter, false);
  for (let i = 0; i < 3; i += 1) {
    addBox(`neighbor living room separate sofa cushion ${i + 1}`, x - 0.82 + i * 0.82, 0.64, z - 0.04, 0.72, 0.12, 0.72, materials.secondFloor, false);
  }
  addBox("neighbor sofa gold throw pillow", x - 0.82, 0.92, z + 0.23, 0.36, 0.32, 0.12, materials.pillowGold, false);
  addBox("neighbor sofa coral throw pillow", x + 0.82, 0.92, z + 0.23, 0.36, 0.32, 0.12, materials.pillowCoral, false);
  addBox("neighbor coffee table wood top", x, 0.34, z - 1.05, 1.35, 0.12, 0.65, materials.livingWood, false);
  for (const lx of [-0.52, 0.52]) for (const lz of [-0.22, 0.22]) addCylinder("neighbor coffee table tapered leg", x + lx, 0.18, z - 1.05 + lz, 0.035, 0.28, materials.livingWood, false);
  addBox("neighbor slim media console", x + 2.05, 0.42, z - 0.05, 0.38, 0.54, 1.85, materials.livingWood, false);
  addBox("neighbor wall mounted tv visible from window", x + 2.26, 1.32, z - 0.05, 0.08, 0.86, 1.45, materials.screen, false);
}

function addNeighborDiningSet(x, z) {
  addFloorTile("neighbor dining room rug", x, z, 2.65, 2.25, materials.rugBorder, 0.082);
  addBox("neighbor dining table wood top", x, 0.73, z, 1.75, 0.12, 1.04, materials.livingWood, false);
  for (const lx of [-0.72, 0.72]) for (const lz of [-0.37, 0.37]) addCylinder("neighbor dining table round leg", x + lx, 0.39, z + lz, 0.045, 0.62, materials.livingWood, false);
  const chairs = [
    [x - 1.18, z, 0.45, 0.5],
    [x + 1.18, z, 0.45, 0.5],
    [x, z - 0.82, 0.5, 0.45],
    [x, z + 0.82, 0.5, 0.45],
  ];
  chairs.forEach(([cx, cz, sx, sz], index) => {
    addBox(`neighbor dining chair ${index + 1} seat`, cx, 0.47, cz, sx, 0.14, sz, materials.warmCabinet, false);
    addBox(`neighbor dining chair ${index + 1} back`, cx, 0.88, cz + (index === 2 ? -0.25 : index === 3 ? 0.25 : 0), sx, 0.72, 0.08, materials.warmCabinet, false);
  });
  for (let i = 0; i < 4; i += 1) {
    addCylinder(`neighbor dining plate ${i + 1}`, x - 0.54 + (i % 2) * 1.08, 0.82, z - 0.25 + Math.floor(i / 2) * 0.5, 0.14, 0.025, materials.fixture, false);
  }
  addBox("neighbor dining pendant shade", x, 1.92, z, 0.55, 0.24, 0.55, materials.lampShade, false);
}

function addNeighborKitchen(x, z) {
  addFloorTile("neighbor kitchen tile floor inset", x + 0.45, z - 0.3, 4.25, 3.35, materials.sidewalk, 0.083);
  addBox("neighbor kitchen rear counter run", x + 0.55, 0.58, z - 1.15, 3.85, 0.72, 0.62, materials.counter, false);
  addBox("neighbor kitchen rear cabinet faces", x + 0.55, 0.42, z - 0.8, 3.75, 0.58, 0.08, materials.warmCabinet, false);
  for (let i = 0; i < 5; i += 1) addBox(`neighbor kitchen rear cabinet pull ${i + 1}`, x - 1.15 + i * 0.62, 0.48, z - 0.74, 0.18, 0.035, 0.035, materials.handle, false);
  addBox("neighbor kitchen left counter run", x - 1.62, 0.58, z + 0.35, 0.62, 0.72, 2.95, materials.counter, false);
  addBox("neighbor kitchen backsplash marble", x + 0.55, 1.06, z - 0.8, 3.86, 0.62, 0.08, materials.wall, false);
  addBox("neighbor kitchen upper cabinet row", x + 0.55, 1.62, z - 0.82, 3.65, 0.72, 0.28, materials.warmCabinet, false);
  addBox("neighbor kitchen fridge realistic white body", x + 2.75, 1.0, z - 0.98, 0.82, 1.86, 0.68, materials.fridgeWhite, false);
  addBox("neighbor kitchen fridge dark side seam", x + 2.75, 1.05, z - 0.62, 0.72, 1.58, 0.035, materials.windowFrame, false);
  addBox("neighbor kitchen stove stainless front", x - 0.55, 0.72, z - 0.78, 0.72, 0.78, 0.12, materials.brushedSteel, false);
  addCylinder("neighbor kitchen left burner", x - 0.73, 1.0, z - 1.15, 0.13, 0.025, materials.burnerBlack, false);
  addCylinder("neighbor kitchen right burner", x - 0.38, 1.0, z - 1.15, 0.13, 0.025, materials.burnerBlack, false);
  addBox("neighbor kitchen sink basin", x + 0.5, 0.97, z - 1.12, 0.62, 0.08, 0.36, materials.brushedSteel, false);
  addCylinder("neighbor kitchen faucet", x + 0.5, 1.17, z - 1.2, 0.035, 0.32, materials.handle, false);
  addBox("neighbor kitchen island wood base", x + 0.58, 0.55, z + 0.78, 1.55, 0.72, 0.72, materials.warmCabinet, false);
  addBox("neighbor kitchen island stone top", x + 0.58, 0.94, z + 0.78, 1.72, 0.12, 0.88, materials.counter, false);
}

function addNeighborDesk(name, x, z) {
  addBox(`${name} desktop`, x, 0.73, z, 1.28, 0.12, 0.56, materials.livingWood, false);
  addBox(`${name} left drawer stack`, x - 0.44, 0.43, z, 0.28, 0.52, 0.48, materials.warmCabinet, false);
  addBox(`${name} chair seat`, x, 0.43, z + 0.76, 0.52, 0.14, 0.48, materials.trim, false);
  addBox(`${name} chair back`, x, 0.84, z + 0.98, 0.52, 0.72, 0.08, materials.trim, false);
  const notebook = addBox(`${name} open notebook`, x + 0.25, 0.83, z - 0.08, 0.5, 0.035, 0.34, materials.paper, false);
  markTruthProp(notebook, "notebook", `${name} writing notebook`, 0, ["write", "sketch"]);
  addBox(`${name} laptop screen`, x - 0.32, 1.03, z - 0.16, 0.46, 0.36, 0.035, materials.screen, false);
}

function addNeighborBathroom(name, x, z) {
  addFloorTile(`${name} tiled floor`, x, z, 2.05, 1.75, materials.sidewalk, 0.084);
  addBox(`${name} vanity cabinet`, x - 0.55, 0.48, z - 0.48, 0.86, 0.72, 0.48, materials.warmCabinet, false);
  addBox(`${name} vanity sink`, x - 0.55, 0.9, z - 0.48, 0.72, 0.12, 0.38, materials.fixture, false);
  addBox(`${name} mirror`, x - 0.55, 1.55, z - 0.78, 0.78, 0.72, 0.04, materials.mirror, false);
  addBox(`${name} toilet tank`, x + 0.58, 0.74, z - 0.58, 0.55, 0.52, 0.22, materials.fixture, false);
  addCylinder(`${name} toilet bowl`, x + 0.58, 0.46, z - 0.24, 0.25, 0.22, materials.fixture, false);
  addBox(`${name} bathtub`, x + 0.45, 0.43, z + 0.56, 1.18, 0.44, 0.52, materials.fixture, false);
  addBox(`${name} shower glass panel`, x - 0.12, 1.18, z + 0.82, 0.06, 1.3, 0.72, materials.transomGlass, false);
  addBox(`${name} towel`, x - 0.95, 1.23, z + 0.34, 0.08, 0.54, 0.42, materials.blanketBlue, false);
}

function addNeighborInteriorLayout(cx, cz, width, depth, doorX, frontZ) {
  addFloorTile("neighbor open foyer wood floor", doorX, frontZ - 1.05, 2.55, 2.25, materials.floor, 0.085);
  addFloorTile("neighbor living room warm wood floor", cx + 1.55, cz + 3.4, 4.7, 4.75, materials.floor, 0.086);
  addFloorTile("neighbor dining room wood floor", cx + 3.65, cz + 0.95, 2.95, 2.8, materials.floor, 0.087);
  addFloorTile("neighbor bedroom two wood floor", cx - 3.45, cz + 1.95, 3.75, 3.25, materials.floor, 0.087);
  addFloorTile("neighbor bedroom three wood floor", cx + 3.2, cz - 1.05, 3.9, 3.45, materials.floor, 0.087);
  addFloorTile("neighbor primary bedroom wood floor", cx - 2.15, cz - 3.2, 4.75, 3.25, materials.floor, 0.087);
  addNeighborInteriorWall("neighbor hallway wall between foyer and living room", cx - 0.45, cz + 3.2, 0.12, 4.3);
  addNeighborInteriorWall("neighbor bedroom two rear wall", cx - 3.55, cz + 0.22, 3.95, 0.12);
  addNeighborInteriorWall("neighbor bedroom wing center wall", cx - 0.42, cz - 2.0, 0.12, 4.45);
  addNeighborInteriorWall("neighbor bedroom three front wall", cx + 2.65, cz + 0.5, 3.7, 0.12);
  addNeighborInteriorWall("neighbor bathroom privacy wall", cx + 0.7, cz - 0.62, 0.12, 2.35);
  addNeighborInteriorDoor("neighbor bedroom two real door", cx - 1.6, cz + 0.22, "z");
  addNeighborInteriorDoor("neighbor bedroom three real door", cx + 1.35, cz + 0.5, "z");
  addNeighborInteriorDoor("neighbor primary bedroom real door", cx - 0.42, cz - 0.8, "x");
  addNeighborInteriorDoor("neighbor bathroom real door", cx + 0.7, cz + 0.42, "x");
  addNeighborSofaGroup(cx + 2.05, cz + 4.05);
  addNeighborDiningSet(cx + 3.6, cz + 1.15);
  addNeighborKitchen(cx - 2.8, cz - 1.15);
  addNeighborBed("neighbor primary bedroom queen bed", cx - 2.65, cz - 3.25, materials.blanketBlue);
  addNeighborBed("neighbor bedroom two twin bed", cx - 3.65, cz + 1.8, materials.blanketPink);
  addNeighborBed("neighbor bedroom three twin bed", cx + 3.15, cz - 1.25, materials.pillowGold);
  addNeighborDesk("neighbor bedroom two homework desk", cx - 4.62, cz + 3.4);
  addNeighborDesk("neighbor bedroom three writing desk", cx + 4.68, cz + 0.38);
  addNeighborBookshelf("neighbor living room built-in bookshelf", cx + 4.55, cz + 3.95);
  addNeighborBathroom("neighbor compact full bathroom", cx + 0.98, cz - 1.35);
}

function loadNeighborEntryDoorReference(doorX, frontZ) {
  gltfLoader.load(
    NEIGHBOR_ENTRY_DOOR_MODEL_URL,
    (gltf) => {
      const root = gltf.scene;
      root.name = "neighbor imported entry door with sidelights";
      const meshCount = makeImportedAssetMaterials(root);
      root.rotation.y = Math.PI;
      scene.add(root);
      const fittedSize = fitObjectToMeshBox(root, {
        x: doorX,
        y: 0.08,
        z: frontZ + 0.12,
        width: 1.85,
        height: 2.55,
        depth: 0.2,
        uniform: false,
      });
      neighborEntryDoorReference = root;
      setNeighborHouseDoorOpen(neighborHouseDoorOpen);
      neighborHouseReferenceStatus = {
        ...neighborHouseReferenceStatus,
        loaded: true,
        entryDoorLoaded: true,
        entryDoorMeshCount: meshCount,
        fittedEntryDoorSize: {
          x: Number(fittedSize.x.toFixed(2)),
          y: Number(fittedSize.y.toFixed(2)),
          z: Number(fittedSize.z.toFixed(2)),
        },
        designReferences: [
          "enterable_panel_house_light.glb for full-house massing",
          "entry_door_with_sidelights.glb for the front entry",
          "seamless_brick_wall_texture_light.glb for masonry/material direction",
        ],
      };
    },
    undefined,
    (error) => {
      neighborHouseReferenceStatus = {
        ...neighborHouseReferenceStatus,
        loaded: false,
        entryDoorLoaded: false,
        error: error?.message || String(error),
      };
      console.warn("Could not load neighbor entry door model", error);
    },
  );
}

function placeNeighborImportedBed(placement) {
  if (!neighborBedReferenceSource) {
    pendingNeighborBedPlacements.push(placement);
    loadNeighborBedReference();
    return false;
  }
  const root = neighborBedReferenceSource.clone(true);
  root.name = placement.name;
  makeImportedAssetMaterials(root);
  root.rotation.y = placement.yaw || 0;
  scene.add(root);
  const fittedSize = fitObjectToMeshBox(root, {
    x: placement.x,
    y: 0.1,
    z: placement.z,
    width: placement.width || 1.55,
    height: placement.height || 0.9,
    depth: placement.depth || 2.15,
    uniform: false,
  });
  root.userData.truthProp = {
    kind: "bed",
    label: placement.name,
    floor: 0,
    actionHints: ["sit", "sleep", "lay_down"],
  };
  activityTruthProps.push(root);
  neighborHouseReferenceStatus = {
    ...neighborHouseReferenceStatus,
    importedBedPlacements: (neighborHouseReferenceStatus.importedBedPlacements || 0) + 1,
    importedBedFittedSize: {
      x: Number(fittedSize.x.toFixed(2)),
      y: Number(fittedSize.y.toFixed(2)),
      z: Number(fittedSize.z.toFixed(2)),
    },
  };
  return true;
}

function findFirstNodeByPattern(root, pattern) {
  let match = null;
  root?.traverse?.((node) => {
    if (match) return;
    if (pattern.test(String(node.name || ""))) match = node;
  });
  return match;
}

function placeNeighborApartmentNode(placement) {
  if (!neighborApartmentReferenceScene) {
    pendingNeighborApartmentNodePlacements.push(placement);
    loadNeighborBedReference();
    return false;
  }
  const source = findFirstNodeByPattern(neighborApartmentReferenceScene, placement.pattern);
  if (!source) {
    neighborHouseReferenceStatus = {
      ...neighborHouseReferenceStatus,
      importedApartmentNodeMissing: String(placement.pattern),
    };
    return false;
  }
  const root = source.clone(true);
  root.name = placement.name;
  makeImportedAssetMaterials(root);
  root.rotation.y = placement.yaw || 0;
  scene.add(root);
  const fittedSize = fitObjectToMeshBox(root, {
    x: placement.x,
    y: 0.08,
    z: placement.z,
    width: placement.width,
    height: placement.height,
    depth: placement.depth,
    uniform: placement.uniform ?? true,
  });
  neighborHouseReferenceStatus = {
    ...neighborHouseReferenceStatus,
    importedApartmentFurniturePlacements: (neighborHouseReferenceStatus.importedApartmentFurniturePlacements || 0) + 1,
    importedApartmentFurnitureLast: {
      name: placement.name,
      x: Number(fittedSize.x.toFixed(2)),
      y: Number(fittedSize.y.toFixed(2)),
      z: Number(fittedSize.z.toFixed(2)),
    },
  };
  return true;
}

function placeNeighborDoorPanel(placement) {
  if (!neighborApartmentReferenceScene) {
    pendingNeighborDoorPanelPlacements.push(placement);
    loadNeighborBedReference();
    return false;
  }
  const source = findFirstNodeByPattern(neighborApartmentReferenceScene, placement.pattern || /Door_Panel_1_1/i);
  if (!source) {
    neighborHouseReferenceStatus = {
      ...neighborHouseReferenceStatus,
      importedDoorPanelMissing: String(placement.pattern || /Door_Panel_1_1/i),
    };
    return false;
  }
  const root = source.clone(true);
  root.name = placement.name;
  makeImportedAssetMaterials(root);
  root.rotation.y = placement.yaw || 0;
  scene.add(root);
  const fittedSize = fitObjectToMeshBox(root, {
    x: placement.x,
    y: placement.y ?? 0.08,
    z: placement.z,
    width: placement.width ?? 0.96,
    height: placement.height ?? 2.08,
    depth: placement.depth ?? 0.12,
    uniform: placement.uniform ?? false,
  });
  if (placement.frontDoorVisual) neighborImportedFrontDoorVisuals.push(root);
  neighborHouseReferenceStatus = {
    ...neighborHouseReferenceStatus,
    importedDoorPanelPlacements: (neighborHouseReferenceStatus.importedDoorPanelPlacements || 0) + 1,
    importedDoorPanelLast: {
      name: placement.name,
      x: Number(fittedSize.x.toFixed(2)),
      y: Number(fittedSize.y.toFixed(2)),
      z: Number(fittedSize.z.toFixed(2)),
    },
  };
  setNeighborHouseDoorOpen(neighborHouseDoorOpen);
  return true;
}

function placeNeighborPrefabWholeModel(url, placement) {
  const source = neighborPrefabSourceCache.get(url);
  if (!source) {
    if (!pendingNeighborPrefabPlacements.has(url)) pendingNeighborPrefabPlacements.set(url, []);
    pendingNeighborPrefabPlacements.get(url).push(placement);
    gltfLoader.load(
      url,
      (gltf) => {
        neighborPrefabSourceCache.set(url, gltf.scene);
        const queued = pendingNeighborPrefabPlacements.get(url) || [];
        pendingNeighborPrefabPlacements.delete(url);
        for (const item of queued) placeNeighborPrefabWholeModel(url, item);
      },
      undefined,
      (error) => {
        neighborHouseReferenceStatus = {
          ...neighborHouseReferenceStatus,
          prefabLoadErrors: [
            ...(neighborHouseReferenceStatus.prefabLoadErrors || []),
            { url, error: error?.message || String(error) },
          ],
        };
        console.warn("Could not load neighbor prefab model", url, error);
      },
    );
    return false;
  }
  const root = source.clone(true);
  root.name = placement.name;
  const meshCount = makeImportedAssetMaterials(root);
  if (placement.postProcess) placement.postProcess(root);
  root.rotation.y = placement.yaw || 0;
  scene.add(root);
  const fittedSize = fitObjectToMeshBox(root, {
    x: placement.x,
    y: placement.y ?? 0.08,
    z: placement.z,
    width: placement.width,
    height: placement.height,
    depth: placement.depth,
    uniform: placement.uniform ?? false,
  });
  if (placement.truthKind) {
    markTruthProp(root, placement.truthKind, placement.truthLabel || placement.name, placement.floor ?? 0, placement.actionHints || []);
  }
  neighborHouseReferenceStatus = {
    ...neighborHouseReferenceStatus,
    prefabPlacements: {
      ...(neighborHouseReferenceStatus.prefabPlacements || {}),
      [placement.role || placement.name]: {
        url,
        meshCount,
        x: Number(fittedSize.x.toFixed(2)),
        y: Number(fittedSize.y.toFixed(2)),
        z: Number(fittedSize.z.toFixed(2)),
      },
    },
  };
  return true;
}

function loadNeighborLivingRoomFurniture(x, z, yaw = 0) {
  gltfLoader.load(
    NEIGHBOR_LIVING_ROOM_FURNITURE_MODEL_URL,
    (gltf) => {
      const root = gltf.scene;
      root.name = "neighbor imported living room sofa chairs and props";
      const meshCount = makeImportedAssetMaterials(root);
      root.rotation.y = yaw;
      scene.add(root);
      const fittedSize = fitObjectToMeshBox(root, {
        x,
        y: 0.08,
        z,
        width: 3.9,
        height: 1.25,
        depth: 2.75,
        uniform: false,
      });
      neighborHouseReferenceStatus = {
        ...neighborHouseReferenceStatus,
        importedLivingRoomFurnitureLoaded: true,
        importedLivingRoomFurnitureMeshCount: meshCount,
        importedLivingRoomFurnitureFittedSize: {
          x: Number(fittedSize.x.toFixed(2)),
          y: Number(fittedSize.y.toFixed(2)),
          z: Number(fittedSize.z.toFixed(2)),
        },
      };
    },
    undefined,
    (error) => {
      neighborHouseReferenceStatus = {
        ...neighborHouseReferenceStatus,
        importedLivingRoomFurnitureLoaded: false,
        importedLivingRoomFurnitureError: error?.message || String(error),
      };
      console.warn("Could not load neighbor imported living room furniture", error);
    },
  );
}

function loadNeighborBedReference() {
  if (neighborBedReferenceSource || neighborBedReferenceLoading) return;
  neighborBedReferenceLoading = true;
  gltfLoader.load(
    NEIGHBOR_BED_SOURCE_MODEL_URL,
    (gltf) => {
      neighborApartmentReferenceScene = gltf.scene;
      let bedNode = null;
      gltf.scene.traverse((node) => {
        if (bedNode) return;
        if (/^BED_022_1$/i.test(String(node.name || ""))) bedNode = node;
      });
      if (!bedNode) {
        gltf.scene.traverse((node) => {
          if (bedNode) return;
          if (/bed|mattress/i.test(String(node.name || ""))) bedNode = node;
        });
      }
      neighborBedReferenceSource = bedNode || gltf.scene;
      const meshCount = makeImportedAssetMaterials(neighborBedReferenceSource);
      neighborBedReferenceLoading = false;
      neighborHouseReferenceStatus = {
        ...neighborHouseReferenceStatus,
        importedBedSourceLoaded: true,
        importedBedSourceName: neighborBedReferenceSource.name || "apartment layout bed source",
        importedBedMeshCount: meshCount,
      };
      while (pendingNeighborBedPlacements.length) {
        placeNeighborImportedBed(pendingNeighborBedPlacements.shift());
      }
      while (pendingNeighborApartmentNodePlacements.length) {
        placeNeighborApartmentNode(pendingNeighborApartmentNodePlacements.shift());
      }
      while (pendingNeighborDoorPanelPlacements.length) {
        placeNeighborDoorPanel(pendingNeighborDoorPanelPlacements.shift());
      }
    },
    undefined,
    (error) => {
      neighborBedReferenceLoading = false;
      neighborHouseReferenceStatus = {
        ...neighborHouseReferenceStatus,
        importedBedSourceLoaded: false,
        importedBedError: error?.message || String(error),
      };
      console.warn("Could not load neighbor imported bed source", error);
    },
  );
}

function hideImportedReferencePeople(root) {
  root?.traverse?.((node) => {
    const materialNames = Array.isArray(node.material)
      ? node.material.map((mat) => mat?.name || "").join(" ")
      : node.material?.name || "";
    const signature = `${node.name || ""} ${materialNames}`.toLowerCase();
    if (signature.includes("laura_") || signature.includes("laura skin") || signature.includes("laura hair")) {
      node.visible = false;
    }
  });
}

function collapseDownloadedHouseToGroundFloor(root) {
  const removable = [];
  const roofMeshes = [];
  const tempBox = new THREE.Box3();
  const tempCenter = new THREE.Vector3();
  root.updateMatrixWorld(true);
  root.traverse((node) => {
    if (!node.isMesh || !node.geometry) return;
    tempBox.setFromObject(node);
    tempBox.getCenter(tempCenter);
    const signature = `${node.name || ""} ${node.parent?.name || ""}`.toLowerCase();
    const isRoof = signature.includes("roof") || signature.includes("top_ceiling");
    const isStair = signature.includes("ltypestair") || signature.includes("railing") || signature.includes("object043");
    const isUpperFloor =
      tempCenter.y > 90
      || signature.includes("floors_2")
      || signature.includes("outside_top");
    if (isRoof) roofMeshes.push(node);
    else if (isStair || isUpperFloor) removable.push(node);
  });
  for (const node of removable) {
    node.parent?.remove(node);
  }
  root.updateMatrixWorld(true);
  const bodyBounds = new THREE.Box3();
  let foundBody = false;
  root.traverse((node) => {
    if (!node.isMesh || !node.geometry) return;
    if (roofMeshes.includes(node)) return;
    tempBox.setFromObject(node);
    if (!foundBody) {
      bodyBounds.copy(tempBox);
      foundBody = true;
    } else {
      bodyBounds.union(tempBox);
    }
  });
  if (!foundBody || !roofMeshes.length) return { removed: removable.length, loweredRoof: 0 };
  const roofBounds = new THREE.Box3();
  let foundRoof = false;
  for (const node of roofMeshes) {
    tempBox.setFromObject(node);
    if (!foundRoof) {
      roofBounds.copy(tempBox);
      foundRoof = true;
    } else {
      roofBounds.union(tempBox);
    }
  }
  if (!foundRoof) return { removed: removable.length, loweredRoof: 0 };
  const roofDeltaY = (bodyBounds.max.y - 12.0) - roofBounds.min.y;
  for (const node of roofMeshes) {
    if (node.geometry) {
      node.geometry = node.geometry.clone();
      node.geometry.translate(0, 0, roofDeltaY);
      node.geometry.computeBoundingBox();
      node.geometry.computeBoundingSphere();
    } else {
      node.position.y += roofDeltaY;
    }
  }
  root.updateMatrixWorld(true);
  return { removed: removable.length, loweredRoof: roofMeshes.length };
}

function placeKiraBungalowModel(url, placement) {
  const source = kiraBungalowSourceCache.get(url);
  if (!source) {
    if (!pendingKiraBungalowPlacements.has(url)) pendingKiraBungalowPlacements.set(url, []);
    pendingKiraBungalowPlacements.get(url).push(placement);
    gltfLoader.load(
      url,
      (gltf) => {
        kiraBungalowSourceCache.set(url, gltf.scene);
        const queued = pendingKiraBungalowPlacements.get(url) || [];
        pendingKiraBungalowPlacements.delete(url);
        for (const item of queued) placeKiraBungalowModel(url, item);
      },
      undefined,
      (error) => {
        kiraBungalowStatus = {
          ...kiraBungalowStatus,
          loadErrors: [
            ...(kiraBungalowStatus.loadErrors || []),
            { url, error: error?.message || String(error) },
          ],
        };
        console.warn("Could not load Kira bungalow model", url, error);
      },
    );
    return false;
  }

  const root = source.clone(true);
  root.name = placement.name;
  if (placement.hideReferencePeople) hideImportedReferencePeople(root);
  const groundFloorTransform = placement.singleStoryHouse ? collapseDownloadedHouseToGroundFloor(root) : null;
  const meshCount = makeImportedAssetMaterials(root);
  if (placement.rotation) {
    root.rotation.set(placement.rotation.x || 0, placement.rotation.y || 0, placement.rotation.z || 0);
  } else {
    root.rotation.y = placement.yaw || 0;
  }
  scene.add(root);
  const fittedSize = fitObjectToMeshBox(root, {
    x: placement.x,
    y: placement.y ?? 0.08,
    z: placement.z,
    width: placement.width,
    height: placement.height,
    depth: placement.depth,
    uniform: placement.uniform ?? false,
  });
  if (placement.portable) {
    root.userData.portable = true;
    root.userData.itemId = placement.itemId || root.name;
    root.userData.canStore = placement.canStore || [];
  }
  if (placement.truthKind) {
    markTruthProp(root, placement.truthKind, placement.truthLabel || placement.name, placement.floor ?? 0, placement.actionHints || []);
  }
  kiraBungalowStatus = {
    ...kiraBungalowStatus,
    loaded: true,
    placements: {
      ...(kiraBungalowStatus.placements || {}),
      [placement.role || placement.name]: {
        url,
        meshCount,
        singleStoryHouse: !!placement.singleStoryHouse,
        removedUpperMeshes: groundFloorTransform?.removed || 0,
        loweredRoofMeshes: groundFloorTransform?.loweredRoof || 0,
        x: Number(fittedSize.x.toFixed(2)),
        y: Number(fittedSize.y.toFixed(2)),
        z: Number(fittedSize.z.toFixed(2)),
      },
    },
  };
  return true;
}

function placeHomeWorldActivityModel(url, placement) {
  const source = homeWorldActivitySourceCache.get(url);
  if (!source) {
    if (!pendingHomeWorldActivityPlacements.has(url)) pendingHomeWorldActivityPlacements.set(url, []);
    pendingHomeWorldActivityPlacements.get(url).push(placement);
    gltfLoader.load(
      url,
      (gltf) => {
        homeWorldActivitySourceCache.set(url, { scene: gltf.scene, animations: gltf.animations || [] });
        const queued = pendingHomeWorldActivityPlacements.get(url) || [];
        pendingHomeWorldActivityPlacements.delete(url);
        for (const item of queued) placeHomeWorldActivityModel(url, item);
      },
      undefined,
      (error) => {
        homeWorldActivityStatus = {
          ...homeWorldActivityStatus,
          loadErrors: [
            ...(homeWorldActivityStatus.loadErrors || []),
            { url, error: error?.message || String(error) },
          ],
        };
        console.warn("Could not load Home World activity model", url, error);
      },
    );
    return false;
  }

  const root = source.scene.clone(true);
  root.name = placement.name;
  if (typeof placement.prepare === "function") placement.prepare(root, source);
  const meshCount = makeImportedAssetMaterials(root, placement.materialOptions || {});
  if (placement.rotation) root.rotation.set(placement.rotation.x || 0, placement.rotation.y || 0, placement.rotation.z || 0);
  else root.rotation.y = placement.yaw || 0;
  scene.add(root);
  const fittedSize = fitObjectToMeshBox(root, {
    x: placement.x,
    y: placement.y ?? 0.05,
    z: placement.z,
    width: placement.width,
    height: placement.height,
    depth: placement.depth,
    uniform: placement.uniform ?? true,
  });
  if (placement.collider) colliders.push({ x: placement.x, z: placement.z, sx: placement.collider.sx, sz: placement.collider.sz, floor: placement.collider.floor ?? 0 });
  if (placement.truthKind) markTruthProp(root, placement.truthKind, placement.truthLabel || placement.name, placement.floor ?? 0, placement.actionHints || []);
  if (typeof placement.onPlaced === "function") placement.onPlaced(root, source, fittedSize, meshCount);
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    [placement.role || placement.name]: {
      loaded: true,
      url,
      meshCount,
      x: Number(root.position.x.toFixed(2)),
      y: Number(root.position.y.toFixed(2)),
      z: Number(root.position.z.toFixed(2)),
      fittedSize: {
        x: Number(fittedSize.x.toFixed(2)),
        y: Number(fittedSize.y.toFixed(2)),
        z: Number(fittedSize.z.toFixed(2)),
      },
      removedOversizedSiteMeshes: root.userData?.removedOversizedSiteMeshes || 0,
    },
  };
  return root;
}

function prepareStarbucksBuildingOnly(root) {
  const siteMaterialNames = [
    "Concrete_Brushed6",
    "Vegetation_Grass1",
    "Asphalt_New_3",
    "Brick_Pavers_Fan",
    "Concrete_Brushed_Orange",
  ];
  const siteNodeNames = new Set(["Material2_36", "Material2_37", "Material2_38", "Material2_39", "Material3_15"]);
  const removeList = [];
  root.traverse((node) => {
    const isGuidePrimitive = node.isLine || node.isLineSegments || node.isPoints || /Line|Points/i.test(node.type || "");
    if (isGuidePrimitive) {
      removeList.push(node);
      return;
    }
    if (!node.isMesh) return;
    const materialNames = (Array.isArray(node.material) ? node.material : [node.material])
      .map((material) => material?.name || "")
      .join(" ");
    const isSiteMesh = siteNodeNames.has(node.name)
      || siteMaterialNames.some((name) => materialNames.includes(name));
    if (isSiteMesh) removeList.push(node);
  });
  for (const mesh of removeList) mesh.parent?.remove(mesh);
  root.userData.removedOversizedSiteMeshes = removeList.length;
  return removeList.length;
}

function pointInsideKiraBungalow(position, margin = 0.75) {
  if (!position) return false;
  return position.y < 1.8
    && position.x >= KIRA_BUNGALOW_LEFT_X - margin
    && position.x <= KIRA_BUNGALOW_RIGHT_X + margin
    && position.z >= KIRA_BUNGALOW_BACK_Z - margin
    && position.z <= KIRA_BUNGALOW_FRONT_Z + margin;
}

function addKiraBungalowColliders() {
  if (!KIRA_BUNGALOW_ENABLED) return;
  const frontGap = 2.75;
  const frontSegment = (KIRA_BUNGALOW_WIDTH - frontGap) / 2;
  colliders.push({ x: KIRA_BUNGALOW_LEFT_X + frontSegment / 2, z: KIRA_BUNGALOW_FRONT_Z, sx: frontSegment, sz: 0.28, floor: 0 });
  colliders.push({ x: KIRA_BUNGALOW_RIGHT_X - frontSegment / 2, z: KIRA_BUNGALOW_FRONT_Z, sx: frontSegment, sz: 0.28, floor: 0 });
  colliders.push({ x: KIRA_BUNGALOW_CENTER.x, z: KIRA_BUNGALOW_BACK_Z, sx: KIRA_BUNGALOW_WIDTH, sz: 0.28, floor: 0 });
  colliders.push({ x: KIRA_BUNGALOW_LEFT_X, z: KIRA_BUNGALOW_CENTER.z, sx: 0.28, sz: KIRA_BUNGALOW_DEPTH, floor: 0 });
  colliders.push({ x: KIRA_BUNGALOW_RIGHT_X, z: KIRA_BUNGALOW_CENTER.z, sx: 0.28, sz: KIRA_BUNGALOW_DEPTH, floor: 0 });
  colliders.push({ x: KIRA_BUNGALOW_CENTER.x - 2.9, z: KIRA_BUNGALOW_CENTER.z - 1.72, sx: 2.0, sz: 2.25, floor: 0 });
  colliders.push({ x: KIRA_BUNGALOW_CENTER.x + 2.55, z: KIRA_BUNGALOW_CENTER.z + 2.1, sx: 2.55, sz: 1.28, floor: 0 });
  colliders.push({ x: KIRA_BUNGALOW_CENTER.x + 0.92, z: KIRA_BUNGALOW_CENTER.z + 1.6, sx: 1.05, sz: 0.72, floor: 0 });
}

function setKiraBungalowDoorOpen(open = true) {
  kiraBungalowDoorOpen = !!open;
  if (kiraBungalowDoorLeaf) kiraBungalowDoorLeaf.rotation.y = kiraBungalowDoorOpen ? -Math.PI / 2 : 0;
  kiraBungalowStatus = {
    ...kiraBungalowStatus,
    frontDoor: {
      loaded: true,
      open: kiraBungalowDoorOpen,
      x: Number(KIRA_BUNGALOW_CENTER.x.toFixed(2)),
      z: Number(KIRA_BUNGALOW_FRONT_Z.toFixed(2)),
    },
  };
}

function addKiraBungalow() {
  if (!KIRA_BUNGALOW_ENABLED) return;
  addKiraBungalowColliders();
  addFloorTile("Kira temporary open studio wood floor", KIRA_BUNGALOW_CENTER.x, KIRA_BUNGALOW_CENTER.z, KIRA_BUNGALOW_WIDTH, KIRA_BUNGALOW_DEPTH, materials.floor, 0.024);
  addBox("Kira temporary studio back wall", KIRA_BUNGALOW_CENTER.x, 1.48, KIRA_BUNGALOW_BACK_Z, KIRA_BUNGALOW_WIDTH, 2.9, 0.18, materials.wall, true, 0);
  addBox("Kira temporary studio left wall", KIRA_BUNGALOW_LEFT_X, 1.48, KIRA_BUNGALOW_CENTER.z, 0.18, 2.9, KIRA_BUNGALOW_DEPTH, materials.wall, true, 0);
  addBox("Kira temporary studio right wall", KIRA_BUNGALOW_RIGHT_X, 1.48, KIRA_BUNGALOW_CENTER.z, 0.18, 2.9, KIRA_BUNGALOW_DEPTH, materials.wall, true, 0);
  const frontGap = 2.75;
  const frontSegment = (KIRA_BUNGALOW_WIDTH - frontGap) / 2;
  addBox("Kira temporary studio front wall left", KIRA_BUNGALOW_LEFT_X + frontSegment / 2, 1.48, KIRA_BUNGALOW_FRONT_Z, frontSegment, 2.9, 0.18, materials.wall, true, 0);
  addBox("Kira temporary studio front wall right", KIRA_BUNGALOW_RIGHT_X - frontSegment / 2, 1.48, KIRA_BUNGALOW_FRONT_Z, frontSegment, 2.9, 0.18, materials.wall, true, 0);
  addBox("Kira temporary studio clear front opening marker", KIRA_BUNGALOW_CENTER.x, 1.32, KIRA_BUNGALOW_FRONT_Z + 0.035, 2.32, 2.38, 0.035, materials.glass, false, 0);
  addBox("Kira temporary studio roof cap", KIRA_BUNGALOW_CENTER.x, 3.02, KIRA_BUNGALOW_CENTER.z, KIRA_BUNGALOW_WIDTH + 0.4, 0.16, KIRA_BUNGALOW_DEPTH + 0.4, materials.trim, false, 0);
  addBox("Kira temporary studio rear window glass", KIRA_BUNGALOW_CENTER.x + 1.9, 1.48, KIRA_BUNGALOW_BACK_Z - 0.035, 1.45, 1.05, 0.045, materials.glass, false, 0);
  addBox("Kira temporary studio rear window top frame", KIRA_BUNGALOW_CENTER.x + 1.9, 2.06, KIRA_BUNGALOW_BACK_Z - 0.06, 1.64, 0.08, 0.055, materials.windowFrame, false, 0);
  addBox("Kira temporary studio rear window bottom frame", KIRA_BUNGALOW_CENTER.x + 1.9, 0.9, KIRA_BUNGALOW_BACK_Z - 0.06, 1.64, 0.08, 0.055, materials.windowFrame, false, 0);
  addBox("Kira temporary studio rear window left frame", KIRA_BUNGALOW_CENTER.x + 1.08, 1.48, KIRA_BUNGALOW_BACK_Z - 0.06, 0.08, 1.22, 0.055, materials.windowFrame, false, 0);
  addBox("Kira temporary studio rear window right frame", KIRA_BUNGALOW_CENTER.x + 2.72, 1.48, KIRA_BUNGALOW_BACK_Z - 0.06, 0.08, 1.22, 0.055, materials.windowFrame, false, 0);
  kiraBungalowDoorLeaf = addDoorLeafToScene("Kira temporary studio clearly visible working front door", KIRA_BUNGALOW_CENTER.x, KIRA_BUNGALOW_FRONT_Z + 0.1, 1.34, 2.28);
  markTruthProp(kiraBungalowDoorLeaf, "door", "Kira temporary studio working front door", 0, ["open_door", "close_door"]);
  setKiraBungalowDoorOpen(true);
  addBox("Kira temporary studio front porch step", KIRA_BUNGALOW_CENTER.x, 0.075, KIRA_BUNGALOW_FRONT_Z + 0.72, 2.45, 0.13, 0.9, materials.sidewalk, false, 0);
  addBox("Kira temporary studio front path slab", KIRA_BUNGALOW_CENTER.x, 0.03, KIRA_BUNGALOW_FRONT_Z + 1.75, 1.75, 0.045, 1.75, materials.sidewalk, false, 0);
  const kiraAvatarReviewMirror = addReflectiveMirror(
    "Kira and Robert full body avatar review mirror",
    KIRA_BUNGALOW_LEFT_X + 0.12,
    1.36,
    KIRA_BUNGALOW_CENTER.z + 0.35,
    1.08,
    2.24,
    0,
  );
  markTruthProp(kiraAvatarReviewMirror, "mirror", "full body avatar review mirror", 0, ["inspect_avatar", "check_fit", "try_clothes"]);
  kiraBungalowStatus = {
    ...kiraBungalowStatus,
    fullBodyMirror: {
      loaded: true,
      x: Number((KIRA_BUNGALOW_LEFT_X + 0.12).toFixed(2)),
      z: Number((KIRA_BUNGALOW_CENTER.z + 0.35).toFixed(2)),
      purpose: "avatar body and clothing fit review",
    },
  };

  placeKiraBungalowModel(NEIGHBOR_PREFAB_BED_FRAME_MODEL_URL, {
    role: "Kira bedroom imported bed frame",
    name: "Kira temporary studio imported real bed frame",
    x: KIRA_BUNGALOW_CENTER.x - 2.9,
    y: 0.08,
    z: KIRA_BUNGALOW_CENTER.z - 1.72,
    width: 1.86,
    height: 0.68,
    depth: 2.25,
    yaw: 0,
    truthKind: "bed",
    truthLabel: "Kira temporary studio bed frame",
    actionHints: ["sit", "sleep", "lay_down"],
  });
  placeKiraBungalowModel(NEIGHBOR_PREFAB_MATTRESS_MODEL_URL, {
    role: "Kira bedroom imported mattress",
    name: "Kira temporary studio imported real mattress",
    x: KIRA_BUNGALOW_CENTER.x - 2.9,
    y: 0.5,
    z: KIRA_BUNGALOW_CENTER.z - 1.68,
    width: 1.58,
    height: 0.34,
    depth: 1.96,
    yaw: 0,
    truthKind: "bed",
    truthLabel: "Kira temporary studio mattress",
    actionHints: ["sleep", "lay_down"],
  });
  placeKiraBungalowModel(NEIGHBOR_PREFAB_PILLOW_MODEL_URL, {
    role: "Kira bedroom imported pillow",
    name: "Kira temporary studio imported real pillow",
    x: KIRA_BUNGALOW_CENTER.x - 2.9,
    y: 0.76,
    z: KIRA_BUNGALOW_CENTER.z - 2.42,
    width: 0.68,
    height: 0.18,
    depth: 0.36,
    yaw: 0,
    truthKind: "bed",
    truthLabel: "Kira temporary studio pillow",
    actionHints: ["sleep", "lay_down"],
  });
  placeKiraBungalowModel(NEIGHBOR_LIVING_ROOM_FURNITURE_MODEL_URL, {
    role: "Kira living room imported furniture set",
    name: "Kira temporary studio imported sofa chairs and table",
    x: KIRA_BUNGALOW_CENTER.x + 2.55,
    y: 0.08,
    z: KIRA_BUNGALOW_CENTER.z + 2.1,
    width: 2.8,
    height: 1.18,
    depth: 2.75,
    yaw: 0,
    truthKind: "seat",
    truthLabel: "Kira temporary studio seating and table",
    actionHints: ["sit", "lay_down"],
  });
  placeKiraBungalowModel(REALISTIC_BOOKSHELF_MODEL_URL, {
    role: "Kira reading imported bookshelf",
    name: "Kira temporary studio imported real bookshelf",
    x: KIRA_BUNGALOW_CENTER.x - 3.88,
    y: 0.08,
    z: KIRA_BUNGALOW_CENTER.z + 2.24,
    width: 0.58,
    height: 1.75,
    depth: 1.9,
    yaw: Math.PI / 2,
    truthKind: "book",
    truthLabel: "Kira temporary studio bookshelf",
    actionHints: ["read_book", "browse_books"],
  });
  placeKiraBungalowModel(NEIGHBOR_PREFAB_BOOK_MODEL_URL, {
    role: "Kira readable book",
    name: "Kira temporary studio imported readable book",
    x: KIRA_BUNGALOW_CENTER.x + 0.92,
    y: 0.78,
    z: KIRA_BUNGALOW_CENTER.z + 1.28,
    width: 0.56,
    height: 0.08,
    depth: 0.38,
    yaw: 0.22,
    truthKind: "book",
    truthLabel: "Kira temporary studio readable book",
    actionHints: ["read_book"],
  });
  loadKiraSharedPhoneModel();
  addPrototypeGarmentCloset();
  interactZones.push({
    name: "Kira temporary studio front door",
    x: KIRA_BUNGALOW_CENTER.x,
    z: KIRA_BUNGALOW_FRONT_Z + 0.52,
    floor: 0,
    radius: 1.45,
    action: () => {
      setKiraBungalowDoorOpen(!kiraBungalowDoorOpen);
      show(kiraBungalowDoorOpen ? "Kira temporary studio front door open." : "Kira temporary studio front door closed.");
    },
  });
  interactZones.push({
    name: "Kira and Robert full body avatar review mirror",
    x: KIRA_BUNGALOW_LEFT_X + 0.72,
    z: KIRA_BUNGALOW_CENTER.z + 0.35,
    floor: 0,
    radius: 1.1,
    action: () => {
      show("Full-body mirror ready for avatar body and clothing fit review.");
    },
  });
  interactZones.push({
    name: "Kira prototype dress shirt closet",
    x: DRESS_SHIRT_CLOSET_POSITION.x,
    z: DRESS_SHIRT_CLOSET_POSITION.z,
    floor: 0,
    radius: 1.25,
    action: () => {
      if (!prototypeDressShirt || !prototypeCloset || !avatarDressingController) {
        show("Prototype dress shirt closet is not ready yet.");
        return;
      }
      if (prototypeDressShirt.state === GARMENT_STATES.WornClosed || prototypeDressShirt.state === GARMENT_STATES.WornOpen) {
        avatarDressingController.startRemove("closet");
        show("Starting dress shirt removal and hanging it back in the closet.");
        return;
      }
      prototypeCloset.startDressing(prototypeDressShirt);
      show("Taking the dress shirt from the closet and starting the dressing sequence.");
    },
  });
}

function setStarbucksDoorOpen(open = true) {
  starbucksDoorOpen = !!open;
  if (starbucksDoorLeaf) starbucksDoorLeaf.rotation.y = starbucksDoorOpen ? -Math.PI / 2 : 0;
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    starbucksDoor: {
      loaded: true,
      open: starbucksDoorOpen,
      x: STARBUCKS_CENTER.x,
      z: Number(STARBUCKS_PUBLIC_FRONT_Z.toFixed(2)),
    },
  };
}

function addStarbucksCafeColliders() {
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    starbucksShellCollision: {
      enabled: false,
      note: "Temporary shell and door colliders were removed because they created a large invisible wall around Starbucks.",
    },
  };
}

function addStarbucksSolidInteriorColliders() {
  colliders.push({ x: STARBUCKS_SEAT_SPOT.x, z: STARBUCKS_SEAT_SPOT.z + 0.72, sx: 1.18, sz: 0.82, floor: 0 });
  colliders.push({ x: STARBUCKS_CENTER.x - 5.85, z: STARBUCKS_CENTER.z + 1.0, sx: 1.5, sz: 4.6, floor: 0 });
  colliders.push({ x: STARBUCKS_CENTER.x + 5.85, z: STARBUCKS_CENTER.z + 1.0, sx: 1.5, sz: 4.6, floor: 0 });
  colliders.push({ x: STARBUCKS_CENTER.x - 2.45, z: STARBUCKS_CENTER.z + 2.2, sx: 1.3, sz: 1.05, floor: 0 });
  colliders.push({ x: STARBUCKS_CENTER.x + 2.25, z: STARBUCKS_CENTER.z + 2.2, sx: 1.3, sz: 1.05, floor: 0 });
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    starbucksCollision: {
      solidExceptDoor: false,
      note: "Only seating and side furniture zones keep colliders until the Starbucks door and wall collision are rebuilt with an intentional pass-through.",
    },
  };
}

function makeStarbucksCounterCup(name, x, surfaceY, z) {
  const root = new THREE.Group();
  root.name = name;
  const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.066, 0.048, 0.19, 24), materials.paper);
  cup.name = `${name} white cup body`;
  cup.position.y = 0.095;
  cup.castShadow = true;
  cup.receiveShadow = true;
  root.add(cup);
  const sleeve = new THREE.Mesh(new THREE.CylinderGeometry(0.071, 0.058, 0.062, 24), materials.livingWood);
  sleeve.name = `${name} cardboard sleeve`;
  sleeve.position.y = 0.094;
  sleeve.castShadow = true;
  sleeve.receiveShadow = true;
  root.add(sleeve);
  const lid = new THREE.Mesh(new THREE.CylinderGeometry(0.071, 0.071, 0.028, 24), materials.brushedSteel);
  lid.name = `${name} white lid`;
  lid.position.y = 0.203;
  lid.castShadow = true;
  lid.receiveShadow = true;
  root.add(lid);
  root.position.set(x, surfaceY, z);
  scene.add(root);
  markTruthProp(root, "coffee_cup", name, 0, ["drink_coffee"]);
  return root;
}

function spawnTemporaryStarbucksCup(x, z, expiresIn = 38, surfaceY = 0.82) {
  const root = makeStarbucksCounterCup("temporary Starbucks cup placeholder that self-cleans", x, surfaceY, z);
  root.userData.expiresAt = clock.elapsedTime + expiresIn;
  starbucksTemporaryCups.push(root);
  return root;
}

function addFutureParkBasketballCourtColliders() {
  const left = PARK_BASKETBALL_CENTER.x - PARK_BASKETBALL_COURT_WIDTH / 2;
  const right = PARK_BASKETBALL_CENTER.x + PARK_BASKETBALL_COURT_WIDTH / 2;
  const front = PARK_BASKETBALL_CENTER.z - PARK_BASKETBALL_COURT_DEPTH / 2;
  const back = PARK_BASKETBALL_CENTER.z + PARK_BASKETBALL_COURT_DEPTH / 2;
  const gateWidth = 4.0;
  const sideT = 0.34;
  colliders.push({ x: left, z: PARK_BASKETBALL_CENTER.z, sx: sideT, sz: PARK_BASKETBALL_COURT_DEPTH, floor: 0 });
  colliders.push({ x: right, z: PARK_BASKETBALL_CENTER.z, sx: sideT, sz: PARK_BASKETBALL_COURT_DEPTH, floor: 0 });
  colliders.push({ x: PARK_BASKETBALL_CENTER.x, z: back, sx: PARK_BASKETBALL_COURT_WIDTH, sz: sideT, floor: 0 });
  colliders.push({ x: left + (PARK_BASKETBALL_COURT_WIDTH - gateWidth) / 4, z: front, sx: (PARK_BASKETBALL_COURT_WIDTH - gateWidth) / 2, sz: sideT, floor: 0 });
  colliders.push({ x: right - (PARK_BASKETBALL_COURT_WIDTH - gateWidth) / 4, z: front, sx: (PARK_BASKETBALL_COURT_WIDTH - gateWidth) / 2, sz: sideT, floor: 0 });
  colliders.push({ x: PARK_BASKETBALL_CENTER.x - 8.2, z: PARK_BASKETBALL_CENTER.z - 10.25, sx: 1.35, sz: 0.7, floor: 0 });
  colliders.push({ x: PARK_BASKETBALL_CENTER.x + 8.2, z: PARK_BASKETBALL_CENTER.z + 10.25, sx: 1.35, sz: 0.7, floor: 0 });
  colliders.push({ x: BASKETBALL_BENCH_SIT_SPOT.x, z: BASKETBALL_BENCH_SIT_SPOT.z, sx: 2.25, sz: 0.58, floor: 0 });
  colliders.push({ x: PARK_BASKETBALL_CENTER.x + 5.75, z: PARK_BASKETBALL_CENTER.z - 10.35, sx: 2.25, sz: 0.58, floor: 0 });
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    basketballCourt: {
      ...homeWorldActivityStatus.basketballCourt,
      physicalColliders: true,
      gate: { x: Number(PARK_BASKETBALL_CENTER.x.toFixed(2)), z: Number(front.toFixed(2)), width: gateWidth },
      benchPracticeSpot: { x: Number(BASKETBALL_BENCH_SIT_SPOT.x.toFixed(2)), z: Number(BASKETBALL_BENCH_SIT_SPOT.z.toFixed(2)) },
    },
  };
}

function prepareSchoolClassroomReference(root) {
  root.traverse((node) => {
    if (!node.isMesh) return;
    const repairMaterial = (material) => {
      if (!material) return material;
      const next = material.clone();
      const color = next.color;
      if (color) {
        const luminance = color.r * 0.2126 + color.g * 0.7152 + color.b * 0.0722;
        if (luminance < 0.12) color.setHex(0xb9b6ad);
      }
      if ("roughness" in next) next.roughness = Math.max(next.roughness ?? 0.4, 0.62);
      if ("metalness" in next) next.metalness = Math.min(next.metalness ?? 0, 0.08);
      return next;
    };
    node.material = Array.isArray(node.material) ? node.material.map(repairMaterial) : repairMaterial(node.material);
  });
}

function addHomeWorldSchoolClassroom() {
  const leftX = SCHOOL_CENTER.x - SCHOOL_WIDTH / 2;
  const rightX = SCHOOL_CENTER.x + SCHOOL_WIDTH / 2;
  const backZ = SCHOOL_CENTER.z + SCHOOL_DEPTH / 2;
  const frontZ = SCHOOL_FRONT_Z;
  const wallH = 2.75;
  const wallY = wallH / 2;
  const wallT = 0.22;
  const frontGap = 3.6;
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    schoolClassroom: {
      ...homeWorldActivityStatus.schoolClassroom,
      planned: true,
      stationActive: true,
      shared: true,
      modelSuppressedReason: HOME_WORLD_PRE_RAM_LIGHT_MODE
        ? "pre-RAM light mode keeps only the empty classroom shell and learning-room trigger; imported school props are skipped until the RAM upgrade"
        : "downloaded full classroom shells are kept as references because the last generated/whole-building tests trapped bodies; this pass builds a simple open one-room classroom using imported school props",
      entry: { x: Number(SCHOOL_ENTRY.x.toFixed(2)), z: Number(SCHOOL_ENTRY.z.toFixed(2)) },
      desk: { x: Number(SCHOOL_DESK_SPOT.x.toFixed(2)), z: Number(SCHOOL_DESK_SPOT.z.toFixed(2)) },
      seat: { x: Number(SCHOOL_SEAT_SPOT.x.toFixed(2)), z: Number(SCHOOL_SEAT_SPOT.z.toFixed(2)) },
      seatYawDegrees: 0,
      chairRotationFix: "Student chair rotated 180 degrees from the previous backwards-facing pass so it faces the desk.",
      purpose: "shared physical place for Kira, Marinette, Peter, Gwen, and future AIs to attend lessons, take notes, read, and practice subject work",
    },
  };

  addLabel("Home World School", SCHOOL_CENTER.x, 2.5, SCHOOL_FRONT_Z - 2.05, 4.1, {
    color: "#102018",
    background: "rgba(225,235,220,0.78)",
  });
  const schoolFloor = addFloorTile("shared school classroom floor", SCHOOL_CENTER.x, SCHOOL_CENTER.z, SCHOOL_WIDTH, SCHOOL_DEPTH, materials.floor, 0.034);
  markTruthProp(schoolFloor, "classroom", "empty Home World school learning room", 0, ["attend_school", "study", "learn"]);
  addBox("shared school classroom rear wall", SCHOOL_CENTER.x, wallY, backZ, SCHOOL_WIDTH + wallT, wallH, wallT, materials.schoolWall, true, 0);
  addBox("shared school classroom left wall", leftX, wallY, SCHOOL_CENTER.z, wallT, wallH, SCHOOL_DEPTH + wallT, materials.schoolWall, true, 0);
  addBox("shared school classroom right wall", rightX, wallY, SCHOOL_CENTER.z, wallT, wallH, SCHOOL_DEPTH + wallT, materials.schoolWall, true, 0);
  addBox("shared school classroom front wall left", leftX + (SCHOOL_WIDTH - frontGap) / 4, wallY, frontZ, (SCHOOL_WIDTH - frontGap) / 2, wallH, wallT, materials.schoolWall, true, 0);
  addBox("shared school classroom front wall right", rightX - (SCHOOL_WIDTH - frontGap) / 4, wallY, frontZ, (SCHOOL_WIDTH - frontGap) / 2, wallH, wallT, materials.schoolWall, true, 0);
  addBox("shared school classroom entrance header", SCHOOL_CENTER.x, 2.74, frontZ, frontGap + 0.32, 0.18, 0.28, materials.schoolAccent, false, 0);
  addBox("shared school classroom entry left jamb", SCHOOL_CENTER.x - frontGap / 2, 1.18, frontZ - 0.02, 0.16, 2.36, 0.28, materials.schoolAccent, false, 0);
  addBox("shared school classroom entry right jamb", SCHOOL_CENTER.x + frontGap / 2, 1.18, frontZ - 0.02, 0.16, 2.36, 0.28, materials.schoolAccent, false, 0);
  addBox("shared school classroom front threshold", SCHOOL_CENTER.x, 0.055, frontZ - 0.35, frontGap, 0.08, 0.62, materials.sidewalk, false, 0);
  addFloorTile("school classroom activity pad", SCHOOL_CENTER.x, SCHOOL_CENTER.z, SCHOOL_WIDTH + 2.0, SCHOOL_DEPTH + 2.0, materials.sidewalk, 0.018);
  addFloorTile("school front walking path", (SCHOOL_ENTRY.x + 60.5) / 2, SCHOOL_ENTRY.z, Math.abs(SCHOOL_ENTRY.x - 60.5) + 1.5, 1.2, materials.sidewalk, 0.032);
  if (HOME_WORLD_PRE_RAM_LIGHT_MODE) {
    for (const [role, url] of [
      ["schoolDeskTable", HOME_WORLD_SCHOOL_TABLE_MODEL_URL],
      ["schoolChair", HOME_WORLD_SCHOOL_CHAIR_MODEL_URL],
      ["schoolSideTable", HOME_WORLD_SCHOOL_SIDE_TABLE_MODEL_URL],
      ["schoolBoard", HOME_WORLD_SCHOOL_BOARD_MODEL_URL],
      ["schoolLockers", HOME_WORLD_SCHOOL_LOCKERS_MODEL_URL],
      ["schoolClock", HOME_WORLD_SCHOOL_CLOCK_MODEL_URL],
      ["schoolWorldMap", HOME_WORLD_SCHOOL_WORLD_MAP_MODEL_URL],
      ["schoolDeskPhone", KIRA_SHARED_PHONE_MODEL_URL],
      ["schoolLessonBook", NEIGHBOR_PREFAB_BOOK_MODEL_URL],
      ["schoolScrapbook", HOME_WORLD_SCHOOL_SCRAPBOOK_MODEL_URL],
      ["schoolPencils", HOME_WORLD_SCHOOL_PENCILS_MODEL_URL],
    ]) {
      markPreRamAssetSkipped(role, {
        url,
        restoreNote: "restore this prop when rebuilding the larger school after the RAM upgrade",
      });
    }
    interactZones.push({
      name: "empty school learning room",
      x: SCHOOL_CENTER.x,
      z: SCHOOL_CENTER.z,
      floor: 0,
      radius: Math.max(SCHOOL_WIDTH, SCHOOL_DEPTH) / 2,
      action: () => {
        startActiveAvatarSchoolStudyPractice();
        show("School learning room active. Kira can study here; leaving the empty room ends the school program.");
      },
    });
    return;
  }
  placeHomeWorldActivityModel(HOME_WORLD_SCHOOL_TABLE_MODEL_URL, {
    role: "schoolDeskTable",
    name: "shared school imported study table",
    x: SCHOOL_DESK_SPOT.x,
    y: 0.08,
    z: SCHOOL_DESK_SPOT.z,
    width: 1.35,
    height: 0.78,
    depth: 0.85,
    yaw: Math.PI / 2,
    uniform: false,
    truthKind: "desk",
    truthLabel: "shared school study desk",
    actionHints: ["attend_school", "study", "take_notes"],
  });
  placeHomeWorldActivityModel(HOME_WORLD_SCHOOL_CHAIR_MODEL_URL, {
    role: "schoolChair",
    name: "shared school imported chair",
    x: SCHOOL_SEAT_SPOT.x,
    y: 0.08,
    z: SCHOOL_SEAT_SPOT.z,
    width: 0.52,
    height: 0.9,
    depth: 0.58,
    yaw: SCHOOL_SEAT_YAW,
    uniform: false,
    truthKind: "chair",
    truthLabel: "shared school desk chair",
    actionHints: ["sit", "attend_school", "study"],
  });
  placeHomeWorldActivityModel(HOME_WORLD_SCHOOL_SIDE_TABLE_MODEL_URL, {
    role: "schoolSideTable",
    name: "shared school imported side table for class supplies",
    x: SCHOOL_DESK_SPOT.x + 1.75,
    y: 0.08,
    z: SCHOOL_DESK_SPOT.z + 0.85,
    width: 0.82,
    height: 0.74,
    depth: 0.62,
    yaw: 0,
    uniform: false,
    truthKind: "desk",
    truthLabel: "shared school supply table",
    actionHints: ["attend_school", "take_notes"],
  });
  placeHomeWorldActivityModel(HOME_WORLD_SCHOOL_BOARD_MODEL_URL, {
    role: "schoolBoard",
    name: "shared school imported classroom board",
    x: SCHOOL_CENTER.x - 0.7,
    y: 1.55,
    z: backZ - 0.18,
    width: 3.15,
    height: 1.28,
    depth: 0.1,
    yaw: Math.PI,
    uniform: false,
    truthKind: "screen",
    truthLabel: "shared school classroom board",
    actionHints: ["attend_school", "watch_lesson", "study"],
  });
  placeHomeWorldActivityModel(HOME_WORLD_SCHOOL_LOCKERS_MODEL_URL, {
    role: "schoolLockers",
    name: "shared school imported metal lockers",
    x: leftX + 0.48,
    y: 0.08,
    z: SCHOOL_CENTER.z + 0.65,
    width: 0.52,
    height: 1.95,
    depth: 2.2,
    yaw: Math.PI / 2,
    uniform: false,
    truthKind: "storage",
    truthLabel: "shared school lockers",
    actionHints: ["attend_school", "store_book", "take_notes"],
  });
  placeHomeWorldActivityModel(HOME_WORLD_SCHOOL_CLOCK_MODEL_URL, {
    role: "schoolClock",
    name: "shared school imported classroom clock",
    x: SCHOOL_CENTER.x + 2.75,
    y: 2.15,
    z: backZ - 0.16,
    width: 0.58,
    height: 0.58,
    depth: 0.08,
    yaw: Math.PI,
    uniform: true,
    truthKind: "clock",
    truthLabel: "shared school wall clock",
    actionHints: ["attend_school", "study"],
  });
  placeHomeWorldActivityModel(HOME_WORLD_SCHOOL_WORLD_MAP_MODEL_URL, {
    role: "schoolWorldMap",
    name: "shared school imported classroom world map",
    x: SCHOOL_CENTER.x + 3.8,
    y: 1.65,
    z: backZ - 0.16,
    width: 2.25,
    height: 1.35,
    depth: 0.12,
    yaw: Math.PI,
    uniform: false,
    truthKind: "book",
    truthLabel: "shared school classroom world map",
    actionHints: ["attend_school", "study"],
  });
  placeHomeWorldActivityModel(KIRA_SHARED_PHONE_MODEL_URL, {
    role: "schoolDeskPhone",
    name: "shared school imported phone for notes and ebooks",
    x: SCHOOL_DESK_SPOT.x + 0.32,
    y: 0.86,
    z: SCHOOL_DESK_SPOT.z - 0.12,
    width: 0.16,
    height: 0.035,
    depth: 0.31,
    rotation: { x: -Math.PI / 2, y: 0.25, z: 0 },
    uniform: true,
    truthKind: "phone",
    truthLabel: "shared school desk phone",
    actionHints: ["attend_school", "take_notes", "read_book", "research"],
  });
  placeHomeWorldActivityModel(NEIGHBOR_PREFAB_BOOK_MODEL_URL, {
    role: "schoolLessonBook",
    name: "shared school imported lesson book",
    x: SCHOOL_DESK_SPOT.x - 0.22,
    y: 0.86,
    z: SCHOOL_DESK_SPOT.z + 0.18,
    width: 0.42,
    height: 0.06,
    depth: 0.3,
    yaw: -0.18,
    uniform: true,
    truthKind: "book",
    truthLabel: "shared school lesson book",
    actionHints: ["attend_school", "read_book", "study"],
  });
  placeHomeWorldActivityModel(HOME_WORLD_SCHOOL_SCRAPBOOK_MODEL_URL, {
    role: "schoolScrapbook",
    name: "shared school restored scrapbook trinket desk prop",
    x: SCHOOL_DESK_SPOT.x - 0.55,
    y: 0.91,
    z: SCHOOL_DESK_SPOT.z + 0.08,
    width: 0.34,
    height: 0.055,
    depth: 0.26,
    rotation: { x: -Math.PI / 2, y: 0.12, z: 0 },
    uniform: false,
    truthKind: "notebook",
    truthLabel: "shared school restored scrapbook",
    actionHints: ["attend_school", "take_notes", "read_book", "study"],
  });
  placeHomeWorldActivityModel(HOME_WORLD_SCHOOL_PENCILS_MODEL_URL, {
    role: "schoolPencils",
    name: "shared school imported pencils",
    x: SCHOOL_DESK_SPOT.x - 0.62,
    y: 0.9,
    z: SCHOOL_DESK_SPOT.z - 0.02,
    width: 0.28,
    height: 0.08,
    depth: 0.18,
    yaw: -0.35,
    uniform: true,
    truthKind: "pencil",
    truthLabel: "shared school pencils",
    actionHints: ["attend_school", "write_notes", "draw"],
  });
  const schoolNotebook = addBox("shared school notebook for lessons", SCHOOL_DESK_SPOT.x - 0.48, 0.86, SCHOOL_DESK_SPOT.z - 0.18, 0.34, 0.026, 0.24, materials.notebookCover, false, 0);
  markTruthProp(schoolNotebook, "notebook", "shared school lesson notebook", 0, ["attend_school", "take_notes", "study"]);
  interactZones.push({
    name: "shared school study desk",
    x: SCHOOL_DESK_SPOT.x,
    z: SCHOOL_DESK_SPOT.z,
    floor: 0,
    radius: 2.1,
    action: () => {
      startActiveAvatarSchoolStudyPractice();
      show("Shared school study practice started: walk to the desk, sit, and use the phone/notebook for a lesson.");
    },
  });
}

function addHomeWorldActivities() {
  addHomeWorldSchoolClassroom();
  addStarbucksCafeColliders();
  if (!HOME_WORLD_PRE_RAM_LIGHT_MODE) addStarbucksSolidInteriorColliders();
  if (HOME_WORLD_PRE_RAM_LIGHT_MODE) {
    markPreRamAssetSkipped("starbucks", {
      url: HOME_WORLD_STARBUCKS_MODEL_URL,
      restorePlacement: {
        x: STARBUCKS_CENTER.x,
        y: 0.04,
        z: STARBUCKS_CENTER.z,
        width: STARBUCKS_WIDTH,
        height: 4.75,
        depth: STARBUCKS_DEPTH,
        yaw: Math.PI,
        uniform: true,
        prepare: "prepareStarbucksBuildingOnly",
      },
      restoreNote: "This exact cafe GLB and fit values were already resized; restore this block instead of searching Starbucks models again.",
    });
    addBox("pre-RAM coffee pickup counter top", STARBUCKS_COUNTER_SPOT.x + 0.1, 0.82, STARBUCKS_COUNTER_SPOT.z + 0.18, 2.05, 0.14, 0.72, materials.counter, true, 0);
    addBox("pre-RAM coffee pickup counter base", STARBUCKS_COUNTER_SPOT.x + 0.1, 0.42, STARBUCKS_COUNTER_SPOT.z + 0.18, 1.78, 0.68, 0.52, materials.warmCabinet, true, 0);
  } else {
    placeHomeWorldActivityModel(HOME_WORLD_STARBUCKS_MODEL_URL, {
      role: "starbucks",
      name: "Home World imported Starbucks cafe with bathrooms counter and seating",
      x: STARBUCKS_CENTER.x,
      y: 0.04,
      z: STARBUCKS_CENTER.z,
      width: STARBUCKS_WIDTH,
      height: 4.75,
      depth: STARBUCKS_DEPTH,
      yaw: Math.PI,
      uniform: true,
      prepare: prepareStarbucksBuildingOnly,
      truthKind: "cafe",
      truthLabel: "Home World Starbucks cafe",
      actionHints: ["drink_coffee", "sit", "take_notes", "socialize"],
    });
  }
  setStarbucksDoorOpen(true);

  const starbucksCounterTruth = new THREE.Object3D();
  starbucksCounterTruth.name = "Starbucks imported counter cup placement truth spot";
  starbucksCounterTruth.position.set(STARBUCKS_COUNTER_SPOT.x, 0.98, STARBUCKS_COUNTER_SPOT.z);
  scene.add(starbucksCounterTruth);
  markTruthProp(starbucksCounterTruth, "counter", "Starbucks imported counter cup placement", 0, ["drink_coffee", "take_notes"]);
  const cupSpots = [
    [-0.52, 0.18],
    [-0.16, 0.22],
    [0.22, 0.2],
    [0.58, 0.16],
  ];
  for (let i = 0; i < cupSpots.length; i += 1) {
    const [dx, dz] = cupSpots[i];
    makeStarbucksCounterCup(
      `Starbucks inside counter coffee cup ${i + 1}`,
      STARBUCKS_COUNTER_SPOT.x + 0.22 + dx,
      0.98,
      STARBUCKS_COUNTER_SPOT.z + dz,
    );
  }
  addBox("Starbucks note phone table", STARBUCKS_SEAT_SPOT.x, 0.48, STARBUCKS_SEAT_SPOT.z + 0.72, 1.05, 0.12, 0.72, materials.counter, true, 0);
  const cafePhone = addBox("Starbucks phone-sized note slab", STARBUCKS_SEAT_SPOT.x - 0.18, 0.57, STARBUCKS_SEAT_SPOT.z + 0.68, 0.16, 0.018, 0.28, materials.phoneBody, false, 0);
  addBox("Starbucks phone lit note screen", STARBUCKS_SEAT_SPOT.x - 0.18, 0.585, STARBUCKS_SEAT_SPOT.z + 0.68, 0.13, 0.008, 0.23, materials.phoneScreen, false, 0);
  const cafeNotebook = addBox("Starbucks small note notebook", STARBUCKS_SEAT_SPOT.x + 0.22, 0.57, STARBUCKS_SEAT_SPOT.z + 0.64, 0.34, 0.025, 0.24, materials.notebookCover, false, 0);
  markTruthProp(cafePhone, "phone", "Starbucks cafe note phone", 0, ["take_notes", "journal", "take_photo", "browse_books"]);
  markTruthProp(cafeNotebook, "notebook", "Starbucks cafe note notebook", 0, ["take_notes", "journal"]);
  interactZones.push({
    name: "Starbucks cafe front door",
    x: STARBUCKS_CENTER.x,
    z: STARBUCKS_PUBLIC_FRONT_Z - 0.65,
    floor: 0,
    radius: 1.55,
    action: () => {
      setStarbucksDoorOpen(true);
      show(HOME_WORLD_PRE_RAM_LIGHT_MODE
        ? "Coffee pickup spot is active while the full Starbucks model is disabled for RAM."
        : "Starbucks imported entrance is kept open until the real door rig is ready.");
    },
  });
  interactZones.push({
    name: "Starbucks coffee counter",
    x: STARBUCKS_COUNTER_SPOT.x,
    z: STARBUCKS_COUNTER_SPOT.z,
    floor: 0,
    radius: 1.75,
    action: () => {
      spawnTemporaryStarbucksCup(STARBUCKS_COUNTER_SPOT.x + 0.22, STARBUCKS_COUNTER_SPOT.z + 0.2, 38, 0.98);
      show("Coffee cup placed on the inside Starbucks counter. It will self-clean after a short time.");
    },
  });

  if (HOME_WORLD_PRE_RAM_LIGHT_MODE) {
    markPreRamAssetSkipped("basketballCourt", {
      url: HOME_WORLD_BASKETBALL_COURT_MODEL_URL,
      position: { x: PARK_BASKETBALL_CENTER.x, z: PARK_BASKETBALL_CENTER.z },
      restoreNote: "restore the future park basketball court after the RAM upgrade",
    });
    markPreRamAssetSkipped("basketball", {
      url: HOME_WORLD_BASKETBALL_MODEL_URL,
      restoreNote: "restore the ball and practice trigger after the RAM upgrade",
    });
  } else {
  addFutureParkBasketballCourtColliders();
  addLabel("Future Park", PARK_BASKETBALL_CENTER.x, 2.2, PARK_BASKETBALL_CENTER.z - PARK_BASKETBALL_COURT_DEPTH / 2 - 1.2, 3.2, { color: "#102018", background: "rgba(210,232,190,0.72)" });
  placeHomeWorldActivityModel(HOME_WORLD_BASKETBALL_COURT_MODEL_URL, {
    role: "basketballCourt",
    name: "future park imported basketball court with hoops",
    x: PARK_BASKETBALL_CENTER.x,
    y: -0.42,
    z: PARK_BASKETBALL_CENTER.z,
    width: PARK_BASKETBALL_COURT_WIDTH,
    height: 4.75,
    depth: PARK_BASKETBALL_COURT_DEPTH,
    yaw: 0,
    uniform: false,
    truthKind: "court",
    truthLabel: "future park basketball court",
    actionHints: ["play_basketball", "run", "jump", "dodge"],
  });
  placeHomeWorldActivityModel(HOME_WORLD_BASKETBALL_MODEL_URL, {
    role: "basketball",
    name: "future park imported basketball with simple bounce physics",
    x: BASKETBALL_BALL_REST_SPOT.x,
    y: BASKETBALL_BALL_REST_SPOT.y + 0.03,
    z: BASKETBALL_BALL_REST_SPOT.z,
    width: 0.5,
    height: 0.5,
    depth: 0.5,
    uniform: true,
    truthKind: "basketball",
    truthLabel: "future park basketball",
    actionHints: ["play_basketball", "dribble"],
    onPlaced: (root) => {
      basketballBallRoot = root;
      basketballBallBaseY = root.position.y;
    },
  });
  interactZones.push({
    name: "future park basketball",
    x: BASKETBALL_BALL_REST_SPOT.x,
    z: BASKETBALL_BALL_REST_SPOT.z,
    floor: 0,
    radius: 2.0,
    action: () => {
      basketballBounceUntil = clock.elapsedTime + 5.0;
      startActiveAvatarBasketballPractice();
      show("Basketball practice started: pick up, dribble, and line up a shot.");
    },
  });
  }

  if (HOME_WORLD_PRE_RAM_LIGHT_MODE) {
    markPreRamAssetSkipped("sun", {
      url: HOME_WORLD_SUN_MODEL_URL,
      restorePlacement: { x: -34, y: 36, z: -42, width: 5.0, height: 5.0, depth: 5.0, uniform: true },
    });
    markPreRamAssetSkipped("moon", {
      url: HOME_WORLD_MOON_MODEL_URL,
      restorePlacement: { x: 40, y: 31, z: -46, width: 3.8, height: 3.8, depth: 3.8, uniform: true },
    });
    setHomeWorldSkyMode(homeWorldSkyMode);
  } else {
  placeHomeWorldActivityModel(HOME_WORLD_SUN_MODEL_URL, {
    role: "sun",
    name: "downloaded visible sun for Home World sky",
    x: -34,
    y: 36,
    z: -42,
    width: 5.0,
    height: 5.0,
    depth: 5.0,
    uniform: true,
    onPlaced: (root, source) => {
      homeWorldSunRoot = root;
      if (source.animations?.length) {
        homeWorldSkyMixer = new THREE.AnimationMixer(root);
        homeWorldSkyMixer.clipAction(source.animations[0]).play();
      }
      setHomeWorldSkyMode(homeWorldSkyMode);
    },
  });
  placeHomeWorldActivityModel(HOME_WORLD_MOON_MODEL_URL, {
    role: "moon",
    name: "downloaded moon for Home World sky",
    x: 40,
    y: 31,
    z: -46,
    width: 3.8,
    height: 3.8,
    depth: 3.8,
    uniform: true,
    onPlaced: (root) => {
      homeWorldMoonRoot = root;
      setHomeWorldSkyMode(homeWorldSkyMode);
    },
  });
  }
}

function setHomeWorldSkyMode(mode = "day") {
  homeWorldSkyMode = String(mode || "day").toLowerCase().includes("night") ? "night" : "day";
  if (homeWorldSunRoot) homeWorldSunRoot.visible = homeWorldSkyMode === "day";
  if (homeWorldMoonRoot) homeWorldMoonRoot.visible = homeWorldSkyMode === "night";
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    skyMode: {
      mode: homeWorldSkyMode,
      sunVisible: !!homeWorldSunRoot?.visible,
      moonVisible: !!homeWorldMoonRoot?.visible,
    },
  };
  return homeWorldActivityStatus.skyMode;
}

function updateHomeWorldActivityAnimations(t, dt) {
  if (homeWorldSkyMixer) homeWorldSkyMixer.update(dt);
  if (homeWorldSunRoot?.visible) homeWorldSunRoot.rotation.y += dt * 0.08;
  if (homeWorldMoonRoot?.visible) homeWorldMoonRoot.rotation.y -= dt * 0.035;
  if (basketballBallRoot) {
    const heldByAvatar = activeHeldPropKind === "basketball";
    basketballBallRoot.visible = !heldByAvatar;
    const bouncing = !heldByAvatar && t < basketballBounceUntil;
    const bounce = bouncing ? Math.abs(Math.sin(t * 8.2)) * 0.48 : 0;
    basketballBallRoot.position.y = basketballBallBaseY + bounce;
    if (bouncing) {
      basketballBallRoot.rotation.x += dt * 7.0;
      basketballBallRoot.rotation.z += dt * 4.8;
    }
  }
  for (let i = starbucksTemporaryCups.length - 1; i >= 0; i -= 1) {
    const cup = starbucksTemporaryCups[i];
    if (!cup?.parent || t < (cup.userData?.expiresAt || 0)) continue;
    cup.parent.remove(cup);
    starbucksTemporaryCups.splice(i, 1);
  }
}

function addNeighborBrickCourses(label, cx, cz, width, depth, baseY = 0.16, height = 2.7) {
  const frontZ = cz + depth / 2 + 0.102;
  const backZ = cz - depth / 2 - 0.102;
  const leftX = cx - width / 2 - 0.102;
  const rightX = cx + width / 2 + 0.102;
  for (let y = baseY + 0.18; y < baseY + height; y += 0.22) {
    addBox(`${label} front brick mortar course`, cx, y, frontZ, width + 0.08, 0.018, 0.018, materials.neighborStone, false);
    addBox(`${label} rear brick mortar course`, cx, y, backZ, width + 0.08, 0.018, 0.018, materials.neighborStone, false);
    addBox(`${label} left brick mortar course`, leftX, y, cz, 0.018, 0.018, depth + 0.08, materials.neighborStone, false);
    addBox(`${label} right brick mortar course`, rightX, y, cz, 0.018, 0.018, depth + 0.08, materials.neighborStone, false);
  }
  for (let row = 0; row < 12; row += 1) {
    const y = baseY + 0.28 + row * 0.22;
    const offset = row % 2 ? 0.29 : 0;
    for (let x = cx - width / 2 + 0.35 + offset; x < cx + width / 2 - 0.25; x += 0.58) {
      addBox(`${label} front vertical brick joint`, x, y, frontZ + 0.01, 0.018, 0.17, 0.018, materials.neighborStone, false);
      addBox(`${label} rear vertical brick joint`, x, y, backZ - 0.01, 0.018, 0.17, 0.018, materials.neighborStone, false);
    }
    for (let z = cz - depth / 2 + 0.35 + offset; z < cz + depth / 2 - 0.25; z += 0.58) {
      addBox(`${label} left vertical brick joint`, leftX - 0.01, y, z, 0.018, 0.17, 0.018, materials.neighborStone, false);
      addBox(`${label} right vertical brick joint`, rightX + 0.01, y, z, 0.018, 0.17, 0.018, materials.neighborStone, false);
    }
  }
}

function addNeighborHouseLegacyFailed() {
  const cx = 28.4;
  const cz = 3.2;
  const width = 11.6;
  const depth = 13.0;
  const frontZ = cz + depth / 2;
  const backZ = cz - depth / 2;
  const leftX = cx - width / 2;
  const rightX = cx + width / 2;
  const doorX = cx - 2.55;

  addFloorTile("neighbor house separated lot graded pad", cx, cz + 1.0, 14.8, 17.2, materials.grass, -0.018);
  addFloorTile("neighbor house foundation slab", cx, cz, width + 0.75, depth + 0.75, materials.sidewalk, 0.04);
  addFloorTile("neighbor porch stone landing", doorX, frontZ + 1.0, 3.5, 1.75, materials.neighborStone, 0.065);
  addFloorTile("neighbor front walk to sidewalk", doorX, 13.65, 1.55, 7.0, materials.sidewalk, 0.035);
  addFloorTile("neighbor driveway concrete", rightX - 0.45, 13.1, 3.8, 8.2, materials.sidewalk, 0.03);
  addBox("neighbor driveway expansion joint front", rightX - 0.45, 0.07, 16.1, 3.55, 0.035, 0.035, materials.windowFrame, false);
  addBox("neighbor driveway expansion joint rear", rightX - 0.45, 0.07, 10.2, 3.55, 0.035, 0.035, materials.windowFrame, false);

  addNeighborLongWallWithOpenings("neighbor house front first floor wall with real openings", frontZ, leftX, rightX, 0.07, 2.82, 0.18, materials.neighborSiding, [
    { x: doorX, width: 1.86, bottom: 0.07, top: 2.48, blockCollider: false },
    { x: cx + 1.25, width: 1.62, bottom: 1.02, top: 2.36, blockCollider: true },
    { x: cx + 4.15, width: 1.32, bottom: 1.02, top: 2.34, blockCollider: true },
  ], 0);
  addNeighborLongWallWithOpenings("neighbor house rear first floor wall with real openings", backZ, leftX, rightX, 0.07, 2.82, 0.18, materials.neighborSiding, [
    { x: cx - 3.5, width: 1.42, bottom: 1.04, top: 2.26, blockCollider: true },
    { x: cx + 2.75, width: 1.58, bottom: 1.04, top: 2.28, blockCollider: true },
  ], 0);
  addNeighborSideWallWithOpenings("neighbor house left first floor wall with real openings", leftX, backZ, frontZ, 0.07, 2.82, 0.18, materials.neighborSiding, [
    { z: cz + 2.2, width: 1.18, bottom: 1.34, top: 2.76, blockCollider: true },
  ], 0);
  addNeighborSideWallWithOpenings("neighbor house right first floor wall with real openings", rightX, backZ, frontZ, 0.07, 2.82, 0.18, materials.neighborSiding, [
    { z: cz + 3.0, width: 1.02, bottom: 1.08, top: 2.05, blockCollider: true },
  ], 0);
  addNeighborLongWallWithOpenings("neighbor house front second floor wall with real openings", frontZ, leftX, rightX, 3.0, 2.35, 0.18, materials.neighborSiding, [
    { x: cx - 4.25, width: 1.18, bottom: 3.52, top: 4.7, blockCollider: true },
    { x: cx - 0.25, width: 1.18, bottom: 3.52, top: 4.7, blockCollider: true },
  ], 1);
  addNeighborLongWallWithOpenings("neighbor house rear second floor wall with real openings", backZ, leftX, rightX, 3.0, 2.35, 0.18, materials.neighborSiding, [
    { x: cx - 2.3, width: 1.18, bottom: 3.52, top: 4.7, blockCollider: true },
    { x: cx + 3.0, width: 1.18, bottom: 3.52, top: 4.7, blockCollider: true },
  ], 1);
  addNeighborSideWallWithOpenings("neighbor house left second floor wall with real openings", leftX, backZ, frontZ, 3.0, 2.35, 0.18, materials.neighborSiding, [], 1);
  addNeighborSideWallWithOpenings("neighbor house right second floor wall with real openings", rightX, backZ, frontZ, 3.0, 2.35, 0.18, materials.neighborSiding, [
    { z: cz - 2.5, width: 0.98, bottom: 3.62, top: 4.62, blockCollider: true },
  ], 1);

  addNeighborMasonryBase("neighbor three bedroom test house", cx, cz, width, depth);
  addNeighborSidingBands("neighbor three bedroom test house", cx, cz, width, depth);

  addBox("neighbor front belt trim", cx, 2.9, frontZ + 0.1, width + 0.35, 0.11, 0.14, materials.windowFrame, false);
  addBox("neighbor rear belt trim", cx, 2.9, backZ - 0.1, width + 0.35, 0.11, 0.14, materials.windowFrame, false);
  addBox("neighbor left belt trim", leftX - 0.1, 2.9, cz, 0.14, 0.11, depth + 0.35, materials.windowFrame, false);
  addBox("neighbor right belt trim", rightX + 0.1, 2.9, cz, 0.14, 0.11, depth + 0.35, materials.windowFrame, false);

  neighborFallbackDoorGroup = new THREE.Group();
  neighborFallbackDoorGroup.name = "neighbor fallback front door until imported model loads";
  scene.add(neighborFallbackDoorGroup);
  const fallbackDoor = new THREE.Mesh(new THREE.BoxGeometry(1.08, 2.16, 0.12), materials.neighborDoorWood);
  fallbackDoor.position.set(doorX - 0.34, 1.18, frontZ + 0.23);
  fallbackDoor.rotation.y = -0.62;
  fallbackDoor.castShadow = true;
  fallbackDoor.receiveShadow = true;
  neighborFallbackDoorGroup.add(fallbackDoor);
  for (const sx of [-0.78, 0.78]) {
    const sidelight = new THREE.Mesh(new THREE.BoxGeometry(0.36, 1.8, 0.055), materials.glass);
    sidelight.position.set(doorX + sx, 1.27, frontZ + 0.17);
    neighborFallbackDoorGroup.add(sidelight);
  }
  addBox("neighbor fallback door header trim", doorX, 2.38, frontZ + 0.19, 2.1, 0.12, 0.08, materials.windowFrame, false);
  addBox("neighbor front door brass handle", doorX + 0.36, 1.13, frontZ + 0.22, 0.08, 0.36, 0.08, materials.handle, false);
  addFloorTile("neighbor visible foyer floor through usable front door", doorX, frontZ - 1.05, 2.55, 2.2, materials.floor, 0.075);
  neighborHouseDoorLeaf = addDoorLeafToScene("neighbor three bedroom working front door", doorX, frontZ + 0.23, 1.08, 2.16);
  doorColliders.push({ x: doorX, z: frontZ + 0.23, sx: 1.18, sz: 0.35, floor: 0, active: () => !neighborHouseDoorOpen });
  neighborDoorStatus = {
    initialized: true,
    position: { x: doorX, z: frontZ + 0.23 },
  };
  setNeighborHouseDoorOpen(false);
  addNeighborInteriorLayout(cx, cz, width, depth, doorX, frontZ);

  addBox("neighbor porch left column", doorX - 1.9, 1.35, frontZ + 0.9, 0.18, 2.6, 0.18, materials.neighborStone, true);
  addBox("neighbor porch right column", doorX + 1.9, 1.35, frontZ + 0.9, 0.18, 2.6, 0.18, materials.neighborStone, true);
  addBox("neighbor porch beam", doorX, 2.72, frontZ + 0.9, 4.15, 0.18, 0.22, materials.windowFrame, false);
  addGableRoof("neighbor porch gable roof", doorX, 2.82, frontZ + 0.75, 4.55, 2.05, 0.72, materials.neighborRoof);
  addBox("neighbor porch warm wall sconce", doorX - 1.04, 1.72, frontZ + 0.19, 0.14, 0.32, 0.08, materials.neighborWarmLight, false);

  addGableRoof("neighbor main dark gable roof", cx, 5.28, cz, width + 1.35, depth + 1.75, 1.42, materials.neighborRoof);
  addBox("neighbor roof front fascia", cx, 5.22, frontZ + 0.95, width + 1.55, 0.18, 0.18, materials.windowFrame, false);
  addBox("neighbor roof rear fascia", cx, 5.22, backZ - 0.95, width + 1.55, 0.18, 0.18, materials.windowFrame, false);
  addGableRoof("neighbor front bedroom dormer roof", cx + 2.75, 5.72, frontZ + 0.18, 2.45, 2.05, 0.62, materials.neighborRoof);
  addBox("neighbor front bedroom dormer face", cx + 2.75, 4.95, frontZ + 0.72, 2.05, 1.25, 0.16, materials.neighborSiding, false);
  addNeighborFacadeWindow("neighbor dormer bedroom window", cx + 2.75, 4.92, frontZ + 0.82, 0.9, 0.82, 1);

  addNeighborFacadeWindow("neighbor living room picture window", cx + 1.25, 1.7, frontZ, 1.55, 1.24, 1);
  addNeighborFacadeWindow("neighbor dining room front window", cx + 4.15, 1.68, frontZ, 1.25, 1.18, 1);
  addNeighborFacadeWindow("neighbor upstairs front bedroom one window", cx - 4.25, 4.1, frontZ, 1.12, 1.1, 1);
  addNeighborFacadeWindow("neighbor upstairs front bedroom two window", cx - 0.25, 4.1, frontZ, 1.12, 1.1, 1);
  addNeighborFacadeWindow("neighbor rear kitchen window", cx - 3.5, 1.62, backZ, 1.35, 1.12, -1);
  addNeighborFacadeWindow("neighbor rear family room window", cx + 2.75, 1.62, backZ, 1.5, 1.18, -1);
  addNeighborFacadeWindow("neighbor rear bedroom window left", cx - 2.3, 4.08, backZ, 1.12, 1.1, -1);
  addNeighborFacadeWindow("neighbor rear bedroom window right", cx + 3.0, 4.08, backZ, 1.12, 1.1, -1);
  addNeighborSideWindow("neighbor left stair side window", leftX, 2.05, cz + 2.2, 1.1, 1.25, -1);
  addNeighborSideWindow("neighbor right garage side window", rightX, 1.55, cz + 3.0, 0.95, 0.95, 1);
  addNeighborSideWindow("neighbor right upstairs bath window", rightX, 4.12, cz - 2.5, 0.9, 0.95, 1);

  addBox("neighbor attached garage door panel", rightX - 1.45, 1.18, frontZ + 0.12, 2.6, 2.05, 0.12, materials.neighborShutter, false);
  for (let i = 0; i < 5; i += 1) {
    addBox("neighbor garage panel horizontal groove", rightX - 1.45, 0.38 + i * 0.38, frontZ + 0.2, 2.45, 0.035, 0.04, materials.windowFrame, false);
  }

  addBox("neighbor chimney brick stack", cx + 4.3, 6.12, cz - 3.7, 0.62, 1.5, 0.72, materials.neighborBrick, false);
  addBox("neighbor chimney cap", cx + 4.3, 6.92, cz - 3.7, 0.88, 0.14, 0.94, materials.neighborStone, false);
  addBox("neighbor planter box left of porch", doorX - 2.65, 0.34, frontZ + 0.76, 1.05, 0.36, 0.42, materials.livingWood, false);
  addCylinder("neighbor planter shrub left", doorX - 2.88, 0.76, frontZ + 0.76, 0.22, 0.52, materials.plantLeaf, false);
  addCylinder("neighbor planter shrub right", doorX - 2.45, 0.76, frontZ + 0.76, 0.2, 0.48, materials.plantLeaf, false);
  addBox("neighbor mailbox post", doorX - 3.55, 0.52, 15.95, 0.12, 0.9, 0.12, materials.neighborDoorWood, false);
  addBox("neighbor mailbox box", doorX - 3.55, 1.0, 15.95, 0.58, 0.3, 0.34, materials.neighborShutter, false);

  interactZones.push({
    name: "neighbor three bedroom test house front porch",
    x: doorX,
    z: frontZ + 1.0,
    floor: 0,
    radius: 1.2,
    action: () => {
      setNeighborHouseDoorOpen(!neighborHouseDoorOpen);
      show(neighborHouseDoorOpen ? "Neighbor test house front door open." : "Neighbor test house front door closed.");
    },
  });

  neighborHouseReferenceStatus = {
    ...neighborHouseReferenceStatus,
    exteriorScaffold: "3 bedroom neighbor test house with separated lot, porch, driveway, dormer, stone base, siding, garage, imported closed-door reference, and working open-door collider.",
    furnishedInterior: "Visible living room, dining room, kitchen, full bathroom, primary bedroom, two secondary bedrooms, desks, bookshelves, lamps, beds, appliances, and real window glass for exterior inspection.",
    position: { x: cx, z: cz },
    gapMetersFromCurrentHouseEastWall: Number((leftX - 8).toFixed(1)),
  };
  loadNeighborEntryDoorReference(doorX, frontZ);
}

function addNeighborHouse() {
  const cx = 30.2;
  const cz = 3.2;
  const width = 13.4;
  const depth = 12.4;
  const frontZ = cz + depth / 2;
  const backZ = cz - depth / 2;
  const leftX = cx - width / 2;
  const rightX = cx + width / 2;
  const doorX = cx - 0.45;

  addFloorTile("neighbor brick ranch separated grass lot", cx, cz + 0.4, 17.5, 16.8, materials.grass, -0.018);
  addFloorTile("neighbor brick ranch foundation slab", cx, cz, width + 0.75, depth + 0.75, materials.sidewalk, 0.04);
  addFloorTile("neighbor brick ranch porch landing", doorX, frontZ + 0.92, 3.6, 1.62, materials.neighborStone, 0.065);
  addFloorTile("neighbor front walk to street", doorX, 13.75, 1.45, 7.35, materials.sidewalk, 0.035);
  addFloorTile("neighbor right driveway concrete", rightX - 0.78, 13.1, 3.35, 8.35, materials.sidewalk, 0.03);
  addBox("neighbor driveway expansion joint front", rightX - 0.78, 0.07, 16.2, 3.1, 0.035, 0.035, materials.windowFrame, false);
  addBox("neighbor driveway expansion joint rear", rightX - 0.78, 0.07, 10.15, 3.1, 0.035, 0.035, materials.windowFrame, false);

  addNeighborLongWallWithOpenings("neighbor brick ranch front wall with actual openings", frontZ, leftX, rightX, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { x: doorX, width: 1.9, bottom: 0.07, top: 2.5, blockCollider: false },
    { x: cx - 3.9, width: 1.9, bottom: 0.98, top: 2.28, blockCollider: true },
    { x: cx + 3.35, width: 1.65, bottom: 1.02, top: 2.24, blockCollider: true },
  ], 0);
  addNeighborLongWallWithOpenings("neighbor brick ranch rear bedroom wall with actual openings", backZ, leftX, rightX, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { x: cx - 4.1, width: 1.2, bottom: 1.05, top: 2.18, blockCollider: true },
    { x: cx - 0.2, width: 1.2, bottom: 1.05, top: 2.18, blockCollider: true },
    { x: cx + 3.7, width: 1.2, bottom: 1.05, top: 2.18, blockCollider: true },
  ], 0);
  addNeighborSideWallWithOpenings("neighbor brick ranch left wall with actual openings", leftX, backZ, frontZ, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { z: cz - 2.0, width: 1.18, bottom: 1.05, top: 2.18, blockCollider: true },
    { z: cz + 3.2, width: 1.2, bottom: 1.05, top: 2.18, blockCollider: true },
  ], 0);
  addNeighborSideWallWithOpenings("neighbor brick ranch right wall with actual openings", rightX, backZ, frontZ, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { z: cz - 2.0, width: 1.18, bottom: 1.05, top: 2.18, blockCollider: true },
    { z: cz + 3.0, width: 1.1, bottom: 1.08, top: 2.12, blockCollider: true },
  ], 0);

  addNeighborMasonryBase("neighbor brick ranch", cx, cz, width, depth);
  addBox("neighbor brick ranch front trim band", cx, 2.9, frontZ + 0.12, width + 0.42, 0.11, 0.14, materials.windowFrame, false);
  addBox("neighbor brick ranch rear trim band", cx, 2.9, backZ - 0.12, width + 0.42, 0.11, 0.14, materials.windowFrame, false);
  addBox("neighbor brick ranch left trim band", leftX - 0.12, 2.9, cz, 0.14, 0.11, depth + 0.42, materials.windowFrame, false);
  addBox("neighbor brick ranch right trim band", rightX + 0.12, 2.9, cz, 0.14, 0.11, depth + 0.42, materials.windowFrame, false);

  neighborFallbackDoorGroup = null;
  addBox("neighbor brick ranch door header trim", doorX, 2.38, frontZ + 0.19, 2.1, 0.12, 0.08, materials.windowFrame, false);
  addFloorTile("neighbor clear walk-in foyer floor", doorX, frontZ - 1.35, 2.75, 2.8, materials.floor, 0.085);
  neighborHouseDoorLeaf = addDoorLeafToScene("neighbor brick ranch working front door", doorX, frontZ + 0.23, 1.08, 2.16);
  doorColliders.push({ x: doorX, z: frontZ + 0.23, sx: 1.18, sz: 0.35, floor: 0, active: () => !neighborHouseDoorOpen });
  neighborDoorStatus = {
    initialized: true,
    position: { x: doorX, z: frontZ + 0.23 },
  };
  setNeighborHouseDoorOpen(false);

  addFloorTile("neighbor living room front wood floor", cx - 3.6, cz + 3.1, 4.5, 4.55, materials.floor, 0.088);
  addFloorTile("neighbor dining room front wood floor", cx + 3.2, cz + 3.15, 3.55, 3.6, materials.floor, 0.089);
  addFloorTile("neighbor kitchen tile floor", cx + 3.15, cz + 0.52, 3.8, 3.0, materials.sidewalk, 0.09);
  addFloorTile("neighbor bedroom hall wood floor", cx - 0.1, cz - 0.98, 2.45, 4.75, materials.floor, 0.09);
  addFloorTile("neighbor primary rear bedroom floor", cx - 4.15, cz - 2.25, 3.65, 3.25, materials.floor, 0.09);
  addFloorTile("neighbor middle rear bedroom floor", cx - 0.15, cz - 2.25, 3.35, 3.25, materials.floor, 0.09);
  addFloorTile("neighbor right rear bedroom floor", cx + 3.75, cz - 2.25, 3.45, 3.25, materials.floor, 0.09);

  addNeighborInteriorWall("neighbor rear bedroom privacy wall left segment", cx - 3.9, cz + 0.78, 3.25, 0.12);
  addNeighborInteriorWall("neighbor rear bedroom privacy wall right segment", cx + 3.55, cz + 0.78, 3.4, 0.12);
  addNeighborInteriorWall("neighbor primary middle bedroom divider", cx - 2.14, cz - 2.08, 0.12, 4.25);
  addNeighborInteriorWall("neighbor middle right bedroom divider", cx + 1.82, cz - 2.08, 0.12, 4.25);
  addNeighborInteriorWall("neighbor bath and kitchen divider", cx + 1.1, cz + 0.05, 0.12, 2.15);
  addNeighborInteriorDoor("neighbor primary bedroom rear door", cx - 4.02, cz + 0.84, "z");
  addNeighborInteriorDoor("neighbor middle bedroom rear door", cx - 0.15, cz + 0.84, "z");
  addNeighborInteriorDoor("neighbor right bedroom rear door", cx + 3.62, cz + 0.84, "z");
  addNeighborInteriorDoor("neighbor hallway bathroom door", cx + 1.1, cz + 1.04, "x");

  loadNeighborLivingRoomFurniture(cx - 3.75, cz + 4.2, Math.PI);
  placeNeighborApartmentNode({ name: "neighbor imported dining table and chairs", pattern: /outdoor_table_and_chairs/i, x: cx + 3.2, z: cz + 4.05, width: 2.35, height: 1.2, depth: 2.2, yaw: Math.PI, uniform: true });
  placeNeighborImportedBed({ name: "neighbor primary imported bed BED_022_1", x: cx - 4.25, z: cz - 2.7, width: 1.85, depth: 2.25, height: 0.95, yaw: 0 });
  placeNeighborImportedBed({ name: "neighbor middle imported bed BED_022_1", x: cx - 0.18, z: cz - 2.7, width: 1.55, depth: 2.08, height: 0.86, yaw: 0 });
  placeNeighborImportedBed({ name: "neighbor right imported bed BED_022_1", x: cx + 3.72, z: cz - 2.7, width: 1.55, depth: 2.08, height: 0.86, yaw: 0 });

  addBox("neighbor porch left brick column", doorX - 1.9, 1.35, frontZ + 0.86, 0.22, 2.55, 0.22, materials.neighborBrick, true);
  addBox("neighbor porch right brick column", doorX + 1.9, 1.35, frontZ + 0.86, 0.22, 2.55, 0.22, materials.neighborBrick, true);
  addBox("neighbor porch beam", doorX, 2.7, frontZ + 0.86, 4.05, 0.18, 0.22, materials.windowFrame, false);
  addGableRoof("neighbor brick ranch porch gable roof", doorX, 2.78, frontZ + 0.72, 4.4, 1.95, 0.62, materials.neighborRoof);
  addBox("neighbor porch warm wall sconce", doorX - 1.04, 1.72, frontZ + 0.19, 0.14, 0.32, 0.08, materials.neighborWarmLight, false);

  addGableRoof("neighbor brick ranch low main roof", cx, 3.05, cz, width + 1.55, depth + 1.7, 0.96, materials.neighborRoof);
  addBox("neighbor ranch roof front fascia", cx, 3.08, frontZ + 0.9, width + 1.7, 0.16, 0.18, materials.windowFrame, false);
  addBox("neighbor ranch roof rear fascia", cx, 3.08, backZ - 0.9, width + 1.7, 0.16, 0.18, materials.windowFrame, false);

  addNeighborFacadeWindow("neighbor living room front real window", cx - 3.9, 1.62, frontZ, 1.78, 1.22, 1);
  addNeighborFacadeWindow("neighbor dining room front real window", cx + 3.35, 1.62, frontZ, 1.52, 1.16, 1);
  addNeighborFacadeWindow("neighbor rear primary bedroom real window", cx - 4.1, 1.62, backZ, 1.08, 1.08, -1);
  addNeighborFacadeWindow("neighbor rear middle bedroom real window", cx - 0.2, 1.62, backZ, 1.08, 1.08, -1);
  addNeighborFacadeWindow("neighbor rear right bedroom real window", cx + 3.7, 1.62, backZ, 1.08, 1.08, -1);
  addNeighborSideWindow("neighbor left living side real window", leftX, 1.62, cz + 3.2, 1.08, 1.08, -1);
  addNeighborSideWindow("neighbor left bedroom side real window", leftX, 1.62, cz - 2.0, 1.08, 1.08, -1);
  addNeighborSideWindow("neighbor right kitchen side real window", rightX, 1.58, cz + 3.0, 1.02, 1.0, 1);
  addNeighborSideWindow("neighbor right bedroom side real window", rightX, 1.62, cz - 2.0, 1.08, 1.08, 1);

  addBox("neighbor attached garage door panel", rightX - 1.34, 1.18, frontZ + 0.12, 2.4, 2.05, 0.12, materials.neighborShutter, false);
  for (let i = 0; i < 5; i += 1) {
    addBox("neighbor garage panel horizontal groove", rightX - 1.34, 0.38 + i * 0.38, frontZ + 0.2, 2.25, 0.035, 0.04, materials.windowFrame, false);
  }

  addBox("neighbor brick ranch chimney stack", cx + 5.0, 3.65, cz - 2.2, 0.58, 1.1, 0.66, materials.neighborBrick, false);
  addBox("neighbor brick ranch chimney cap", cx + 5.0, 4.24, cz - 2.2, 0.82, 0.12, 0.88, materials.neighborStone, false);
  addBox("neighbor planter box left of porch", doorX - 2.65, 0.34, frontZ + 0.76, 1.05, 0.36, 0.42, materials.livingWood, false);
  addCylinder("neighbor planter shrub left", doorX - 2.88, 0.76, frontZ + 0.76, 0.22, 0.52, materials.plantLeaf, false);
  addCylinder("neighbor planter shrub right", doorX - 2.45, 0.76, frontZ + 0.76, 0.2, 0.48, materials.plantLeaf, false);
  addBox("neighbor mailbox post", doorX - 3.6, 0.52, 15.95, 0.12, 0.9, 0.12, materials.neighborDoorWood, false);
  addBox("neighbor mailbox box", doorX - 3.6, 1.0, 15.95, 0.58, 0.3, 0.34, materials.neighborShutter, false);

  interactZones.push({
    name: "neighbor brick ranch front porch",
    x: doorX,
    z: frontZ + 1.0,
    floor: 0,
    radius: 1.55,
    action: () => {
      setNeighborHouseDoorOpen(!neighborHouseDoorOpen);
      show(neighborHouseDoorOpen ? "Neighbor brick ranch front door open." : "Neighbor brick ranch front door closed.");
    },
  });

  neighborHouseReferenceStatus = {
    ...neighborHouseReferenceStatus,
    exteriorScaffold: "Replacement 3 bedroom brick ranch test house with actual window openings, porch, driveway, garage door panel, and a clean working front door without the barred decorative entry model.",
    furnishedInterior: "The visible test furniture is imported: living room sofa/chair props, dining table/chairs, and three BED_022_1 beds from the preserved apartment reference. Block-built kitchen, bath, desk, and nightstand placeholders were removed from this active test house.",
    layoutFix: "No bed is staged in the front room. The walk-in door opens into a clear foyer/living area.",
    entryDoorLoaded: false,
    entryDoorSkippedReason: "entry_door_with_sidelights.glb looked barred across the front entrance in the inspection screenshots, so it is preserved in the library but not placed on this test house.",
    position: { x: cx, z: cz },
    gapMetersFromCurrentHouseEastWall: Number((leftX - 8).toFixed(1)),
  };
}

function addNeighborPrefabBedSet(label, x, z, yaw = 0) {
  placeNeighborPrefabWholeModel(NEIGHBOR_PREFAB_BED_FRAME_MODEL_URL, {
    role: `${label} frame`,
    name: `${label} imported real bed frame`,
    x,
    y: 0.08,
    z,
    width: 1.86,
    height: 0.68,
    depth: 2.25,
    yaw,
    truthKind: "bed",
    truthLabel: `${label} bed frame`,
    actionHints: ["sit", "sleep", "lay_down"],
  });
  placeNeighborPrefabWholeModel(NEIGHBOR_PREFAB_MATTRESS_MODEL_URL, {
    role: `${label} mattress`,
    name: `${label} imported real mattress`,
    x,
    y: 0.5,
    z: z + 0.03,
    width: 1.58,
    height: 0.34,
    depth: 1.96,
    yaw,
    truthKind: "bed",
    truthLabel: `${label} mattress`,
    actionHints: ["sleep", "lay_down"],
  });
  placeNeighborPrefabWholeModel(NEIGHBOR_PREFAB_PILLOW_MODEL_URL, {
    role: `${label} pillow`,
    name: `${label} imported real pillow`,
    x,
    y: 0.76,
    z: z - 0.73,
    width: 0.68,
    height: 0.18,
    depth: 0.36,
    yaw,
    truthKind: "bed",
    truthLabel: `${label} pillow`,
    actionHints: ["sleep", "lay_down"],
  });
}

function localPointByYaw(x, z, dx, dz, yaw = 0) {
  const cos = Math.cos(yaw);
  const sin = Math.sin(yaw);
  return {
    x: x + dx * cos + dz * sin,
    z: z - dx * sin + dz * cos,
  };
}

function cloneOneBedroomMaterialInstances(root) {
  root.traverse((node) => {
    node.userData = { ...(node.userData || {}) };
    if (!node.isMesh || !node.material) return;
    node.material = Array.isArray(node.material)
      ? node.material.map((mat) => (mat?.clone ? mat.clone() : mat))
      : node.material.clone ? node.material.clone() : node.material;
  });
}

function tagOneBedroomHomeCopy(root, config) {
  root.userData = {
    ...(root.userData || {}),
    copiedOneBedroomHome: true,
    sourceHome: "Kira's Home",
    residentHomeId: config.id,
    residentOwner: config.owner,
  };
  root.traverse((node) => {
    node.userData = {
      ...(node.userData || {}),
      copiedOneBedroomHome: true,
      sourceHome: "Kira's Home",
      residentHomeId: config.id,
      residentOwner: config.owner,
    };
    if (node.isMesh) {
      node.castShadow = true;
      node.receiveShadow = true;
    }
  });
}

function addOneBedroomImportedModelCopy(source, placement, config) {
  const root = source.clone(true);
  root.name = `${config.title} copy ${placement.name || placement.role || "one-bedroom model"}`;
  cloneOneBedroomMaterialInstances(root);
  tagOneBedroomHomeCopy(root, config);
  const meshCount = makeImportedAssetMaterials(root);
  if (placement.postProcess) placement.postProcess(root);
  root.rotation.y = placement.yaw || 0;
  scene.add(root);
  fitObjectToMeshBox(root, {
    x: placement.x + config.offsetX,
    y: placement.y ?? 0.08,
    z: placement.z + (config.offsetZ || 0),
    width: placement.width,
    height: placement.height,
    depth: placement.depth,
    uniform: placement.uniform ?? false,
  });
  if (placement.truthKind) {
    markTruthProp(root, placement.truthKind, `${config.title} ${placement.truthLabel || placement.name}`, placement.floor ?? 0, placement.actionHints || []);
  }
  return { root, meshCount };
}

function placeOneBedroomModel(url, placement) {
  const source = oneBedroomPrefabSourceCache.get(url);
  if (!source) {
    if (!pendingOneBedroomPrefabPlacements.has(url)) pendingOneBedroomPrefabPlacements.set(url, []);
    pendingOneBedroomPrefabPlacements.get(url).push(placement);
    gltfLoader.load(
      url,
      (gltf) => {
        oneBedroomPrefabSourceCache.set(url, gltf.scene);
        const queued = pendingOneBedroomPrefabPlacements.get(url) || [];
        pendingOneBedroomPrefabPlacements.delete(url);
        for (const item of queued) placeOneBedroomModel(url, item);
      },
      undefined,
      (error) => {
        oneBedroomBlueprintHouseStatus = {
          ...oneBedroomBlueprintHouseStatus,
          loadErrors: [
            ...(oneBedroomBlueprintHouseStatus.loadErrors || []),
            { url, error: error?.message || String(error) },
          ],
        };
        console.warn("Could not load one-bedroom blueprint model", url, error);
      },
    );
    return false;
  }
  const root = source.clone(true);
  root.name = placement.name;
  const meshCount = makeImportedAssetMaterials(root);
  if (placement.postProcess) placement.postProcess(root);
  root.rotation.y = placement.yaw || 0;
  scene.add(root);
  const fittedSize = fitObjectToMeshBox(root, {
    x: placement.x,
    y: placement.y ?? 0.08,
    z: placement.z,
    width: placement.width,
    height: placement.height,
    depth: placement.depth,
    uniform: placement.uniform ?? false,
  });
  if (placement.truthKind) {
    markTruthProp(root, placement.truthKind, placement.truthLabel || placement.name, placement.floor ?? 0, placement.actionHints || []);
  }
  if (placement.onPlaced) placement.onPlaced(root);
  if (oneBedroomCopyReplicationArmed && placement.copyToOneBedroomNeighbors !== false) {
    for (const config of ONE_BEDROOM_HOME_WORLD_COPY_CONFIGS) {
      addOneBedroomImportedModelCopy(source, placement, config);
    }
  }
  oneBedroomBlueprintHouseStatus = {
    ...oneBedroomBlueprintHouseStatus,
    importedPlacements: {
      ...(oneBedroomBlueprintHouseStatus.importedPlacements || {}),
      [placement.role || placement.name]: {
        url,
        meshCount,
        x: Number(fittedSize.x.toFixed(2)),
        y: Number(fittedSize.y.toFixed(2)),
        z: Number(fittedSize.z.toFixed(2)),
      },
    },
  };
  return true;
}

function addOpenFacadeWindowFrame(name, x, y, z, width = 1.22, height = 1.22, zSign = 1) {
  const surfaceZ = z + zSign * 0.13;
  addBox(`${name} empty opening left casing`, x - width * 0.5 - 0.055, y, surfaceZ, 0.08, height + 0.25, 0.09, materials.windowFrame, false, 0);
  addBox(`${name} empty opening right casing`, x + width * 0.5 + 0.055, y, surfaceZ, 0.08, height + 0.25, 0.09, materials.windowFrame, false, 0);
  addBox(`${name} empty opening top casing`, x, y + height * 0.5 + 0.06, surfaceZ, width + 0.25, 0.08, 0.09, materials.windowFrame, false, 0);
  addBox(`${name} empty opening bottom casing`, x, y - height * 0.5 - 0.06, surfaceZ, width + 0.25, 0.08, 0.09, materials.windowFrame, false, 0);
  addBox(`${name} stone sill`, x, y - height * 0.5 - 0.17, surfaceZ + zSign * 0.04, width + 0.42, 0.1, 0.22, materials.neighborStone, false, 0);
}

function addOpenSideWindowFrame(name, x, y, z, width = 1.1, height = 1.18, xSign = 1) {
  const surfaceX = x + xSign * 0.13;
  addBox(`${name} empty opening left casing`, surfaceX, y, z - width * 0.5 - 0.055, 0.09, height + 0.25, 0.08, materials.windowFrame, false, 0);
  addBox(`${name} empty opening right casing`, surfaceX, y, z + width * 0.5 + 0.055, 0.09, height + 0.25, 0.08, materials.windowFrame, false, 0);
  addBox(`${name} empty opening top casing`, surfaceX, y + height * 0.5 + 0.06, z, 0.09, 0.08, width + 0.25, materials.windowFrame, false, 0);
  addBox(`${name} empty opening bottom casing`, surfaceX, y - height * 0.5 - 0.06, z, 0.09, 0.08, width + 0.25, materials.windowFrame, false, 0);
  addBox(`${name} stone sill`, surfaceX + xSign * 0.04, y - height * 0.5 - 0.17, z, 0.22, 0.1, width + 0.42, materials.neighborStone, false, 0);
}

function closeOneBedroomFridgeDoors(root) {
  root.traverse((node) => {
    if (node.name === "DoorBottom" || node.name === "DoorTop") {
      node.rotation.set(0, 0, 0);
      node.quaternion.identity();
      node.updateMatrix();
    }
  });
  root.updateMatrixWorld(true);
}

function addOneBedroomFrontEntryTrim(name, z, x, width, floor = 0) {
  const y = floorBase(floor);
  const surfaceZ = z + 0.245;
  addBox(`${name} left jamb`, x - width * 0.5, y + 1.17, surfaceZ, 0.1, 2.32, 0.08, materials.windowFrame, false, floor);
  addBox(`${name} right jamb`, x + width * 0.5, y + 1.17, surfaceZ, 0.1, 2.32, 0.08, materials.windowFrame, false, floor);
  addBox(`${name} raised header`, x, y + 2.42, surfaceZ, width + 0.22, 0.14, 0.08, materials.windowFrame, false, floor);
  addBox(`${name} threshold`, x, y + 0.035, z + 0.16, width + 0.28, 0.07, 0.32, materials.neighborStone, false, floor);
}

function addOneBedroomBedSet(label, x, z, yaw = 0, pillowHeadOffsetX = -0.88) {
  placeOneBedroomModel(ONE_BEDROOM_WOOD_BED_FRAME_MODEL_URL, {
    role: `${label} frame`,
    name: `${label} imported all wood bed frame`,
    x,
    y: 0.08,
    z,
    width: 2.48,
    height: 0.72,
    depth: 1.95,
    yaw,
    truthKind: "bed",
    truthLabel: `${label} all wood bed frame`,
    actionHints: ["sit", "sleep", "lay_down"],
  });
  const sideRailA = localPointByYaw(x, z, 0.08, -0.82, yaw);
  const sideRailB = localPointByYaw(x, z, 0.08, 0.82, yaw);
  const footRail = localPointByYaw(x, z, 1.06, 0, yaw);
  addOneBedroomRotatedBox(`${label} visible left bed rail support`, sideRailA.x, 0.34, sideRailA.z, 2.12, 0.11, 0.08, materials.wood, yaw);
  addOneBedroomRotatedBox(`${label} visible right bed rail support`, sideRailB.x, 0.34, sideRailB.z, 2.12, 0.11, 0.08, materials.wood, yaw);
  addOneBedroomRotatedBox(`${label} visible foot rail support`, footRail.x, 0.36, footRail.z, 0.08, 0.14, 1.62, materials.wood, yaw);
  for (let i = 0; i < 6; i += 1) {
    const slat = localPointByYaw(x, z, -0.68 + i * 0.29, 0, yaw);
    addOneBedroomRotatedBox(`${label} separate mattress slat ${i + 1}`, slat.x, 0.38, slat.z, 0.07, 0.04, 1.46, materials.windowFrame, yaw);
  }
  const mattressCenter = localPointByYaw(x, z, 0.08, 0, yaw);
  const mattress = markTruthProp(
    addOneBedroomRotatedBox(`${label} temporary white mattress placeholder`, mattressCenter.x, 0.55, mattressCenter.z, 2.18, 0.3, 1.62, materials.mattress, yaw),
    "bed",
    `${label} temporary white mattress`,
    0,
    ["sleep", "lay_down"],
  );
  mattress.userData.temporaryReplacement = true;
  mattress.userData.reason = "Imported mattress model rendered invisible in one-bedroom bed; use visible temporary mattress until the GLB is repaired.";
  for (const [index, offset] of [-0.34, 0.34].entries()) {
    const pillow = localPointByYaw(x, z, pillowHeadOffsetX, offset, yaw);
    const pillowMesh = markTruthProp(
      addOneBedroomRotatedBox(`${label} temporary pillow ${index + 1} returned to prior orientation`, pillow.x, 0.77, pillow.z, 0.34, 0.11, 0.56, materials.mattress, yaw),
      "pillow",
      `${label} temporary pillow ${index + 1}`,
      0,
      ["sleep", "lay_down"],
    );
    pillowMesh.userData.temporaryReplacement = true;
    pillowMesh.userData.orientation = "returned to the prior temporary pillow orientation Robert preferred";
  }
  const rotated = Math.abs(Math.sin(yaw)) > 0.7;
  colliders.push({ x, z, sx: rotated ? 1.98 : 2.52, sz: rotated ? 2.52 : 1.98, floor: 0 });
}

function addOneBedroomRotatedBox(name, x, y, z, sx, sy, sz, material, yaw = 0) {
  const mesh = addBox(name, x, y, z, sx, sy, sz, material, false, 0);
  mesh.rotation.y = yaw;
  return mesh;
}

function tintOneBedroomPillow(root) {
  root.traverse((node) => {
    if (!node.isMesh) return;
    const tint = (mat) => {
      const next = mat?.clone ? mat.clone() : new THREE.MeshStandardMaterial();
      if (next.color) next.color.set(0xf2eee8);
      next.map = null;
      next.normalMap = null;
      next.roughnessMap = null;
      next.metalnessMap = null;
      next.roughness = 0.82;
      next.metalness = 0.0;
      return next;
    };
    node.material = Array.isArray(node.material) ? node.material.map(tint) : tint(node.material);
  });
}

function setOneBedroomDresserOpen(open) {
  if (!oneBedroomBedroomDresserParts) return;
  oneBedroomBedroomDresserOpen = !!open;
  for (const drawer of oneBedroomBedroomDresserParts.drawers) {
    drawer.position.x = oneBedroomBedroomDresserOpen ? drawer.userData.openX : drawer.userData.closedX;
  }
  for (const cloth of oneBedroomBedroomDresserParts.clothes) cloth.visible = oneBedroomBedroomDresserOpen;
}

function toggleOneBedroomDresser() {
  setOneBedroomDresserOpen(!oneBedroomBedroomDresserOpen);
  show(oneBedroomBedroomDresserOpen ? "Bedroom dresser opened. Clothes are stored here for outfit changes." : "Bedroom dresser closed.");
}

function addOneBedroomClothesDresser(leftX, bathFrontZ) {
  const dresserX = leftX + 0.48;
  const dresserZ = bathFrontZ + 1.35;
  const body = markTruthProp(
    addBox("one-bedroom bedroom working clothes dresser body", dresserX, 0.5, dresserZ, 0.64, 0.86, 1.58, materials.warmCabinet, true, 0),
    "closet",
    "one-bedroom bedroom clothes dresser",
    0,
    ["change_clothes", "store_clothes", "take_from_dresser"],
  );
  body.userData.clothingStorage = true;

  addBox("one-bedroom dresser back panel", dresserX - 0.34, 0.5, dresserZ, 0.06, 0.82, 1.5, materials.wood, false, 0);
  addBox("one-bedroom dresser top cap", dresserX, 0.96, dresserZ, 0.72, 0.08, 1.66, materials.livingWood, false, 0);
  addBox("one-bedroom dresser lower plinth", dresserX, 0.08, dresserZ, 0.74, 0.1, 1.66, materials.livingWood, false, 0);

  const drawers = [];
  const clothes = [];
  const frontX = dresserX + 0.34;
  for (let i = 0; i < 3; i += 1) {
    const y = 0.28 + i * 0.24;
    for (let j = 0; j < 2; j += 1) {
      const zOffset = j === 0 ? -0.39 : 0.39;
      const drawer = addBox(`one-bedroom dresser sliding drawer ${i + 1}-${j + 1}`, frontX, y, dresserZ + zOffset, 0.08, 0.18, 0.52, materials.livingWood, false, 0);
      drawer.userData.closedX = frontX;
      drawer.userData.openX = frontX + 0.32;
      addBox(`one-bedroom dresser drawer ${i + 1}-${j + 1} brass pull`, frontX + 0.055, y, dresserZ + zOffset, 0.035, 0.04, 0.26, materials.handle, false, 0);
      drawers.push(drawer);

      const cloth = markTruthProp(
        addBox(
          `one-bedroom folded clothes stack ${i + 1}-${j + 1}`,
          frontX + 0.16,
          y + 0.035,
          dresserZ + zOffset,
          0.22,
          0.045,
          0.32,
          j % 2 ? materials.blanketPink : materials.blanketBlue,
          false,
          0,
        ),
        "wearable_clothing",
        `folded dresser clothes ${i + 1}-${j + 1}`,
        0,
        ["change_clothes", "take_from_dresser"],
      );
      cloth.visible = false;
      clothes.push(cloth);
    }
  }

  oneBedroomBedroomDresserParts = { drawers, clothes };
  interactZones.push({
    name: "one-bedroom bedroom clothes dresser",
    x: dresserX + 0.62,
    z: dresserZ,
    radius: 1.35,
    floor: 0,
    action: toggleOneBedroomDresser,
  });
}

function setOneBedroomHangingClosetOpen(open) {
  if (!oneBedroomHangingClosetParts) return;
  oneBedroomHangingClosetOpen = !!open;
  for (const panel of oneBedroomHangingClosetParts.doors) {
    panel.position.z = oneBedroomHangingClosetOpen ? panel.userData.openZ : panel.userData.closedZ;
  }
  for (const handle of oneBedroomHangingClosetParts.doorHandles || []) {
    handle.position.z = oneBedroomHangingClosetOpen ? handle.userData.openZ : handle.userData.closedZ;
  }
  for (const item of oneBedroomHangingClosetParts.visibleWhenOpen) item.visible = oneBedroomHangingClosetOpen;
  oneBedroomBlueprintHouseStatus = {
    ...oneBedroomBlueprintHouseStatus,
    oneBedroomCloset: {
      open: oneBedroomHangingClosetOpen,
      supports: ["hang_clothes", "fold_clothes", "unfold_clothes", "put_on", "take_off", "send_to_laundry"],
    },
  };
}

function toggleOneBedroomHangingCloset() {
  setOneBedroomHangingClosetOpen(!oneBedroomHangingClosetOpen);
  show(oneBedroomHangingClosetOpen ? "Bedroom closet opened. Hanging clothes and folded stacks are reachable." : "Bedroom closet closed.");
}

function addOneBedroomHangingCloset(splitX, frontZ) {
  const closetX = splitX - 0.48;
  const closetZ = frontZ - 1.55;
  const back = markTruthProp(
    addBox("one-bedroom bedroom hanging closet back panel", closetX + 0.28, 1.08, closetZ, 0.08, 2.08, 1.48, materials.closetWood, false, 0),
    "closet",
    "one-bedroom hanging clothing closet",
    0,
    ["select_garment", "take_from_closet", "hang_garment", "fold_clothes", "unfold_clothes"],
  );
  back.userData.clothingSystem = {
    garmentStates: Object.values(GARMENT_STATES),
    stores: ["hanging clothes", "folded clothes", "laundry return"],
    nextUpgrade: "Attach per-garment inventory records so shirts, pants, dresses, and pajamas can fold, unfold, hang, be worn, and return to laundry.",
  };

  addBox("one-bedroom bedroom closet left side", closetX, 1.08, closetZ - 0.78, 0.64, 2.08, 0.08, materials.closetWood, false, 0);
  addBox("one-bedroom bedroom closet right side", closetX, 1.08, closetZ + 0.78, 0.64, 2.08, 0.08, materials.closetWood, false, 0);
  addBox("one-bedroom bedroom closet top shelf", closetX, 2.14, closetZ, 0.68, 0.08, 1.62, materials.closetWood, false, 0);
  addBox("one-bedroom bedroom closet lower shelf", closetX, 0.16, closetZ, 0.68, 0.08, 1.62, materials.closetWood, false, 0);
  addBox("one-bedroom bedroom closet hanger rail", closetX - 0.08, 1.62, closetZ, 0.045, 0.045, 1.26, materials.closetRail, false, 0);

  const visibleWhenOpen = [];
  const hangerZs = [-0.42, -0.18, 0.08, 0.34];
  for (let i = 0; i < hangerZs.length; i += 1) {
    const z = closetZ + hangerZs[i];
    visibleWhenOpen.push(addBox(`one-bedroom bedroom closet hanger ${i + 1}`, closetX - 0.14, 1.52, z, 0.035, 0.025, 0.34, materials.hangerWire, false, 0));
    const garment = markTruthProp(
      addBox(
        `one-bedroom hanging garment ${i + 1}`,
        closetX - 0.18,
        1.08,
        z,
        0.055,
        0.72,
        0.24,
        i % 2 ? materials.blanketPink : materials.blanketBlue,
        false,
        0,
      ),
      "wearable_clothing",
      `one-bedroom hanging garment ${i + 1}`,
      0,
      ["take_from_closet", "put_on", "take_off", "hang_garment"],
    );
    garment.userData.garmentState = GARMENT_STATES.OnHanger;
    visibleWhenOpen.push(garment);
  }

  for (let i = 0; i < 3; i += 1) {
    const stack = markTruthProp(
      addBox(
        `one-bedroom folded closet clothes stack ${i + 1}`,
        closetX - 0.14,
        0.38 + i * 0.09,
        closetZ + 0.5,
        0.2,
        0.055,
        0.38,
        i % 2 ? materials.blanketPink : materials.bookGreen,
        false,
        0,
      ),
      "wearable_clothing",
      `folded closet clothes stack ${i + 1}`,
      0,
      ["fold_clothes", "unfold_clothes", "put_on"],
    );
    stack.userData.garmentState = GARMENT_STATES.InCloset;
    visibleWhenOpen.push(stack);
  }

  const leftDoor = addBox("one-bedroom bedroom closet sliding left door", closetX - 0.34, 1.08, closetZ - 0.4, 0.055, 1.82, 0.74, materials.warmCabinet, false, 0);
  const rightDoor = addBox("one-bedroom bedroom closet sliding right door", closetX - 0.34, 1.08, closetZ + 0.4, 0.055, 1.82, 0.74, materials.warmCabinet, false, 0);
  leftDoor.userData.closedZ = closetZ - 0.4;
  leftDoor.userData.openZ = closetZ - 0.82;
  rightDoor.userData.closedZ = closetZ + 0.4;
  rightDoor.userData.openZ = closetZ + 0.82;
  const leftPull = addBox("one-bedroom bedroom closet left door pull", closetX - 0.38, 1.08, closetZ - 0.1, 0.035, 0.42, 0.045, materials.handle, false, 0);
  const rightPull = addBox("one-bedroom bedroom closet right door pull", closetX - 0.38, 1.08, closetZ + 0.1, 0.035, 0.42, 0.045, materials.handle, false, 0);
  leftPull.userData.closedZ = closetZ - 0.1;
  leftPull.userData.openZ = closetZ - 0.52;
  rightPull.userData.closedZ = closetZ + 0.1;
  rightPull.userData.openZ = closetZ + 0.52;

  oneBedroomHangingClosetParts = { doors: [leftDoor, rightDoor], doorHandles: [leftPull, rightPull], visibleWhenOpen };
  colliders.push({ x: closetX, z: closetZ, sx: 0.78, sz: 1.72, floor: 0 });
  addPrototypeGarmentCloset({ includeClosetShell: false });
  interactZones.push({
    name: "one-bedroom bedroom hanging closet",
    x: closetX - 0.95,
    z: closetZ,
    radius: 1.25,
    floor: 0,
    action: toggleOneBedroomHangingCloset,
  });
  interactZones.push({
    name: "one-bedroom prototype dress shirt dressing station",
    x: closetX - 1.0,
    z: closetZ + 0.58,
    radius: 0.62,
    floor: 0,
    action: () => {
      if (!prototypeDressShirt || !prototypeCloset || !avatarDressingController) {
        show("Prototype dress shirt is not ready yet.");
        return;
      }
      if (!oneBedroomHangingClosetOpen) setOneBedroomHangingClosetOpen(true);
      if ([GARMENT_STATES.WornClosed, GARMENT_STATES.WornOpen].includes(prototypeDressShirt.state)) {
        avatarDressingController.startRemove("closet");
        show("Starting the physical shirt-removal sequence, then returning it to the closet.");
        return;
      }
      prototypeCloset.startDressing(prototypeDressShirt);
      show("Taking the shirt from its hanger and starting the arm-through-sleeves dressing sequence.");
    },
  });
  setOneBedroomHangingClosetOpen(false);
}

function addOneBedroomBedroomStorage(leftX, splitX, bathFrontZ, frontZ) {
  addOneBedroomClothesDresser(leftX, bathFrontZ);
  addOneBedroomHangingCloset(splitX, frontZ);
}

function addOneBedroomFridgeDoorMesh(parent, name, x, y, z, sx, sy, sz, material) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), material);
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function setOneBedroomFridgeOpen(open) {
  oneBedroomFridgeOpen = !!open;
  if (oneBedroomFridgeDoorGroup) oneBedroomFridgeDoorGroup.rotation.y = oneBedroomFridgeOpen ? -Math.PI / 2 : 0;
  for (const part of oneBedroomFridgeInteriorParts) part.visible = oneBedroomFridgeOpen;
  oneBedroomBlueprintHouseStatus = {
    ...oneBedroomBlueprintHouseStatus,
    refrigerator: {
      openable: true,
      open: oneBedroomFridgeOpen,
      supports: ["open", "close", "put_food_in", "take_food_out"],
    },
  };
}

function toggleOneBedroomFridge() {
  setOneBedroomFridgeOpen(!oneBedroomFridgeOpen);
  show(oneBedroomFridgeOpen ? "Refrigerator opened. Shelves and food are reachable." : "Refrigerator closed.");
}

function addOneBedroomClosedRefrigerator(x, z) {
  const body = markTruthProp(
    addBox("one-bedroom closed refrigerator body", x, 1.04, z, 0.82, 1.92, 0.76, materials.fixture, true, 0),
    "refrigerator",
    "one-bedroom openable kitchen refrigerator",
    0,
    ["open_fridge", "close_fridge", "put_food_in", "get_food", "make_coffee"],
  );
  oneBedroomFridgeInteriorParts = [
    addBox("one-bedroom refrigerator cold interior back", x - 0.42, 1.02, z, 0.035, 1.48, 0.64, materials.closetInterior, false, 0),
    addBox("one-bedroom refrigerator middle shelf", x - 0.45, 1.05, z, 0.04, 0.035, 0.58, materials.glass, false, 0),
    addBox("one-bedroom refrigerator upper shelf", x - 0.45, 1.38, z, 0.04, 0.035, 0.58, materials.glass, false, 0),
    markTruthProp(addBox("one-bedroom refrigerator milk carton", x - 0.48, 1.18, z - 0.16, 0.09, 0.28, 0.12, materials.fixture, false, 0), "milk", "milk carton in Kira's refrigerator", 0, ["drink", "eat_food", "get_food"]),
    markTruthProp(addBox("one-bedroom refrigerator greens container", x - 0.48, 0.82, z + 0.12, 0.1, 0.12, 0.2, materials.produceGreen, false, 0), "food", "greens container in Kira's refrigerator", 0, ["eat_food", "get_food"]),
    markTruthProp(addCylinder("one-bedroom refrigerator drink bottle", x - 0.48, 1.47, z + 0.17, 0.045, 0.3, materials.activeBlue, false, 0), "cup", "drink bottle in Kira's refrigerator", 0, ["drink", "get_drink"]),
  ];
  oneBedroomFridgeDoorGroup = new THREE.Group();
  oneBedroomFridgeDoorGroup.name = "one-bedroom refrigerator hinged door group";
  oneBedroomFridgeDoorGroup.position.set(x - 0.43, 0, z - 0.34);
  scene.add(oneBedroomFridgeDoorGroup);
  addOneBedroomFridgeDoorMesh(oneBedroomFridgeDoorGroup, "one-bedroom refrigerator freezer door leaf", 0, 1.45, 0.34, 0.045, 0.72, 0.68, materials.windowFrame);
  addOneBedroomFridgeDoorMesh(oneBedroomFridgeDoorGroup, "one-bedroom refrigerator lower door leaf", 0, 0.72, 0.34, 0.045, 0.72, 0.68, materials.windowFrame);
  addOneBedroomFridgeDoorMesh(oneBedroomFridgeDoorGroup, "one-bedroom refrigerator freezer handle", -0.04, 1.45, 0.58, 0.035, 0.48, 0.045, materials.handle);
  addOneBedroomFridgeDoorMesh(oneBedroomFridgeDoorGroup, "one-bedroom refrigerator lower handle", -0.04, 0.72, 0.58, 0.035, 0.48, 0.045, materials.handle);
  addBox("one-bedroom closed refrigerator toe kick", x - 0.44, 0.16, z, 0.055, 0.16, 0.66, materials.trim, false, 0);
  body.userData.closedReplacementFor = ONE_BEDROOM_FRIDGE_MODEL_URL;
  body.userData.openable = true;
  interactZones.push({
    name: "one-bedroom kitchen refrigerator",
    x: x - 0.9,
    z: z + 0.15,
    radius: 1.1,
    floor: 0,
    action: toggleOneBedroomFridge,
  });
  setOneBedroomFridgeOpen(false);
  return body;
}

function addOneBedroomBookshelfLibraryBooks(shelfX, shelfZ) {
  const bookMats = [materials.bookRed, materials.bookBlue, materials.bookGreen, materials.bookGold, materials.notebookCover, materials.produceGreen];
  for (let row = 0; row < 3; row += 1) {
    let cursorZ = shelfZ - 0.62;
    const baseY = 0.58 + row * 0.39;
    for (let i = 0; i < 7; i += 1) {
      const record = ONE_BEDROOM_LIBRARY_BOOK_SELECTION[(i + row * 3) % ONE_BEDROOM_LIBRARY_BOOK_SELECTION.length];
      const width = 0.055 + ((i + row) % 3) * 0.018;
      const height = 0.26 + ((i + row) % 4) * 0.035;
      const book = markTruthProp(
        addBox(
          `one-bedroom bookshelf library spine ${record.title} row ${row + 1} book ${i + 1}`,
          shelfX - 0.08,
          baseY + height * 0.5,
          cursorZ + width * 0.5,
          0.085,
          height,
          width,
          bookMats[(i + row) % bookMats.length],
          false,
          0,
        ),
        "book",
        record.title,
        0,
        ["read_book", "browse_books", "borrow_media"],
      );
      book.userData.catalogSource = record.source;
      cursorZ += width + 0.03;
    }
  }

  for (let i = 0; i < 4; i += 1) {
    const record = ONE_BEDROOM_LIBRARY_BOOK_SELECTION[(i + 2) % ONE_BEDROOM_LIBRARY_BOOK_SELECTION.length];
    const book = markTruthProp(
      addBox(
        `one-bedroom bookshelf horizontal book stack ${i + 1}`,
        shelfX - 0.1,
        1.54 + i * 0.04,
        shelfZ + 0.46 + i * 0.035,
        0.095,
        0.035,
        0.42,
        i % 2 ? materials.bookGold : materials.fixture,
        false,
        0,
      ),
      "book",
      record.title,
      0,
      ["read_book", "browse_books", "borrow_media"],
    );
    book.userData.catalogSource = record.source;
  }

  interactZones.push({
    name: "one-bedroom living bookshelf library books",
    x: shelfX - 0.78,
    z: shelfZ,
    radius: 1.45,
    floor: 0,
    action: () => show("One-bedroom bookshelf has library books: Alice, Sherlock Holmes, Frankenstein, The Hobbit, Project Hail Mary, The Martian, Doctor Who, and The Time Machine."),
  });
}

function addOneBedroomCoffeeStation(rightX, backZ) {
  const station = new THREE.Group();
  station.name = "one-bedroom stocked working coffee station";
  station.position.set(rightX - 4.05, 1.08, backZ + 2.34);

  const machine = new THREE.Group();
  machine.name = "one-bedroom drip coffee maker";
  const machineBody = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.42, 0.32), materials.phoneBody);
  machineBody.name = "coffee maker black body";
  machineBody.position.y = 0.22;
  machine.add(machineBody);
  const waterTank = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.24, 0.12), materials.glass);
  waterTank.name = "coffee maker visible water reservoir";
  waterTank.position.set(0, 0.29, -0.18);
  machine.add(waterTank);
  const waterFill = new THREE.Mesh(new THREE.BoxGeometry(0.21, 0.13, 0.085), materials.water);
  waterFill.name = "coffee maker reservoir water";
  waterFill.position.set(0, 0.235, -0.18);
  machine.add(waterFill);
  const warmingPlate = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, 0.025, 32), materials.brushedSteel);
  warmingPlate.name = "coffee maker warming plate";
  warmingPlate.position.set(0, 0.025, 0.02);
  machine.add(warmingPlate);
  const brewButton = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.018, 18), materials.handle);
  brewButton.name = "coffee maker brew button";
  brewButton.rotation.x = Math.PI / 2;
  brewButton.position.set(0.085, 0.32, 0.17);
  machine.add(brewButton);
  station.add(machine);
  markTruthProp(machine, "coffee_maker", "stocked one-bedroom drip coffee maker with water", 0, ["make_coffee", "brew_coffee"]);

  const carafe = new THREE.Group();
  carafe.name = "one-bedroom coffee carafe with brewed coffee";
  carafe.position.set(0, 0.115, 0.025);
  const carafeGlass = new THREE.Mesh(new THREE.CylinderGeometry(0.105, 0.13, 0.22, 32), materials.glass);
  carafeGlass.name = "coffee carafe glass";
  carafe.add(carafeGlass);
  const brewedCoffee = new THREE.Mesh(new THREE.CylinderGeometry(0.092, 0.112, 0.11, 32), materials.coffeeLiquid);
  brewedCoffee.name = "visible brewed coffee in carafe";
  brewedCoffee.position.y = -0.04;
  carafe.add(brewedCoffee);
  const carafeHandle = new THREE.Mesh(new THREE.TorusGeometry(0.09, 0.018, 10, 28, Math.PI * 1.45), materials.phoneBody);
  carafeHandle.name = "coffee carafe handle";
  carafeHandle.rotation.x = Math.PI / 2;
  carafeHandle.position.set(0.14, 0.02, 0);
  carafe.add(carafeHandle);
  station.add(carafe);
  markTruthProp(carafe, "coffee", "brewed coffee in the kitchen carafe", 0, ["pour_coffee", "drink_coffee", "get_coffee"]);

  const grounds = new THREE.Group();
  grounds.name = "one-bedroom sealed coffee grounds canister";
  grounds.position.set(-0.31, 0.11, 0.02);
  const groundsJar = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.22, 24), materials.coffeeGrounds);
  groundsJar.name = "coffee grounds canister brown contents";
  grounds.add(groundsJar);
  const groundsLid = new THREE.Mesh(new THREE.CylinderGeometry(0.086, 0.086, 0.025, 24), materials.brushedSteel);
  groundsLid.name = "coffee grounds canister lid";
  groundsLid.position.y = 0.122;
  grounds.add(groundsLid);
  station.add(grounds);
  markTruthProp(grounds, "coffee_grounds", "sealed coffee grounds beside the coffee maker", 0, ["make_coffee", "brew_coffee"]);

  const mug = new THREE.Group();
  mug.name = "one-bedroom reusable coffee mug at coffee station";
  mug.position.set(0.33, 0.075, 0.05);
  const mugBody = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.062, 0.15, 28), materials.fixture);
  mugBody.name = "reusable coffee mug body";
  mug.add(mugBody);
  const mugCoffee = new THREE.Mesh(new THREE.CylinderGeometry(0.058, 0.058, 0.012, 28), materials.coffeeLiquid);
  mugCoffee.name = "visible coffee surface in reusable mug";
  mugCoffee.position.y = 0.078;
  mug.add(mugCoffee);
  const mugHandle = new THREE.Mesh(new THREE.TorusGeometry(0.055, 0.012, 10, 24, Math.PI * 1.55), materials.fixture);
  mugHandle.name = "reusable coffee mug handle";
  mugHandle.rotation.x = Math.PI / 2;
  mugHandle.position.set(0.075, 0.005, 0);
  mug.add(mugHandle);
  station.add(mug);
  markTruthProp(mug, "coffee_cup", "filled reusable coffee mug at Kira's kitchen coffee station", 0, ["get_coffee", "drink_coffee", "pour_coffee"]);
  mug.userData.portable = true;
  mug.userData.propId = "kira_home_kitchen_filled_coffee_mug";

  station.traverse((node) => {
    if (!node.isMesh) return;
    node.castShadow = true;
    node.receiveShadow = true;
  });
  scene.add(station);
  markTruthProp(station, "coffee_station", "stocked working coffee station in Kira's kitchen", 0, ["make_coffee", "get_coffee", "drink_coffee"]);

  interactZones.push({
    name: "one-bedroom stocked coffee station",
    x: station.position.x,
    z: station.position.z + 0.84,
    radius: 1.15,
    floor: 0,
    action: () => show("Kira's kitchen coffee station has water, grounds, a drip machine, brewed coffee, a carafe, and a filled reusable mug."),
  });
  return station;
}

function addOneBedroomKitchenAppliances(splitX, rightX, backZ, bathFrontZ) {
  const kitchenCenterX = rightX - 3.68;
  const counterZ = backZ + 1.92;
  const fridgeX = rightX - 0.78;
  const fridgeZ = backZ + 1.14;
  addOneBedroomClosedRefrigerator(fridgeX, fridgeZ);

  placeOneBedroomModel(ONE_BEDROOM_KITCHEN_CABINET_MODEL_URL, {
    role: "kitchen real cabinet stove sink set",
    name: "one-bedroom imported real kitchen cabinet stove and sink set",
    x: kitchenCenterX,
    y: 0.08,
    z: counterZ,
    width: 3.72,
    height: 1.74,
    depth: 3.28,
    yaw: Math.PI / 2,
    truthKind: "kitchen_sink",
    truthLabel: "one-bedroom real kitchen cabinet stove and sink",
    actionHints: ["wash_dishes", "make_coffee", "prepare_food", "cook"],
  });
  colliders.push({ x: kitchenCenterX - 0.35, z: counterZ - 1.02, sx: 2.3, sz: 0.42, floor: 0 });
  colliders.push({ x: kitchenCenterX - 1.5, z: counterZ + 0.22, sx: 0.42, sz: 1.18, floor: 0 });

  const counterTruth = new THREE.Object3D();
  counterTruth.name = "one-bedroom real kitchen usable counter truth marker";
  counterTruth.position.set(kitchenCenterX - 0.15, 1.18, counterZ);
  scene.add(counterTruth);
  markTruthProp(counterTruth, "counter", "one-bedroom real kitchen usable counter", 0, ["prepare_food", "make_coffee"]);

  for (let i = 0; i < 3; i += 1) {
    const cup = markTruthProp(
      addCylinder(
        `one-bedroom kitchen clean cup ${i + 1}`,
        kitchenCenterX - 0.72 + i * 0.18,
        1.14,
        counterZ + 0.42,
        0.055,
        0.12,
        materials.paper,
        false,
        0,
      ),
      "cup",
      `clean cup ${i + 1} on Kira's kitchen counter`,
      0,
      ["drink", "drink_coffee", "get_drink"],
    );
    cup.userData.portable = true;
  }
  addOneBedroomCoffeeStation(rightX, backZ);
  markTruthProp(addBox("one-bedroom kitchen fruit snack plate", kitchenCenterX + 0.45, 1.12, counterZ + 0.42, 0.32, 0.035, 0.22, materials.fixture, false, 0), "food", "small snack plate on Kira's kitchen counter", 0, ["eat_food", "snack"]);
}

function addOneBedroomCoffeeTableTablet(x, y, z, yaw = 0) {
  const tablet = new THREE.Group();
  tablet.name = "one-bedroom Kira temporary tablet on coffee table";
  tablet.position.set(x, y, z);
  tablet.rotation.y = yaw;
  tablet.userData = {
    type: "personal_item",
    owner: "Kira",
    itemId: "one_bedroom_coffee_table_temporary_tablet",
    deviceType: "temporary_tablet",
    portable: true,
    currentLocation: "one-bedroom living room coffee table",
    abilities: ["look_online", "browse_books", "read_book", "take_notes", "type_notes", "research", "control_tv", "play_music", "listen_music"],
  };
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.026, 0.32), materials.phoneBody);
  body.name = "one-bedroom temporary tablet black body";
  body.castShadow = true;
  body.receiveShadow = true;
  tablet.add(body);
  const screen = new THREE.Mesh(new THREE.BoxGeometry(0.152, 0.008, 0.27), materials.phoneScreen);
  screen.name = "one-bedroom temporary tablet glass screen";
  screen.position.y = 0.019;
  screen.castShadow = true;
  screen.receiveShadow = true;
  tablet.add(screen);
  const camera = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.006, 16), materials.brushedSteel);
  camera.name = "one-bedroom temporary tablet camera dot";
  camera.rotation.x = Math.PI / 2;
  camera.position.set(-0.055, 0.027, -0.105);
  camera.castShadow = true;
  tablet.add(camera);
  scene.add(tablet);
  markTruthProp(tablet, "tablet", "Kira one-bedroom temporary coffee-table tablet", 0, ["look_online", "browse_books", "read_book", "take_notes", "type_notes", "research", "control_tv", "play_music"]);
  return tablet;
}

function addOneBedroomPinkRangerMorpher(x, y, z, yaw = 0) {
  const morpher = new THREE.Group();
  morpher.name = "one-bedroom Pink Ranger morpher on coffee table";
  morpher.position.set(x, y, z);
  morpher.rotation.y = yaw;
  morpher.userData = {
    type: "personal_item",
    owner: "Kira",
    itemId: "one_bedroom_pink_ranger_morpher",
    deviceType: "power_morpher_reference_prop",
    portable: true,
    currentLocation: "one-bedroom living room coffee table",
    abilities: ["pick_up_morpher", "hold_forward", "say_pterodactyl", "morph_pink_ranger", "change_clothes", "helmet_optional"],
    activationPhrase: "Pterodactyl",
    activationGesture: "pick up the morpher, hold it in front with both hands, and say Pterodactyl",
    costumeState: "staged_reference_only",
  };

  const body = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.045, 0.15), materials.phoneBody);
  body.name = "Pink Ranger morpher black grip body";
  body.castShadow = true;
  body.receiveShadow = true;
  morpher.add(body);

  const silverFace = new THREE.Mesh(new THREE.BoxGeometry(0.215, 0.018, 0.12), materials.brushedSteel);
  silverFace.name = "Pink Ranger morpher brushed silver face";
  silverFace.position.y = 0.032;
  silverFace.castShadow = true;
  silverFace.receiveShadow = true;
  morpher.add(silverFace);

  const coin = new THREE.Mesh(new THREE.CylinderGeometry(0.047, 0.047, 0.014, 32), materials.bookGold);
  coin.name = "Pterodactyl Power Coin reference disk";
  coin.position.y = 0.051;
  coin.castShadow = true;
  coin.receiveShadow = true;
  morpher.add(coin);

  const pterodactylWingA = new THREE.Mesh(new THREE.BoxGeometry(0.058, 0.006, 0.014), materials.pursePink);
  pterodactylWingA.name = "pink pterodactyl wing mark left";
  pterodactylWingA.position.set(-0.018, 0.061, 0);
  pterodactylWingA.rotation.y = 0.46;
  morpher.add(pterodactylWingA);
  const pterodactylWingB = pterodactylWingA.clone();
  pterodactylWingB.name = "pink pterodactyl wing mark right";
  pterodactylWingB.position.x = 0.018;
  pterodactylWingB.rotation.y = -0.46;
  morpher.add(pterodactylWingB);

  scene.add(morpher);
  markTruthProp(
    morpher,
    "morpher",
    "Pink Ranger Power Morpher with Pterodactyl Power Coin reference prop",
    0,
    ["pick_up_morpher", "hold_forward", "say_pterodactyl", "morph_pink_ranger", "change_clothes", "helmet_optional"],
  );

  interactZones.push({
    name: "one-bedroom Pink Ranger morpher pickup",
    x,
    z,
    radius: 0.88,
    floor: 0,
    action: () => {
      const started = startActiveAvatarHoldSkill({
        id: "one_bedroom_pick_up_pink_ranger_morpher",
        label: "pick up Pink Ranger morpher and hold it forward",
        action: "hold_pink_ranger_morpher_forward_say_pterodactyl",
        truthAction: "pick_up_morpher",
        seconds: 12,
        position: oneBedroomCouchSeatSpot(),
        yaw: 0,
        postureState: {
          id: "one_bedroom_pick_up_pink_ranger_morpher",
          posture: "sit",
          rootTiltX: 0.01,
          rootYOffset: -0.22,
          surface: "one_bedroom_couch_front_edge",
        },
        heldPropKind: "pink_ranger_morpher",
      });
      show(started
        ? "Kira picks up the Pink Ranger morpher and holds it forward. The activation word is Pterodactyl."
        : "Pink Ranger morpher is on the coffee table. To morph, hold it forward and say Pterodactyl.");
    },
  });

  oneBedroomBlueprintHouseStatus = {
    ...oneBedroomBlueprintHouseStatus,
    pinkRangerMorpher: {
      added: true,
      location: "one-bedroom living room coffee table",
      activationPhrase: "Pterodactyl",
      activationGesture: "Kira must pick up the morpher, hold it forward like the reference pictures, and say Pterodactyl.",
      costumeState: "staged; helmet optional once the costume body fit pass is ready",
      sourceHint: "Mighty Morphin Pink Ranger morpher uses the Pterodactyl Power Coin reference.",
    },
    ladybugEarringsRule: {
      activationPhrase: "spots on",
      activationGesture: "Wear Ladybug's earrings, then say spots on.",
      costumeState: "staged; Avatar Builder must fit the Ladybug costume to the current body before runtime use",
    },
  };
  return morpher;
}

function toggleOneBedroomTvMusic(controller = "remote") {
  oneBedroomTvMusicPlaying = !oneBedroomTvMusicPlaying;
  const controllerLabel = controller === "tablet" ? "Temporary tablet" : "Remote";
  oneBedroomBlueprintHouseStatus = {
    ...oneBedroomBlueprintHouseStatus,
    tvMusic: {
      tvScreenOn: false,
      remotePickupReady: true,
      tabletControlReady: true,
      controller,
      requestedPlayback: oneBedroomTvMusicPlaying,
      source: "MP3 bridge placeholder; physical TV, remote, and temporary tablet hooks are ready for the later media-library audio connector.",
    },
  };
  show(oneBedroomTvMusicPlaying ? `${controllerLabel} requested TV music playback. TV stays visually off for now.` : `${controllerLabel} stopped the TV music request. TV remains off.`);
}

function addOneBedroomDiningSet(splitX, backZ, bathFrontZ) {
  const tableX = splitX + 2.1;
  const tableZ = backZ + 2.88;
  const tableTop = markTruthProp(
    addBox("one-bedroom compact dining table wood top", tableX, 0.72, tableZ, 1.45, 0.11, 0.86, materials.livingWood, false, 0),
    "dining_table",
    "one-bedroom kitchen dining table",
    0,
    ["eat", "sit", "read_book", "take_notes"],
  );
  tableTop.userData.diningSurface = true;
  addBox("one-bedroom compact dining table dark underside", tableX, 0.62, tableZ, 1.24, 0.08, 0.68, materials.wood, false, 0);
  for (const [dx, dz] of [
    [-0.55, -0.29],
    [0.55, -0.29],
    [-0.55, 0.29],
    [0.55, 0.29],
  ]) {
    addBox("one-bedroom compact dining table leg", tableX + dx, 0.36, tableZ + dz, 0.09, 0.64, 0.09, materials.wood, false, 0);
  }
  colliders.push({ x: tableX, z: tableZ, sx: 1.55, sz: 0.96, floor: 0 });

  const chairs = [
    { x: tableX - 0.98, z: tableZ, yaw: Math.PI / 2, label: "left" },
    { x: tableX + 0.98, z: tableZ, yaw: -Math.PI / 2, label: "right" },
    { x: tableX, z: tableZ - 0.72, yaw: 0, label: "back" },
    { x: tableX, z: tableZ + 0.72, yaw: Math.PI, label: "front" },
  ];
  for (const chair of chairs) {
    placeOneBedroomModel(HOME_WORLD_SCHOOL_CHAIR_MODEL_URL, {
      role: `kitchen dining ${chair.label} chair`,
      name: `one-bedroom imported dining chair ${chair.label}`,
      x: chair.x,
      y: 0.08,
      z: chair.z,
      width: 0.48,
      height: 0.82,
      depth: 0.52,
      yaw: chair.yaw,
      uniform: true,
      truthKind: "chair",
      truthLabel: `one-bedroom dining chair ${chair.label}`,
      actionHints: ["sit", "eat"],
    });
  }

  interactZones.push({
    name: "one-bedroom kitchen dining set",
    x: tableX,
    z: tableZ,
    radius: 1.35,
    floor: 0,
    action: () => show("This compact dining table gives Kira and visitors a place to eat, read, or take notes near the kitchen."),
  });
  oneBedroomBlueprintHouseStatus = {
    ...oneBedroomBlueprintHouseStatus,
    diningSet: {
      added: true,
      x: Number(tableX.toFixed(2)),
      z: Number(tableZ.toFixed(2)),
      chairModel: HOME_WORLD_SCHOOL_CHAIR_MODEL_URL,
    },
  };
}

function addOneBedroomBathroomFixtures(leftX, splitX, backZ, bathFrontZ) {
  const bathCenterX = (leftX + splitX) * 0.5;
  const toiletX = leftX + 1.05;
  const toiletZ = backZ + 0.58;
  const sinkX = splitX - 1.05;
  const sinkZ = backZ + 0.5;
  const bathX = leftX + 1.58;
  const bathZ = bathFrontZ - 0.92;
  addCylinder("one-bedroom bathroom visible toilet bowl", toiletX, 0.36, toiletZ + 0.08, 0.25, 0.22, materials.fixture, false, 0);
  addCylinder("one-bedroom bathroom visible toilet seat opening", toiletX, 0.49, toiletZ + 0.08, 0.18, 0.025, materials.burnerBlack, false, 0);
  addBox("one-bedroom bathroom visible toilet tank", toiletX, 0.72, toiletZ - 0.28, 0.58, 0.5, 0.18, materials.fixture, false, 0);
  addBox("one-bedroom bathroom visible toilet rear tank panel", toiletX, 0.74, toiletZ - 0.37, 0.68, 0.54, 0.12, materials.fixture, false, 0);
  addBox("one-bedroom bathroom visible toilet base", toiletX, 0.18, toiletZ, 0.32, 0.34, 0.46, materials.fixture, false, 0);
  const toiletTruth = new THREE.Object3D();
  toiletTruth.name = "one-bedroom blueprint visible toilet truth marker";
  toiletTruth.position.set(toiletX, 0.42, toiletZ);
  scene.add(toiletTruth);
  markTruthProp(toiletTruth, "toilet", "one-bedroom bathroom toilet", 0, ["use_bathroom"]);
  colliders.push({ x: toiletX, z: toiletZ, sx: 0.92, sz: 0.96, floor: 0 });

  placeOneBedroomModel(ONE_BEDROOM_BATHROOM_SINK_MODEL_URL, {
    role: "bathroom sink cabinet",
    name: "one-bedroom blueprint imported bathroom sink cabinet",
    x: sinkX,
    y: 0.08,
    z: sinkZ,
    width: 0.92,
    height: 0.98,
    depth: 0.58,
    yaw: 0,
    truthKind: "sink",
    truthLabel: "one-bedroom bathroom sink",
    actionHints: ["wash_hands", "brush_teeth", "use_bathroom"],
  });
  colliders.push({ x: sinkX, z: sinkZ, sx: 1.0, sz: 0.68, floor: 0 });
  addBackWallReflectiveMirror("one-bedroom bathroom real reflective mirror above sink", sinkX, 1.58, backZ + 0.155, 0.88, 0.76, 0, 1);

  placeOneBedroomModel(ONE_BEDROOM_BATH_SHOWER_MODEL_URL, {
    role: "bathroom bath shower combo",
    name: "one-bedroom blueprint imported bath and shower combo",
    x: bathX,
    y: 0.08,
    z: bathZ,
    width: 1.34,
    height: 2.22,
    depth: 1.86,
    yaw: Math.PI / 2,
    truthKind: "bath_shower",
    truthLabel: "one-bedroom bathroom bath and shower combo",
    actionHints: ["shower", "bathe"],
  });
  const showerTruth = new THREE.Object3D();
  showerTruth.name = "one-bedroom bathroom bath shower usable zone";
  showerTruth.position.set(bathX, 0.055, bathZ);
  scene.add(showerTruth);
  markTruthProp(showerTruth, "bath_shower", "one-bedroom bathroom bath and shower usable zone", 0, ["shower", "bathe"]);
  colliders.push({ x: bathX, z: bathZ, sx: 1.44, sz: 1.96, floor: 0 });
}

function oneBedroomLooseNotebookProtectedName(name) {
  return /(floor|wall|roof|grass|sidewalk|road|street|path|walk|porch|lawn|driveway|counter|cabinet|table|chair|bed|mattress|pillow|sofa|couch|fridge|refrigerator|window|door|trim|base|bookshelf|shelf|rug|pool|bathtub|bath|shower|sink|toilet|mirror|remote|phone|tablet|starbucks|cafe|library|school|basketball|capture flag|parking|\bcar\b|vehicle|time machine|delorean|asphalt|curb|stall|stripe|portal|billboard|umbrella|rail|lamp|tardis)/.test(name);
}

function objectNamePathLower(obj) {
  const names = [];
  let node = obj;
  while (node && node !== scene) {
    if (node.name) names.push(String(node.name));
    node = node.parent;
  }
  return names.join(" ").toLowerCase();
}

function materialLooksLikeLooseNotebookSurface(material) {
  const materialsToCheck = Array.isArray(material) ? material : [material];
  return materialsToCheck.some((mat) => {
    if (!mat) return false;
    if (mat === materials.paper || mat === materials.notebookCover) return true;
    if (!mat.color?.getHSL) return false;
    const hsl = {};
    mat.color.getHSL(hsl);
    const lightPaper = hsl.l > 0.52 && hsl.s < 0.34;
    const blueCover = hsl.h > 0.53 && hsl.h < 0.67 && hsl.s > 0.18 && hsl.l > 0.18 && hsl.l < 0.58;
    return lightPaper || blueCover;
  });
}

function looseFieldOpenBookMeshSignature(obj) {
  const meshName = String(obj.name || "").toLowerCase();
  const materialNames = (Array.isArray(obj.material) ? obj.material : [obj.material])
    .map((mat) => String(mat?.name || "").toLowerCase())
    .join(" ");
  const downloadedBookMesh = /architexture_[01]/.test(meshName) && /architexture|bookpage/.test(materialNames);
  const neighborOpenBookMesh = /object_3[89]/.test(meshName) && /pages|cover/.test(materialNames);
  return downloadedBookMesh || neighborOpenBookMesh;
}

function looksLikeLooseFieldNotebookMesh(obj, name, size, center) {
  if (!obj.isMesh) return false;
  const protectedName = oneBedroomLooseNotebookProtectedName(name);
  const nearNotebookArtifactField = center.x > -65 && center.x < 45 && center.z > -45 && center.z < 40;
  const outsideSchool = !pointInsideHudRegion(center, SCHOOL_CENTER.x, SCHOOL_CENTER.z, SCHOOL_WIDTH, SCHOOL_DEPTH, 4.0);
  const outsideOneBedroom = !pointInsideHudRegion(center, ONE_BEDROOM_HOUSE_CENTER.x, ONE_BEDROOM_HOUSE_CENTER.z, ONE_BEDROOM_HOUSE_WIDTH, ONE_BEDROOM_HOUSE_DEPTH, 2.0);
  const onOrNearGround = center.y > -0.18 && center.y < 0.72;
  const flatAndLarge = size.y < 0.34 && Math.max(size.x, size.z) > 2.35 && Math.min(size.x, size.z) > 0.95;
  const oversizedOpenBook = looseFieldOpenBookMeshSignature(obj) && Math.max(size.x, size.z) > 1.45 && size.y < 0.62;
  if (protectedName && !oversizedOpenBook) return false;
  if (!nearNotebookArtifactField || !outsideSchool || !outsideOneBedroom || !onOrNearGround || (!flatAndLarge && !oversizedOpenBook)) return false;
  if (oversizedOpenBook) return true;
  const nameSuggestsNotebook = /(notebook|open book|sketchbook|loose page|paper page|blueprint page)/.test(name);
  return nameSuggestsNotebook && materialLooksLikeLooseNotebookSurface(obj.material);
}

function removeHomeWorldNotebookFieldArtifacts() {
  const removed = [];
  const candidates = [];
  scene.traverse((obj) => {
    if (!obj || !obj.parent) return;
    const name = objectNamePathLower(obj);
    const knownOldArtifact =
      /one-bedroom blueprint foundation slab/.test(name) ||
      /old two-story.*notebook/.test(name) ||
      /giant notebook/.test(name);
    const bounds = new THREE.Box3().setFromObject(obj);
    const size = bounds.getSize(new THREE.Vector3());
    const center = bounds.getCenter(new THREE.Vector3());
    const nearNotebookArtifactField = center.x > -65 && center.x < 45 && center.z > -45 && center.z < 40;
    const largeEnough = Math.max(size.x, size.z) > 1.8 || knownOldArtifact;
    const strictLooseNotebookMesh = looksLikeLooseFieldNotebookMesh(obj, name, size, center);
    if (nearNotebookArtifactField && ((knownOldArtifact && largeEnough) || strictLooseNotebookMesh)) {
      candidates.push(obj);
    }
  });
  for (const obj of candidates) {
    if (!obj.parent) continue;
    removed.push(obj.name || "unnamed notebook artifact");
    obj.parent.remove(obj);
  }
  oneBedroomBlueprintHouseStatus = {
    ...oneBedroomBlueprintHouseStatus,
    notebookArtifactCleanup: {
      ran: true,
      removed,
      strictGeometry: true,
      protectedRealWorldProps: true,
      scrapbookWasFalseLead: true,
      targetSignature: "oversized open-book meshes from inspected book.glb/neighbor_book_reference.glb outside the school and Kira's home",
      inspectedModelNames: ["inventory/book.glb", "neighbor_book_reference.glb"],
    },
  };
  return removed.length;
}

function darkenOneBedroomTvScreen(root) {
  let screenMeshesChanged = 0;
  root.traverse((node) => {
    if (!node.isMesh) return;
    const meshName = String(node.name || "").toLowerCase();
    const mats = Array.isArray(node.material) ? node.material : [node.material];
    const looksLikeScreen = meshName.includes("body_02")
      || mats.some((mat) => /02.*default|screen|display/i.test(String(mat?.name || "")) || Boolean(mat?.emissiveMap));
    if (!looksLikeScreen) return;
    const offMaterial = new THREE.MeshStandardMaterial({
      color: 0x030506,
      emissive: 0x000000,
      metalness: 0.05,
      roughness: 0.48,
    });
    node.material = Array.isArray(node.material) ? node.material.map((mat) => (mat ? offMaterial.clone() : mat)) : offMaterial;
    screenMeshesChanged += 1;
  });
  root.userData.tvState = {
    visuallyOff: true,
    modelScreenAltered: true,
    screenOverlayRemoved: true,
    screenMeshesChanged,
    streamingFuture: true,
    musicBridgeFuture: true,
  };
  oneBedroomBlueprintHouseStatus = {
    ...oneBedroomBlueprintHouseStatus,
    tvOffModelPatch: {
      applied: true,
      screenOverlayRemoved: true,
      screenMeshesChanged,
    },
  };
}

function addOneBedroomLivingMedia(splitX, rightX, bathFrontZ, frontZ) {
  const livingCenterX = (splitX + rightX) * 0.5;
  const tvWallX = livingCenterX - 0.15;
  const tvWallZ = bathFrontZ + 0.62;
  const coffeeTableX = livingCenterX - 0.45;
  const coffeeTableZ = frontZ - 3.35;
  placeOneBedroomModel(ONE_BEDROOM_TV_CABINET_MODEL_URL, {
    role: "living tv cabinet",
    name: "one-bedroom blueprint imported TV cabinet",
    x: tvWallX,
    y: 0.08,
    z: tvWallZ,
    width: 1.7,
    height: 0.56,
    depth: 0.46,
    yaw: 0,
    truthKind: "tv_stand",
    truthLabel: "one-bedroom living TV cabinet",
    actionHints: ["watch_tv"],
  });
  colliders.push({ x: tvWallX, z: tvWallZ, sx: 1.76, sz: 0.54, floor: 0 });

  placeOneBedroomModel(ONE_BEDROOM_TV_MODEL_URL, {
    role: "living curved tv",
    name: "one-bedroom imported game-ready curved TV",
    x: tvWallX,
    y: 0.62,
    z: tvWallZ + 0.25,
    width: 1.86,
    height: 1.05,
    depth: 0.24,
    yaw: Math.PI / 2,
    uniform: true,
    postProcess: darkenOneBedroomTvScreen,
    truthKind: "tv",
    truthLabel: "one-bedroom living room TV currently off and music-ready",
    actionHints: ["turn_on_tv", "play_music", "listen_music"],
  });

  placeOneBedroomModel(ONE_BEDROOM_COFFEE_TABLE_MODEL_URL, {
    role: "living coffee table",
    name: "one-bedroom blueprint imported low coffee table",
    x: coffeeTableX,
    y: 0.08,
    z: coffeeTableZ,
    width: 1.45,
    height: 0.42,
    depth: 0.78,
    yaw: 0,
    truthKind: "coffee_table",
    truthLabel: "one-bedroom living coffee table",
    actionHints: ["place_tablet", "place_remote", "drink_coffee", "read_book"],
  });
  colliders.push({ x: coffeeTableX, z: coffeeTableZ, sx: 1.5, sz: 0.82, floor: 0 });

  placeOneBedroomModel(ONE_BEDROOM_TV_REMOTE_MODEL_URL, {
    role: "living samsung tv remote",
    name: "one-bedroom Samsung TV remote on coffee table",
    x: coffeeTableX + 0.34,
    y: 0.52,
    z: coffeeTableZ - 0.06,
    width: 0.24,
    height: 0.035,
    depth: 0.08,
    yaw: Math.PI / 2,
    truthKind: "remote",
    truthLabel: "one-bedroom Samsung TV remote",
    actionHints: ["pick_up_remote", "turn_on_tv", "play_music", "listen_music"],
  });

  addOneBedroomCoffeeTableTablet(coffeeTableX - 0.28, 0.535, coffeeTableZ + 0.1, -0.2);
  addOneBedroomPinkRangerMorpher(coffeeTableX + 0.02, 0.545, coffeeTableZ + 0.27, 0.08);
  interactZones.push({
    name: "one-bedroom TV remote music control",
    x: coffeeTableX + 0.34,
    z: coffeeTableZ - 0.06,
    radius: 0.9,
    floor: 0,
    action: () => toggleOneBedroomTvMusic("remote"),
  });
  interactZones.push({
    name: "one-bedroom temporary tablet TV music control",
    x: coffeeTableX - 0.28,
    z: coffeeTableZ + 0.1,
    radius: 0.9,
    floor: 0,
    action: () => toggleOneBedroomTvMusic("tablet"),
  });
}

function addOneBedroomBlueprintHouse() {
  if (!ONE_BEDROOM_BLUEPRINT_HOUSE_ENABLED) return;
  const cx = ONE_BEDROOM_HOUSE_CENTER.x;
  const cz = ONE_BEDROOM_HOUSE_CENTER.z;
  const width = ONE_BEDROOM_HOUSE_WIDTH;
  const depth = ONE_BEDROOM_HOUSE_DEPTH;
  const leftX = ONE_BEDROOM_HOUSE_LEFT_X;
  const rightX = ONE_BEDROOM_HOUSE_RIGHT_X;
  const backZ = ONE_BEDROOM_HOUSE_BACK_Z;
  const frontZ = ONE_BEDROOM_HOUSE_FRONT_Z;
  const wallY = 1.54;
  const wallHeight = 2.94;
  const splitX = leftX + width * 0.39;
  const bathFrontZ = backZ + depth * 0.36;
  const entryX = splitX + 1.15;
  const bedroomDoorZ = frontZ - 3.05;
  const bathDoorX = splitX - 1.18;
  const bathKitchenDoorZ = bathFrontZ - 1.18;
  const bedroomCenterX = (leftX + splitX) * 0.5;
  const rightRoomCenterX = (splitX + rightX) * 0.5;
  const frontRoomCenterZ = (bathFrontZ + frontZ) * 0.5;
  const rearRoomCenterZ = (backZ + bathFrontZ) * 0.5;
  const leftRoomWidth = splitX - leftX - 0.35;
  const rightRoomWidth = rightX - splitX - 0.35;
  const frontRoomDepth = frontZ - bathFrontZ - 0.35;
  const rearRoomDepth = bathFrontZ - backZ - 0.35;

  oneBedroomBlueprintHouseStatus = {
    ...oneBedroomBlueprintHouseStatus,
    enabled: true,
    built: true,
    position: { x: cx, z: cz },
    footprintMeters: { width, depth },
    rooms: {
      bedroom: "left/front 10x12-inspired bedroom with imported all-wood bed frame, fitted separate mattress, pillows, working dresser, and hanging clothing closet",
      bathroom: "left/rear bath with simple wall toilet, sink cabinet, mirror, and bath/shower combo pulled inside the walls",
      kitchen: "right/rear kitchen with openable replacement refrigerator and real cabinet/stove/sink set using reduced L-shaped colliders",
      living: "right/front living area with imported sofa, TV, coffee table, and stocked bookshelf",
    },
    openings: "Door leaves and window glass are intentionally omitted in this pass. Frames surround empty openings only.",
    sizeFix: "Footprint enlarged after review so the bedroom doorway, bathroom, living area, and kitchen have walking clearance.",
  };

  addFloorTile("one-bedroom blueprint front porch slab", entryX, frontZ + 0.76, 2.2, 1.4, materials.neighborStone, 0.06);
  addFloorTile("one-bedroom blueprint front walk", entryX, frontZ + 3.2, 1.18, 4.9, materials.sidewalk, 0.03);

  const windowBottom = 1.02;
  const windowTop = 2.22;
  addNeighborLongWallWithOpenings("one-bedroom blueprint front brick wall", frontZ, leftX, rightX, 0.07, wallHeight, 0.2, materials.neighborBrick, [
    { x: entryX, width: 1.24, bottom: 0.07, top: 2.38, blockCollider: false },
    { x: leftX + 2.02, width: 1.15, bottom: windowBottom, top: windowTop, blockCollider: true },
    { x: rightX - 1.5, width: 1.24, bottom: windowBottom, top: windowTop, blockCollider: true },
  ], 0);
  addNeighborLongWallWithOpenings("one-bedroom blueprint rear brick wall", backZ, leftX, rightX, 0.07, wallHeight, 0.2, materials.neighborBrick, [
    { x: leftX + 1.0, width: 0.92, bottom: windowBottom, top: windowTop, blockCollider: true },
    { x: splitX + 2.35, width: 1.32, bottom: windowBottom, top: windowTop, blockCollider: true },
    { x: rightX - 1.15, width: 1.12, bottom: windowBottom, top: windowTop, blockCollider: true },
  ], 0);
  addNeighborSideWallWithOpenings("one-bedroom blueprint left brick wall", leftX, backZ, frontZ, 0.07, wallHeight, 0.2, materials.neighborBrick, [
    { z: frontZ - 2.15, width: 1.0, bottom: windowBottom, top: windowTop, blockCollider: true },
  ], 0);
  addNeighborSideWallWithOpenings("one-bedroom blueprint right brick wall", rightX, backZ, frontZ, 0.07, wallHeight, 0.2, materials.neighborBrick, [
    { z: backZ + 2.05, width: 1.08, bottom: windowBottom, top: windowTop, blockCollider: true },
    { z: frontZ - 2.0, width: 1.08, bottom: windowBottom, top: windowTop, blockCollider: true },
  ], 0);

  const entryLeft = entryX - 0.72;
  const entryRight = entryX + 0.72;
  addBox("one-bedroom blueprint stone base front left of entry", (leftX + entryLeft) * 0.5, 0.34, frontZ + 0.07, entryLeft - leftX, 0.54, 0.14, materials.neighborStone, false);
  addBox("one-bedroom blueprint stone base front right of entry", (entryRight + rightX) * 0.5, 0.34, frontZ + 0.07, rightX - entryRight, 0.54, 0.14, materials.neighborStone, false);
  addBox("one-bedroom blueprint stone base rear", cx, 0.34, backZ - 0.07, width + 0.22, 0.54, 0.14, materials.neighborStone, false);
  addBox("one-bedroom blueprint stone base left", leftX - 0.07, 0.34, cz, 0.14, 0.54, depth + 0.22, materials.neighborStone, false);
  addBox("one-bedroom blueprint stone base right", rightX + 0.07, 0.34, cz, 0.14, 0.54, depth + 0.22, materials.neighborStone, false);
  addBox("one-bedroom blueprint front lintel band", cx, 2.92, frontZ + 0.12, width + 0.42, 0.11, 0.14, materials.neighborStone, false);
  addBox("one-bedroom blueprint rear lintel band", cx, 2.92, backZ - 0.12, width + 0.42, 0.11, 0.14, materials.neighborStone, false);
  addBox("one-bedroom blueprint left lintel band", leftX - 0.12, 2.92, cz, 0.14, 0.11, depth + 0.42, materials.neighborStone, false);
  addBox("one-bedroom blueprint right lintel band", rightX + 0.12, 2.92, cz, 0.14, 0.11, depth + 0.42, materials.neighborStone, false);
  addGableRoof("one-bedroom blueprint low hip-style roof placeholder", cx, 3.02, cz, width + 1.25, depth + 1.2, 0.82, materials.neighborRoof);

  addOpenFacadeWindowFrame("one-bedroom front bedroom window empty", leftX + 2.02, 1.62, frontZ, 1.15, 1.2, 1);
  addOpenFacadeWindowFrame("one-bedroom front living window empty", rightX - 1.5, 1.62, frontZ, 1.24, 1.2, 1);
  addOpenFacadeWindowFrame("one-bedroom rear bath window empty", leftX + 1.0, 1.62, backZ, 0.92, 1.2, -1);
  addOpenFacadeWindowFrame("one-bedroom rear kitchen window empty", splitX + 2.35, 1.62, backZ, 1.32, 1.2, -1);
  addOpenFacadeWindowFrame("one-bedroom rear kitchen service window empty", rightX - 1.15, 1.62, backZ, 1.12, 1.2, -1);
  addOpenSideWindowFrame("one-bedroom left bedroom side window empty", leftX, 1.62, frontZ - 2.15, 1.0, 1.18, -1);
  addOpenSideWindowFrame("one-bedroom right kitchen side window empty", rightX, 1.62, backZ + 2.05, 1.08, 1.18, 1);
  addOpenSideWindowFrame("one-bedroom right living side window empty", rightX, 1.62, frontZ - 2.0, 1.08, 1.18, 1);
  addOneBedroomFrontEntryTrim("one-bedroom front entry non-flicker trim", frontZ, entryX, 1.24, 0);

  addFloorTile("one-bedroom continuous indoor seam cover floor", cx, cz, width + 0.12, depth + 0.12, materials.floor, 0.086);
  addFloorTile("one-bedroom bedroom wood floor", bedroomCenterX, frontRoomCenterZ, leftRoomWidth, frontRoomDepth, materials.floor, 0.09);
  addFloorTile("one-bedroom bath tile floor", bedroomCenterX, rearRoomCenterZ, leftRoomWidth, rearRoomDepth, materials.sidewalk, 0.091);
  addFloorTile("one-bedroom living wood floor", rightRoomCenterX, frontRoomCenterZ, rightRoomWidth, frontRoomDepth, materials.floor, 0.092);
  addFloorTile("one-bedroom kitchen floor", rightRoomCenterX, rearRoomCenterZ, rightRoomWidth, rearRoomDepth, materials.sidewalk, 0.093);

  addZWallWithGaps("one-bedroom bedroom/living dividing wall with open bedroom doorway", splitX, bathFrontZ, frontZ - 0.12, [
    { center: bedroomDoorZ, width: 1.7 },
  ], wallY, wallHeight, materials.wall, 0);
  addZWallWithGaps("one-bedroom bath/kitchen dividing wall", splitX, backZ + 0.15, bathFrontZ, [
    { center: bathKitchenDoorZ, width: 1.38 },
  ], wallY, wallHeight, materials.wall, 0);
  addXWallWithGaps("one-bedroom bath front wall with open bath doorway", bathFrontZ, leftX + 0.16, splitX - 0.08, [
    { center: bathDoorX, width: 1.32 },
  ], wallY, wallHeight, materials.wall, 0);

  placeOneBedroomModel(REALISTIC_SOFA_MODEL_URL, {
    role: "living sofa",
    name: "one-bedroom blueprint imported modern sofa",
    x: rightRoomCenterX - 0.55,
    y: 0.08,
    z: frontZ - 1.08,
    width: 3.25,
    height: 1.05,
    depth: 1.42,
    yaw: Math.PI,
    truthKind: "sofa",
    truthLabel: "one-bedroom living room sofa",
    actionHints: ["sit", "lay_down", "relax"],
  });
  colliders.push({ x: rightRoomCenterX - 0.55, z: frontZ - 1.08, sx: 3.3, sz: 1.48, floor: 0 });
  placeOneBedroomModel(REALISTIC_BOOKSHELF_MODEL_URL, {
    role: "small bookshelf",
    name: "one-bedroom blueprint imported bookshelf",
    x: rightX - 0.72,
    y: 0.08,
    z: frontRoomCenterZ - 0.78,
    width: 0.72,
    height: 2.08,
    depth: 2.0,
    yaw: -Math.PI / 2,
    truthKind: "bookshelf",
    truthLabel: "one-bedroom living bookshelf",
    actionHints: ["browse_books", "read_book"],
  });
  colliders.push({ x: rightX - 0.72, z: frontRoomCenterZ - 0.78, sx: 0.62, sz: 2.1, floor: 0 });
  addOneBedroomBookshelfLibraryBooks(rightX - 0.72, frontRoomCenterZ - 0.78);
  const bedX = leftX + 1.38;
  const bedZ = frontRoomCenterZ + 0.05;
  addOneBedroomBedSet("one-bedroom blueprint bedroom", bedX, bedZ, 0);
  addOneBedroomBedroomStorage(leftX, splitX, bathFrontZ, frontZ);
  const bedroomFullBodyMirror = addReflectiveMirror(
    "Kira one-bedroom bedroom full body mirror",
    splitX - 0.1,
    1.42,
    bathFrontZ + 2.8,
    0.82,
    1.84,
    0,
    -1,
  );
  markTruthProp(bedroomFullBodyMirror, "mirror", "Kira one-bedroom full body bedroom mirror", 0, ["inspect_avatar", "check_outfit", "change_clothes"]);
  addOneBedroomBathroomFixtures(leftX, splitX, backZ, bathFrontZ);
  addOneBedroomKitchenAppliances(splitX, rightX, backZ, bathFrontZ);
  addOneBedroomDiningSet(splitX, backZ, bathFrontZ);
  addOneBedroomLivingMedia(splitX, rightX, bathFrontZ, frontZ);
  oneBedroomBlueprintHouseStatus = {
    ...oneBedroomBlueprintHouseStatus,
    usableColliders: {
      sofa: true,
      bed: true,
      toilet: true,
      bathroomSink: true,
      shower: true,
      refrigerator: true,
    kitchenCounter: true,
      diningSet: true,
      tv: true,
      coffeeTable: true,
      exteriorWalls: true,
      windowOpeningsBlockedAtPlayerLevel: true,
      frontDoorOpeningWalkable: true,
      interiorDoorwayTrimSkipped: true,
    },
    kitchenNote: "Kitchen real cabinet/stove/sink model is pulled forward from the brick wall and its colliders are narrowed again; the small extra stove blocker was removed so the stove-to-refrigerator lane stays walkable.",
    bathroomNote: "Bathroom uses a simple in-room toilet, rear-wall sink, Reflector mirror, and a bath/shower combo moved inward so it should no longer protrude through the exterior wall.",
    bedNote: "Bed uses the separate imported frame, a visible temporary white mattress placeholder because the imported mattress GLB rendered invisible, visible frame supports/slats, and temporary pillows oriented across the headboard.",
    tvNote: "Living room TV is visually off by default by darkening the imported TV model screen directly; no black cover overlay remains. The Samsung remote and temporary coffee-table tablet both toggle the future MP3 bridge request.",
    diningNote: "A compact dining table and chair set was added in the kitchen-side open gap without blocking the main kitchen walking path.",
    doorwayNote: "Bedroom doorway gap is narrowed for this pass so the opening reads more like a real future door frame while still staying doorless.",
    dresserNote: "Bedroom dresser is a lower working clothes dresser with sliding drawer fronts and folded clothing visible when opened.",
    mirrorNote: "A real Reflector full-body mirror is mounted on the bedroom divider wall for outfit and avatar checks.",
    closetNote: "Bedroom now has a hanging clothes closet with rails, hangers, visible garments, folded stacks, door pulls that move with the sliding doors, and lifecycle hooks for fold/unfold/put-on/take-off/laundry work.",
    bookshelfLibraryNote: "Bookshelf is stocked with in-shelf procedural book spines and stacks linked to selected files from Data/library/novels; floating imported book props were removed.",
    bookshelfBookCount: ONE_BEDROOM_LIBRARY_BOOK_SELECTION.length,
    livingClearanceNote: "Coffee table is moved farther from the couch to leave a walkable sitting gap.",
    floorSeamNote: "A continuous indoor seam-cover floor sits below room floors so grass-green gaps should not show between rooms.",
    twoStoryHouseRemoved: !MAIN_TWO_STORY_HOUSE_ENABLED,
    oldBackyardPoolRemovedWithTwoStoryHouse: !MAIN_TWO_STORY_HOUSE_ENABLED,
    notebookBattlefieldHiddenByDefault: !CAPTURE_FLAG_WORLD_ENABLED,
    oversizedFoundationPadRemoved: true,
    oneBedroomFoundationSlabRemoved: true,
    notebookArtifactCleanup: {
      ...(oneBedroomBlueprintHouseStatus.notebookArtifactCleanup || {}),
      geometryBased: true,
      repeatedAtStartup: true,
    },
  };
}

function cloneOneBedroomSceneObjectForCopy(source, config) {
  if (!source || source.userData?.skipOneBedroomCopy) return null;
  let clone = null;
  try {
    clone = source.clone(true);
  } catch (err) {
    return null;
  }
  clone.name = `${config.title} copy of ${source.name || source.type || "one-bedroom object"}`;
  clone.position.x += config.offsetX;
  clone.position.z += config.offsetZ || 0;
  cloneOneBedroomMaterialInstances(clone);
  tagOneBedroomHomeCopy(clone, config);
  clone.traverse((node) => {
    if (node.userData?.truthProp) activityTruthProps.push(node);
  });
  scene.add(clone);
  return clone;
}

function offsetOneBedroomCollider(collider, config) {
  return {
    ...collider,
    x: collider.x + config.offsetX,
    z: collider.z + (config.offsetZ || 0),
  };
}

function addOneBedroomForRentSign(config) {
  const signX = ONE_BEDROOM_HOUSE_ENTRY.x + config.offsetX - 1.35;
  const signZ = ONE_BEDROOM_HOUSE_FRONT_Z + 2.45 + (config.offsetZ || 0);
  addBox("for rent one-bedroom yard sign left post", signX - 0.42, 0.62, signZ, 0.07, 1.08, 0.07, materials.windowFrame, false, 0);
  addBox("for rent one-bedroom yard sign right post", signX + 0.42, 0.62, signZ, 0.07, 1.08, 0.07, materials.windowFrame, false, 0);
  addBox("for rent one-bedroom yard sign rail", signX, 1.12, signZ, 0.98, 0.06, 0.07, materials.windowFrame, false, 0);
  const sign = addLabel("FOR RENT", signX, 1.32, signZ + 0.04, 1.65, { billboard: false, rotationY: 0 });
  sign.name = "for rent one-bedroom front yard sign";
  sign.userData.forRentHouse = config.id;
  return sign;
}

function registerOneBedroomCopyWorkbench(config) {
  const workbenches = homeWorldActivityStatus.oneBedroomHomeWorkbenches || [];
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    oneBedroomHomeWorkbenches: [
      ...workbenches,
      {
        id: config.id,
        owner: config.owner,
        title: config.title,
        forRent: !!config.empty,
        houseCenter: {
          x: ONE_BEDROOM_HOUSE_CENTER.x + config.offsetX,
          z: ONE_BEDROOM_HOUSE_CENTER.z + (config.offsetZ || 0),
        },
        futurePersonalization: ["wall_sketches", "photos", "resident_item_swaps", "owned_media"],
      },
    ],
  };
}

function addOneBedroomBlueprintHouseWithCopies() {
  if (!ONE_BEDROOM_BLUEPRINT_HOUSE_ENABLED) return false;
  const sceneStart = scene.children.length;
  const colliderStart = colliders.length;
  const doorColliderStart = doorColliders.length;
  const interactStart = interactZones.length;
  oneBedroomCopyReplicationArmed = false;
  addOneBedroomBlueprintHouse();
  const sourceObjects = scene.children.slice(sceneStart);
  const sourceColliders = colliders.slice(colliderStart);
  const sourceDoorColliders = doorColliders.slice(doorColliderStart);
  const sourceInteractZones = interactZones.slice(interactStart);
  registerOneBedroomCopyWorkbench(ONE_BEDROOM_ALL_HOUSE_CONFIGS[0]);
  for (const config of ONE_BEDROOM_HOME_WORLD_COPY_CONFIGS) {
    for (const obj of sourceObjects) cloneOneBedroomSceneObjectForCopy(obj, config);
    for (const collider of sourceColliders) colliders.push(offsetOneBedroomCollider(collider, config));
    for (const collider of sourceDoorColliders) doorColliders.push(offsetOneBedroomCollider(collider, config));
    for (const zone of sourceInteractZones) {
      interactZones.push({
        ...zone,
        name: `${config.title} ${zone.name || "one-bedroom interact zone"}`,
        x: zone.x + config.offsetX,
        z: zone.z + (config.offsetZ || 0),
      });
    }
    registerOneBedroomCopyWorkbench(config);
    if (config.empty) addOneBedroomForRentSign(config);
  }
  oneBedroomCopyReplicationArmed = true;
  oneBedroomBlueprintHouseStatus = {
    ...oneBedroomBlueprintHouseStatus,
    kiraMovedIn: true,
    oldStudioRuntimeDeleted: !KIRA_BUNGALOW_ENABLED,
    houseCopies: {
      source: "Kira's Home",
      totalPlannedHomes: ONE_BEDROOM_ALL_HOUSE_CONFIGS.length,
      activeHomeWorldHomes: ONE_BEDROOM_HOME_WORLD_CONFIGS.map((config) => ({
        id: config.id,
        owner: config.owner,
        title: config.title,
        offsetX: config.offsetX,
        offsetZ: config.offsetZ || 0,
        forRent: !!config.empty,
      })),
      activeHomeWorldTotal: ONE_BEDROOM_HOME_WORLD_CONFIGS.length,
      copiedHomes: ONE_BEDROOM_HOME_WORLD_COPY_CONFIGS.map((config) => ({
        id: config.id,
        owner: config.owner,
        title: config.title,
        offsetX: config.offsetX,
        offsetZ: config.offsetZ || 0,
        forRent: !!config.empty,
      })),
      offloadedHomes: ONE_BEDROOM_HOUSE_COPY_CONFIGS.filter((config) => !ONE_BEDROOM_HOME_WORLD_ACTIVE_COPY_IDS.has(config.id)).map((config) => ({
        id: config.id,
        owner: config.owner,
        title: config.title,
        forRent: !!config.empty,
      })),
      savedPlacesTemplate: SAVED_PLACES_NOTEBOOK_WORLD_TEMPLATE,
      note: "Pre-RAM voice recovery: Home World only loads Kira's live one-bedroom house. Lisa, Marinette, Peter, Gwen, and For Rent are not spawned here; use the saved-places template notebook world for future copies.",
    },
    oldTwoStoryCollisionCleanup: {
      mainHouseEnabled: MAIN_TWO_STORY_HOUSE_ENABLED,
      playerStairTraversalDisabled: !MAIN_TWO_STORY_HOUSE_ENABLED,
      avatarSecondFloorSupportDisabled: !MAIN_TWO_STORY_HOUSE_ENABLED,
    },
  };
  return true;
}

function addNeighborPrefabHouse() {
  const cx = 30.2;
  const cz = 3.2;
  const width = 14.2;
  const depth = 12.8;
  const frontZ = cz + depth / 2;
  const backZ = cz - depth / 2;
  const leftX = cx - width / 2;
  const rightX = cx + width / 2;
  const doorX = cx - 0.55;

  neighborHouseReferenceStatus = {
    ...neighborHouseReferenceStatus,
    disabled: false,
    prefabRetry: true,
    sourceProject: "Data/world_builder/projects/neighbor_three_bed_house_retry_20260707",
    exteriorScaffold: "Prefab retry 3-bedroom house: generated brick shell with real tagged model furniture and no block furniture.",
    furnishedInterior: "Real imported prefabs: sofa, bookshelf, books/notebooks, dining set, bed frames, mattresses, pillows, and toilet.",
    layoutFix: "Living/dining stays in front; all three bedrooms are in the rear wing; front entry path remains clear.",
    position: { x: cx, z: cz },
    gapMetersFromCurrentHouseEastWall: Number((leftX - 8).toFixed(1)),
  };

  addFloorTile("neighbor prefab retry grass lot", cx, cz + 0.4, 17.8, 17.0, materials.grass, -0.018);
  addFloorTile("neighbor prefab retry foundation", cx, cz, width + 0.75, depth + 0.75, materials.sidewalk, 0.04);
  addFloorTile("neighbor prefab retry porch landing", doorX, frontZ + 0.92, 3.3, 1.55, materials.neighborStone, 0.065);
  addFloorTile("neighbor prefab retry front walk", doorX, 13.75, 1.45, 7.35, materials.sidewalk, 0.035);

  addNeighborLongWallWithOpenings("neighbor prefab retry front wall with clear door", frontZ, leftX, rightX, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { x: doorX, width: 1.42, bottom: 0.07, top: 2.36, blockCollider: false },
    { x: cx - 4.15, width: 1.85, bottom: 1.02, top: 2.24, blockCollider: true },
    { x: cx + 3.9, width: 1.72, bottom: 1.02, top: 2.24, blockCollider: true },
  ], 0);
  addNeighborLongWallWithOpenings("neighbor prefab retry rear bedroom wall", backZ, leftX, rightX, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { x: cx - 4.65, width: 1.08, bottom: 1.05, top: 2.18, blockCollider: true },
    { x: cx - 0.15, width: 1.08, bottom: 1.05, top: 2.18, blockCollider: true },
    { x: cx + 4.35, width: 1.08, bottom: 1.05, top: 2.18, blockCollider: true },
  ], 0);
  addNeighborSideWallWithOpenings("neighbor prefab retry left wall", leftX, backZ, frontZ, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { z: cz + 3.45, width: 1.15, bottom: 1.05, top: 2.18, blockCollider: true },
    { z: cz - 2.15, width: 1.15, bottom: 1.05, top: 2.18, blockCollider: true },
  ], 0);
  addNeighborSideWallWithOpenings("neighbor prefab retry right wall", rightX, backZ, frontZ, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { z: cz + 3.2, width: 1.15, bottom: 1.05, top: 2.18, blockCollider: true },
    { z: cz - 2.15, width: 1.15, bottom: 1.05, top: 2.18, blockCollider: true },
  ], 0);

  addNeighborMasonryBase("neighbor prefab retry", cx, cz, width, depth);
  addBox("neighbor prefab retry front trim band", cx, 2.9, frontZ + 0.12, width + 0.42, 0.11, 0.14, materials.windowFrame, false);
  addBox("neighbor prefab retry rear trim band", cx, 2.9, backZ - 0.12, width + 0.42, 0.11, 0.14, materials.windowFrame, false);
  addGableRoof("neighbor prefab retry low main roof", cx, 3.05, cz, width + 1.55, depth + 1.7, 0.96, materials.neighborRoof);

  addFloorTile("neighbor prefab retry foyer floor", doorX, frontZ - 1.35, 2.7, 2.85, materials.floor, 0.088);
  addFloorTile("neighbor prefab retry living room floor", cx - 4.2, cz + 3.55, 4.95, 4.4, materials.floor, 0.089);
  addFloorTile("neighbor prefab retry dining room floor", cx + 3.7, cz + 3.65, 3.8, 3.9, materials.floor, 0.09);
  addFloorTile("neighbor prefab retry hall floor", cx - 0.1, cz - 0.75, 2.6, 4.2, materials.floor, 0.091);
  addFloorTile("neighbor prefab retry bedroom one floor", cx - 4.65, cz - 2.25, 3.8, 3.45, materials.floor, 0.092);
  addFloorTile("neighbor prefab retry bedroom two floor", cx - 0.15, cz - 2.25, 3.55, 3.45, materials.floor, 0.093);
  addFloorTile("neighbor prefab retry bedroom three floor", cx + 4.3, cz - 2.25, 3.8, 3.45, materials.floor, 0.094);
  addFloorTile("neighbor prefab retry bathroom tile floor", cx + 5.55, cz + 0.3, 2.0, 2.0, materials.sidewalk, 0.095);

  addNeighborInteriorWall("neighbor prefab retry rear privacy left wall", cx - 4.85, cz + 0.75, 3.25, 0.12);
  addNeighborInteriorWall("neighbor prefab retry rear privacy right wall", cx + 4.25, cz + 0.75, 3.55, 0.12);
  addNeighborInteriorWall("neighbor prefab retry bedroom one divider", cx - 2.42, cz - 2.15, 0.12, 4.3);
  addNeighborInteriorWall("neighbor prefab retry bedroom two divider", cx + 2.2, cz - 2.15, 0.12, 4.3);
  addNeighborInteriorWall("neighbor prefab retry bath divider", cx + 4.35, cz + 0.1, 0.12, 2.2);

  neighborHouseDoorLeaf = addDoorLeafToScene("neighbor prefab retry hidden front door collider leaf", doorX, frontZ + 0.23, 1.08, 2.16);
  doorColliders.push({ x: doorX, z: frontZ + 0.23, sx: 1.18, sz: 0.35, floor: 0, active: () => !neighborHouseDoorOpen });
  neighborDoorStatus = {
    initialized: true,
    position: { x: doorX, z: frontZ + 0.23 },
  };
  setNeighborHouseDoorOpen(false);

  placeNeighborDoorPanel({ name: "neighbor prefab retry imported front door panel", pattern: /Door_Panel_1_1/i, x: doorX, z: frontZ + 0.18, width: 1.02, height: 2.16, depth: 0.12, yaw: 0, frontDoorVisual: true });
  placeNeighborDoorPanel({ name: "neighbor prefab retry bedroom one imported open door", pattern: /Door_Panel_1_1/i, x: cx - 4.0, z: cz + 0.86, width: 0.88, height: 2.02, depth: 0.1, yaw: -0.72 });
  placeNeighborDoorPanel({ name: "neighbor prefab retry bedroom two imported open door", pattern: /Door_Panel_1_1/i, x: cx - 0.15, z: cz + 0.86, width: 0.88, height: 2.02, depth: 0.1, yaw: 0.64 });
  placeNeighborDoorPanel({ name: "neighbor prefab retry bedroom three imported open door", pattern: /Door_Panel_1_1/i, x: cx + 3.65, z: cz + 0.86, width: 0.88, height: 2.02, depth: 0.1, yaw: -0.62 });

  placeNeighborPrefabWholeModel(REALISTIC_SOFA_MODEL_URL, {
    role: "living room real sofa",
    name: "neighbor prefab retry imported real sofa",
    x: cx - 4.65,
    y: 0.08,
    z: cz + 4.15,
    width: 3.35,
    height: 1.08,
    depth: 1.42,
    yaw: Math.PI,
    truthKind: "seat",
    truthLabel: "neighbor living room real sofa",
    actionHints: ["sit", "lay_down"],
  });
  placeNeighborPrefabWholeModel(REALISTIC_BOOKSHELF_MODEL_URL, {
    role: "living room real bookshelf",
    name: "neighbor prefab retry imported real bookshelf",
    x: cx - 6.45,
    y: 0.08,
    z: cz + 2.65,
    width: 0.72,
    height: 2.08,
    depth: 2.35,
    yaw: Math.PI / 2,
    truthKind: "book",
    truthLabel: "neighbor real bookshelf",
    actionHints: ["read_book", "browse_books"],
  });
  placeNeighborPrefabWholeModel(NEIGHBOR_PREFAB_BOOK_MODEL_URL, {
    role: "living room real book",
    name: "neighbor prefab retry imported real book",
    x: cx - 5.42,
    y: 0.8,
    z: cz + 3.45,
    width: 0.58,
    height: 0.08,
    depth: 0.38,
    yaw: 0.18,
    truthKind: "book",
    truthLabel: "neighbor readable book",
    actionHints: ["read_book"],
  });
  placeNeighborApartmentNode({ name: "neighbor prefab retry imported dining table and chairs", pattern: /outdoor_table_and_chairs/i, x: cx + 3.72, z: cz + 4.05, width: 2.35, height: 1.2, depth: 2.2, yaw: Math.PI, uniform: true });

  addNeighborPrefabBedSet("neighbor bedroom one", cx - 4.65, cz - 2.35, 0);
  addNeighborPrefabBedSet("neighbor bedroom two", cx - 0.15, cz - 2.35, 0);
  addNeighborPrefabBedSet("neighbor bedroom three", cx + 4.3, cz - 2.35, 0);
  addRealisticToiletModel("neighbor prefab retry bathroom toilet", cx + 5.55, cz + 0.25, 0, Math.PI);

  addNeighborFacadeWindow("neighbor prefab retry living front real window", cx - 4.15, 1.62, frontZ, 1.72, 1.16, 1);
  addNeighborFacadeWindow("neighbor prefab retry dining front real window", cx + 3.9, 1.62, frontZ, 1.55, 1.14, 1);
  addNeighborFacadeWindow("neighbor prefab retry rear bedroom one real window", cx - 4.65, 1.62, backZ, 1.02, 1.06, -1);
  addNeighborFacadeWindow("neighbor prefab retry rear bedroom two real window", cx - 0.15, 1.62, backZ, 1.02, 1.06, -1);
  addNeighborFacadeWindow("neighbor prefab retry rear bedroom three real window", cx + 4.35, 1.62, backZ, 1.02, 1.06, -1);
  addNeighborSideWindow("neighbor prefab retry left living real window", leftX, 1.62, cz + 3.45, 1.08, 1.08, -1);
  addNeighborSideWindow("neighbor prefab retry right bathroom real window", rightX, 1.62, cz + 0.25, 0.92, 0.92, 1);

  interactZones.push({
    name: "neighbor prefab retry front porch",
    x: doorX,
    z: frontZ + 1.0,
    floor: 0,
    radius: 1.55,
    action: () => {
      setNeighborHouseDoorOpen(!neighborHouseDoorOpen);
      show(neighborHouseDoorOpen ? "Neighbor prefab house front door open." : "Neighbor prefab house front door closed.");
    },
  });
}

function addNeighborBlueprintBathroom(name, x, z) {
  addFloorTile(`${name} tile floor`, x, z, 2.75, 1.55, materials.sidewalk, 0.096);
  addBox(`${name} vanity cabinet`, x - 0.82, 0.47, z + 0.43, 0.72, 0.7, 0.42, materials.warmCabinet, false);
  addBox(`${name} vanity counter`, x - 0.82, 0.86, z + 0.43, 0.82, 0.08, 0.5, materials.counter, false);
  addBox(`${name} sink basin`, x - 0.82, 0.93, z + 0.43, 0.52, 0.08, 0.31, materials.fixture, false);
  addBox(`${name} mirror`, x - 0.82, 1.55, z + 0.68, 0.72, 0.62, 0.04, materials.mirror, false);
  addCylinder(`${name} faucet`, x - 0.82, 1.1, z + 0.27, 0.035, 0.24, materials.handle, false);
  addBox(`${name} bathtub`, x + 0.72, 0.42, z + 0.42, 1.12, 0.44, 0.48, materials.fixture, false);
  addBox(`${name} shower glass`, x + 0.18, 1.1, z + 0.61, 0.055, 1.25, 0.58, materials.transomGlass, false);
  addRealisticToiletModel(`${name} real imported toilet`, x + 0.78, z - 0.43, 0, -Math.PI / 2);
}

function addNeighborBlueprintHouse() {
  const cx = 31.0;
  const cz = 1.0;
  const width = 16.8;
  const depth = 16.2;
  const leftX = 22.6;
  const rightX = 39.4;
  const backZ = -7.1;
  const frontZ = 9.1;
  const hallLeft = 29.95;
  const hallRight = 32.05;
  const serviceLeft = 32.2;
  const serviceMid = 35.2;
  const doorX = 30.65;
  const rearHallBackZ = -0.85;

  neighborHouseReferenceStatus = {
    ...neighborHouseReferenceStatus,
    disabled: false,
    prefabRetry: false,
    blueprintDriven: true,
    deletedFailedPrefabHouse: true,
    sourceProject: "Data/world_builder/projects/neighbor_three_bed_house_blueprint_20260707",
    exteriorScaffold: "Blueprint-driven single-story brick ranch. The rejected prefab retry house is no longer spawned.",
    furnishedInterior: "Real imported prefabs are used for the sofa, bookshelf, readable book, dining set, three bed frames, mattresses, pillows, and toilet. Kitchen/vanity/tub shell pieces remain generated until tagged kitchen/bath prefabs are available.",
    layoutFix: "Blueprint has a front living room, front dining room, right-side kitchen, separate hall bathroom, central hall, rear bedroom hall, and exactly three rear bedrooms.",
    rules: [
      "No bed, mattress, or pillow may be placed in the living, dining, kitchen, foyer, or hall.",
      "Doors must sit in actual wall gaps; no door panel may cover the front doorway.",
      "Front door opens into the foyer/central hall, not a bedroom.",
    ],
    blueprintRooms: [
      "front living room",
      "entry foyer and central hall",
      "rear bedroom hall",
      "front dining room",
      "right side kitchen",
      "hall bathroom",
      "rear left bedroom",
      "rear middle bedroom",
      "rear right bedroom",
    ],
    position: { x: cx, z: cz },
    gapMetersFromCurrentHouseEastWall: Number((leftX - 8).toFixed(1)),
  };

  addFloorTile("neighbor blueprint grass lot", cx, cz + 0.3, width + 3.8, depth + 3.2, materials.grass, -0.018);
  addFloorTile("neighbor blueprint foundation", cx, cz, width + 0.8, depth + 0.85, materials.sidewalk, 0.04);
  addFloorTile("neighbor blueprint front porch", doorX, frontZ + 0.94, 3.6, 1.6, materials.neighborStone, 0.066);
  addFloorTile("neighbor blueprint front walk", doorX, 13.72, 1.45, 7.35, materials.sidewalk, 0.035);

  addNeighborLongWallWithOpenings("neighbor blueprint front brick wall", frontZ, leftX, rightX, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { x: doorX, width: 1.55, bottom: 0.07, top: 2.45, blockCollider: false },
    { x: 26.45, width: 1.95, bottom: 1.02, top: 2.28, blockCollider: true },
    { x: 35.62, width: 1.75, bottom: 1.02, top: 2.26, blockCollider: true },
  ], 0);
  addNeighborLongWallWithOpenings("neighbor blueprint rear bedroom brick wall", backZ, leftX, rightX, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { x: 26.45, width: 1.25, bottom: 1.05, top: 2.18, blockCollider: true },
    { x: 33.62, width: 1.05, bottom: 1.05, top: 2.18, blockCollider: true },
    { x: 37.25, width: 1.05, bottom: 1.05, top: 2.18, blockCollider: true },
  ], 0);
  addNeighborSideWallWithOpenings("neighbor blueprint left brick wall", leftX, backZ, frontZ, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { z: 6.05, width: 1.15, bottom: 1.05, top: 2.18, blockCollider: true },
    { z: -2.7, width: 1.15, bottom: 1.05, top: 2.18, blockCollider: true },
  ], 0);
  addNeighborSideWallWithOpenings("neighbor blueprint right brick wall", rightX, backZ, frontZ, 0.07, 2.82, 0.2, materials.neighborBrick, [
    { z: 4.1, width: 1.12, bottom: 1.05, top: 2.16, blockCollider: true },
    { z: 0.9, width: 0.88, bottom: 1.13, top: 2.04, blockCollider: true },
    { z: -2.7, width: 1.05, bottom: 1.05, top: 2.18, blockCollider: true },
  ], 0);

  addNeighborMasonryBase("neighbor blueprint", cx, cz, width, depth);
  addNeighborBrickCourses("neighbor blueprint", cx, cz, width, depth, 0.18, 2.55);
  addBox("neighbor blueprint front trim band", cx, 2.9, frontZ + 0.12, width + 0.45, 0.11, 0.14, materials.windowFrame, false);
  addBox("neighbor blueprint rear trim band", cx, 2.9, backZ - 0.12, width + 0.45, 0.11, 0.14, materials.windowFrame, false);
  addGableRoof("neighbor blueprint low ranch roof", cx, 3.08, cz, width + 1.6, depth + 1.8, 0.98, materials.neighborRoof);

  addFloorTile("neighbor blueprint living room floor", 26.45, 6.25, 6.75, 4.8, materials.floor, 0.091);
  addFloorTile("neighbor blueprint foyer and central hall floor", 31.0, 5.28, 1.88, 6.75, materials.floor, 0.092);
  addFloorTile("neighbor blueprint rear bedroom hall floor", 34.5, 0.47, 8.9, 2.45, materials.floor, 0.093);
  addFloorTile("neighbor blueprint dining room floor", 35.62, 7.15, 6.5, 3.0, materials.floor, 0.094);
  addFloorTile("neighbor blueprint kitchen floor", 35.62, 4.1, 6.5, 2.55, materials.sidewalk, 0.095);
  addFloorTile("neighbor blueprint rear left bedroom floor", 26.45, -2.7, 6.75, 7.55, materials.floor, 0.096);
  addFloorTile("neighbor blueprint rear middle bedroom floor", 33.62, -3.45, 2.9, 5.4, materials.floor, 0.097);
  addFloorTile("neighbor blueprint rear right bedroom floor", 37.25, -3.45, 3.3, 5.4, materials.floor, 0.098);

  addZWallWithGaps("neighbor blueprint left hall wall", hallLeft, backZ + 0.45, frontZ - 0.35, [
    { center: 4.55, width: 1.2 },
    { center: 0.55, width: 0.95 },
  ], 1.3, 2.35, materials.wall, 0);
  addZWallWithGaps("neighbor blueprint right hall wall", hallRight, rearHallBackZ, frontZ - 0.35, [
    { center: 3.85, width: 1.15 },
    { center: 1.1, width: 0.95 },
  ], 1.3, 2.35, materials.wall, 0);
  addXWallWithGaps("neighbor blueprint rear bedroom wall with door gaps", rearHallBackZ, hallRight, rightX - 0.35, [
    { center: 33.85, width: 0.95 },
    { center: 37.25, width: 0.95 },
  ], 1.3, 2.35, materials.wall, 0);
  addZWallWithGaps("neighbor blueprint middle right bedroom divider", 35.32, backZ + 0.45, rearHallBackZ - 0.1, [], 1.3, 2.35, materials.wall, 0);
  addXWallWithGaps("neighbor blueprint left bedroom front wall", 1.25, leftX + 0.35, hallLeft, [], 1.3, 2.35, materials.wall, 0);
  addXWallWithGaps("neighbor blueprint living rear wall", 3.75, leftX + 0.35, hallLeft, [], 1.3, 2.35, materials.wall, 0);
  addXWallWithGaps("neighbor blueprint bathroom front wall", 1.75, serviceLeft, serviceMid, [], 1.3, 2.35, materials.wall, 0);
  addXWallWithGaps("neighbor blueprint bathroom rear wall", 0.05, serviceLeft, serviceMid, [], 1.3, 2.35, materials.wall, 0);
  addZWallWithGaps("neighbor blueprint bathroom right wall", serviceMid, 0.05, 1.75, [], 1.3, 2.35, materials.wall, 0);

  addZWallDoorTrim("neighbor blueprint living hall opening trim", hallLeft, 4.55, 1.2, 0);
  addZWallDoorTrim("neighbor blueprint kitchen hall opening trim", hallRight, 3.85, 1.15, 0);
  addZWallDoorTrim("neighbor blueprint bathroom door trim", hallRight, 1.1, 0.95, 0);
  addZWallDoorTrim("neighbor blueprint left bedroom door trim", hallLeft, 0.55, 0.95, 0);
  addXWallDoorTrim("neighbor blueprint middle bedroom door trim", rearHallBackZ, 33.85, 0.95, 0);
  addXWallDoorTrim("neighbor blueprint right bedroom door trim", rearHallBackZ, 37.25, 0.95, 0);
  createZWallInteriorDoor("neighbor blueprint bathroom working door", hallRight, 1.1, 0.95, 0, -1, "neighbor blueprint bathroom door");
  createZWallInteriorDoor("neighbor blueprint rear left bedroom working door", hallLeft, 0.55, 0.95, 0, 1, "neighbor blueprint rear left bedroom door");
  createXWallInteriorDoor("neighbor blueprint rear middle bedroom working door", rearHallBackZ, 33.85, 0.95, 0, -1, "neighbor blueprint rear middle bedroom door");
  createXWallInteriorDoor("neighbor blueprint rear right bedroom working door", rearHallBackZ, 37.25, 0.95, 0, -1, "neighbor blueprint rear right bedroom door");

  neighborHouseDoorLeaf = addDoorLeafToScene("neighbor blueprint working front door", doorX, frontZ + 0.23, 1.08, 2.16);
  doorColliders.push({ x: doorX, z: frontZ + 0.23, sx: 1.18, sz: 0.35, floor: 0, active: () => !neighborHouseDoorOpen });
  neighborDoorStatus = {
    initialized: true,
    position: { x: doorX, z: frontZ + 0.23 },
  };
  setNeighborHouseDoorOpen(false);

  placeNeighborPrefabWholeModel(REALISTIC_SOFA_MODEL_URL, {
    role: "living room real sofa",
    name: "neighbor blueprint imported living room real sofa",
    x: 25.95,
    y: 0.08,
    z: 6.55,
    width: 3.45,
    height: 1.08,
    depth: 1.42,
    yaw: Math.PI,
    truthKind: "seat",
    truthLabel: "neighbor blueprint living room real sofa",
    actionHints: ["sit", "lay_down"],
  });
  placeNeighborPrefabWholeModel(REALISTIC_BOOKSHELF_MODEL_URL, {
    role: "living room real bookshelf",
    name: "neighbor blueprint imported living room real bookshelf",
    x: 23.35,
    y: 0.08,
    z: 6.05,
    width: 0.72,
    height: 2.08,
    depth: 2.5,
    yaw: Math.PI / 2,
    truthKind: "book",
    truthLabel: "neighbor blueprint real bookshelf",
    actionHints: ["read_book", "browse_books"],
  });
  addBox("neighbor blueprint coffee table", 26.15, 0.34, 5.22, 1.35, 0.12, 0.65, materials.livingWood, false);
  placeNeighborPrefabWholeModel(NEIGHBOR_PREFAB_BOOK_MODEL_URL, {
    role: "living room real book",
    name: "neighbor blueprint imported readable book",
    x: 26.15,
    y: 0.48,
    z: 5.22,
    width: 0.58,
    height: 0.08,
    depth: 0.38,
    yaw: 0.18,
    truthKind: "book",
    truthLabel: "neighbor blueprint readable book",
    actionHints: ["read_book"],
  });
  placeNeighborApartmentNode({ name: "neighbor blueprint imported dining table and chairs", pattern: /outdoor_table_and_chairs/i, x: 35.62, z: 7.15, width: 2.45, height: 1.2, depth: 2.25, yaw: Math.PI, uniform: true });
  addNeighborKitchen(34.85, 4.35);
  addNeighborBlueprintBathroom("neighbor blueprint hall bathroom", 33.7, 0.9);
  addNeighborPrefabBedSet("neighbor blueprint rear left bedroom", 26.35, -3.65, Math.PI / 2);
  addNeighborPrefabBedSet("neighbor blueprint rear middle bedroom", 33.62, -4.1, 0);
  addNeighborPrefabBedSet("neighbor blueprint rear right bedroom", 37.25, -4.1, 0);

  addNeighborFacadeWindow("neighbor blueprint living front window", 26.45, 1.62, frontZ, 1.78, 1.18, 1);
  addNeighborFacadeWindow("neighbor blueprint dining front window", 35.62, 1.62, frontZ, 1.62, 1.14, 1);
  addNeighborFacadeWindow("neighbor blueprint rear left bedroom window", 26.45, 1.62, backZ, 1.1, 1.06, -1);
  addNeighborFacadeWindow("neighbor blueprint rear middle bedroom window", 33.62, 1.62, backZ, 1.0, 1.04, -1);
  addNeighborFacadeWindow("neighbor blueprint rear right bedroom window", 37.25, 1.62, backZ, 1.0, 1.04, -1);
  addNeighborSideWindow("neighbor blueprint left living side window", leftX, 1.62, 6.05, 1.08, 1.08, -1);
  addNeighborSideWindow("neighbor blueprint left rear bedroom side window", leftX, 1.62, -2.7, 1.08, 1.08, -1);
  addNeighborSideWindow("neighbor blueprint right kitchen side window", rightX, 1.62, 4.1, 1.02, 1.0, 1);
  addNeighborSideWindow("neighbor blueprint right bathroom side window", rightX, 1.62, 0.9, 0.85, 0.85, 1);
  addNeighborSideWindow("neighbor blueprint right bedroom side window", rightX, 1.62, -2.7, 1.02, 1.04, 1);

  addBox("neighbor blueprint porch left brick column", doorX - 1.9, 1.35, frontZ + 0.86, 0.22, 2.55, 0.22, materials.neighborBrick, true);
  addBox("neighbor blueprint porch right brick column", doorX + 1.9, 1.35, frontZ + 0.86, 0.22, 2.55, 0.22, materials.neighborBrick, true);
  addBox("neighbor blueprint porch beam", doorX, 2.7, frontZ + 0.86, 4.05, 0.18, 0.22, materials.windowFrame, false);
  addGableRoof("neighbor blueprint porch roof", doorX, 2.78, frontZ + 0.72, 4.4, 1.95, 0.62, materials.neighborRoof);
  addBox("neighbor blueprint porch wall sconce", doorX - 1.04, 1.72, frontZ + 0.19, 0.14, 0.32, 0.08, materials.neighborWarmLight, false);

  interactZones.push({
    name: "neighbor blueprint front porch",
    x: doorX,
    z: frontZ + 1.0,
    floor: 0,
    radius: 1.55,
    action: () => {
      setNeighborHouseDoorOpen(!neighborHouseDoorOpen);
      show(neighborHouseDoorOpen ? "Neighbor blueprint house front door open." : "Neighbor blueprint house front door closed.");
    },
  });
}

function updateImportedHouseReferenceVisibility() {
  if (!importedHouseReference) return;
  const forceInside = params.get("houseReferenceInside") === "1";
  const insideMainHouse =
    Math.abs(player.position.x) < 7.7 &&
    player.position.z > -7.55 &&
    player.position.z < 7.55 &&
    player.position.y < 5.3;
  importedHouseReference.visible = forceInside || !insideMainHouse;
  importedHouseReferenceStatus = {
    ...importedHouseReferenceStatus,
    visible: importedHouseReference.visible,
    hiddenWhileInside: insideMainHouse && !forceInside,
  };
}

function placeRealisticToiletModel(placement) {
  if (!realisticToiletSource) return false;
  if (isSuppressedDownstairsToilet(placement.name, placement.floor)) {
    for (const fallback of placement.fallbacks || []) fallback.visible = false;
    return true;
  }
  const root = realisticToiletSource.clone(true);
  root.name = `${placement.name} imported realistic toilet`;
  makeImportedAssetMaterials(root);
  root.rotation.y = placement.rotationY || 0;
  scene.add(root);
  fitObjectToBox(root, {
    x: placement.x,
    y: floorBase(placement.floor) + 0.02,
    z: placement.z,
    width: 0.72,
    height: 0.84,
    depth: 0.78,
    uniform: true,
  });
  for (const fallback of placement.fallbacks || []) fallback.visible = false;
  removeSuppressedDownstairsToiletObjects();
  return true;
}

function loadRealisticToiletModel() {
  if (realisticToiletSource || realisticToiletLoading) return;
  realisticToiletLoading = true;
  gltfLoader.load(
    REALISTIC_TOILET_MODEL_URL,
    (gltf) => {
      realisticToiletSource = gltf.scene;
      realisticToiletLoading = false;
      while (pendingRealisticToilets.length) placeRealisticToiletModel(pendingRealisticToilets.shift());
    },
    undefined,
    (error) => {
      realisticToiletLoading = false;
      console.warn("Could not load imported toilet model", error);
    },
  );
}

function addRealisticToiletModel(name, x, z, floor, rotationY = 0, fallbacks = []) {
  if (isSuppressedDownstairsToilet(name, floor)) return;
  const placement = { name, x, z, floor, rotationY, fallbacks };
  if (!placeRealisticToiletModel(placement)) {
    pendingRealisticToilets.push(placement);
    loadRealisticToiletModel();
  }
}

const DOWNSTAIRS_TOILET_FORBIDDEN_ZONES = [
  { id: "stair_living_room_no_toilet_zone", xMin: -2.35, xMax: 4.25, zMin: -1.75, zMax: 5.9, yMax: ACTIVE_AVATAR_SECOND_FLOOR_Y - 0.35 },
  { id: "former_downstairs_powder_room_no_toilet_zone", xMin: 5.15, xMax: 8.15, zMin: -7.45, zMax: -4.75, yMax: ACTIVE_AVATAR_SECOND_FLOOR_Y - 0.35 },
];

function pointInsideRectZone(zone, world) {
  return world.x >= zone.xMin && world.x <= zone.xMax && world.z >= zone.zMin && world.z <= zone.zMax && world.y <= zone.yMax;
}

function nodeLooksLikeLooseBathroomFixture(node) {
  if (!node.isMesh || !node.material) return false;
  const materialsToCheck = Array.isArray(node.material) ? node.material : [node.material];
  const box = new THREE.Box3().setFromObject(node);
  const size = box.getSize(new THREE.Vector3());
  const compactFixtureScale = size.x <= 1.55 && size.y <= 1.45 && size.z <= 1.55;
  return materialsToCheck.some((material) => {
    const color = material?.color;
    if (!color) return false;
    const name = `${material.name || ""} ${node.name || ""}`.toLowerCase();
    const mostlyWhiteOrGrey = color.r > 0.55 && color.g > 0.55 && color.b > 0.52 && Math.abs(color.r - color.g) < 0.18;
    return /fixture|ceramic|porcelain|toilet|bath/.test(name) || (mostlyWhiteOrGrey && compactFixtureScale);
  });
}

function nodeAndAncestorName(node) {
  const names = [];
  let cursor = node;
  while (cursor && cursor !== scene) {
    if (cursor.name) names.push(String(cursor.name).toLowerCase());
    cursor = cursor.parent;
  }
  return names.join(" ");
}

function suppressedDownstairsBathroomReason(node, world) {
  if (!node || world.y > ACTIVE_AVATAR_SECOND_FLOOR_Y - 0.35) return "";
  const name = nodeAndAncestorName(node);
  if (/one-bedroom|neighbor|starbucks|kira bungalow|bungalow|school/.test(name)) return "";
  if (/\btoilet\b|downstairs powder|powder room|powder_room|bathroom toilet|bath mat/.test(name)) return "named_downstairs_bathroom_fixture";
  const zone = DOWNSTAIRS_TOILET_FORBIDDEN_ZONES.find((candidate) => pointInsideRectZone(candidate, world));
  if (zone && nodeLooksLikeLooseBathroomFixture(node)) return `forbidden_zone_${zone.id}`;
  return "";
}

function suppressedDownstairsBathroomRemovalRoot(node) {
  let cursor = node;
  let best = node;
  while (cursor && cursor.parent && cursor.parent !== scene) {
    const world = cursor.getWorldPosition(new THREE.Vector3());
    if (world.y > ACTIVE_AVATAR_SECOND_FLOOR_Y - 0.35) break;
    const name = String(cursor.name || "").toLowerCase();
    if (/\btoilet\b|downstairs powder|powder room|powder_room/.test(name)) best = cursor;
    cursor = cursor.parent;
  }
  return best;
}

function removeSuppressedDownstairsToiletObjects() {
  const removable = new Set();
  scene.traverse((node) => {
    if (node === scene) return;
    const world = node.getWorldPosition(new THREE.Vector3());
    if (suppressedDownstairsBathroomReason(node, world)) removable.add(suppressedDownstairsBathroomRemovalRoot(node));
  });
  for (const node of removable) {
    if (node.parent) node.parent.remove(node);
  }
  for (let i = pendingRealisticToilets.length - 1; i >= 0; i -= 1) {
    const placement = pendingRealisticToilets[i];
    if (isSuppressedDownstairsToilet(placement.name, placement.floor)) pendingRealisticToilets.splice(i, 1);
  }
  for (let i = interactZones.length - 1; i >= 0; i -= 1) {
    const zone = interactZones[i];
    const name = String(zone?.name || "").toLowerCase();
    if (zone?.floor === 0 && (name.includes("toilet") || name.includes("powder room") || name.includes("bathroom"))) interactZones.splice(i, 1);
  }
}

function downstairsToiletDebugSnapshot() {
  const items = [];
  scene.traverse((node) => {
    if (node === scene || !node.visible) return;
    const world = node.getWorldPosition(new THREE.Vector3());
    const name = String(node.name || "");
    const inForbiddenZone = DOWNSTAIRS_TOILET_FORBIDDEN_ZONES.some((zone) => pointInsideRectZone(zone, world));
    const reason = suppressedDownstairsBathroomReason(node, world);
    if (!name.toLowerCase().includes("toilet") && !inForbiddenZone && !reason) return;
    items.push({
      name,
      x: Number(world.x.toFixed(3)),
      y: Number(world.y.toFixed(3)),
      z: Number(world.z.toFixed(3)),
      inForbiddenZone,
      suppressedReason: reason,
      looksLikeLooseBathroomFixture: nodeLooksLikeLooseBathroomFixture(node),
    });
  });
  return items;
}

function makeActiveHeldProp(kind = "book") {
  const group = new THREE.Group();
  group.name = `active avatar held ${kind}`;
  if (kind === "basketball") {
    const ball = new THREE.Mesh(new THREE.SphereGeometry(0.16, 28, 18), materials.basketballOrange);
    ball.name = `${group.name} ball`;
    ball.castShadow = true;
    ball.receiveShadow = true;
    group.add(ball);
    const seamAngles = [
      { rx: Math.PI / 2, ry: 0, rz: 0 },
      { rx: 0, ry: Math.PI / 2, rz: 0 },
      { rx: 0, ry: 0, rz: Math.PI / 2 },
    ];
    for (const angle of seamAngles) {
      const seam = new THREE.Mesh(new THREE.TorusGeometry(0.162, 0.006, 8, 42), materials.basketballSeam);
      seam.name = `${group.name} seam`;
      seam.rotation.set(angle.rx, angle.ry, angle.rz);
      seam.castShadow = true;
      group.add(seam);
    }
    markTruthProp(group, "basketball", "held basketball", null, ["play_basketball", "dribble", "shoot_hoops"]);
    scene.add(group);
    return group;
  }
  if (kind === "phone" || kind === "tablet") {
    const isTablet = kind === "tablet";
    const body = new THREE.Mesh(new THREE.BoxGeometry(isTablet ? 0.17 : 0.12, 0.022, isTablet ? 0.28 : 0.23), materials.phoneBody);
    body.name = `${group.name} body`;
    body.castShadow = true;
    body.receiveShadow = true;
    group.add(body);
    const screen = new THREE.Mesh(new THREE.BoxGeometry(isTablet ? 0.148 : 0.102, 0.008, isTablet ? 0.246 : 0.19), materials.phoneScreen);
    screen.name = `${group.name} lit screen`;
    screen.position.y = 0.018;
    screen.castShadow = true;
    screen.receiveShadow = true;
    group.add(screen);
    markTruthProp(group, kind, isTablet ? "held tablet" : "held phone", null, ["read_book", "research", "take_notes", "take_photo", "browse_books", "control_tv"]);
    scene.add(group);
    return group;
  }
  if (kind === "coffee_cup") {
    const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.062, 0.18, 24), materials.paper);
    cup.name = `${group.name} cup`;
    cup.position.y = 0.08;
    group.add(cup);
    const lid = new THREE.Mesh(new THREE.CylinderGeometry(0.079, 0.079, 0.026, 24), materials.brushedSteel);
    lid.name = `${group.name} lid`;
    lid.position.y = 0.185;
    group.add(lid);
    const sleeve = new THREE.Mesh(new THREE.CylinderGeometry(0.077, 0.066, 0.065, 24), materials.livingWood);
    sleeve.name = `${group.name} sleeve`;
    sleeve.position.y = 0.09;
    group.add(sleeve);
    group.traverse((node) => {
      if (!node.isMesh) return;
      node.castShadow = true;
      node.receiveShadow = true;
    });
    markTruthProp(group, "coffee_cup", "held coffee cup", null, ["drink_coffee"]);
    scene.add(group);
    return group;
  }
  if (kind === "pink_ranger_morpher") {
    const body = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.04, 0.12), materials.phoneBody);
    body.name = `${group.name} black body`;
    group.add(body);
    const face = new THREE.Mesh(new THREE.BoxGeometry(0.17, 0.018, 0.09), materials.brushedSteel);
    face.name = `${group.name} silver face`;
    face.position.y = 0.028;
    group.add(face);
    const coin = new THREE.Mesh(new THREE.CylinderGeometry(0.036, 0.036, 0.012, 28), materials.bookGold);
    coin.name = `${group.name} Pterodactyl Power Coin`;
    coin.position.y = 0.044;
    group.add(coin);
    const pinkMark = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.006, 0.012), materials.pursePink);
    pinkMark.name = `${group.name} pink pterodactyl mark`;
    pinkMark.position.y = 0.053;
    group.add(pinkMark);
    group.traverse((node) => {
      if (!node.isMesh) return;
      node.castShadow = true;
      node.receiveShadow = true;
    });
    markTruthProp(group, "morpher", "held Pink Ranger morpher", null, ["pick_up_morpher", "hold_forward", "say_pterodactyl", "morph_pink_ranger", "change_clothes"]);
    scene.add(group);
    return group;
  }
  const isNotebook = kind === "notebook" || kind === "sketchbook";
  const coverMat = isNotebook ? materials.notebookCover : materials.bookBlue;
  const leftPage = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.018, 0.32), materials.paper);
  leftPage.name = `${group.name} left page`;
  leftPage.position.set(-0.12, 0, 0);
  leftPage.rotation.z = 0.08;
  group.add(leftPage);
  const rightPage = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.018, 0.32), materials.paper);
  rightPage.name = `${group.name} right page`;
  rightPage.position.set(0.12, 0, 0);
  rightPage.rotation.z = -0.08;
  group.add(rightPage);
  const cover = new THREE.Mesh(new THREE.BoxGeometry(0.54, 0.025, 0.38), coverMat);
  cover.name = `${group.name} cover`;
  cover.position.set(0, -0.018, 0);
  group.add(cover);
  if (isNotebook) {
    const pencil = new THREE.Mesh(new THREE.BoxGeometry(0.025, 0.025, 0.42), materials.pencilWood);
    pencil.name = `${group.name} pencil`;
    pencil.position.set(0.18, 0.045, 0.06);
    pencil.rotation.y = 0.38;
    group.add(pencil);
  }
  group.traverse((node) => {
    if (!node.isMesh) return;
    node.castShadow = true;
    node.receiveShadow = true;
  });
  markTruthProp(group, isNotebook ? "notebook" : "book", isNotebook ? "held sketch notebook" : "held open book", null, ["read_book", "sketch_design"]);
  scene.add(group);
  return group;
}

function setActiveHeldProp(kind = "") {
  if (!kind) {
    if (activeHeldProp) activeHeldProp.visible = false;
    activeHeldPropKind = "";
    return null;
  }
  if (!activeHeldProp || activeHeldPropKind !== kind) {
    if (activeHeldProp?.parent) activeHeldProp.parent.remove(activeHeldProp);
    activeHeldProp = makeActiveHeldProp(kind);
    activeHeldPropKind = kind;
  }
  activeHeldProp.visible = true;
  return activeHeldProp;
}

function updateActiveHeldProp(t = clock.elapsedTime) {
  if (!activeMarker) {
    setActiveHeldProp("");
    return;
  }
  const skillKind = activeSkillInteraction?.heldPropKind || "";
  const action = String(activeAvatarAction || "");
  const wantsPutDown = /(?:put|place|set|return)[_-]?(?:down[_-]?)?(?:the[_-]?)?tablet/.test(action);
  const wantsTablet = /tablet|look_online|online_lookup|research_online|take_notes|type_notes|write_notes|creative_write/.test(action);
  const wantsPhone = /phone|tablet|ebook|e-book|web|online|research|notes?|photo|picture|camera|browse/.test(action);
  const wantsCoffee = /coffee|tea|cafe|starbucks|drink/.test(action);
  const wantsBasketball = /basketball|dribble|shoot|hoop/.test(action);
  const wantsMorpher = /morpher|morph|pink_ranger|power_ranger/.test(action);
  const nextKind = wantsPutDown ? "" : skillKind || (wantsMorpher ? "pink_ranger_morpher" : wantsBasketball ? "basketball" : wantsCoffee ? "coffee_cup" : wantsTablet ? "tablet" : wantsPhone ? "phone" : /sketch|draw/.test(action) ? "sketchbook" : /read|book/.test(action) ? "book" : "");
  const prop = setActiveHeldProp(nextKind);
  if (!prop) return;
  const yaw = activeMarker.rotation?.y || 0;
  const forward = new THREE.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw));
  const right = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
  prop.position.copy(activeMarker.position)
    .add(forward.clone().multiplyScalar(0.38))
    .add(right.clone().multiplyScalar(0.05));
  prop.position.y = activeMarker.position.y + 1.05 + Math.sin(t * 2.2) * 0.01;
  if (activeHeldPropKind === "coffee_cup") {
    prop.position.y = activeMarker.position.y + 1.08 + Math.sin(t * 2.2) * 0.006;
    prop.rotation.set(0.1, yaw + 0.1, -0.05);
  } else if (activeHeldPropKind === "basketball") {
    const shotAge = basketballPracticeState ? t - basketballPracticeState.startedAt : 0;
    const shotStart = Math.max(0.8, (basketballPracticeState?.seconds || 0) - 1.65);
    if (basketballPracticeState && shotAge > shotStart) {
      const k = THREE.MathUtils.clamp((shotAge - shotStart) / 1.25, 0, 1);
      const start = activeMarker.position.clone().add(forward.clone().multiplyScalar(0.42)).add(right.clone().multiplyScalar(0.02));
      start.y = activeMarker.position.y + 1.18;
      const end = basketballPracticeState.shotTarget || BASKETBALL_SHOT_TARGET;
      prop.position.lerpVectors(start, end, k);
      prop.position.y += Math.sin(k * Math.PI) * 0.72;
      prop.rotation.set(t * 6.0, yaw + 0.35, t * 4.1);
    } else {
      prop.position.add(forward.clone().multiplyScalar(-0.04));
      prop.position.y = activeMarker.position.y + 0.72 + Math.abs(Math.sin(t * 7.6)) * 0.22;
      prop.rotation.set(t * 3.4, yaw + 0.2, t * 2.1);
    }
  } else if (activeHeldPropKind === "phone" || activeHeldPropKind === "tablet") {
    prop.position.add(right.clone().multiplyScalar(0.03));
    prop.position.y = activeMarker.position.y + 0.98 + Math.sin(t * 2.2) * 0.006;
    prop.rotation.set(-0.18, yaw + 0.16, 0.1);
  } else if (activeHeldPropKind === "pink_ranger_morpher") {
    prop.position.add(forward.clone().multiplyScalar(0.24)).add(right.clone().multiplyScalar(-0.02));
    prop.position.y = activeMarker.position.y + 1.17 + Math.sin(t * 2.2) * 0.004;
    prop.rotation.set(-0.32, yaw, 0);
  } else {
    prop.rotation.set(-0.42, yaw, 0.06);
  }
}

function clearActiveHeldProp() {
  setActiveHeldProp("");
}

function activeHeldPropEvidenceSnapshot() {
  if (!activeHeldProp?.visible) return null;
  const target = activeHeldProp.getWorldPosition(new THREE.Vector3());
  const contact = activeAvatarClosestHandContact(target);
  return {
    kind: activeHeldPropKind,
    x: Number(target.x.toFixed(3)),
    y: Number(target.y.toFixed(3)),
    z: Number(target.z.toFixed(3)),
    grounded: false,
    syntheticPreview: true,
    sourcePropId: "",
    sourceRemovedOrHidden: false,
    handContact: contact ? {
      node: contact.node,
      distance: Number(contact.distance.toFixed(3)),
      touching: contact.distance <= 0.20,
    } : null,
    reason: "Generated hand prop has no world-object pickup/put-down provenance yet.",
  };
}

function setGeneratedHomeBookshelfVisible(visible) {
  scene.traverse((node) => {
    const name = String(node.name || "").toLowerCase();
    if (!name.includes("home bookshelf") && !name.includes("home living room freestanding bookcase")) return;
    if (name.includes("imported realistic")) return;
    node.visible = visible;
  });
}

function addHomeImportedBookshelfBookRows() {
  const bookMats = [materials.notebookCover, materials.paper, materials.blanketBlue, materials.produceGreen, materials.produceYellow, materials.purseRed];
  const shelfZ = 4.82;
  const x = -7.12;
  const titles = ["home reading novel", "home design notebook", "home library reference", "home paperback"];
  for (let row = 0; row < 3; row += 1) {
    const baseY = 0.69 + row * 0.36;
    let cursorZ = shelfZ - 0.92 + row * 0.045;
    for (let i = 0; i < 16; i += 1) {
      const width = 0.055 + ((i + row) % 5) * 0.012;
      const height = 0.24 + ((i + row * 2) % 5) * 0.03;
      const book = addBox(
        `home reading shelf seated book row ${row + 1} volume ${i + 1}`,
        x,
        baseY + height * 0.5,
        cursorZ + width * 0.5,
        0.085,
        height,
        width,
        bookMats[(i + row) % bookMats.length],
        false,
        0,
      );
      book.rotation.x = i % 6 === 0 ? 0.025 : 0;
      markTruthProp(book, "book", titles[i % titles.length], 0, ["read_book", "browse_books"]);
      cursorZ += width + 0.015;
    }
  }
}

function loadRealisticHomeBookshelf() {
  gltfLoader.load(
    REALISTIC_BOOKSHELF_MODEL_URL,
    (gltf) => {
      const root = gltf.scene;
      root.name = "home living room imported realistic bookshelf";
      const meshCount = makeImportedAssetMaterials(root);
      root.rotation.y = Math.PI / 2;
      scene.add(root);
      const fittedSize = fitObjectToMeshBox(root, {
        x: -7.42,
        y: 0.07,
        z: 4.82,
        width: 0.72,
        height: 2.06,
        depth: 2.42,
        uniform: false,
      });
      realisticHomeBookshelf = root;
      markTruthProp(root, "book", "imported home bookshelf with books", 0, ["read_book", "browse_books"]);
      setGeneratedHomeBookshelfVisible(false);
      addHomeImportedBookshelfBookRows();
      realisticBookshelfStatus = {
        loaded: true,
        url: REALISTIC_BOOKSHELF_MODEL_URL,
        meshCount,
        fittedSize: {
          x: Number(fittedSize.x.toFixed(2)),
          y: Number(fittedSize.y.toFixed(2)),
          z: Number(fittedSize.z.toFixed(2)),
        },
      };
    },
    undefined,
    (error) => {
      setGeneratedHomeBookshelfVisible(true);
      realisticBookshelfStatus = {
        loaded: false,
        url: REALISTIC_BOOKSHELF_MODEL_URL,
        error: error?.message || String(error),
      };
      console.warn("Could not load imported bookshelf model", error);
    },
  );
}

function loadRealisticLivingRoomSofa() {
  gltfLoader.load(
    REALISTIC_SOFA_MODEL_URL,
    (gltf) => {
      const root = gltf.scene;
      root.name = "living room imported realistic modern sofa";
      const meshCount = makeImportedAssetMaterials(root);
      root.rotation.y = Math.PI;
      scene.add(root);
      const fittedSize = fitObjectToMeshBox(root, {
        x: -5.15,
        y: 0.08,
        z: 3.02,
        width: 3.45,
        height: 1.1,
        depth: 1.42,
        uniform: false,
      });
      realisticSofaStatus = {
        loaded: true,
        url: REALISTIC_SOFA_MODEL_URL,
        meshCount,
        fittedSize: {
          x: Number(fittedSize.x.toFixed(2)),
          y: Number(fittedSize.y.toFixed(2)),
          z: Number(fittedSize.z.toFixed(2)),
        },
      };
    },
    undefined,
    (error) => {
      realisticSofaStatus = {
        loaded: false,
        url: REALISTIC_SOFA_MODEL_URL,
        error: error?.message || String(error),
      };
      console.warn("Could not load imported sofa model", error);
    },
  );
}

function loadKiraSharedPhoneModel() {
  gltfLoader.load(
    KIRA_SHARED_PHONE_MODEL_URL,
    (gltf) => {
      const root = gltf.scene;
      root.name = "Kira personal Samsung phone on one-bedroom table";
      makeImportedAssetMaterials(root);
      root.rotation.set(-Math.PI / 2, 0.35, 0);
      scene.add(root);
      fitObjectToMeshBox(root, {
        x: KIRA_BUNGALOW_CENTER.x + 0.92,
        y: 0.82,
        z: KIRA_BUNGALOW_CENTER.z + 1.62,
        width: 0.18,
        height: 0.035,
        depth: 0.34,
        uniform: true,
      });
      root.userData.portable = true;
      root.userData.itemId = "kira_personal_phone";
      root.userData.canStore = ["ebook_notes", "library_ideas", "photos", "voice_notes"];
      markTruthProp(root, "phone", "Kira personal phone in her one-bedroom home", 0, ["read_book", "research", "take_notes", "take_photo", "browse_books"]);
    },
    undefined,
    (error) => {
      console.warn("Could not load Kira shared phone model", error);
    },
  );
}

function addLabel(text, x, y, z, width = 3.0, options = {}) {
  const { billboard = true, rotationY = 0 } = options;
  const canvas = document.createElement("canvas");
  canvas.width = 768;
  canvas.height = 192;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "rgba(7,17,28,0.86)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#7fd7ff";
  ctx.lineWidth = 8;
  ctx.strokeRect(8, 8, canvas.width - 16, canvas.height - 16);
  ctx.fillStyle = "#f5fbff";
  ctx.font = "bold 52px Segoe UI, Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const words = text.split(" ");
  let line = "";
  const lines = [];
  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > 660 && line) {
      lines.push(line);
      line = word;
    } else {
      line = test;
    }
  }
  lines.push(line);
  lines.slice(0, 2).forEach((l, i) => ctx.fillText(l, canvas.width / 2, 78 + i * 58));
  const texture = new THREE.CanvasTexture(canvas);
  const mat = new THREE.MeshBasicMaterial({ map: texture, transparent: true, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, width / 4), mat);
  mesh.position.set(x, y, z);
  mesh.rotation.y = rotationY;
  mesh.userData.billboard = billboard;
  scene.add(mesh);
  return mesh;
}

function addStorefrontSign(text, x, y, z, width = 3.0) {
  return addLabel(text, x, y, z, width, { billboard: false, rotationY: Math.PI });
}

function makeBillboardTexture(title, subtitle, options = {}) {
  const canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
  gradient.addColorStop(0, options.topColor || "#10243a");
  gradient.addColorStop(1, options.bottomColor || "#050b13");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = options.borderColor || "#ffd75d";
  ctx.lineWidth = 18;
  ctx.strokeRect(18, 18, canvas.width - 36, canvas.height - 36);

  if (options.flag) {
    ctx.save();
    ctx.translate(118, 110);
    ctx.fillStyle = "#dfe9ef";
    ctx.fillRect(0, 0, 16, 250);
    ctx.fillStyle = options.flagColor || "#ffd83d";
    ctx.beginPath();
    ctx.moveTo(18, 8);
    ctx.quadraticCurveTo(118, 42, 220, 12);
    ctx.lineTo(220, 132);
    ctx.quadraticCurveTo(118, 166, 18, 132);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "rgba(0,0,0,0.28)";
    ctx.lineWidth = 8;
    ctx.stroke();
    ctx.restore();
  }

  if (options.kiraWorld) {
    ctx.save();
    ctx.translate(100, 105);
    ctx.fillStyle = "#6bd3ff";
    ctx.beginPath();
    ctx.arc(120, 120, 86, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#101827";
    ctx.font = "bold 72px Segoe UI, Arial";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("K", 120, 120);
    ctx.restore();
  }

  ctx.fillStyle = options.titleColor || "#fff7d1";
  ctx.font = "bold 76px Segoe UI, Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const titleX = options.flag || options.kiraWorld ? 640 : canvas.width / 2;
  ctx.fillText(title, titleX, 210);
  ctx.fillStyle = options.subtitleColor || "#d8f2ff";
  ctx.font = "bold 38px Segoe UI, Arial";
  ctx.fillText(subtitle, titleX, 302);
  ctx.font = "28px Segoe UI, Arial";
  ctx.fillStyle = "rgba(255,255,255,0.78)";
  ctx.fillText(options.footer || "Walk into this wall to travel", titleX, 365);
  return new THREE.CanvasTexture(canvas);
}

function addWallBillboard(name, x, y, z, width, height, rotationY, title, subtitle, options = {}) {
  const texture = makeBillboardTexture(title, subtitle, options);
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(width, height),
    new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide }),
  );
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.rotation.y = rotationY;
  mesh.userData.portalBillboard = true;
  scene.add(mesh);
  return mesh;
}

function addRetroParkedTimeCar(x, z, yaw = Math.PI / 2, options = {}) {
  const group = new THREE.Group();
  group.name = "generic retro gullwing time-machine inspired parked car";
  group.position.set(x, 0.08, z);
  group.rotation.y = yaw;
  group.visible = options.visible !== false;

  const body = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.62, 1.62), materials.retroCarSteel);
  body.position.y = 0.52;
  body.castShadow = true;
  body.receiveShadow = true;
  group.add(body);

  const hood = new THREE.Mesh(new THREE.BoxGeometry(1.35, 0.34, 1.42), materials.retroCarSteel);
  hood.position.set(1.12, 0.77, 0);
  hood.castShadow = true;
  group.add(hood);

  const cabin = new THREE.Mesh(new THREE.BoxGeometry(1.18, 0.66, 1.28), materials.retroCarGlass);
  cabin.position.set(-0.28, 1.08, 0);
  cabin.castShadow = true;
  group.add(cabin);

  for (const side of [-1, 1]) {
    const door = new THREE.Mesh(new THREE.BoxGeometry(1.08, 0.08, 1.08), materials.retroCarSteel);
    door.position.set(-0.25, 1.32, side * 0.78);
    door.rotation.x = side * 0.72;
    door.castShadow = true;
    group.add(door);
  }

  for (const sx of [-1.15, 1.15]) {
    for (const sz of [-0.88, 0.88]) {
      const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.34, 0.22, 24), materials.ctfNpcBlack);
      wheel.position.set(sx, 0.32, sz);
      wheel.rotation.x = Math.PI / 2;
      wheel.castShadow = true;
      group.add(wheel);
    }
  }

  for (const sx of [-1.62, 1.62]) {
    const coil = new THREE.Mesh(new THREE.TorusGeometry(0.28, 0.025, 8, 32), materials.tardisGlow);
    coil.position.set(sx, 0.95, 0);
    coil.rotation.y = Math.PI / 2;
    group.add(coil);
  }

  scene.add(group);
  if (options.collider !== false) colliders.push({ x, z, sx: 3.8, sz: 2.15, floor: null });
  return group;
}

function placeCaptureFlagTimeCarModel(placement) {
  if (!captureFlagTimeCarSource) return false;
  const root = captureFlagTimeCarSource.clone(true);
  root.name = "capture flag parking lot imported time machine reference car";
  makeImportedAssetMaterials(root);
  root.rotation.y = placement.yaw || 0;
  scene.add(root);
  fitObjectToMeshBox(root, {
    x: placement.x,
    y: 0.07,
    z: placement.z,
    width: 4.25,
    height: 1.35,
    depth: 2.05,
    uniform: true,
  });
  if (placement.fallback) placement.fallback.visible = false;
  if (!placement.colliderAdded) {
    colliders.push({ x: placement.x, z: placement.z, sx: 3.8, sz: 2.15, floor: null });
    placement.colliderAdded = true;
  }
  return root;
}

function loadCaptureFlagTimeCarModel() {
  if (captureFlagTimeCarSource || captureFlagTimeCarLoading) return;
  captureFlagTimeCarLoading = true;
  gltfLoader.load(
    CAPTURE_FLAG_TIME_CAR_MODEL_URL,
    (gltf) => {
      captureFlagTimeCarSource = gltf.scene;
      captureFlagTimeCarLoading = false;
      while (pendingCaptureFlagTimeCars.length) placeCaptureFlagTimeCarModel(pendingCaptureFlagTimeCars.shift());
    },
    undefined,
    (error) => {
      captureFlagTimeCarLoading = false;
      console.warn("Could not load imported time machine reference car", error);
    },
  );
}

function addImportedCaptureFlagTimeCar(x, z, yaw = Math.PI / 2) {
  const fallback = addRetroParkedTimeCar(x, z, yaw, { visible: false, collider: false });
  fallback.name = "capture flag parking lot fallback car hidden after import";
  const placement = { x, z, yaw, fallback };
  if (!placeCaptureFlagTimeCarModel(placement)) {
    pendingCaptureFlagTimeCars.push(placement);
    loadCaptureFlagTimeCarModel();
  }
  return fallback;
}

function addCaptureFlagParkingLot() {
  if (captureFlagParkingLotBuilt) return;
  captureFlagParkingLotBuilt = true;
  addFloorTile("capture flag parking lot asphalt", 43.8, 41.8, 21.5, 16.5, materials.asphalt, 0.012);
  addFloorTile("capture flag parking lot sidewalk apron", 34.2, 41.8, 2.0, 16.8, materials.sidewalk, 0.025);
  for (const x of [37.7, 41.4, 45.1, 48.8]) {
    addBox("capture flag parking stall stripe", x, 0.045, 37.7, 0.12, 0.035, 6.4, materials.parkingStripe, false);
    addBox("capture flag parking stall stripe", x, 0.045, 45.9, 0.12, 0.035, 6.4, materials.parkingStripe, false);
  }
  addBox("capture flag parking lot curb north", 43.8, 0.12, 50.2, 21.8, 0.18, 0.28, materials.sidewalk, true);
  addBox("capture flag parking lot curb south", 43.8, 0.12, 33.4, 21.8, 0.18, 0.28, materials.sidewalk, true);
  addBox("capture flag portal wall", 54.65, 1.62, 42.2, 0.28, 3.24, 8.4, materials.trim, true);
  addWallBillboard(
    "capture flag home-world portal billboard",
    54.47,
    1.95,
    42.2,
    6.5,
    3.1,
    -Math.PI / 2,
    "Play Capture The Flag",
    "Run. Dodge. Grab the glowing flag.",
    { flag: true, footer: "Walk into this billboard wall" },
  );
  addImportedCaptureFlagTimeCar(43.2, 38.25, Math.PI / 2);
  addLabel("Game Parking", 43.5, 2.2, 50.6, 3.5);
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    captureFlagParkingLot: {
      restored: true,
      protectedFromNotebookCleanup: true,
      asphaltCenter: { x: 43.8, z: 41.8 },
      timeMachineCarUrl: CAPTURE_FLAG_TIME_CAR_MODEL_URL,
    },
  };
}

function addCaptureFlagFlagGroup() {
  const group = new THREE.Group();
  group.name = "capture flag glowing objective flag";
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.055, 2.35, 18), materials.handle);
  pole.position.y = 1.18;
  group.add(pole);
  const cloth = new THREE.Mesh(new THREE.PlaneGeometry(1.25, 0.72), materials.ctfFlagCloth);
  cloth.position.set(0.66, 1.78, 0);
  cloth.rotation.y = Math.PI / 2;
  group.add(cloth);
  const glow = new THREE.Mesh(new THREE.SphereGeometry(0.28, 24, 16), materials.ctfFlagGlow);
  glow.position.set(0.06, 2.45, 0);
  group.add(glow);
  captureFlagFlagLight = new THREE.PointLight(0xffd84c, 1.45, 9);
  captureFlagFlagLight.position.set(0, 2.2, 0);
  group.add(captureFlagFlagLight);
  group.visible = false;
  scene.add(group);
  captureFlagFlagGroup = group;
}

function createCaptureFlagStormtrooperFallback() {
  const group = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.24, 0.58, 6, 18), materials.ctfStormtrooper);
  body.name = "life size rounded stormtrooper torso";
  body.position.y = 1.02;
  body.scale.set(1.08, 1, 0.78);
  group.add(body);
  const belt = new THREE.Mesh(new THREE.BoxGeometry(0.54, 0.08, 0.08), materials.ctfNpcBlack);
  belt.name = "life size stormtrooper black belt";
  belt.position.set(0, 0.78, -0.19);
  group.add(belt);
  const chest = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.18, 0.055), materials.ctfNpcBlack);
  chest.name = "life size stormtrooper chest plate shadow";
  chest.position.set(0, 1.18, -0.22);
  group.add(chest);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.24, 24, 16), materials.ctfStormtrooper);
  head.name = "life size rounded stormtrooper helmet";
  head.position.y = 1.66;
  head.scale.set(1.08, 0.9, 0.96);
  group.add(head);
  const visor = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.08, 0.045), materials.ctfNpcBlack);
  visor.name = "life size stormtrooper visor";
  visor.position.set(0, 1.69, -0.235);
  group.add(visor);
  for (const sx of [-0.38, 0.38]) {
    const shoulder = new THREE.Mesh(new THREE.SphereGeometry(0.105, 16, 10), materials.ctfStormtrooper);
    shoulder.position.set(sx * 0.82, 1.28, 0);
    shoulder.scale.set(1.0, 0.82, 0.9);
    group.add(shoulder);
    const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.072, 0.72, 16), materials.ctfStormtrooper);
    arm.name = "life size stormtrooper rounded arm";
    arm.position.set(sx, 0.94, -0.01);
    arm.rotation.z = -sx * 0.08;
    group.add(arm);
    const glove = new THREE.Mesh(new THREE.SphereGeometry(0.072, 14, 10), materials.ctfNpcBlack);
    glove.position.set(sx * 1.04, 0.56, -0.02);
    group.add(glove);
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.09, 0.72, 16), materials.ctfStormtrooper);
    leg.name = "life size stormtrooper rounded leg";
    leg.position.set(sx * 0.36, 0.36, 0);
    group.add(leg);
    const boot = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.08, 0.26), materials.ctfNpcBlack);
    boot.position.set(sx * 0.36, 0.04, -0.045);
    group.add(boot);
  }
  const blaster = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.06, 0.52), materials.ctfNpcBlack);
  blaster.name = "life size stormtrooper prop blaster";
  blaster.position.set(0.42, 0.78, -0.3);
  blaster.rotation.y = -0.18;
  group.add(blaster);
  return group;
}

function createCaptureFlagDalekFallback() {
  const group = new THREE.Group();
  const skirt = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.72, 0.95, 24), materials.ctfDalekBronze);
  skirt.position.y = 0.52;
  group.add(skirt);
  const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.5, 0.72, 24), materials.ctfDalekBronze);
  torso.position.y = 1.22;
  group.add(torso);
  const dome = new THREE.Mesh(new THREE.SphereGeometry(0.4, 24, 12), materials.ctfDalekBronze);
  dome.position.y = 1.76;
  group.add(dome);
  const eye = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.08, 0.55), materials.ctfNpcBlack);
  eye.position.set(0, 1.78, -0.48);
  group.add(eye);
  return group;
}

function loadCaptureFlagNpcModel(type) {
  if (captureFlagNpcModels[type] || captureFlagNpcLoading[type]) return;
  captureFlagNpcLoading[type] = true;
  const url = type === "dalek" ? CAPTURE_FLAG_DALEK_MODEL_URL : CAPTURE_FLAG_STORMTROOPER_MODEL_URL;
  gltfLoader.load(
    url,
    (gltf) => {
      captureFlagNpcModels[type] = gltf.scene;
      captureFlagNpcLoading[type] = false;
      for (const npc of captureFlagNpcs.filter((item) => item.type === type)) attachCaptureFlagNpcModel(npc);
    },
    undefined,
    () => {
      captureFlagNpcLoading[type] = false;
    },
  );
}

function attachCaptureFlagNpcModel(npc) {
  if (!npc?.group || !captureFlagNpcModels[npc.type] || npc.modelAttached) return;
  const model = captureFlagNpcModels[npc.type].clone(true);
  model.name = `${npc.name} imported ${npc.type} body`;
  model.traverse((node) => {
    if (node.isMesh) {
      node.castShadow = true;
      node.receiveShadow = true;
      node.frustumCulled = false;
    }
  });
  const fittedSize = fitObjectToMeshBox(model, {
    x: 0,
    y: 0.02,
    z: 0,
    width: npc.type === "dalek" ? 0.95 : 0.72,
    height: npc.type === "dalek" ? 1.65 : 1.78,
    depth: npc.type === "dalek" ? 0.95 : 0.58,
    uniform: true,
  });
  const saneImportedScale =
    fittedSize.y > 0.65 &&
    fittedSize.y < 2.25 &&
    fittedSize.x < 1.6 &&
    fittedSize.z < 1.6;
  if (!saneImportedScale) {
    model.visible = false;
    npc.modelSuppressedReason = `imported ${npc.type} fit was unsafe (${fittedSize.x.toFixed(2)} x ${fittedSize.y.toFixed(2)} x ${fittedSize.z.toFixed(2)})`;
  }
  npc.group.add(model);
  npc.group.updateMatrixWorld(true);
  const groupSize = new THREE.Box3().setFromObject(npc.group).getSize(new THREE.Vector3());
  if (groupSize.y > 3.0 || groupSize.x > 2.4 || groupSize.z > 2.4) {
    model.visible = false;
    npc.modelSuppressedReason = `imported ${npc.type} group bounds were unsafe (${groupSize.x.toFixed(2)} x ${groupSize.y.toFixed(2)} x ${groupSize.z.toFixed(2)})`;
  }
  if (saneImportedScale) {
    const importedStillVisible = model.visible !== false;
    for (const child of npc.fallback.children) child.visible = !importedStillVisible;
    npc.modelAttached = importedStillVisible;
  }
}

function addCaptureFlagNpc(type, name, waypoints, options = {}) {
  const group = new THREE.Group();
  group.name = name;
  group.userData.captureFlagNpc = true;
  const fallback = type === "dalek" ? createCaptureFlagDalekFallback() : createCaptureFlagStormtrooperFallback();
  fallback.name = `${name} fallback body`;
  group.add(fallback);
  group.position.copy(waypoints[0]);
  group.position.y = ACTIVE_AVATAR_GROUND_Y;
  scene.add(group);
  const npc = {
    type,
    name,
    group,
    fallback,
    waypoints: waypoints.map((point) => point.clone()),
    index: 1,
    speed: options.speed || (type === "dalek" ? 0.72 : 0.95),
    chaseSpeed: options.chaseSpeed || (type === "dalek" ? 1.15 : 1.42),
    sightRadius: options.sightRadius || (type === "dalek" ? 9.5 : 12.5),
    tagRadius: options.tagRadius || (type === "dalek" ? 0.9 : 0.72),
    collisionRadius: options.collisionRadius || (type === "dalek" ? 0.78 : 0.52),
    forwardYawOffset: options.forwardYawOffset ?? (type === "dalek" ? 0 : Math.PI),
    alertUntil: 0,
    lastSeen: null,
    modelAttached: false,
    modelSuppressedReason: null,
  };
  captureFlagNpcs.push(npc);
  loadCaptureFlagNpcModel(type);
  attachCaptureFlagNpcModel(npc);
  return npc;
}

function addRuinedBuilding(name, x, z, sx, sz, options = {}) {
  const h = options.height || 2.3;
  addFloorTile(`${name} cracked floor`, x, z, sx, sz, materials.ctfConcrete, 0.018);
  addBox(`${name} torn north wall`, x, h / 2, z - sz / 2, sx, h, 0.28, materials.ctfBrick, true);
  addBox(`${name} torn west wall`, x - sx / 2, h / 2, z, 0.28, h, sz * 0.72, materials.ctfBrick, true);
  addBox(`${name} broken short wall`, x + sx * 0.24, 0.8, z + sz / 2, sx * 0.52, 1.6, 0.28, materials.ctfBrick, true);
  for (let i = 0; i < 8; i += 1) {
    const rx = x - sx * 0.35 + ((i * 1.37) % sx) - sx * 0.15;
    const rz = z - sz * 0.2 + ((i * 0.91) % sz) - sz * 0.18;
    addBox(`${name} rubble chunk`, rx, 0.18, rz, 0.45 + (i % 3) * 0.18, 0.28, 0.35 + (i % 2) * 0.22, materials.ctfRubble, true);
  }
}

function addCaptureFlagBattlefield() {
  const beforeBuild = new Set(scene.children);
  captureFlagBattlefieldGroup = new THREE.Group();
  captureFlagBattlefieldGroup.name = "capture flag notebook world isolated battlefield";
  scene.add(captureFlagBattlefieldGroup);
  const b = captureFlagWorld.bounds;
  const centerX = (b.xMin + b.xMax) / 2;
  const centerZ = (b.zMin + b.zMax) / 2;
  addFloorTile("capture flag battlefield scorched terrain", centerX, centerZ, b.xMax - b.xMin, b.zMax - b.zMin, materials.ctfConcrete, -0.005);
  addFloorTile("capture flag main street", centerX, 130, b.xMax - b.xMin - 8, 7.0, materials.ctfAsphalt, 0.015);
  addFloorTile("capture flag cross street", 123, centerZ, 6.4, b.zMax - b.zMin - 10, materials.ctfAsphalt, 0.017);
  addFloorTile("capture flag east alley street", 148, centerZ + 6, 5.6, b.zMax - b.zMin - 18, materials.ctfAsphalt, 0.017);
  addFloorTile("capture flag far boulevard", centerX + 28, 204, b.xMax - b.xMin - 26, 8.0, materials.ctfAsphalt, 0.018);
  addFloorTile("capture flag west broken side street", 101, centerZ + 32, 6.0, b.zMax - b.zMin - 22, materials.ctfAsphalt, 0.018);
  addFloorTile("capture flag far east service road", 212, centerZ + 14, 6.4, b.zMax - b.zMin - 28, materials.ctfAsphalt, 0.018);

  addBox("capture flag north boundary wall", centerX, 1.7, b.zMin, b.xMax - b.xMin, 3.4, 0.36, materials.trim, true);
  addBox("capture flag south boundary wall", centerX, 1.7, b.zMax, b.xMax - b.xMin, 3.4, 0.36, materials.trim, true);
  addBox("capture flag west boundary wall", b.xMin, 1.7, centerZ, 0.36, 3.4, b.zMax - b.zMin, materials.trim, true);
  addBox("capture flag east boundary wall", b.xMax, 1.7, centerZ, 0.36, 3.4, b.zMax - b.zMin, materials.trim, true);

  const basePad = addCylinder("capture flag blue base camp start ring", captureFlagWorld.base.x, 0.025, captureFlagWorld.base.z, 4.1, 0.05, materials.ctfBase, false);
  basePad.userData.captureFlagBase = true;
  addBox("capture flag base supply wall", 96.2, 0.75, 101.8, 5.8, 1.35, 0.26, materials.ctfBase, true);
  addBox("capture flag base crate left", 102.8, 0.32, 101.2, 1.0, 0.6, 0.9, materials.ctfRubble, true);
  addBox("capture flag base crate right", 104.1, 0.42, 99.6, 0.9, 0.8, 0.8, materials.ctfRubble, true);

  addRuinedBuilding("capture flag ruined library block", 103, 122, 11, 12, { height: 2.8 });
  addRuinedBuilding("capture flag torn apartment block", 136, 112, 13, 10, { height: 3.2 });
  addRuinedBuilding("capture flag collapsed corner store", 142, 146, 12, 12, { height: 2.5 });
  addRuinedBuilding("capture flag broken warehouse", 112, 158, 14, 10, { height: 2.4 });
  addRuinedBuilding("capture flag shattered office row", 176, 126, 18, 13, { height: 3.0 });
  addRuinedBuilding("capture flag bombed theater shell", 202, 162, 20, 16, { height: 3.4 });
  addRuinedBuilding("capture flag torn parking garage", 188, 214, 18, 18, { height: 2.7 });
  addRuinedBuilding("capture flag ruined school block", 222, 222, 14, 18, { height: 3.1 });
  addRuinedBuilding("capture flag collapsed clinic", 132, 210, 16, 14, { height: 2.8 });
  addBox("capture flag concrete cover wall one", 119, 0.85, 134, 8.5, 1.55, 0.32, materials.ctfRubble, true);
  addBox("capture flag concrete cover wall two", 134, 0.85, 133, 0.32, 1.55, 7.5, materials.ctfRubble, true);
  addBox("capture flag concrete cover wall three", 151, 0.85, 124, 6.0, 1.55, 0.32, materials.ctfRubble, true);
  addBox("capture flag far concrete cover wall four", 184, 0.85, 178, 10.5, 1.55, 0.32, materials.ctfRubble, true);
  addBox("capture flag far concrete cover wall five", 211, 0.85, 193, 0.32, 1.55, 9.0, materials.ctfRubble, true);
  addBox("capture flag far concrete cover wall six", 158, 0.85, 224, 8.0, 1.55, 0.32, materials.ctfRubble, true);

  addWallBillboard(
    "capture flag return to Kira World billboard",
    captureFlagWorld.returnPortal.x,
    2.05,
    captureFlagWorld.returnPortal.z,
    6.8,
    3.2,
    Math.PI,
    "Kira World",
    "Return To Home World",
    { kiraWorld: true, borderColor: "#6bd3ff", footer: "Walk into this billboard to leave the game" },
  );
  addBox("capture flag return billboard wall", captureFlagWorld.returnPortal.x, 1.62, captureFlagWorld.returnPortal.z + 0.18, 7.4, 3.24, 0.28, materials.trim, true);

  addCaptureFlagFlagGroup();
  addCaptureFlagNpc("stormtrooper", "capture flag stormtrooper patrol alpha", [
    new THREE.Vector3(119, ACTIVE_AVATAR_GROUND_Y, 118),
    new THREE.Vector3(134, ACTIVE_AVATAR_GROUND_Y, 118),
    new THREE.Vector3(134, ACTIVE_AVATAR_GROUND_Y, 132),
    new THREE.Vector3(119, ACTIVE_AVATAR_GROUND_Y, 132),
  ]);
  addCaptureFlagNpc("stormtrooper", "capture flag stormtrooper patrol beta", [
    new THREE.Vector3(149, ACTIVE_AVATAR_GROUND_Y, 128),
    new THREE.Vector3(155, ACTIVE_AVATAR_GROUND_Y, 144),
    new THREE.Vector3(142, ACTIVE_AVATAR_GROUND_Y, 151),
    new THREE.Vector3(137, ACTIVE_AVATAR_GROUND_Y, 136),
  ], { speed: 1.04, chaseSpeed: 1.52 });
  addCaptureFlagNpc("stormtrooper", "capture flag stormtrooper guard gamma", [
    new THREE.Vector3(127, ACTIVE_AVATAR_GROUND_Y, 160),
    new THREE.Vector3(145, ACTIVE_AVATAR_GROUND_Y, 161),
    new THREE.Vector3(153, ACTIVE_AVATAR_GROUND_Y, 151),
    new THREE.Vector3(135, ACTIVE_AVATAR_GROUND_Y, 149),
  ], { speed: 0.88, chaseSpeed: 1.45 });
  addCaptureFlagNpc("stormtrooper", "capture flag stormtrooper patrol delta", [
    new THREE.Vector3(176, ACTIVE_AVATAR_GROUND_Y, 126),
    new THREE.Vector3(199, ACTIVE_AVATAR_GROUND_Y, 132),
    new THREE.Vector3(199, ACTIVE_AVATAR_GROUND_Y, 154),
    new THREE.Vector3(172, ACTIVE_AVATAR_GROUND_Y, 151),
  ], { speed: 1.02, chaseSpeed: 1.58, sightRadius: 15.5 });
  addCaptureFlagNpc("stormtrooper", "capture flag stormtrooper patrol epsilon", [
    new THREE.Vector3(212, ACTIVE_AVATAR_GROUND_Y, 165),
    new THREE.Vector3(225, ACTIVE_AVATAR_GROUND_Y, 188),
    new THREE.Vector3(205, ACTIVE_AVATAR_GROUND_Y, 202),
    new THREE.Vector3(190, ACTIVE_AVATAR_GROUND_Y, 182),
  ], { speed: 0.98, chaseSpeed: 1.5, sightRadius: 14.5 });
  addCaptureFlagNpc("stormtrooper", "capture flag stormtrooper far guard zeta", [
    new THREE.Vector3(170, ACTIVE_AVATAR_GROUND_Y, 220),
    new THREE.Vector3(202, ACTIVE_AVATAR_GROUND_Y, 236),
    new THREE.Vector3(224, ACTIVE_AVATAR_GROUND_Y, 218),
    new THREE.Vector3(194, ACTIVE_AVATAR_GROUND_Y, 204),
  ], { speed: 0.82, chaseSpeed: 1.44, sightRadius: 16.5 });
  addCaptureFlagNpc("dalek", "capture flag dalek patrol bronze one", [
    new THREE.Vector3(112, ACTIVE_AVATAR_GROUND_Y, 142),
    new THREE.Vector3(124, ACTIVE_AVATAR_GROUND_Y, 145),
    new THREE.Vector3(121, ACTIVE_AVATAR_GROUND_Y, 158),
    new THREE.Vector3(109, ACTIVE_AVATAR_GROUND_Y, 154),
  ]);
  addCaptureFlagNpc("dalek", "capture flag dalek patrol bronze two", [
    new THREE.Vector3(145, ACTIVE_AVATAR_GROUND_Y, 101),
    new THREE.Vector3(156, ACTIVE_AVATAR_GROUND_Y, 111),
    new THREE.Vector3(150, ACTIVE_AVATAR_GROUND_Y, 124),
    new THREE.Vector3(138, ACTIVE_AVATAR_GROUND_Y, 113),
  ], { speed: 0.78, chaseSpeed: 1.18 });
  addCaptureFlagNpc("dalek", "capture flag dalek patrol bronze three", [
    new THREE.Vector3(164, ACTIVE_AVATAR_GROUND_Y, 176),
    new THREE.Vector3(184, ACTIVE_AVATAR_GROUND_Y, 188),
    new THREE.Vector3(178, ACTIVE_AVATAR_GROUND_Y, 210),
    new THREE.Vector3(154, ACTIVE_AVATAR_GROUND_Y, 198),
  ], { speed: 0.72, chaseSpeed: 1.2, sightRadius: 13.5 });
  addCaptureFlagNpc("dalek", "capture flag dalek patrol bronze four", [
    new THREE.Vector3(214, ACTIVE_AVATAR_GROUND_Y, 202),
    new THREE.Vector3(228, ACTIVE_AVATAR_GROUND_Y, 226),
    new THREE.Vector3(204, ACTIVE_AVATAR_GROUND_Y, 236),
    new THREE.Vector3(192, ACTIVE_AVATAR_GROUND_Y, 214),
  ], { speed: 0.7, chaseSpeed: 1.22, sightRadius: 14.0 });
  addCaptureFlagNpc("dalek", "capture flag dalek patrol bronze five", [
    new THREE.Vector3(186, ACTIVE_AVATAR_GROUND_Y, 118),
    new THREE.Vector3(226, ACTIVE_AVATAR_GROUND_Y, 118),
    new THREE.Vector3(229, ACTIVE_AVATAR_GROUND_Y, 148),
    new THREE.Vector3(196, ACTIVE_AVATAR_GROUND_Y, 152),
  ], { speed: 0.76, chaseSpeed: 1.26, sightRadius: 13.0 });

  const baseLabel = addLabel("Base Camp", captureFlagWorld.base.x, 2.2, captureFlagWorld.base.z - 5.2, 3.6);
  baseLabel.name = "capture flag base camp label";

  const created = scene.children.filter((obj) => obj !== captureFlagBattlefieldGroup && !beforeBuild.has(obj));
  for (const obj of created) captureFlagBattlefieldGroup.attach(obj);
  captureFlagBattlefieldGroup.visible = false;
}

function addRoomLabel(text, x, z, floor = 0) {
  return null;
  const y = floor ? 3.45 : 0.08;
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 128;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#233a4a";
  ctx.fillRect(0, 0, 512, 128);
  ctx.strokeStyle = "#eaf8ff";
  ctx.strokeRect(8, 8, 496, 112);
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 40px Segoe UI, Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 256, 64);
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(2.5, 0.62),
    new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true })
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.set(x, y, z);
  scene.add(mesh);
}

function addLight() {
  scene.add(new THREE.HemisphereLight(0xdfefff, 0x8c7b65, 1.9));
  const sun = new THREE.DirectionalLight(0xffffff, 2.4);
  sun.position.set(-30, 44, 18);
  sun.castShadow = true;
  sun.shadow.camera.left = -45;
  sun.shadow.camera.right = 45;
  sun.shadow.camera.top = 45;
  sun.shadow.camera.bottom = -45;
  sun.shadow.mapSize.set(2048, 2048);
  scene.add(sun);
}

function addSite() {
  const scaledGrassCount = (count) => Math.max(600, Math.floor(count * HOME_WORLD_GRASS_DENSITY_SCALE));
  const lawn = HOME_WORLD_PRE_RAM_LIGHT_MODE
    ? { x: 16, z: 28, width: 150, depth: 112 }
    : { x: 60, z: 96, width: 432, depth: 384 };
  addFloorTile("expanded home world lawn", lawn.x, lawn.z, lawn.width, lawn.depth, materials.grass, -0.012);
  addFloorTile("public library side lawn", 25, 44, 32, 28, materials.grass, -0.012);
  const grassAvoid = [
    { x: 0, z: 0, sx: 18.5, sz: 17 },
    { x: 0, z: -18.5, sx: 11.5, sz: 8.5 },
    { x: 0, z: 16.8, sx: 72, sz: 4.3 },
    { x: 0, z: 23, sx: 72, sz: 12.5 },
    { x: 0, z: 29.2, sx: 72, sz: 4.3 },
    { x: 0, z: 35.2, sx: 66, sz: 13.5 },
    { x: 24.5, z: 43.4, sx: 13.8, sz: 10.4 },
    { x: 20.5, z: 48.1, sx: 4.0, sz: 3.0 },
    { x: 43.8, z: 41.8, sx: 24.5, sz: 19.2 },
    { x: KIRA_BUNGALOW_CENTER.x, z: KIRA_BUNGALOW_CENTER.z, sx: KIRA_BUNGALOW_WIDTH + 3.4, sz: KIRA_BUNGALOW_DEPTH + 5.8 },
    { x: ONE_BEDROOM_HOUSE_CENTER.x, z: ONE_BEDROOM_HOUSE_CENTER.z, sx: ONE_BEDROOM_HOUSE_WIDTH + 34.0, sz: ONE_BEDROOM_HOUSE_DEPTH + 34.0 },
    { x: ONE_BEDROOM_HOUSE_CENTER.x, z: ONE_BEDROOM_HOUSE_CENTER.z + 1.2, sx: ONE_BEDROOM_HOUSE_WIDTH + 24.0, sz: ONE_BEDROOM_HOUSE_DEPTH + 26.0 },
    { x: STARBUCKS_CENTER.x, z: STARBUCKS_CENTER.z, sx: STARBUCKS_WIDTH + 5.4, sz: STARBUCKS_DEPTH + 9.2 },
    { x: PARK_BASKETBALL_CENTER.x, z: PARK_BASKETBALL_CENTER.z, sx: PARK_BASKETBALL_COURT_WIDTH + 10.0, sz: PARK_BASKETBALL_COURT_DEPTH + 10.0 },
    { x: 25.85, z: 10.7, sx: 4.2, sz: 2.8 },
    { x: 25.85, z: 13.65, sx: 2.0, sz: 7.4 },
    { x: 33.75, z: 13.1, sx: 4.4, sz: 8.8 },
    { x: 70, z: 23, sx: 74, sz: 12.5 },
    { x: 70, z: 29.2, sx: 74, sz: 4.3 },
  ];
  addGrassBladeField({
    name: "home world lawn individual grass blades",
    x: 18,
    z: 18,
    width: 118,
    depth: 92,
    count: scaledGrassCount(23000),
    seed: 70101,
    avoid: grassAvoid,
  });
  addGrassBladeField({
    name: "home world taller edge grass tufts",
    x: 0,
    z: -20,
    width: 64,
    depth: 8,
    count: scaledGrassCount(3200),
    y: 0.04,
    seed: 70102,
    avoid: grassAvoid,
  });
  addGrassBladeField({
    name: "public library reading lawn grass blades",
    x: 25,
    z: 46,
    width: 30,
    depth: 22,
    count: scaledGrassCount(6200),
    seed: 70103,
    avoid: grassAvoid,
  });
  if (!HOME_WORLD_PRE_RAM_LIGHT_MODE) {
    addGrassBladeField({
      name: "future park first lawn grass blades around basketball court",
      x: PARK_BASKETBALL_CENTER.x,
      z: PARK_BASKETBALL_CENTER.z,
      width: 46,
      depth: 38,
      count: scaledGrassCount(7600),
      seed: 70104,
      avoid: grassAvoid,
    });
  }
  if (HOME_WORLD_HIGH_DETAIL_GRASS_PATCHES) {
    for (const patch of [
      { x: -18, z: 6, yaw: 0.2 },
      { x: 14, z: -9, yaw: -0.55 },
      { x: 36, z: 18, yaw: 0.85 },
      { x: 76, z: 43, yaw: 0.05 },
    ]) {
      placeHomeWorldActivityModel(HOME_WORLD_REAL_GRASS_PATCH_MODEL_URL, {
        role: `realGrassPatch${patch.x}_${patch.z}`,
        name: "imported real grass sample patch for Home World lawn",
        x: patch.x,
        y: 0.02,
        z: patch.z,
        width: 4.2,
        height: 0.28,
        depth: 4.2,
        yaw: patch.yaw,
        uniform: true,
        truthKind: "grass",
        truthLabel: "imported real grass patch",
        actionHints: ["walk"],
      });
    }
  } else {
    homeWorldActivityStatus = {
      ...homeWorldActivityStatus,
      realGrassPatches: {
        ...homeWorldActivityStatus.realGrassPatches,
        loaded: false,
        enabled: false,
        disabledReason: "disabled by default after the expanded map caused lag; add ?highGrass=1 to the Home World URL for the expensive imported patch stress test",
      },
    };
  }
  if (HOME_WORLD_PRE_RAM_LIGHT_MODE) {
    addFloorTile("street", 20, 23, 134, 10, materials.asphalt, 0);
    addFloorTile("house sidewalk", 20, 16.8, 134, 3.1, materials.sidewalk, 0.02);
    addFloorTile("strip mall sidewalk", 20, 29.2, 134, 3.1, materials.sidewalk, 0.02);
  } else {
    addFloorTile("street", 0, 23, 70, 10, materials.asphalt, 0);
    addFloorTile("extended main road east", 70, 23, 70, 10, materials.asphalt, 0);
    addFloorTile("house sidewalk", 0, 16.8, 70, 3.1, materials.sidewalk, 0.02);
    addFloorTile("extended house sidewalk east", 70, 16.8, 70, 3.1, materials.sidewalk, 0.02);
    addFloorTile("strip mall sidewalk", 0, 29.2, 70, 3.1, materials.sidewalk, 0.02);
    addFloorTile("extended strip mall sidewalk east", 70, 29.2, 70, 3.1, materials.sidewalk, 0.02);
  }
  addFloorTile("starbucks cafe concrete pad", STARBUCKS_CENTER.x, STARBUCKS_CENTER.z, STARBUCKS_WIDTH + 5.0, STARBUCKS_DEPTH + 9.2, materials.sidewalk, 0.024);
  addFloorTile("starbucks cafe front walk", STARBUCKS_CENTER.x, (STARBUCKS_PUBLIC_FRONT_Z + 29.2) / 2, 2.6, Math.abs(STARBUCKS_PUBLIC_FRONT_Z - 29.2), materials.sidewalk, 0.03);
  if (!HOME_WORLD_PRE_RAM_LIGHT_MODE) {
    addFloorTile("future park grass pad", PARK_BASKETBALL_CENTER.x, PARK_BASKETBALL_CENTER.z, PARK_BASKETBALL_COURT_WIDTH + 12.0, PARK_BASKETBALL_COURT_DEPTH + 10.0, materials.grass, -0.012);
    addFloorTile("future park path to basketball court", PARK_BASKETBALL_CENTER.x - 2.2, (29.2 + PARK_BASKETBALL_CENTER.z - PARK_BASKETBALL_COURT_DEPTH / 2) / 2, 2.4, PARK_BASKETBALL_CENTER.z - PARK_BASKETBALL_COURT_DEPTH / 2 - 29.2, materials.sidewalk, 0.026);
  }
  for (let i = -32; i <= 32; i += 4) addBox("crosswalk stripe", i, 0.035, 23, 2.6, 0.04, 0.38, new THREE.MeshStandardMaterial({ color: 0xf5f1e7 }), false);
  if (!HOME_WORLD_PRE_RAM_LIGHT_MODE) {
    for (let i = 40; i <= 102; i += 8) addBox("extended road dashed lane stripe", i, 0.035, 23, 3.6, 0.04, 0.18, materials.parkingStripe, false);
  }
  if (MAIN_TWO_STORY_HOUSE_ENABLED) addBackyardPool();
}

function addBackyardPool() {
  const x = 0;
  const z = -18.5;
  addFloorTile("backyard pool concrete deck left strip", x - 5.9, z, 1.2, 8.8, materials.sidewalk, 0.015);
  addFloorTile("backyard pool concrete deck right strip", x + 5.9, z, 1.2, 8.8, materials.sidewalk, 0.015);
  addFloorTile("backyard pool concrete deck shallow strip", x, z + 3.95, 12.6, 0.9, materials.sidewalk, 0.015);
  addFloorTile("backyard pool concrete deck deep strip", x, z - 3.95, 12.6, 0.9, materials.sidewalk, 0.015);
  addBox("backyard pool deep end wall", x, -0.28, z - 3.25, 10.1, 0.62, 0.18, materials.trim, false);
  addBox("backyard pool shallow end wall", x, -0.28, z + 3.25, 10.1, 0.62, 0.18, materials.trim, false);
  addBox("backyard pool left wall", x - 5.0, -0.28, z, 0.18, 0.62, 6.5, materials.trim, false);
  addBox("backyard pool right wall", x + 5.0, -0.28, z, 0.18, 0.62, 6.5, materials.trim, false);
  addFloorTile("backyard pool basin floor", x, z, 9.65, 6.15, materials.activeBlue, -0.58);
  backyardPoolWater = addFloorTile("backyard pool animated water", x, z, 9.65, 6.15, materials.poolWater, 0.12);
  backyardPoolWater.material.depthWrite = false;
  backyardPoolWater.material.polygonOffset = true;
  backyardPoolWater.material.polygonOffsetFactor = -2;
  backyardPoolWater.material.polygonOffsetUnits = -2;
  backyardPoolWater.renderOrder = 2;
  backyardPoolWater.userData.baseY = 0.12;
  addBox("backyard pool ladder left rail", -4.65, 0.32, z + 2.3, 0.05, 0.8, 0.05, materials.handle, false);
  addBox("backyard pool ladder right rail", -4.25, 0.32, z + 2.3, 0.05, 0.8, 0.05, materials.handle, false);
  for (const rungY of [0.1, -0.1, -0.3]) addBox("backyard pool ladder rung", -4.45, rungY, z + 2.3, 0.42, 0.035, 0.045, materials.handle, false);
  addBox("backyard diving board base", x + 3.4, 0.18, z - 4.25, 0.75, 0.36, 0.95, materials.sidewalk, true);
  addBox("backyard diving board", x + 3.4, 0.48, z - 3.2, 0.72, 0.12, 2.25, materials.fixture, false);
  addBox("backyard pool deep end marker", x + 4.35, 0.05, z - 3.85, 0.9, 0.04, 0.08, materials.line, false);

  backyardPoolSplash = new THREE.Group();
  backyardPoolSplash.name = "backyard pool splash placeholder";
  backyardPoolSplash.visible = false;
  backyardPoolSplash.position.set(x + 3.4, 0.25, z - 2.15);
  for (let i = 0; i < 14; i++) {
    const drop = new THREE.Mesh(new THREE.SphereGeometry(0.045, 10, 6), materials.poolWater);
    const angle = (i / 14) * Math.PI * 2;
    const radius = 0.22 + (i % 4) * 0.12;
    drop.position.set(Math.cos(angle) * radius, 0.12 + (i % 5) * 0.06, Math.sin(angle) * radius);
    backyardPoolSplash.add(drop);
  }
  scene.add(backyardPoolSplash);

  interactZones.push({
    name: "backyard diving board",
    x: x + 3.4,
    z: z - 3.2,
    floor: 0,
    radius: 1.5,
    action: () => {
      if (backyardPoolSplash) {
        backyardPoolSplash.visible = true;
        backyardPoolSplash.userData.startedAt = clock.elapsedTime;
      }
      show("Pool splash test. Future pass needs swimming, real splash particles, wet clothes, and wet hair simulation.");
    },
  });
}

function addHouseShell() {
  addFloorTile("first floor slab", 0, 0, 16, 15.5, materials.floor, 0.04);
  addFloorTile("second floor west bedroom deck", -3.72, 0, 8.55, 15.5, materials.secondFloor, 3.22);
  addFloorTile("second floor east bedroom deck", 5.62, 0, 4.75, 15.5, materials.secondFloor, 3.22);
  addFloorTile("second floor front hall deck around stair opening", 1.9, 5.35, 2.7, 4.8, materials.secondFloor, 3.22);
  addFloorTile("second floor rear hall deck around stair opening", 1.9, -5.15, 2.7, 5.2, materials.secondFloor, 3.22);
  addFloorTile("second floor front hall runner", 0.5, 5.3, 4.9, 4.45, materials.pathGravel, 3.265);
  addFloorTile("second floor rear hall runner", 0.5, -5.28, 4.9, 4.9, materials.pathGravel, 3.265);
  addFloorTile("second floor stair landing inlaid floor", 1.9, -1.45, 2.25, 1.8, materials.secondFloor, 3.275);
  addBox("open stairwell left floor edge trim", 0.55, 3.31, 0.2, 0.08, 0.12, 5.45, materials.trim, false, 1);
  addBox("open stairwell right floor edge trim", 3.25, 3.31, 0.2, 0.08, 0.12, 5.45, materials.trim, false, 1);
  addBox("open stairwell front floor edge trim", 1.9, 3.31, 2.94, 2.78, 0.12, 0.08, materials.trim, false, 1);
  addBox("open stairwell rear floor edge trim", 1.9, 3.31, -2.52, 2.78, 0.12, 0.08, materials.trim, false, 1);
  addFrontWallSegmented("first front west", -8, -1.22, 1.6, 3.2, [
    { x: -5.7, y: 1.55, width: 1.05, height: 1.2 },
    { x: -2.4, y: 1.55, width: 1.05, height: 1.2 },
  ], 0);
  addFrontWallSegmented("first front east", 1.22, 8, 1.6, 3.2, [
    { x: 2.4, y: 1.55, width: 1.05, height: 1.2 },
    { x: 5.7, y: 1.55, width: 1.05, height: 1.2 },
  ], 0);
  colliders.push({ x: -4.6, z: 7.75, sx: 6.8, sz: 0.35, floor: 0 });
  colliders.push({ x: 4.6, z: 7.75, sx: 6.8, sz: 0.35, floor: 0 });

  addBox("front entry threshold", 0, 0.09, 8.18, 2.45, 0.18, 0.62, materials.sidewalk, false);
  addBox("front entry top beam", 0, 3.04, 7.79, 2.5, 0.24, 0.28, materials.exterior, false);
  addBox("front door left trim", -1.08, 1.55, 8.02, 0.12, 2.85, 0.12, materials.windowFrame, false);
  addBox("front door right trim", 1.08, 1.55, 8.02, 0.12, 2.85, 0.12, materials.windowFrame, false);
  addBox("front door top trim", 0, 2.98, 8.02, 2.28, 0.12, 0.12, materials.windowFrame, false);
  addBox("front entry transom glass", 0, 2.6, 8.03, 1.9, 0.62, 0.035, materials.transomGlass, false);
  addBox("front story belt trim", 0, 3.18, 8.02, 16.2, 0.12, 0.1, materials.windowFrame, false);
  frontDoorLeft = createFrontDoorLeaf("front door left", -1);
  frontDoorRight = createFrontDoorLeaf("front door right", 1);
  frontDoorLeftClosed = frontDoorLeft.position.clone();
  frontDoorRightClosed = frontDoorRight.position.clone();
  doorColliders.push({ x: 0, z: 7.95, sx: 2.05, sz: 0.35, floor: 0, active: () => !frontDoorOpen });
  addBackWallSegmented("first back", -8, 8, 1.6, 3.2, [
    { x: -1.9, y: 1.55, width: 1.05, height: 1.2 },
    { x: 1.9, y: 1.25, width: 1.15, height: 2.2, type: "door" },
    { x: 5.4, y: 1.55, width: 1.05, height: 1.2 },
  ], 0);
  addSideWallSegmented("first left", -1, -7.75, 7.75, 1.6, 3.2, [
    { z: -1.8, y: 1.55, width: 1.05, height: 1.2 },
    { z: 1.8, y: 1.55, width: 1.05, height: 1.2 },
    { z: 5.0, y: 1.55, width: 1.05, height: 1.2 },
  ], 0);
  addSideWallSegmented("first right", 1, -7.75, 7.75, 1.6, 3.2, [
    { z: -5.0, y: 1.55, width: 1.05, height: 1.2 },
    { z: -1.8, y: 1.55, width: 1.05, height: 1.2 },
    { z: 1.8, y: 1.55, width: 1.05, height: 1.2 },
    { z: 5.0, y: 1.55, width: 1.05, height: 1.2 },
  ], 0);
  colliders.push({ x: -3.65, z: -7.75, sx: 8.1, sz: 0.35, floor: 0 });
  colliders.push({ x: 5.4, z: -7.75, sx: 5.2, sz: 0.35, floor: 0 });
  doorColliders.push({ x: 1.9, z: -7.75, sx: 1.25, sz: 0.35, floor: 0, active: () => !backDoorOpen });
  colliders.push({ x: -8, z: 0, sx: 0.35, sz: 15.5, floor: 0 });
  colliders.push({ x: 8, z: 0, sx: 0.35, sz: 15.5, floor: 0 });

  addFrontWallSegmented("second front west", -8, -1.22, 4.6, 2.75, [
    { x: -5.7, y: 4.65, width: 1.05, height: 1.2 },
    { x: -2.4, y: 4.65, width: 1.05, height: 1.2 },
  ], 1);
  addFrontWallSegmented("second front east", 1.22, 8, 4.6, 2.75, [
    { x: 2.4, y: 4.65, width: 1.05, height: 1.2 },
    { x: 5.7, y: 4.65, width: 1.05, height: 1.2 },
  ], 1);
  addBox("second front center lower panel", 0, 3.92, 7.75, 2.44, 1.15, 0.22, materials.exterior, false);
  addBox("second front center upper panel", 0, 5.45, 7.75, 2.44, 1.04, 0.22, materials.exterior, false);
  addBox("second front center left pier", -1.15, 4.6, 7.75, 0.18, 2.75, 0.24, materials.exterior, false);
  addBox("second front center right pier", 1.15, 4.6, 7.75, 0.18, 2.75, 0.24, materials.exterior, false);
  addFrontWindowOpening("second front center stair window", 0, 4.75, 1.25, 1.25, 1);
  colliders.push({ x: -4.6, z: 7.75, sx: 6.8, sz: 0.35, floor: 1 });
  colliders.push({ x: 4.6, z: 7.75, sx: 6.8, sz: 0.35, floor: 1 });
  colliders.push({ x: 0, z: 7.75, sx: 2.3, sz: 0.35, floor: 1 });
  addBackWallSegmented("second back", -8, 8, 4.6, 2.75, [
    { x: -5.4, y: 4.65, width: 1.05, height: 1.2 },
    { x: -1.9, y: 4.65, width: 1.05, height: 1.2 },
    { x: 1.9, y: 4.65, width: 1.05, height: 1.2 },
    { x: 5.4, y: 4.65, width: 1.05, height: 1.2 },
  ], 1);
  addSideWallSegmented("second left", -1, -7.75, 7.75, 4.6, 2.75, [
    { z: -5.0, y: 4.65, width: 1.05, height: 1.2 },
    { z: -1.8, y: 4.65, width: 1.05, height: 1.2 },
    { z: 1.8, y: 4.65, width: 1.05, height: 1.2 },
    { z: 5.0, y: 4.65, width: 1.05, height: 1.2 },
  ], 1);
  addSideWallSegmented("second right", 1, -7.75, 7.75, 4.6, 2.75, [
    { z: -5.0, y: 4.65, width: 1.05, height: 1.2 },
    { z: -1.8, y: 4.65, width: 1.05, height: 1.2 },
    { z: 1.8, y: 4.65, width: 1.05, height: 1.2 },
    { z: 5.0, y: 4.65, width: 1.05, height: 1.2 },
  ], 1);
  colliders.push({ x: 0, z: -7.75, sx: 16, sz: 0.35, floor: 1 });
  colliders.push({ x: -8, z: 0, sx: 0.35, sz: 15.5, floor: 1 });
  colliders.push({ x: 8, z: 0, sx: 0.35, sz: 15.5, floor: 1 });
  addBox("roof", 0, 6.15, 0, 17.2, 0.35, 16.7, materials.trim, false);

}

function addFixtures() {
  addBox("kitchen left prep base cabinet", -6.2, 0.55, -6.65, 0.82, 0.86, 0.52, materials.warmCabinet, true, 0);
  addBox("kitchen sink base cabinet", -5.08, 0.55, -6.65, 1.18, 0.86, 0.52, materials.warmCabinet, true, 0);
  addBox("kitchen right drawer base cabinet", -4.28, 0.55, -6.65, 0.58, 0.86, 0.52, materials.warmCabinet, true, 0);
  addBox("kitchen continuous countertop clear of fridge", -5.22, 1.02, -6.65, 2.58, 0.1, 0.6, materials.counter, false, 0);
  addBox("kitchen counter front rounded lip", -5.22, 1.08, -6.34, 2.66, 0.08, 0.075, materials.livingWood, false, 0);
  addBox("kitchen base cabinet continuous toe kick", -5.22, 0.18, -6.36, 2.48, 0.12, 0.07, materials.trim, false, 0);
  addBox("kitchen prep cabinet recessed front panel", -6.2, 0.54, -6.36, 0.52, 0.46, 0.04, materials.wood, false, 0);
  addBox("kitchen sink cabinet double left panel", -5.32, 0.54, -6.36, 0.42, 0.46, 0.04, materials.wood, false, 0);
  addBox("kitchen sink cabinet double right panel", -4.84, 0.54, -6.36, 0.42, 0.46, 0.04, materials.wood, false, 0);
  addBox("kitchen right drawer front upper", -4.28, 0.72, -6.36, 0.42, 0.18, 0.04, materials.wood, false, 0);
  addBox("kitchen right drawer front lower", -4.28, 0.44, -6.36, 0.42, 0.18, 0.04, materials.wood, false, 0);
  addBox("kitchen island cabinet body", -4.2, 0.5, -4.2, 2.05, 0.78, 0.9, materials.warmCabinet, true, 0);
  addBox("kitchen island recessed left panel", -4.72, 0.52, -3.74, 0.54, 0.42, 0.045, materials.wood, false, 0);
  addBox("kitchen island recessed right panel", -3.68, 0.52, -3.74, 0.54, 0.42, 0.045, materials.wood, false, 0);
  addBox("kitchen island toe kick shadow", -4.2, 0.16, -3.74, 1.82, 0.1, 0.06, materials.trim, false, 0);
  addKitchenDetails();

  addColliderOnly(-5.15, 3.02, 3.38, 1.36, 0);
  loadRealisticLivingRoomSofa();
  addBox("living room couch-facing tv console", -5.15, 0.42, 0.62, 2.7, 0.5, 0.36, materials.counter, true, 0);
  addBox("living room couch-facing big screen tv", -5.15, 1.32, 0.42, 2.35, 1.16, 0.08, materials.screen, true, 0);
  addBox("living room tv rear stand", -5.15, 0.84, 0.54, 0.18, 0.62, 0.1, materials.trim, true, 0);
  addBox("living room tv base", -5.15, 0.55, 0.62, 0.72, 0.08, 0.26, materials.trim, true, 0);
  addLivingRoomDecor();
  addHomeBookshelf();
  loadRealisticHomeBookshelf();

  addEnclosedDownstairsPowderRoom();
  addDiningRoom();

  addUpstairsSharedBathroom();

  addBed("empty upstairs guest room queen", -5.45, 5.72, 1.95, 2.18, 1, materials.blanketBlue, "front");
  addBedroomDetails("empty upstairs guest room", -5.45, 5.2, 1, materials.blanketBlue);
  addWallCloset("empty upstairs guest room fitted wall closet", -5.55, 7.32, 1, 2.35, "back", materials.blanketBlue);

  addBed("lisa queen", 5.85, 5.72, 1.95, 2.18, 1, materials.blanketPink, "front");
  addBedroomDetails("lisa bedroom", 5.85, 5.2, 1, materials.blanketPink);
  addWallCloset("lisa fitted wall closet", 5.65, 7.32, 1, 2.35, "back", materials.blanketPink);

  addBed("peter parker temporary twin", -5.62, 0.18, 1.25, 1.95, 1, materials.produceGreen, "front");
  addBedroomDetails("peter parker temporary bedroom", -5.62, -0.12, 1, materials.produceGreen);
  addWallDeskComputer("peter parker temporary photo science desk", -6.25, -1.72, 1);
  addPeterTemporaryWorkspaceProps();
  addWallCloset("peter parker temporary closet", -5.55, 2.35, 1, 1.85, "back", materials.produceGreen);

  addBed("gwen stacy temporary queen", -5.75, -5.75, 1.95, 2.18, 1, materials.blanketBlue, "back");
  addBedroomDetails("gwen stacy temporary bedroom", -5.75, -5.25, 1, materials.blanketBlue);
  addGwenUpstairsBedroomProps();
  addWallCloset("gwen stacy temporary wall closet", -5.75, -7.32, 1, 2.35, "front", materials.blanketBlue);

  addBed("marinette temporary full bed", 5.85, -5.9, 1.45, 1.95, 1, materials.blanketPink, "back");
  addBedroomDetails("marinette temporary bedroom", 5.85, -5.35, 1, materials.blanketPink);
  addWalkInCloset("marinette temporary walk in closet", 3.95, -7.15, 1, materials.blanketPink);
  addSideWallDeskComputer("marinette temporary workbench", 7.45, -4.35, 1, "right");
  addMarinetteDesignWorkbenchProps();
  addMarinetteWardrobePrototypeProps();
  addBox("ladybug fabric roll", 7.35, 3.55, -4.55, 0.18, 0.18, 0.82, materials.blanketPink, false);
  addBox("ladybug sketch box", 7.2, 3.48, -4.1, 0.52, 0.22, 0.34, materials.counter, false);
  addWallSketches();
  addMarinettePurseSet();
  interactZones.push({
    name: "marinette temporary workbench computer",
    x: 7.45,
    z: -4.35,
    floor: 1,
    radius: 1.05,
    action: () => show("This computer is a physical workstation placeholder. Search, videos, and library books are planned for the connected library/browser pass."),
  });
  removeSuppressedDownstairsToiletObjects();
}

function addInteriorWalls() {
  const wallMat = materials.wall;
  // First floor partitions.
  addBox("first hall wall rear left of stair", 0, 1.58, -5.45, 0.14, 3.05, 0.65, wallMat, true, 0);
  addBox("first rear divider left", -5.0, 1.58, -1.0, 6.0, 3.05, 0.14, wallMat, true, 0);
  addBox("first study divider front", 5.2, 1.58, 2.0, 5.6, 3.05, 0.14, wallMat, true, 0);

  addRoomLabel("COMMON ROOM", -4.1, 3.8, 0);
  addRoomLabel("FOYER", 0, 5.6, 0);
  addRoomLabel("STUDY", 4.1, 3.8, 0);
  addRoomLabel("KITCHEN / DINING", -4.1, -4.6, 0);
  addRoomLabel("UTILITY", 4.5, -5.5, 0);

  // Second floor: one central hallway, five bedrooms, and a middle shared bath.
  addBox("second stairwell front handrail", 0.75, 4.05, 2.35, 1.7, 0.08, 0.08, materials.trim, false, 1);
  addBox("second stairwell rear handrail", 0.75, 4.05, -2.25, 1.7, 0.08, 0.08, materials.trim, false, 1);
  addBox("second stairwell left handrail", -0.25, 4.05, 0.05, 0.08, 0.08, 4.45, materials.trim, false, 1);
  for (const [x, z] of [
    [-0.25, -2.25], [-0.25, -0.85], [-0.25, 0.75], [-0.25, 2.35],
    [0.05, 2.35], [0.75, 2.35], [1.45, 2.35],
    [0.05, -2.25], [0.75, -2.25], [1.45, -2.25],
  ]) {
    addBox("second stairwell rail post", x, 3.64, z, 0.08, 0.9, 0.08, materials.trim, false, 1);
  }

  addZWallWithGaps("second west hall bedroom wall", -2.25, -7.75, 7.75, [
    { center: -5.25, width: 1.35 },
    { center: 0.05, width: 1.25 },
    { center: 5.25, width: 1.35 },
  ], 4.6, 2.6, wallMat, 1);
  addZWallWithGaps("second east hall room wall", 3.25, -7.75, 7.75, [
    { center: -5.25, width: 1.35 },
    { center: 5.25, width: 1.35 },
  ], 4.6, 2.6, wallMat, 1);
  addXWallWithGaps("second west kira future guest divider", 2.75, -8, -2.25, [], 4.6, 2.6, wallMat, 1);
  addXWallWithGaps("second west future guest robert divider", -2.75, -8, -2.25, [], 4.6, 2.6, wallMat, 1);
  addXWallWithGaps("second east lisa bath divider", 2.75, 3.25, 8, [{ center: 5.65, width: 1.15 }], 4.6, 2.6, wallMat, 1);
  addXWallWithGaps("second east bath ladybug divider", -2.75, 3.25, 8, [{ center: 5.65, width: 1.15 }], 4.6, 2.6, wallMat, 1);
  addBox("second hall linen closet back", 0.42, 4.6, 7.18, 1.25, 2.3, 0.12, materials.wood, true, 1);
  addBox("second hall linen closet left return", -0.22, 4.6, 6.82, 0.1, 2.3, 0.72, materials.wood, true, 1);
  addBox("second hall linen closet right return", 1.06, 4.6, 6.82, 0.1, 2.3, 0.72, materials.wood, true, 1);
  addBox("second hall linen closet shelves", 0.42, 4.18, 6.8, 1.0, 0.08, 0.42, materials.counter, false, 1);
  addBox("second hall linen folded towels", 0.12, 4.3, 6.8, 0.38, 0.16, 0.28, materials.curtain, false, 1);

  for (const door of [
    ["empty upstairs guest room doorway trim", -2.25, 5.25, 1.35],
    ["peter parker temporary room doorway trim", -2.25, 0.05, 1.25],
    ["gwen stacy temporary room doorway trim", -2.25, -5.25, 1.35],
    ["lisa bedroom doorway trim", 3.25, 5.25, 1.35],
    ["marinette temporary room doorway trim", 3.25, -5.25, 1.35],
  ]) {
    addZWallDoorTrim(door[0], door[1], door[2], door[3], 1);
    addFloorThreshold(door[0].replace(" trim", " threshold"), door[1], door[2], 0.36, door[3] * 0.86, 1);
  }
  createZWallInteriorDoor("empty upstairs guest room hinged door", -2.25, 5.25, 1.28, 1, -1, "empty upstairs guest room door");
  createZWallInteriorDoor("peter parker temporary room hinged door", -2.25, 0.05, 1.18, 1, -1, "Peter Parker temporary room door");
  createZWallInteriorDoor("gwen stacy temporary room hinged door", -2.25, -5.25, 1.28, 1, -1, "Gwen Stacy temporary room door");
  createZWallInteriorDoor("lisa bedroom hinged door", 3.25, 5.25, 1.28, 1, 1, "Lisa bedroom door");
  createZWallInteriorDoor("marinette temporary room hinged door", 3.25, -5.25, 1.28, 1, 1, "Marinette temporary room door");
  addXWallDoorTrim("lisa private bath door trim", 2.75, 5.65, 1.15, 1);
  addXWallDoorTrim("ladybug private bath door trim", -2.75, 5.65, 1.15, 1);

  addRoomLabel("EMPTY ROOM", -5.4, 5.25, 1);
  addRoomLabel("LISA BEDROOM", 5.65, 5.25, 1);
  addRoomLabel("PETER PARKER TEMP", -5.45, 0.15, 1);
  addRoomLabel("GWEN STACY TEMP", -5.35, -5.25, 1);
  addRoomLabel("MARINETTE TEMP", 5.85, -5.25, 1);
  addRoomLabel("SHARED BATH", 5.75, 0.4, 1);
}

function addStairCore() {
  addBox("stair left handrail", 0.95, 1.72, 0.8, 0.08, 0.08, 4.9, materials.trim, false);
  addBox("stair right handrail", 2.85, 1.72, 0.8, 0.08, 0.08, 4.9, materials.trim, false);
  for (let i = 0; i < 6; i++) {
    const t = i / 5;
    const y = 0.58 + t * 2.25;
    const z = 2.65 - t * 3.95;
    addBox("stair left rail post", 0.95, y, z, 0.08, 0.72, 0.08, materials.trim, false);
    addBox("stair right rail post", 2.85, y, z, 0.08, 0.72, 0.08, materials.trim, false);
  }
  addBox("stair upper landing slab", 1.9, 3.28, -1.48, 2.25, 0.14, 1.72, materials.secondFloor, false);
  addBox("under stair side safety wall", 3.16, 1.28, 0.25, 0.16, 2.42, 3.45, materials.wall, true, 0);
  addBox("under stair rear safety wall", 2.34, 1.28, -1.58, 1.64, 2.42, 0.16, materials.wall, true, 0);
  addBox("under stair storage door hint", 2.34, 1.0, -1.48, 0.62, 1.48, 0.055, materials.wood, false, 0);
  addBox("under stair storage small handle", 2.64, 1.0, -1.42, 0.055, 0.16, 0.05, materials.handle, false, 0);
  addBox("upstairs stairwell left landing handrail", 0.85, 4.06, -1.25, 0.08, 0.08, 2.0, materials.trim, false);
  addBox("upstairs stairwell right landing handrail", 2.95, 4.06, -1.25, 0.08, 0.08, 2.0, materials.trim, false);
  addBox("upstairs landing left return handrail", 1.0, 4.06, -2.25, 0.38, 0.08, 0.08, materials.trim, false);
  addBox("upstairs landing right return handrail", 2.8, 4.06, -2.25, 0.38, 0.08, 0.08, materials.trim, false);
  for (const [x, z] of [
    [0.85, -2.18], [0.85, -1.25], [0.85, -0.32],
    [2.95, -2.18], [2.95, -1.25], [2.95, -0.32],
  ]) {
    addBox("upstairs landing rail grounded post", x, 3.64, z, 0.08, 0.9, 0.08, materials.trim, false, 1);
  }
  for (let i = 0; i < 16; i++) {
    const t = i / 15;
    addBox("solid stair tread", 1.9, 0.18 + t * 2.85, 2.95 - t * 4.55, 1.62, 0.11, 0.34, materials.trim, false);
    addBox("stair beige riser fill", 1.9, 0.09 + t * 2.85, 2.83 - t * 4.55, 1.55, 0.15, 0.055, materials.floor, false);
  }
  interactZones.push({
    name: "stairs bottom",
    x: 1.9,
    z: 2.86,
    floor: 0,
    radius: 0.82,
    action: () => show("Walk up the stair treads; the floor height now follows your movement instead of teleporting."),
  });
  interactZones.push({
    name: "stairs upstairs landing",
    x: 2.55,
    z: -1.95,
    floor: 1,
    radius: 0.9,
    action: () => show("Walk down the stair treads; the old instant floor jump is disabled."),
  });
}

function addDoorLeafToScene(name, x, z, width = 1.18, height = 2.32) {
  const group = new THREE.Group();
  group.name = name;
  group.position.set(x - width * 0.5, 0, z);
  const panel = new THREE.Mesh(new THREE.BoxGeometry(width, height, 0.1), materials.door);
  panel.position.set(width * 0.5, height * 0.5, 0);
  panel.castShadow = true;
  panel.receiveShadow = true;
  group.add(panel);
  for (const side of [-1, 1]) {
    const handle = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.42, 0.07), materials.handle);
    handle.position.set(width * 0.78, 1.08, side * 0.08);
    group.add(handle);
  }
  addBox(`${name} left jamb`, x - width * 0.5 - 0.07, height * 0.5, z + 0.01, 0.1, height + 0.14, 0.16, materials.windowFrame, false);
  addBox(`${name} right jamb`, x + width * 0.5 + 0.07, height * 0.5, z + 0.01, 0.1, height + 0.14, 0.16, materials.windowFrame, false);
  addBox(`${name} header frame`, x, height + 0.08, z + 0.01, width + 0.26, 0.12, 0.16, materials.windowFrame, false);
  addBox(`${name} threshold`, x, 0.08, z + 0.06, width + 0.24, 0.14, 0.38, materials.sidewalk, false);
  scene.add(group);
  return group;
}

function addExpertDesk(label, x, z, width = 2.4) {
  addBox(`${label} expert desk`, x, 0.58, z, width, 0.22, 0.78, materials.counter, true);
  addBox(`${label} expert chair seat`, x, 0.42, z + 0.9, 0.72, 0.18, 0.62, materials.trim, false);
  addBox(`${label} expert chair back`, x, 0.88, z + 1.2, 0.76, 0.72, 0.12, materials.trim, false);
  addBox(`${label} computer monitor`, x, 1.08, z - 0.32, 1.0, 0.62, 0.06, materials.screen, false);
  addBox(`${label} keyboard`, x, 0.74, z + 0.1, 0.72, 0.04, 0.22, materials.trim, false);
  addBox(`${label} wall briefing screen`, x, 1.85, z - 2.6, width * 0.9, 1.1, 0.06, materials.screen, false);
}

function toggleStripMallDoor(key, label) {
  const isOpen = !stripMallDoorOpen.get(key);
  stripMallDoorOpen.set(key, isOpen);
  const leaf = stripMallDoorLeaves.get(key);
  if (leaf) leaf.rotation.y = isOpen ? -Math.PI / 2 : 0;
  show(isOpen ? `${label} door open.` : `${label} door closed.`);
}

function addStripMall() {
  const sceneMeshCount = () => {
    let count = 0;
    scene.traverse((node) => {
      if (node.isMesh) count += 1;
    });
    return count;
  };
  const before = {
    meshes: sceneMeshCount(),
    colliders: colliders.length,
    doorColliders: doorColliders.length,
    interactionZones: interactZones.length,
  };
  addFloorTile("strip mall foundation", 0, 35, 32, 8, materials.sidewalk, 0.04);
  addBox("strip mall roof", 0, 3.35, 35, 31, 0.35, 6.8, materials.trim, false);
  addBox("strip mall back wall", 0, 1.62, 38.02, 30, 3.15, 0.18, materials.mall, true);
  addBox("strip mall left side wall", -15.05, 1.62, 35.0, 0.18, 3.15, 6, materials.mall, true);
  addBox("strip mall right side wall", 15.05, 1.62, 35.0, 0.18, 3.15, 6, materials.mall, true);

  const units = [
    { key: "law", label: "LAW OFFICE", x: -12 },
    { key: "pr", label: "PUBLIC RELATIONS FIRM", x: -6 },
    { key: "spa", label: "AI BODY SPA", x: 0 },
    { key: "programming", label: "PROGRAMMING / AI LAB", x: 6 },
    { key: "robotics", label: "ROBOTICS WORKSHOP", x: 12 },
  ];

  for (const dividerX of [-9, -3, 3, 9]) {
    addBox("strip mall partition wall", dividerX, 1.5, 35.0, 0.14, 2.85, 5.8, materials.mall, true);
    addBox("strip mall front divider cover", dividerX, 1.55, 31.89, 0.22, 2.95, 0.22, materials.mallFront, false);
  }
  for (const unit of units) {
    const { key, label, x } = unit;
    addFloorTile(`${label} office floor`, x, 35, 5.7, 5.8, materials.floor, 0.055);
    addBox(`${label} front wall left`, x - 1.82, 1.55, 31.98, 1.35, 2.9, 0.16, materials.mall, true);
    addBox(`${label} front wall right`, x + 1.82, 1.55, 31.98, 1.35, 2.9, 0.16, materials.mall, true);
    addBox(`${label} front header`, x, 2.72, 31.98, 2.1, 0.52, 0.16, materials.mall, true);
    addBox(`${label} display glass left`, x - 1.55, 1.35, 31.82, 1.45, 2.2, 0.06, materials.glass, false);
    addBox(`${label} display glass right`, x + 1.55, 1.35, 31.82, 1.45, 2.2, 0.06, materials.glass, false);
    const door = addDoorLeafToScene(`${label} working front door`, x, 31.78, 1.18, 2.32);
    stripMallDoorLeaves.set(key, door);
    stripMallDoorOpen.set(key, false);
    doorColliders.push({ x, z: 31.78, sx: 1.1, sz: 0.32, floor: null, active: () => !stripMallDoorOpen.get(key) });
    addBox(`${label} awning`, x, 2.85, 31.65, 4.8, 0.25, 0.65, materials.trim, false);
    addStorefrontSign(label, x, 3.55, 31.35, label.length > 16 ? 4.6 : 3.3);
    addExpertDesk(label, x, 34.7, key === "spa" ? 1.9 : 2.5);
    interactZones.push({ name: `${label} front door`, x, z: 31.7, radius: 1.35, action: () => toggleStripMallDoor(key, label) });
  }
  addSpaSuite();
  const after = {
    meshes: sceneMeshCount(),
    colliders: colliders.length,
    doorColliders: doorColliders.length,
    interactionZones: interactZones.length,
  };
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    legacyStripMall: {
      ...homeWorldActivityStatus.legacyStripMall,
      enabled: true,
      loaded: true,
      mode: "legacy_opt_in",
      sourceDeleted: false,
      spaPlacedHere: false,
      constructedDelta: {
        meshes: after.meshes - before.meshes,
        colliders: after.colliders - before.colliders,
        doorColliders: after.doorColliders - before.doorColliders,
        interactionZones: after.interactionZones - before.interactionZones,
      },
    },
  };
}

function setLibraryDoorOpen(open) {
  libraryDoorOpen = !!open;
  if (libraryDoorLeaf) libraryDoorLeaf.rotation.y = libraryDoorOpen ? -Math.PI / 2 : 0;
}

function nextLibraryCatalogItem(kind = "book") {
  const matching = PUBLIC_LIBRARY_CATALOG.filter((item) => item.kind === kind);
  const source = matching.length ? matching : PUBLIC_LIBRARY_CATALOG;
  const item = source[libraryCatalogCursor % source.length];
  libraryCatalogCursor += 1;
  return item;
}

function addLibraryBookRow(label, x, z, count = 8, rotationY = 0) {
  const mats = [materials.bookRed, materials.bookBlue, materials.bookGreen, materials.bookGold];
  const group = new THREE.Group();
  group.name = label;
  group.position.set(x, 0, z);
  group.rotation.y = rotationY;
  for (let i = 0; i < count; i += 1) {
    const book = new THREE.Mesh(new THREE.BoxGeometry(0.13, 0.56 + (i % 3) * 0.05, 0.36), mats[i % mats.length]);
    book.name = `${label} book spine`;
    book.position.set(-0.46 + i * 0.14, 1.0, 0);
    book.castShadow = true;
    book.receiveShadow = true;
    group.add(book);
    const catalogItem = nextLibraryCatalogItem("book");
    markTruthProp(book, catalogItem.kind, catalogItem.title, 0, ["read_book", "borrow_media"]);
    book.userData.catalogSource = catalogItem.source;
  }
  scene.add(group);
  markTruthProp(group, "shelf", label, 0, ["browse_books", "borrow_media"]);
  return group;
}

function addPublicLibrary() {
  const cx = 24;
  const cz = 43.5;
  addFloorTile("public library foundation", cx, cz, 13.2, 11.2, materials.sidewalk, 0.035);
  addFloorTile("public library carpet", cx, cz + 0.6, 10.8, 8.6, materials.libraryCarpet, 0.075);
  addFloorTile("public library entry mat", cx, cz - 4.28, 2.6, 1.0, materials.rugWarm, 0.09);
  addBox("public library rear wall", cx, 1.62, cz + 4.95, 12.2, 3.0, 0.18, materials.libraryWall, true);
  addBox("public library left wall", cx - 6.1, 1.62, cz + 0.35, 0.18, 3.0, 9.4, materials.libraryWall, true);
  addBox("public library right wall", cx + 6.1, 1.62, cz + 0.35, 0.18, 3.0, 9.4, materials.libraryWall, true);
  addBox("public library front wall left", cx - 4.0, 1.62, cz - 4.75, 4.0, 3.0, 0.18, materials.libraryWall, true);
  addBox("public library front wall right", cx + 4.0, 1.62, cz - 4.75, 4.0, 3.0, 0.18, materials.libraryWall, true);
  addBox("public library front header", cx, 2.82, cz - 4.75, 3.65, 0.55, 0.18, materials.libraryWall, false);
  addBox("public library stone base trim front", cx, 0.24, cz - 4.88, 12.7, 0.26, 0.12, materials.libraryStone, false);
  addBox("public library stone base trim left", cx - 6.2, 0.24, cz + 0.35, 0.12, 0.26, 9.5, materials.libraryStone, false);
  addBox("public library stone base trim right", cx + 6.2, 0.24, cz + 0.35, 0.12, 0.26, 9.5, materials.libraryStone, false);
  addBox("public library roof", cx, 3.25, cz, 13.2, 0.28, 11.0, materials.libraryTrim, false);
  addBox("public library roof fascia front", cx, 3.02, cz - 5.62, 13.8, 0.38, 0.18, materials.libraryTrim, false);
  addBox("public library roof fascia rear", cx, 3.02, cz + 5.58, 13.8, 0.38, 0.18, materials.libraryTrim, false);
  for (const wx of [cx - 4.25, cx + 4.25]) {
    addBox("public library front display glass", wx, 1.62, cz - 4.88, 1.7, 1.45, 0.055, materials.glass, false);
    addBox("public library front display window frame vertical", wx - 0.88, 1.62, cz - 4.92, 0.07, 1.65, 0.08, materials.windowFrame, false);
    addBox("public library front display window frame vertical", wx + 0.88, 1.62, cz - 4.92, 0.07, 1.65, 0.08, materials.windowFrame, false);
    addBox("public library front display window frame horizontal", wx, 1.62, cz - 4.93, 1.82, 0.07, 0.08, materials.windowFrame, false);
    addBox("public library front display window sill", wx, 0.82, cz - 5.02, 2.0, 0.12, 0.26, materials.libraryStone, false);
  }
  addBox("public library side reading window", cx - 6.18, 1.62, cz + 1.8, 0.055, 1.45, 2.3, materials.glass, false);
  addBox("public library side reading window frame", cx - 6.23, 1.62, cz + 1.8, 0.08, 1.62, 2.5, materials.windowFrame, false);
  addBox("public library front awning", cx, 2.9, cz - 5.15, 5.5, 0.18, 0.55, materials.libraryTrim, false);
  addStorefrontSign("PUBLIC LIBRARY", cx, 3.55, cz - 5.35, 4.5);
  addBox("public library glass vestibule left", cx - 1.22, 1.46, cz - 4.9, 0.72, 1.92, 0.045, materials.glass, false);
  addBox("public library glass vestibule right", cx + 1.22, 1.46, cz - 4.9, 0.72, 1.92, 0.045, materials.glass, false);
  addBox("public library door transom glass", cx, 2.48, cz - 4.9, 1.78, 0.36, 0.045, materials.glass, false);
  libraryDoorLeaf = addDoorLeafToScene("public library working front door", cx, cz - 5.08, 1.72, 2.32);
  doorColliders.push({ x: cx, z: cz - 5.08, sx: 1.68, sz: 0.32, floor: null, active: () => !libraryDoorOpen });

  addBox("library checkout desk", cx + 3.6, 0.62, cz - 2.2, 2.7, 0.76, 0.72, materials.libraryWood, true);
  addBox("library checkout lower return bin", cx + 2.95, 0.32, cz - 1.7, 0.66, 0.34, 0.42, materials.mediaCase, false);
  markTruthProp(addBox("library checked out open book", cx + 3.55, 1.05, cz - 1.95, 0.72, 0.04, 0.48, materials.paper, false), "book", "The Story of Coding", 0, ["read_book"]);
  addBox("library librarian monitor", cx + 4.15, 1.18, cz - 2.22, 0.86, 0.52, 0.06, materials.screen, false);
  addBox("library self checkout kiosk", cx + 2.1, 0.85, cz - 3.55, 0.52, 1.3, 0.42, materials.brushedSteel, false);
  addBox("library self checkout touch screen", cx + 2.1, 1.35, cz - 3.78, 0.42, 0.32, 0.04, materials.screen, false);
  addBox("library reading table", cx - 1.95, 0.58, cz + 0.65, 2.6, 0.18, 1.35, materials.libraryWood, true);
  for (const [sx, sz, yaw] of [[-3.15, 0.85, Math.PI / 2], [-0.35, 0.85, -Math.PI / 2], [-1.75, -0.2, 0], [-1.75, 1.9, Math.PI]]) {
    addBox("library reading chair seat", cx + sx, 0.42, cz + sz, 0.58, 0.16, 0.58, materials.trim, true);
    addBox("library reading chair back", cx + sx + Math.sin(yaw) * 0.32, 0.82, cz + sz + Math.cos(yaw) * 0.32, 0.62, 0.72, 0.1, materials.trim, false);
  }
  markTruthProp(addBox("library table open book", cx - 2.2, 0.82, cz + 0.55, 0.72, 0.04, 0.5, materials.paper, false), "book", "Fashion Studies Guide", 0, ["read_book"]);
  markTruthProp(addBox("library table notebook", cx - 1.18, 0.84, cz + 0.88, 0.55, 0.05, 0.42, materials.notebookCover, false), "notebook", "library table notebook", 0, ["read_book", "sketch_design"]);
  for (const [x, z] of [[cx + 0.95, cz + 0.45], [cx + 2.55, cz + 0.45]]) {
    addBox("library public computer desk", x, 0.58, z, 1.1, 0.18, 0.68, materials.libraryWood, true);
    addBox("library public computer monitor", x, 1.08, z - 0.22, 0.72, 0.44, 0.06, materials.screen, false);
    addBox("library public computer keyboard", x, 0.74, z + 0.08, 0.55, 0.035, 0.18, materials.trim, false);
    addBox("library computer chair seat", x, 0.4, z + 0.78, 0.55, 0.14, 0.52, materials.trim, true);
    addBox("library computer chair back", x, 0.82, z + 1.02, 0.58, 0.62, 0.1, materials.trim, false);
  }
  addBox("library media shelf", cx + 4.9, 0.95, cz + 2.55, 0.6, 1.75, 3.1, materials.libraryWood, true);
  for (let i = 0; i < 12; i += 1) {
    const catalogItem = nextLibraryCatalogItem("media");
    const mediaCase = addBox("library movie and music media case", cx + 4.55, 0.55 + (i % 3) * 0.42, cz + 1.3 + Math.floor(i / 3) * 0.45, 0.08, 0.32, 0.28, i % 2 ? materials.mediaCase : materials.bookBlue, false);
    mediaCase.userData.catalogSource = catalogItem.source;
    markTruthProp(mediaCase, catalogItem.kind, catalogItem.title, 0, ["borrow_media"]);
  }
  for (const shelf of [
    ["library rear left shelf row", cx - 3.4, cz + 4.35, 9, 0],
    ["library rear middle shelf row", cx - 0.4, cz + 4.35, 9, 0],
    ["library rear right shelf row", cx + 2.6, cz + 4.35, 9, 0],
    ["library left wall shelf row", cx - 5.45, cz - 0.7, 7, Math.PI / 2],
    ["library left wall second shelf row", cx - 5.45, cz + 2.2, 7, Math.PI / 2],
    ["library right wall reference shelf row", cx + 5.45, cz + 3.0, 7, Math.PI / 2],
  ]) {
    addBox(`${shelf[0]} wood shelf`, shelf[1], 0.78, shelf[2], shelf[4] ? 0.56 : 1.65, 1.35, shelf[4] ? 1.65 : 0.56, materials.libraryWood, true);
    addLibraryBookRow(shelf[0], shelf[1], shelf[2] - (shelf[4] ? 0 : 0.28), shelf[3], shelf[4]);
  }
  addLabel("QUIET READING", cx - 1.95, 2.05, cz + 2.7, 2.0, { billboard: false, rotationY: 0 });
  addLabel("BOOKS + MEDIA", cx + 4.98, 2.05, cz + 0.65, 2.0, { billboard: false, rotationY: -Math.PI / 2 });
  addFloorTile("library grass reading blanket", cx - 3.9, cz + 8.2, 3.2, 2.1, materials.blanketBlue, 0.04);
  markTruthProp(addBox("library lawn paperback book", cx - 4.15, 0.1, cz + 8.1, 0.52, 0.045, 0.34, materials.paper, false), "book", "Alice's Adventures in Wonderland", 0, ["read_book"]);
  addFloorTile("library stone path to sidewalk", cx, 34.0, 2.2, 9.2, materials.pathGravel, 0.025);
  addBox("library exterior book return slot", cx + 2.0, 1.28, cz - 4.95, 0.62, 0.16, 0.08, materials.tardisDark, false);
  addBox("library exterior planter box", cx - 5.0, 0.3, cz - 5.45, 1.45, 0.4, 0.42, materials.libraryWood, false);
  addCylinder("library exterior planter shrub", cx - 5.34, 0.72, cz - 5.45, 0.22, 0.52, materials.plantLeaf, false);
  addCylinder("library exterior planter shrub", cx - 4.84, 0.72, cz - 5.45, 0.24, 0.56, materials.plantLeaf, false);
  addCylinder("library exterior planter shrub", cx - 4.38, 0.72, cz - 5.45, 0.2, 0.48, materials.plantLeaf, false);
  interactZones.push({
    name: "public library front door",
    x: cx,
    z: cz - 5.05,
    radius: 1.25,
    action: () => {
      setLibraryDoorOpen(!libraryDoorOpen);
      show(libraryDoorOpen ? "Public library door open." : "Public library door closed.");
    },
  });
  interactZones.push({
    name: "library reading table",
    x: cx - 1.75,
    z: cz + 0.85,
    radius: 1.55,
    action: () => show("Library reading table: books and notebooks are real truth props, so reading now needs a visible object nearby."),
  });
  interactZones.push({
    name: "library media shelves",
    x: cx + 4.6,
    z: cz + 2.4,
    radius: 1.25,
    action: () => show("Media shelf: visible cases are tagged to safe items from Data/library."),
  });
}

function addLocalBox(group, name, x, y, z, sx, sy, sz, material) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), material);
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
  return mesh;
}

function addLocalSignText(group, name, text, x, y, z, rotationY = 0, width = 1.34, height = 0.14) {
  const canvas = document.createElement("canvas");
  canvas.width = 768;
  canvas.height = 128;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#05070a";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#89d8ff";
  ctx.lineWidth = 6;
  ctx.strokeRect(8, 8, canvas.width - 16, canvas.height - 16);
  ctx.fillStyle = "#f3fbff";
  ctx.font = "bold 48px Segoe UI, Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2 + 2);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(width, height),
    new THREE.MeshBasicMaterial({ map: texture, transparent: true, side: THREE.DoubleSide })
  );
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.rotation.y = rotationY;
  group.add(mesh);
  return mesh;
}

function buildHomeTardisExterior(position = new THREE.Vector3(-12.8, 0, 12.4)) {
  if (homeTardisGroup) return homeTardisGroup;
  const group = new THREE.Group();
  group.name = "home world callable TARDIS exterior";
  group.position.copy(position);
  const interiorDark = new THREE.MeshStandardMaterial({ color: 0x020913, roughness: 0.86 });
  const consoleGlow = new THREE.MeshBasicMaterial({ color: 0x00a6ff });
  addLocalBox(group, "home TARDIS base", 0, 0.08, 0, 1.7, 0.16, 1.7, materials.tardisDark);
  addLocalBox(group, "home TARDIS main blue box", 0, 1.42, 0, 1.46, 2.68, 1.46, materials.tardisBlue);

  const addDoorFace = (z, interactive = false) => {
    for (const x of [-0.34, 0.34]) {
      const slab = addLocalBox(group, interactive ? "home TARDIS openable front door slab" : "home TARDIS rear door slab", x, 1.35, z, 0.58, 2.05, 0.08, materials.tardisBlue);
      if (interactive && x < 0) homeTardisLeftDoor = slab;
      if (interactive && x > 0) homeTardisRightDoor = slab;
      addLocalBox(group, "home TARDIS lit window", x, 2.18, z + Math.sign(z) * 0.055, 0.26, 0.38, 0.05, materials.tardisGlow);
      addLocalBox(group, "home TARDIS lower door inset", x, 0.82, z + Math.sign(z) * 0.055, 0.36, 0.34, 0.04, materials.tardisDark);
      addLocalBox(group, "home TARDIS middle door inset", x, 1.28, z + Math.sign(z) * 0.055, 0.36, 0.34, 0.04, materials.tardisDark);
      addLocalBox(group, "home TARDIS upper door inset", x, 1.72, z + Math.sign(z) * 0.055, 0.36, 0.34, 0.04, materials.tardisDark);
    }
    for (const x of [-0.78, 0.78]) addLocalBox(group, "home TARDIS front post", x, 1.48, z, 0.12, 2.8, 0.12, materials.tardisDark);
    addLocalBox(group, "home TARDIS police public call box sign", 0, 2.77, z + Math.sign(z) * 0.08, 1.52, 0.2, 0.05, materials.tardisDark);
    addLocalSignText(
      group,
      "home TARDIS readable police public call box sign",
      "POLICE  PUBLIC CALL  BOX",
      0,
      2.78,
      z + Math.sign(z) * 0.112,
      z > 0 ? 0 : Math.PI,
      1.34,
      0.13
    );
  };

  addDoorFace(0.82, true);
  addDoorFace(-0.82, false);

  homeTardisInteriorPreview = new THREE.Group();
  homeTardisInteriorPreview.name = "home TARDIS visible interior preview";
  homeTardisInteriorPreview.visible = false;
  homeTardisInteriorPreview.add(new THREE.Mesh(new THREE.BoxGeometry(0.96, 1.76, 0.06), interiorDark));
  homeTardisInteriorPreview.children[0].name = "home TARDIS dark interior opening";
  homeTardisInteriorPreview.children[0].position.set(0, 1.34, 0.91);
  const tinyConsole = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.34, 0.04), consoleGlow);
  tinyConsole.name = "home TARDIS visible world console glow";
  tinyConsole.position.set(0, 1.58, 0.96);
  homeTardisInteriorPreview.add(tinyConsole);
  const rotor = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.055, 1.05, 16), consoleGlow);
  rotor.name = "home TARDIS visible time rotor glow";
  rotor.position.set(0, 1.42, 0.99);
  homeTardisInteriorPreview.add(rotor);
  group.add(homeTardisInteriorPreview);

  for (const z of [-0.78, 0.78]) addLocalBox(group, "home TARDIS side sign rail", 0, 2.76, z, 1.62, 0.18, 0.08, materials.tardisDark);
  for (const x of [-0.86, 0.86]) {
    addLocalBox(group, "home TARDIS side police sign", x, 2.76, 0, 0.08, 0.18, 1.46, materials.tardisDark);
    addLocalBox(group, "home TARDIS side blue timber", x, 1.43, 0, 0.1, 2.65, 1.46, materials.tardisBlue);
    addLocalSignText(
      group,
      "home TARDIS readable side police public call box sign",
      "POLICE  PUBLIC CALL  BOX",
      x + Math.sign(x) * 0.052,
      2.78,
      0,
      Math.sign(x) > 0 ? Math.PI / 2 : -Math.PI / 2,
      1.22,
      0.13
    );
  }
  addLocalBox(group, "home TARDIS telephone notice", -0.42, 1.47, 0.9, 0.28, 0.42, 0.04, materials.paper);
  addLocalBox(group, "home TARDIS brass door handle", 0.1, 1.2, 0.94, 0.07, 0.07, 0.05, materials.brass || materials.handle);
  addLocalBox(group, "home TARDIS roof lower", 0, 2.88, 0, 1.82, 0.18, 1.82, materials.tardisDark);
  addLocalBox(group, "home TARDIS roof upper", 0, 3.08, 0, 1.35, 0.22, 1.35, materials.tardisDark);
  addLocalBox(group, "home TARDIS lamp glass", 0, 3.28, 0, 0.26, 0.24, 0.26, materials.tardisGlow);
  scene.add(group);
  homeTardisGroup = group;
  homeTardisCollider = { x: position.x, z: position.z, sx: 1.75, sz: 1.75, floor: 0 };
  colliders.push(homeTardisCollider);
  return group;
}

function setHomeTardisDoorOpen(open) {
  homeTardisDoorOpen = !!open;
  if (homeTardisLeftDoor) {
    homeTardisLeftDoor.rotation.y = homeTardisDoorOpen ? 1.18 : 0;
    homeTardisLeftDoor.position.set(homeTardisDoorOpen ? -0.64 : -0.34, 1.35, homeTardisDoorOpen ? 0.98 : 0.82);
  }
  if (homeTardisRightDoor) {
    homeTardisRightDoor.rotation.y = homeTardisDoorOpen ? -1.18 : 0;
    homeTardisRightDoor.position.set(homeTardisDoorOpen ? 0.64 : 0.34, 1.35, homeTardisDoorOpen ? 0.98 : 0.82);
  }
  if (homeTardisInteriorPreview) homeTardisInteriorPreview.visible = homeTardisDoorOpen;
  if (homeTardisGroup) {
    homeTardisGroup.traverse((node) => {
      if (!node.isMesh || node === homeTardisLeftDoor || node === homeTardisRightDoor) return;
      const name = node.name || "";
      const frontDetail = node.position?.z > 0.84 && (
        name.includes("lit window") ||
        name.includes("door inset") ||
        name.includes("telephone notice") ||
        name.includes("brass door handle")
      );
      if (frontDetail) node.visible = !homeTardisDoorOpen;
    });
  }
}

function moveHomeTardisTo(position, yaw = null) {
  buildHomeTardisExterior(position);
  homeTardisGroup.position.copy(position);
  if (Number.isFinite(yaw)) homeTardisGroup.rotation.y = yaw;
  setHomeTardisDoorOpen(false);
  if (homeTardisCollider) {
    homeTardisCollider.x = position.x;
    homeTardisCollider.z = position.z;
  }
}

function callHomeTardisToUser() {
  const forward = new THREE.Vector3(0, 0, -2.7).applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw);
  const target = new THREE.Vector3(
    THREE.MathUtils.clamp(player.position.x + forward.x, -32, 32),
    0,
    THREE.MathUtils.clamp(player.position.z + forward.z, -23, 54),
  );
  if (isBlocked(target.x, target.z)) {
    const fallbackSpots = [
      new THREE.Vector3(player.position.x + 2.4, 0, player.position.z),
      new THREE.Vector3(player.position.x - 2.4, 0, player.position.z),
      new THREE.Vector3(player.position.x, 0, player.position.z + 2.4),
      new THREE.Vector3(player.position.x, 0, player.position.z - 2.4),
      new THREE.Vector3(-12.8, 0, 12.4),
      new THREE.Vector3(13.8, 0, 35.6),
    ];
    const openSpot = fallbackSpots.find((spot) => !isBlocked(spot.x, spot.z));
    if (openSpot) target.copy(openSpot);
    else {
      show("TARDIS call failed: no clear landing spot nearby.");
      return false;
    }
  }
  const toPlayer = new THREE.Vector3(player.position.x - target.x, 0, player.position.z - target.z);
  const yaw = Math.atan2(toPlayer.x, toPlayer.z);
  moveHomeTardisTo(target, yaw);
  show("TARDIS call accepted in Home World. Walk to the front doors and press E to open them.");
  return true;
}

function homeTardisActiveAvatarLandingCandidates() {
  if (!activeMarker) return [];
  const base = activeMarker.position;
  const y = ACTIVE_AVATAR_GROUND_Y;
  const raw = [
    new THREE.Vector3(base.x, y, base.z + 2.8),
    new THREE.Vector3(base.x + 2.8, y, base.z),
    new THREE.Vector3(base.x - 2.8, y, base.z),
    new THREE.Vector3(base.x, y, base.z - 2.8),
    new THREE.Vector3(base.x + 4.0, y, base.z + 1.8),
    new THREE.Vector3(base.x - 4.0, y, base.z + 1.8),
    new THREE.Vector3(13.8, y, 35.6),
    new THREE.Vector3(-12.8, y, 12.4),
  ];
  return raw.map((spot) => new THREE.Vector3(
    THREE.MathUtils.clamp(spot.x, -32, 32),
    y,
    THREE.MathUtils.clamp(spot.z, -23, 54),
  ));
}

function homeTardisLandingSpotClearForActiveAvatar(spot) {
  if (!spot) return false;
  if (Math.hypot(spot.x - activeMarker.position.x, spot.z - activeMarker.position.z) < 1.85) return false;
  return !isAvatarBlocked(spot.x, spot.z, spot.y, 1.18);
}

function callHomeTardisToActiveAvatar() {
  if (!activeMarker) {
    show("TARDIS call failed: no active avatar body is available.");
    return false;
  }
  const target = homeTardisActiveAvatarLandingCandidates().find(homeTardisLandingSpotClearForActiveAvatar);
  if (!target) {
    recordMovementLearningAttempt({
      skill: "tardis_entry",
      phase: "active_avatar_call_failed_no_clear_landing",
      target: "TARDIS landing spot",
      actor: activeAvatarDisplayName(),
    });
    show(`${activeAvatarDisplayName()} tries to call the TARDIS, but no clear landing spot is available.`);
    return false;
  }
  const toAvatar = new THREE.Vector3(activeMarker.position.x - target.x, 0, activeMarker.position.z - target.z);
  const yaw = Math.atan2(toAvatar.x, toAvatar.z);
  moveHomeTardisTo(target, yaw);
  setActiveAvatarAction("walk");
  recordMovementLearningAttempt({
    skill: "tardis_entry",
    phase: "active_avatar_called_tardis",
    target: "TARDIS exterior",
    actor: activeAvatarDisplayName(),
    landing: {
      x: Number(target.x.toFixed(3)),
      z: Number(target.z.toFixed(3)),
    },
  });
  show(`${activeAvatarDisplayName()} calls the TARDIS to her current area.`);
  guideActiveAvatarToHomeTardisDoor(clock.elapsedTime, "active_avatar_called_tardis");
  return true;
}

function requestShellLocation(location, options = {}) {
  if (window.parent && window.parent !== window) {
    window.parent.postMessage({ type: "kira-shell-location", location, ...options }, "*");
    return true;
  }
  show(`The launcher shell is needed to move to ${location}.`);
  return false;
}

function tryEnterHomeTardis() {
  if (!homeTardisGroup || player.floor !== 0) return false;
  const local = new THREE.Vector3(
    player.position.x - homeTardisGroup.position.x,
    0,
    player.position.z - homeTardisGroup.position.z,
  ).applyAxisAngle(new THREE.Vector3(0, 1, 0), -homeTardisGroup.rotation.y);
  const nearBox = Math.abs(local.x) < 2.2 && Math.abs(local.z) < 2.5;
  if (!nearBox) return false;
  const atFrontDoors = Math.abs(local.x) < 1.25 && local.z > 0.62 && local.z < 2.35;
  if (!atFrontDoors) {
    show("The TARDIS is solid except at the front doors. Move around to the lit windows and handle.");
    return true;
  }
  if (!homeTardisDoorOpen) {
    setHomeTardisDoorOpen(true);
    show("The TARDIS doors open. The console is visible inside; walk through the doorway and press E.");
    return true;
  }
  if (local.z < 1.02) {
    show("The TARDIS interior is visible. Step through the open doorway first.");
    return true;
  }
  show("Stepping through the TARDIS doorway into the persistent gateway.");
  requestShellLocation("tardis", { returnLocation: "home", arrival: "tardis" });
  return true;
}

function homeTardisLocalFromWorld(position) {
  if (!homeTardisGroup || !position) return null;
  return new THREE.Vector3(
    position.x - homeTardisGroup.position.x,
    0,
    position.z - homeTardisGroup.position.z,
  ).applyAxisAngle(new THREE.Vector3(0, 1, 0), -homeTardisGroup.rotation.y);
}

function homeTardisDoorwayWorldPosition(localZ = 1.28) {
  if (!homeTardisGroup) return null;
  return new THREE.Vector3(0, ACTIVE_AVATAR_GROUND_Y, localZ)
    .applyAxisAngle(new THREE.Vector3(0, 1, 0), homeTardisGroup.rotation.y)
    .add(homeTardisGroup.position);
}

function activeAvatarHomeTardisStateSnapshot(position = activeMarker?.position) {
  const local = homeTardisLocalFromWorld(position);
  if (!local) return null;
  const near = Math.abs(local.x) < 2.4 && Math.abs(local.z) < 2.7;
  const atDoorway = Math.abs(local.x) < 0.82 && local.z > 0.55 && local.z < 1.85;
  const entered = homeTardisDoorOpen && Math.abs(local.x) < 0.62 && local.z > 1.02 && local.z < 1.7;
  return {
    near,
    atDoorway,
    entered,
    doorOpen: !!homeTardisDoorOpen,
    localX: Number(local.x.toFixed(3)),
    localZ: Number(local.z.toFixed(3)),
    worldX: Number(homeTardisGroup.position.x.toFixed(3)),
    worldZ: Number(homeTardisGroup.position.z.toFixed(3)),
  };
}

function guideActiveAvatarToHomeTardisDoor(t, reason = "tardis_side_contact") {
  if (!activeMarker || !homeTardisGroup) return false;
  const doorway = homeTardisDoorwayWorldPosition(1.34);
  if (!doorway) return false;
  activeMarker.userData.autonomousRoamTarget = {
    id: "TARDIS front doorway",
    reason,
    x: doorway.x,
    y: ACTIVE_AVATAR_GROUND_Y,
    z: doorway.z,
    pickedAt: t,
    attempt: 0,
  };
  activeMarker.userData.autonomousGaitMode = "walk";
  activeMarker.userData.roamPolicy = "tardis_doorway_guided_entry";
  activeMarker.userData.waitUntil = t + 0.08;
  faceActiveAvatarToward(doorway.x, doorway.z);
  show(`${activeAvatarDisplayName()} turns toward the TARDIS front doorway.`);
  recordMovementLearningAttempt({
    skill: "tardis_entry",
    phase: "guided_to_front_door",
    target: "TARDIS front doorway",
    reason,
  });
  return true;
}

function tryEnterHomeTardisForActiveAvatar(nextX, nextZ, y) {
  if (!activeMarker || !homeTardisGroup || y > 1.8) return false;
  const nextLocal = homeTardisLocalFromWorld({ x: nextX, z: nextZ });
  if (!nextLocal) return false;
  const nearShell = Math.abs(nextLocal.x) < 2.1 && Math.abs(nextLocal.z) < 2.25;
  if (!nearShell) return false;
  const atFrontDoors = Math.abs(nextLocal.x) < 0.92 && nextLocal.z > 0.55 && nextLocal.z < 1.95;
  if (!atFrontDoors) {
    if (nextLocal.z > -0.1) return guideActiveAvatarToHomeTardisDoor(clock.elapsedTime, "near_tardis_but_not_front_door");
    return false;
  }
  if (!homeTardisDoorOpen) {
    setHomeTardisDoorOpen(true);
    activeMarker.userData.waitUntil = clock.elapsedTime + 0.45;
    activeMarker.userData.isMoving = false;
    activeMarker.userData.walkSpeed = 0;
    show(`${activeAvatarDisplayName()} opens the TARDIS doors and looks inside.`);
    recordMovementLearningAttempt({
      skill: "tardis_entry",
      phase: "active_avatar_opened_doors",
      target: "TARDIS front doors",
    });
    return true;
  }
  const inside = homeTardisDoorwayWorldPosition(1.36);
  if (inside) {
    activeMarker.position.copy(inside);
    activeMarker.userData.lastSafePosition = inside.clone();
  }
  activeMarker.userData.tardisEntered = true;
  activeMarker.userData.waitUntil = clock.elapsedTime + 0.8;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  show(`${activeAvatarDisplayName()} steps through the TARDIS doorway.`);
  recordMovementLearningAttempt({
    skill: "tardis_entry",
    phase: "active_avatar_entered_tardis",
    target: "TARDIS interior",
  });
  requestShellLocation("tardis", {
    returnLocation: "home",
    arrival: "tardis",
    traveler: activeShellState?.active_candidate || "active_avatar",
  });
  return true;
}

function startActiveAvatarTardisEntryPractice() {
  if (!activeMarker) {
    show("TARDIS entry practice needs an active body.");
    return false;
  }
  activePostureInteraction = null;
  activeDoorInteraction = null;
  activeFurnitureInteraction = null;
  activeSkillInteraction = null;
  clearActiveAvatarAutonomousRoamTarget("tardis_entry_practice_started");
  const tardisState = activeAvatarHomeTardisStateSnapshot(activeMarker.position);
  if (!homeTardisGroup || !tardisState?.near) {
    return callHomeTardisToActiveAvatar();
  }
  setActiveAvatarAction("walk");
  recordMovementLearningAttempt({
    skill: "tardis_entry",
    phase: "active_avatar_entry_practice_started",
    target: "TARDIS front doorway",
    actor: activeAvatarDisplayName(),
    tardisState,
  });
  return guideActiveAvatarToHomeTardisDoor(clock.elapsedTime, "active_avatar_entry_practice_started");
}

function startActiveAvatarSoftGoodsDraftPractice(kind = "robe") {
  if (!activeMarker) {
    show("Soft-goods practice needs an active body.");
    return false;
  }
  const normalized = String(kind).toLowerCase().includes("towel") ? "towel" : "robe";
  const skill = normalized === "towel" ? "use_towel" : "put_on_robe";
  activeMarker.userData.softGoodsPractice = {
    kind: normalized,
    status: "blocked_missing_approved_cloth_prop",
    updatedAtSeconds: Number(clock.elapsedTime.toFixed(3)),
  };
  setActiveAvatarAction("idle");
  recordMovementLearningAttempt({
    skill,
    phase: "blocked_missing_approved_cloth_prop",
    target: normalized === "towel" ? "bath towel / hand towel" : "shared white bath robe",
    actor: activeAvatarDisplayName(),
    requiredBeforePass: [
      "approved cloth mesh",
      "hanger/folded/worn/wrapped state machine",
      "grab anchors",
      "body-fit collision",
      "visible proof clip",
    ],
  });
  show(`${activeAvatarDisplayName()} cannot physically use the ${normalized} yet: the approved cloth prop and state rig are still missing.`);
  return true;
}

function addSpaSuite() {
  addBox("spa reception counter", -0.65, 0.62, 33.0, 2.2, 0.78, 0.55, materials.counter, true);
  addBox("spa waiting bench", 1.6, 0.38, 32.8, 1.7, 0.34, 0.55, materials.spaAccent, true);
  addBox("spa avatar builder screen", -0.65, 1.72, 37.89, 2.35, 1.1, 0.05, materials.screen, false);
  addBox("spa treatment wall left", -1.95, 1.48, 36.2, 0.12, 2.65, 3.3, materials.spaWall, true);
  addBox("spa treatment wall right", 1.95, 1.48, 36.2, 0.12, 2.65, 3.3, materials.spaWall, true);
  addBox("spa treatment rear wall", 0, 1.48, 37.75, 3.9, 2.65, 0.12, materials.spaWall, true);
  addBox("spa scan platform", -0.8, 0.16, 35.95, 1.45, 0.18, 1.45, materials.spaAccent, false);
  addCylinder("spa scan ring", -0.8, 1.35, 35.95, 0.85, 0.05, materials.activeBlue, false);
  addBox("spa hair styling chair", 0.95, 0.48, 36.0, 0.7, 0.58, 0.7, materials.trim, false);
  addBox("spa privacy curtain", 1.78, 1.45, 36.0, 0.06, 2.2, 1.6, materials.blanketPink, false);
  interactZones.push({
    name: "AI Body Spa avatar builder",
    x: -0.4,
    z: 35.2,
    radius: 1.9,
    action: () => show("Avatar spa is connected to the body builder. Styling changes stay age-appropriate and permission-gated."),
  });
}

function addInteractLabels() {
  interactZones.push({
    name: "front door",
    x: 0,
    z: 8.2,
    floor: 0,
    radius: 1.6,
    action: () => {
      setFrontDoorOpen(!frontDoorOpen);
      show(frontDoorOpen ? "Front door open." : "Front door closed.");
    },
  });
  interactZones.push({
    name: "back door",
    x: 1.9,
    z: -7.75,
    floor: 0,
    radius: 1.45,
    action: () => {
      setBackDoorOpen(!backDoorOpen);
      show(backDoorOpen ? "Back door open." : "Back door closed.");
    },
  });
}

function isBlocked(nextX, nextZ) {
  for (const c of doorColliders) {
    if (c.floor !== null && c.floor !== player.floor) continue;
    if (c.active && !c.active()) continue;
    const dx = Math.abs(nextX - c.x);
    const dz = Math.abs(nextZ - c.z);
    if (dx < c.sx / 2 + player.radius && dz < c.sz / 2 + player.radius) return true;
  }
  for (const c of colliders) {
    if (c.floor !== null && c.floor !== player.floor) continue;
    if (c === homeTardisCollider && homeTardisDoorOpen && homeTardisGroup) {
      const local = new THREE.Vector3(nextX - homeTardisGroup.position.x, 0, nextZ - homeTardisGroup.position.z)
        .applyAxisAngle(new THREE.Vector3(0, 1, 0), -homeTardisGroup.rotation.y);
      if (Math.abs(local.x) < 0.66 && local.z > 0.62 && local.z < 1.58) continue;
    }
    const dx = Math.abs(nextX - c.x);
    const dz = Math.abs(nextZ - c.z);
    if (dx < c.sx / 2 + player.radius && dz < c.sz / 2 + player.radius) return true;
  }
  if (captureFlagNpcBlocksPlayer(nextX, nextZ, player.radius)) return true;
  return false;
}

function isAvatarBlocked(nextX, nextZ, y, radius = 0.34) {
  const floor = y > 1.8 ? 1 : 0;
  for (const c of doorColliders) {
    if (c.floor !== null && c.floor !== floor) continue;
    if (c.active && !c.active()) continue;
    const dx = Math.abs(nextX - c.x);
    const dz = Math.abs(nextZ - c.z);
    if (dx < c.sx / 2 + radius && dz < c.sz / 2 + radius) return true;
  }
  for (const c of colliders) {
    if (c.floor !== null && c.floor !== floor) continue;
    if (c === homeTardisCollider && homeTardisDoorOpen && homeTardisGroup) {
      const local = new THREE.Vector3(nextX - homeTardisGroup.position.x, 0, nextZ - homeTardisGroup.position.z)
        .applyAxisAngle(new THREE.Vector3(0, 1, 0), -homeTardisGroup.rotation.y);
      if (Math.abs(local.x) < 0.66 && local.z > 0.62 && local.z < 1.58) continue;
    }
    const dx = Math.abs(nextX - c.x);
    const dz = Math.abs(nextZ - c.z);
    if (dx < c.sx / 2 + radius && dz < c.sz / 2 + radius) return true;
  }
  return false;
}

function shortestAvatarYawDelta(fromYaw, toYaw) {
  return movementShortestYawDelta(fromYaw, toYaw);
}

function turnActiveAvatarTowardYaw(targetYaw, dt) {
  if (!activeMarker || !Number.isFinite(targetYaw)) return 0;
  const result = stepAcceleratedYaw({
    yaw: activeMarker.rotation.y,
    targetYaw,
    angularVelocity: activeMarker.userData.turnAngularVelocity || 0,
    dt,
    maxSpeed: ACTIVE_AVATAR_MAX_TURN_RADIANS_PER_SECOND,
    maxAcceleration: ACTIVE_AVATAR_MAX_TURN_ACCELERATION_RADIANS_PER_SECOND_SQUARED,
  });
  activeMarker.rotation.y = result.yaw;
  activeMarker.userData.turnAngularVelocity = result.angularVelocity;
  const remaining = result.remainingRadians;
  activeMarker.userData.turnEvidence = {
    mode: "acceleration_bounded_shortest_arc_yaw_v2",
    targetYaw: Number(targetYaw.toFixed(5)),
    remainingRadians: Number(remaining.toFixed(5)),
    angularVelocityRadiansPerSecond: Number(result.angularVelocity.toFixed(5)),
    angularAccelerationRadiansPerSecondSquared: Number(result.angularAcceleration.toFixed(5)),
    maxSpeedRadiansPerSecond: ACTIVE_AVATAR_MAX_TURN_RADIANS_PER_SECOND,
    maxAccelerationRadiansPerSecondSquared: ACTIVE_AVATAR_MAX_TURN_ACCELERATION_RADIANS_PER_SECOND_SQUARED,
    aligned: result.aligned,
    instantFlip: false,
    visuallyReviewedThisSession: false,
  };
  return remaining;
}

function updateActiveAvatarLocomotionTransition(dt) {
  if (!activeMarker) return;
  const desired = activeMarker.userData.isMoving && Number(activeMarker.userData.lastStepMeters || 0) > 0.0001 ? 1 : 0;
  const previous = Number(activeMarker.userData.locomotionBlend || 0);
  const blend = advanceLocomotionBlend(previous, desired, dt, {
    riseSeconds: 0.24,
    fallSeconds: 0.34,
  });
  const turnBlend = THREE.MathUtils.clamp(
    Math.abs(Number(activeMarker.userData.turnAngularVelocity || 0)) / ACTIVE_AVATAR_MAX_TURN_RADIANS_PER_SECOND,
    0,
    1,
  );
  activeMarker.userData.locomotionBlend = blend;
  activeMarker.userData.turnInPlaceBlend = turnBlend;
  activeMarker.userData.locomotionTransition = {
    mode: "distance_driven_start_stop_blend_v1",
    blend: Number(blend.toFixed(4)),
    desired,
    turnInPlaceBlend: Number(turnBlend.toFixed(4)),
    startSeconds: 0.24,
    stopSeconds: 0.34,
    phaseFrozenWhileStopped: true,
    visuallyReviewedThisSession: false,
  };
}

function captureFlagPointInBounds(position) {
  if (!position) return false;
  const b = captureFlagWorld.bounds;
  return position.x > b.xMin && position.x < b.xMax && position.z > b.zMin && position.z < b.zMax;
}

function captureFlagShouldShowBattlefield() {
  const playerInBattlefield = captureFlagPointInBounds(player.position);
  const activeInBattlefield = captureFlagPointInBounds(activeMarker?.position);
  return playerInBattlefield || (observeFollowEnabled && activeInBattlefield);
}

function updateCaptureFlagBattlefieldVisibility() {
  if (!captureFlagBattlefieldGroup) return;
  captureFlagBattlefieldGroup.visible = captureFlagShouldShowBattlefield();
}

function captureFlagDistanceTo(point, position) {
  if (!point || !position) return Infinity;
  return Math.hypot(point.x - position.x, point.z - position.z);
}

function captureFlagParticipantPosition() {
  if (captureFlagState.actor === "active_avatar" && activeMarker) return activeMarker.position;
  if (captureFlagState.actor === "player" && !observeFollowEnabled) return player.position;
  return null;
}

function captureFlagParticipantCanBeTagged() {
  if (captureFlagState.actor === "active_avatar") return !!activeMarker;
  if (captureFlagState.actor === "player") return !observeFollowEnabled;
  return false;
}

function captureFlagNpcBlocksPlayer(nextX, nextZ, radius = player.radius) {
  if (observeFollowEnabled) return false;
  if (!captureFlagPointInBounds({ x: nextX, z: nextZ })) return false;
  if (captureFlagBattlefieldGroup && !captureFlagBattlefieldGroup.visible) return false;
  for (const npc of captureFlagNpcs) {
    const r = npc.collisionRadius || 0.55;
    if (Math.hypot(nextX - npc.group.position.x, nextZ - npc.group.position.z) < r + radius) return true;
  }
  return false;
}

function resetCaptureFlagNpcPositions() {
  for (const npc of captureFlagNpcs) {
    if (!npc.waypoints.length) continue;
    npc.group.position.copy(npc.waypoints[0]);
    npc.group.position.y = ACTIVE_AVATAR_GROUND_Y;
    npc.index = Math.min(1, npc.waypoints.length - 1);
    npc.alertUntil = 0;
    npc.lastSeen = null;
  }
}

function hideCaptureFlagObjective() {
  if (captureFlagFlagGroup) captureFlagFlagGroup.visible = false;
  if (captureFlagFlagLight) captureFlagFlagLight.visible = false;
}

function spawnCaptureFlagObjective() {
  if (!captureFlagFlagGroup) return null;
  const previous = captureFlagState.flagIndex;
  let next = Math.floor(Math.random() * captureFlagWorld.flagSpots.length);
  if (captureFlagWorld.flagSpots.length > 1 && next === previous) {
    next = (next + 1 + Math.floor(Math.random() * (captureFlagWorld.flagSpots.length - 1))) % captureFlagWorld.flagSpots.length;
  }
  const spot = captureFlagWorld.flagSpots[next];
  captureFlagState.flagIndex = next;
  captureFlagState.flagCarried = false;
  captureFlagFlagGroup.position.copy(spot);
  captureFlagFlagGroup.position.y = ACTIVE_AVATAR_GROUND_Y;
  captureFlagFlagGroup.visible = true;
  if (captureFlagFlagLight) captureFlagFlagLight.visible = true;
  return spot;
}

function startCaptureFlagGame(actor = "player") {
  if (!CAPTURE_FLAG_WORLD_ENABLED) {
    show("Capture The Flag is offloaded from Home World. It should return later as a separate notebook world, not as Home World geometry.");
    return null;
  }
  const captures = captureFlagState.captures || 0;
  const tags = captureFlagState.tags || 0;
  const bestSeconds = captureFlagState.bestSeconds || null;
  captureFlagState = {
    actor,
    phase: "seeking_flag",
    flagIndex: captureFlagState.flagIndex ?? -1,
    flagCarried: false,
    captures,
    tags,
    bestSeconds,
    startedAt: clock.elapsedTime,
    lastEvent: "game_started",
    dodges: 0,
  };
  resetCaptureFlagNpcPositions();
  const spot = spawnCaptureFlagObjective();
  if (actor === "player") {
    player.position.copy(captureFlagWorld.battlefieldArrival);
    player.floor = 0;
    player.yaw = 0;
  } else if (actor === "active_avatar" && activeMarker) {
    activeMarker.position.copy(captureFlagWorld.activeBase);
    activeMarker.userData.roamZone = "capture_flag";
    activeMarker.userData.roamReady = true;
    activeMarker.userData.roamIndex = 0;
    activeMarker.userData.waitUntil = 0;
  }
  show(`Capture the Flag started. Glowing flag spawned at sector ${spot ? spot.x.toFixed(0) : "?"},${spot ? spot.z.toFixed(0) : "?"}.`);
  return spot;
}

function travelToCaptureFlagWorld(actor = "player") {
  if (!CAPTURE_FLAG_WORLD_ENABLED) {
    show("Capture The Flag is offloaded from Home World. It should return later as a separate notebook world, not as Home World geometry.");
    return false;
  }
  captureFlagHomePortalCooldownUntil = clock.elapsedTime + 2.0;
  player.position.copy(captureFlagWorld.battlefieldArrival);
  player.floor = 0;
  player.yaw = 0;
  player.pitch = 0;
  startCaptureFlagGame(actor);
  show("Entered the Capture The Flag notebook world. Touch the glowing flag, then get back to base without being tagged.");
}

function returnToHomeWorldFromCaptureFlag() {
  captureFlagReturnPortalCooldownUntil = clock.elapsedTime + 2.0;
  hideCaptureFlagObjective();
  captureFlagState = {
    ...captureFlagState,
    actor: null,
    phase: "idle",
    flagCarried: false,
    lastEvent: "returned_home",
  };
  player.position.copy(captureFlagWorld.homeArrival);
  player.floor = 0;
  player.yaw = Math.PI / 2;
  player.pitch = 0;
  show("Returned to Home World by the Kira World billboard.");
}

function collectCaptureFlagObjective(actor = captureFlagState.actor) {
  if (captureFlagState.phase !== "seeking_flag") return false;
  captureFlagState.phase = "returning_base";
  captureFlagState.flagCarried = true;
  captureFlagState.lastEvent = `${actor || "player"}_collected_flag`;
  hideCaptureFlagObjective();
  show("Flag collected. Get back to base camp before a Dalek or Stormtrooper tags you.");
  recordMovementLearningAttempt({
    skill: "capture_flag_game",
    phase: "flag_collected",
    target: "glowing far-side flag",
    actor,
  });
  return true;
}

function completeCaptureFlagGame(actor = captureFlagState.actor) {
  if (captureFlagState.phase !== "returning_base") return false;
  const elapsed = Math.max(0, clock.elapsedTime - (captureFlagState.startedAt || clock.elapsedTime));
  captureFlagState.phase = "won";
  captureFlagState.flagCarried = false;
  captureFlagState.captures = (captureFlagState.captures || 0) + 1;
  captureFlagState.bestSeconds = captureFlagState.bestSeconds === null ? elapsed : Math.min(captureFlagState.bestSeconds, elapsed);
  captureFlagState.lastEvent = `${actor || "player"}_captured_flag`;
  hideCaptureFlagObjective();
  show(`Capture complete in ${elapsed.toFixed(1)} seconds. Base camp wins.`);
  recordMovementLearningAttempt({
    skill: "capture_flag_game",
    phase: "capture_complete",
    target: "base camp",
    actor,
    elapsedSeconds: Number(elapsed.toFixed(2)),
    dodges: captureFlagState.dodges || 0,
  });
  return true;
}

function tagCaptureFlagParticipant(npc) {
  if (!["seeking_flag", "returning_base"].includes(captureFlagState.phase)) return false;
  const actor = captureFlagState.actor || "player";
  captureFlagState.phase = "tagged";
  captureFlagState.flagCarried = false;
  captureFlagState.tags = (captureFlagState.tags || 0) + 1;
  captureFlagState.lastEvent = `${actor}_tagged_by_${npc?.type || "npc"}`;
  captureFlagState.restartAt = clock.elapsedTime + 2.2;
  hideCaptureFlagObjective();
  if (actor === "player") {
    player.position.copy(captureFlagWorld.battlefieldArrival);
    player.floor = 0;
  } else if (activeMarker) {
    activeMarker.position.copy(captureFlagWorld.activeBase);
    activeMarker.userData.gaitMode = null;
    activeMarker.userData.isMoving = false;
    activeMarker.userData.walkSpeed = 0;
    setActiveAvatarAction("idle");
  }
  show(`Tagged by ${npc?.type === "dalek" ? "a Dalek" : "a Stormtrooper"}. Back to base camp.`);
  recordMovementLearningAttempt({
    skill: "capture_flag_game",
    phase: "tagged",
    target: npc?.name || "smart npc",
    actor,
  });
  return true;
}

function updateCaptureFlagFlagVisual(t) {
  if (!captureFlagFlagGroup?.visible) return;
  captureFlagFlagGroup.position.y = ACTIVE_AVATAR_GROUND_Y + Math.sin(t * 2.6) * 0.08;
  captureFlagFlagGroup.rotation.y = Math.sin(t * 1.3) * 0.22;
}

function moveCaptureFlagNpcToward(npc, target, speed, dt) {
  const dx = target.x - npc.group.position.x;
  const dz = target.z - npc.group.position.z;
  const distance = Math.hypot(dx, dz);
  if (distance < 0.001) return distance;
  const step = Math.min(distance, speed * dt);
  npc.group.position.x += (dx / distance) * step;
  npc.group.position.z += (dz / distance) * step;
  npc.group.rotation.y = Math.atan2(dx, dz) + (npc.forwardYawOffset ?? Math.PI);
  npc.group.position.y = ACTIVE_AVATAR_GROUND_Y + Math.sin(clock.elapsedTime * 5.2 + npc.index) * 0.015;
  return distance;
}

function updateCaptureFlagNpcs(t, dt) {
  const participant = captureFlagParticipantPosition();
  const gameActive = ["seeking_flag", "returning_base"].includes(captureFlagState.phase) && participant && captureFlagParticipantCanBeTagged();
  for (const npc of captureFlagNpcs) {
    let target = npc.waypoints[npc.index] || npc.waypoints[0];
    let speed = npc.speed;
    let chasingParticipant = false;
    if (gameActive) {
      const distanceToParticipant = captureFlagDistanceTo(npc.group.position, participant);
      if (distanceToParticipant < npc.sightRadius) {
        target = participant;
        speed = npc.chaseSpeed;
        chasingParticipant = true;
        npc.alertUntil = t + 2.4;
        npc.lastSeen = participant.clone();
      } else if (npc.lastSeen && t < npc.alertUntil) {
        target = npc.lastSeen;
        speed = npc.chaseSpeed * 0.82;
      }
    }
    const distance = moveCaptureFlagNpcToward(npc, target, speed, dt);
    if (gameActive && chasingParticipant && captureFlagDistanceTo(npc.group.position, participant) < npc.tagRadius) {
      tagCaptureFlagParticipant(npc);
    }
    if (!gameActive || target !== participant) {
      if (distance < 0.42 && npc.waypoints.length) npc.index = (npc.index + 1) % npc.waypoints.length;
    }
    const alert = t < npc.alertUntil;
    npc.group.traverse((node) => {
      if (!node.isMesh || node.userData.originalMaterial) return;
      node.userData.originalMaterial = node.material;
    });
    if (npc.fallback?.children?.length) {
      npc.fallback.scale.y = 1 + Math.sin(t * 4 + npc.index) * 0.02;
    }
    npc.group.userData.alert = alert;
  }
}

function updateCaptureFlagPlayerGame(t) {
  if (observeFollowEnabled && captureFlagState.actor !== "player") return;
  const playerInBattlefield = captureFlagPointInBounds(player.position);
  if (captureFlagDistanceTo(captureFlagWorld.homePortal, player.position) < 2.1 && t > captureFlagHomePortalCooldownUntil && !playerInBattlefield) {
    travelToCaptureFlagWorld("player");
    return;
  }
  if (playerInBattlefield && captureFlagDistanceTo(captureFlagWorld.returnPortal, player.position) < 2.0 && t > captureFlagReturnPortalCooldownUntil) {
    returnToHomeWorldFromCaptureFlag();
    return;
  }
  if (!playerInBattlefield || captureFlagState.actor !== "player") return;
  if (captureFlagState.phase === "tagged" && t > (captureFlagState.restartAt || 0) && captureFlagDistanceTo(captureFlagWorld.base, player.position) < 4.5) {
    startCaptureFlagGame("player");
    return;
  }
  if (captureFlagState.phase === "seeking_flag" && captureFlagFlagGroup?.visible && captureFlagDistanceTo(captureFlagFlagGroup.position, player.position) < 1.25) {
    collectCaptureFlagObjective("player");
  }
  if (captureFlagState.phase === "returning_base" && captureFlagDistanceTo(captureFlagWorld.base, player.position) < 3.5) {
    completeCaptureFlagGame("player");
  }
}

function updateCaptureFlagWorld(t, dt) {
  if (HOME_WORLD_PRE_RAM_LIGHT_MODE) return;
  updateCaptureFlagBattlefieldVisibility();
  updateCaptureFlagPlayerGame(t);
  updateCaptureFlagFlagVisual(t);
  updateCaptureFlagNpcs(t, dt);
}

function activeAvatarInsideSharedBathroom(position = activeMarker?.position) {
  if (!position || position.y < 1.8) return false;
  return position.x > 3.35 && position.x < 7.85 && position.z > -2.62 && position.z < 2.62;
}

function activeAvatarSafeRecoveryPosition() {
  if (activeAvatarIsKiraLike() && activeMarker?.userData?.roamZone === "kira_bungalow") {
    return KIRA_BUNGALOW_SPAWN.clone();
  }
  if (activeAvatarIsKiraLike()) return KIRA_BUNGALOW_SPAWN.clone();
  if (activeMarker?.userData?.roamZone === "upstairs" || (activeMarker?.position.y ?? 0) > 1.8) {
    return new THREE.Vector3(2.55, ACTIVE_AVATAR_SECOND_FLOOR_Y, -4.85);
  }
  return marinetteRoamWaypoints[0].clone();
}

function replanActiveAvatarThroughHomeEntry(t, reason = "home_entry_blocked") {
  if (!activeMarker) return false;
  const route = activeMarker.userData.practiceRoute;
  if (!route?.requiresHomeEntry || activeAvatarInsideOneBedroomHome(activeMarker.position)) return false;
  if ((route.homeEntryReplanCount || 0) >= 3) return false;
  if (t - Number(route.homeEntryReplanAt || -999) < 0.7) return false;

  const entryCorridor = oneBedroomHomeEntryCorridorWaypoints();
  const destination = (route.postEntryWaypoints || []).map((point) => point.clone());
  route.waypoints = [activeMarker.position.clone(), ...entryCorridor, ...destination];
  route.waypointLabels = [
    "current_body_position",
    "outside_door_threshold",
    "door_opening_center",
    "inside_door_threshold",
    ...destination.map((_, index) => index === destination.length - 1 ? "interaction_target" : "interaction_approach"),
  ];
  route.homeEntryReplanCount = (route.homeEntryReplanCount || 0) + 1;
  route.homeEntryReplanAt = t;
  activeMarker.userData.roamIndex = 1;
  activeMarker.userData.navigationRecovery = null;
  activeMarker.userData.stuckSince = null;
  activeMarker.userData.lastDistanceToTarget = null;
  activeMarker.userData.lastRouteFailureTruth = null;
  activeMarker.userData.waitUntil = t + 0.12;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  recordMovementLearningAttempt({
    skill: "home_entry_navigation",
    phase: "replanned_centered_doorway_corridor",
    target: route.id,
    reason,
    replanCount: route.homeEntryReplanCount,
    teleported: false,
    personOwnedIntent: !!route.selfChosen,
  });
  return true;
}

function failActiveAvatarPracticeRouteInPlace(t, reason = "bounded_replans_exhausted", plannerReason = "no_collision_free_route") {
  if (!activeMarker) return false;
  const route = activeMarker.userData.practiceRoute;
  if (!route) return false;
  const bodyPosition = activeMarker.position.clone();
  const target = route.interiorGoal?.clone?.() || route.waypoints?.[route.waypoints.length - 1]?.clone?.() || null;
  const failure = {
    id: route.id,
    reason: "no_collision_free_route_after_bounded_replans",
    trigger: reason,
    plannerReason,
    replanCount: Number(route.interiorReplanCount || 0),
    target: target ? {
      x: Number(target.x.toFixed(3)),
      y: Number(target.y.toFixed(3)),
      z: Number(target.z.toFixed(3)),
    } : null,
    bodyPosition: {
      x: Number(bodyPosition.x.toFixed(3)),
      y: Number(bodyPosition.y.toFixed(3)),
      z: Number(bodyPosition.z.toFixed(3)),
    },
    bodyStayedInPlace: true,
    personOwnedIntent: !!route.selfChosen,
    teleported: false,
    recordedAt: new Date().toISOString(),
  };
  if (activeMarker.userData.transitionEvidence) {
    activeMarker.userData.transitionEvidence.completed = false;
    activeMarker.userData.transitionEvidence.failed = true;
    activeMarker.userData.transitionEvidence.failureReason = failure.reason;
    activeMarker.userData.transitionEvidence.failedAt = failure.recordedAt;
  }
  activeMarker.userData.practiceRoute = null;
  activeMarker.userData.skillInteraction = null;
  activeMarker.userData.navigationRecovery = null;
  activeMarker.userData.gaitMode = null;
  activeMarker.userData.stuckSince = null;
  activeMarker.userData.lastDistanceToTarget = null;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  activeMarker.userData.waitUntil = t + 0.65;
  activeMarker.userData.lastRouteFailureTruth = failure;
  activeMarker.userData.lastEmbodimentCapabilityBlock = {
    ...failure,
    requires: "choose another reachable activity or revise the physical collision/navigation path",
  };
  setActiveAvatarAction("idle");
  recordMovementLearningAttempt({
    skill: route.id,
    phase: "bounded_replans_exhausted_body_stayed_in_place",
    target: route.finishHold?.label || route.id,
    trigger: reason,
    plannerReason,
    replanCount: failure.replanCount,
    bodyPosition: failure.bodyPosition,
    personOwnedIntent: failure.personOwnedIntent,
    teleported: false,
  });
  return true;
}

function replanActiveAvatarInsideOneBedroom(t, reason = "interior_route_stuck") {
  if (!activeMarker) return false;
  const route = activeMarker.userData.practiceRoute;
  if (!route?.interiorRoute || !route.interiorGoal || !activeAvatarInsideOneBedroomHome(activeMarker.position)) return false;
  if (t - Number(route.interiorReplanAt || -999) < 0.7) {
    activeMarker.userData.waitUntil = Math.max(Number(activeMarker.userData.waitUntil || 0), t + 0.18);
    return true;
  }
  if (Number(route.interiorReplanCount || 0) >= ACTIVE_AVATAR_INTERIOR_REPLAN_LIMIT) {
    return failActiveAvatarPracticeRouteInPlace(t, reason, route.lastInteriorPlannerReason || "replan_limit_reached");
  }

  route.interiorReplanCount = Number(route.interiorReplanCount || 0) + 1;
  route.interiorReplanAt = t;
  const plan = planActiveAvatarOneBedroomInteriorRoute(activeMarker.position, route.interiorGoal, reason);
  route.lastInteriorPlannerReason = plan.reason;
  route.interiorPlanVisitedNodes = Number(plan.visitedNodes || 0);
  if (!plan.ok || !plan.waypoints.length) {
    activeMarker.userData.stuckSince = null;
    activeMarker.userData.lastDistanceToTarget = null;
    activeMarker.userData.isMoving = false;
    activeMarker.userData.walkSpeed = 0;
    activeMarker.userData.lastStepMeters = 0;
    activeMarker.userData.waitUntil = t + 0.45;
    recordMovementLearningAttempt({
      skill: route.id,
      phase: "interior_route_replan_failed_body_stayed_in_place",
      target: route.finishHold?.label || route.id,
      trigger: reason,
      plannerReason: plan.reason,
      replanCount: route.interiorReplanCount,
      visitedNodes: Number(plan.visitedNodes || 0),
      teleported: false,
    });
    if (route.interiorReplanCount >= ACTIVE_AVATAR_INTERIOR_REPLAN_LIMIT) {
      return failActiveAvatarPracticeRouteInPlace(t, reason, plan.reason);
    }
    return true;
  }

  route.waypoints = [activeMarker.position.clone(), ...plan.waypoints.map((point) => point.clone())];
  route.waypointLabels = [
    "current_body_position",
    ...plan.waypoints.map((_, index) => (
      index === plan.waypoints.length - 1 ? "interaction_target" : `collision_free_replan_detour_${index + 1}`
    )),
  ];
  route.postEntryWaypoints = plan.waypoints.map((point) => point.clone());
  route.interiorPlanMode = plan.mode;
  route.progressWatch = null;
  activeMarker.userData.roamIndex = Math.min(1, route.waypoints.length - 1);
  activeMarker.userData.navigationRecovery = null;
  activeMarker.userData.stuckSince = null;
  activeMarker.userData.lastDistanceToTarget = null;
  activeMarker.userData.waitUntil = t + 0.12;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  recordMovementLearningAttempt({
    skill: route.id,
    phase: "interior_route_replanned_around_collision",
    target: route.finishHold?.label || route.id,
    trigger: reason,
    plannerMode: plan.mode,
    plannerReason: plan.reason,
    replanCount: route.interiorReplanCount,
    visitedNodes: Number(plan.visitedNodes || 0),
    waypointCount: plan.waypoints.length,
    bodyPositionUnchangedByReplan: true,
    personOwnedIntent: !!route.selfChosen,
    teleported: false,
  });
  return true;
}

function recoverActiveAvatarFromRouteStuck(t, reason = "route_stuck") {
  if (!activeMarker) return false;
  if (replanActiveAvatarThroughHomeEntry(t, reason)) return true;
  if (replanActiveAvatarInsideOneBedroom(t, reason)) return true;
  const current = activeMarker.position.clone();
  const recovery = activeMarker.userData.lastSafePosition?.clone?.() || null;
  const distance = recovery ? Math.hypot(recovery.x - current.x, recovery.z - current.z) : Infinity;
  const canUseRecovery = !!(
    recovery &&
    !activeAvatarInsideSharedBathroom(recovery) &&
    !isAvatarBlocked(recovery.x, recovery.z, recovery.y, ACTIVE_AVATAR_COLLISION_RADIUS) &&
    Math.abs(recovery.y - current.y) < 0.25 &&
    distance > 0.04 &&
    distance <= ACTIVE_AVATAR_RECOVERY_MAX_DISTANCE_METERS &&
    activeAvatarDirectPathIsClear(current, recovery, ACTIVE_AVATAR_COLLISION_RADIUS)
  );
  let phase = "paused_replan_no_safe_recovery_path";
  if (canUseRecovery) {
    activeMarker.userData.navigationRecovery = {
      reason,
      mode: "collision_checked_recovery_walk_v2",
      target: { x: recovery.x, y: recovery.y, z: recovery.z },
      queuedAt: t,
      expiresAt: t + 4.0,
      startingDistanceMeters: Number(distance.toFixed(3)),
      teleported: false,
      collisionChecked: true,
      visuallyReviewedThisSession: false,
    };
    phase = "queued_collision_checked_recovery_walk";
  } else {
    activeMarker.userData.navigationRecovery = null;
  }
  activeMarker.userData.stuckSince = null;
  activeMarker.userData.lastDistanceToTarget = null;
  activeMarker.userData.waitUntil = t + (canUseRecovery ? 0.12 : 0.55);
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  recordMovementLearningAttempt({
    skill: "route_safety",
    phase,
    target: reason,
    position: {
      x: Number(activeMarker.position.x.toFixed(3)),
      y: Number(activeMarker.position.y.toFixed(3)),
      z: Number(activeMarker.position.z.toFixed(3)),
    },
    recoveryDistanceMeters: Number.isFinite(distance) ? Number(distance.toFixed(3)) : null,
    teleported: false,
    collisionChecked: canUseRecovery,
  });
  return true;
}

function activeAvatarNavigationRecoveryTarget(t) {
  if (!activeMarker) return null;
  const state = activeMarker.userData.navigationRecovery;
  const target = state?.target;
  if (!state || !target) return null;
  const point = new THREE.Vector3(target.x, target.y, target.z);
  const invalid = t > Number(state.expiresAt || 0)
    || isAvatarBlocked(point.x, point.z, point.y, ACTIVE_AVATAR_COLLISION_RADIUS)
    || !activeAvatarDirectPathIsClear(activeMarker.position, point, ACTIVE_AVATAR_COLLISION_RADIUS);
  if (invalid) {
    recordMovementLearningAttempt({
      skill: "route_safety",
      phase: "recovery_walk_cancelled_before_crossing_obstacle",
      target: state.reason || "route_stuck",
      teleported: false,
    });
    activeMarker.userData.navigationRecovery = null;
    return null;
  }
  return point;
}

function activeAvatarResumePositionFromShell(shellState, label) {
  const resume = shellState?.active_resume_position || null;
  const activeName = String(label || shellState?.active_label || "").toLowerCase();
  const resumeCandidate = String(resume?.candidate || "").toLowerCase();
  const activeCandidate = String(shellState?.active_candidate || "").toLowerCase();
  if (!resume || !resume.position) return null;
  if (resumeCandidate && activeCandidate && resumeCandidate !== activeCandidate) return null;
  if (!activeName && !activeCandidate) return null;
  const position = resume.position;
  const x = Number(position.x);
  const y = Number(position.y);
  const z = Number(position.z);
  if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) return null;
  if (x < -156 || x > 276 || z < -96 || z > 288 || y < -1 || y > 8) return null;
  const isKira = activeName === "kira" || activeName.includes("kira first") || activeCandidate === "kira" || resumeCandidate === "kira";
  if (isKira && (y > 1.8 || String(resume.roamZone || "").toLowerCase() === "upstairs")) return null;
  return {
    position: new THREE.Vector3(x, y, z),
    rotationY: Number.isFinite(Number(resume.rotationY)) ? Number(resume.rotationY) : null,
    roamZone: String(resume.roamZone || ""),
    roamIndex: Number.isFinite(resume.roamIndex) ? resume.roamIndex : null,
    wardrobeState: resume.wardrobeState || null,
  };
}

function applyActiveAvatarResumeState(resume) {
  if (!activeMarker || !resume) return;
  if (Number.isFinite(resume.rotationY)) activeMarker.rotation.y = resume.rotationY;
  let zone = activeAvatarIsKiraLike() && pointInsideKiraBungalow(activeMarker.position)
    ? "kira_home_world"
    : (resume.roamZone || (activeMarker.position.y > 1.8 ? "upstairs" : "downstairs"));
  if (activeAvatarIsKiraLike() && (zone === "kira_bungalow" || zone === "downstairs")) zone = "kira_home_world";
  activeMarker.userData.roamReady = true;
  activeMarker.userData.roamZone = zone;
  activeMarker.userData.usesGenericAutonomy = true;
  activeMarker.userData.roamPolicy = "self_directed_random_goal_learning";
  activeMarker.userData.autonomousRoamTarget = null;
  activeMarker.userData.autonomousRoamHistory = activeMarker.userData.autonomousRoamHistory || [];
  const route = activeAvatarCurrentWaypoints();
  activeMarker.userData.roamIndex = Number.isFinite(resume.roamIndex)
    ? resume.roamIndex
    : activeAvatarNearestWaypointIndex(route, activeMarker.position);
  activeMarker.userData.lastMoveT = clock.elapsedTime;
  activeMarker.userData.waitUntil = clock.elapsedTime + 0.7;
  activeMarker.userData.lastSafePosition = activeMarker.position.clone();
  activeMarker.userData.stuckSince = null;
  activeMarker.userData.lastDistanceToTarget = null;
  applyActiveAvatarWardrobeResumeState(resume.wardrobeState);
}

function activeWorldPosition(location, label, shellState = null) {
  const resume = activeAvatarResumePositionFromShell(shellState, label);
  const legacyMallLocationUnavailable = !HOME_WORLD_LEGACY_STRIP_MALL_ENABLED && ["spa", "stripmall"].includes(location);
  if (resume && !legacyMallLocationUnavailable) return resume.position.clone();
  if (location === "library") return new THREE.Vector3(22.4, 0.05, 45.2);
  if (HOME_WORLD_LEGACY_STRIP_MALL_ENABLED && location === "spa") return new THREE.Vector3(2.9, 0.05, 32.2);
  if (HOME_WORLD_LEGACY_STRIP_MALL_ENABLED && location === "stripmall") return new THREE.Vector3(-10, 0.05, 29.4);
  const activeName = String(label || "").toLowerCase();
  if (activeName === "kira" || activeName.includes("kira first")) {
    if (location === "home" || location === "upstairs" || legacyMallLocationUnavailable) return KIRA_BUNGALOW_SPAWN.clone();
  }
  if (location === "upstairs") return new THREE.Vector3(5.7, ACTIVE_AVATAR_SECOND_FLOOR_Y, -4.65);
  return new THREE.Vector3(0.9, 0.05, 5.8);
}

function shouldUsePoseAvatarFirst(label) {
  const activeName = (label || "").toLowerCase();
  return false;
}

function displayModelUrlFor(shellState, label) {
  const url = shellState.active_model_url || "";
  const activeName = String(label || shellState.active_ai || "").toLowerCase();
  if (shouldRevokeKiraRuntimeModel(shellState, label, url)) return "";
  if ((activeName === "kira" || activeName.includes("kira first")) && url.startsWith("/Avatar/models/temp_ai/kira/")) {
    return url.replace("/Avatar/models/temp_ai/kira/", "/models/temp_ai/kira/");
  }
  return url;
}

function unloadActiveAvatarModel() {
  activeAvatarModelLoadGeneration += 1;
  clearKiraExistingMouthLipSync();
  clearKiraEyeRig();
  clearKiraHairRig();
  if (activeMarker && activeAvatarRoot) activeMarker.remove(activeAvatarRoot);
  activeAvatarMixer = null;
  activeAvatarProceduralRig = null;
  activeAvatarAmbientMicroMovementFrame = null;
  activeAvatarRoot = null;
  activeAvatarModelUrl = "";
}

function clearActiveAvatar() {
  clearDoorReachRig();
  unloadActiveAvatarModel();
  activeVoiceExpressionOwnsTalkingAction = false;
  activeVoiceExpressionReleaseAt = -Infinity;
  activeKiraMouthPlaybackEvidence = {
    matchedPlaybackSegments: 0,
    matchedPlaybackFrames: 0,
    currentPlaybackFrames: 0,
    lastMatchedRevision: 0,
    lastCompletedPlaybackFrames: 0,
    lastPlaybackPeakAmount: 0,
    lastPlaybackPeakOpeningDistance: 0,
  };
  activePostureInteraction = null;
  activeSkillInteraction = null;
  if (activeMarker) {
    scene.remove(activeMarker);
    activeMarker = null;
  }
  activePoseTextures = new Map();
  activePoseManifestUrl = "";
  activePoseKey = "";
  activePoseSprite = null;
  activePoseMaterial = null;
}

function makeOrbMarker(label) {
  const group = new THREE.Group();
  const orb = new THREE.Mesh(new THREE.SphereGeometry(0.38, 32, 20), materials.glass);
  orb.position.y = 1.05;
  group.add(orb);
  const glow = new THREE.Mesh(new THREE.SphereGeometry(0.52, 32, 20), materials.glass);
  glow.position.y = 1.05;
  glow.scale.set(1.0, 0.9, 1.0);
  group.add(glow);
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 128;
  const context = canvas.getContext("2d");
  context.fillStyle = "rgba(4, 13, 26, 0.82)";
  context.fillRect(0, 18, canvas.width, 92);
  context.strokeStyle = "rgba(155, 231, 255, 0.95)";
  context.lineWidth = 5;
  context.strokeRect(3, 21, canvas.width - 6, 86);
  context.fillStyle = "#eefaff";
  context.font = "600 48px Segoe UI, sans-serif";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(String(label || "Active person").slice(0, 28), canvas.width / 2, canvas.height / 2);
  const nameTexture = new THREE.CanvasTexture(canvas);
  nameTexture.colorSpace = THREE.SRGBColorSpace;
  const nameSprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: nameTexture,
    transparent: true,
    depthWrite: false,
  }));
  nameSprite.position.y = 1.82;
  nameSprite.scale.set(2.8, 0.7, 1);
  nameSprite.userData.kind = "orb_identity_label";
  group.add(nameSprite);
  group.userData.label = label;
  group.userData.kind = "orb";
  group.userData.movementContract = "gentle_bob_and_bounded_roam";
  group.userData.identityLabelVisible = true;
  return group;
}

function updateActiveOrbFallback(t) {
  const orb = activeMarker?.children?.find?.((child) => child.userData?.kind === "orb");
  if (!orb) return;
  orb.position.y = Math.sin(t * 1.35) * 0.075;
  orb.rotation.y = Math.sin(t * 0.42) * 0.08;
  orb.userData.lastMovementAt = t;
}

function removeGroupPresenceOrb(candidateId) {
  const item = groupPresenceOrbs.get(candidateId);
  if (!item) return;
  scene.remove(item.marker);
  item.marker.traverse((child) => {
    child.geometry?.dispose?.();
    if (child.userData?.kind === "orb_identity_label") {
      child.material?.map?.dispose?.();
      child.material?.dispose?.();
    }
  });
  groupPresenceOrbs.delete(candidateId);
}

function syncGroupPresenceOrbs(shellState) {
  const payloads = Array.isArray(shellState?.active_presence_payloads)
    ? shellState.active_presence_payloads
    : [];
  const desired = new Map(
    payloads
      .filter((item) => !item?.focused && String(item?.presentation || "").startsWith("named_moving_orb"))
      .map((item) => [String(item.candidate_id || ""), item])
      .filter(([candidateId]) => candidateId),
  );
  for (const candidateId of groupPresenceOrbs.keys()) {
    if (!desired.has(candidateId)) removeGroupPresenceOrb(candidateId);
  }
  let index = 0;
  for (const [candidateId, payload] of desired.entries()) {
    const label = String(payload.label || candidateId);
    const position = payload.position || {};
    const base = new THREE.Vector3(
      Number.isFinite(Number(position.x)) ? Number(position.x) : 5.7 + index * 0.85,
      Number.isFinite(Number(position.y)) ? Number(position.y) : 3.32,
      Number.isFinite(Number(position.z)) ? Number(position.z) : -4.65 - index * 0.65,
    );
    let item = groupPresenceOrbs.get(candidateId);
    if (!item || item.label !== label) {
      if (item) removeGroupPresenceOrb(candidateId);
      const marker = makeOrbMarker(label);
      marker.userData.kind = "secondary_group_presence_orb";
      marker.userData.candidateId = candidateId;
      marker.userData.sensoryInitiativeOwner = false;
      marker.userData.bodyTelemetryOwner = false;
      marker.position.copy(base);
      scene.add(marker);
      item = {
        marker,
        label,
        base,
        phase: index * 1.61803398875,
      };
      groupPresenceOrbs.set(candidateId, item);
    } else {
      item.base.copy(base);
    }
    index += 1;
  }
}

function updateGroupPresenceOrbs(t) {
  for (const item of groupPresenceOrbs.values()) {
    item.marker.position.set(
      item.base.x + Math.sin(t * 0.27 + item.phase) * 0.16,
      item.base.y + Math.sin(t * 1.2 + item.phase) * 0.075,
      item.base.z + Math.cos(t * 0.23 + item.phase) * 0.16,
    );
    item.marker.rotation.y = Math.sin(t * 0.38 + item.phase) * 0.1;
    item.marker.userData.lastMovementAt = t;
  }
}

function safeActiveClips(clips) {
  return (clips || []).filter((clip) => {
    const name = (clip.name || "").toLowerCase();
    return !name.includes("shared_mouth") && !name.includes("mouth") && !name.includes("_control");
  });
}

function fallbackActiveClip(clips) {
  const safeClips = safeActiveClips(clips);
  return safeClips.find((clip) => /idle|stand|breath/i.test(clip.name || ""))
    || safeClips.find((clip) => /walk|run|move/i.test(clip.name || ""))
    || safeClips[0]
    || null;
}

function activeAvatarActionIsGroundedLocomotion(action = activeAvatarAction) {
  return ["walk", "jog", "run", "dodge"].includes(String(action || "").toLowerCase());
}

function findActiveClip(clips, action) {
  const wanted = String(action || "idle").toLowerCase();
  const safeClips = safeActiveClips(clips);
  const terms = {
    idle: ["idle", "stand", "breath"],
    talking: ["talk", "speak", "conversation", "idle"],
    wave: ["wave", "greet", "hello"],
    use_computer: ["type", "computer", "idle"],
    read_book: ["read", "book", "idle"],
    walk: ["walk", "run", "jog", "locomotion"],
    jog: ["jog", "run", "walk", "locomotion"],
    run: ["run", "sprint", "jog", "walk", "locomotion"],
    dodge: ["dodge", "evade", "run", "jog", "walk", "locomotion"],
    sit: ["sit", "idle"],
    lie_down: ["lie_down", "lie", "lay", "idle"],
    duck: ["duck", "crouch", "idle"],
    jump: ["jump", "hop", "idle"],
    swim_idle: ["swim", "swim_idle", "idle"],
    door_open_reach: ["door_open_reach", "door", "reach", "idle"],
  }[wanted] || [wanted, "idle"];
  return safeClips.find((clip) => clip.name.toLowerCase() === wanted)
    || safeClips.find((clip) => terms.some((term) => clip.name.toLowerCase().includes(term)))
    || null;
}

function activeClipTerms(action) {
  const wanted = String(action || "idle").toLowerCase();
  return {
    idle: ["idle"],
    talking: ["talking", "talk", "speak", "conversation"],
    wave: ["wave", "greet", "hello"],
    use_computer: ["use_computer", "type", "computer"],
    read_book: ["read_book", "read", "book"],
    walk: ["walk"],
    jog: ["jog", "run", "walk", "locomotion"],
    run: ["run", "sprint", "jog", "walk", "locomotion"],
    dodge: ["dodge", "evade", "run", "jog", "walk", "locomotion"],
    sit: ["sit"],
    lie_down: ["lie_down", "lie", "lay"],
    duck: ["duck", "crouch"],
    jump: ["jump", "hop"],
    door_open_reach: ["door_open_reach", "door", "reach"],
    pick_up: ["pick_up", "pickup"],
    change_clothes: ["change_clothes"],
    swim_idle: ["swim_idle", "swim"],
    look_around: ["look_around"],
  }[wanted] || [wanted];
}

function clipMatchesAction(clip, action) {
  const name = (clip.name || "").toLowerCase();
  if (!name || name.includes("_control")) return false;
  return activeClipTerms(action).some((term) => name === term || name.endsWith(`_${term}`) || name.includes(term));
}

function activeAvatarCurrentWalkSpeed() {
  if (activeMarker?.userData?.walkSpeed) return activeMarker.userData.walkSpeed;
  return activeMarker?.position?.y > 2 ? ACTIVE_AVATAR_WALK_SPEED_UPSTAIRS : ACTIVE_AVATAR_WALK_SPEED_GROUND;
}

function activeAvatarWalkTimeScaleForClip(clip) {
  const speed = Math.max(0.05, activeAvatarCurrentWalkSpeed());
  const cycleSeconds = ACTIVE_AVATAR_WALK_STRIDE_METERS / speed;
  const authoredSeconds = Math.max(0.1, clip?.duration || cycleSeconds);
  return THREE.MathUtils.clamp(
    authoredSeconds / cycleSeconds,
    ACTIVE_AVATAR_MIN_WALK_TIME_SCALE,
    ACTIVE_AVATAR_MAX_WALK_TIME_SCALE,
  );
}

function activeAvatarWalkPhase01() {
  const phase = activeMarker?.userData?.walkCyclePhase ?? activeAvatarMovePhase;
  const wrapped = ((phase % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
  return wrapped / (Math.PI * 2);
}

function syncActiveWalkClipTiming() {
  if (!activeAvatarMixer || !activeAvatarRoot?.userData?.clips?.length || !activeAvatarActionIsGroundedLocomotion()) return;
  for (const clip of activeAvatarRoot.userData.clips) {
    if (!clipMatchesAction(clip, activeAvatarAction) && !clipMatchesAction(clip, "walk")) continue;
    const scale = activeAvatarWalkTimeScaleForClip(clip);
    const action = activeAvatarMixer.clipAction(clip);
    action.timeScale = ACTIVE_AVATAR_WALK_PHASE_LOCKED ? 0 : scale;
    action.paused = false;
    if (activeMarker) {
      activeMarker.userData.walkTimeScale = scale;
      activeMarker.userData.walkPhaseLocked = ACTIVE_AVATAR_WALK_PHASE_LOCKED;
      activeMarker.userData.walkClipDuration = clip.duration;
    }
  }
}

function syncActiveWalkClipPhase() {
  if (!ACTIVE_AVATAR_WALK_PHASE_LOCKED || !activeAvatarMixer || !activeAvatarRoot?.userData?.clips?.length || !activeAvatarActionIsGroundedLocomotion()) return false;
  const phase01 = activeAvatarWalkPhase01();
  let synced = false;
  for (const clip of activeAvatarRoot.userData.clips) {
    if (!clipMatchesAction(clip, activeAvatarAction) && !clipMatchesAction(clip, "walk")) continue;
    const action = activeAvatarMixer.clipAction(clip);
    action.enabled = true;
    action.paused = false;
    action.timeScale = 0;
    action.time = clip.duration * phase01;
    synced = true;
    if (activeMarker) {
      activeMarker.userData.walkPhase01 = phase01;
      activeMarker.userData.walkClipTime = action.time;
    }
  }
  return synced;
}

function playActiveClip(clips) {
  if (!activeAvatarMixer || !clips?.length) return;
  const matchedClips = clips.filter((clip) => clipMatchesAction(clip, activeAvatarAction));
  if (activeAvatarActionIsGroundedLocomotion() && activeAvatarProceduralRig?.usable && !matchedClips.length && !findActiveClip(clips, "walk")) {
    if (activeMarker) activeMarker.userData.usingProceduralWalk = true;
    return;
  }
  if (activeMarker) activeMarker.userData.usingProceduralWalk = false;
  const clipsToPlay = matchedClips.length
    ? matchedClips
    : [findActiveClip(clips, activeAvatarAction) || fallbackActiveClip(clips)].filter(Boolean);
  for (const clip of clipsToPlay) {
    const action = activeAvatarMixer.clipAction(clip);
    action.reset();
    action.enabled = true;
    if (activeAvatarActionIsGroundedLocomotion()) {
      const scale = activeAvatarWalkTimeScaleForClip(clip);
      action.timeScale = ACTIVE_AVATAR_WALK_PHASE_LOCKED ? 0 : scale;
      if (ACTIVE_AVATAR_WALK_PHASE_LOCKED) action.time = clip.duration * activeAvatarWalkPhase01();
      if (activeMarker) activeMarker.userData.walkTimeScale = scale;
    } else {
      action.timeScale = 1;
    }
    action.setLoop(activeAvatarAction === "wave" ? THREE.LoopOnce : THREE.LoopRepeat, activeAvatarAction === "wave" ? 1 : Infinity);
    action.clampWhenFinished = activeAvatarAction === "wave";
    action.fadeIn(0.08);
    action.play();
  }
  const blinkClip = clips.find((item) => clipMatchesAction(item, "blink"));
  if (blinkClip && !clipsToPlay.includes(blinkClip)) {
    const blinkAction = activeAvatarMixer.clipAction(blinkClip);
    blinkAction.reset();
    blinkAction.enabled = true;
    blinkAction.setLoop(THREE.LoopRepeat, Infinity);
    blinkAction.play();
  }
  const visemeClip = clips.find((item) => clipMatchesAction(item, "viseme_talking"));
  if (visemeClip && activeAvatarAction === "talking" && !clipsToPlay.includes(visemeClip)) {
    const visemeAction = activeAvatarMixer.clipAction(visemeClip);
    visemeAction.reset();
    visemeAction.enabled = true;
    visemeAction.setLoop(THREE.LoopRepeat, Infinity);
    visemeAction.play();
  }
}

function setActiveAvatarAction(actionName) {
  if (activeAvatarAction === actionName) return;
  activeAvatarAction = actionName;
  activeAvatarActionStarted = clock.elapsedTime;
  if (activeAvatarMixer && activeAvatarRoot?.userData?.clips) {
    activeAvatarMixer.stopAllAction();
    playActiveClip(activeAvatarRoot.userData.clips);
    syncActiveWalkClipTiming();
  }
}

function cleanActiveAvatarModelNode(node) {
  const name = (node.name || "").toLowerCase();
  const isBrokenAddedDetail =
    name.startsWith("v4_") &&
    (name.includes("finger") ||
      name.includes("fingernail") ||
      name.includes("nail") ||
      name.includes("pigtail") ||
      name.includes("bang") ||
      name.includes("hair"));
  const isVisibleRigHelper =
    isBrokenAddedDetail ||
    name.includes("_control") ||
    name.includes("control_") ||
    name.includes("guide") ||
    name.includes("detached") ||
    name.includes("loose_finger") ||
    name.includes("loose_fingernail") ||
    name.includes("detached_fingernail") ||
    name.includes("detached_finger") ||
    name.includes("mouth_proxy") ||
    name.includes("mouth_control");
  const form = String(activeAvatarForm || "civilian").toLowerCase();
  const wantsHero = form === "hero" || form === "ladybug";
  const wantsSleep = form === "sleepwear" || form === "sleep";
  const wantsSwim = form === "swimwear" || form === "swim";
  const isHeroPart = name.startsWith("hero_") || name.includes("_hero_") || name === "hero_form_group";
  const isCivilianPart = name.startsWith("civilian_") || name.includes("_civilian_") || name === "civilian_form_group";
  const isSleepPart = name.startsWith("sleepwear_") || name.includes("_sleepwear_");
  const isSwimPart = name.startsWith("swimwear_") || name.includes("_swimwear_");
  if (isVisibleRigHelper) node.visible = false;
  if (isHeroPart) node.visible = wantsHero && !isVisibleRigHelper;
  if (isSleepPart) node.visible = wantsSleep && !isVisibleRigHelper;
  if (isSwimPart) node.visible = wantsSwim && !isVisibleRigHelper;
  if (isCivilianPart) node.visible = !wantsHero && !wantsSleep && !wantsSwim && !isVisibleRigHelper;
  if (node.isMesh) {
    node.castShadow = true;
    node.receiveShadow = true;
    node.frustumCulled = false;
  }
}

function harmonizeRuntimeMarinetteSkin(root, skinColor = MARINETTE_SKIN_COLOR) {
  const target = new THREE.Color(skinColor);
  const isRebuiltBaseBody = !!root?.userData?.useGenericProceduralRigForMarinette;
  root.traverse((node) => {
    if (!node.isMesh || !node.material) return;
    const name = String(node.name || "").toLowerCase();
    if (/body_neck|simple_neck|bead_neck|neck_proxy|generated_neck|shared_neck/.test(name)) {
      node.visible = false;
      node.userData.hiddenByRuntimeMarinetteRepair = true;
      return;
    }
    const materialsToTint = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materialsToTint) {
      if (!material?.color) continue;
      const c = material.color;
      const materialName = String(material.name || "").toLowerCase();
      const isSkinNamed = isRebuiltBaseBody
        ? /skin/.test(materialName)
        : /skin|body|torso|chest|arm|leg|hand|shoulder|thigh|shin|calf/.test(name);
      const looksSkin = c.r > 0.46 && c.g > 0.28 && c.b > 0.22 && c.r >= c.g && c.g >= c.b * 0.72;
      if (!isSkinNamed && !looksSkin) continue;
      material.color.copy(target);
      material.roughness = Math.max(material.roughness ?? 0.55, 0.48);
      material.metalness = Math.min(material.metalness ?? 0, 0.02);
      material.needsUpdate = true;
    }
  });
}

function harmonizeRuntimeKiraAdultSkin(root, skinColor = KIRA_ADULT_SKIN_COLOR) {
  if (!root || !activeAvatarIsKiraLike()) return;
  const target = new THREE.Color(skinColor);
  root.traverse((node) => {
    if (!node.isMesh || !node.material) return;
    const name = String(node.name || "").toLowerCase();
    if (/hair|wig|eye|iris|pupil|lash|brow|teeth|tongue|mouth|shoe|shirt|pants|dress|cloth|phone/.test(name)) return;
    const tintMaterial = (material) => {
      if (!material?.color) return;
      const materialName = String(material.name || "").toLowerCase();
      if (/hair|wig|eye|iris|pupil|lash|brow|teeth|tongue|mouth|shoe|shirt|pants|dress|cloth/.test(materialName)) return;
      const c = material.color;
      const looksBlankBody = c.r > 0.72 && c.g > 0.72 && c.b > 0.72;
      const looksSkin = c.r > 0.45 && c.g > 0.28 && c.b > 0.22 && c.r >= c.g && c.g >= c.b * 0.7;
      const namedSkin = /skin|body|torso|chest|arm|leg|hand|shoulder|thigh|shin|calf|foot|head|face|neck/.test(`${name} ${materialName}`);
      if (!looksBlankBody && !looksSkin && !namedSkin) return;
      // R6 carries a baked dark review texture.  Multiplying that texture by
      // the old light color can only make it darker; it cannot reproduce the
      // pre-R6 live appearance.  Restore the exact earlier runtime material
      // contract: untextured skin response, the established light tone,
      // roughness 0.60, metalness 0, and double-sided rendering.  This changes
      // no geometry and leaves both the selected R6 GLB and rollback GLB
      // byte-for-byte untouched.
      for (const textureSlot of [
        "map", "normalMap", "roughnessMap", "metalnessMap", "aoMap",
        "emissiveMap", "bumpMap", "displacementMap", "alphaMap",
      ]) {
        if (textureSlot in material) material[textureSlot] = null;
      }
      material.color.copy(target);
      material.roughness = 0.6;
      material.metalness = 0;
      material.side = THREE.DoubleSide;
      material.vertexColors = false;
      material.transparent = false;
      material.opacity = 1;
      material.alphaTest = 0;
      material.userData.kiraSkinTemplate = "pre_r6_live_light_untextured_v1";
      material.userData.kiraOriginalSkinMaterialRestored = true;
      material.needsUpdate = true;
    };
    const materialsToTint = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materialsToTint) tintMaterial(material);
  });
  root.userData.kiraSkinTemplate = {
    name: "pre_r6_live_light_untextured_v1",
    color: `#${new THREE.Color(skinColor).getHexString()}`,
    maturity: "adult",
    geometryChanged: false,
    completeAdultAnatomyProven: false,
  };
}

function markerSpaceToAvatarRootLocal(root, x, y, z) {
  const s = root?.scale?.x || 1;
  return new THREE.Vector3(
    (x - (root?.position?.x || 0)) / s,
    (y - (root?.position?.y || 0)) / s,
    (z - (root?.position?.z || 0)) / s,
  );
}

function markerLengthToAvatarRootLocal(root, value) {
  const s = root?.scale?.x || 1;
  return value / s;
}

function meshCountInside(root) {
  let count = 0;
  root?.traverse?.((node) => {
    if (node.isMesh) count += 1;
  });
  return count;
}

function clearKiraExistingMouthLipSync() {
  if (activeKiraMouthLipSyncRig) restoreExistingMouthLipSyncRig(activeKiraMouthLipSyncRig);
  activeKiraMouthLipSyncRig = null;
}

function attachKiraExistingMouthLipSync(root) {
  clearKiraExistingMouthLipSync();
  if (!root || !activeAvatarIsKiraLike()) return false;
  const meshCountBefore = meshCountInside(root);
  let selection = null;
  root.traverse((node) => {
    if (!node.isSkinnedMesh || !node.geometry?.attributes?.position || !node.geometry?.index) return;
    const region = findExistingMouthVertexRegion(node.geometry.attributes.position, node.geometry.index);
    if (!region || (selection && selection.region.score <= region.score)) return;
    selection = { mesh: node, region };
  });
  if (!selection) {
    if (activeMarker) {
      activeMarker.userData.kiraExistingMouthLipSync = {
        active: false,
        reason: "existing_lip_island_not_found; no fallback mouth was created",
        createdSceneNodes: 0,
      };
    }
    return false;
  }
  activeKiraMouthLipSyncRig = createExistingMouthLipSyncRig(selection.mesh, selection.region);
  if (!activeKiraMouthLipSyncRig) return false;
  activeKiraMouthLipSyncRig.meshCountBefore = meshCountBefore;
  activeKiraMouthLipSyncRig.meshCountAfter = meshCountInside(root);
  if (activeKiraMouthLipSyncRig.meshCountAfter !== meshCountBefore) {
    clearKiraExistingMouthLipSync();
    return false;
  }
  if (activeMarker) activeMarker.userData.kiraExistingMouthLipSync = kiraExistingMouthLipSyncProbe();
  return true;
}

function normalizedIdentity(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function voicePlaybackMatchesActiveAvatar(playback = activeVoicePlaybackState) {
  if (!playback?.playing || !activeAvatarIsKiraLike()) return false;
  const playbackCandidate = normalizedIdentity(playback.candidate);
  const activeCandidate = normalizedIdentity(activeShellState?.active_candidate);
  if (playbackCandidate && activeCandidate) return playbackCandidate === activeCandidate;
  const playbackLabel = normalizedIdentity(playback.label);
  const activeLabel = normalizedIdentity(activeMarker?.userData?.label || activeShellState?.active_label);
  return !!playbackLabel && !!activeLabel && playbackLabel === activeLabel;
}

function setActiveVoicePlaybackState(playback = {}) {
  const wasMatched = voicePlaybackMatchesActiveAvatar();
  activeVoicePlaybackState = {
    revision: Number(playback.revision || 0),
    active: !!playback.active,
    playing: !!playback.playing,
    phase: String(playback.phase || "idle"),
    candidate: String(playback.candidate || ""),
    label: String(playback.label || ""),
    chunkIndex: Number.isFinite(Number(playback.chunk_index)) ? Number(playback.chunk_index) : null,
    playbackStartedAt: Number(playback.playback_started_at || 0),
    playbackEndedAt: Number(playback.playback_ended_at || 0),
  };
  const isMatched = voicePlaybackMatchesActiveAvatar();
  if (isMatched && (!wasMatched || activeKiraMouthPlaybackEvidence.lastMatchedRevision !== activeVoicePlaybackState.revision)) {
    activeKiraMouthPlaybackEvidence.matchedPlaybackSegments += 1;
    activeKiraMouthPlaybackEvidence.currentPlaybackFrames = 0;
    activeKiraMouthPlaybackEvidence.lastMatchedRevision = activeVoicePlaybackState.revision;
    activeKiraMouthPlaybackEvidence.lastPlaybackPeakAmount = 0;
    activeKiraMouthPlaybackEvidence.lastPlaybackPeakOpeningDistance = 0;
  } else if (!isMatched && wasMatched) {
    activeKiraMouthPlaybackEvidence.lastCompletedPlaybackFrames = activeKiraMouthPlaybackEvidence.currentPlaybackFrames;
    activeKiraMouthPlaybackEvidence.currentPlaybackFrames = 0;
  }
  if (isMatched) {
    activeVoiceExpressionReleaseAt = Infinity;
    // Actual audio playback may own a conversational pose when Kira was
    // otherwise standing idle. It never interrupts walking, reading, resting,
    // or another self-chosen action, and it is not driven by the user's text.
    if (activeAvatarAction === "idle" || activeAvatarAction === "talking") {
      activeVoiceExpressionOwnsTalkingAction = true;
      if (activeAvatarAction !== "talking") setActiveAvatarAction("talking");
    }
  } else if (wasMatched && activeVoiceExpressionOwnsTalkingAction) {
    activeVoiceExpressionReleaseAt = clock.elapsedTime + 0.42;
  }
  return activeVoicePlaybackState;
}

function updateKiraExistingMouthLipSync(t, dt) {
  if (!activeKiraMouthLipSyncRig || !activeAvatarIsKiraLike()) return;
  const playingMatchedActiveAvatar = voicePlaybackMatchesActiveAvatar();
  const updated = updateExistingMouthLipSyncRig(activeKiraMouthLipSyncRig, {
    playing: playingMatchedActiveAvatar,
    seconds: t,
    deltaSeconds: dt,
    // The same authored lip island supplies both speech and a very small idle
    // smile. Ambient smile is always zero while matched audio is playing, so
    // it cannot fight lip sync and it never creates a replacement mouth.
    smileAmount: Number(activeAvatarAmbientMicroMovementFrame?.face?.smile || 0),
  });
  if (updated && playingMatchedActiveAvatar) {
    activeKiraMouthPlaybackEvidence.matchedPlaybackFrames += 1;
    activeKiraMouthPlaybackEvidence.currentPlaybackFrames += 1;
    activeKiraMouthPlaybackEvidence.lastPlaybackPeakAmount = Math.max(
      activeKiraMouthPlaybackEvidence.lastPlaybackPeakAmount,
      Number(activeKiraMouthLipSyncRig.amount || 0),
    );
    activeKiraMouthPlaybackEvidence.lastPlaybackPeakOpeningDistance = Math.max(
      activeKiraMouthPlaybackEvidence.lastPlaybackPeakOpeningDistance,
      Number(activeKiraMouthLipSyncRig.openingDistance || 0),
    );
  }
}

function kiraExistingMouthLipSyncProbe() {
  const probe = existingMouthLipSyncProbe(activeKiraMouthLipSyncRig);
  const sourceMeshes = [];
  if (!activeKiraMouthLipSyncRig) {
    activeAvatarRoot?.traverse?.((node) => {
      if (!node.isMesh || !node.geometry?.attributes?.position) return;
      sourceMeshes.push({
        name: node.name || null,
        skinned: !!node.isSkinnedMesh,
        vertexCount: Number(node.geometry.attributes.position.count || 0),
        indexCount: Number(node.geometry.index?.count || 0),
        mouthCandidates: node.isSkinnedMesh && node.geometry.index
          ? auditExistingMouthVertexRegions(node.geometry.attributes.position, node.geometry.index, 8)
          : undefined,
      });
    });
  }
  return {
    ...probe,
    inactiveReason: !activeKiraMouthLipSyncRig
      ? activeMarker?.userData?.kiraExistingMouthLipSync?.reason || "not_attached"
      : null,
    sourceMeshes: !activeKiraMouthLipSyncRig ? sourceMeshes : undefined,
    playingMatchedActiveAvatar: voicePlaybackMatchesActiveAvatar(),
    matchedPlaybackSegments: activeKiraMouthPlaybackEvidence.matchedPlaybackSegments,
    matchedPlaybackFrames: activeKiraMouthPlaybackEvidence.matchedPlaybackFrames,
    currentPlaybackFrames: activeKiraMouthPlaybackEvidence.currentPlaybackFrames,
    lastMatchedRevision: activeKiraMouthPlaybackEvidence.lastMatchedRevision,
    lastCompletedPlaybackFrames: activeKiraMouthPlaybackEvidence.lastCompletedPlaybackFrames,
    lastPlaybackPeakAmount: Number(activeKiraMouthPlaybackEvidence.lastPlaybackPeakAmount.toFixed(6)),
    lastPlaybackPeakOpeningDistance: Number(activeKiraMouthPlaybackEvidence.lastPlaybackPeakOpeningDistance.toFixed(6)),
    playback: {
      revision: activeVoicePlaybackState.revision,
      active: activeVoicePlaybackState.active,
      playing: activeVoicePlaybackState.playing,
      phase: activeVoicePlaybackState.phase,
      candidate: activeVoicePlaybackState.candidate || null,
      chunkIndex: activeVoicePlaybackState.chunkIndex,
    },
    meshCountBefore: activeKiraMouthLipSyncRig?.meshCountBefore ?? null,
    meshCountAfter: activeKiraMouthLipSyncRig?.meshCountAfter ?? null,
    secondMouthCreated: false,
  };
}

function kiraExistingMouthScreenBounds() {
  const rig = activeKiraMouthLipSyncRig;
  if (!rig?.mesh || !rig?.position || !rig?.region?.vertices?.length) return null;
  rig.mesh.updateMatrixWorld(true);
  const rect = renderer.domElement.getBoundingClientRect();
  const points = [];
  for (const vertex of rig.region.vertices) {
    const point = new THREE.Vector3().fromBufferAttribute(rig.position, vertex);
    if (rig.mesh.isSkinnedMesh && typeof rig.mesh.applyBoneTransform === "function") {
      rig.mesh.applyBoneTransform(vertex, point);
    }
    rig.mesh.localToWorld(point);
    point.project(camera);
    points.push({
      x: rect.left + (point.x * 0.5 + 0.5) * rect.width,
      y: rect.top + (-point.y * 0.5 + 0.5) * rect.height,
    });
  }
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    minX: Number(minX.toFixed(3)),
    maxX: Number(maxX.toFixed(3)),
    minY: Number(minY.toFixed(3)),
    maxY: Number(maxY.toFixed(3)),
    centerX: Number(((minX + maxX) * 0.5).toFixed(3)),
    centerY: Number(((minY + maxY) * 0.5).toFixed(3)),
    width: Number((maxX - minX).toFixed(3)),
    height: Number((maxY - minY).toFixed(3)),
  };
}

function clearKiraEyeRig() {
  if (activeKiraEyeRig?.root?.parent) activeKiraEyeRig.root.parent.remove(activeKiraEyeRig.root);
  activeKiraEyeRig = null;
  activeKiraEyeTestState = null;
}

function clearKiraHairRig() {
  if (activeKiraHairRig?.root?.parent) activeKiraHairRig.root.parent.remove(activeKiraHairRig.root);
  activeKiraHairRig = null;
}

function isNodeInsideRoot(node, root) {
  let cursor = node;
  while (cursor) {
    if (cursor === root) return true;
    cursor = cursor.parent;
  }
  return false;
}

function findKiraHeadBone(root) {
  const proceduralHead = activeAvatarProceduralRig?.bones?.head;
  if (proceduralHead && isNodeInsideRoot(proceduralHead, root)) return proceduralHead;
  let head = null;
  root.traverse((node) => {
    if (head || !node.isBone) return;
    const name = String(node.name || "").toLowerCase();
    if (name.includes("head") && !name.includes("top") && !name.includes("end")) head = node;
  });
  return head;
}

function findKiraHeadSkinBinding(root, headBone) {
  let binding = null;
  root?.traverse((node) => {
    if (binding || !node.isSkinnedMesh || !node.skeleton || !headBone) return;
    const boneIndex = node.skeleton.bones.indexOf(headBone);
    const boneInverse = boneIndex >= 0 ? node.skeleton.boneInverses?.[boneIndex] : null;
    if (boneInverse) binding = { mesh: node, boneIndex, boneInverse: boneInverse.clone() };
  });
  return binding;
}

function countLegacyKiraEyeNodes(root) {
  let count = 0;
  root?.traverse((node) => {
    if (/inset eye socket|eye movement test rig|imported human eye reference socket insert/i.test(String(node.name || ""))) count += 1;
  });
  return count;
}

function cloneKiraStagedEyeRig(source) {
  const clone = source.clone(true);
  clone.name = "Kira socket-seated brown eye rig v3.3 runtime container";
  clone.position.set(0, 0, 0);
  clone.rotation.set(0, 0, 0);
  clone.scale.set(1, 1, 1);
  clone.traverse((node) => {
    const nodeName = String(node.name || "");
    if (/^Kira(?:Left|Right)Iris$/.test(nodeName)) {
      node.scale.x *= KIRA_RUNTIME_IRIS_DIAMETER_SCALE;
      node.scale.y *= KIRA_RUNTIME_IRIS_DIAMETER_SCALE;
      node.userData.kiraRuntimeVisualFit = "reviewed_authored_diameter_1.0x";
    } else if (/^Kira(?:Left|Right)Cornea$/.test(nodeName)) {
      node.scale.x *= KIRA_RUNTIME_CORNEA_DIAMETER_SCALE;
      node.scale.y *= KIRA_RUNTIME_CORNEA_DIAMETER_SCALE;
      node.userData.kiraRuntimeVisualFit = "reviewed_authored_diameter_1.0x";
    }
    if (!node.isMesh) return;
    if (Array.isArray(node.material)) node.material = node.material.map((material) => material.clone());
    else if (node.material) node.material = node.material.clone();
    if (/^Kira(?:Left|Right)Iris$/.test(nodeName)) {
      // The source-derived iris discs face the anatomical eye interior in the
      // exported GLB. Blender's review renderer shows both sides, while
      // Three.js normally culls this camera-facing back side. Keep the authored
      // geometry and texture intact and make only that existing iris surface
      // two-sided; no second eye or painted overlay is introduced.
      const irisMaterials = Array.isArray(node.material) ? node.material : [node.material];
      for (const material of irisMaterials) {
        if (!material) continue;
        material.side = THREE.DoubleSide;
        if (KIRA_EYE_IRIS_DEPTH_DIAGNOSTIC) {
          material.depthTest = false;
          material.depthWrite = false;
        }
        material.needsUpdate = true;
      }
      if (KIRA_EYE_IRIS_DEPTH_DIAGNOSTIC) node.renderOrder = 999;
      node.userData.kiraRuntimeIrisSideRepair = "authored_surface_double_sided";
    }
    if (/UpperLid|LowerLid/.test(node.name || "")) {
      const materialsToTint = Array.isArray(node.material) ? node.material : [node.material];
      for (const material of materialsToTint) {
        if (!material) continue;
        if (material.color) material.color.setHex(KIRA_ADULT_EYELID_COLOR);
        material.roughness = 0.66;
        material.needsUpdate = true;
      }
    }
  });
  return clone;
}

function stagedKiraEyeNodes(container) {
  const exact = (name) => container.getObjectByName(name);
  const leftPivot = exact("KiraLeftEyePivot");
  const rightPivot = exact("KiraRightEyePivot");
  const leftSocket = exact("KiraLeftEyeSocket");
  const rightSocket = exact("KiraRightEyeSocket");
  const leftIris = exact("KiraLeftIris");
  const rightIris = exact("KiraRightIris");
  const leftSclera = exact("KiraLeftSclera");
  const rightSclera = exact("KiraRightSclera");
  const leftCornea = exact("KiraLeftCornea");
  const rightCornea = exact("KiraRightCornea");
  const visualFitNodes = [
    "KiraLeftIris", "KiraRightIris",
    "KiraLeftCornea", "KiraRightCornea",
    "KiraLeftSclera", "KiraRightSclera",
  ].map((name) => exact(name)).filter(Boolean);
  // R7-v3.3 deliberately has no generated eyelid shells.  Kira's existing
  // face remains the visible lid boundary until a real skinned-lid pass has
  // visual proof; an empty list prevents a false blink capability claim.
  const lids = [];
  const foundNames = [];
  container.traverse((node) => {
    if (node.name) foundNames.push(node.name);
  });
  return {
    leftPivot,
    rightPivot,
    leftSocket,
    rightSocket,
    leftIris,
    rightIris,
    leftSclera,
    rightSclera,
    leftCornea,
    rightCornea,
    visualFitNodes,
    lids,
    foundNames,
  };
}

function eyeCenterToHeadDistance(nodes, headBone) {
  if (!nodes?.leftSocket || !nodes?.rightSocket || !headBone) return null;
  const left = nodes.leftSocket.getWorldPosition(new THREE.Vector3());
  const right = nodes.rightSocket.getWorldPosition(new THREE.Vector3());
  const center = left.add(right).multiplyScalar(0.5);
  const head = headBone.getWorldPosition(new THREE.Vector3());
  return center.distanceTo(head);
}

function applyKiraR6EyeVisualFit(rig, requested = {}) {
  if (!rig?.pivots?.left?.node || !rig?.pivots?.right?.node) return false;
  const fit = {
    forwardOffset: THREE.MathUtils.clamp(
      Number.isFinite(Number(requested.forwardOffset))
        ? Number(requested.forwardOffset)
        : KIRA_R6_EYE_VISUAL_FIT.forwardOffset,
      -0.02,
      0.03,
    ),
    verticalOffset: THREE.MathUtils.clamp(
      Number.isFinite(Number(requested.verticalOffset))
        ? Number(requested.verticalOffset)
        : KIRA_R6_EYE_VISUAL_FIT.verticalOffset,
      -0.03,
      0.03,
    ),
    horizontalOffset: THREE.MathUtils.clamp(
      Number.isFinite(Number(requested.horizontalOffset))
        ? Number(requested.horizontalOffset)
        : KIRA_R6_EYE_VISUAL_FIT.horizontalOffset,
      -0.03,
      0.03,
    ),
    commonHorizontalOffset: THREE.MathUtils.clamp(
      Number.isFinite(Number(requested.commonHorizontalOffset))
        ? Number(requested.commonHorizontalOffset)
        : KIRA_R6_EYE_VISUAL_FIT.commonHorizontalOffset,
      -0.01,
      0.01,
    ),
    neutralYawDegrees: THREE.MathUtils.clamp(
      Number.isFinite(Number(requested.neutralYawDegrees))
        ? Number(requested.neutralYawDegrees)
        : KIRA_R6_EYE_VISUAL_FIT.neutralYawDegrees,
      -30,
      30,
    ),
    irisHorizontalOffset: THREE.MathUtils.clamp(
      Number.isFinite(Number(requested.irisHorizontalOffset))
        ? Number(requested.irisHorizontalOffset)
        : KIRA_R6_EYE_VISUAL_FIT.irisHorizontalOffset,
      -0.006,
      0.006,
    ),
    irisVerticalOffset: THREE.MathUtils.clamp(
      Number.isFinite(Number(requested.irisVerticalOffset))
        ? Number(requested.irisVerticalOffset)
        : KIRA_R6_EYE_VISUAL_FIT.irisVerticalOffset,
      -0.006,
      0.006,
    ),
    irisDepthOffset: THREE.MathUtils.clamp(
      Number.isFinite(Number(requested.irisDepthOffset))
        ? Number(requested.irisDepthOffset)
        : KIRA_R6_EYE_VISUAL_FIT.irisDepthOffset,
      -0.003,
      0.003,
    ),
    socketVerticalOffset: THREE.MathUtils.clamp(
      Number.isFinite(Number(requested.socketVerticalOffset))
        ? Number(requested.socketVerticalOffset)
        : KIRA_R6_EYE_VISUAL_FIT.socketVerticalOffset,
      -0.02,
      0.02,
    ),
    socketDepthOffset: THREE.MathUtils.clamp(
      Number.isFinite(Number(requested.socketDepthOffset))
        ? Number(requested.socketDepthOffset)
        : KIRA_R6_EYE_VISUAL_FIT.socketDepthOffset,
      -0.02,
      0.02,
    ),
  };
  for (const [side, sign] of [["left", -1], ["right", 1]]) {
    const socket = rig.nodes?.[`${side}Socket`];
    if (socket) {
      if (!socket.userData.kiraR6BasePosition) {
        socket.userData.kiraR6BasePosition = socket.position.toArray();
      }
      socket.position.fromArray(socket.userData.kiraR6BasePosition);
      socket.position.y += fit.socketVerticalOffset;
      socket.position.z += fit.socketDepthOffset;
    }
    const pivot = rig.pivots[side];
    if (!pivot.basePosition) pivot.basePosition = pivot.node.position.clone();
    pivot.node.position.copy(pivot.basePosition);
    pivot.node.position.x += fit.horizontalOffset * sign;
    pivot.node.position.x += fit.commonHorizontalOffset;
    pivot.node.position.y += fit.verticalOffset;
    pivot.node.position.z += fit.forwardOffset;
  }
  for (const node of rig.nodes.visualFitNodes || []) {
    if (!/Iris|LimbalRing|Pupil/.test(String(node.name || ""))) continue;
    if (!node.userData.kiraR6BasePosition) {
      node.userData.kiraR6BasePosition = node.position.toArray();
    }
    node.position.fromArray(node.userData.kiraR6BasePosition);
    // A positive irisHorizontalOffset means "away from the nose" for both
    // eyes.  Applying one common local-X shift made the reviewed face appear
    // cross-eyed even though the authored v3.3 eye asset is centred.  Keep the
    // sclera/socket/cornea placement unchanged and move only the existing
    // textured iris surface symmetrically within the fixed globes.
    const irisSideSign = /Left/.test(String(node.name || ""))
      ? -1
      : /Right/.test(String(node.name || ""))
        ? 1
        : 0;
    node.position.x += fit.irisHorizontalOffset * irisSideSign;
    node.position.y += fit.irisVerticalOffset;
    // The authored iris sits correctly in Blender, but GLTF axis conversion
    // can leave its coplanar surface hidden behind the sclera in WebGL.  This
    // bounded, reversible offset moves only the existing iris/limbal/pupil
    // layers along their local depth; it never moves or duplicates the eye.
    node.position.z += fit.irisDepthOffset;
  }
  rig.runtimeVisualFit.eyeGlobeTranslation = {
    ...fit,
    units: "metres_in_authored_eye_socket_space",
    reversible: true,
    sourceGlbModified: false,
    headGeometryModified: false,
  };
  rig.runtimeVisualFit.socketTranslationApplied = Math.abs(fit.socketVerticalOffset) > 0.0000001
    || Math.abs(fit.socketDepthOffset) > 0.0000001;
  rig.runtimeVisualFit.eyeGlobeTranslationApplied = Object.values(fit).some((value) => Math.abs(value) > 0.0000001);
  rig.runtimeVisualFit.r6VisualPlacementApplied = true;
  rig.runtimeVisualFit.r6VisualPlacementSourceOfTruth = "rendered_full_face_existing_r6_head_apertures";
  for (const side of ["left", "right"]) {
    const iris = rig.irises?.[side];
    if (iris?.node) iris.basePosition = iris.node.position.clone();
  }
  rig.avatarRoot.updateMatrixWorld(true);
  // Reset the invariant after a deliberate visual-fit change. Subsequent
  // browser checks can then distinguish real head-binding drift from this
  // one-time reversible socket correction.
  rig.initialEyeCenterToHeadDistance = eyeCenterToHeadDistance(rig.nodes, rig.headBone);
  return kiraEyeBindingProbe();
}

function attachStagedKiraEyeRig(root, source) {
  clearKiraEyeRig();
  const container = cloneKiraStagedEyeRig(source);
  root.add(container);
  root.updateMatrixWorld(true);
  const headBone = findKiraHeadBone(root);
  const headSkinBinding = findKiraHeadSkinBinding(root, headBone);
  if (headBone && KIRA_EYE_BINDING_MODE === "skin" && headSkinBinding) {
    // The eye vertices are authored in the same rest-model coordinates as the
    // skinned R6 head.  Parenting with the head bone's inverse-bind matrix
    // applies the same current-pose transform as a vertex weighted 100% to
    // that bone.  `Bone.attach()` preserves rest-world placement and therefore
    // leaves a posed head behind; this mode fixes that mismatch without
    // editing either source GLB.
    headBone.add(container);
    container.matrix.copy(headSkinBinding.boneInverse);
    container.matrix.decompose(container.position, container.quaternion, container.scale);
    container.updateMatrixWorld(true);
  } else if (headBone && KIRA_EYE_BINDING_MODE === "head") {
    headBone.updateWorldMatrix(true, false);
    headBone.attach(container);
    headBone.updateMatrixWorld(true);
  }
  const nodes = stagedKiraEyeNodes(container);
  const blinkMorphs = Object.fromEntries(nodes.lids.map(({ mesh, blinkIndex }) => [mesh?.name || "missing", blinkIndex]));
  const oldProceduralNodeCount = countLegacyKiraEyeNodes(root);
  const structurallyHeadBound = Boolean(headBone) && (
    container.parent === headBone || KIRA_EYE_BINDING_MODE === "root"
  );
  const structural = buildKiraEyeStructuralReport({
    foundNames: nodes.foundNames,
    blinkMorphs,
    headBound: structurallyHeadBound,
    headBoneName: headBone?.name || null,
    oldProceduralNodeCount,
  });
  activeKiraEyeRig = {
    avatarRoot: root,
    root: container,
    headBone,
    headSkinBinding,
    nodes,
    pivots: {
      left: nodes.leftPivot ? {
        node: nodes.leftPivot,
        baseQuaternion: nodes.leftPivot.quaternion.clone(),
        basePosition: nodes.leftPivot.position.clone(),
      } : null,
      right: nodes.rightPivot ? {
        node: nodes.rightPivot,
        baseQuaternion: nodes.rightPivot.quaternion.clone(),
        basePosition: nodes.rightPivot.position.clone(),
      } : null,
    },
    irises: {
      left: nodes.leftIris ? {
        node: nodes.leftIris,
        basePosition: nodes.leftIris.position.clone(),
      } : null,
      right: nodes.rightIris ? {
        node: nodes.rightIris,
        basePosition: nodes.rightIris.position.clone(),
      } : null,
    },
    lids: nodes.lids,
    direction: "center",
    blink: { left: 0, right: 0 },
    manualDirection: null,
    manualBlink: null,
    modelUrl: KIRA_STAGED_EYE_RIG_MODEL_URL,
    expectedSha256: KIRA_STAGED_EYE_RIG_SHA256,
    version: KIRA_EYE_CONTROL_EXAM_VERSION,
    structural,
    initialEyeCenterToHeadDistance: eyeCenterToHeadDistance(nodes, headBone),
    bindingMode: KIRA_EYE_BINDING_MODE,
    skinBindingMeshName: headSkinBinding?.mesh?.name || null,
    skinBindingBoneIndex: headSkinBinding?.boneIndex ?? null,
    runtimeVisualFit: {
      irisLimbusPupilDiameterScale: KIRA_RUNTIME_IRIS_DIAMETER_SCALE,
      corneaDiameterScale: KIRA_RUNTIME_CORNEA_DIAMETER_SCALE,
      socketTranslationApplied: false,
      affectedNodes: nodes.visualFitNodes.map((node) => node.name),
      liveBodyGlbModified: false,
    },
  };
  applyKiraR6EyeVisualFit(activeKiraEyeRig, KIRA_R6_EYE_VISUAL_FIT);
  if (activeMarker) {
    activeMarker.userData.kiraEyeRig = {
      active: true,
      version: KIRA_EYE_CONTROL_EXAM_VERSION,
      modelUrl: KIRA_STAGED_EYE_RIG_MODEL_URL,
      expectedSha256: KIRA_STAGED_EYE_RIG_SHA256,
      structural,
      defaultEnabled: true,
      optOutFlag: "?kiraEyeRig=off",
      explicitVersionFlag: "?kiraEyeRig=v3.3",
    };
  }
  return structural.complete && structural.headBound && structural.oldProceduralNodeCount === 0;
}

function ensureKiraEyeRig(root) {
  if (!root || !activeAvatarIsKiraLike()) return false;
  if (!KIRA_LIVE_EYE_RIG_ENABLED) {
    clearKiraEyeRig();
    if (activeMarker) {
      activeMarker.userData.kiraEyeRig = {
        active: false,
        disabledReason: KIRA_STAGED_EYE_RIG_VERSION === "off"
          ? "Kira's reviewed v3.3 socket-seated brown-eye rig was explicitly disabled for this page with ?kiraEyeRig=off."
          : `Unsupported Kira eye-rig request: ${KIRA_STAGED_EYE_RIG_VERSION}.`,
        defaultEnabled: true,
        optOutFlag: "?kiraEyeRig=off",
      };
    }
    return false;
  }
  if (activeKiraEyeRig?.avatarRoot === root) return true;
  if (kiraStagedEyeRigSource) return attachStagedKiraEyeRig(root, kiraStagedEyeRigSource);
  if (kiraStagedEyeRigLoading) return false;
  kiraStagedEyeRigLoading = true;
  if (activeMarker) {
    activeMarker.userData.kiraEyeRig = {
      active: false,
      loading: true,
      modelUrl: KIRA_STAGED_EYE_RIG_MODEL_URL,
    };
  }
  gltfLoader.load(
    KIRA_STAGED_EYE_RIG_MODEL_URL,
    (gltf) => {
      kiraStagedEyeRigSource = gltf.scene;
      kiraStagedEyeRigLoading = false;
      if (KIRA_LIVE_EYE_RIG_ENABLED && activeAvatarRoot && activeAvatarIsKiraLike()) ensureKiraEyeRig(activeAvatarRoot);
    },
    undefined,
    (error) => {
      kiraStagedEyeRigLoading = false;
      if (activeMarker) {
        activeMarker.userData.kiraEyeRig = {
          active: false,
          loading: false,
          modelUrl: KIRA_STAGED_EYE_RIG_MODEL_URL,
          error: error?.message || String(error),
        };
      }
      console.warn("Could not load staged Kira socket-seated brown-eye rig v3.3", error);
    },
  );
  return false;
}

function setKiraEyeDirectionOverride(direction = "center") {
  if (!activeKiraEyeRig) return false;
  activeKiraEyeRig.manualDirection = kiraEyeSideTargets(direction).id;
  activeKiraEyeTestState = null;
  return kiraEyeBindingProbe();
}

function setKiraEyeBlinkOverride(side = "both", amount = 1) {
  if (!activeKiraEyeRig) return false;
  // Kept as a diagnostic API so old review pages fail honestly.  R7-v3.3
  // has no approved skinned eyelids and must not fake a blink by moving the
  // eyeball or creating a second lid/face surface.
  activeKiraEyeRig.manualBlink = null;
  activeKiraEyeRig.blinkUnsupportedRequest = {
    side: String(side || "both"),
    amount: THREE.MathUtils.clamp(Number(amount) || 0, 0, 1),
    reason: "no_visually_approved_skinned_eyelid_geometry",
  };
  activeKiraEyeTestState = null;
  return false;
}

function clearKiraEyeOverrides() {
  if (!activeKiraEyeRig) return false;
  activeKiraEyeRig.manualDirection = null;
  activeKiraEyeRig.manualBlink = null;
  return true;
}

function startKiraEyeMovementTest(seconds = 10.6) {
  if (!activeMarker || !activeAvatarIsKiraLike() || !activeAvatarRoot) return false;
  if (!KIRA_LIVE_EYE_RIG_ENABLED) {
    clearKiraEyeRig();
    show("Kira's reviewed v3.3 eye rig is disabled for this page. Remove ?kiraEyeRig=off to restore her eyes.");
    return false;
  }
  if (!ensureKiraEyeRig(activeAvatarRoot) || !activeKiraEyeRig) {
    show("Loading Kira's exact-hash staged brown-eye rig for the optional eye-rig engineering check.");
    return false;
  }
  clearKiraEyeOverrides();
  const plannedSeconds = KIRA_EYE_CONTROL_PHASES.reduce((sum, phase) => sum + phase.seconds, 0);
  activeKiraEyeTestState = {
    startedAt: clock.elapsedTime,
    seconds: Math.max(2, Number(seconds) || plannedSeconds),
    plannedSeconds,
    phase: "center",
    completed: false,
  };
  setActiveAvatarAction("talking");
  return true;
}

function applyKiraIrisSurfaceGaze(iris, degrees) {
  if (!iris?.node || !iris?.basePosition) return;
  const yawRatio = THREE.MathUtils.clamp(Number(degrees?.yaw || 0) / 13, -1, 1);
  const pitchRatio = THREE.MathUtils.clamp(Number(degrees?.pitch || 0) / 7, -1, 1);
  const target = iris.basePosition.clone();
  target.x += 0.00125 * yawRatio;
  // Blender local Z is exported as Three.js local Y for this Y-up GLB.
  target.y += 0.00072 * pitchRatio;
  iris.node.position.lerp(target, 0.38);
}

function applyKiraBlink(sideAmounts) {
  if (!activeKiraEyeRig) return;
  activeKiraEyeRig.blink = { left: 0, right: 0 };
  activeKiraEyeRig.blinkRequestedButUnsupported = Boolean(
    Number(sideAmounts?.left || 0) > 0 || Number(sideAmounts?.right || 0) > 0,
  );
}

function updateKiraEyeRig(t) {
  if (!activeKiraEyeRig || !activeAvatarIsKiraLike()) return;
  const matchedVoicePlaying = voicePlaybackMatchesActiveAvatar();
  let direction = activeKiraEyeRig.manualDirection || "idle";
  let sideTargets = activeKiraEyeRig.manualDirection
    ? kiraEyeSideTargets(activeKiraEyeRig.manualDirection)
    : {
        id: matchedVoicePlaying
          ? "actual_playback_centered_parallel_gaze"
          : KIRA_CENTERED_IDLE_EYE_FIT_ENABLED ? "idle_centered_socket_fit" : "idle_legacy_excursion",
        left: {
          yaw: Math.sin(t * 0.63) * (matchedVoicePlaying ? 0.1 : KIRA_CENTERED_IDLE_EYE_FIT_ENABLED ? 0.18 : 1.6)
            + Math.sin(t * 1.71) * (matchedVoicePlaying ? 0.025 : KIRA_CENTERED_IDLE_EYE_FIT_ENABLED ? 0.05 : 0.45),
          pitch: Math.sin(t * 0.47) * (matchedVoicePlaying ? 0.06 : KIRA_CENTERED_IDLE_EYE_FIT_ENABLED ? 0.1 : 0.75),
        },
        right: {
          yaw: Math.sin(t * 0.63) * (matchedVoicePlaying ? 0.1 : KIRA_CENTERED_IDLE_EYE_FIT_ENABLED ? 0.18 : 1.6)
            + Math.sin(t * 1.71) * (matchedVoicePlaying ? 0.025 : KIRA_CENTERED_IDLE_EYE_FIT_ENABLED ? 0.05 : 0.45),
          pitch: Math.sin(t * 0.47) * (matchedVoicePlaying ? 0.06 : KIRA_CENTERED_IDLE_EYE_FIT_ENABLED ? 0.1 : 0.75),
        },
      };
  if (!activeKiraEyeRig.manualDirection) direction = sideTargets.id;
  if (activeKiraEyeTestState) {
    const age = t - activeKiraEyeTestState.startedAt;
    const scaledAge = age * (activeKiraEyeTestState.plannedSeconds / activeKiraEyeTestState.seconds);
    const phase = kiraEyeExamPhaseAt(scaledAge);
    activeKiraEyeTestState.phase = phase.id;
    direction = phase.id;
    sideTargets = kiraEyeSideTargets(direction);
    if (phase.complete || age >= activeKiraEyeTestState.seconds) {
      activeKiraEyeTestState.completed = true;
      activeKiraEyeTestState = null;
      direction = "center";
      sideTargets = kiraEyeSideTargets("center");
    }
  }
  applyKiraIrisSurfaceGaze(activeKiraEyeRig.irises.left, sideTargets.left);
  applyKiraIrisSurfaceGaze(activeKiraEyeRig.irises.right, sideTargets.right);
  applyKiraBlink({ left: 0, right: 0 });
  activeKiraEyeRig.direction = direction;
  activeKiraEyeRig.blinking = false;
}

function kiraEyeBindingProbe() {
  if (!activeKiraEyeRig) {
    return {
      active: false,
      enabled: KIRA_LIVE_EYE_RIG_ENABLED,
      version: KIRA_EYE_CONTROL_EXAM_VERSION,
      defaultEnabled: true,
      optOutFlag: "?kiraEyeRig=off",
      explicitVersionFlag: "?kiraEyeRig=v3.3",
    };
  }
  activeKiraEyeRig.avatarRoot.updateMatrixWorld(true);
  const nodes = activeKiraEyeRig.nodes;
  const currentDistance = eyeCenterToHeadDistance(nodes, activeKiraEyeRig.headBone);
  const leftLocal = nodes.leftSocket?.position || null;
  const rightLocal = nodes.rightSocket?.position || null;
  const vector = (node) => {
    if (!node) return null;
    const point = node.getWorldPosition(new THREE.Vector3());
    return { x: Number(point.x.toFixed(6)), y: Number(point.y.toFixed(6)), z: Number(point.z.toFixed(6)) };
  };
  const localVector = (node) => node ? {
    x: Number(node.position.x.toFixed(8)),
    y: Number(node.position.y.toFixed(8)),
    z: Number(node.position.z.toFixed(8)),
  } : null;
  const forward = (node) => {
    if (!node) return null;
    const direction = new THREE.Vector3(0, 0, 1).applyQuaternion(node.getWorldQuaternion(new THREE.Quaternion())).normalize();
    return { x: Number(direction.x.toFixed(6)), y: Number(direction.y.toFixed(6)), z: Number(direction.z.toFixed(6)) };
  };
  const meshAudit = (node) => {
    if (!node?.isMesh) return null;
    const materials = (Array.isArray(node.material) ? node.material : [node.material]).filter(Boolean);
    node.geometry?.computeBoundingBox?.();
    const box = node.geometry?.boundingBox;
    return {
      visible: node.visible,
      renderOrder: node.renderOrder,
      frustumCulled: node.frustumCulled,
      positionCount: node.geometry?.attributes?.position?.count || 0,
      localBounds: box ? {
        min: box.min.toArray().map((value) => Number(value.toFixed(8))),
        max: box.max.toArray().map((value) => Number(value.toFixed(8))),
      } : null,
      materials: materials.map((material) => ({
        name: material.name || "",
        visible: material.visible,
        side: material.side,
        opacity: material.opacity,
        transparent: material.transparent,
        depthTest: material.depthTest,
        depthWrite: material.depthWrite,
        color: material.color ? `#${material.color.getHexString()}` : null,
        map: material.map ? {
          name: material.map.name || "",
          imageWidth: material.map.image?.width || 0,
          imageHeight: material.map.image?.height || 0,
        } : null,
      })),
    };
  };
  return {
    active: true,
    version: activeKiraEyeRig.version,
    modelUrl: activeKiraEyeRig.modelUrl,
    expectedSha256: activeKiraEyeRig.expectedSha256,
    defaultEnabled: true,
    optOutFlag: "?kiraEyeRig=off",
    explicitVersionFlag: "?kiraEyeRig=v3.3",
    runtimeVisualFit: activeKiraEyeRig.runtimeVisualFit,
    direction: activeKiraEyeRig.direction,
    blink: { ...activeKiraEyeRig.blink },
    blinkSupported: false,
    blinkUnsupportedRequest: activeKiraEyeRig.blinkUnsupportedRequest || null,
    gazeMethod: "fixed_socket_and_cornea_bounded_iris_surface_translation",
    leftIrisLocal: localVector(nodes.leftIris),
    rightIrisLocal: localVector(nodes.rightIris),
    leftIrisMeshAudit: meshAudit(nodes.leftIris),
    rightIrisMeshAudit: meshAudit(nodes.rightIris),
    leftScleraMeshAudit: meshAudit(nodes.leftSclera),
    leftCorneaMeshAudit: meshAudit(nodes.leftCornea),
    blinkMorphInfluences: Object.fromEntries((activeKiraEyeRig.lids || []).map(({ mesh, blinkIndex }) => [
      mesh?.name || "missing",
      blinkIndex >= 0 && mesh?.morphTargetInfluences
        ? Number((mesh.morphTargetInfluences[blinkIndex] || 0).toFixed(6))
        : null,
    ])),
    testRunning: !!activeKiraEyeTestState,
    testPhase: activeKiraEyeTestState?.phase || null,
    headBound: !!activeKiraEyeRig.headBone && activeKiraEyeRig.root.parent === activeKiraEyeRig.headBone,
    headBoneName: activeKiraEyeRig.headBone?.name || null,
    rootParentName: activeKiraEyeRig.root.parent?.name || null,
    leftSocketWorld: vector(nodes.leftSocket),
    rightSocketWorld: vector(nodes.rightSocket),
    leftSocketLocal: localVector(nodes.leftSocket),
    rightSocketLocal: localVector(nodes.rightSocket),
    leftScleraWorld: vector(nodes.leftSclera),
    rightScleraWorld: vector(nodes.rightSclera),
    leftScleraLocal: localVector(nodes.leftSclera),
    rightScleraLocal: localVector(nodes.rightSclera),
    leftCorneaWorld: vector(nodes.leftCornea),
    rightCorneaWorld: vector(nodes.rightCornea),
    leftCorneaLocal: localVector(nodes.leftCornea),
    rightCorneaLocal: localVector(nodes.rightCornea),
    leftEyeForward: forward(nodes.leftPivot),
    rightEyeForward: forward(nodes.rightPivot),
    socketFitAudit: leftLocal && rightLocal ? {
      interocularDistance: Number(leftLocal.distanceTo(rightLocal).toFixed(8)),
      centerlineOffset: Number(Math.abs(leftLocal.x + rightLocal.x).toFixed(10)),
      heightDelta: Number(Math.abs(leftLocal.z - rightLocal.z).toFixed(10)),
      depthDelta: Number(Math.abs(leftLocal.y - rightLocal.y).toFixed(10)),
      symmetricWithinOneMicrometer: Math.abs(leftLocal.x + rightLocal.x) < 0.000001
        && Math.abs(leftLocal.z - rightLocal.z) < 0.000001
        && Math.abs(leftLocal.y - rightLocal.y) < 0.000001,
      staticSocketTranslationApplied: false,
      supersededPreR6HeadApertureEstimate: {
        measuredCenterX: [-0.021, 0.021],
        measuredOpenBandZ: [1.1056, 1.109],
        authoredSocketCenterX: [-0.02232, 0.02232],
        authoredSocketCenterZ: 1.10676,
        usedForR6Placement: false,
        conclusion: "legacy pre-R6 estimate retained only for audit history; the reversible R6 eye-globe placement and rendered full-face proof are authoritative",
      },
      r6RuntimeVisualPlacement: activeKiraEyeRig.runtimeVisualFit?.eyeGlobeTranslation || null,
      r6VisualPlacementSourceOfTruth: "R7_v3_fixed_original_resolution_socket_and_profile_review",
      centeredIdleGazeFit: {
        active: KIRA_CENTERED_IDLE_EYE_FIT_ENABLED,
        method: "very small parallel iris-surface micro-saccade; socket, sclera, and cornea unchanged",
        optOutFlag: "?kiraEyeIdleFit=off",
      },
    } : null,
    headWorld: vector(activeKiraEyeRig.headBone),
    eyeCenterToHeadDistance: Number.isFinite(currentDistance) ? Number(currentDistance.toFixed(8)) : null,
    bindingDistanceDelta: Number.isFinite(currentDistance) && Number.isFinite(activeKiraEyeRig.initialEyeCenterToHeadDistance)
      ? Number(Math.abs(currentDistance - activeKiraEyeRig.initialEyeCenterToHeadDistance).toFixed(10))
      : null,
    oldProceduralNodeCount: countLegacyKiraEyeNodes(activeKiraEyeRig.avatarRoot),
    structural: activeKiraEyeRig.structural,
    error: activeKiraEyeRig.error || null,
  };
}

function focusStagedKiraEyes(offset = {}) {
  if (!activeKiraEyeRig?.nodes?.leftSocket || !activeKiraEyeRig?.nodes?.rightSocket) return false;
  activeKiraEyeRig.avatarRoot.updateMatrixWorld(true);
  const left = activeKiraEyeRig.nodes.leftSocket.getWorldPosition(new THREE.Vector3());
  const right = activeKiraEyeRig.nodes.rightSocket.getWorldPosition(new THREE.Vector3());
  const target = left.add(right).multiplyScalar(0.5);
  const orientation = activeKiraEyeRig.nodes.leftPivot.getWorldQuaternion(new THREE.Quaternion());
  const outward = new THREE.Vector3(0, 0, 1).applyQuaternion(orientation).normalize();
  const eye = target.clone().addScaledVector(outward, offset.distance ?? 0.34);
  eye.y += offset.y ?? 0.004;
  player.position.copy(eye);
  const dx = target.x - eye.x;
  const dz = target.z - eye.z;
  const dy = target.y - eye.y;
  player.yaw = Math.atan2(-dx, -dz);
  player.pitch = Math.atan2(dy, Math.max(0.001, Math.hypot(dx, dz)));
  updateCamera();
  return true;
}

function kiraHairMeshText(node) {
  const materials = Array.isArray(node.material) ? node.material : [node.material];
  const materialText = materials.map((material) => String(material?.name || "")).join(" ");
  return `${node.name || ""} ${materialText}`.toLowerCase();
}

function pruneKiraHairAttachmentMeshes(root) {
  const meshes = [];
  root.traverse((node) => {
    if (node.isMesh) meshes.push(node);
  });
  if (meshes.length <= 1) return { removed: 0, kept: meshes.length };
  const forcedKeep = new Set();
  if (/reddish hair|long_reddish_hair|downloaded reddish/i.test(root.name || "") && meshes.length === 4) {
    const wigMeshes = meshes.filter((mesh) => /wig/i.test(kiraHairMeshText(mesh)));
    forcedKeep.add(wigMeshes[0] || meshes[0]);
  }
  const removals = [];
  for (const mesh of meshes) {
    if (forcedKeep.size && !forcedKeep.has(mesh)) {
      removals.push(mesh);
      continue;
    }
    if (forcedKeep.has(mesh)) continue;
    const text = kiraHairMeshText(mesh);
    const likelyHair = /hair|wig|strand|lock|bang|scalp|card/.test(text);
    const likelyNonHair = /head|face|body|skin|eye|mouth|teeth|neck|bust|torso|mannequin/.test(text);
    if (!likelyHair || likelyNonHair) removals.push(mesh);
  }
  if (!removals.length || removals.length >= meshes.length) {
    root.userData.kiraHairPruneSkipped = removals.length >= meshes.length
      ? "all meshes looked non-hair; kept original attachment to avoid deleting the style"
      : "no non-hair meshes detected";
    return { removed: 0, kept: meshes.length };
  }
  for (const mesh of removals) {
    mesh.visible = false;
    mesh.userData.removedFromKiraHairAttachment = true;
    if (mesh.parent) mesh.parent.remove(mesh);
  }
  root.userData.kiraHairRemovedNonHairMeshes = removals.map((mesh) => mesh.name || "unnamed");
  return { removed: removals.length, kept: meshes.length - removals.length };
}

function tintKiraHairMaterials(root) {
  const target = new THREE.Color(0x7d3026);
  root.traverse((node) => {
    if (!node.isMesh) return;
    const tintMaterial = (material) => {
      if (!material) return material;
      const next = material.clone();
      if (next.color) next.color.lerp(target, 0.58);
      if (next.emissive) next.emissive.setHex(0x160504);
      if ("roughness" in next) next.roughness = Math.max(next.roughness ?? 0.5, 0.54);
      if ("metalness" in next) next.metalness = Math.min(next.metalness ?? 0, 0.08);
      return next;
    };
    node.material = Array.isArray(node.material) ? node.material.map(tintMaterial) : tintMaterial(node.material);
    node.castShadow = true;
    node.receiveShadow = true;
  });
}

function normalizeKiraHairClone(root) {
  root.updateMatrixWorld(true);
  const bounds = meshOnlyWorldBounds(root) || new THREE.Box3().setFromObject(root);
  if (bounds.isEmpty()) return new THREE.Vector3();
  const size = bounds.getSize(new THREE.Vector3());
  const scale = Math.min(
    size.x > 0 ? 0.3 / size.x : 1,
    size.y > 0 ? 0.39 / size.y : 1,
    size.z > 0 ? 0.34 / size.z : 1,
  );
  root.scale.multiplyScalar(scale);
  root.updateMatrixWorld(true);
  const scaledBounds = meshOnlyWorldBounds(root) || new THREE.Box3().setFromObject(root);
  const center = scaledBounds.getCenter(new THREE.Vector3());
  root.position.add(new THREE.Vector3(-center.x, -center.y - 0.055, -center.z));
  root.updateMatrixWorld(true);
  return (meshOnlyWorldBounds(root) || new THREE.Box3().setFromObject(root)).getSize(new THREE.Vector3());
}

function attachKiraReddishHair(root) {
  if (!root || !activeAvatarIsKiraLike()) return;
  if (!KIRA_REDDISH_HAIR_ENABLED) {
    clearKiraHairRig();
    homeWorldActivityStatus = {
      ...homeWorldActivityStatus,
      kiraReddishHair: {
        loaded: false,
        disabled: true,
        reason: "disabled_after_bad_asset_fit",
        url: KIRA_REDDISH_HAIR_MODEL_URL,
      },
    };
    if (activeMarker) {
      activeMarker.userData.kiraHair = {
        active: false,
        disabled: true,
        reason: "disabled_after_bad_asset_fit",
      };
    }
    return;
  }
  if (activeKiraHairRig?.avatarRoot === root) return;
  clearKiraHairRig();
  const attach = (source) => {
    if (!activeAvatarIsKiraLike() || activeAvatarRoot !== root) return;
    const anchor = new THREE.Group();
    anchor.name = "Kira reddish hair attachment anchor";
    const clone = source.clone(true);
    clone.name = "Kira downloaded reddish hair attachment";
    makeImportedAssetMaterials(clone);
    const pruneStatus = pruneKiraHairAttachmentMeshes(clone);
    tintKiraHairMaterials(clone);
    const fittedSize = normalizeKiraHairClone(clone);
    anchor.add(clone);
    scene.add(anchor);
    activeKiraHairRig = {
      avatarRoot: root,
      root: anchor,
      clone,
      fittedSize,
      headBone: activeAvatarProceduralRig?.bones?.head || null,
      correction: new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, 0)),
      pruneStatus,
    };
    updateKiraHairRig(clock.elapsedTime);
    homeWorldActivityStatus = {
      ...homeWorldActivityStatus,
      kiraReddishHair: {
        loaded: true,
        url: KIRA_REDDISH_HAIR_MODEL_URL,
        fittedSize: {
          x: Number(fittedSize.x.toFixed(3)),
          y: Number(fittedSize.y.toFixed(3)),
          z: Number(fittedSize.z.toFixed(3)),
        },
        pruneStatus,
      },
    };
    if (activeMarker) {
      activeMarker.userData.kiraHair = {
        active: true,
        url: KIRA_REDDISH_HAIR_MODEL_URL,
        color: "reddish auburn",
        temporaryAttachment: true,
        pruneStatus,
      };
    }
  };
  if (kiraHairReferenceSource) {
    attach(kiraHairReferenceSource);
    return;
  }
  if (kiraHairReferenceLoading) return;
  kiraHairReferenceLoading = true;
  gltfLoader.load(
    KIRA_REDDISH_HAIR_MODEL_URL,
    (gltf) => {
      kiraHairReferenceSource = gltf.scene;
      kiraHairReferenceLoading = false;
      attach(kiraHairReferenceSource);
    },
    undefined,
    (error) => {
      kiraHairReferenceLoading = false;
      homeWorldActivityStatus = {
        ...homeWorldActivityStatus,
        kiraReddishHair: {
          ...homeWorldActivityStatus.kiraReddishHair,
          loaded: false,
          error: error?.message || String(error),
        },
      };
      console.warn("Could not load Kira reddish hair model", error);
    },
  );
}

function updateKiraHairRig(t) {
  if (!activeKiraHairRig || !activeAvatarIsKiraLike()) return;
  const rig = activeKiraHairRig;
  const headBone = rig.headBone || activeAvatarProceduralRig?.bones?.head || null;
  const anchor = rig.root;
  if (headBone) {
    const headPosition = new THREE.Vector3();
    const headQuaternion = new THREE.Quaternion();
    headBone.getWorldPosition(headPosition);
    headBone.getWorldQuaternion(headQuaternion);
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(headQuaternion).multiplyScalar(0.048);
    const forward = new THREE.Vector3(0, 0, 1).applyQuaternion(headQuaternion).multiplyScalar(0.012);
    anchor.position.copy(headPosition).add(up).add(forward);
    anchor.quaternion.copy(headQuaternion).multiply(rig.correction);
  } else if (activeAvatarRoot) {
    const rootPosition = new THREE.Vector3();
    activeAvatarRoot.getWorldPosition(rootPosition);
    anchor.position.copy(rootPosition).add(new THREE.Vector3(0, 1.535, 0.045));
    anchor.quaternion.setFromEuler(new THREE.Euler(0, activeAvatarRoot.rotation.y + Math.PI, Math.sin(t * 0.9) * 0.006));
  }
  anchor.rotateZ(Math.sin(t * 0.9) * 0.006);
}

function makeRuntimeMarinetteTorsoGeometry(root) {
  const geometry = new THREE.BufferGeometry();
  const segments = 28;
  const rings = [
    { y: 0.72, rx: 0.155, rz: 0.088 },
    { y: 0.86, rx: 0.178, rz: 0.105 },
    { y: 1.00, rx: 0.128, rz: 0.088 },
    { y: 1.13, rx: 0.158, rz: 0.098 },
    { y: 1.24, rx: 0.205, rz: 0.086 },
  ];
  const positions = [];
  const indices = [];
  for (const ring of rings) {
    for (let i = 0; i < segments; i += 1) {
      const angle = (i / segments) * Math.PI * 2;
      const x = Math.cos(angle) * ring.rx;
      const z = Math.sin(angle) * ring.rz - 0.005;
      const p = markerSpaceToAvatarRootLocal(root, x, ring.y, z);
      positions.push(p.x, p.y, p.z);
    }
  }
  for (let r = 0; r < rings.length - 1; r += 1) {
    for (let i = 0; i < segments; i += 1) {
      const a = r * segments + i;
      const b = r * segments + ((i + 1) % segments);
      const c = (r + 1) * segments + i;
      const d = (r + 1) * segments + ((i + 1) % segments);
      indices.push(a, c, b, b, c, d);
    }
  }
  const bottomCenter = positions.length / 3;
  const bottom = markerSpaceToAvatarRootLocal(root, 0, rings[0].y - 0.005, -0.005);
  positions.push(bottom.x, bottom.y, bottom.z);
  const topCenter = positions.length / 3;
  const top = markerSpaceToAvatarRootLocal(root, 0, rings[rings.length - 1].y + 0.004, -0.005);
  positions.push(top.x, top.y, top.z);
  for (let i = 0; i < segments; i += 1) {
    indices.push(bottomCenter, (i + 1) % segments, i);
    const row = (rings.length - 1) * segments;
    indices.push(topCenter, row + i, row + ((i + 1) % segments));
  }
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function collectRuntimeMarinetteAccessoryRig(root) {
  const rig = { rig: null, eyes: [], lids: [], mouth: null, hairSway: null, fingers: [] };
  root.traverse((node) => {
    if (!node.isMesh) return;
    const name = String(node.name || "").toLowerCase();
    if (!name.includes("marinette_single_body")) return;
    node.userData.basePosition = node.position.clone();
    node.userData.baseScale = node.scale.clone();
    node.userData.baseRotation = node.rotation.clone();
    if (name.includes("eye_white") || name.includes("iris")) rig.eyes.push(node);
    if (name.includes("blink_lid")) rig.lids.push(node);
    if (name.includes("mouth_viseme")) rig.mouth = node;
    if (name.includes("hair_") || name.includes("pigtail") || name.includes("bang")) rig.hairSway = node;
  });
  return rig.eyes.length || rig.lids.length || rig.mouth || rig.hairSway ? rig : null;
}

function addRuntimeMarinetteEnhancements(root) {
  const label = (activeMarker?.userData?.label || "").toLowerCase();
  if (!label.includes("ladybug") && !label.includes("marinette")) return;

  harmonizeRuntimeMarinetteSkin(root);

  if (root.userData.useGenericProceduralRigForMarinette) {
    if (!root.userData.marinetteSilhouetteTuned) {
      root.scale.x *= 0.9;
      root.scale.z *= 0.94;
      root.userData.marinetteSilhouetteTuned = true;
    }
    root.userData.runtimeRig = collectRuntimeMarinetteAccessoryRig(root);
    if (activeMarker) {
      activeMarker.userData.marinetteRuntimeRepair = {
        rebuiltBaseBody: true,
        genericProceduralRig: true,
        shapedTorsoOverlaySkipped: true,
        silhouetteTuned: true,
        singleBodyAccessoryRig: !!root.userData.runtimeRig,
      };
    }
    return;
  }

  let hiddenArtifacts = 0;
  root.traverse((node) => {
    if (!node.isMesh) return;
    const name = String(node.name || "").toLowerCase();
    if (name.includes("shared_neck") || name.includes("active_neutral_smooth_body_shell")) {
      node.visible = false;
      node.userData.hiddenByRuntimeMarinetteRepair = true;
      hiddenArtifacts += 1;
    }
  });

  const skinMat = new THREE.MeshStandardMaterial({ color: MARINETTE_SKIN_COLOR, roughness: 0.52, metalness: 0.0 });
  const neckBlend = null;

  const torso = new THREE.Mesh(makeRuntimeMarinetteTorsoGeometry(root), skinMat);
  torso.name = "runtime_marinette_shaped_torso_shell";
  torso.castShadow = true;
  torso.receiveShadow = true;
  root.add(torso);

  root.userData.runtimeRig = {
    rig: null,
    eyes: [],
    lids: [],
    mouth: null,
    hairSway: null,
    neckBlend,
    bodyShape: torso,
  };
  if (activeMarker) {
    activeMarker.userData.marinetteRuntimeRepair = {
      hiddenArtifacts,
      singleNeckBlend: false,
      shapedTorso: true,
    };
  }
}

function restoreSpiderHeroMaterialBrightness(root, label = "") {
  const name = String(label || "").toLowerCase();
  if (!name.includes("spider") && !name.includes("gwen") && !name.includes("peter parker")) return;
  const targetPeterRed = new THREE.Color(0xff665b);
  const targetPeterBlue = new THREE.Color(0x5a92ff);
  root.traverse((node) => {
    if (!node.isMesh || !node.material) return;
    const materialsToCheck = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materialsToCheck) {
      if (!material?.color) continue;
      const c = material.color;
      const hsl = {};
      c.getHSL(hsl);
      const redDominant = c.r > c.g * 1.35 && c.r > c.b * 1.08;
      const blueDominant = c.b > c.r * 1.08 && c.b > c.g * 0.8;
      const nearWhite = c.r > 0.52 && c.g > 0.52 && c.b > 0.52;
      if (name.includes("peter") && redDominant) {
        c.lerp(targetPeterRed, 0.92);
        c.getHSL(hsl);
        if (hsl.l < 0.62) c.setHSL(hsl.h, Math.max(hsl.s, 0.82), 0.62);
        if (material.emissive) material.emissive.copy(c).multiplyScalar(0.16);
      } else if (name.includes("peter") && blueDominant) {
        c.lerp(targetPeterBlue, 0.82);
        c.getHSL(hsl);
        if (hsl.l < 0.48) c.setHSL(hsl.h, Math.max(hsl.s, 0.68), 0.48);
        if (material.emissive) material.emissive.copy(c).multiplyScalar(0.1);
      } else if (name.includes("gwen") && nearWhite) {
        c.lerp(new THREE.Color(0xf1f4f6), 0.34);
      }
      material.roughness = Math.max(material.roughness ?? 0.5, 0.38);
      material.needsUpdate = true;
    }
  });
  if (activeMarker) activeMarker.userData.spiderHeroMaterialRepair = true;
}

function loadActiveModel(shellState, position) {
  if (!shellState.active_model_url || shellState.active_model_url === activeAvatarModelUrl) return;
  const requestedModelUrl = shellState.active_model_url;
  const requestGeneration = ++activeAvatarModelLoadGeneration;
  activeAvatarModelUrl = requestedModelUrl;
  gltfLoader.load(requestedModelUrl, (gltf) => {
    if (!isCurrentAvatarModelLoad({
      requestGeneration,
      currentGeneration: activeAvatarModelLoadGeneration,
      requestedUrl: requestedModelUrl,
      currentUrl: activeAvatarModelUrl,
      markerPresent: !!activeMarker,
    })) return;
    if (activeAvatarRoot) {
      clearKiraExistingMouthLipSync();
      activeMarker.remove(activeAvatarRoot);
    }
    activeAvatarMixer = null;
    activeAvatarProceduralRig = null;
    activeAvatarRoot = gltf.scene;
    activeAvatarRoot.traverse(cleanActiveAvatarModelNode);
    const bounds = new THREE.Box3().setFromObject(activeAvatarRoot);
    const size = bounds.getSize(new THREE.Vector3());
    activeAvatarRoot.scale.setScalar(size.y > 0 ? 1.62 / size.y : 1);
    const scaledBounds = new THREE.Box3().setFromObject(activeAvatarRoot);
    const center = scaledBounds.getCenter(new THREE.Vector3());
    activeAvatarRoot.position.set(-center.x, -scaledBounds.min.y, -center.z);
    activeAvatarRoot.userData.baseY = activeAvatarRoot.position.y;
    activeAvatarRoot.userData.visualGroundCorrectionY = 0;
    activeAvatarRoot.userData.lastVisualGroundCalibrationAt = -Infinity;
    activeAvatarRoot.userData.forwardYawOffset = activeAvatarForwardYawOffsetForLabel(activeMarker?.userData?.label || "");
    activeAvatarRoot.rotation.y = activeAvatarRoot.userData.forwardYawOffset;
    activeMarker.position.copy(position);
    activeMarker.add(activeAvatarRoot);
    activeAvatarRoot.userData.runtimeRig = null;
    activeAvatarRoot.userData.clips = gltf.animations || [];
    activeAvatarProceduralRig = collectActiveAvatarProceduralRig(activeAvatarRoot, gltf.animations || []);
    const hasMixamoRig = Object.values(activeAvatarProceduralRig?.bones || {}).some((bone) => String(bone?.name || "").toLowerCase().includes("mixamorig"));
    activeAvatarRoot.userData.useGenericProceduralRigForMarinette = activeAvatarIsMarinetteLike() && hasMixamoRig && !gltf.animations?.length;
    addRuntimeMarinetteEnhancements(activeAvatarRoot);
    harmonizeRuntimeKiraAdultSkin(activeAvatarRoot);
    attachKiraExistingMouthLipSync(activeAvatarRoot);
    ensureKiraEyeRig(activeAvatarRoot);
    attachKiraReddishHair(activeAvatarRoot);
    restoreSpiderHeroMaterialBrightness(activeAvatarRoot, activeMarker?.userData?.label || "");
    activeMarker.userData.proceduralRig = activeAvatarProceduralRig?.usable ? activeAvatarProceduralRig.id : null;
    activeMarker.userData.activeModelHasWalkClip = !!activeAvatarProceduralRig?.hasWalkClip;
    activeMarker.userData.activeModelNeedsProceduralWalk = !!activeAvatarProceduralRig?.usable && (!activeAvatarProceduralRig?.hasWalkClip || activeAvatarUsesProceduralWalkOverride());
    activeMarker.userData.proceduralWalkOverride = activeAvatarUsesProceduralWalkOverride();
    activeMarker.userData.useGenericProceduralRigForMarinette = !!activeAvatarRoot.userData.useGenericProceduralRigForMarinette;
    if (activePoseSprite) activePoseSprite.visible = false;
    if (gltf.animations?.length && fallbackActiveClip(gltf.animations) && !activeAvatarUsesProceduralWalkOverride()) {
      activeAvatarMixer = new THREE.AnimationMixer(activeAvatarRoot);
      playActiveClip(gltf.animations);
    }
  }, undefined, () => {
    if (!isCurrentAvatarModelLoad({
      requestGeneration,
      currentGeneration: activeAvatarModelLoadGeneration,
      requestedUrl: requestedModelUrl,
      currentUrl: activeAvatarModelUrl,
      markerPresent: !!activeMarker,
    })) return;
    activeAvatarModelUrl = "";
    if (shellState.active_pose_manifest_url) loadActivePoseManifest(shellState, position);
  });
}

function poseNameForActiveAction(t) {
  if (activeAvatarAction === "wave") return Math.floor(t * 3.2) % 2 ? "wave_1" : "wave_2";
  if (activeAvatarAction === "talking") return Math.floor(t * 2.8) % 2 ? "talking" : "neutral";
  if (Math.floor(t) % 12 === 8) return "look_left";
  if (Math.floor(t) % 12 === 9) return "look_right";
  return "neutral";
}

function updateActivePoseSprite(t) {
  if (!activePoseSprite?.visible || !activePoseTextures.size) return;
  const forms = [...new Set([...activePoseTextures.keys()].map((key) => key.split(":", 1)[0]))];
  const form = forms.includes(activeAvatarForm) ? activeAvatarForm : forms.includes("civilian") ? "civilian" : forms[0];
  const pose = poseNameForActiveAction(t);
  const key = activePoseTextures.has(`${form}:${pose}`) ? `${form}:${pose}` : `${form}:neutral`;
  const texture = activePoseTextures.get(key) || activePoseTextures.values().next().value;
  if (!texture || key === activePoseKey) return;
  activePoseKey = key;
  activePoseMaterial.map = texture;
  activePoseMaterial.needsUpdate = true;
  const aspect = texture.image?.width && texture.image?.height ? texture.image.width / texture.image.height : 0.55;
  activePoseSprite.scale.set(2.15 * aspect, 2.15, 1);
}

function updateRuntimeMarinetteRig(t, moving) {
  const runtimeRig = activeAvatarRoot?.userData?.runtimeRig;
  if (!runtimeRig) return;
  const blinkCycle = t % 4.6;
  const blink = blinkCycle < 0.12 || (blinkCycle > 2.42 && blinkCycle < 2.52);
  for (const lid of runtimeRig.lids || []) {
    const baseScale = lid.userData.baseScale || lid.scale;
    const basePosition = lid.userData.basePosition || lid.position;
    lid.scale.y = baseScale.y * (blink ? 5.2 : 1);
    lid.position.y = basePosition.y + (blink ? -0.008 : 0);
  }
  for (const eye of runtimeRig.eyes || []) {
    const baseScale = eye.userData.baseScale || eye.scale;
    eye.scale.y = baseScale.y * (blink ? 0.18 : 1);
  }

  const lookYaw = Math.sin(t * 0.47) * 0.055 + (moving ? Math.sin(t * 1.1) * 0.018 : 0);
  if (runtimeRig.rig) {
    runtimeRig.rig.rotation.y = THREE.MathUtils.lerp(runtimeRig.rig.rotation.y, lookYaw, 0.08);
    runtimeRig.rig.rotation.x = THREE.MathUtils.lerp(runtimeRig.rig.rotation.x, moving ? -0.012 : Math.sin(t * 0.31) * 0.01, 0.06);
  }
  if (runtimeRig.neckBlend) {
    runtimeRig.neckBlend.rotation.y = THREE.MathUtils.lerp(runtimeRig.neckBlend.rotation.y, lookYaw * 0.45, 0.08);
  }

  const speaking = activeAvatarAction === "talking" || !!activeDoorInteraction;
  const speechPulse = speaking ? (Math.sin(t * 13.0) + 1) * 0.5 : 0.08;
  if (runtimeRig.mouth) {
    const baseScale = runtimeRig.mouth.userData.baseScale || runtimeRig.mouth.scale;
    const basePosition = runtimeRig.mouth.userData.basePosition || runtimeRig.mouth.position;
    runtimeRig.mouth.scale.y = baseScale.y * (0.65 + speechPulse * 2.4);
    runtimeRig.mouth.position.y = basePosition.y - speechPulse * 0.006;
  }

  if (runtimeRig.hairSway) {
    const baseRotation = runtimeRig.hairSway.userData?.baseRotation || runtimeRig.hairSway.rotation;
    runtimeRig.hairSway.rotation.z = baseRotation.z + Math.sin(t * (moving ? 4.1 : 1.2)) * (moving ? 0.035 : 0.014);
    runtimeRig.hairSway.rotation.x = baseRotation.x + Math.sin(t * 1.7) * 0.008;
  }
  for (const finger of runtimeRig.fingers || []) {
    const phase = t * (moving ? 5.5 : 2.2) + finger.userData.index * 0.7;
    finger.rotation.x = Math.sin(phase) * (activeAvatarAction === "talking" ? 0.22 : 0.08);
  }
}

const ACTIVE_AVATAR_PROCEDURAL_RIG_ID = "generic_humanoid_v1";

function activeAvatarClipCanDriveWalk(clips) {
  return safeActiveClips(clips).some((clip) => /walk|run|jog|locomotion|stride/i.test(clip.name || ""));
}

function activeAvatarForwardYawOffsetForLabel(label) {
  return Math.PI;
}

function activeAvatarProceduralNameInfo(node) {
  const raw = String(node?.name || "").toLowerCase();
  return {
    raw,
    compact: raw.replace(/[^a-z0-9]/g, ""),
  };
}

function activeAvatarProceduralSideMatches(info, side) {
  if (!side) return true;
  const raw = info.raw;
  const compact = info.compact;
  const tokens = raw.split(/[^a-z0-9]+/).filter(Boolean);
  const suffixToken = tokens[tokens.length - 1] || "";
  if (side === "L") {
    return compact.includes("left")
      || tokens.includes("l")
      || suffixToken === "l"
      || suffixToken.startsWith("l0")
      || /(^|[._:\-\s])l([._:\-\s]|\d|$)/.test(raw)
      || /_l($|[._:\-\s]|\d)/.test(raw)
      || /\.l($|[._:\-\s]|\d)/.test(raw);
  }
  if (side === "R") {
    return compact.includes("right")
      || tokens.includes("r")
      || suffixToken === "r"
      || suffixToken.startsWith("r0")
      || /(^|[._:\-\s])r([._:\-\s]|\d|$)/.test(raw)
      || /_r($|[._:\-\s]|\d)/.test(raw)
      || /\.r($|[._:\-\s]|\d)/.test(raw);
  }
  return true;
}

function activeAvatarProceduralFindBone(root, specs) {
  if (!root) return null;
  let best = null;
  root.traverse((node) => {
    if (!node.isBone) return;
    const info = activeAvatarProceduralNameInfo(node);
    for (const spec of specs) {
      if (!activeAvatarProceduralSideMatches(info, spec.side)) continue;
      const reject = spec.reject || [];
      if (reject.some((term) => info.compact.includes(term))) continue;
      const any = spec.any || [];
      if (any.length && !any.some((term) => info.compact.includes(term))) continue;
      const all = spec.all || [];
      if (all.length && !all.every((term) => info.compact.includes(term))) continue;
      const prefer = spec.prefer || [];
      const score = any.filter((term) => info.compact.includes(term)).length
        + all.length * 3
        + prefer.filter((term) => info.compact.includes(term)).length * 2
        - info.compact.length * 0.001;
      if (!best || score > best.score) best = { node, score };
    }
  });
  return best?.node || null;
}

function activeAvatarProceduralCollectFingers(root, side) {
  const fingers = { thumb: [], index: [], middle: [], ring: [], pinky: [] };
  if (!root) return fingers;
  root.traverse((node) => {
    if (!node.isBone) return;
    const info = activeAvatarProceduralNameInfo(node);
    if (!activeAvatarProceduralSideMatches(info, side)) return;
    // Terminal *_end bones do not deform another phalanx. Excluding them keeps
    // finger tests and curls tied to the four real articulated finger bones.
    if (info.compact.includes("end")) return;
    for (const finger of Object.keys(fingers)) {
      if (info.compact.includes(finger)) fingers[finger].push(node);
    }
  });
  for (const list of Object.values(fingers)) {
    list.sort((a, b) => activeAvatarProceduralNameInfo(a).compact.localeCompare(activeAvatarProceduralNameInfo(b).compact));
  }
  return fingers;
}

function collectActiveAvatarProceduralRig(root, clips = []) {
  const bones = {
    hips: activeAvatarProceduralFindBone(root, [{ any: ["hips", "pelvis"], reject: ["helper", "control"] }]),
    spine: activeAvatarProceduralFindBone(root, [{ any: ["spine", "chest", "upperchest"], prefer: ["spine2", "chest"], reject: ["helper", "control"] }]),
    neck: activeAvatarProceduralFindBone(root, [{ any: ["neck"], reject: ["helper", "control"] }]),
    head: activeAvatarProceduralFindBone(root, [{ any: ["head"], reject: ["helper", "control"] }]),
    leftUpperArm: activeAvatarProceduralFindBone(root, [{ side: "L", any: ["leftarm", "upperarm", "uparm", "shoulder"], reject: ["forearm", "lowerarm", "lower", "hand", "finger", "twist"] }]),
    leftForearm: activeAvatarProceduralFindBone(root, [{ side: "L", any: ["leftforearm", "leftlowerarm", "forearm", "lowerarm"], reject: ["hand", "finger", "twist"] }]),
    leftHand: activeAvatarProceduralFindBone(root, [{ side: "L", any: ["lefthand", "hand", "wrist"], reject: ["thumb", "index", "middle", "ring", "pinky", "finger"] }]),
    rightUpperArm: activeAvatarProceduralFindBone(root, [{ side: "R", any: ["rightarm", "upperarm", "uparm", "shoulder"], reject: ["forearm", "lowerarm", "lower", "hand", "finger", "twist"] }]),
    rightForearm: activeAvatarProceduralFindBone(root, [{ side: "R", any: ["rightforearm", "rightlowerarm", "forearm", "lowerarm"], reject: ["hand", "finger", "twist"] }]),
    rightHand: activeAvatarProceduralFindBone(root, [{ side: "R", any: ["righthand", "hand", "wrist"], reject: ["thumb", "index", "middle", "ring", "pinky", "finger"] }]),
    leftThigh: activeAvatarProceduralFindBone(root, [{ side: "L", any: ["leftupleg", "leftthigh", "upleg", "thigh", "upperleg"], reject: ["legroll", "lowerleg", "shin", "calf", "foot", "toe"] }]),
    leftShin: activeAvatarProceduralFindBone(root, [{ side: "L", any: ["leftleg", "leftlowerleg", "leftshin", "lowerleg", "shin", "calf"], reject: ["upleg", "upperleg", "thigh", "foot", "toe"] }]),
    leftFoot: activeAvatarProceduralFindBone(root, [{ side: "L", any: ["leftfoot", "foot", "ankle"], reject: ["toe"] }]),
    leftToe: activeAvatarProceduralFindBone(root, [{ side: "L", any: ["lefttoebase", "toebase", "toe"], reject: ["end", "helper", "control"] }]),
    rightThigh: activeAvatarProceduralFindBone(root, [{ side: "R", any: ["rightupleg", "rightthigh", "upleg", "thigh", "upperleg"], reject: ["legroll", "lowerleg", "shin", "calf", "foot", "toe"] }]),
    rightShin: activeAvatarProceduralFindBone(root, [{ side: "R", any: ["rightleg", "rightlowerleg", "rightshin", "lowerleg", "shin", "calf"], reject: ["upleg", "upperleg", "thigh", "foot", "toe"] }]),
    rightFoot: activeAvatarProceduralFindBone(root, [{ side: "R", any: ["rightfoot", "foot", "ankle"], reject: ["toe"] }]),
    rightToe: activeAvatarProceduralFindBone(root, [{ side: "R", any: ["righttoebase", "toebase", "toe"], reject: ["end", "helper", "control"] }]),
  };
  const baseQuaternions = new Map();
  const nodesByUuid = new Map();
  root?.traverse((node) => {
    if (!node.isBone) return;
    baseQuaternions.set(node.uuid, node.quaternion.clone());
    nodesByUuid.set(node.uuid, node);
  });
  const hasArms = !!((bones.leftUpperArm && bones.leftForearm && bones.leftHand) || (bones.rightUpperArm && bones.rightForearm && bones.rightHand));
  const hasLegs = !!((bones.leftThigh && bones.leftShin && bones.leftFoot) || (bones.rightThigh && bones.rightShin && bones.rightFoot));
  return {
    id: ACTIVE_AVATAR_PROCEDURAL_RIG_ID,
    usable: hasArms || hasLegs,
    hasWalkClip: activeAvatarClipCanDriveWalk(clips),
    bones,
    fingers: {
      L: activeAvatarProceduralCollectFingers(root, "L"),
      R: activeAvatarProceduralCollectFingers(root, "R"),
    },
    baseQuaternions,
    nodesByUuid,
  };
}

function resetActiveAvatarProceduralRigPose(rig) {
  if (!rig?.baseQuaternions) return;
  for (const [uuid, quaternion] of rig.baseQuaternions.entries()) {
    const node = rig.nodesByUuid.get(uuid);
    if (node) node.quaternion.copy(quaternion);
  }
}

function activeAvatarProceduralRigDiagnostics() {
  const rig = activeAvatarProceduralRig;
  if (!rig) return null;
  const boneNames = {};
  const missing = [];
  for (const [key, bone] of Object.entries(rig.bones || {})) {
    boneNames[key] = bone?.name || null;
    if (!bone) missing.push(key);
  }
  const fingerCounts = {};
  for (const side of ["L", "R"]) {
    fingerCounts[side] = {};
    for (const [finger, bones] of Object.entries(rig.fingers?.[side] || {})) {
      fingerCounts[side][finger] = bones.length;
    }
  }
  return {
    id: rig.id,
    usable: !!rig.usable,
    hasWalkClip: !!rig.hasWalkClip,
    activeLabel: activeAvatarDisplayName(),
    spiderLike: activeAvatarIsSpiderLike(),
    driving: !!activeMarker?.userData?.proceduralRigDriving,
    gaitMode: activeMarker?.userData?.proceduralGaitMode || activeMarker?.userData?.gaitMode || null,
    boneNames,
    fingerCounts,
    missing,
  };
}

function curlActiveAvatarProceduralFingers(rig, side, amount) {
  const hand = rig?.fingers?.[side];
  if (!hand) return;
  const curl = THREE.MathUtils.clamp(amount, 0, 1);
  for (const [finger, bones] of Object.entries(hand)) {
    bones.forEach((bone, index) => {
      const isThumb = finger === "thumb";
      const strength = (isThumb ? 0.32 : 0.58) * curl * Math.max(0.35, 1 - index * 0.14);
      bone.rotation.x += strength;
      if (isThumb && index === 0) bone.rotation.z += side === "L" ? -0.18 * curl : 0.18 * curl;
    });
  }
}

function solveActiveAvatarProceduralLimb(upper, lower, effector, target, strength = 0.45) {
  if (!upper || !lower || !effector || !target) return;
  for (let i = 0; i < 2; i += 1) {
    rotateActiveAvatarBoneTowardTarget(lower, effector, target, strength);
    rotateActiveAvatarBoneTowardTarget(upper, effector, target, strength * 0.68);
  }
}

function applyKiraSchoolStudyPose(rig, t) {
  const posture = activeMarker?.userData?.postureState;
  if (!activeAvatarIsKiraLike() || !String(posture?.id || "").startsWith("attend_school")) return false;
  if (rig.bones.hips) rig.bones.hips.rotation.x += 0.16;
  if (rig.bones.spine) rig.bones.spine.rotation.x += 0.11;
  if (rig.bones.neck) rig.bones.neck.rotation.x -= 0.04 + Math.sin(t * 0.9) * 0.012;
  if (rig.bones.head) rig.bones.head.rotation.x -= 0.03 + Math.sin(t * 0.85) * 0.01;

  for (const item of [
    {
      side: "L",
      sideSign: 1,
      thigh: rig.bones.leftThigh,
      shin: rig.bones.leftShin,
      foot: rig.bones.leftFoot,
      upper: rig.bones.leftUpperArm,
      lower: rig.bones.leftForearm,
      hand: rig.bones.leftHand,
      handX: -0.18,
    },
    {
      side: "R",
      sideSign: -1,
      thigh: rig.bones.rightThigh,
      shin: rig.bones.rightShin,
      foot: rig.bones.rightFoot,
      upper: rig.bones.rightUpperArm,
      lower: rig.bones.rightForearm,
      hand: rig.bones.rightHand,
      handX: 0.18,
    },
  ]) {
    if (item.thigh) item.thigh.rotation.x += 1.02;
    if (item.shin) item.shin.rotation.x += 1.06;
    if (item.foot) item.foot.rotation.x -= 0.22;
    if (item.upper) {
      item.upper.rotation.z += item.sideSign * 0.96;
      item.upper.rotation.y += item.sideSign * 0.05;
      item.upper.rotation.x -= 0.18;
    }
    if (item.lower) {
      item.lower.rotation.z += item.sideSign * 0.03;
      item.lower.rotation.x += 0.52;
    }
    if (item.hand) {
      const handTarget = activeAvatarWorldOffset(item.handX, 0.78, -0.38);
      solveActiveAvatarProceduralLimb(item.upper, item.lower, item.hand, handTarget, 0.24);
    }
    curlActiveAvatarProceduralFingers(rig, item.side, 0.38);
  }

  if (activeMarker) {
    activeMarker.userData.proceduralRig = rig.id;
    activeMarker.userData.proceduralRigDriving = true;
    activeMarker.userData.proceduralGaitMode = "school_study_sit";
  }
  return true;
}

function applyKiraSleepPose(rig, t) {
  const posture = activeMarker?.userData?.postureState;
  if (!activeAvatarIsKiraLike() || !/kira_sleep_bed|kira_lie_bed|kira_lie_couch|kira_lie_ground/.test(String(posture?.id || ""))) return false;
  if (rig.bones.spine) rig.bones.spine.rotation.x += 0.04 + Math.sin(t * 0.42) * 0.01;
  if (rig.bones.neck) rig.bones.neck.rotation.y += Math.sin(t * 0.3) * 0.025;
  if (rig.bones.head) rig.bones.head.rotation.y += Math.sin(t * 0.28) * 0.03;
  for (const item of [
    {
      side: "L",
      sideSign: 1,
      thigh: rig.bones.leftThigh,
      shin: rig.bones.leftShin,
      foot: rig.bones.leftFoot,
      upper: rig.bones.leftUpperArm,
      lower: rig.bones.leftForearm,
      hand: rig.bones.leftHand,
      handX: -0.16,
      handZ: -0.12,
    },
    {
      side: "R",
      sideSign: -1,
      thigh: rig.bones.rightThigh,
      shin: rig.bones.rightShin,
      foot: rig.bones.rightFoot,
      upper: rig.bones.rightUpperArm,
      lower: rig.bones.rightForearm,
      hand: rig.bones.rightHand,
      handX: 0.16,
      handZ: -0.1,
    },
  ]) {
    if (item.thigh) item.thigh.rotation.x += 0.05 + item.sideSign * 0.025;
    if (item.shin) item.shin.rotation.x += 0.1;
    if (item.foot) item.foot.rotation.x -= 0.04;
    if (item.upper) {
      item.upper.rotation.z += item.sideSign * 0.58;
      item.upper.rotation.x -= 0.08;
    }
    if (item.lower) item.lower.rotation.x += 0.36;
    if (item.hand) {
      const handTarget = activeAvatarWorldOffset(item.handX, 0.78, item.handZ);
      solveActiveAvatarProceduralLimb(item.upper, item.lower, item.hand, handTarget, 0.18);
    }
    curlActiveAvatarProceduralFingers(rig, item.side, 0.42);
  }
  if (activeMarker) {
    activeMarker.userData.proceduralRig = rig.id;
    activeMarker.userData.proceduralRigDriving = true;
    activeMarker.userData.proceduralGaitMode = "kira_sleep";
    activeMarker.userData.dreamState = activeKiraDreamState;
  }
  return true;
}

function applyKiraVoluntaryBodyActionPose(rig, t) {
  if (!activeAvatarIsKiraLike()) return false;
  const action = String(activeAvatarAction || "").toLowerCase();
  if (!/^(raise_hand|push_up|sit)$/.test(action)) return false;

  if (action === "raise_hand") {
    if (rig.bones.leftUpperArm) {
      rig.bones.leftUpperArm.rotation.z -= 1.08;
      rig.bones.leftUpperArm.rotation.x += 0.12;
    }
    if (rig.bones.leftForearm) rig.bones.leftForearm.rotation.x += 0.18;
    if (rig.bones.leftHand) rig.bones.leftHand.rotation.z -= 0.08;
    curlActiveAvatarProceduralFingers(rig, "L", 0.12);
    curlActiveAvatarProceduralFingers(rig, "R", 0.08);
  } else if (action === "push_up") {
    if (rig.bones.spine) rig.bones.spine.rotation.x += 0.035;
    for (const item of [
      { side: "L", upper: rig.bones.leftUpperArm, lower: rig.bones.leftForearm, thigh: rig.bones.leftThigh, shin: rig.bones.leftShin },
      { side: "R", upper: rig.bones.rightUpperArm, lower: rig.bones.rightForearm, thigh: rig.bones.rightThigh, shin: rig.bones.rightShin },
    ]) {
      const pulse = 0.32 + (Math.sin(t * 2.4) + 1) * 0.12;
      if (item.upper) item.upper.rotation.z += (item.side === "L" ? 1 : -1) * 0.72;
      if (item.upper) item.upper.rotation.x -= pulse * 0.35;
      if (item.lower) item.lower.rotation.x += pulse;
      if (item.thigh) item.thigh.rotation.x -= 0.06;
      if (item.shin) item.shin.rotation.x -= 0.04;
      curlActiveAvatarProceduralFingers(rig, item.side, 0.24);
    }
  } else {
    for (const item of [
      { thigh: rig.bones.leftThigh, shin: rig.bones.leftShin, foot: rig.bones.leftFoot },
      { thigh: rig.bones.rightThigh, shin: rig.bones.rightShin, foot: rig.bones.rightFoot },
    ]) {
      if (item.thigh) item.thigh.rotation.x -= 1.02;
      if (item.shin) item.shin.rotation.x -= 1.08;
      if (item.foot) item.foot.rotation.x += 0.14;
    }
  }
  if (activeMarker) {
    activeMarker.userData.proceduralRig = rig.id;
    activeMarker.userData.proceduralRigDriving = true;
    activeMarker.userData.proceduralGaitMode = `voluntary_${action}_staged_unreviewed`;
    activeMarker.userData.armMotionEvidence = {
      mode: `voluntary_${action}_procedural_pose_v1`,
      objectContactClaimed: false,
      objectContactIkReservedForInteraction: true,
      visuallyReviewedThisSession: false,
    };
  }
  return true;
}

function startActiveAvatarKiraArmMobilityTest(seconds = 10) {
  if (!activeMarker || !activeAvatarIsKiraLike()) return false;
  clearActiveAvatarPracticeInteractions();
  activeKiraArmTestState = {
    startedAt: clock.elapsedTime,
    seconds,
    phases: ["relaxed_down", "reach_forward", "bend_elbows", "side_balance", "relaxed_down"],
  };
  activeMarker.userData.skillInteraction = "kira_arm_control";
  activeMarker.userData.gaitMode = null;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  setActiveAvatarAction("arm_control_test");
  recordMovementLearningAttempt({ skill: "arm_control", phase: "practice_started", target: "Kira relaxed arms and hand control" });
  return true;
}

function applyKiraArmMobilityPose(rig, t) {
  if (!activeAvatarIsKiraLike() || !activeKiraArmTestState) return false;
  const age = t - activeKiraArmTestState.startedAt;
  if (age > activeKiraArmTestState.seconds) {
    activeKiraArmTestState = null;
    if (activeMarker?.userData?.skillInteraction === "kira_arm_control") {
      activeMarker.userData.skillInteraction = null;
      setActiveAvatarAction("idle");
    }
    recordMovementLearningAttempt({ skill: "arm_control", phase: "practice_finished", target: "Kira relaxed arms and hand control" });
    return false;
  }
  const phaseIndex = Math.min(activeKiraArmTestState.phases.length - 1, Math.floor((age / activeKiraArmTestState.seconds) * activeKiraArmTestState.phases.length));
  const phaseName = activeKiraArmTestState.phases[phaseIndex] || "relaxed_down";
  if (rig.bones.spine) rig.bones.spine.rotation.x += 0.025;
  if (rig.bones.neck) rig.bones.neck.rotation.y += Math.sin(t * 0.7) * 0.03;
  for (const item of [
    { side: "L", sideSign: 1, upper: rig.bones.leftUpperArm, lower: rig.bones.leftForearm, hand: rig.bones.leftHand, x: -0.16 },
    { side: "R", sideSign: -1, upper: rig.bones.rightUpperArm, lower: rig.bones.rightForearm, hand: rig.bones.rightHand, x: 0.16 },
  ]) {
    let targetY = 0.66;
    let targetZ = -0.08;
    let targetX = item.x * 0.72;
    let upperZ = 0.68;
    let lowerX = 0.22;
    let curl = 0.42;
    if (phaseName === "reach_forward") {
      targetY = 0.98;
      targetZ = -0.48;
      targetX = item.x * 0.9;
      upperZ = 0.18;
      lowerX = 0.12;
      curl = 0.2;
    } else if (phaseName === "bend_elbows") {
      targetY = 0.88;
      targetZ = -0.22;
      targetX = item.x * 0.62;
      upperZ = 0.54;
      lowerX = 0.58;
      curl = 0.34;
    } else if (phaseName === "side_balance") {
      targetY = 0.78;
      targetZ = -0.05;
      targetX = item.x * 1.12;
      upperZ = 0.86;
      lowerX = 0.24;
      curl = 0.38;
    }
    if (item.upper) {
      item.upper.rotation.z += item.sideSign * upperZ;
      item.upper.rotation.x += -0.04 + Math.sin(t * 1.2) * 0.025;
    }
    if (item.lower) item.lower.rotation.x += lowerX;
    if (item.hand) {
      const target = activeAvatarWorldOffset(targetX, targetY, targetZ);
      solveActiveAvatarProceduralLimb(item.upper, item.lower, item.hand, target, 0.34);
    }
    curlActiveAvatarProceduralFingers(rig, item.side, curl);
  }
  if (activeMarker) {
    activeMarker.userData.proceduralRig = rig.id;
    activeMarker.userData.proceduralRigDriving = true;
    activeMarker.userData.proceduralGaitMode = `kira_arm_${phaseName}`;
  }
  return true;
}

function kiraDoctorRigContext(rig = activeAvatarProceduralRig) {
  const bones = {};
  for (const [key, bone] of Object.entries(rig?.bones || {})) bones[key] = !!bone;
  const fingerCounts = {};
  for (const side of ["L", "R"]) {
    fingerCounts[side] = {};
    for (const [finger, nodes] of Object.entries(rig?.fingers?.[side] || {})) {
      fingerCounts[side][finger] = nodes.length;
    }
  }
  return { bones, fingerCounts };
}

function kiraDoctorTargetNodes(rig, target) {
  if (target.joint) return rig?.bones?.[target.joint] ? [rig.bones[target.joint]] : [];
  if (!target.finger) return [];
  const [side, finger] = String(target.finger).split(":");
  return rig?.fingers?.[side]?.[finger] || [];
}

function applyKiraDoctorExamPhase(rig, phase, amount = 1) {
  const poseAmount = THREE.MathUtils.clamp(Number(amount) || 0, 0, 1);
  const missing = [];
  const touched = new Map();
  for (const target of phase.targets || []) {
    const nodes = kiraDoctorTargetNodes(rig, target);
    if (!nodes.length) {
      missing.push(target.joint || `finger:${target.finger}`);
      continue;
    }
    nodes.forEach((node) => {
      if (!touched.has(node.uuid)) touched.set(node.uuid, { node, before: node.quaternion.clone() });
      if (target.joint) {
        const axis = ["x", "y", "z"].includes(target.axis) ? target.axis : "x";
        node.rotation[axis] += Number(target.radians || 0) * poseAmount;
      } else {
        const index = nodes.indexOf(node);
        node.rotation.x += Number(target.radians || 0) * poseAmount * Math.max(0.34, 1 - index * 0.15);
        if (String(target.finger).endsWith(":thumb") && index === 0) {
          node.rotation.z += String(target.finger).startsWith("L:") ? -0.1 * poseAmount : 0.1 * poseAmount;
        }
      }
    });
  }
  let maxQuaternionDeltaRadians = 0;
  const changedJoints = [];
  for (const { node, before } of touched.values()) {
    const delta = before.angleTo(node.quaternion);
    maxQuaternionDeltaRadians = Math.max(maxQuaternionDeltaRadians, delta);
    if (delta > 0.002) changedJoints.push(node.name || node.uuid);
  }
  const passed = missing.length === 0 && changedJoints.length > 0 && maxQuaternionDeltaRadians >= 0.01;
  return {
    id: phase.id,
    label: phase.label,
    structurallySupported: missing.length === 0,
    executed: true,
    passed,
    status: missing.length ? "fail_missing_joint" : passed ? "pass_measured_joint_delta" : "fail_no_measured_joint_delta",
    missing: [...new Set(missing)],
    changedJointCount: changedJoints.length,
    changedJoints,
    maxQuaternionDeltaRadians: Number(maxQuaternionDeltaRadians.toFixed(6)),
  };
}

function probeKiraDoctorJointControl() {
  const rig = activeAvatarProceduralRig;
  if (!activeMarker || !activeAvatarIsKiraLike() || !rig?.usable) {
    return {
      version: KIRA_DOCTOR_BODY_EXAM_VERSION,
      passed: false,
      status: "fail_no_loaded_kira_rig",
      results: [],
    };
  }
  const results = [];
  for (const phase of KIRA_DOCTOR_JOINT_PHASES) {
    resetActiveAvatarProceduralRigPose(rig);
    results.push(applyKiraDoctorExamPhase(rig, phase, 1));
  }
  resetActiveAvatarProceduralRigPose(rig);
  const summary = summarizeExecutedExam(results);
  const report = {
    version: KIRA_DOCTOR_BODY_EXAM_VERSION,
    status: summary.allPassed ? "pass" : "fail_or_unsupported",
    summary,
    structural: buildKiraDoctorStructuralReport(kiraDoctorRigContext(rig)),
    results,
    visuallyReviewed: false,
    bodyRuntimeLoadedForProbe: true,
    mindOrLifeLoopActivatedByProbe: false,
    limitation: "This is a measured skeleton-control probe. It does not prove that every pose looks natural or that a route/posture completed.",
  };
  activeMarker.userData.lastDoctorBodyJointProbe = report;
  return report;
}

function startKiraDoctorBodyControlExam(options = {}) {
  if (!activeMarker || !activeAvatarIsKiraLike() || !activeAvatarProceduralRig?.usable) return false;
  clearActiveAvatarPracticeInteractions();
  const phaseSeconds = THREE.MathUtils.clamp(Number(options.phaseSeconds) || 0.8, 0.45, 2.5);
  activeKiraDoctorExamState = {
    version: KIRA_DOCTOR_BODY_EXAM_VERSION,
    startedAt: clock.elapsedTime,
    phaseSeconds,
    results: new Map(),
  };
  activeMarker.userData.doctorBodyExam = {
    running: true,
    version: KIRA_DOCTOR_BODY_EXAM_VERSION,
    phase: KIRA_DOCTOR_JOINT_PHASES[0]?.id || null,
    total: KIRA_DOCTOR_JOINT_PHASES.length,
    results: [],
  };
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  setActiveAvatarAction("doctor_body_control_exam");
  recordMovementLearningAttempt({
    skill: "doctor_body_control_exam",
    phase: "joint_exam_started",
    target: "Kira exact runtime skeleton",
    version: KIRA_DOCTOR_BODY_EXAM_VERSION,
  });
  return true;
}

function finishKiraDoctorBodyControlExam() {
  if (!activeKiraDoctorExamState || !activeMarker) return false;
  const results = KIRA_DOCTOR_JOINT_PHASES.map((phase) => (
    activeKiraDoctorExamState.results.get(phase.id) || {
      id: phase.id,
      label: phase.label,
      executed: false,
      passed: false,
      status: "fail_not_executed",
      missing: [],
    }
  ));
  const summary = summarizeExecutedExam(results);
  activeMarker.userData.doctorBodyExam = {
    running: false,
    version: KIRA_DOCTOR_BODY_EXAM_VERSION,
    summary,
    results,
    visuallyReviewed: false,
  };
  recordMovementLearningAttempt({
    skill: "doctor_body_control_exam",
    phase: "joint_exam_finished",
    target: "Kira exact runtime skeleton",
    version: KIRA_DOCTOR_BODY_EXAM_VERSION,
    passed: summary.passed,
    failed: summary.failed,
  });
  activeKiraDoctorExamState = null;
  setActiveAvatarAction("idle");
  return true;
}

function applyKiraDoctorBodyControlExamPose(rig, t) {
  if (!activeAvatarIsKiraLike() || !activeKiraDoctorExamState) return false;
  const age = Math.max(0, t - activeKiraDoctorExamState.startedAt);
  const index = Math.floor(age / activeKiraDoctorExamState.phaseSeconds);
  if (index >= KIRA_DOCTOR_JOINT_PHASES.length) {
    finishKiraDoctorBodyControlExam();
    return false;
  }
  const phase = KIRA_DOCTOR_JOINT_PHASES[index];
  const local = (age - index * activeKiraDoctorExamState.phaseSeconds) / activeKiraDoctorExamState.phaseSeconds;
  const amount = Math.sin(THREE.MathUtils.clamp(local, 0, 1) * Math.PI);
  const result = applyKiraDoctorExamPhase(rig, phase, amount);
  const previous = activeKiraDoctorExamState.results.get(phase.id);
  if (!previous || result.maxQuaternionDeltaRadians > (previous.maxQuaternionDeltaRadians || 0)) {
    activeKiraDoctorExamState.results.set(phase.id, result);
  }
  if (activeMarker) {
    activeMarker.userData.doctorBodyExam = {
      running: true,
      version: KIRA_DOCTOR_BODY_EXAM_VERSION,
      phase: phase.id,
      label: phase.label,
      index: index + 1,
      total: KIRA_DOCTOR_JOINT_PHASES.length,
      current: activeKiraDoctorExamState.results.get(phase.id),
      results: Array.from(activeKiraDoctorExamState.results.values()),
    };
    activeMarker.userData.proceduralRig = rig.id;
    activeMarker.userData.proceduralRigDriving = true;
    activeMarker.userData.proceduralGaitMode = `doctor_exam_${phase.id}`;
  }
  return true;
}

function applyKiraComfortFingerMotion(rig, comfort, locomotionBlend) {
  const strength = (1 - locomotionBlend) * Number(comfort?.fingerStrength || 0.035);
  if (strength <= 0.0001) return;
  const pulseIsRadians = comfort?.fingerPulseIsRadians === true;
  for (const side of ["L", "R"]) {
    for (const [finger, bones] of Object.entries(rig?.fingers?.[side] || {})) {
      const pulse = Number(comfort.fingerPulse?.[side]?.[finger] || 0);
      bones.forEach((bone, index) => {
        const delta = pulseIsRadians ? pulse : pulse * strength;
        bone.rotation.x += delta * Math.max(0.3, 1 - index * 0.17);
      });
    }
  }
}

function activeAvatarIdleMotionProfile() {
  if (!activeMarker) return { phase: 0.7, breathRate: 0.78, weightRate: 0.31 };
  if (activeMarker.userData.idleMotionProfile) return activeMarker.userData.idleMotionProfile;
  const label = String(activeMarker.userData.label || activeShellState?.active_candidate || "active-avatar");
  let hash = 2166136261;
  for (let index = 0; index < label.length; index += 1) {
    hash ^= label.charCodeAt(index);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  activeMarker.userData.idleMotionProfile = {
    phase: (hash / 0xffffffff) * Math.PI * 2,
    breathRate: 0.68 + ((hash >>> 8) % 19) / 100,
    weightRate: 0.25 + ((hash >>> 16) % 11) / 100,
    mode: "identity_seeded_low_frequency_idle_v1",
  };
  return activeMarker.userData.idleMotionProfile;
}

function activeAvatarAmbientMotionProfile() {
  if (!activeMarker) return buildAmbientMicroMovementProfile("active-avatar");
  if (activeMarker.userData.ambientMotionProfile) return activeMarker.userData.ambientMotionProfile;
  const identity = String(
    activeShellState?.active_candidate
      || activeMarker.userData.label
      || activeShellState?.active_label
      || "active-avatar",
  );
  activeMarker.userData.ambientMotionProfile = buildAmbientMicroMovementProfile(identity);
  return activeMarker.userData.ambientMotionProfile;
}

function activeAvatarHasDeliberatePoseOwner() {
  if (activeDoorInteraction || activePostureInteraction || activeFurnitureInteraction || activeSkillInteraction) return true;
  if (avatarDressingController?.phase) return true;
  return false;
}

function kiraComfortIdleStatus(t = clock.elapsedTime) {
  if (!activeMarker || !activeAvatarIsKiraLike() || !activeAvatarProceduralRig) return null;
  const profile = activeAvatarAmbientMotionProfile();
  const expressionAction = voicePlaybackMatchesActiveAvatar() ? "talking" : activeAvatarAction;
  const offsets = ambientMicroMovementFrame({
    seconds: t,
    identity: activeShellState?.active_candidate || activeMarker.userData.label || "kira",
    profile,
    action: activeAvatarAction,
    locomotionBlend: THREE.MathUtils.clamp(Number(activeMarker.userData?.locomotionBlend || 0), 0, 1),
    deliberateAction: activeAvatarHasDeliberatePoseOwner(),
    lipSyncActive: voicePlaybackMatchesActiveAvatar(),
    supportsExistingMouthSmile: !!activeKiraMouthLipSyncRig,
  });
  const rotation = (bone) => bone ? {
    x: Number(bone.rotation.x.toFixed(6)),
    y: Number(bone.rotation.y.toFixed(6)),
    z: Number(bone.rotation.z.toFixed(6)),
  } : null;
  return {
    mode: offsets.mode,
    action: activeAvatarAction,
    expressionAction,
    actualPlaybackExpression: voicePlaybackMatchesActiveAvatar(),
    bodyPosition: {
      x: Number(activeMarker.position.x.toFixed(6)),
      y: Number(activeMarker.position.y.toFixed(6)),
      z: Number(activeMarker.position.z.toFixed(6)),
    },
    rootTranslationRequested: offsets.rootTranslation,
    rootRotationRequested: offsets.rootRotation,
    scaleDeltaRequested: offsets.scaleDelta,
    suppression: offsets.suppression,
    existingMouthSmile: Number(offsets.face?.smile || 0),
    profile,
    offsets: {
      breath: Number(offsets.breath.toFixed(6)),
      weight: Number(offsets.weight.toFixed(6)),
      gaze: Number(offsets.gaze.toFixed(6)),
      gesture: Number(offsets.gesture.toFixed(6)),
      leftGesture: Number(offsets.leftGesture.toFixed(6)),
      rightGesture: Number(offsets.rightGesture.toFixed(6)),
      leftWristX: Number(offsets.leftWristX.toFixed(6)),
      rightWristX: Number(offsets.rightWristX.toFixed(6)),
      fingerStrength: Number(offsets.fingerStrength.toFixed(6)),
    },
    joints: {
      hips: rotation(activeAvatarProceduralRig.bones?.hips),
      spine: rotation(activeAvatarProceduralRig.bones?.spine),
      neck: rotation(activeAvatarProceduralRig.bones?.neck),
      head: rotation(activeAvatarProceduralRig.bones?.head),
      leftUpperArm: rotation(activeAvatarProceduralRig.bones?.leftUpperArm),
      leftForearm: rotation(activeAvatarProceduralRig.bones?.leftForearm),
      leftHand: rotation(activeAvatarProceduralRig.bones?.leftHand),
      rightUpperArm: rotation(activeAvatarProceduralRig.bones?.rightUpperArm),
      rightForearm: rotation(activeAvatarProceduralRig.bones?.rightForearm),
      rightHand: rotation(activeAvatarProceduralRig.bones?.rightHand),
      leftThumb: rotation(activeAvatarProceduralRig.fingers?.L?.thumb?.[0]),
      leftIndex: rotation(activeAvatarProceduralRig.fingers?.L?.index?.[0]),
      leftMiddle: rotation(activeAvatarProceduralRig.fingers?.L?.middle?.[0]),
      leftRing: rotation(activeAvatarProceduralRig.fingers?.L?.ring?.[0]),
      leftPinky: rotation(activeAvatarProceduralRig.fingers?.L?.pinky?.[0]),
      rightThumb: rotation(activeAvatarProceduralRig.fingers?.R?.thumb?.[0]),
      rightIndex: rotation(activeAvatarProceduralRig.fingers?.R?.index?.[0]),
      rightMiddle: rotation(activeAvatarProceduralRig.fingers?.R?.middle?.[0]),
      rightRing: rotation(activeAvatarProceduralRig.fingers?.R?.ring?.[0]),
      rightPinky: rotation(activeAvatarProceduralRig.fingers?.R?.pinky?.[0]),
      leftFoot: rotation(activeAvatarProceduralRig.bones?.leftFoot),
      rightFoot: rotation(activeAvatarProceduralRig.bones?.rightFoot),
      leftToe: rotation(activeAvatarProceduralRig.bones?.leftToe),
      rightToe: rotation(activeAvatarProceduralRig.bones?.rightToe),
    },
    planner: "none_comfort_motion_only_executes_current_body_action",
  };
}

function updateActiveAvatarProceduralRig(t) {
  const rig = activeAvatarProceduralRig;
  if (!rig?.usable || !activeAvatarRoot) return;
  if (activeAvatarIsMarinetteLike() && !activeAvatarUsesGenericProceduralRigForMarinette()) return;
  const action = String(activeAvatarAction || "idle").toLowerCase();
  const groundedLocomotion = activeAvatarActionIsGroundedLocomotion(action);
  if (rig.hasWalkClip && groundedLocomotion && activeAvatarMixer && !activeAvatarUsesProceduralWalkOverride()) return;
  const locomotionBlend = action === "swim_idle"
    ? 1
    : THREE.MathUtils.clamp(Number(activeMarker?.userData?.locomotionBlend || 0), 0, 1);
  const moving = locomotionBlend > 0.012 || action === "swim_idle";
  const phase = activeMarker?.userData?.walkCyclePhase ?? activeAvatarMovePhase;
  const isSpiderLike = activeAvatarIsSpiderLike();
  const isKiraLike = activeAvatarIsKiraLike();
  const gaitMode = activeMarker?.userData?.gaitMode || (action === "run" || action === "dodge" ? "run" : action === "jog" ? "jog" : "walk");
  const gaitScale = gaitMode === "run" ? 1.55 : gaitMode === "jog" ? 1.22 : 1.0;
  const idleProfile = activeAvatarIdleMotionProfile();
  const expressionAction = voicePlaybackMatchesActiveAvatar() ? "talking" : action;
  const comfortIdle = isKiraLike
    ? ambientMicroMovementFrame({
      seconds: t,
      identity: activeShellState?.active_candidate || activeMarker?.userData?.label || "kira",
      profile: activeAvatarAmbientMotionProfile(),
      action,
      locomotionBlend,
      deliberateAction: activeAvatarHasDeliberatePoseOwner(),
      lipSyncActive: voicePlaybackMatchesActiveAvatar(),
      supportsExistingMouthSmile: !!activeKiraMouthLipSyncRig,
    })
    : comfortIdleOffsets(t, idleProfile, expressionAction);
  activeAvatarAmbientMicroMovementFrame = isKiraLike ? comfortIdle : null;
  const idleBreath = comfortIdle.breath;
  const idleWeight = comfortIdle.weight;
  const turnInPlaceBlend = THREE.MathUtils.clamp(Number(activeMarker?.userData?.turnInPlaceBlend || 0), 0, 1);
  resetActiveAvatarProceduralRigPose(rig);
  activeAvatarRoot.updateMatrixWorld(true);

  if (rig.bones.hips) {
    rig.bones.hips.rotation.z += Math.sin(phase) * 0.024 * locomotionBlend + comfortIdle.hipsZ * (1 - locomotionBlend);
    rig.bones.hips.rotation.y += Math.sin(phase) * 0.012 * locomotionBlend + comfortIdle.hipsY * (1 - locomotionBlend);
  }
  if (rig.bones.spine) {
    rig.bones.spine.rotation.z += -Math.sin(phase) * 0.016 * locomotionBlend + comfortIdle.spineZ * (1 - locomotionBlend);
    rig.bones.spine.rotation.x += comfortIdle.spineX * (1 - locomotionBlend) + turnInPlaceBlend * 0.01;
  }
  if (action === "dodge" && rig.bones.spine) rig.bones.spine.rotation.z += Math.sin(phase) * 0.18;
  if (rig.bones.neck) rig.bones.neck.rotation.y += (isKiraLike ? comfortIdle.neckY : idleWeight * (activeAvatarIsMarinetteLike() ? 0.018 : 0.01)) * (1 - locomotionBlend * 0.55);
  if (isKiraLike && rig.bones.neck) rig.bones.neck.rotation.z += comfortIdle.neckZ;
  if (rig.bones.head) {
    rig.bones.head.rotation.y += (isKiraLike ? comfortIdle.headY : idleWeight * (activeAvatarIsMarinetteLike() ? 0.026 : 0.012)) * (1 - locomotionBlend * 0.45);
    if (isKiraLike) {
      rig.bones.head.rotation.x += comfortIdle.headX * (1 - locomotionBlend * 0.7);
      rig.bones.head.rotation.z += comfortIdle.headZ;
    }
  }

  if (action === "duck") {
    if (rig.bones.hips) rig.bones.hips.rotation.x += 0.18;
    if (rig.bones.spine) rig.bones.spine.rotation.x += 0.2;
    for (const item of [
      { upper: rig.bones.leftThigh, lower: rig.bones.leftShin, foot: rig.bones.leftFoot, arm: rig.bones.leftUpperArm, forearm: rig.bones.leftForearm },
      { upper: rig.bones.rightThigh, lower: rig.bones.rightShin, foot: rig.bones.rightFoot, arm: rig.bones.rightUpperArm, forearm: rig.bones.rightForearm },
    ]) {
      if (item.upper) item.upper.rotation.x += 0.58;
      if (item.lower) item.lower.rotation.x += 0.82;
      if (item.foot) item.foot.rotation.x -= 0.18;
      if (item.arm) item.arm.rotation.x -= 0.12;
      if (item.forearm) item.forearm.rotation.x += 0.22;
    }
    if (activeMarker) {
      activeMarker.userData.proceduralRig = rig.id;
      activeMarker.userData.proceduralRigDriving = true;
      activeMarker.userData.proceduralGaitMode = "duck";
    }
    return;
  }

  if (action === "jump") {
    const age = activeSkillInteraction?.kind === "jump" ? t - activeSkillInteraction.startedAt : 0;
    const seconds = activeSkillInteraction?.seconds || 1.12;
    const k = THREE.MathUtils.clamp(age / seconds, 0, 1);
    const bend = 1 - Math.sin(k * Math.PI);
    const armsUp = Math.sin(k * Math.PI);
    for (const item of [
      { upper: rig.bones.leftThigh, lower: rig.bones.leftShin, foot: rig.bones.leftFoot, arm: rig.bones.leftUpperArm, forearm: rig.bones.leftForearm },
      { upper: rig.bones.rightThigh, lower: rig.bones.rightShin, foot: rig.bones.rightFoot, arm: rig.bones.rightUpperArm, forearm: rig.bones.rightForearm },
    ]) {
      if (item.upper) item.upper.rotation.x += 0.32 * bend;
      if (item.lower) item.lower.rotation.x += 0.48 * bend;
      if (item.foot) item.foot.rotation.x -= 0.14 * bend;
      if (item.arm) item.arm.rotation.x -= 0.35 * armsUp;
      if (item.forearm) item.forearm.rotation.x -= 0.18 * armsUp;
    }
    if (activeMarker) {
      activeMarker.userData.proceduralRig = rig.id;
      activeMarker.userData.proceduralRigDriving = true;
      activeMarker.userData.proceduralGaitMode = "jump";
    }
    return;
  }

  if (action === "swim_idle") {
    if (rig.bones.spine) rig.bones.spine.rotation.x += Math.sin(t * 2.2) * 0.08;
    for (const item of [
      { side: "L", offset: 0, arm: rig.bones.leftUpperArm, forearm: rig.bones.leftForearm, thigh: rig.bones.leftThigh, shin: rig.bones.leftShin, foot: rig.bones.leftFoot },
      { side: "R", offset: Math.PI, arm: rig.bones.rightUpperArm, forearm: rig.bones.rightForearm, thigh: rig.bones.rightThigh, shin: rig.bones.rightShin, foot: rig.bones.rightFoot },
    ]) {
      const p = phase + item.offset;
      if (item.arm) item.arm.rotation.x += Math.sin(p) * 0.55 - 0.18;
      if (item.forearm) item.forearm.rotation.x += Math.max(0, Math.cos(p)) * 0.42;
      if (item.thigh) item.thigh.rotation.x += Math.sin(p * 1.2) * 0.24;
      if (item.shin) item.shin.rotation.x += Math.sin(p * 1.2 + 0.8) * 0.34;
      if (item.foot) item.foot.rotation.x += Math.sin(p * 1.2 + 1.2) * 0.08;
      curlActiveAvatarProceduralFingers(rig, item.side, 0.34);
    }
    if (activeMarker) {
      activeMarker.userData.proceduralRig = rig.id;
      activeMarker.userData.proceduralRigDriving = true;
      activeMarker.userData.proceduralGaitMode = "swim";
    }
    return;
  }

  if (applyAvatarDressingPose(rig, t)) return;
  if (applyKiraSleepPose(rig, t)) return;
  if (applyKiraVoluntaryBodyActionPose(rig, t)) return;
  if (applyKiraDoctorBodyControlExamPose(rig, t)) return;
  if (applyKiraArmMobilityPose(rig, t)) return;
  if (applyKiraSchoolStudyPose(rig, t)) return;

  for (const item of [
    { side: "L", offset: 0, upper: rig.bones.leftUpperArm, lower: rig.bones.leftForearm, hand: rig.bones.leftHand },
    { side: "R", offset: Math.PI, upper: rig.bones.rightUpperArm, lower: rig.bones.rightForearm, hand: rig.bones.rightHand },
  ]) {
    const swing = Math.sin(phase + item.offset) * locomotionBlend
      + idleWeight * (1 - locomotionBlend) * (item.side === "L" ? 0.055 : -0.042);
    const sideSign = (item.side === "L" ? 1 : -1) * (isSpiderLike ? -1 : 1);
    const kiraArmOverride = isKiraLike && typeof window !== "undefined" ? window.__kiraArmPoseOverride || null : null;
    const kiraNumber = (key, fallback) => (Number.isFinite(kiraArmOverride?.[key]) ? Number(kiraArmOverride[key]) : fallback);
    const tPoseDrop = isSpiderLike ? 1.34 : isKiraLike ? kiraNumber("upperZ", 0.1) : activeAvatarIsMarinetteLike() ? 0.26 : 0.14;
    const relaxedOutward = isSpiderLike ? 0.0 : isKiraLike ? kiraNumber("outward", 0.0) : 0.08;
    const kiraGaitArmSwing = gaitMode === "run" ? 0.2 : gaitMode === "jog" ? 0.19 : 0.18;
    const armSwing = swing * (isSpiderLike ? 0.055 : isKiraLike ? kiraNumber("swing", kiraGaitArmSwing) : 0.1) * gaitScale;
    if (isKiraLike && item.upper && item.lower && item.hand) {
      // Ordinary locomotion uses constrained local joint rotations.  The old
      // body-relative hand IK had no elbow pole constraint, so the solver could
      // flip or hyperextend an elbow while chasing an imaginary point beside
      // the hip.  Contact IK remains reserved for real door/prop interactions.
      const relaxedUpperZ = THREE.MathUtils.clamp(
        kiraNumber("upperZ", 0.1),
        ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS.upperZ[0],
        ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS.upperZ[1],
      );
      const relaxedUpperY = THREE.MathUtils.clamp(
        kiraNumber("upperY", 1.1),
        ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS.upperY[0],
        ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS.upperY[1],
      );
      const relaxedElbowX = item.side === "L" ? 0.155 : 0.135;
      const relaxedLowerX = THREE.MathUtils.clamp(
        kiraNumber("lowerX", relaxedElbowX) - armSwing * 0.08,
        ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS.lowerX[0],
        ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS.lowerX[1],
      );
      const comfortShoulderZ = item.side === "L" ? comfortIdle.leftShoulderZ : comfortIdle.rightShoulderZ;
      item.upper.rotation.z += sideSign * relaxedUpperZ + comfortShoulderZ * (1 - locomotionBlend);
      item.upper.rotation.y += sideSign * relaxedUpperY;
      const comfortShoulderX = item.side === "L" ? comfortIdle.leftShoulderX : comfortIdle.rightShoulderX;
      item.upper.rotation.x += THREE.MathUtils.clamp(
        armSwing + comfortShoulderX * (1 - locomotionBlend),
        ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS.upperX[0],
        ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS.upperX[1],
      );
      const comfortElbowX = item.side === "L" ? comfortIdle.leftElbowX : comfortIdle.rightElbowX;
      item.lower.rotation.x += relaxedLowerX + comfortElbowX * (1 - locomotionBlend);
      const comfortElbowZ = item.side === "L" ? comfortIdle.leftElbowZ : comfortIdle.rightElbowZ;
      item.lower.rotation.z += comfortElbowZ * (1 - locomotionBlend);
      const comfortWristX = item.side === "L" ? comfortIdle.leftWristX : comfortIdle.rightWristX;
      const comfortWristY = item.side === "L" ? comfortIdle.leftWristY : comfortIdle.rightWristY;
      const comfortWristZ = item.side === "L" ? comfortIdle.leftWristZ : comfortIdle.rightWristZ;
      item.hand.rotation.x += -armSwing * 0.04 + comfortWristX * (1 - locomotionBlend);
      item.hand.rotation.y += comfortWristY * (1 - locomotionBlend);
      item.hand.rotation.z += THREE.MathUtils.clamp(
        sideSign * (0.012 + idleBreath * 0.003 * (1 - locomotionBlend))
          + comfortWristZ * (1 - locomotionBlend),
        ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS.handZ[0],
        ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS.handZ[1],
      );
      const relaxedFingerCurl = item.side === "L" ? 0.20 : 0.17;
      curlActiveAvatarProceduralFingers(rig, item.side, THREE.MathUtils.lerp(relaxedFingerCurl, 0.15, locomotionBlend));
      continue;
    }
    if (item.upper) {
      item.upper.rotation.z += sideSign * (tPoseDrop + relaxedOutward);
      item.upper.rotation.y += sideSign * (isSpiderLike ? -0.055 : isKiraLike ? kiraNumber("upperY", 1.1) : 0.015);
      item.upper.rotation.x += (isSpiderLike ? -0.08 : isKiraLike ? kiraNumber("upperX", 0.0) : -0.02) + armSwing;
    }
    if (item.lower) {
      item.lower.rotation.z += sideSign * (isSpiderLike ? 0.015 : isKiraLike ? kiraNumber("lowerZ", 0.0) : 0.04);
      item.lower.rotation.x += (isSpiderLike ? 0.34 : isKiraLike ? kiraNumber("lowerX", 0.1) : 0.08) - armSwing * (isKiraLike ? 0.08 : 0.12);
    }
    if ((isSpiderLike || isKiraLike) && item.hand) {
      // Ordinary walking has no object target.  The previous hard-coded hand
      // IK target bent Kira's elbows toward an imaginary point and made the
      // hands look as if they were claiming contact that did not exist.
      // Contact IK remains in the dedicated door/prop interaction paths.
      item.hand.rotation.x += isKiraLike ? -armSwing * 0.08 : -armSwing * 0.12;
      item.hand.rotation.z += sideSign * (isKiraLike ? 0.018 : 0.03);
    }
    curlActiveAvatarProceduralFingers(rig, item.side, isSpiderLike ? (groundedLocomotion ? 0.62 : 0.7) : isKiraLike ? (groundedLocomotion ? 0.08 : 0.04) : (groundedLocomotion ? 0.2 : 0.28));
  }
  if (isKiraLike) applyKiraComfortFingerMotion(rig, comfortIdle, locomotionBlend);

  if (isKiraLike && activeMarker) {
    activeMarker.userData.armMotionEvidence = {
      mode: "calibrated_bind_axis_joint_limited_swing_v10_relaxed_elbow_hand_asymmetry",
      predecessorMode: "calibrated_bind_axis_joint_limited_swing_v9_asymmetric_expression",
      objectContactClaimed: false,
      objectContactIkReservedForInteraction: true,
      ordinaryLocomotionUsesHandIk: false,
      elbowPoleFlipAvoided: true,
      jointLimitsRadians: ACTIVE_AVATAR_KIRA_RELAXED_ARM_LIMITS,
      idleMotionMode: idleProfile.mode,
      comfortIdleMode: comfortIdle.mode,
      comfortIdleRootTranslation: comfortIdle.rootTranslation,
      expressionAction,
      actualPlaybackExpression: voicePlaybackMatchesActiveAvatar(),
      leftGesture: Number(comfortIdle.leftGesture.toFixed(4)),
      rightGesture: Number(comfortIdle.rightGesture.toFixed(4)),
      fingerStrength: Number(comfortIdle.fingerStrength.toFixed(4)),
      locomotionBlend: Number(locomotionBlend.toFixed(4)),
      ambientMicroMovement: {
        version: comfortIdle.version,
        mode: comfortIdle.mode,
        ownership: "person_owned_not_user_motor_command",
        suppression: comfortIdle.suppression,
        rootTranslation: comfortIdle.rootTranslation,
        rootRotation: comfortIdle.rootRotation,
        scaleDelta: comfortIdle.scaleDelta,
        existingMouthSmile: Number(comfortIdle.face?.smile || 0),
        createsSecondMouth: false,
      },
      visuallyReviewedThisSession: false,
    };
  }

  for (const item of [
    { side: "L", x: -0.16, offset: 0, upper: rig.bones.leftThigh, lower: rig.bones.leftShin, foot: rig.bones.leftFoot, toe: rig.bones.leftToe },
    { side: "R", x: 0.16, offset: Math.PI, upper: rig.bones.rightThigh, lower: rig.bones.rightShin, foot: rig.bones.rightFoot, toe: rig.bones.rightToe },
  ]) {
    const cycle = phase + item.offset;
    const swing = Math.sin(cycle) * locomotionBlend;
    const swingLift = Math.max(0, -Math.cos(cycle)) * locomotionBlend;
    const thighSwing = swing * (isSpiderLike ? 0.4 : 0.38) * gaitScale;
    const kneeBend = swingLift * (isSpiderLike ? 0.62 : 0.66) * gaitScale + 0.025 * (1 - locomotionBlend);
    const footPitch = Math.sin(cycle - 0.35) * 0.12 * gaitScale * locomotionBlend;
    const kneeDirection = isSpiderLike || isKiraLike ? -1 : activeAvatarUsesGenericProceduralRigForMarinette() ? -1 : 1;
    if (item.upper) item.upper.rotation.x += thighSwing + kneeBend * 0.06 * kneeDirection;
    const comfortKneeX = item.side === "L" ? comfortIdle.leftKneeX : comfortIdle.rightKneeX;
    const comfortAnkleX = item.side === "L" ? comfortIdle.leftAnkleX : comfortIdle.rightAnkleX;
    const comfortToeX = item.side === "L" ? comfortIdle.leftToeX : comfortIdle.rightToeX;
    if (item.lower) item.lower.rotation.x += kneeBend * kneeDirection + comfortKneeX * (1 - locomotionBlend);
    if (item.foot) item.foot.rotation.x += footPitch - kneeBend * 0.08 * kneeDirection + comfortAnkleX * (1 - locomotionBlend);
    if (item.toe) item.toe.rotation.x += comfortToeX * (1 - locomotionBlend);
  }

  if (activeMarker) {
    activeMarker.userData.proceduralRig = rig.id;
    activeMarker.userData.proceduralRigDriving = moving || !rig.hasWalkClip;
    activeMarker.userData.proceduralGaitMode = action === "dodge" ? "dodge" : gaitMode;
  }
}

async function loadActivePoseManifest(shellState, position) {
  if (!shellState.active_pose_manifest_url || shellState.active_pose_manifest_url === activePoseManifestUrl) return;
  try {
    const response = await fetch(shellState.active_pose_manifest_url, { cache: "no-store" });
    if (!response.ok) throw new Error(`pose manifest ${response.status}`);
    const manifest = await response.json();
    const nextTextures = new Map();
    const loads = [];
    for (const [formName, formData] of Object.entries(manifest.forms || {})) {
      for (const [poseName, poseData] of Object.entries(formData.poses || {})) {
        if (!poseData?.file || poseData.status !== "ready") continue;
        const shellAssetOrigin = new URL(shellState.active_pose_manifest_url).origin;
        const url = poseData.file.startsWith("http") ? poseData.file : `${shellAssetOrigin}/${poseData.file}`;
        loads.push(new Promise((resolve) => {
          textureLoader.load(url, (texture) => {
            texture.colorSpace = THREE.SRGBColorSpace;
            nextTextures.set(`${formName}:${poseName}`, texture);
            resolve();
          }, undefined, resolve);
        }));
      }
    }
    await Promise.all(loads);
    if (!nextTextures.size || !activeMarker) return;
    activePoseManifestUrl = shellState.active_pose_manifest_url;
    activePoseTextures = nextTextures;
    activePoseMaterial = new THREE.SpriteMaterial({ transparent: true, depthWrite: false, alphaTest: 0.04 });
    activePoseSprite = new THREE.Sprite(activePoseMaterial);
    activePoseSprite.position.y = 1.12;
    activeMarker.position.copy(position);
    activeMarker.add(activePoseSprite);
    updateActivePoseSprite(performance.now() / 1000);
  } catch (error) {
    console.warn("Active pose manifest failed.", error);
  }
}

function setActiveMarker(shellState) {
  const label = shellState.active_label || "";
  if (!label || label === "none") {
    clearActiveAvatar();
    activeShellState = null;
    return;
  }
  const nextForm = shellState.active_form || "civilian";
  const displayModelUrl = displayModelUrlFor(shellState, label);
  const kiraRuntimeModelRevoked = shouldRevokeKiraRuntimeModel(shellState, label, displayModelUrl);
  if (kiraRuntimeModelRevoked) unloadActiveAvatarModel();
  const sameActiveAvatar =
    !kiraRuntimeModelRevoked &&
    activeMarker &&
    activeShellState?.active_candidate === shellState.active_candidate &&
    activeAvatarModelUrl === displayModelUrl &&
    activeAvatarForm === nextForm;
  const previousIntentRevision = String(activeShellState?.active_intent_updated_at || "");
  const nextIntentRevision = String(shellState?.active_intent_updated_at || "");
  activeShellState = shellState;
  if (sameActiveAvatar) {
    activeMarker.userData.label = label;
    if (activeSkillInteraction?.persistentQuietActivity && shellState.active_action) {
      const quietActivityHandled = handlePersistentQuietActivityShellAction(shellState.active_action);
      if (quietActivityHandled) return;
    }
    const personOwnedIntentChanged = nextIntentRevision
      && nextIntentRevision !== previousIntentRevision
      && shellState?.active_intent_metadata?.person_owned_intent === true;
    if (personOwnedIntentChanged) {
      activeMarker.userData.lastPersonOwnedIntentRevision = nextIntentRevision;
      activeMarker.userData.lastPersonOwnedIntentSource = shellState.active_intent_source || "";
      if (shellState.active_action) setActiveAvatarAction(shellState.active_action);
      maybeStartBodyPracticeFromShellAction(shellState.active_action);
    } else if (shellState.active_action && shellState.active_action !== activeAvatarAction) {
      setActiveAvatarAction(shellState.active_action);
      maybeStartBodyPracticeFromShellAction(shellState.active_action);
    }
    return;
  }
  clearActiveAvatar();
  activeShellState = shellState;
  const resumePosition = activeAvatarResumePositionFromShell(shellState, label);
  const position = activeWorldPosition(shellState.location, label, shellState);
  activeAvatarHomePosition.copy(position);
  activeAvatarMovePhase = 0;
  activeAvatarAction = shellState.active_action || "idle";
  activeAvatarActionStarted = clock.elapsedTime;
  activeAvatarForm = nextForm;
  activeMarker = new THREE.Group();
  activeMarker.userData.label = label;
  scene.add(activeMarker);
  activeMarker.position.copy(position);
  if (!resumePosition && activeAvatarIsKiraLike()) {
    activeMarker.userData.roamZone = "kira_home_world";
  }
  if (resumePosition) applyActiveAvatarResumeState(resumePosition);
  const displayState = { ...shellState, active_model_url: displayModelUrl };
  if (shouldUsePoseAvatarFirst(label) && shellState.active_pose_manifest_url) loadActivePoseManifest(shellState, position);
  else if (displayModelUrl) loadActiveModel(displayState, position);
  else if (shellState.active_pose_manifest_url) loadActivePoseManifest(shellState, position);
  else if (activeAvatarIsKiraLike()) {
    // Kira's exact body selection remains fail-closed: the orb is an explicit,
    // named presence marker and never a substitute body or identity claim.
    activeMarker.userData.kind = "body_load_blocked_named_orb_presence";
    activeMarker.userData.bodyLoadBlockedReason = shellState?.active_body_selection?.reason || "model_url_unavailable";
    activeMarker.add(makeOrbMarker(label));
  } else activeMarker.add(makeOrbMarker(label));
  maybeStartBodyPracticeFromShellAction(shellState.active_action);
}

function activeAvatarStairProgress(z) {
  return THREE.MathUtils.clamp(
    (ACTIVE_AVATAR_STAIR_BOTTOM_Z - z) / (ACTIVE_AVATAR_STAIR_BOTTOM_Z - ACTIVE_AVATAR_STAIR_TOP_Z),
    0,
    1,
  );
}

function activeAvatarStairInfo(position) {
  if (!MAIN_TWO_STORY_HOUSE_ENABLED) return { onRun: false, y: position.y, stepIndex: null };
  const onRun = Math.abs(position.x - 1.9) < ACTIVE_AVATAR_STAIR_HALF_WIDTH && position.z <= ACTIVE_AVATAR_STAIR_BOTTOM_Z && position.z >= ACTIVE_AVATAR_STAIR_TOP_Z;
  if (!onRun) return { onRun: false, y: position.y, stepIndex: null };
  const progress = activeAvatarStairProgress(position.z);
  const stepIndex = Math.min(ACTIVE_AVATAR_STAIR_STEPS, Math.max(0, Math.round(progress * ACTIVE_AVATAR_STAIR_STEPS)));
  const y = ACTIVE_AVATAR_STAIR_BOTTOM_Y + (stepIndex / ACTIVE_AVATAR_STAIR_STEPS) * (ACTIVE_AVATAR_STAIR_TOP_Y - ACTIVE_AVATAR_STAIR_BOTTOM_Y);
  return { onRun: true, y, stepIndex, progress };
}

function activeAvatarSupportContains(surface, x, z) {
  return x >= surface.xMin && x <= surface.xMax && z >= surface.zMin && z <= surface.zMax;
}

function activeAvatarCanUseStairSupport(position, stair) {
  if (!stair?.onRun) return false;
  const yDiff = Math.abs(position.y - stair.y);
  if (yDiff <= ACTIVE_AVATAR_SUPPORT_SNAP_RANGE + 0.18) return true;
  if (position.y < ACTIVE_AVATAR_STAIR_BOTTOM_Y + 0.45 && stair.stepIndex <= 4) return true;
  if (position.y > ACTIVE_AVATAR_STAIR_TOP_Y - 0.55 && stair.stepIndex >= ACTIVE_AVATAR_STAIR_STEPS - 4) return true;
  return false;
}

function activeAvatarShouldBlockUnsafeFloorDrop(support) {
  if (!activeMarker || !support || support.isStair) return false;
  const upstairsHeight = activeMarker.position.y > ACTIVE_AVATAR_SECOND_FLOOR_Y - 0.62;
  const downstairsSupport = support.y < ACTIVE_AVATAR_GROUND_Y + 0.12;
  const routeAllowsDrop = activeMarker.userData?.stairTraversalActive || activeMarker.userData?.practiceRoute?.id === "stairs_step";
  return upstairsHeight && downstairsSupport && !routeAllowsDrop;
}

function recoverActiveAvatarFromUnsafeFloorDrop() {
  if (!activeMarker) return;
  if (!MAIN_TWO_STORY_HOUSE_ENABLED) {
    activeMarker.position.copy(activeAvatarSafeRecoveryPosition());
    activeMarker.position.y = ACTIVE_AVATAR_GROUND_Y;
    activeMarker.userData.roamZone = activeAvatarDefaultRoamZone();
    activeMarker.userData.autonomousRoamTarget = null;
    activeMarker.userData.stairTraversalActive = false;
    activeMarker.userData.stuckSince = null;
    activeMarker.userData.lastDistanceToTarget = null;
    activeMarker.userData.waitUntil = clock.elapsedTime + 0.9;
    activeMarker.userData.isMoving = false;
    activeMarker.userData.walkSpeed = 0;
    activeMarker.userData.lastStepMeters = 0;
    recordMovementLearningAttempt({
      skill: "route_safety",
      phase: "old_two_story_support_disabled_ground_recovery",
      actor: activeAvatarDisplayName(),
      position: {
        x: Number(activeMarker.position.x.toFixed(3)),
        y: Number(activeMarker.position.y.toFixed(3)),
        z: Number(activeMarker.position.z.toFixed(3)),
      },
      rotationY: Number(activeMarker.rotation.y.toFixed(6)),
    });
    return;
  }
  const lastSafe = activeMarker.userData.lastSafePosition;
  const canUseLastSafe = lastSafe
    && Math.abs(lastSafe.y - ACTIVE_AVATAR_SECOND_FLOOR_Y) < 0.35
    && !isAvatarBlocked(lastSafe.x, lastSafe.z, lastSafe.y, 0.42);
  activeMarker.position.copy(canUseLastSafe ? lastSafe : activeAvatarSafeRecoveryPosition());
  activeMarker.position.y = ACTIVE_AVATAR_SECOND_FLOOR_Y;
  activeMarker.userData.roamZone = "upstairs";
  activeMarker.userData.autonomousRoamTarget = null;
  activeMarker.userData.stairTraversalActive = false;
  activeMarker.userData.stuckSince = null;
  activeMarker.userData.lastDistanceToTarget = null;
  activeMarker.userData.waitUntil = clock.elapsedTime + 0.9;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  recordMovementLearningAttempt({
    skill: "route_safety",
    phase: "blocked_unsafe_stair_side_drop",
    actor: activeAvatarDisplayName(),
    position: {
      x: Number(activeMarker.position.x.toFixed(3)),
      y: Number(activeMarker.position.y.toFixed(3)),
      z: Number(activeMarker.position.z.toFixed(3)),
    },
  });
}

function activeAvatarSupportAt(position) {
  const stair = activeAvatarStairInfo(position);
  if (activeAvatarCanUseStairSupport(position, stair)) return { id: "main_stairs", y: stair.y, isStair: true, stepIndex: stair.stepIndex };
  let best = null;
  const reachableY = position.y + ACTIVE_AVATAR_SUPPORT_SNAP_RANGE;
  for (const surface of ACTIVE_AVATAR_SUPPORT_SURFACES) {
    if (!MAIN_TWO_STORY_HOUSE_ENABLED && (surface.id === "first_floor_slab" || surface.id.startsWith("second_floor"))) continue;
    if (!activeAvatarSupportContains(surface, position.x, position.z)) continue;
    if (surface.y > reachableY) continue;
    if (!best || surface.y > best.y) best = surface;
  }
  return best;
}

function applyActiveAvatarSupport(dt = 0.016) {
  if (!activeMarker) return null;
  const support = activeAvatarSupportAt(activeMarker.position);
  if (!support) {
    if (activeMarker.position.y > ACTIVE_AVATAR_SECOND_FLOOR_Y - 0.62 && !activeMarker.userData?.stairTraversalActive) {
      recoverActiveAvatarFromUnsafeFloorDrop();
      activeMarker.userData.supportState = {
        id: "second_floor_no_support_guard",
        supported: true,
        falling: false,
        y: ACTIVE_AVATAR_SECOND_FLOOR_Y,
        floor: 1,
        isStair: false,
      };
      return activeMarker.userData.supportState;
    }
    activeMarker.position.y -= ACTIVE_AVATAR_UNSUPPORTED_FALL_METERS_PER_SECOND * dt;
    activeMarker.userData.supportState = {
      supported: false,
      falling: true,
      floor: activeMarker.position.y > 1.8 ? 1 : 0,
    };
    return null;
  }

  if (activeAvatarShouldBlockUnsafeFloorDrop(support)) {
    recoverActiveAvatarFromUnsafeFloorDrop();
    activeMarker.userData.supportState = {
      id: "second_floor_drop_guard",
      supported: true,
      falling: false,
      y: ACTIVE_AVATAR_SECOND_FLOOR_Y,
      floor: 1,
      isStair: false,
    };
    return activeMarker.userData.supportState;
  }

  const diff = support.y - activeMarker.position.y;
  const falling = diff < -ACTIVE_AVATAR_SUPPORT_SNAP_RANGE;
  if (falling) {
    activeMarker.position.y = Math.max(support.y, activeMarker.position.y - ACTIVE_AVATAR_UNSUPPORTED_FALL_METERS_PER_SECOND * dt);
  } else {
    activeMarker.position.y = THREE.MathUtils.lerp(activeMarker.position.y, support.y, Math.min(1, dt * 14.0));
  }
  activeMarker.userData.supportState = {
    id: support.id,
    supported: Math.abs(support.y - activeMarker.position.y) < 0.025,
    falling,
    y: Number(support.y.toFixed(3)),
    floor: support.y > 1.8 ? 1 : 0,
    stepIndex: support.stepIndex ?? null,
    isStair: !!support.isStair,
  };
  return support;
}

function updateActiveAvatarStairPractice(t) {
  if (!activeMarker) return false;
  if (!MAIN_TWO_STORY_HOUSE_ENABLED) {
    activeMarker.userData.onStairs = false;
    activeMarker.userData.lastStairStepIndex = null;
    activeMarker.userData.stairTraversalActive = false;
    return false;
  }
  const stair = activeAvatarStairInfo(activeMarker.position);
  activeMarker.userData.onStairs = stair.onRun;
  const routeAllowsStairs = activeMarker.userData.stairTraversalActive || activeMarker.userData.practiceRoute?.id === "stairs_step" || activeMarker.userData.practiceRoute?.skill === "stairs_step";
  if (!stair.onRun || !routeAllowsStairs || !activeAvatarCanUseStairSupport(activeMarker.position, stair)) {
    activeMarker.userData.lastStairStepIndex = null;
    return false;
  }
  const previous = activeMarker.userData.lastStairStepIndex;
  activeMarker.userData.lastStairStepIndex = stair.stepIndex;
  activeMarker.position.y = THREE.MathUtils.lerp(activeMarker.position.y, stair.y, Math.min(1, (t - (activeMarker.userData.lastMoveT ?? t) + 0.05) * 9.0));
  activeMarker.userData.walkSpeed = ACTIVE_AVATAR_STAIR_PRACTICE_SPEED;
  activeMarker.userData.supportState = {
    id: "main_stairs",
    supported: true,
    falling: false,
    y: Number(stair.y.toFixed(3)),
    floor: stair.y > 1.8 ? 1 : 0,
    stepIndex: stair.stepIndex,
    isStair: true,
  };
  if (previous !== stair.stepIndex) {
    recordMovementLearningAttempt({
      skill: "stairs_step",
      phase: "step_contact",
      stepIndex: stair.stepIndex,
      stepCount: ACTIVE_AVATAR_STAIR_STEPS,
      targetY: Number(stair.y.toFixed(3)),
    });
  }
  return true;
}

function activeAvatarIsMarinetteLike() {
  const activeName = (activeMarker?.userData?.label || "").toLowerCase();
  return activeName.includes("ladybug") || activeName.includes("marinette");
}

function activeAvatarUsesGenericProceduralRigForMarinette() {
  return activeAvatarIsMarinetteLike() && !!activeAvatarRoot?.userData?.useGenericProceduralRigForMarinette;
}

function activeAvatarLabelLower() {
  return String(activeMarker?.userData?.label || activeShellState?.active_ai || "").toLowerCase();
}

function activeAvatarDisplayName() {
  return activeMarker?.userData?.label || activeShellState?.active_ai || "Active avatar";
}

function activeAvatarIsSpiderLike() {
  const label = activeAvatarLabelLower();
  return label.includes("spider") || label.includes("gwen") || label.includes("stacy") || label.includes("peter parker");
}

function activeAvatarIsKiraLike() {
  const label = activeAvatarLabelLower();
  return label === "kira" || label.includes("kira first");
}

function activeAvatarCanUseDoors() {
  return !!activeMarker && activeMarker.userData?.kind !== "orb";
}

function activeAvatarUsesProceduralWalkOverride() {
  return activeAvatarIsSpiderLike() || activeAvatarIsKiraLike();
}

function actionIsEquivalentKitchenDrinkIntent(actionName) {
  return /^(get_drink|drink|water|milk|kitchen_drink|get_home_coffee|kitchen_coffee|make_home_coffee|coffee|get_coffee|drink_coffee)$/.test(
    String(actionName || "").toLowerCase().trim(),
  );
}

function coalesceEquivalentKitchenIntentWithoutRouteReset(normalized, now) {
  if (!activeMarker || !actionIsEquivalentKitchenDrinkIntent(normalized)) return false;
  const route = activeMarker.userData?.practiceRoute;
  const routeIsKitchen = /^walk_inside_to_kitchen_(?:drink|coffee_station)$/.test(String(route?.id || ""));
  const holdIsKitchen = /^autonomous_kitchen_(?:drink|coffee)$/.test(String(activeSkillInteraction?.id || ""));
  if (!routeIsKitchen && !holdIsKitchen) return false;
  activeMarker.userData.lastShellBodyPracticeAction = normalized;
  activeMarker.userData.lastShellBodyPracticeAt = now;
  if (routeIsKitchen) {
    route.coalescedIntentCount = Number(route.coalescedIntentCount || 0) + 1;
    route.lastCoalescedIntent = normalized;
    route.lastCoalescedIntentAt = now;
  }
  recordMovementLearningAttempt({
    skill: route?.id || activeSkillInteraction?.id || "kitchen_drink",
    phase: "equivalent_person_owned_kitchen_intent_coalesced_route_preserved",
    target: normalized,
    coalescedIntentCount: Number(route?.coalescedIntentCount || 0),
    bodyPositionUnchangedByIntent: true,
    teleported: false,
  });
  return true;
}

function maybeStartBodyPracticeFromShellAction(actionName) {
  if (!activeMarker) return false;
  const normalized = String(actionName || "").toLowerCase().trim();
  const now = clock.elapsedTime || 0;
  if (coalesceEquivalentKitchenIntentWithoutRouteReset(normalized, now)) return true;
  const intentAge = now - (activeMarker.userData.lastShellBodyPracticeAt || -999);
  if (normalized && activeMarker.userData.lastShellBodyPracticeAction === normalized && intentAge < 3.0) return false;

  if (/^(doctor_body_exam|doctor_body_control_exam|body_control_exam|movement_exam)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    // An engineering diagnostic is not a command to the person.  It remains a
    // developer-only staged harness and is never auto-started from chat/shell
    // text. Voluntary actions below still require Kira's expressed intent.
    recordMovementLearningAttempt({
      skill: "body_control_engineering_check",
      phase: "not_started_from_live_person_action",
      target: normalized,
      personOwnedIntentRequired: true,
    });
    return false;
  }
  if (normalized === "raise_hand") {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarVoluntaryBodyIntent("raise_hand", {
      source: "subject_runtime_intent",
      seconds: 3.5,
    });
  }
  if (/^(walk|jog|run)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    if (normalized === "walk") return startActiveAvatarWalkPractice({ selfChosen: true });
    if (normalized === "jog") return startActiveAvatarJogPractice({ selfChosen: true });
    return startActiveAvatarRunPractice({ selfChosen: true });
  }

  if (/^(take_notes|type_notes|write_tablet|creative_write|tablet_creative_write)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarTabletWorkHold({ mode: normalized.includes("creative") ? "creative_write" : "take_notes", seconds: 22 });
  }
  if (/^(look_online|online_lookup|lookup|research|browse_web|use_tablet)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarTabletWorkHold({ mode: "look_online", seconds: 20 });
  }
  if (/^(read_all_day|read_for_hours|keep_reading|settle_in_and_read|persistent_read)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarPersistentHomeRead({
      seconds: ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY.initialReviewSeconds,
    });
  }
  if (/^(read|read_book|read_tablet|ebook|e-book|browse_books)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarHomeReadHold({ seconds: 18 });
  }
  if (/^(library|read_library|go_library|browse_library)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarLibraryReadPractice(22);
  }
  if (/^(go_inside|enter_home|walk_inside)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarHomeEntryWalk({ selfChosen: true });
  }
  if (/^(go_outside|walk_outside|head_outside|exit_home)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarHomeExitWalk({ selfChosen: true });
  }
  if (/^(sit|sit_down|sit_on_couch|couch|sofa|rest)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarHomeSitHold({ seconds: 18, selfChosen: true });
  }
  if (/^(lie_on_ground|lay_on_ground|lie_on_floor|lay_on_floor|look_at_sky)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarGroundLieHold({ seconds: 90, selfChosen: true });
  }
  if (/^(lie|lie_down|lay_down|lie_on_couch|lay_on_couch|lie_on_bed|lay_on_bed|bed|nap|sleep)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarHomeLieHold({
      where: /(?:lie|lay)_on_couch/.test(normalized) ? "couch" : "bed",
      sleep: normalized === "sleep",
      seconds: 22,
      selfChosen: true,
    });
  }
  if (/^(look_window|window|look_outside|watch_yard)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarHomeWindowHold({ seconds: 16 });
  }
  if (/^(get_drink|drink|water|milk|kitchen_drink)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarKitchenDrinkHold({ seconds: 12, selfChosen: true });
  }
  if (/^(get_home_coffee|kitchen_coffee|make_home_coffee)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarKitchenCoffeeHold({ seconds: 12, selfChosen: true });
  }
  if (/^(coffee|get_coffee|drink_coffee|starbucks|cafe)$/.test(normalized)) {
    activeMarker.userData.lastShellBodyPracticeAction = normalized;
    activeMarker.userData.lastShellBodyPracticeAt = now;
    return startActiveAvatarCafeCoffeePractice();
  }
  if (!window.kiraBodyPractice) return false;
  const skillByAction = {
    call_tardis: "call_tardis",
    enter_tardis: "enter_tardis",
    call_enter_tardis: "call_enter_tardis",
    use_tardis: "call_enter_tardis",
    put_on_robe: "put_on_robe",
    wear_robe: "put_on_robe",
    use_towel: "use_towel",
    wrap_towel: "use_towel",
  };
  const skill = skillByAction[normalized];
  if (!skill) return false;
  if (activeMarker.userData.lastShellBodyPracticeSkill === skill && intentAge < 3.0) return false;
  activeMarker.userData.lastShellBodyPracticeSkill = skill;
  activeMarker.userData.lastShellBodyPracticeAction = normalized;
  activeMarker.userData.lastShellBodyPracticeAt = now;
  window.setTimeout(() => window.kiraBodyPractice.startSkill(skill), 60);
  recordMovementLearningAttempt({
    skill,
    phase: "queued_from_shell_action",
    target: normalized,
    actor: activeAvatarDisplayName(),
  });
  return true;
}

function activeAvatarDefaultRoamZone() {
  if (!activeMarker) return "generic";
  if (activeShellState?.location === "library") return "library";
  if (activeAvatarIsMarinetteLike()) return activeMarker.position.y > 1.8 ? "upstairs" : "downstairs";
  if (activeAvatarIsSpiderLike()) return activeMarker.position.y > 1.8 ? "upstairs" : "downstairs";
  if (activeAvatarIsKiraLike()) return "kira_home_world";
  const label = activeAvatarLabelLower();
  if (label.includes("library") || label.includes("reader")) return "library";
  return "generic";
}

function activeAvatarDefaultWaypoints() {
  if (!activeMarker) return genericHomeRoamWaypoints;
  if (activeMarker.userData?.practiceRoute?.waypoints) return activeMarker.userData.practiceRoute.waypoints;
  if (activeMarker.userData?.roamZone === "capture_flag") return captureFlagRoamWaypoints;
  if (activeAvatarIsMarinetteLike()) return activeMarker.userData?.roamZone === "upstairs" ? marinetteUpstairsWaypoints : marinetteRoamWaypoints;
  if (activeAvatarIsSpiderLike()) return activeMarker.userData?.roamZone === "spider_outdoor" ? spiderHeroRoamWaypoints : spiderIndoorRoamWaypoints;
  if (activeAvatarIsKiraLike()) return activeMarker.userData?.roamZone === "kira_bungalow" ? kiraBungalowWaypoints : kiraHomeWorldWaypoints;
  if (activeMarker.userData?.roamZone === "library") return libraryVisitorRoamWaypoints;
  return genericHomeRoamWaypoints;
}

function activeAvatarAutonomousRoamAreas(zone = activeAvatarDefaultRoamZone()) {
  const floorY = zone === "upstairs" ? ACTIVE_AVATAR_SECOND_FLOOR_Y : ACTIVE_AVATAR_GROUND_Y;
  if (activeAvatarIsKiraLike() && (zone === "kira_bungalow" || zone === "kira_home_world")) {
    const areas = [
      { id: "Kira one-bedroom living room", y: ACTIVE_AVATAR_GROUND_Y, minX: ONE_BEDROOM_ROOM_SPLIT_X + 0.95, maxX: ONE_BEDROOM_HOUSE_RIGHT_X - 1.15, minZ: ONE_BEDROOM_BATH_FRONT_Z + 0.95, maxZ: ONE_BEDROOM_HOUSE_FRONT_Z - 0.95 },
      { id: "Kira one-bedroom bedroom clear floor", y: ACTIVE_AVATAR_GROUND_Y, minX: ONE_BEDROOM_HOUSE_LEFT_X + 2.4, maxX: ONE_BEDROOM_ROOM_SPLIT_X - 0.8, minZ: ONE_BEDROOM_BATH_FRONT_Z + 0.82, maxZ: ONE_BEDROOM_HOUSE_FRONT_Z - 0.75 },
      { id: "Kira one-bedroom front walk", y: ACTIVE_AVATAR_GROUND_Y, minX: ONE_BEDROOM_HOUSE_ENTRY.x - 1.8, maxX: ONE_BEDROOM_HOUSE_ENTRY.x + 1.8, minZ: ONE_BEDROOM_HOUSE_FRONT_Z - 0.4, maxZ: ONE_BEDROOM_HOUSE_FRONT_Z + 4.2 },
      { id: "public library front walk", y: ACTIVE_AVATAR_GROUND_Y, minX: 18.4, maxX: 28.6, minZ: 31.2, maxZ: 36.0 },
      { id: "public library reading area", y: ACTIVE_AVATAR_GROUND_Y, minX: 20.2, maxX: 27.8, minZ: 38.2, maxZ: 45.2 },
      { id: "Starbucks public entrance walk", y: ACTIVE_AVATAR_GROUND_Y, minX: STARBUCKS_CENTER.x - 4.0, maxX: STARBUCKS_CENTER.x + 4.0, minZ: STARBUCKS_PUBLIC_FRONT_Z - 2.4, maxZ: STARBUCKS_PUBLIC_FRONT_Z + 2.2 },
      { id: "Starbucks table with notes", y: ACTIVE_AVATAR_GROUND_Y, minX: STARBUCKS_SEAT_SPOT.x - 1.2, maxX: STARBUCKS_SEAT_SPOT.x + 1.2, minZ: STARBUCKS_SEAT_SPOT.z - 0.9, maxZ: STARBUCKS_SEAT_SPOT.z + 1.4 },
      { id: "Home World school entrance walk", y: ACTIVE_AVATAR_GROUND_Y, minX: SCHOOL_CENTER.x - 4.2, maxX: SCHOOL_CENTER.x + 4.2, minZ: SCHOOL_FRONT_Z - 2.2, maxZ: SCHOOL_FRONT_Z + 1.4 },
      HOME_WORLD_PRE_RAM_LIGHT_MODE
        ? { id: "empty school learning room", y: ACTIVE_AVATAR_GROUND_Y, minX: SCHOOL_CENTER.x - 3.4, maxX: SCHOOL_CENTER.x + 3.4, minZ: SCHOOL_CENTER.z - 2.8, maxZ: SCHOOL_CENTER.z + 2.8 }
        : { id: "Kira school study desk", y: ACTIVE_AVATAR_GROUND_Y, minX: SCHOOL_DESK_SPOT.x - 1.2, maxX: SCHOOL_DESK_SPOT.x + 1.2, minZ: SCHOOL_DESK_SPOT.z - 1.0, maxZ: SCHOOL_DESK_SPOT.z + 1.0 },
    ];
    if (!HOME_WORLD_PRE_RAM_LIGHT_MODE) {
      areas.push({ id: "future park basketball court edge", y: ACTIVE_AVATAR_GROUND_Y, minX: PARK_BASKETBALL_CENTER.x - 8.0, maxX: PARK_BASKETBALL_CENTER.x + 5.0, minZ: PARK_BASKETBALL_CENTER.z - 10.0, maxZ: PARK_BASKETBALL_CENTER.z + 2.5 });
    }
    return areas;
  }
  if (activeAvatarIsKiraLike() && zone === "upstairs") {
    return [
      { id: "Kira bedroom clear floor", y: ACTIVE_AVATAR_SECOND_FLOOR_Y, minX: -4.58, maxX: -3.82, minZ: 3.72, maxZ: 4.42 },
      { id: "upstairs hall outside Kira room", y: ACTIVE_AVATAR_SECOND_FLOOR_Y, minX: -1.68, maxX: -0.54, minZ: 4.72, maxZ: 5.72 },
      { id: "Kira bedroom workspace side", y: ACTIVE_AVATAR_SECOND_FLOOR_Y, minX: -5.98, maxX: -4.92, minZ: 4.68, maxZ: 5.92 },
    ];
  }
  const areas = {
    upstairs: [
      { id: "upstairs hall", y: ACTIVE_AVATAR_SECOND_FLOOR_Y, minX: -5.0, maxX: 5.6, minZ: -1.72, maxZ: 1.18 },
      { id: "Kira bedroom workspace", y: ACTIVE_AVATAR_SECOND_FLOOR_Y, minX: -6.82, maxX: -3.12, minZ: 3.14, maxZ: 6.42 },
      { id: "Lisa bedroom", y: ACTIVE_AVATAR_SECOND_FLOOR_Y, minX: 4.42, maxX: 7.22, minZ: 3.14, maxZ: 6.42 },
      { id: "Marinette temporary room", y: ACTIVE_AVATAR_SECOND_FLOOR_Y, minX: 4.42, maxX: 7.22, minZ: -6.42, maxZ: -3.74 },
      { id: "Peter temporary room", y: ACTIVE_AVATAR_SECOND_FLOOR_Y, minX: -6.82, maxX: -3.12, minZ: -1.52, maxZ: 1.58 },
      { id: "Gwen temporary room", y: ACTIVE_AVATAR_SECOND_FLOOR_Y, minX: -6.82, maxX: -3.12, minZ: -6.42, maxZ: -3.74 },
      { id: "shared bath door approach", y: ACTIVE_AVATAR_SECOND_FLOOR_Y, minX: 1.08, maxX: 3.42, minZ: -6.24, maxZ: -3.66 },
    ],
    downstairs: [
      { id: "front entry", y: ACTIVE_AVATAR_GROUND_Y, minX: -2.2, maxX: 3.6, minZ: 3.1, maxZ: 7.25 },
      { id: "front dining room", y: ACTIVE_AVATAR_GROUND_Y, minX: 3.72, maxX: 7.22, minZ: 2.84, maxZ: 6.42 },
      { id: "living room", y: ACTIVE_AVATAR_GROUND_Y, minX: -6.82, maxX: -1.62, minZ: -1.48, maxZ: 4.72 },
      { id: "home bookshelf reading spot", y: ACTIVE_AVATAR_GROUND_Y, minX: -6.94, maxX: -6.48, minZ: 4.48, maxZ: 5.02 },
      { id: "living room couch rest spot", y: ACTIVE_AVATAR_GROUND_Y, minX: -5.72, maxX: -4.66, minZ: 2.14, maxZ: 2.98 },
      { id: "kitchen", y: ACTIVE_AVATAR_GROUND_Y, minX: 1.36, maxX: 7.02, minZ: -7.02, maxZ: -1.24 },
      { id: "back hall", y: ACTIVE_AVATAR_GROUND_Y, minX: -0.72, maxX: 2.4, minZ: -7.22, maxZ: -4.5 },
    ],
    spider_outdoor: [
      { id: "front yard", y: ACTIVE_AVATAR_GROUND_Y, minX: -6.5, maxX: 8.5, minZ: 8.4, maxZ: 18.5 },
      { id: "sidewalk by strip mall", y: ACTIVE_AVATAR_GROUND_Y, minX: -2.0, maxX: 18.0, minZ: 22.4, maxZ: 28.8 },
      { id: "road shoulder", y: ACTIVE_AVATAR_GROUND_Y, minX: -12.0, maxX: 22.0, minZ: 15.8, maxZ: 21.7 },
    ],
    library: [
      { id: "library floor", y: ACTIVE_AVATAR_GROUND_Y, minX: 18.8, maxX: 28.6, minZ: 37.0, maxZ: 45.7 },
      { id: "library front sidewalk", y: ACTIVE_AVATAR_GROUND_Y, minX: 18.0, maxX: 30.2, minZ: 30.2, maxZ: 34.4 },
    ],
    generic: [
      { id: "home common area", y: floorY, minX: -5.8, maxX: 6.7, minZ: -1.2, maxZ: 7.0 },
      { id: "front sidewalk", y: ACTIVE_AVATAR_GROUND_Y, minX: -10.0, maxX: 13.0, minZ: 19.2, maxZ: 27.8 },
    ],
  };
  return areas[zone] || areas.generic;
}

function activeAvatarRandomPointInArea(area) {
  return new THREE.Vector3(
    THREE.MathUtils.lerp(area.minX, area.maxX, Math.random()),
    area.y,
    THREE.MathUtils.lerp(area.minZ, area.maxZ, Math.random()),
  );
}

function activeAvatarDirectPathIsClear(from, to, radius = 0.46) {
  if (!from || !to) return false;
  const distance = Math.hypot(to.x - from.x, to.z - from.z);
  if (distance < 0.001) return !isAvatarBlocked(to.x, to.z, to.y, radius);
  const sampleCount = Math.max(1, Math.ceil(distance / 0.14));
  for (let index = 1; index <= sampleCount; index += 1) {
    const k = index / sampleCount;
    const x = THREE.MathUtils.lerp(from.x, to.x, k);
    const y = THREE.MathUtils.lerp(from.y, to.y, k);
    const z = THREE.MathUtils.lerp(from.z, to.z, k);
    if (isAvatarBlocked(x, z, y, radius)) return false;
  }
  return true;
}

function planActiveAvatarOneBedroomInteriorRoute(from, to, reason = "person_owned_home_interaction") {
  if (!from || !to) {
    return { ok: false, waypoints: [], reason: "missing_interior_route_endpoint", mode: null, visitedNodes: 0 };
  }
  const y = Number.isFinite(Number(from.y)) ? Number(from.y) : ACTIVE_AVATAR_GROUND_Y;
  const plan = planCollisionFreeGridRoute({
    start: { x: from.x, z: from.z },
    goal: { x: to.x, z: to.z },
    bounds: ONE_BEDROOM_INTERIOR_ROUTE_BOUNDS,
    cellSize: ONE_BEDROOM_INTERIOR_ROUTE_CELL_METERS,
    // Match the finest swept-path sampling used by local steering.  The
    // 2026-07-19 TV incident began only millimetres outside the expanded TV
    // collider; the former 7 cm samples could jump across that short blocked
    // interval and hand the body a first waypoint it correctly refused.
    sampleSpacing: 0.04,
    maxVisited: 7000,
    isBlocked: (x, z) => isAvatarBlocked(x, z, y, ACTIVE_AVATAR_COLLISION_RADIUS),
  });
  return {
    ...plan,
    reasonContext: reason,
    waypoints: (plan.waypoints || []).map((point) => new THREE.Vector3(point.x, y, point.z)),
  };
}

function stopActiveAvatarForRouteRequestFailure(id, label, plan, target = null) {
  if (!activeMarker) return false;
  clearActiveAvatarPracticeInteractions();
  const failure = {
    id: id || "home_interaction_route",
    reason: "no_collision_free_route_to_physical_affordance",
    plannerReason: plan?.reason || "no_collision_free_route",
    plannerMode: plan?.mode || "bounded_collision_checked_astar",
    visitedNodes: Number(plan?.visitedNodes || 0),
    target: target ? {
      x: Number(target.x.toFixed(3)),
      y: Number(target.y.toFixed(3)),
      z: Number(target.z.toFixed(3)),
    } : null,
    bodyStayedInPlace: true,
    teleported: false,
    personOwnedIntent: true,
    recordedAt: new Date().toISOString(),
  };
  activeMarker.userData.lastRouteFailureTruth = failure;
  activeMarker.userData.lastEmbodimentCapabilityBlock = {
    ...failure,
    requires: "a collision-free physical path or a different reachable activity",
  };
  activeMarker.userData.navigationRecovery = null;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  activeMarker.userData.gaitMode = null;
  activeMarker.userData.waitUntil = clock.elapsedTime + 0.35;
  setActiveAvatarAction("idle");
  recordMovementLearningAttempt({
    skill: id || "home_interaction_route",
    phase: "route_request_failed_body_stayed_in_place",
    target: label || id || "physical affordance",
    plannerReason: failure.plannerReason,
    visitedNodes: failure.visitedNodes,
    personOwnedIntent: true,
    teleported: false,
  });
  return false;
}

function pointInsideArea2D(pos, area, margin = 0) {
  if (!pos || !area) return false;
  return pos.x >= area.minX - margin && pos.x <= area.maxX + margin && pos.z >= area.minZ - margin && pos.z <= area.maxZ + margin;
}

function activeAvatarPlaceEntry(label, summary, options = {}) {
  const pos = activeMarker?.position || new THREE.Vector3();
  return {
    areaId: options.areaId || label,
    label,
    summary,
    category: options.category || "home_world",
    inside: !!options.inside,
    outside: !!options.outside,
    confidence: options.confidence || "high",
    nearDoor: !!options.nearDoor,
    nearWindow: !!options.nearWindow,
    canEnter: !!options.canEnter,
    canReadHere: !!options.canReadHere,
    canSitHere: !!options.canSitHere,
    canLieHere: !!options.canLieHere,
    canGetCoffeeHere: !!options.canGetCoffeeHere,
    canGetDrinkHere: !!options.canGetDrinkHere,
    canEatHere: !!options.canEatHere,
    canStudyHere: !!options.canStudyHere,
    position: {
      x: Number(pos.x.toFixed(3)),
      y: Number(pos.y.toFixed(3)),
      z: Number(pos.z.toFixed(3)),
    },
  };
}

function activeAvatarNamedPlaceSnapshot() {
  if (!activeMarker) return null;
  const pos = activeMarker.position;
  const y = pos.y;
  const oneBedroomLiving = {
    minX: ONE_BEDROOM_ROOM_SPLIT_X + 0.55,
    maxX: ONE_BEDROOM_HOUSE_RIGHT_X - 0.6,
    minZ: ONE_BEDROOM_BATH_FRONT_Z + 0.35,
    maxZ: ONE_BEDROOM_HOUSE_FRONT_Z - 0.35,
  };
  const oneBedroomKitchen = {
    minX: ONE_BEDROOM_ROOM_SPLIT_X + 0.55,
    maxX: ONE_BEDROOM_HOUSE_RIGHT_X - 0.6,
    minZ: ONE_BEDROOM_HOUSE_BACK_Z + 0.35,
    maxZ: ONE_BEDROOM_BATH_FRONT_Z + 0.35,
  };
  const oneBedroomBedroom = {
    minX: ONE_BEDROOM_HOUSE_LEFT_X + 0.75,
    maxX: ONE_BEDROOM_ROOM_SPLIT_X - 0.35,
    minZ: ONE_BEDROOM_BATH_FRONT_Z + 0.35,
    maxZ: ONE_BEDROOM_HOUSE_FRONT_Z - 0.35,
  };
  const oneBedroomBathroom = {
    minX: ONE_BEDROOM_HOUSE_LEFT_X + 0.75,
    maxX: ONE_BEDROOM_ROOM_SPLIT_X - 0.35,
    minZ: ONE_BEDROOM_HOUSE_BACK_Z + 0.35,
    maxZ: ONE_BEDROOM_BATH_FRONT_Z + 0.2,
  };
  const oneBedroomFrontWalk = {
    minX: ONE_BEDROOM_HOUSE_ENTRY.x - 2.2,
    maxX: ONE_BEDROOM_HOUSE_ENTRY.x + 2.2,
    minZ: ONE_BEDROOM_HOUSE_FRONT_Z - 0.65,
    maxZ: ONE_BEDROOM_HOUSE_FRONT_Z + 4.8,
  };
  const libraryInterior = { minX: 18.0, maxX: 29.5, minZ: 36.0, maxZ: 46.5 };
  const libraryFront = { minX: 17.4, maxX: 30.4, minZ: 30.2, maxZ: 36.2 };
  const starbucksInterior = { minX: -35.5, maxX: -17.3, minZ: 34.5, maxZ: 51.6 };
  const starbucksFront = {
    minX: STARBUCKS_CENTER.x - 4.5,
    maxX: STARBUCKS_CENTER.x + 4.5,
    minZ: STARBUCKS_PUBLIC_FRONT_Z - 2.7,
    maxZ: STARBUCKS_PUBLIC_FRONT_Z + 2.8,
  };
  const schoolInterior = { minX: SCHOOL_CENTER.x - 4.0, maxX: SCHOOL_CENTER.x + 4.0, minZ: SCHOOL_CENTER.z - 3.3, maxZ: SCHOOL_CENTER.z + 3.3 };
  const schoolFront = { minX: SCHOOL_CENTER.x - 4.6, maxX: SCHOOL_CENTER.x + 4.6, minZ: SCHOOL_FRONT_Z - 2.7, maxZ: SCHOOL_FRONT_Z + 1.8 };
  const stripMallFront = { minX: -16.5, maxX: 16.5, minZ: 30.0, maxZ: 39.2 };
  const tardis = activeAvatarHomeTardisStateSnapshot(pos);

  if (tardis?.entered) {
    return activeAvatarPlaceEntry("TARDIS doorway", "inside the open TARDIS doorway", {
      category: "tardis",
      inside: true,
      nearDoor: true,
      canEnter: true,
    });
  }
  if (tardis?.near) {
    return activeAvatarPlaceEntry("TARDIS exterior", "near the TARDIS exterior; not inside unless the doorway says entered", {
      category: "tardis",
      outside: true,
      nearDoor: true,
      canEnter: !!tardis.doorOpen,
    });
  }
  if (y > ACTIVE_AVATAR_SECOND_FLOOR_Y - 0.45) {
    return activeAvatarPlaceEntry("upstairs area", "upstairs in the older main-house area", {
      category: "old_main_house",
      inside: true,
      canReadHere: true,
      canSitHere: true,
    });
  }
  if (pointInsideArea2D(pos, oneBedroomKitchen)) {
    const coffeeDistance = Math.hypot(
      pos.x - ONE_BEDROOM_COFFEE_STATION_USE_SPOT.x,
      pos.z - ONE_BEDROOM_COFFEE_STATION_USE_SPOT.z,
    );
    return activeAvatarPlaceEntry("Kira one-bedroom kitchen", "inside Kira's accepted one-bedroom kitchen", {
      category: "kira_home",
      inside: true,
      canReadHere: true,
      canSitHere: true,
      // Availability is deliberately local to the real station.  Whether she
      // is actually drinking remains controlled by activityTruthForAction().
      canGetCoffeeHere: coffeeDistance <= 1.35,
      canGetDrinkHere: true,
      canEatHere: true,
    });
  }
  if (pointInsideArea2D(pos, oneBedroomLiving)) {
    const nearKitchen = pos.z < ONE_BEDROOM_BATH_FRONT_Z + 2.8 || pos.x > ONE_BEDROOM_ROOM_SPLIT_X + 2.2;
    return activeAvatarPlaceEntry("Kira one-bedroom living/kitchen", "inside Kira's accepted one-bedroom living and kitchen area", {
      category: "kira_home",
      inside: true,
      nearWindow: pos.z > ONE_BEDROOM_HOUSE_FRONT_Z - 2.4,
      canReadHere: true,
      canSitHere: true,
      canGetCoffeeHere: false,
      canGetDrinkHere: nearKitchen,
      canEatHere: nearKitchen,
    });
  }
  if (pointInsideArea2D(pos, oneBedroomBedroom)) {
    return activeAvatarPlaceEntry("Kira one-bedroom bedroom", "inside Kira's accepted one-bedroom bedroom", {
      category: "kira_home",
      inside: true,
      nearWindow: pos.z > ONE_BEDROOM_HOUSE_FRONT_Z - 2.0,
      canReadHere: true,
      canSitHere: true,
      canLieHere: true,
    });
  }
  if (pointInsideArea2D(pos, oneBedroomBathroom)) {
    return activeAvatarPlaceEntry("Kira one-bedroom bathroom", "inside Kira's accepted one-bedroom bathroom", {
      category: "kira_home",
      inside: true,
    });
  }
  // Hall/threshold points that are physically inside the accepted house must
  // never fall through to the generic outdoor-ground label.  This fallback is
  // geometric only; it does not grant coffee, reading, or project evidence.
  if (activeAvatarInsideOneBedroomHome(pos)) {
    return activeAvatarPlaceEntry("Kira one-bedroom interior", "inside Kira's accepted one-bedroom home between named rooms", {
      category: "kira_home",
      inside: true,
    });
  }
  if (pointInsideArea2D(pos, oneBedroomFrontWalk)) {
    return activeAvatarPlaceEntry("Kira one-bedroom front walk", "outside at Kira's one-bedroom front walk or doorway approach", {
      category: "kira_home",
      outside: true,
      nearDoor: true,
      canEnter: true,
    });
  }
  if (pointInsideArea2D(pos, libraryInterior)) {
    return activeAvatarPlaceEntry("public library", "inside or immediately at the public library reading area", {
      category: "library",
      inside: true,
      canReadHere: true,
      canSitHere: true,
    });
  }
  if (pointInsideArea2D(pos, libraryFront)) {
    return activeAvatarPlaceEntry("public library front walk", "outside at the public library front walk", {
      category: "library",
      outside: true,
      nearDoor: true,
      canEnter: true,
    });
  }
  if (pointInsideArea2D(pos, starbucksInterior)) {
    return activeAvatarPlaceEntry("Starbucks cafe", "inside or immediately beside the cafe counter/table area", {
      category: "cafe",
      inside: true,
      canReadHere: true,
      canSitHere: true,
      canGetCoffeeHere: true,
    });
  }
  if (pointInsideArea2D(pos, starbucksFront)) {
    return activeAvatarPlaceEntry("Starbucks entrance walk", "outside at the cafe entrance walk", {
      category: "cafe",
      outside: true,
      nearDoor: true,
      canEnter: true,
    });
  }
  if (pointInsideArea2D(pos, schoolInterior)) {
    return activeAvatarPlaceEntry("empty Home World school room", "inside the empty Home World school learning room", {
      category: "school",
      inside: true,
      canStudyHere: true,
    });
  }
  if (pointInsideArea2D(pos, schoolFront)) {
    return activeAvatarPlaceEntry("Home World school entrance", "outside at the Home World school entrance", {
      category: "school",
      outside: true,
      nearDoor: true,
      canEnter: true,
    });
  }
  if (pointInsideArea2D(pos, stripMallFront)) {
    if (!HOME_WORLD_LEGACY_STRIP_MALL_ENABLED) {
      return activeAvatarPlaceEntry("empty former strip-mall lot", "outside on the intentionally empty former strip-mall lot; there is no shopfront or door to enter", {
        category: "empty_lot",
        outside: true,
        nearDoor: false,
        canEnter: false,
        confidence: "high",
      });
    }
    return activeAvatarPlaceEntry("strip mall shopfront", "outside along the strip mall shopfront wall; opening a door is not the same as being inside", {
      category: "strip_mall",
      outside: true,
      nearDoor: true,
      canEnter: true,
      confidence: "medium",
    });
  }
  const target = activeMarker.userData?.autonomousRoamTarget;
  if (target?.id) {
    return activeAvatarPlaceEntry("Home World ground area", "outside in Home World at an unlabelled current ground position", {
      category: "home_world",
      outside: true,
      confidence: "high",
    });
  }
  return activeAvatarPlaceEntry("Home World ground area", "outside in the Home World ground area", {
    category: "home_world",
    outside: true,
    confidence: "medium",
  });
}

function activeAvatarAffordanceSnapshot(place = activeAvatarNamedPlaceSnapshot()) {
  if (!activeMarker) return {};
  const heldKind = activeHeldProp?.visible ? activeHeldPropKind : "";
  const readTruth = activityTruthForAction("read_book");
  const drinkTruth = activityTruthForAction("drink");
  const coffeeTruth = activityTruthForAction("drink_coffee");
  const projectWorkTruth = activityTruthForAction("project_work");
  const posture = activeMarker.userData?.postureState?.posture || "";
  return {
    read: {
      available: !!(place?.canReadHere || readTruth.grounded || ["book", "notebook", "phone", "tablet", "computer"].includes(heldKind)),
      grounded: !!readTruth.grounded,
      evidence: readTruth.evidence || [],
    },
    sit: {
      available: !!place?.canSitHere,
      grounded: posture === "sit" || !!place?.canSitHere,
    },
    lieDown: {
      available: !!place?.canLieHere,
      grounded: posture === "lie" || !!place?.canLieHere,
    },
    lookWindow: {
      available: !!place?.nearWindow,
      grounded: !!place?.nearWindow,
    },
    coffee: {
      available: !!(place?.canGetCoffeeHere || coffeeTruth.grounded || ["coffee_cup", "cup"].includes(heldKind)),
      grounded: !!coffeeTruth.grounded,
      evidence: coffeeTruth.evidence || [],
    },
    drink: {
      available: !!(place?.canGetDrinkHere || ["coffee_cup", "cup"].includes(heldKind)),
      grounded: !!(drinkTruth.grounded || place?.canGetDrinkHere || ["coffee_cup", "cup"].includes(heldKind)),
      evidence: drinkTruth.evidence || [],
    },
    eat: {
      available: !!place?.canEatHere,
      grounded: !!activityTruthForAction("eat_food").grounded,
    },
    enterDoor: {
      available: !!place?.canEnter,
      grounded: !!place?.nearDoor,
    },
    study: {
      available: !!place?.canStudyHere,
      grounded: !!place?.canStudyHere,
    },
    projectWork: {
      // A nearby computer/tablet/notebook is an available affordance.  It is
      // only grounded as current work while the body is actually using it.
      available: !!(
        projectWorkTruth.grounded
        || (projectWorkTruth.evidence || []).some((item) => item?.kind)
      ),
      grounded: !!projectWorkTruth.grounded,
      activeUse: !!projectWorkTruth.activeUse,
      evidence: projectWorkTruth.evidence || [],
    },
  };
}

function activeAvatarUsingAutonomousRoam() {
  if (!activeMarker || activeMarker.userData.kind === "orb") return false;
  if (activeMarker.userData.practiceRoute || activeSkillInteraction || activeMarker.userData.skillInteraction) return false;
  if (activeMarker.userData.roamZone === "capture_flag") return false;
  // Kira's life-loop model owns her intent.  Random browser-side destinations
  // are not a second mind and must not move her when she chose no action.
  if (activeAvatarIsKiraLike()) return false;
  return true;
}

function activeAvatarPickAutonomousRoamTarget(t, reason = "new_goal") {
  if (!activeMarker) return null;
  const zone = activeMarker.userData.roamZone || activeAvatarDefaultRoamZone();
  const areas = activeAvatarAutonomousRoamAreas(zone);
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const area = areas[Math.floor(Math.random() * areas.length)];
    const candidate = activeAvatarRandomPointInArea(area);
    const distance = Math.hypot(candidate.x - activeMarker.position.x, candidate.z - activeMarker.position.z);
    if (distance < 1.2) continue;
    if (isAvatarBlocked(candidate.x, candidate.z, candidate.y, 0.48)) continue;
    if (!activeAvatarDirectPathIsClear(activeMarker.position, candidate, 0.46)) continue;
    activeMarker.userData.autonomousRoamTarget = {
      id: area.id,
      reason,
      x: candidate.x,
      y: candidate.y,
      z: candidate.z,
      pickedAt: t,
      pathCheckedAt: t,
      pathMode: "direct_collision_verified",
      attempt,
    };
    activeMarker.userData.autonomousGaitMode = area.id.includes("sidewalk") && Math.random() < 0.28 ? "jog" : "walk";
    activeMarker.userData.roamPolicy = "self_directed_random_goal_learning";
    return candidate;
  }
  return null;
}

function activeAvatarCurrentAutonomousTarget(t) {
  if (!activeMarker) return null;
  const stored = activeMarker.userData.autonomousRoamTarget;
  if (stored && !isAvatarBlocked(stored.x, stored.z, stored.y, 0.48)) {
    const target = new THREE.Vector3(stored.x, stored.y, stored.z);
    if (t - Number(stored.pathCheckedAt || 0) < 0.35 || activeAvatarDirectPathIsClear(activeMarker.position, target, 0.46)) {
      stored.pathCheckedAt = t;
      return target;
    }
    activeMarker.userData.autonomousCollisionReplans = (activeMarker.userData.autonomousCollisionReplans || 0) + 1;
    clearActiveAvatarAutonomousRoamTarget("route_obstructed_before_contact");
  }
  return activeAvatarPickAutonomousRoamTarget(t, stored ? "blocked_goal_replanned" : "new_goal");
}

function clearActiveAvatarAutonomousRoamTarget(reason = "cleared") {
  if (!activeMarker) return;
  const oldTarget = activeMarker.userData.autonomousRoamTarget;
  if (oldTarget) {
    activeMarker.userData.autonomousRoamHistory = [
      ...(activeMarker.userData.autonomousRoamHistory || []).slice(-5),
      { ...oldTarget, clearedAt: Number(clock.elapsedTime.toFixed(2)), reason },
    ];
  }
  activeMarker.userData.autonomousRoamTarget = null;
  activeMarker.userData.autonomousGaitMode = null;
}

function maybeStartActiveAvatarAutonomousIdleActivity(t) {
  if (!activeMarker || activeMarker.userData.kind === "orb") return false;
  if (activeMarker.userData.practiceRoute || activeSkillInteraction || activeDoorInteraction || activeFurnitureInteraction || activePostureInteraction) return false;
  const zone = activeMarker.userData.roamZone || activeAvatarDefaultRoamZone();
  if (zone === "capture_flag") return false;
  const floor = activeMarker.position.y >= ACTIVE_AVATAR_SECOND_FLOOR_Y - 0.45 ? "upstairs" : "downstairs";
  const roll = Math.random();
  const nearPoint = (x, z, maxDistance = 1.25) => Math.hypot(activeMarker.position.x - x, activeMarker.position.z - z) <= maxDistance;
  const place = activeAvatarNamedPlaceSnapshot();

  if (activeAvatarIsKiraLike() && (zone === "kira_home_world" || zone === "kira_bungalow")) {
    if (place?.label === "Kira one-bedroom living/kitchen") {
      if (roll < 0.34) {
        show(`${activeAvatarDisplayName()} chooses to settle on the couch with the tablet. She can keep reading for hours instead of being forced back into pacing.`);
        return startActiveAvatarPersistentHomeRead({
          seconds: ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY.initialReviewSeconds,
        });
      }
      if (roll < 0.56) {
        show(`${activeAvatarDisplayName()} sits on the couch for a quiet pause.`);
        return startActiveAvatarHomeSitHold({ seconds: 18 + Math.random() * 32 });
      }
      if (roll < 0.74 && place.nearWindow) {
        show(`${activeAvatarDisplayName()} stands by the living window and looks out.`);
        return startActiveAvatarHomeWindowHold({ seconds: 14 + Math.random() * 24 });
      }
      if (roll < 0.86) {
        show(`${activeAvatarDisplayName()} goes to the kitchen for a drink.`);
        return startActiveAvatarKitchenDrinkHold({
          seconds: 10 + Math.random() * 18,
          selfChosen: true,
        });
      }
    }
    if (place?.label === "Kira one-bedroom bedroom") {
      if (roll < 0.42) {
        show(`${activeAvatarDisplayName()} lies down on the bed for a rest.`);
        return startActiveAvatarHomeLieHold({ seconds: 24 + Math.random() * 42 });
      }
      if (roll < 0.74) {
        show(`${activeAvatarDisplayName()} reads on the bed with the tablet.`);
        return startActiveAvatarHomeReadHold({ where: "bed", seconds: 24 + Math.random() * 38 });
      }
    }
    if (place?.category === "library" && place.inside) {
      if (roll < 0.88) {
        show(`${activeAvatarDisplayName()} stays in the library and reads instead of immediately leaving.`);
        return startActiveAvatarLibraryReadPractice(26 + Math.random() * 40);
      }
    }
    if (place?.category === "cafe" && place.inside) {
      if (roll < 0.58) {
        show(`${activeAvatarDisplayName()} pauses at the cafe counter with a cup.`);
        return startActiveAvatarHoldSkill({
          id: "autonomous_cafe_coffee_pause",
          label: "cafe coffee pause",
          action: "drink_coffee",
          truthAction: "drink_coffee",
          seconds: 14 + Math.random() * 24,
          position: STARBUCKS_COUNTER_SPOT.clone(),
          yaw: Math.PI,
          postureState: {
            id: "autonomous_cafe_coffee_pause",
            posture: "stand_drink",
            rootTiltX: 0.02,
            rootYOffset: 0,
          },
          heldPropKind: "coffee_cup",
        }, t);
      }
    }
    if (place?.category === "school" && place.inside) {
      if (roll < 0.5) {
        show(`${activeAvatarDisplayName()} stands in the empty school room and waits for the learning program instead of inventing a class.`);
        return startActiveAvatarHoldSkill({
          id: "autonomous_school_room_wait",
          label: "empty school room wait",
          action: "stand_think",
          seconds: 12 + Math.random() * 24,
          position: SCHOOL_CENTER.clone(),
          yaw: Math.PI,
          postureState: {
            id: "autonomous_school_room_wait",
            posture: "stand_look",
            rootTiltX: 0.02,
            rootYOffset: 0,
          },
        }, t);
      }
    }
  }

  if (floor === "downstairs" && (zone === "downstairs" || zone === "home" || zone === "generic")) {
    if (roll < 0.36 && nearPoint(-6.62, 4.72, 1.2)) {
      show(`${activeAvatarDisplayName()} chooses a book from the home shelf instead of pacing.`);
      return startActiveAvatarHoldSkill({
        id: "autonomous_home_bookshelf_read",
        label: "home living room bookshelf",
        action: "read_book",
        truthAction: "read_book",
        seconds: 5.5 + Math.random() * 6.0,
        yaw: Math.PI / 2,
        postureState: {
          id: "autonomous_home_bookshelf_read",
          posture: "read",
          rootTiltX: 0.04,
          rootYOffset: -0.05,
        },
      }, t);
    }
    if (roll < 0.64 && nearPoint(-5.15, 2.56, 1.35)) {
      show(`${activeAvatarDisplayName()} sits down for a short rest instead of walking another loop.`);
      return startActiveAvatarHoldSkill({
        id: "autonomous_living_room_couch_rest",
        label: "living room couch rest",
        action: "sit",
        seconds: 5.0 + Math.random() * 5.0,
        yaw: 0,
        postureState: {
          id: "autonomous_living_room_couch_rest",
          posture: "sit",
          rootTiltX: 0,
          rootYOffset: -0.28,
        },
      }, t);
    }
  }

  if (floor === "upstairs" && activeAvatarIsMarinetteLike() && roll < 0.22 && nearPoint(5.85, -5.9, 1.35)) {
    show(`${activeAvatarDisplayName()} lies down briefly instead of pacing upstairs.`);
    return startActiveAvatarHoldSkill({
      id: "autonomous_marinette_bed_rest",
      label: "Marinette temporary bed rest",
      action: "lie_down",
      seconds: 6.0 + Math.random() * 6.0,
      yaw: Math.PI,
      postureState: {
        id: "autonomous_marinette_bed_rest",
        posture: "lie",
        rootTiltX: Math.PI / 2,
        rootYOffset: -0.18,
      },
    }, t);
  }
  return false;
}

function activeAvatarCurrentPracticeStops() {
  if (!activeMarker || !activeAvatarIsMarinetteLike() || activeMarker.userData.practiceRoute || !ACTIVE_AVATAR_AUTO_PRACTICE_STOPS) {
    return new Map();
  }
  return activeMarker?.userData?.roamZone === "upstairs" ? marinetteUpstairsPracticeStops : marinetteRoamPracticeStops;
}

function startActiveAvatarStairPracticeRoute(fromCurrent = false) {
  if (!activeMarker) return false;
  activePostureInteraction = null;
  activeDoorInteraction = null;
  activeFurnitureInteraction = null;
  activeSkillInteraction = null;
  clearDoorReachRig();
  const route = marinetteStairPracticeWaypoints.map((point) => point.clone());
  if (fromCurrent) route.unshift(activeMarker.position.clone());
  else activeMarker.position.copy(marinetteStairPracticeWaypoints[0]);
  activeMarker.userData.practiceRoute = {
    id: "stairs_step",
    waypoints: route,
    finishZone: "upstairs",
  };
  activeMarker.userData.stairTraversalActive = true;
  activeMarker.userData.roamIndex = 1;
  activeMarker.userData.waitUntil = 0;
  activeMarker.userData.stuckSince = null;
  activeMarker.userData.lastDistanceToTarget = null;
  activeMarker.userData.postureState = null;
  activeMarker.userData.doorInteraction = null;
  activeMarker.userData.furnitureInteraction = null;
  setActiveAvatarAction("walk");
  recordMovementLearningAttempt({ skill: "stairs_step", phase: "practice_started", target: "main stairs" });
  return true;
}

function clearActiveAvatarPracticeInteractions() {
  activePostureInteraction = null;
  activeDoorInteraction = null;
  activeFurnitureInteraction = null;
  activeSkillInteraction = null;
  basketballPracticeState = null;
  activeKiraArmTestState = null;
  activeKiraDoctorExamState = null;
  clearActiveHeldProp();
  clearDoorReachRig();
  if (!activeMarker) return;
  clearActiveAvatarAutonomousRoamTarget("practice_or_skill_started");
  activeMarker.userData.postureState = null;
  activeMarker.userData.doorInteraction = null;
  activeMarker.userData.furnitureInteraction = null;
  activeMarker.userData.skillInteraction = null;
  activeMarker.userData.gaitMode = null;
  activeMarker.userData.practiceRoute = null;
  activeMarker.userData.stairTraversalActive = false;
}

function activeAvatarLocomotionActionForGait(gaitMode = "walk") {
  const mode = String(gaitMode || "walk").toLowerCase();
  if (mode === "run") return "run";
  if (mode === "jog") return "jog";
  return "walk";
}

function startActiveAvatarPracticeRouteSkill(id, waypoints, options = {}) {
  if (!activeMarker || !waypoints?.length) return false;
  clearActiveAvatarPracticeInteractions();
  clearActiveAvatarAutonomousRoamTarget("practice_route_started");
  // Preserve body continuity.  Older practice routes copied the avatar to the
  // route's first point, which made a route look successful even when no walk
  // occurred.  Always begin from the body's actual current position.
  const route = [activeMarker.position.clone(), ...waypoints.map((point) => point.clone())];
  const startPosition = activeMarker.position.clone();
  activeMarker.userData.practiceRoute = {
    id,
    waypoints: route,
    finishZone: options.finishZone || activeMarker.userData.roamZone || activeAvatarDefaultRoamZone(),
    gaitMode: options.gaitMode || "walk",
    speed: options.speed || null,
    locomotionAction: options.action || activeAvatarLocomotionActionForGait(options.gaitMode || "walk"),
    finishHold: options.finishHold || null,
    selfChosen: !!options.selfChosen,
    requiresHomeEntry: !!options.requiresHomeEntry,
    homeEntryReplanCount: 0,
    homeEntryReplanAt: null,
    interiorRoute: !!options.interiorRoute,
    interiorGoal: options.interiorGoal?.clone?.() || null,
    interactionTarget: options.interactionTarget?.clone?.() || null,
    interiorPlanMode: options.interiorPlanMode || null,
    interiorPlanVisitedNodes: Number(options.interiorPlanVisitedNodes || 0),
    interiorReplanCount: 0,
    interiorReplanAt: null,
    coalescedIntentCount: 0,
    progressWatch: null,
    postEntryWaypoints: (options.postEntryWaypoints || []).map((point) => point.clone()),
    waypointLabels: ["current_body_position", ...(options.waypointLabels || [])],
  };
  activeMarker.userData.roamReady = true;
  activeMarker.userData.roamIndex = Math.min(1, route.length - 1);
  activeMarker.userData.waitUntil = 0;
  activeMarker.userData.stuckSince = null;
  activeMarker.userData.lastDistanceToTarget = null;
  activeMarker.userData.lastRouteFailureTruth = null;
  activeMarker.userData.gaitMode = options.gaitMode || "walk";
  activeMarker.userData.skillInteraction = id;
  activeMarker.userData.transitionEvidence = {
    mode: options.gaitMode || "walk",
    teleported: false,
    startedAt: new Date().toISOString(),
    start: {
      x: Number(startPosition.x.toFixed(3)),
      y: Number(startPosition.y.toFixed(3)),
      z: Number(startPosition.z.toFixed(3)),
    },
    path: [{
      x: Number(startPosition.x.toFixed(3)),
      y: Number(startPosition.y.toFixed(3)),
      z: Number(startPosition.z.toFixed(3)),
    }],
    pathSampleCount: 1,
    distanceMeters: 0,
    collisionBlocked: false,
    completed: false,
    personOwnedIntent: !!options.selfChosen,
  };
  setActiveAvatarAction(activeMarker.userData.practiceRoute.locomotionAction);
  recordMovementLearningAttempt({
    skill: id,
    phase: "practice_started",
    target: options.label || id,
    gaitMode: activeMarker.userData.gaitMode,
    selfChosen: !!options.selfChosen,
  });
  return true;
}

function startActiveAvatarHoldSkill(spec, t = clock.elapsedTime) {
  if (!activeMarker || !spec) return false;
  const targetDistance = spec.position
    ? Math.hypot(spec.position.x - activeMarker.position.x, spec.position.z - activeMarker.position.z)
    : 0;
  if (spec.position && (targetDistance > 0.55 || Math.abs(spec.position.y - activeMarker.position.y) > 0.2)) {
    activeMarker.userData.lastEmbodimentCapabilityBlock = {
      id: spec.id,
      reason: "body_not_at_interaction_target_no_teleport_allowed",
      targetDistanceMeters: Number(targetDistance.toFixed(3)),
      recordedAt: new Date().toISOString(),
    };
    recordMovementLearningAttempt({
      skill: spec.id,
      phase: "hold_blocked_no_teleport",
      target: spec.label || spec.id,
      targetDistanceMeters: Number(targetDistance.toFixed(3)),
    });
    return false;
  }
  const readingRequested = /\b(read|reading|read_book|read_tablet|ebook|e-book)\b/i.test(
    `${spec.action || ""} ${spec.truthAction || ""}`,
  );
  if (readingRequested) {
    const readingTruth = activityTruthForAction("read_book");
    const independentEvidence = (readingTruth.evidence || []).find((item) => {
      const label = String(item?.label || "").toLowerCase();
      return label
        && !label.startsWith("held ")
        && !label.startsWith("active avatar held ")
        && Number(item?.distanceMeters ?? 999) <= 2.25;
    });
    if (!readingTruth.grounded || !independentEvidence) {
      activeMarker.userData.lastEmbodimentCapabilityBlock = {
        id: spec.id,
        reason: "reading_source_prop_not_visible_or_reachable",
        truthAction: "read_book",
        requirement: readingTruth.requirement || "a visible reachable book or tablet",
        recordedAt: new Date().toISOString(),
      };
      activeMarker.userData.isMoving = false;
      activeMarker.userData.walkSpeed = 0;
      activeMarker.userData.lastStepMeters = 0;
      activeMarker.userData.gaitMode = null;
      setActiveAvatarAction("idle");
      recordMovementLearningAttempt({
        skill: spec.id,
        phase: "hold_blocked_missing_reading_source",
        target: spec.label || spec.id,
        truthGrounded: !!readingTruth.grounded,
        reason: "reading_source_prop_not_visible_or_reachable",
      });
      return false;
    }
    activeMarker.userData.readingSourceEvidence = {
      kind: independentEvidence.kind || null,
      label: independentEvidence.label || null,
      distanceMeters: independentEvidence.distanceMeters ?? null,
      confirmedAt: new Date().toISOString(),
    };
  }
  const projectWorkRequested = ACTIVITY_TRUTH_RULES
    .find((rule) => rule.id === "project_work")
    ?.tests.some((test) => test.test(`${spec.action || ""} ${spec.truthAction || ""}`.toLowerCase()));
  if (projectWorkRequested) {
    const projectTruth = activityTruthForAction("project_work");
    const independentWorkTool = (projectTruth.evidence || []).find((item) => {
      const label = String(item?.label || "").toLowerCase();
      return label
        && !label.startsWith("held ")
        && !label.startsWith("active avatar held ")
        && Number(item?.distanceMeters ?? 999) <= 2.25;
    });
    if (!independentWorkTool) {
      activeMarker.userData.lastEmbodimentCapabilityBlock = {
        id: spec.id,
        reason: "project_work_tool_not_visible_or_reachable",
        truthAction: spec.truthAction || spec.action || "project_work",
        requirement: projectTruth.requirement,
        recordedAt: new Date().toISOString(),
      };
      activeMarker.userData.isMoving = false;
      activeMarker.userData.walkSpeed = 0;
      activeMarker.userData.lastStepMeters = 0;
      activeMarker.userData.gaitMode = null;
      setActiveAvatarAction("idle");
      recordMovementLearningAttempt({
        skill: spec.id,
        phase: "hold_blocked_missing_project_work_tool",
        target: spec.label || spec.id,
        reason: "project_work_tool_not_visible_or_reachable",
      });
      return false;
    }
    activeMarker.userData.projectWorkToolEvidence = {
      kind: independentWorkTool.kind || null,
      label: independentWorkTool.label || null,
      distanceMeters: independentWorkTool.distanceMeters ?? null,
      reachedAt: new Date().toISOString(),
    };
  }
  clearActiveAvatarPracticeInteractions();
  activeSkillInteraction = {
    kind: "hold",
    id: spec.id,
    label: spec.label || spec.id,
    action: spec.action || "idle",
    startedAt: t,
    seconds: Number.isFinite(spec.seconds) ? spec.seconds : 2.0,
    position: spec.position?.clone?.() || null,
    yaw: Number.isFinite(spec.yaw) ? spec.yaw : null,
    phase: Number.isFinite(spec.yaw) ? "aligning_yaw" : "holding",
    holdStartedAt: Number.isFinite(spec.yaw) ? null : t,
    postureState: spec.postureState || null,
    truthAction: spec.truthAction || spec.action || "",
    heldPropKind: spec.heldPropKind || "",
    persistentQuietActivity: !!spec.persistentQuietActivity,
    selfChosen: !!spec.selfChosen,
    nextContinuationReviewAt: spec.persistentQuietActivity
      ? t + Math.max(
        ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY.minimumSelfChosenSeconds,
        Number.isFinite(spec.seconds) ? spec.seconds : ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY.initialReviewSeconds,
      )
      : null,
    continuationCount: 0,
    chatActive: false,
    chatInterruptions: 0,
    voluntaryExitAvailable: !!spec.persistentQuietActivity,
    startedAtIso: new Date().toISOString(),
  };
  activeMarker.userData.skillInteraction = activeSkillInteraction.id;
  activeMarker.userData.gaitMode = null;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  // Do not copy the body onto the target or snap its yaw. The preceding route
  // must bring the body into the zone, then the bounded turn controller aligns
  // it over visible frames before the hold/posture begins.
  activeMarker.userData.postureState = Number.isFinite(activeSkillInteraction.yaw)
    ? null
    : activeSkillInteraction.postureState;
  if (activeSkillInteraction.phase === "holding" && activeSkillInteraction.postureState?.surface) {
    activeMarker.userData.supportState = {
      id: activeSkillInteraction.postureState.surface,
      supported: true,
      falling: false,
      y: Number(activeMarker.position.y.toFixed(3)),
      floor: activeMarker.position.y > 1.8 ? 1 : 0,
    };
  }
  if (!activeMarker.userData.transitionEvidence) {
    activeMarker.userData.transitionEvidence = {
      mode: "already_at_target",
      teleported: false,
      pathSampleCount: 1,
      distanceMeters: 0,
      collisionBlocked: false,
      completed: true,
    };
  }
  if (activeSkillInteraction.heldPropKind && activeSkillInteraction.phase === "holding") {
    setActiveHeldProp(activeSkillInteraction.heldPropKind);
  }
  if (activeSkillInteraction.phase === "holding" && activeSkillInteraction.heldPropKind === "basketball") {
    basketballPracticeState = {
      startedAt: t,
      seconds: activeSkillInteraction.seconds,
      phase: "pick_up_dribble_shoot",
      shotTarget: BASKETBALL_SHOT_TARGET.clone(),
    };
    if (basketballBallRoot) basketballBallRoot.visible = false;
  }
  setActiveAvatarAction(activeSkillInteraction.phase === "aligning_yaw" ? "idle" : activeSkillInteraction.action);
  recordMovementLearningAttempt({
    skill: activeSkillInteraction.id,
    phase: "hold_started",
    target: activeSkillInteraction.label,
    action: activeSkillInteraction.action,
    persistentQuietActivity: activeSkillInteraction.persistentQuietActivity,
    selfChosen: activeSkillInteraction.selfChosen,
  });
  return true;
}

function activeAvatarHomeReadHoldSpec(options = {}) {
  const place = activeAvatarNamedPlaceSnapshot();
  const seconds = options.seconds || 18 + Math.random() * 38;
  const inBedroom = place?.label === "Kira one-bedroom bedroom" || options.where === "bed";
  const position = inBedroom ? KIRA_BED_SLEEP_SPOT.clone() : oneBedroomCouchSeatSpot();
  return {
    id: inBedroom ? "autonomous_bed_tablet_read" : "autonomous_couch_tablet_read",
    label: inBedroom ? "bed reading with tablet" : "couch reading with tablet",
    action: "read_tablet",
    truthAction: "read_book",
    seconds,
    position,
    yaw: inBedroom ? Math.PI / 2 : 0,
    postureState: {
      id: inBedroom ? "autonomous_bed_tablet_read" : "autonomous_couch_tablet_read",
      posture: inBedroom ? "lie" : "sit",
      rootTiltX: inBedroom ? Math.PI / 2 : 0.02,
      rootYOffset: inBedroom ? -0.2 : -0.22,
      surface: inBedroom ? "one_bedroom_bed" : "one_bedroom_couch_front_edge",
    },
    heldPropKind: "tablet",
    persistentQuietActivity: !!options.persistentQuietActivity,
    selfChosen: !!options.selfChosen,
  };
}

function startActiveAvatarHomeReadHold(options = {}) {
  if (!activeMarker) return false;
  const place = activeAvatarNamedPlaceSnapshot();
  const seconds = options.seconds || 18 + Math.random() * 38;
  if (place?.category === "library" && !options.where) return startActiveAvatarLibraryReadPractice(seconds);
  return startActiveAvatarHoldSkill(activeAvatarHomeReadHoldSpec({ ...options, seconds }));
}

function startActiveAvatarPersistentHomeRead(options = {}) {
  if (!activeMarker) return false;
  const seconds = Math.max(
    ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY.minimumSelfChosenSeconds,
    Number(options.seconds) || ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY.initialReviewSeconds,
  );
  const holdSpec = activeAvatarHomeReadHoldSpec({
    ...options,
    where: options.where || "couch",
    seconds,
    persistentQuietActivity: true,
    selfChosen: true,
  });
  return routeActiveAvatarToHomeHold(holdSpec, {
    routeId: "walk_to_persistent_couch_reading",
    label: "walk naturally to the couch for self-chosen long reading",
    approach: holdSpec.position.clone().add(new THREE.Vector3(0, 0, -0.5)),
  });
}

function startActiveAvatarTabletWorkHold(options = {}) {
  if (!activeMarker) return false;
  const mode = options.mode === "creative_write" ? "creative_write" : options.mode === "look_online" ? "look_online" : "take_notes";
  const labels = {
    creative_write: "creative writing on the coffee-table tablet",
    look_online: "review-safe online look-up request on the coffee-table tablet",
    take_notes: "notes on the coffee-table tablet",
  };
  const holdSpec = {
    id: `home_tablet_${mode}`,
    label: labels[mode],
    action: mode,
    truthAction: mode,
    seconds: options.seconds || 18 + Math.random() * 28,
    position: oneBedroomCouchSeatSpot(),
    yaw: 0,
    postureState: {
      id: `home_tablet_${mode}`,
      posture: "sit_tablet",
      rootTiltX: 0.035,
      rootYOffset: -0.22,
      surface: "one_bedroom_couch_front_edge",
    },
    heldPropKind: "tablet",
  };
  return routeActiveAvatarToHomeHold(holdSpec, {
    routeId: `walk_to_home_tablet_${mode}`,
    label: `walk naturally to the couch for ${labels[mode]}`,
    approach: oneBedroomCouchSeatSpot().add(new THREE.Vector3(0, 0, -0.5)),
  });
}

function routeActiveAvatarToHomeHold(holdSpec, options = {}) {
  if (!activeMarker || !holdSpec?.position) return false;
  const target = holdSpec.position;
  const distance = Math.hypot(target.x - activeMarker.position.x, target.z - activeMarker.position.z);
  if (distance <= 0.55 && Math.abs(target.y - activeMarker.position.y) <= 0.2) {
    return startActiveAvatarHoldSkill(holdSpec);
  }
  const insideHome = activeAvatarInsideOneBedroomHome(activeMarker.position);
  const entryWaypoints = insideHome ? [] : oneBedroomHomeEntryCorridorWaypoints();
  const interiorStart = insideHome
    ? activeMarker.position.clone()
    : entryWaypoints[entryWaypoints.length - 1]?.clone?.();
  const interiorPlan = planActiveAvatarOneBedroomInteriorRoute(
    interiorStart,
    target,
    options.routeId || holdSpec.id,
  );
  if (!interiorPlan.ok || !interiorPlan.waypoints.length) {
    return stopActiveAvatarForRouteRequestFailure(
      options.routeId || `walk_to_${holdSpec.id}`,
      options.label || holdSpec.label,
      interiorPlan,
      target,
    );
  }
  const destinationWaypoints = interiorPlan.waypoints;
  const waypoints = [...entryWaypoints, ...destinationWaypoints];
  return startActiveAvatarPracticeRouteSkill(options.routeId || `walk_to_${holdSpec.id}`, waypoints, {
    label: options.label || `walk naturally to ${holdSpec.label}`,
    finishZone: "kira_home_world",
    gaitMode: "walk",
    speed: 0.82,
    action: "walk",
    finishHold: holdSpec,
    selfChosen: !!holdSpec.selfChosen,
    requiresHomeEntry: !insideHome,
    interiorRoute: true,
    interiorGoal: target,
    interactionTarget: target,
    interiorPlanMode: interiorPlan.mode,
    interiorPlanVisitedNodes: interiorPlan.visitedNodes,
    postEntryWaypoints: destinationWaypoints,
    waypointLabels: [
      ...(insideHome ? [] : ["outside_door_threshold", "door_opening_center", "inside_door_threshold"]),
      ...destinationWaypoints.map((_, index) => (
        index === destinationWaypoints.length - 1 ? "interaction_target" : `collision_free_detour_${index + 1}`
      )),
    ],
  });
}

function startActiveAvatarHomeEntryWalk(options = {}) {
  if (!activeMarker) return false;
  if (activeAvatarInsideOneBedroomHome(activeMarker.position)) {
    recordMovementLearningAttempt({
      skill: "walk_inside_home",
      phase: "already_inside_no_route_needed",
      target: "inside front-door threshold",
      teleported: false,
      personOwnedIntent: !!options.selfChosen,
    });
    return true;
  }
  return startActiveAvatarPracticeRouteSkill(
    "walk_inside_home",
    oneBedroomHomeEntryCorridorWaypoints(),
    {
      label: "walk through the centered front doorway and stop safely inside",
      finishZone: "kira_home_world",
      gaitMode: "walk",
      speed: 0.82,
      action: "walk",
      selfChosen: !!options.selfChosen,
      requiresHomeEntry: true,
      postEntryWaypoints: [],
      waypointLabels: [
        "outside_door_threshold",
        "door_opening_center",
        "inside_door_threshold",
      ],
    },
  );
}

function startActiveAvatarHomeExitWalk(options = {}) {
  if (!activeMarker) return false;
  if (!activeAvatarInsideOneBedroomHome(activeMarker.position)) {
    recordMovementLearningAttempt({
      skill: "walk_outside_home",
      phase: "already_outside_no_exit_route_needed",
      target: "front walk outside Kira's home",
      teleported: false,
      personOwnedIntent: !!options.selfChosen,
    });
    return true;
  }

  const exitCorridor = oneBedroomHomeEntryCorridorWaypoints().reverse();
  const insideThreshold = exitCorridor[0];
  const interiorPlan = planActiveAvatarOneBedroomInteriorRoute(
    activeMarker.position.clone(),
    insideThreshold,
    "walk_outside_home",
  );
  if (!interiorPlan.ok || !interiorPlan.waypoints.length) {
    return stopActiveAvatarForRouteRequestFailure(
      "walk_outside_home",
      "walk through the front door and continue outside",
      interiorPlan,
      insideThreshold,
    );
  }

  const continuation = exitCorridor[exitCorridor.length - 1].clone();
  continuation.z += 1.8;
  const waypoints = [
    ...interiorPlan.waypoints,
    ...exitCorridor.slice(1),
    continuation,
  ];
  return startActiveAvatarPracticeRouteSkill("walk_outside_home", waypoints, {
    label: "walk through the centered front doorway and continue outside",
    finishZone: "kira_home_world",
    gaitMode: "walk",
    speed: 0.82,
    action: "walk",
    selfChosen: !!options.selfChosen,
    waypointLabels: [
      ...interiorPlan.waypoints.map((_, index) => (
        index === interiorPlan.waypoints.length - 1 ? "inside_door_threshold" : `collision_free_exit_detour_${index + 1}`
      )),
      "door_opening_center",
      "outside_door_threshold",
      "front_walk_outside",
    ],
  });
}

function startActiveAvatarHomeSitHold(options = {}) {
  if (!activeMarker) return false;
  const holdSpec = {
    id: "autonomous_home_couch_sit",
    label: "couch sit and think",
    action: "sit",
    seconds: options.seconds || 14 + Math.random() * 32,
    position: oneBedroomCouchSeatSpot(),
    yaw: 0,
    postureState: {
      id: "autonomous_home_couch_sit",
      posture: "sit",
      rootTiltX: 0,
      rootYOffset: -0.22,
      surface: "one_bedroom_couch_front_edge",
    },
    persistentQuietActivity: !!options.persistentQuietActivity,
    selfChosen: !!options.selfChosen,
  };
  return routeActiveAvatarToHomeHold(holdSpec, {
    routeId: "walk_to_home_couch_sit",
    approach: oneBedroomCouchSeatSpot().add(new THREE.Vector3(0, 0, -0.5)),
  });
}

function startActiveAvatarHomeLieHold(options = {}) {
  if (!activeMarker) return false;
  const onCouch = options.where === "couch";
  const sleeping = options.sleep === true;
  const position = onCouch ? oneBedroomCouchSeatSpot() : KIRA_BED_SLEEP_SPOT.clone();
  const holdSpec = {
    id: onCouch ? "kira_lie_couch" : sleeping ? "kira_sleep_bed" : "kira_lie_bed",
    label: onCouch ? "lie on the couch" : sleeping ? "sleep in bed" : "lie in bed",
    action: sleeping ? "lie_down" : "lie_down",
    seconds: options.seconds || 18 + Math.random() * 42,
    position,
    yaw: Math.PI / 2,
    postureState: {
      id: onCouch ? "kira_lie_couch" : sleeping ? "kira_sleep_bed" : "kira_lie_bed",
      posture: sleeping ? "sleep" : "lie",
      rootTiltX: Math.PI / 2,
      rootYOffset: -0.18,
      surface: onCouch ? "one_bedroom_couch" : "one_bedroom_bed",
    },
    persistentQuietActivity: !!options.persistentQuietActivity,
    selfChosen: !!options.selfChosen,
  };
  return routeActiveAvatarToHomeHold(holdSpec, {
    routeId: onCouch ? "walk_to_lie_on_couch" : "walk_to_lie_in_bed",
    approach: onCouch
      ? oneBedroomCouchSeatSpot().add(new THREE.Vector3(0, 0, -0.5))
      : KIRA_BED_STAND_SPOT.clone(),
  });
}

function activeAvatarCurrentGroundLieClearance() {
  if (!activeMarker) return { clear: false, reason: "no_active_body" };
  const support = activeAvatarSupportAt(activeMarker.position);
  if (!support || support.falling) return { clear: false, reason: "ground_support_required" };
  const yaw = activeMarker.rotation.y || 0;
  const forwardX = Math.sin(yaw);
  const forwardZ = Math.cos(yaw);
  const sideX = Math.cos(yaw);
  const sideZ = -Math.sin(yaw);
  const samples = [];
  for (const along of [-0.82, -0.45, 0, 0.45, 0.82]) {
    for (const across of [-0.24, 0, 0.24]) {
      const point = {
        x: activeMarker.position.x + forwardX * along + sideX * across,
        y: activeMarker.position.y,
        z: activeMarker.position.z + forwardZ * along + sideZ * across,
      };
      const pointSupport = activeAvatarSupportAt(point);
      const blocked = isAvatarBlocked(point.x, point.z, point.y, 0.16);
      const sameLevel = !!pointSupport && Math.abs(pointSupport.y - support.y) <= 0.12;
      samples.push({ along, across, blocked, supported: sameLevel });
    }
  }
  const clear = samples.every((sample) => !sample.blocked && sample.supported);
  return {
    clear,
    reason: clear ? null : "clear_supported_body_length_floor_area_required",
    supportId: support.id || "supported_floor",
    samples,
  };
}

function startActiveAvatarGroundLieHold(options = {}) {
  if (!activeMarker) return false;
  const clearance = activeAvatarCurrentGroundLieClearance();
  if (!clearance.clear) return activeAvatarRecordVoluntaryActionBlock("lie_on_ground", clearance.reason);
  activeMarker.userData.groundLieClearance = {
    supportId: clearance.supportId,
    sampleCount: clearance.samples.length,
    blockedSamples: clearance.samples.filter((sample) => sample.blocked || !sample.supported).length,
    checkedAt: new Date().toISOString(),
  };
  return startActiveAvatarHoldSkill({
    id: "kira_lie_ground",
    label: "lie on the current supported floor or ground and look upward",
    action: "lie_down",
    seconds: Number(options.seconds) || 90,
    yaw: activeMarker.rotation.y || 0,
    postureState: {
      id: "kira_lie_ground",
      posture: "lie",
      rootTiltX: Math.PI / 2,
      // Two isolated-browser bounds passes converged from 0.16 -> 0.104 ->
      // 0.094 to target the reviewed 8 mm clearance without changing X/Z.
      rootYOffset: 0.094,
      surface: clearance.supportId,
      lookingDirection: "upward",
      positionChangedForPosture: false,
    },
    persistentQuietActivity: !!options.persistentQuietActivity,
    selfChosen: options.selfChosen !== false,
  });
}

function activeAvatarRecordVoluntaryActionBlock(intent, reason) {
  if (!activeMarker) return false;
  activeMarker.userData.lastEmbodimentCapabilityBlock = {
    id: String(intent || "body_action"),
    reason,
    source: "subject_runtime_intent",
    recordedAt: new Date().toISOString(),
  };
  recordMovementLearningAttempt({ skill: String(intent || "body_action"), phase: "voluntary_action_blocked", target: reason });
  return false;
}

function startActiveAvatarVoluntaryBodyIntent(intent, options = {}) {
  if (!activeMarker || activeMarker.userData.kind === "orb") return false;
  if (options.source !== "subject_runtime_intent") {
    return activeAvatarRecordVoluntaryActionBlock(intent, "requires_subject_runtime_choice_not_external_force");
  }
  const normalized = String(intent || "").toLowerCase().trim();
  const longChoice = options.continueUntilVoluntaryExit === true;
  const longSeconds = ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY.initialReviewSeconds;
  if (/^(sit|sit_down|sit_on_couch)$/.test(normalized)) {
    return startActiveAvatarHomeSitHold({
      seconds: longChoice ? longSeconds : Number(options.seconds) || 60,
      persistentQuietActivity: longChoice,
      selfChosen: true,
    });
  }
  if (/^(lie_on_couch|lay_on_couch)$/.test(normalized)) {
    return startActiveAvatarHomeLieHold({
      where: "couch",
      seconds: longChoice ? longSeconds : Number(options.seconds) || 90,
      persistentQuietActivity: longChoice,
      selfChosen: true,
    });
  }
  if (/^(lie_on_bed|lay_on_bed|rest|sleep)$/.test(normalized)) {
    const sleeping = normalized === "sleep";
    return startActiveAvatarHomeLieHold({
      where: "bed",
      sleep: sleeping,
      seconds: sleeping || longChoice ? longSeconds : Number(options.seconds) || 90,
      persistentQuietActivity: sleeping || longChoice,
      selfChosen: true,
    });
  }
  if (/^(lie_on_ground|lay_on_ground|lie_on_floor|lay_on_floor|look_at_sky)$/.test(normalized)) {
    return startActiveAvatarGroundLieHold({
      seconds: longChoice ? longSeconds : Number(options.seconds) || 90,
      persistentQuietActivity: longChoice,
      selfChosen: true,
    });
  }
  const support = activeMarker.userData.supportState;
  if (!support?.supported || support.falling) {
    return activeAvatarRecordVoluntaryActionBlock(normalized, "ground_support_required");
  }
  if (normalized === "raise_hand") {
    return startActiveAvatarHoldSkill({
      id: "voluntary_raise_hand",
      label: "raise one hand",
      action: "raise_hand",
      seconds: Number(options.seconds) || 3.5,
      selfChosen: true,
    });
  }
  if (normalized === "push_up") {
    const clear = [0, Math.PI / 2, Math.PI, Math.PI * 1.5].every((angle) => (
      !isAvatarBlocked(
        activeMarker.position.x + Math.cos(angle) * 0.72,
        activeMarker.position.z + Math.sin(angle) * 0.72,
        activeMarker.position.y,
        0.34,
      )
    ));
    if (!clear) return activeAvatarRecordVoluntaryActionBlock(normalized, "clear_supported_floor_area_required");
    return startActiveAvatarHoldSkill({
      id: "voluntary_push_up",
      label: "push-up on a clear supported floor",
      action: "push_up",
      seconds: Number(options.seconds) || 8,
      postureState: {
        id: "voluntary_push_up",
        posture: "exercise_prone",
        rootTiltX: Math.PI / 2,
        rootYOffset: 0.18,
        surface: support.id || "current_supported_floor",
      },
      selfChosen: true,
    });
  }
  return activeAvatarRecordVoluntaryActionBlock(normalized, "unknown_voluntary_body_intent");
}

function startActiveAvatarHomeWindowHold(options = {}) {
  if (!activeMarker) return false;
  const windowSpot = new THREE.Vector3(ONE_BEDROOM_HOUSE_RIGHT_X - 2.05, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_HOUSE_FRONT_Z - 1.15);
  return startActiveAvatarHoldSkill({
    id: "autonomous_home_window_look",
    label: "look out the one-bedroom living window",
    action: "look_window",
    seconds: options.seconds || 10 + Math.random() * 24,
    position: windowSpot,
    yaw: 0,
    postureState: {
      id: "autonomous_home_window_look",
      posture: "stand_look",
      rootTiltX: 0.02,
      rootYOffset: -0.02,
    },
  });
}

function startActiveAvatarKitchenDrinkHold(options = {}) {
  if (!activeMarker) return false;
  const kitchenSpot = new THREE.Vector3(ONE_BEDROOM_ROOM_SPLIT_X + 3.4, ACTIVE_AVATAR_GROUND_Y, ONE_BEDROOM_HOUSE_BACK_Z + 2.4);
  const holdSpec = {
    id: "autonomous_kitchen_drink",
    label: "kitchen counter drink",
    action: "drink",
    truthAction: "drink",
    seconds: options.seconds || 8 + Math.random() * 18,
    position: kitchenSpot,
    yaw: Math.PI,
    postureState: {
      id: "autonomous_kitchen_drink",
      posture: "stand_drink",
      rootTiltX: 0.02,
      rootYOffset: 0,
    },
    heldPropKind: "coffee_cup",
    selfChosen: !!options.selfChosen,
  };
  return routeActiveAvatarToHomeHold(holdSpec, {
    routeId: "walk_inside_to_kitchen_drink",
    label: "walk through the front doorway to get a drink in the kitchen",
    approach: kitchenSpot.clone().add(new THREE.Vector3(0, 0, 0.5)),
  });
}

function startActiveAvatarKitchenCoffeeHold(options = {}) {
  if (!activeMarker) return false;
  const kitchenSpot = ONE_BEDROOM_COFFEE_STATION_USE_SPOT.clone();
  const holdSpec = {
    id: "autonomous_kitchen_coffee",
    label: "use the stocked kitchen coffee station",
    action: "drink_coffee",
    truthAction: "drink_coffee",
    seconds: options.seconds || 8 + Math.random() * 18,
    position: kitchenSpot,
    yaw: Math.PI,
    postureState: {
      id: "autonomous_kitchen_coffee",
      posture: "stand_drink",
      rootTiltX: 0.02,
      rootYOffset: 0,
    },
    heldPropKind: "coffee_cup",
    selfChosen: !!options.selfChosen,
  };
  return routeActiveAvatarToHomeHold(holdSpec, {
    routeId: "walk_inside_to_kitchen_coffee_station",
    label: "walk through the front doorway to the stocked kitchen coffee station",
    approach: kitchenSpot.clone().add(new THREE.Vector3(0, 0, 0.45)),
  });
}

function persistentQuietActivitySnapshot() {
  if (!activeSkillInteraction?.persistentQuietActivity) return null;
  const skill = activeSkillInteraction;
  return {
    id: skill.id,
    label: skill.label,
    action: skill.action,
    selfChosen: !!skill.selfChosen,
    active: true,
    ageSeconds: Number(Math.max(0, clock.elapsedTime - skill.startedAt).toFixed(3)),
    nextContinuationReviewInSeconds: Number(Math.max(0, (skill.nextContinuationReviewAt || clock.elapsedTime) - clock.elapsedTime).toFixed(3)),
    continuationCount: skill.continuationCount || 0,
    chatActive: !!skill.chatActive,
    chatInterruptions: skill.chatInterruptions || 0,
    voluntaryExitAvailable: !!skill.voluntaryExitAvailable,
    heldPropKind: skill.heldPropKind || "",
    supportSurface: skill.postureState?.surface || null,
    positionLockedByTeleport: false,
    policy: ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY,
  };
}

function continuePersistentQuietActivity(extensionSeconds = ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY.continuationReviewSeconds, reason = "voluntary_continue") {
  if (!activeSkillInteraction?.persistentQuietActivity || !activeMarker) return false;
  const skill = activeSkillInteraction;
  const extension = Math.max(60, Number(extensionSeconds) || ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY.continuationReviewSeconds);
  skill.nextContinuationReviewAt = Math.max(clock.elapsedTime, skill.nextContinuationReviewAt || clock.elapsedTime) + extension;
  skill.seconds = skill.nextContinuationReviewAt - skill.startedAt;
  skill.continuationCount = (skill.continuationCount || 0) + 1;
  skill.lastContinuationReason = reason;
  recordMovementLearningAttempt({
    skill: skill.id,
    phase: "quiet_activity_voluntarily_continued",
    target: skill.label,
    extensionSeconds: extension,
    continuationCount: skill.continuationCount,
    teleported: false,
  });
  return persistentQuietActivitySnapshot();
}

function exitPersistentQuietActivity(reason = "voluntary_exit") {
  if (!activeSkillInteraction?.persistentQuietActivity || !activeMarker) return false;
  return finishActiveAvatarSkillInteraction(clock.elapsedTime, "quiet_activity_voluntary_exit", {
    reason,
    teleported: false,
  });
}

function handlePersistentQuietActivityShellAction(actionName) {
  if (!activeSkillInteraction?.persistentQuietActivity || !activeMarker) return false;
  const skill = activeSkillInteraction;
  const normalized = String(actionName || "").toLowerCase().trim();
  if (!normalized) return true;
  const isChat = /^(talk|talking|speak|speaking|chat|conversation|listen|listening|wave|voice_message)$/.test(normalized);
  const isContinue = /^(read|read_book|read_tablet|ebook|e-book|browse_books|read_all_day|read_for_hours|keep_reading|settle_in_and_read|persistent_read)$/.test(normalized);
  if (isChat) {
    if (!skill.chatActive) {
      skill.chatInterruptions = (skill.chatInterruptions || 0) + 1;
      recordMovementLearningAttempt({
        skill: skill.id,
        phase: "quiet_activity_chat_interruption_preserved",
        target: skill.label,
        heldPropKind: skill.heldPropKind,
        supportSurface: skill.postureState?.surface || null,
        teleported: false,
      });
    }
    skill.chatActive = true;
    skill.lastChatAt = clock.elapsedTime;
    setActiveAvatarAction("talking");
    return true;
  }
  if (isContinue) {
    skill.chatActive = false;
    continuePersistentQuietActivity(ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY.continuationReviewSeconds, "shell_continue_intent");
    setActiveAvatarAction(skill.action);
    return true;
  }
  if (normalized === "idle") {
    skill.chatActive = false;
    setActiveAvatarAction(skill.action);
    return true;
  }
  exitPersistentQuietActivity(`new_embodied_intent:${normalized}`);
  return false;
}

function finishActiveAvatarSkillInteraction(t, phase = "finished", details = {}) {
  if (!activeSkillInteraction || !activeMarker) return false;
  const skill = activeSkillInteraction;
  const truth = skill.truthAction ? activityTruthForAction(skill.truthAction) : null;
  recordMovementLearningAttempt({
    skill: skill.id,
    phase,
    target: skill.label,
    action: skill.action,
    truthGrounded: truth ? !!truth.grounded : undefined,
    ...details,
  });
  activeSkillInteraction = null;
  if (skill.heldPropKind === "basketball") {
    basketballPracticeState = null;
    if (basketballBallRoot) {
      basketballBallRoot.position.set(BASKETBALL_BALL_REST_SPOT.x, basketballBallBaseY, BASKETBALL_BALL_REST_SPOT.z);
      basketballBallRoot.visible = true;
    }
  }
  clearActiveHeldProp();
  activeMarker.userData.skillInteraction = null;
  activeMarker.userData.gaitMode = null;
  activeMarker.userData.postureState = null;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  activeMarker.userData.waitUntil = t + 0.65;
  setActiveAvatarAction("idle");
  applyActiveAvatarSupport(0.016);
  return true;
}

function startActiveAvatarDuckPractice() {
  return startActiveAvatarHoldSkill({
    id: "duck",
    label: "duck under an imaginary low obstacle",
    action: "duck",
    seconds: 2.2,
    postureState: {
      id: "duck",
      posture: "duck",
      rootTiltX: 0.12,
      rootYOffset: -0.46,
    },
  });
}

function startActiveAvatarDodgePractice() {
  if (!activeMarker) return false;
  clearActiveAvatarPracticeInteractions();
  const basePosition = activeMarker.position.clone();
  activeSkillInteraction = {
    kind: "dodge",
    id: "dodge",
    label: "quick side dodge",
    action: "dodge",
    startedAt: clock.elapsedTime,
    seconds: 1.05,
    basePosition,
    yaw: activeMarker.rotation.y,
  };
  activeMarker.userData.skillInteraction = "dodge";
  activeMarker.userData.gaitMode = "run";
  setActiveAvatarAction("dodge");
  recordMovementLearningAttempt({
    skill: "dodge",
    phase: "practice_started",
    target: "quick side dodge",
  });
  return true;
}

function startActiveAvatarJumpPractice() {
  if (!activeMarker) return false;
  clearActiveAvatarPracticeInteractions();
  const basePosition = activeMarker.position.clone();
  activeSkillInteraction = {
    kind: "jump",
    id: "jump",
    label: "controlled two-foot jump",
    action: "jump",
    startedAt: clock.elapsedTime,
    seconds: 1.12,
    basePosition,
    height: 0.52,
  };
  activeMarker.userData.skillInteraction = "jump";
  activeMarker.userData.gaitMode = null;
  setActiveAvatarAction("jump");
  recordMovementLearningAttempt({ skill: "jump", phase: "takeoff_started", target: "controlled vertical jump" });
  return true;
}

function startActiveAvatarSwimPractice() {
  if (!activeMarker) return false;
  clearActiveAvatarPracticeInteractions();
  const route = activeAvatarSwimPracticeWaypoints.map((point) => point.clone());
  activeMarker.position.copy(route[0]);
  activeSkillInteraction = {
    kind: "swim",
    id: "swim_pool",
    label: "backyard pool swim lap",
    action: "swim_idle",
    startedAt: clock.elapsedTime,
    waypoints: route,
    index: 1,
  };
  activeMarker.userData.skillInteraction = "swim_pool";
  activeMarker.userData.gaitMode = "swim";
  activeMarker.userData.postureState = {
    id: "swim_pool",
    posture: "swim",
    rootTiltX: Math.PI / 2,
    rootYOffset: 0.2,
  };
  activeMarker.userData.supportState = {
    id: "backyard_pool_water",
    supported: true,
    falling: false,
    y: 0.12,
    floor: 0,
    isWater: true,
  };
  setActiveAvatarAction("swim_idle");
  recordMovementLearningAttempt({ skill: "swim_pool", phase: "entered_pool", target: "backyard pool" });
  return true;
}

function startActiveAvatarLibraryReadPractice(seconds = 4.8) {
  if (!activeMarker) return false;
  setLibraryDoorOpen(true);
  const readSpot = activeAvatarLibraryReadWaypoints[activeAvatarLibraryReadWaypoints.length - 1].clone();
  return startActiveAvatarHoldSkill({
    id: "read_library",
    label: "public library reading table",
    action: "read_book",
    truthAction: "read_book",
    seconds,
    position: readSpot,
    yaw: -Math.PI / 2,
    postureState: {
      id: "read_library",
      posture: "read",
      rootTiltX: 0.04,
      rootYOffset: -0.08,
    },
    heldPropKind: "book",
  });
}

function startActiveAvatarCafeCoffeePractice() {
  if (!activeMarker) return false;
  setStarbucksDoorOpen(true);
  return startActiveAvatarPracticeRouteSkill("get_coffee", activeAvatarCafeCoffeeWaypoints, {
    label: "walk to Starbucks and get coffee",
    finishZone: "starbucks_cafe",
    gaitMode: "walk",
    speed: 1.65,
    action: "walk",
    finishHold: {
      id: "drink_coffee",
      label: "Starbucks cafe counter coffee",
      action: "drink_coffee",
      truthAction: "drink_coffee",
      seconds: 4.6,
      position: STARBUCKS_COUNTER_SPOT.clone(),
      yaw: Math.PI,
      postureState: {
        id: "drink_coffee",
        posture: "stand_drink",
        rootTiltX: 0.02,
        rootYOffset: 0,
      },
      heldPropKind: "coffee_cup",
    },
  });
}

function startActiveAvatarBasketballPractice() {
  if (!activeMarker) return false;
  if (HOME_WORLD_PRE_RAM_LIGHT_MODE) {
    show("Basketball court is disabled in pre-RAM light mode.");
    return false;
  }
  basketballBounceUntil = clock.elapsedTime + 8.0;
  return startActiveAvatarPracticeRouteSkill("play_basketball", activeAvatarBasketballPracticeWaypoints, {
    label: "jog to the future park basketball court",
    finishZone: "future_park_basketball_court",
    gaitMode: "jog",
    speed: 2.7,
    action: "jog",
    finishHold: {
      id: "play_basketball",
      label: "future park basketball dribble spot",
      action: "dribble_basketball",
      truthAction: "play_basketball",
      seconds: 6.4,
      position: BASKETBALL_DRIBBLE_SPOT.clone(),
      yaw: Math.PI / 2,
      postureState: {
        id: "play_basketball",
        posture: "athletic_ready",
        rootTiltX: 0.08,
        rootYOffset: -0.06,
      },
      heldPropKind: "basketball",
    },
  });
}

function startActiveAvatarBasketballBenchSitStand() {
  if (!activeMarker) return false;
  if (HOME_WORLD_PRE_RAM_LIGHT_MODE) {
    show("Basketball bench is disabled in pre-RAM light mode.");
    return false;
  }
  return startActiveAvatarHoldSkill({
    id: "basketball_bench_sit_stand",
    label: "future park bench sit and stand",
    action: "sit",
    truthAction: "sit",
    seconds: 4.8,
    position: BASKETBALL_BENCH_SIT_SPOT.clone(),
    yaw: 0,
    postureState: {
      id: "basketball_bench_sit_stand",
      posture: "sit",
      rootTiltX: 0.04,
      rootYOffset: -0.34,
    },
  });
}

function startActiveAvatarSchoolStudyPractice() {
  if (!activeMarker) return false;
  if (HOME_WORLD_PRE_RAM_LIGHT_MODE) {
    return startActiveAvatarPracticeRouteSkill("attend_school", [
      KIRA_BUNGALOW_SPAWN.clone(),
      KIRA_BUNGALOW_FRONT_OUTSIDE.clone(),
      new THREE.Vector3(42.0, ACTIVE_AVATAR_GROUND_Y, 24.4),
      new THREE.Vector3(60.5, ACTIVE_AVATAR_GROUND_Y, 24.0),
      SCHOOL_ENTRY.clone(),
      SCHOOL_CENTER.clone(),
    ], {
      label: "walk to the empty Home World school learning room",
      finishZone: "home_world_school_classroom",
      gaitMode: "walk",
      speed: 1.7,
      action: "walk",
      finishHold: {
        id: "attend_school_empty_room",
        label: "empty school learning room",
        action: "study",
        truthAction: "attend_school",
        seconds: 7.5,
        position: SCHOOL_CENTER.clone(),
        yaw: Math.PI,
      },
    });
  }
  return startActiveAvatarPracticeRouteSkill("attend_school", activeAvatarSchoolStudyWaypoints, {
    label: "walk to the Home World school classroom",
    finishZone: "home_world_school_classroom",
    gaitMode: "walk",
    speed: 1.7,
    action: "walk",
    finishHold: {
      id: "attend_school",
      label: "Kira school lesson desk",
      action: "study",
      truthAction: "attend_school",
      seconds: 5.6,
      position: SCHOOL_SEAT_SPOT.clone(),
      yaw: SCHOOL_SEAT_YAW,
      postureState: {
        id: "attend_school",
        posture: "sit",
        rootTiltX: 0.06,
        rootYOffset: -0.42,
      },
      heldPropKind: "notebook",
    },
  });
}

function startActiveAvatarKiraSleepPractice() {
  if (!activeMarker || !activeAvatarIsKiraLike()) return false;
  const dreamTopics = [
    "walking through a quiet library and finding a notebook of new ideas",
    "practicing basketball shots under bright park lights",
    "getting briefly lost near an unreliable doorway, then finding the right path",
    "sitting at a cafe table and writing plans for Kira World",
  ];
  activeKiraDreamState = {
    startedAt: new Date().toISOString(),
    kind: Math.random() < 0.18 ? "nightmare_seed" : "dream_seed",
    topic: dreamTopics[Math.floor(Math.random() * dreamTopics.length)],
    storedAs: "runtime_body_dream_seed_for_future_journal",
  };
  return startActiveAvatarHoldSkill({
    id: "kira_sleep_bed",
    label: "Kira one-bedroom bed sleep",
    action: "lie_down",
    truthAction: "sleep_bed",
    seconds: 7.2,
    position: KIRA_BED_SLEEP_SPOT.clone(),
    yaw: Math.PI / 2,
    postureState: {
      id: "kira_sleep_bed",
      posture: "sleep",
      rootTiltX: Math.PI / 2,
      rootYOffset: 0.74,
      dreamState: activeKiraDreamState,
    },
  });
}

function captureFlagActiveRouteToFlag(flagSpot) {
  return [
    captureFlagWorld.activeBase.clone(),
    new THREE.Vector3(114, ACTIVE_AVATAR_GROUND_Y, 108),
    new THREE.Vector3(122, ACTIVE_AVATAR_GROUND_Y, 128),
    new THREE.Vector3(133, ACTIVE_AVATAR_GROUND_Y, 134),
    new THREE.Vector3(flagSpot.x - 4.5, ACTIVE_AVATAR_GROUND_Y, Math.max(137, flagSpot.z - 8)),
    flagSpot.clone(),
  ];
}

function captureFlagActiveRouteToBase(fromSpot) {
  return [
    fromSpot.clone(),
    new THREE.Vector3(Math.max(118, fromSpot.x - 12), ACTIVE_AVATAR_GROUND_Y, 139),
    new THREE.Vector3(124, ACTIVE_AVATAR_GROUND_Y, 129),
    new THREE.Vector3(115, ACTIVE_AVATAR_GROUND_Y, 112),
    captureFlagWorld.activeBase.clone(),
  ];
}

function startActiveAvatarCaptureFlagGamePractice() {
  if (!activeMarker) return false;
  if (!CAPTURE_FLAG_WORLD_ENABLED) {
    show("Capture The Flag practice is offloaded until it exists as a separate notebook world.");
    return false;
  }
  clearActiveAvatarPracticeInteractions();
  const flagSpot = startCaptureFlagGame("active_avatar") || captureFlagWorld.flagSpots[0].clone();
  const route = captureFlagActiveRouteToFlag(flagSpot);
  activeMarker.position.copy(captureFlagWorld.activeBase);
  activeMarker.userData.roamZone = "capture_flag";
  activeMarker.userData.roamReady = true;
  activeMarker.userData.roamIndex = 0;
  activeMarker.userData.waitUntil = 0;
  activeMarker.userData.stuckSince = null;
  activeMarker.userData.lastDistanceToTarget = null;
  activeMarker.userData.lastMoveT = clock.elapsedTime - 0.05;
  activeSkillInteraction = {
    kind: "capture_flag_game",
    id: "capture_flag_game",
    label: "Capture The Flag notebook world",
    action: "run",
    startedAt: clock.elapsedTime,
    phase: "to_flag",
    route,
    index: 1,
    didDodge: false,
    dodgeUntil: 0,
    dodgePoint: new THREE.Vector3(122, ACTIVE_AVATAR_GROUND_Y, 128),
    flagSpot: flagSpot.clone(),
  };
  activeMarker.userData.skillInteraction = "capture_flag_game";
  activeMarker.userData.gaitMode = "run";
  activeMarker.userData.isMoving = true;
  activeMarker.userData.walkSpeed = ACTIVE_AVATAR_RUN_SPEED_GROUND;
  activeMarker.userData.lastStepMeters = 0.01;
  setActiveAvatarAction("run");
  recordMovementLearningAttempt({
    skill: "capture_flag_game",
    phase: "practice_started",
    target: "glowing flag and base camp",
    actor: activeAvatarDisplayName(),
  });
  return true;
}

function updateActiveAvatarCaptureFlagGameSkill(skill, t, dt) {
  if (!activeMarker || !skill || skill.kind !== "capture_flag_game") return false;
  if (captureFlagState.phase === "tagged") {
    finishActiveAvatarSkillInteraction(t, "tagged_by_npc", { dodges: captureFlagState.dodges || 0 });
    return true;
  }
  const route = skill.route || [];
  const target = route[skill.index];
  if (!target) {
    finishActiveAvatarSkillInteraction(t, "route_missing");
    return true;
  }

  const previous = activeMarker.position.clone();
  const dx = target.x - activeMarker.position.x;
  const dz = target.z - activeMarker.position.z;
  const distance = Math.hypot(dx, dz);
  if (distance < 0.52) {
    if (skill.phase === "to_flag" && skill.index >= route.length - 1) {
      collectCaptureFlagObjective("active_avatar");
      skill.phase = "return_base";
      skill.route = captureFlagActiveRouteToBase(activeMarker.position.clone());
      skill.index = 1;
      skill.action = "run";
      return true;
    }
    if (skill.phase === "return_base" && skill.index >= route.length - 1) {
      completeCaptureFlagGame("active_avatar");
      finishActiveAvatarSkillInteraction(t, "capture_complete", { dodges: captureFlagState.dodges || 0 });
      return true;
    }
    skill.index += 1;
    return true;
  }

  const closestNpc = captureFlagNpcs
    .map((npc) => ({ npc, distance: captureFlagDistanceTo(npc.group.position, activeMarker.position) }))
    .sort((a, b) => a.distance - b.distance)[0];
  const nearPlannedDodge = !skill.didDodge && captureFlagDistanceTo(skill.dodgePoint, activeMarker.position) < 2.25;
  const nearNpcDodge = closestNpc && closestNpc.distance < 4.0 && t > (skill.dodgeUntil || 0);
  if ((nearPlannedDodge || nearNpcDodge) && !skill.didDodge) {
    skill.didDodge = true;
    skill.dodgeUntil = t + 0.9;
    captureFlagState.dodges = (captureFlagState.dodges || 0) + 1;
    recordMovementLearningAttempt({
      skill: "capture_flag_game",
      phase: "dodge",
      target: closestNpc?.npc?.name || "planned street danger point",
      actor: activeAvatarDisplayName(),
    });
  }

  const dodging = t < (skill.dodgeUntil || 0);
  const turnOrNearTarget = distance < 4.0 || skill.index === 1;
  const action = dodging ? "dodge" : turnOrNearTarget ? "jog" : "run";
  const speed = dodging ? 5.6 : action === "jog" ? 2.85 : 5.2;
  const step = Math.min(distance, speed * dt);
  if (distance > 0.001) {
    const forwardX = dx / distance;
    const forwardZ = dz / distance;
    let sideX = 0;
    let sideZ = 0;
    if (dodging) {
      sideX = -forwardZ * 0.64;
      sideZ = forwardX * 0.64;
    }
    activeMarker.position.x += forwardX * step + sideX * dt;
    activeMarker.position.z += forwardZ * step + sideZ * dt;
    activeMarker.rotation.y = Math.atan2(forwardX, forwardZ) + Math.PI;
  }
  activeMarker.position.y = ACTIVE_AVATAR_GROUND_Y;
  activeMarker.userData.postureState = dodging
    ? { id: "capture_flag_dodge", posture: "dodge", rootTiltX: 0.04, rootYOffset: -0.04 }
    : null;
  activeMarker.userData.isMoving = true;
  activeMarker.userData.walkSpeed = speed;
  activeMarker.userData.lastStepMeters = Math.hypot(activeMarker.position.x - previous.x, activeMarker.position.z - previous.z);
  activeMarker.userData.gaitMode = action === "jog" ? "jog" : "run";
  activeMarker.userData.skillInteraction = "capture_flag_game";
  activeMarker.userData.supportState = {
    id: "capture_flag_battlefield",
    supported: true,
    falling: false,
    y: ACTIVE_AVATAR_GROUND_Y,
    floor: 0,
  };
  if (activeMarker.userData.lastStepMeters > 0.0001) {
    activeAvatarMovePhase = (activeAvatarMovePhase + (activeMarker.userData.lastStepMeters / ACTIVE_AVATAR_WALK_STRIDE_METERS) * Math.PI * 2.45) % (Math.PI * 2);
    activeMarker.userData.walkCyclePhase = activeAvatarMovePhase;
  }
  skill.action = action;
  if (activeAvatarAction !== action) setActiveAvatarAction(action);
  if (skill.phase === "to_flag" && captureFlagFlagGroup?.visible && captureFlagDistanceTo(captureFlagFlagGroup.position, activeMarker.position) < 1.35) {
    collectCaptureFlagObjective("active_avatar");
    skill.phase = "return_base";
    skill.route = captureFlagActiveRouteToBase(activeMarker.position.clone());
    skill.index = 1;
  } else if (skill.phase === "return_base" && captureFlagDistanceTo(captureFlagWorld.activeBase, activeMarker.position) < 2.3) {
    completeCaptureFlagGame("active_avatar");
    finishActiveAvatarSkillInteraction(t, "capture_complete", { dodges: captureFlagState.dodges || 0 });
  }
  return true;
}

function startActiveAvatarWalkPractice(options = {}) {
  return startActiveAvatarPracticeRouteSkill("walk", activeAvatarJogPracticeWaypoints, {
    label: "front sidewalk walk route",
    gaitMode: "walk",
    speed: ACTIVE_AVATAR_WALK_SPEED_GROUND,
    selfChosen: !!options.selfChosen,
  });
}

function startActiveAvatarJogPractice(options = {}) {
  return startActiveAvatarPracticeRouteSkill("jog", activeAvatarJogPracticeWaypoints, {
    label: "front sidewalk jog route",
    gaitMode: "jog",
    speed: ACTIVE_AVATAR_JOG_SPEED_GROUND,
    selfChosen: !!options.selfChosen,
  });
}

function startActiveAvatarRunPractice(options = {}) {
  return startActiveAvatarPracticeRouteSkill("run", activeAvatarRunPracticeWaypoints, {
    label: "front sidewalk run route",
    gaitMode: "run",
    speed: ACTIVE_AVATAR_RUN_SPEED_GROUND,
    selfChosen: !!options.selfChosen,
  });
}

function updateActiveAvatarSkillInteraction(t, dt = 0.016) {
  if (!activeSkillInteraction || !activeMarker) return false;
  const skill = activeSkillInteraction;
  const age = t - skill.startedAt;
  if (skill.kind === "capture_flag_game") {
    return updateActiveAvatarCaptureFlagGameSkill(skill, t, dt);
  }
  if (skill.kind === "hold") {
    if (Number.isFinite(skill.yaw) && skill.phase === "aligning_yaw") {
      const remainingTurn = turnActiveAvatarTowardYaw(skill.yaw, dt);
      activeMarker.userData.postureState = null;
      activeMarker.userData.isMoving = false;
      activeMarker.userData.walkSpeed = 0;
      activeMarker.userData.lastStepMeters = 0;
      if (activeAvatarAction !== "idle") setActiveAvatarAction("idle");
      applyActiveAvatarSupport(dt);
      if (remainingTurn > 0.025) return true;
      skill.phase = "holding";
      skill.holdStartedAt = t;
      if (skill.heldPropKind) setActiveHeldProp(skill.heldPropKind);
      if (skill.heldPropKind === "basketball" && !basketballPracticeState) {
        basketballPracticeState = {
          startedAt: t,
          seconds: skill.seconds,
          phase: "pick_up_dribble_shoot",
          shotTarget: BASKETBALL_SHOT_TARGET.clone(),
        };
        if (basketballBallRoot) basketballBallRoot.visible = false;
      }
      recordMovementLearningAttempt({
        skill: skill.id,
        phase: "bounded_yaw_alignment_finished",
        target: skill.label,
        instantFlip: false,
      });
    }
    activeMarker.userData.postureState = skill.postureState;
    if (skill.heldPropKind) setActiveHeldProp(skill.heldPropKind);
    updateActiveHeldProp(t);
    activeMarker.userData.isMoving = false;
    activeMarker.userData.walkSpeed = 0;
    activeMarker.userData.lastStepMeters = 0;
    const desiredAction = skill.persistentQuietActivity && skill.chatActive ? "talking" : skill.action;
    if (activeAvatarAction !== desiredAction) setActiveAvatarAction(desiredAction);
    applyActiveAvatarSupport(dt);
    if (skill.postureState?.surface) {
      activeMarker.userData.supportState = {
        id: skill.postureState.surface,
        supported: true,
        falling: false,
        y: Number(activeMarker.position.y.toFixed(3)),
        floor: activeMarker.position.y > 1.8 ? 1 : 0,
      };
    }
    if (skill.persistentQuietActivity && t >= (skill.nextContinuationReviewAt || t)) {
      continuePersistentQuietActivity(
        ACTIVE_AVATAR_QUIET_ACTIVITY_POLICY.continuationReviewSeconds,
        "no_exit_intent_at_review",
      );
    } else if (!skill.persistentQuietActivity && t - Number(skill.holdStartedAt ?? skill.startedAt) >= skill.seconds) {
      finishActiveAvatarSkillInteraction(t, "finished_hold");
    }
    return true;
  }
  if (skill.kind === "jump") {
    const k = THREE.MathUtils.clamp(age / skill.seconds, 0, 1);
    const lift = Math.sin(k * Math.PI) * skill.height;
    activeMarker.position.copy(skill.basePosition);
    activeMarker.position.y = skill.basePosition.y + lift;
    activeMarker.userData.postureState = {
      id: "jump",
      posture: "jump",
      rootTiltX: -0.06 + Math.sin(k * Math.PI) * 0.1,
      rootYOffset: 0,
    };
    activeMarker.userData.isMoving = true;
    activeMarker.userData.walkSpeed = 0;
    activeMarker.userData.lastStepMeters = 0;
    activeMarker.userData.supportState = {
      id: "jump_arc",
      supported: k === 0 || k >= 1,
      falling: k > 0.5 && k < 1,
      y: Number(activeMarker.position.y.toFixed(3)),
      floor: activeMarker.position.y > 1.8 ? 1 : 0,
    };
    if (age >= skill.seconds) {
      activeMarker.position.copy(skill.basePosition);
      finishActiveAvatarSkillInteraction(t, "landed", { jumpHeightMeters: skill.height });
    }
    return true;
  }
  if (skill.kind === "dodge") {
    const k = THREE.MathUtils.clamp(age / skill.seconds, 0, 1);
    const offset = Math.sin(k * Math.PI) * 1.05;
    const right = new THREE.Vector3(Math.cos(skill.yaw || 0), 0, -Math.sin(skill.yaw || 0));
    activeMarker.position.copy(skill.basePosition).add(right.multiplyScalar(offset));
    activeMarker.position.y = skill.basePosition.y;
    activeMarker.rotation.y = skill.yaw || activeMarker.rotation.y;
    activeMarker.userData.postureState = {
      id: "dodge",
      posture: "dodge",
      rootTiltX: 0.04,
      rootYOffset: -0.04,
    };
    activeMarker.userData.isMoving = true;
    activeMarker.userData.walkSpeed = ACTIVE_AVATAR_RUN_SPEED_GROUND;
    activeMarker.userData.lastStepMeters = Math.abs(Math.cos(k * Math.PI)) * 0.08;
    activeMarker.userData.gaitMode = "run";
    activeMarker.userData.supportState = {
      id: activeMarker.position.y > 1.8 ? "second_floor" : "outside_ground",
      supported: true,
      falling: false,
      y: Number(activeMarker.position.y.toFixed(3)),
      floor: activeMarker.position.y > 1.8 ? 1 : 0,
    };
    if (activeAvatarAction !== "dodge") setActiveAvatarAction("dodge");
    if (age >= skill.seconds) finishActiveAvatarSkillInteraction(t, "dodged", { dodgeMeters: 1.05 });
    return true;
  }
  if (skill.kind === "swim") {
    const route = skill.waypoints || [];
    const target = route[skill.index];
    if (!target) {
      activeMarker.position.set(-4.45, ACTIVE_AVATAR_GROUND_Y, -15.85);
      finishActiveAvatarSkillInteraction(t, "swim_lap_finished", { pool: "backyard" });
      return true;
    }
    const previous = activeMarker.position.clone();
    const dx = target.x - activeMarker.position.x;
    const dz = target.z - activeMarker.position.z;
    const distance = Math.hypot(dx, dz);
    const step = Math.min(distance, ACTIVE_AVATAR_SWIM_SPEED * dt);
    if (distance > 0.001) {
      activeMarker.position.x += (dx / distance) * step;
      activeMarker.position.z += (dz / distance) * step;
      turnActiveAvatarTowardYaw(Math.atan2(dx, dz) + Math.PI, dt);
    }
    activeMarker.position.y = 0.12 + Math.sin(t * 4.1) * 0.018;
    activeMarker.userData.postureState = {
      id: "swim_pool",
      posture: "swim",
      rootTiltX: Math.PI / 2,
      rootYOffset: 0.2,
    };
    activeMarker.userData.supportState = {
      id: "backyard_pool_water",
      supported: true,
      falling: false,
      y: 0.12,
      floor: 0,
      isWater: true,
    };
    activeMarker.userData.isMoving = distance > 0.04;
    activeMarker.userData.walkSpeed = ACTIVE_AVATAR_SWIM_SPEED;
    const movedMeters = Math.hypot(activeMarker.position.x - previous.x, activeMarker.position.z - previous.z);
    activeMarker.userData.lastStepMeters = movedMeters;
    if (movedMeters > 0.0001) {
      activeAvatarMovePhase = (activeAvatarMovePhase + (movedMeters / ACTIVE_AVATAR_WALK_STRIDE_METERS) * Math.PI * 2.4) % (Math.PI * 2);
      activeMarker.userData.walkCyclePhase = activeAvatarMovePhase;
    }
    if (distance < 0.22) {
      recordMovementLearningAttempt({
        skill: "swim_pool",
        phase: "lap_turn",
        target: "backyard pool",
        waypointIndex: skill.index,
      });
      skill.index += 1;
    }
    if (activeAvatarAction !== "swim_idle") setActiveAvatarAction("swim_idle");
    return true;
  }
  return false;
}

function tryStartActiveAvatarRoamPractice(index) {
  if (!activeMarker) return false;
  if (activeMarker.userData.practiceRoute) return false;
  const route = activeAvatarCurrentWaypoints();
  const routeLength = Math.max(1, route.length);
  const normalizedIndex = ((index % routeLength) + routeLength) % routeLength;
  const skill = activeAvatarCurrentPracticeStops().get(normalizedIndex);
  const practiceKey = `${activeMarker.userData.roamZone || "downstairs"}:${normalizedIndex}:${skill || ""}`;
  if (!skill || activeMarker.userData.lastRoamPracticeKey === practiceKey) return false;
  activeMarker.userData.lastRoamPracticeKey = practiceKey;
  activeMarker.userData.roamIndex = normalizedIndex + 1;
  if (skill === "stairs_step") return startActiveAvatarStairPracticeRoute(true);
  if (skill === "desk_computer") return startActiveAvatarDeskComputerSequence();
  return startActiveAvatarPostureTest(skill);
}

function activeAvatarCurrentWaypoints() {
  return activeAvatarDefaultWaypoints();
}

function activeAvatarNearestWaypointIndex(route, position) {
  if (!route?.length || !position) return 0;
  let bestIndex = 0;
  let bestDistance = Number.POSITIVE_INFINITY;
  for (let i = 0; i < route.length; i += 1) {
    const point = route[i];
    const dy = Math.abs((point.y || 0) - (position.y || 0));
    const distance = Math.hypot(point.x - position.x, point.z - position.z) + dy * 2.0;
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = i;
    }
  }
  return bestIndex;
}

function finishActiveAvatarPracticeRoute(t) {
  if (!activeMarker?.userData?.practiceRoute) return false;
  const route = activeMarker.userData.practiceRoute;
  const id = route.id;
  const finishHold = route.finishHold;
  activeMarker.userData.practiceRoute = null;
  activeMarker.userData.stairTraversalActive = false;
  clearActiveAvatarAutonomousRoamTarget("practice_route_finished");
  if (route.finishZone) activeMarker.userData.roamZone = route.finishZone;
  activeMarker.userData.roamIndex = 0;
  activeMarker.userData.waitUntil = t + 2.5;
  activeMarker.userData.isMoving = false;
  activeMarker.userData.walkSpeed = 0;
  activeMarker.userData.lastStepMeters = 0;
  activeMarker.userData.lastDistanceToTarget = null;
  activeMarker.userData.gaitMode = null;
  recordMovementLearningAttempt({
    skill: id || "practice_route",
    phase: "route_finished",
    target: "practice route",
  });
  const transition = activeMarker.userData.transitionEvidence;
  if (transition) {
    transition.completed = true;
    transition.completedAt = new Date().toISOString();
    transition.end = {
      x: Number(activeMarker.position.x.toFixed(3)),
      y: Number(activeMarker.position.y.toFixed(3)),
      z: Number(activeMarker.position.z.toFixed(3)),
    };
    transition.pathSampleCount = Array.isArray(transition.path) ? transition.path.length : transition.pathSampleCount || 0;
  }
  if (finishHold) {
    activeMarker.userData.waitUntil = 0;
    startActiveAvatarHoldSkill(finishHold, t);
  }
  return true;
}

function updateActiveAvatarMovement(t) {
  if (!activeMarker || (activeMarker.userData.kind === "orb" && !activeAvatarRoot)) return;
  const isMarinetteLike = activeAvatarIsMarinetteLike();
  if (activeAvatarIsKiraLike() && activeMarker.position.y > 1.8) {
    // Resume validation already rejects an upstairs Kira position. If an
    // impossible height appears after activation, fail closed in place instead
    // of hiding the fault with a runtime teleport to the bungalow spawn.
    activeMarker.userData.roamReady = true;
    activeMarker.userData.practiceRoute = null;
    activeMarker.userData.stairTraversalActive = false;
    activeMarker.userData.autonomousRoamTarget = null;
    activeMarker.userData.navigationRecovery = null;
    activeMarker.userData.isMoving = false;
    activeMarker.userData.walkSpeed = 0;
    activeMarker.userData.lastStepMeters = 0;
    activeMarker.userData.waitUntil = t + 1.0;
    activeMarker.userData.lastMoveT = t;
    activeMarker.userData.lastEmbodimentCapabilityBlock = {
      id: "kira_invalid_runtime_height",
      reason: "invalid_height_safe_stop_no_runtime_teleport",
      position: {
        x: Number(activeMarker.position.x.toFixed(3)),
        y: Number(activeMarker.position.y.toFixed(3)),
        z: Number(activeMarker.position.z.toFixed(3)),
      },
      requires: "deactivate_then_reactivate_from_validated_resume_or_owner_review",
      recordedAt: new Date().toISOString(),
    };
    if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
    if (!activeMarker.userData.invalidHeightRecorded) {
      activeMarker.userData.invalidHeightRecorded = true;
      recordMovementLearningAttempt({
        skill: "route_safety",
        phase: "invalid_height_safe_stop_no_runtime_teleport",
        target: "validated Kira resume state",
        teleported: false,
      });
    }
    return;
  }
  if (activeAvatarIsKiraLike() && activeMarker.userData.roamZone === "upstairs") {
    // A stale zone label can be repaired without moving the body.
    activeMarker.userData.roamZone = "kira_home_world";
    activeMarker.userData.roamReady = true;
    activeMarker.userData.practiceRoute = null;
    activeMarker.userData.stairTraversalActive = false;
    activeMarker.userData.autonomousRoamTarget = null;
    activeMarker.userData.navigationRecovery = null;
    activeMarker.userData.roamIndex = activeAvatarNearestWaypointIndex(kiraHomeWorldWaypoints, activeMarker.position);
    activeMarker.userData.waitUntil = t + 1.0;
    activeMarker.userData.lastMoveT = t;
    activeMarker.userData.lastSafePosition = activeMarker.position.clone();
    activeMarker.userData.stuckSince = null;
    activeMarker.userData.lastDistanceToTarget = null;
    recordMovementLearningAttempt({
      skill: "route_safety",
      phase: "stale_upstairs_zone_repaired_in_place_no_runtime_teleport",
      target: "Kira current grounded position",
      teleported: false,
    });
  }
  if (!activeMarker.userData.roamReady) {
    activeMarker.userData.roamReady = true;
    const startZone = activeAvatarDefaultRoamZone();
    activeMarker.userData.roamZone = startZone;
    const startRoute = activeAvatarDefaultWaypoints();
    activeMarker.userData.usesGenericAutonomy = true;
    activeMarker.userData.roamPolicy = "self_directed_random_goal_learning";
    activeMarker.userData.autonomousRoamTarget = null;
    activeMarker.userData.autonomousRoamHistory = activeMarker.userData.autonomousRoamHistory || [];
    activeMarker.userData.roamIndex = activeAvatarNearestWaypointIndex(startRoute, activeMarker.position);
    activeMarker.userData.lastMoveT = t;
    activeMarker.userData.waitUntil = t + 0.7;
    activeMarker.userData.lastSafePosition = activeMarker.position.clone();
    activeMarker.userData.stuckSince = null;
    activeMarker.userData.lastRoamPracticeKey = null;
  }
  const lastT = activeMarker.userData.lastMoveT ?? t;
  const dt = Math.min(Math.max(t - lastT, 0), 0.05);
  activeMarker.userData.lastMoveT = t;
  if (updateActiveDoorInteraction(t, dt)) {
    applyActiveAvatarSupport(dt);
    return;
  }
  if (updateActiveAvatarSkillInteraction(t, dt)) {
    return;
  }
  if (isMarinetteLike) {
    maybeAutoStartActiveAvatarSelfTest(t);
    if (!activeMarker.userData.allowBathroomPractice && activeAvatarInsideSharedBathroom()) {
      recoverActiveAvatarFromRouteStuck(t, "left_autonomous_route_for_shared_bathroom");
      applyActiveAvatarSupport(dt);
      return;
    }
    if (updateActiveFurnitureInteraction(t)) {
      applyActiveAvatarSupport(dt);
      return;
    }
    if (updateActivePostureInteraction(t)) {
      applyActiveAvatarSupport(dt);
      return;
    }
    if (updateActiveAvatarSelfTest(t)) {
      applyActiveAvatarSupport(dt);
      return;
    }
  }
  if (t < (activeMarker.userData.waitUntil || 0)) {
    activeMarker.userData.isMoving = false;
    activeMarker.userData.walkSpeed = 0;
    activeMarker.userData.lastStepMeters = 0;
    if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
    applyActiveAvatarSupport(dt);
    return;
  }

  let target = null;
  let targetIndex = null;
  const recoveryTarget = activeAvatarNavigationRecoveryTarget(t);
  const usingRecovery = !!recoveryTarget;
  const usingAutonomousRoam = !usingRecovery && activeAvatarUsingAutonomousRoam();
  if (activeAvatarIsKiraLike() && !usingRecovery && !activeMarker.userData.practiceRoute) {
    activeMarker.userData.roamPolicy = "person_owned_intent_only";
    activeMarker.userData.isMoving = false;
    activeMarker.userData.walkSpeed = 0;
    activeMarker.userData.lastStepMeters = 0;
    activeMarker.userData.lastDistanceToTarget = null;
    if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
    applyActiveAvatarSupport(dt);
    return;
  }
  const route = usingAutonomousRoam ? [] : activeAvatarCurrentWaypoints();
  const routeLength = Math.max(1, route.length);
  const baseIndex = usingAutonomousRoam ? 0 : activeMarker.userData.roamIndex % routeLength;
  activeMarker.userData.stairTraversalActive = activeMarker.userData.practiceRoute?.id === "stairs_step";
  if (usingRecovery) {
    target = recoveryTarget;
    targetIndex = null;
    activeMarker.userData.gaitMode = "walk";
  } else if (usingAutonomousRoam) {
    target = activeAvatarCurrentAutonomousTarget(t);
    targetIndex = null;
    activeMarker.userData.gaitMode = activeMarker.userData.autonomousGaitMode || "walk";
  } else if (activeMarker.userData.practiceRoute) {
    const index = Math.min(Math.max(baseIndex, 0), routeLength - 1);
    target = route[index];
    targetIndex = index;
  } else {
    for (let offset = 0; offset < routeLength; offset += 1) {
      const index = (baseIndex + offset) % routeLength;
      const candidate = route[index];
      if (!isAvatarBlocked(candidate.x, candidate.z, candidate.y, 0.46)) {
        activeMarker.userData.roamIndex = index;
        target = candidate;
        targetIndex = index;
        break;
      }
    }
  }
  if (!target) {
    activeMarker.userData.waitUntil = t + 1.0;
    activeMarker.userData.isMoving = false;
    activeMarker.userData.walkSpeed = 0;
    activeMarker.userData.lastStepMeters = 0;
    if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
    applyActiveAvatarSupport(dt);
    return;
  }
  const dx = target.x - activeMarker.position.x;
  const dz = target.z - activeMarker.position.z;
  const dy = target.y - activeMarker.position.y;
  const horizontalDistance = Math.hypot(dx, dz);
  if (horizontalDistance < 0.32 && Math.abs(dy) < 0.12) {
    if (usingRecovery) {
      const completedRecovery = activeMarker.userData.navigationRecovery;
      activeMarker.userData.navigationRecovery = null;
      activeMarker.userData.waitUntil = t + 0.28;
      activeMarker.userData.isMoving = false;
      activeMarker.userData.walkSpeed = 0;
      activeMarker.userData.lastStepMeters = 0;
      activeMarker.userData.lastDistanceToTarget = null;
      activeMarker.userData.lastSafePosition = activeMarker.position.clone();
      if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
      recordMovementLearningAttempt({
        skill: "route_safety",
        phase: "collision_checked_recovery_walk_finished",
        target: completedRecovery?.reason || "route_stuck",
        teleported: false,
      });
      applyActiveAvatarSupport(dt);
      return;
    }
    if (usingAutonomousRoam) {
      const reached = activeMarker.userData.autonomousRoamTarget;
      activeMarker.userData.autonomousGoalCount = (activeMarker.userData.autonomousGoalCount || 0) + 1;
      recordMovementLearningAttempt({
        skill: "autonomous_roam",
        phase: "goal_reached",
        target: reached?.id || "self-selected local goal",
        actor: activeAvatarDisplayName(),
        roamPolicy: activeMarker.userData.roamPolicy,
      });
      clearActiveAvatarAutonomousRoamTarget("goal_reached");
      if (maybeStartActiveAvatarAutonomousIdleActivity(t)) {
        applyActiveAvatarSupport(dt);
        return;
      }
      activeMarker.userData.waitUntil = t + 1.0 + Math.random() * 2.2;
      activeMarker.userData.isMoving = false;
      activeMarker.userData.walkSpeed = 0;
      activeMarker.userData.lastStepMeters = 0;
      activeMarker.userData.lastDistanceToTarget = null;
      if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
      applyActiveAvatarSupport(dt);
      return;
    }
    if (activeMarker.userData.practiceRoute && targetIndex >= routeLength - 1 && finishActiveAvatarPracticeRoute(t)) {
      applyActiveAvatarSupport(dt);
      if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
      return;
    }
    if (tryStartActiveAvatarRoamPractice(targetIndex ?? baseIndex)) {
      applyActiveAvatarSupport(dt);
      return;
    }
    activeMarker.userData.roamIndex += 1;
    if (activeMarker.userData.practiceRoute) activeMarker.userData.practiceRoute.progressWatch = null;
    activeMarker.userData.waitUntil = activeMarker.userData.practiceRoute
      ? t + 0.12
      : t + 1.5 + ((activeMarker.userData.roamIndex % 3) * 0.45);
    activeMarker.userData.isMoving = false;
    activeMarker.userData.walkSpeed = 0;
    activeMarker.userData.lastStepMeters = 0;
    activeMarker.userData.lastDistanceToTarget = null;
    if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
    applyActiveAvatarSupport(dt);
    return;
  }
  const speed = usingRecovery
    ? ACTIVE_AVATAR_WALK_SPEED_GROUND * 0.72
    : activeMarker.userData.practiceRoute?.id === "stairs_step"
    ? ACTIVE_AVATAR_STAIR_PRACTICE_SPEED
    : activeMarker.userData.practiceRoute?.speed
      ? activeMarker.userData.practiceRoute.speed
    : usingAutonomousRoam && activeMarker.userData.gaitMode === "jog"
      ? ACTIVE_AVATAR_JOG_SPEED_GROUND * 0.72
    : target.y > 2 || activeMarker.position.y > 2 ? ACTIVE_AVATAR_WALK_SPEED_UPSTAIRS : ACTIVE_AVATAR_WALK_SPEED_GROUND;
  const desiredHeading = Math.atan2(dx, dz);
  const directLookAheadDistance = Math.min(
    horizontalDistance,
    Math.max(speed * dt, ACTIVE_AVATAR_COLLISION_LOOKAHEAD_METERS),
  );
  const directLookAheadX = activeMarker.position.x + Math.sin(desiredHeading) * directLookAheadDistance;
  const directLookAheadZ = activeMarker.position.z + Math.cos(desiredHeading) * directLookAheadDistance;
  if (activeAvatarCanUseDoors() && openDoorForActiveAvatar(directLookAheadX, directLookAheadZ, activeMarker.position.y)) return;

  const steering = selectCollisionFreeHeading({
    originX: activeMarker.position.x,
    originZ: activeMarker.position.z,
    desiredHeading,
    stepDistance: Math.min(horizontalDistance, speed * dt),
    lookAheadDistance: directLookAheadDistance,
    isBlocked: (x, z) => isAvatarBlocked(x, z, activeMarker.position.y, ACTIVE_AVATAR_COLLISION_RADIUS),
  });
  if (!steering) {
    if (activeMarker.userData.transitionEvidence) activeMarker.userData.transitionEvidence.collisionBlocked = true;
    if (usingAutonomousRoam) clearActiveAvatarAutonomousRoamTarget("predictive_wall_avoidance");
    recoverActiveAvatarFromRouteStuck(t, "blocked_step");
    if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
    applyActiveAvatarSupport(dt);
    return;
  }
  activeMarker.userData.localSteeringEvidence = {
    mode: "combined_xz_collision_checked_heading_v1",
    direct: steering.direct,
    offsetRadians: Number(steering.offsetRadians.toFixed(4)),
    axisWallSlideUsed: false,
    checkedAtSeconds: Number(t.toFixed(3)),
    visuallyReviewedThisSession: false,
  };
  const targetYaw = steering.heading + Math.PI;
  const remainingTurn = turnActiveAvatarTowardYaw(targetYaw, dt);
  const turnTranslationScale = translationScaleForTurn(
    remainingTurn,
    ACTIVE_AVATAR_TURN_BEFORE_TRANSLATE_RADIANS,
    ACTIVE_AVATAR_TURN_FULL_TRANSLATE_RADIANS,
  );
  const step = Math.min(horizontalDistance, speed * dt * turnTranslationScale);
  activeMarker.userData.isMoving = step > 0.002 || Math.abs(dy) > 0.02;
  activeMarker.userData.walkSpeed = speed;
  const previousPosition = activeMarker.position.clone();
  if (horizontalDistance > 0.001 && step <= 0.0001) {
    activeMarker.userData.isMoving = false;
    activeMarker.userData.walkSpeed = 0;
    activeMarker.userData.lastStepMeters = 0;
    if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
    applyActiveAvatarSupport(dt);
    return;
  }
  if (horizontalDistance > 0.001) {
    const nextX = activeMarker.position.x + Math.sin(steering.heading) * step;
    const nextZ = activeMarker.position.z + Math.cos(steering.heading) * step;
    const moved = step > 0.0001
      && !isAvatarBlocked(nextX, nextZ, activeMarker.position.y, ACTIVE_AVATAR_COLLISION_RADIUS);
    if (moved) {
      // X and Z are committed together after one swept-heading collision check.
      // Independent axis writes caused the earlier wall-sliding/zombie motion.
      activeMarker.position.set(nextX, activeMarker.position.y, nextZ);
    }
    if (!moved) {
      if (activeMarker.userData.transitionEvidence) activeMarker.userData.transitionEvidence.collisionBlocked = true;
      if (!activeMarker.userData.stuckSince) activeMarker.userData.stuckSince = t;
      if (t - activeMarker.userData.stuckSince > 0.75) {
        if (usingAutonomousRoam) clearActiveAvatarAutonomousRoamTarget("blocked_step");
        recoverActiveAvatarFromRouteStuck(t, "blocked_step");
      } else {
        activeMarker.userData.waitUntil = t + 0.18;
      }
      activeMarker.userData.isMoving = false;
      activeMarker.userData.walkSpeed = 0;
      activeMarker.userData.lastStepMeters = 0;
      if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
      applyActiveAvatarSupport(dt);
      return;
    }
    const previousDistance = activeMarker.userData.lastDistanceToTarget;
    if (previousDistance !== null && previousDistance !== undefined && previousDistance - horizontalDistance < 0.002) {
      if (!activeMarker.userData.stuckSince) activeMarker.userData.stuckSince = t;
      if (t - activeMarker.userData.stuckSince > 1.15) {
        if (usingAutonomousRoam) clearActiveAvatarAutonomousRoamTarget("no_route_progress");
        recoverActiveAvatarFromRouteStuck(t, "no_route_progress");
        if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
        applyActiveAvatarSupport(dt);
        return;
      }
    } else {
      activeMarker.userData.stuckSince = null;
    }
    activeMarker.userData.lastDistanceToTarget = horizontalDistance;
    if (!isAvatarBlocked(activeMarker.position.x, activeMarker.position.z, activeMarker.position.y, 0.58)) {
      activeMarker.userData.lastSafePosition = activeMarker.position.clone();
    }
  }
  const movedMeters = Math.hypot(
    activeMarker.position.x - previousPosition.x,
    activeMarker.position.z - previousPosition.z,
  );
  activeMarker.userData.lastStepMeters = movedMeters;
  const transition = activeMarker.userData.transitionEvidence;
  if (transition && movedMeters > 0.0001) {
    transition.distanceMeters = Number(((transition.distanceMeters || 0) + movedMeters).toFixed(3));
    transition.path = Array.isArray(transition.path) ? transition.path : [];
    const prior = transition.path[transition.path.length - 1];
    if (!prior || Math.hypot(activeMarker.position.x - prior.x, activeMarker.position.z - prior.z) >= 0.25) {
      transition.path.push({
        x: Number(activeMarker.position.x.toFixed(3)),
        y: Number(activeMarker.position.y.toFixed(3)),
        z: Number(activeMarker.position.z.toFixed(3)),
      });
      if (transition.path.length > 160) transition.path.shift();
      transition.pathSampleCount = transition.path.length;
    }
  }
  const progressRoute = !usingRecovery && !usingAutonomousRoam ? activeMarker.userData.practiceRoute : null;
  if (progressRoute && movedMeters > 0.0001) {
    const remainingAfterStep = Math.hypot(
      target.x - activeMarker.position.x,
      target.z - activeMarker.position.z,
    );
    progressRoute.progressWatch = updateRouteProgressWatch(progressRoute.progressWatch, {
      t,
      x: activeMarker.position.x,
      z: activeMarker.position.z,
      distance: remainingAfterStep,
    });
    if (progressRoute.progressWatch.oscillating || progressRoute.progressWatch.stalled) {
      const failureReason = progressRoute.progressWatch.oscillating
        ? "route_oscillation_detected"
        : "bounded_no_route_progress";
      recordMovementLearningAttempt({
        skill: progressRoute.id,
        phase: failureReason,
        target: progressRoute.finishHold?.label || progressRoute.id,
        pathLengthMeters: Number((progressRoute.progressWatch.pathLengthMeters || 0).toFixed(3)),
        netMeters: Number((progressRoute.progressWatch.netMeters || 0).toFixed(3)),
        personOwnedIntent: !!progressRoute.selfChosen,
        teleported: false,
      });
      recoverActiveAvatarFromRouteStuck(t, failureReason);
      if (activeAvatarActionIsGroundedLocomotion()) setActiveAvatarAction("idle");
      applyActiveAvatarSupport(dt);
      return;
    }
  }
  if (movedMeters > 0.0001) {
    activeAvatarMovePhase = (activeAvatarMovePhase + (movedMeters / ACTIVE_AVATAR_WALK_STRIDE_METERS) * Math.PI * 2) % (Math.PI * 2);
    activeMarker.userData.walkCyclePhase = activeAvatarMovePhase;
  }
  const stairAdjusted = updateActiveAvatarStairPractice(t);
  if (!stairAdjusted) applyActiveAvatarSupport(dt);
  if (activeAvatarAction === "door_open_reach" && t - activeAvatarActionStarted > 1.15) {
    setActiveAvatarAction(activeMarker.userData.isMoving ? activeAvatarLocomotionActionForGait(activeMarker.userData.gaitMode || "walk") : "idle");
  } else if (activeMarker.userData.isMoving && activeAvatarAction === "idle") {
    setActiveAvatarAction(activeAvatarLocomotionActionForGait(activeMarker.userData.practiceRoute?.gaitMode || activeMarker.userData.gaitMode || activeMarker.userData.autonomousGaitMode || "walk"));
  }
}

function setStartPosition() {
  if (startArea === "library") {
    player.position.set(24, 1.65, 36.8);
    player.yaw = 0;
    show("At the new public library across the street. Books, media shelves, and reading tables are physical props.");
  } else if (startArea === "stripmall") {
    if (HOME_WORLD_LEGACY_STRIP_MALL_ENABLED) {
      player.position.set(0, 1.65, 28.5);
      player.yaw = 0;
      show("Across the street at the restored legacy strip mall.");
    } else {
      player.position.set(0, 1.65, 28.5);
      player.yaw = 0;
      show("Across the street at the intentionally empty former strip-mall lot. The source is preserved behind ?stripMall=1.");
    }
  } else if (startArea === "spa") {
    if (HOME_WORLD_LEGACY_STRIP_MALL_ENABLED) {
      player.position.set(2.4, 1.65, 30.2);
      player.yaw = 0;
      show("At the restored legacy AI Body Spa blockout. The real spa remains a separate notebook world.");
    } else {
      player.position.set(0, 1.65, 28.5);
      player.yaw = 0;
      show("The former Home World spa site is intentionally empty. The staged legal spa remains a separate notebook world.");
    }
  } else if (HOME_WORLD_PRE_RAM_LIGHT_MODE && (startArea === "capture_flag" || startArea === "captureflag")) {
    player.position.set(0, 1.65, 7.2);
    player.yaw = Math.PI;
    show("Capture The Flag world is disabled in pre-RAM light mode.");
  } else if (startArea === "capture_flag" || startArea === "captureflag") {
    player.position.copy(captureFlagWorld.battlefieldArrival);
    player.floor = 0;
    player.yaw = 0;
    startCaptureFlagGame("player");
    show("At the Capture The Flag notebook world base camp. Touch the glowing flag and get back without being tagged.");
  } else if (startArea === "upstairs") {
    player.position.set(ONE_BEDROOM_HOUSE_ENTRY.x, 1.65, ONE_BEDROOM_HOUSE_ENTRY.z + 0.35);
    player.floor = 0;
    player.yaw = 0;
    show("The two-story main house has been removed for this pass. Starting at the repaired one-bedroom house.");
  } else if (startArea === "one_bedroom_bedroom" || startArea === "bedroom") {
    player.position.set(ONE_BEDROOM_HOUSE_LEFT_X + 4.55, 1.65, ONE_BEDROOM_HOUSE_BACK_Z + 8.9);
    player.floor = 0;
    player.yaw = Math.PI / 2;
    show("Inside the one-bedroom bedroom inspection start.");
  } else if (startArea === "one_bedroom_kitchen" || startArea === "kitchen") {
    player.position.set(ONE_BEDROOM_HOUSE_RIGHT_X - 5.0, 1.65, ONE_BEDROOM_HOUSE_BACK_Z + 4.1);
    player.floor = 0;
    player.yaw = -0.78;
    show("Inside the one-bedroom kitchen inspection start.");
  } else if (startArea === "one_bedroom_living" || startArea === "living") {
    player.position.set(ONE_BEDROOM_HOUSE_RIGHT_X - 5.65, 1.65, ONE_BEDROOM_HOUSE_FRONT_Z - 5.15);
    player.floor = 0;
    player.yaw = Math.PI;
    show("Inside the one-bedroom living room inspection start.");
  } else if (startArea === "one_bedroom_bathroom" || startArea === "bathroom") {
    player.position.set(ONE_BEDROOM_HOUSE_LEFT_X + 6.2, 1.65, ONE_BEDROOM_HOUSE_BACK_Z + 3.72);
    player.floor = 0;
    player.yaw = Math.PI / 2;
    show("Inside the one-bedroom bathroom inspection start.");
  } else if (startArea === "one_bedroom_yard" || startArea === "yard") {
    player.position.set(ONE_BEDROOM_HOUSE_CENTER.x - 3.7, 1.65, ONE_BEDROOM_HOUSE_FRONT_Z + 8.0);
    player.floor = 0;
    player.yaw = 0;
    show("Outside the one-bedroom house inspection start.");
  } else if (startArea === "tardis_arrival") {
    player.position.set(-12.8, 1.65, 14.8);
    player.yaw = Math.PI;
    show("Arrived in Home World by TARDIS. The blue box stays only for this arrival or a new call.");
  } else {
    player.position.set(ONE_BEDROOM_HOUSE_ENTRY.x, 1.65, ONE_BEDROOM_HOUSE_ENTRY.z + 0.35);
    player.yaw = 0;
    show("At the repaired one-bedroom house front door. Walk inside to inspect the living room, kitchen, bedroom, and bathroom fixes.");
  }
}

function updateCamera() {
  camera.position.copy(player.position);
  camera.rotation.order = "YXZ";
  camera.rotation.y = player.yaw;
  camera.rotation.x = player.pitch;
}

function updateObserveFollowButton() {
  if (!observeFollowButton) return;
  observeFollowButton.textContent = observeFollowEnabled ? "Stop Following" : "Observe / Follow";
  observeFollowButton.classList.toggle("active", observeFollowEnabled);
  observeFollowButton.style.background = observeFollowEnabled ? "rgba(26,86,116,0.92)" : "rgba(7,17,28,0.86)";
  observeFollowButton.style.borderColor = observeFollowEnabled ? "rgba(185,238,255,0.96)" : "rgba(127,215,255,0.78)";
}

function safeActiveAvatarSnapshotField(label, factory, fallback = null) {
  try {
    return factory();
  } catch (error) {
    if (activeMarker) {
      const previous = activeMarker.userData?.snapshotTelemetryErrors || {};
      activeMarker.userData.snapshotTelemetryErrors = {
        ...previous,
        [label]: {
          atSeconds: Number(clock.elapsedTime.toFixed(3)),
          message: String(error?.message || error || "unknown snapshot error"),
        },
      };
    }
    console.warn(`[Kira body state] Optional ${label} telemetry failed; publishing core body state.`, error);
    return fallback;
  }
}

function postActiveAvatarSnapshot(t, force = false, requestId = "") {
  if (!activeMarker || !activeShellState?.active_candidate) return;
  if (!force && t - lastActiveAvatarSnapshotPostAt < 2.5) return;
  lastActiveAvatarSnapshotPostAt = t;
  const sequence = ++activeAvatarSnapshotSequence;
  const place = safeActiveAvatarSnapshotField("place", () => activeAvatarNamedPlaceSnapshot(), {
    id: "unlabelled_current_ground_position",
    label: "current body position",
    kind: "ground_position",
  });
  const affordances = safeActiveAvatarSnapshotField("affordances", () => activeAvatarAffordanceSnapshot(place), []);
  const truthByAction = {
    read_book: safeActiveAvatarSnapshotField("truth_read_book", () => activityTruthForAction("read_book"), null),
    project_work: safeActiveAvatarSnapshotField("truth_project_work", () => activityTruthForAction("project_work"), null),
    creative_write: safeActiveAvatarSnapshotField("truth_creative_write", () => activityTruthForAction("creative_write"), null),
    take_notes: safeActiveAvatarSnapshotField("truth_take_notes", () => activityTruthForAction("take_notes"), null),
    look_online: safeActiveAvatarSnapshotField("truth_look_online", () => activityTruthForAction("look_online"), null),
    use_computer: safeActiveAvatarSnapshotField("truth_use_computer", () => activityTruthForAction("use_computer"), null),
    use_phone: safeActiveAvatarSnapshotField("truth_use_phone", () => activityTruthForAction("use_phone"), null),
    drink: safeActiveAvatarSnapshotField("truth_drink", () => activityTruthForAction("drink"), null),
    drink_coffee: safeActiveAvatarSnapshotField("truth_drink_coffee", () => activityTruthForAction("drink_coffee"), null),
    attend_school: safeActiveAvatarSnapshotField("truth_attend_school", () => activityTruthForAction("attend_school"), null),
    eat_food: safeActiveAvatarSnapshotField("truth_eat_food", () => activityTruthForAction("eat_food"), null),
  };
  const autonomousTarget = activeMarker.userData?.autonomousRoamTarget || null;
  const practiceRouteProgress = safeActiveAvatarSnapshotField(
    "practice_route_progress",
    () => activeAvatarPracticeRouteProgressSnapshot(),
    null,
  );
  const autonomousIntentDistanceMeters = autonomousTarget
    ? Number(Math.hypot(autonomousTarget.x - activeMarker.position.x, autonomousTarget.z - activeMarker.position.z).toFixed(3))
    : practiceRouteProgress?.distanceMeters ?? null;
  window.parent?.postMessage({
    type: "kira-active-avatar-snapshot",
    requestId,
    snapshot: {
      snapshotSequence: sequence,
      snapshotRequestId: requestId,
      capturedAtMonotonicSeconds: Number(t.toFixed(3)),
      candidate: activeShellState.active_candidate,
      label: activeMarker.userData?.label || activeShellState.active_label || "",
      location: activeShellState.location || startArea || "home",
      world: "home_world",
      position: {
        x: Number(activeMarker.position.x.toFixed(3)),
        y: Number(activeMarker.position.y.toFixed(3)),
        z: Number(activeMarker.position.z.toFixed(3)),
      },
      place,
      affordances,
      autonomousIntent: autonomousTarget?.id || activeMarker.userData?.skillInteraction || null,
      autonomousIntentDistanceMeters,
      bodyIntent: practiceRouteProgress ? {
        source: practiceRouteProgress.personOwnedIntent ? "person_owned_self_intent" : "runtime_route",
        id: practiceRouteProgress.id,
        status: practiceRouteProgress.status,
        currentWaypoint: practiceRouteProgress.waypointLabel,
        distanceMeters: practiceRouteProgress.distanceMeters,
      } : null,
      practiceRouteProgress,
      roamZone: activeMarker.userData?.roamZone || "",
      roamIndex: Number.isFinite(activeMarker.userData?.roamIndex) ? activeMarker.userData.roamIndex : null,
      action: activeAvatarAction,
      supportState: activeMarker.userData?.supportState || {},
      activeMoving: !!activeMarker.userData?.isMoving,
      activeGaitMode: activeMarker.userData?.gaitMode || activeMarker.userData?.autonomousGaitMode || null,
      transitionEvidence: activeMarker.userData?.transitionEvidence || null,
      lastEmbodimentCapabilityBlock: activeMarker.userData?.lastEmbodimentCapabilityBlock || null,
      lastRouteFailureTruth: activeMarker.userData?.lastRouteFailureTruth || null,
      activeHeldProp: safeActiveAvatarSnapshotField("held_prop", () => activeHeldPropEvidenceSnapshot(), null),
      wardrobeState: safeActiveAvatarSnapshotField("wardrobe", () => activeAvatarWardrobeSnapshot(), {}),
      activityTruth: safeActiveAvatarSnapshotField("activity_truth", () => activityTruthForAction(activeAvatarAction), null),
      activityTruthByAction: truthByAction,
      mindBodyTruth: activeMarker.userData?.lastMindBodyTruth || safeActiveAvatarSnapshotField(
        "mind_body_truth",
        () => activeMindBodyTruthSnapshot("snapshot_post", activeShellState?.active_action || activeAvatarAction),
        null,
      ),
      armMotionEvidence: activeMarker.userData?.armMotionEvidence || null,
      kiraExistingMouthLipSync: activeAvatarIsKiraLike()
        ? safeActiveAvatarSnapshotField("existing_mouth_lipsync", () => kiraExistingMouthLipSyncProbe(), null)
        : null,
      kiraEyeRig: activeAvatarIsKiraLike()
        ? safeActiveAvatarSnapshotField("eye_rig", () => activeKiraEyeRig ? kiraEyeBindingProbe() : {
          active: false,
          version: KIRA_EYE_CONTROL_EXAM_VERSION,
          disabledReason: "staged_eye_rig_not_attached",
        }, null)
        : null,
      visualGroundContact: activeMarker.userData?.visualGroundContact || null,
      turnEvidence: activeMarker.userData?.turnEvidence || null,
      navigationRecovery: activeMarker.userData?.navigationRecovery || null,
      localSteeringEvidence: activeMarker.userData?.localSteeringEvidence || null,
      locomotionTransition: activeMarker.userData?.locomotionTransition || null,
      doorInteraction: activeDoorInteraction ? {
        id: activeDoorInteraction.id,
        opened: !!activeDoorInteraction.opened,
        failed: !!activeDoorInteraction.failed,
        gripped: !!activeDoorInteraction.gripped,
        ikSolved: !!activeDoorInteraction.ikSolved,
        ikGripLocked: !!activeDoorInteraction.ikGripLocked,
        preferredHand: activeDoorInteraction.preferredHand || "R",
        handContact: activeDoorInteraction.handContact || null,
      } : null,
      activeSkillInteraction: activeSkillInteraction ? {
        id: activeSkillInteraction.id,
        kind: activeSkillInteraction.kind,
        action: activeSkillInteraction.action,
      } : activeMarker.userData?.skillInteraction || null,
      persistentQuietActivity: safeActiveAvatarSnapshotField("quiet_activity", () => persistentQuietActivitySnapshot(), null),
      postureInteraction: activePostureInteraction ? {
        id: activePostureInteraction.id,
        action: activePostureInteraction.action,
      } : null,
      postureState: activeMarker.userData?.postureState || null,
      tardisState: safeActiveAvatarSnapshotField("tardis", () => activeAvatarHomeTardisStateSnapshot(), null),
      telemetryErrors: activeMarker.userData?.snapshotTelemetryErrors || {},
    },
  }, "*");
}

function setObserveFollow(enabled = true) {
  observeFollowEnabled = !!enabled;
  if (observeFollowEnabled && !activeMarker) {
    observeFollowEnabled = false;
    show("No active body is available to observe yet.");
  } else if (observeFollowEnabled) {
    show("Observe/Follow active. The camera follows the active body and enemies ignore you as a watcher.");
  } else {
    show("Observe/Follow off. Manual walking restored.");
  }
  updateObserveFollowButton();
  if (window.parent && window.parent !== window) {
    window.parent.postMessage({ type: "kira-observe-follow-state", enabled: observeFollowEnabled }, "*");
  }
  if (observeFollowEnabled) updateObserveFollowCamera();
  else updateCamera();
  return observeFollowEnabled;
}

function updateObserveFollowCamera() {
  if (!observeFollowEnabled || !activeMarker) return;
  const target = activeMarker.position.clone();
  const followYaw = activeMarker.rotation?.y || 0;
  const behind = new THREE.Vector3(0, 1.18, 4.1).applyAxisAngle(new THREE.Vector3(0, 1, 0), followYaw);
  const eye = target.clone().add(behind);
  player.position.copy(eye);
  player.floor = target.y > 2 ? 1 : 0;
  const dx = target.x - eye.x;
  const dz = target.z - eye.z;
  player.yaw = Math.atan2(-dx, -dz);
  player.pitch = THREE.MathUtils.clamp(-0.18 + (target.y - eye.y) * 0.04, -0.9, 0.35);
  updateCamera();
}

function createObserveFollowButton() {
  if (params.get("showObserveOverlay") !== "1") return;
  const button = document.createElement("button");
  button.id = "observe-follow";
  button.type = "button";
  button.textContent = "Observe / Follow";
  Object.assign(button.style, {
    position: "fixed",
    right: "360px",
    top: "14px",
    zIndex: "20",
    padding: "9px 12px",
    borderRadius: "6px",
    border: "1px solid rgba(127,215,255,0.78)",
    background: "rgba(7,17,28,0.86)",
    color: "#f5fbff",
    font: "600 13px Segoe UI, Arial, sans-serif",
    cursor: "pointer",
  });
  button.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    setObserveFollow(!observeFollowEnabled);
  });
  document.body.appendChild(button);
  observeFollowButton = button;
  updateObserveFollowButton();
}

function observationSample(reason = "manual_observation_sample") {
  const sample = {
    reason,
    iso: new Date().toISOString(),
    seconds: Number(clock.elapsedTime.toFixed(3)),
    observeFollowEnabled,
    runtime: window.__kiraHomeWorldRuntime || null,
    mindBodyTruth: activeMindBodyTruthSnapshot(reason, activeShellState?.active_action || activeAvatarAction),
    truthPropsNearActive: activityTruthProps
      .map((prop) => truthPropSnapshot(prop, activeMarker?.position || null))
      .filter(Boolean)
      .sort((a, b) => (a.distanceMeters ?? 999) - (b.distanceMeters ?? 999))
      .slice(0, 10),
  };
  return sample;
}

function startObservationReport(options = {}) {
  const intervalSeconds = Number.isFinite(options.intervalSeconds) ? Math.max(10, options.intervalSeconds) : 60;
  observationReportState = {
    running: true,
    startedAt: clock.elapsedTime,
    intervalSeconds,
    nextAt: clock.elapsedTime,
    samples: [],
  };
  setObserveFollow(true);
  show(`Observation report running. Sampling every ${intervalSeconds.toFixed(0)} seconds.`);
  return observationReportState;
}

function stopObservationReport() {
  observationReportState.running = false;
  show("Observation report stopped.");
  return observationReportState;
}

function updateObservationReport(t) {
  if (!observationReportState.running || t < observationReportState.nextAt) return;
  const sample = observationSample("in_world_observation_interval");
  observationReportState.samples.push(sample);
  if (observationReportState.samples.length > 240) observationReportState.samples.shift();
  observationReportState.nextAt = t + observationReportState.intervalSeconds;
  try {
    window.localStorage.setItem("kira.observation.latest", JSON.stringify(sample));
  } catch (err) {
    // Observation still works live if browser storage is unavailable.
  }
}

window.kiraHomeWorldDebug = {
  focusActiveAvatar(offset = {}) {
    if (!activeMarker) return false;
    const target = activeMarker.position.clone();
    const eye = target.clone().add(new THREE.Vector3(offset.x ?? 2.1, offset.y ?? 1.42, offset.z ?? 3.1));
    player.position.copy(eye);
    player.floor = target.y > 2 ? 1 : 0;
    const dx = target.x - eye.x;
    const dz = target.z - eye.z;
    player.yaw = Math.atan2(-dx, -dz);
    player.pitch = -0.12;
    updateCamera();
    return true;
  },
  injectShellState(shellState = {}) {
    setActiveMarker(shellState);
    syncGroupPresenceOrbs(shellState);
    return window.__kiraHomeWorldRuntime || {
      activeLabel: activeMarker?.userData?.label || null,
      activeModelLoaded: !!activeAvatarRoot,
    };
  },
  activeAvatarState() {
    return {
      activeLabel: activeMarker?.userData?.label || activeShellState?.active_label || null,
      activeCandidate: activeShellState?.active_candidate || null,
      markerPresent: !!activeMarker,
      markerKind: activeMarker?.userData?.kind || (activeAvatarRoot ? "loaded_model" : null),
      markerChildCount: activeMarker?.children?.length || 0,
      rootPresent: !!activeAvatarRoot,
      modelUrl: activeAvatarModelUrl || null,
      action: activeAvatarAction,
      skillInteraction: activeSkillInteraction ? {
        id: activeSkillInteraction.id,
        kind: activeSkillInteraction.kind,
        action: activeSkillInteraction.action,
      } : activeMarker?.userData?.skillInteraction || null,
      persistentQuietActivity: persistentQuietActivitySnapshot(),
      gaitMode: activeMarker?.userData?.gaitMode || null,
      roamZone: activeMarker?.userData?.roamZone || null,
      garment: prototypeDressShirt ? prototypeDressShirt.toJSON() : null,
      moving: !!activeMarker?.userData?.isMoving,
      position: activeMarker ? {
        x: Number(activeMarker.position.x.toFixed(3)),
        y: Number(activeMarker.position.y.toFixed(3)),
        z: Number(activeMarker.position.z.toFixed(3)),
      } : null,
      rotationY: activeMarker ? Number(activeMarker.rotation.y.toFixed(6)) : null,
      proceduralRig: activeAvatarProceduralRigDiagnostics(),
      visualGroundContact: activeMarker?.userData?.visualGroundContact || null,
      voluntaryBodyActionPolicy: {
        subjectChoiceRequired: true,
        externalForceAllowed: false,
        actions: ["raise_hand", "sit_on_couch", "lie_on_couch", "lie_on_bed", "lie_on_ground", "sleep", "rest", "push_up"],
      },
      doctorBodyExam: activeMarker?.userData?.doctorBodyExam || null,
      comfortIdle: activeAvatarIsKiraLike() ? kiraComfortIdleStatus() : null,
      groundLieClearance: activeMarker?.userData?.groundLieClearance || null,
    };
  },
  kiraExistingMouthLipSync() {
    return kiraExistingMouthLipSyncProbe();
  },
  kiraExistingMouthScreenBounds() {
    return kiraExistingMouthScreenBounds();
  },
  kiraEyeSocketFit() {
    return activeKiraEyeRig ? kiraEyeBindingProbe().socketFitAudit : null;
  },
  kiraEyeRig() {
    return activeKiraEyeRig ? kiraEyeBindingProbe() : null;
  },
  setKiraR6EyeVisualFit(fit = {}) {
    if (!activeKiraEyeRig) return false;
    return applyKiraR6EyeVisualFit(activeKiraEyeRig, fit);
  },
  injectVoicePlaybackForHeadlessTest(playback = {}) {
    if (!HEADLESS_MOTION_SMOKE_ENABLED) return { accepted: false, reason: "headless_test_mode_required" };
    setActiveVoicePlaybackState(playback);
    return { accepted: true, playback: { ...activeVoicePlaybackState } };
  },
  resourceSnapshot() {
    let sceneMeshes = 0;
    scene.traverse((node) => {
      if (node.isMesh) sceneMeshes += 1;
    });
    const renderInfo = renderer.info?.render || {};
    const memoryInfo = renderer.info?.memory || {};
    return {
      measurementKind: "live_threejs_renderer_counters_not_process_ram_or_whole_gpu_vram",
      renderer: {
        frame: Number(renderInfo.frame || 0),
        calls: Number(renderInfo.calls || 0),
        triangles: Number(renderInfo.triangles || 0),
        lines: Number(renderInfo.lines || 0),
        points: Number(renderInfo.points || 0),
        geometries: Number(memoryInfo.geometries || 0),
        textures: Number(memoryInfo.textures || 0),
      },
      scene: {
        directChildren: scene.children.length,
        meshObjects: sceneMeshes,
        colliders: colliders.length,
        doorColliders: doorColliders.length,
        interactionZones: interactZones.length,
      },
      activeAvatarPresent: !!activeMarker,
      activeAvatarModelLoaded: !!activeAvatarRoot,
      legacyStripMall: homeWorldActivityStatus.legacyStripMall,
      limitation: "Use a controlled two-run process/GPU A/B for RAM or VRAM deltas; renderer counters alone cannot measure those values.",
    };
  },
  quietActivityState() {
    return persistentQuietActivitySnapshot();
  },
  startPersistentCouchReading(hours = 8) {
    const requestedHours = Math.max(4, Number(hours) || 8);
    return startActiveAvatarPersistentHomeRead({
      seconds: requestedHours * 60 * 60,
    });
  },
  continueQuietActivity(hours = 4) {
    const requestedHours = Math.max(1 / 60, Number(hours) || 4);
    return continuePersistentQuietActivity(requestedHours * 60 * 60, "voluntary_debug_continue");
  },
  exitQuietActivity(reason = "voluntary_debug_exit") {
    return exitPersistentQuietActivity(reason);
  },
  homeWorldActivityStatus() {
    const liveKiraHairStatus = activeKiraHairRig ? {
      ...homeWorldActivityStatus.kiraReddishHair,
      loaded: true,
      url: KIRA_REDDISH_HAIR_MODEL_URL,
      fittedSize: activeKiraHairRig.fittedSize ? {
        x: Number(activeKiraHairRig.fittedSize.x.toFixed(3)),
        y: Number(activeKiraHairRig.fittedSize.y.toFixed(3)),
        z: Number(activeKiraHairRig.fittedSize.z.toFixed(3)),
      } : homeWorldActivityStatus.kiraReddishHair?.fittedSize,
    } : homeWorldActivityStatus.kiraReddishHair;
    return {
      ...homeWorldActivityStatus,
      dressShirtPrototype: prototypeDressShirt ? prototypeDressShirt.toJSON() : homeWorldActivityStatus.dressShirtPrototype,
      closetPrototype: prototypeCloset ? prototypeCloset.toJSON() : homeWorldActivityStatus.closetPrototype,
      avatarDressingController: avatarDressingController ? avatarDressingController.toJSON() : null,
      kiraReddishHair: liveKiraHairStatus,
      oneBedroomBlueprintHouse: oneBedroomBlueprintHouseStatus,
      starbucksDoorOpen,
      temporaryCafeCups: starbucksTemporaryCups.filter((cup) => cup?.parent).length,
      kiraArmTest: activeKiraArmTestState ? {
        active: true,
        secondsRemaining: Number(Math.max(0, activeKiraArmTestState.seconds - (clock.elapsedTime - activeKiraArmTestState.startedAt)).toFixed(2)),
      } : { active: false },
      kiraDoctorBodyExam: activeKiraDoctorExamState ? {
        active: true,
        phase: activeMarker?.userData?.doctorBodyExam?.phase || null,
        phaseIndex: activeMarker?.userData?.doctorBodyExam?.index || 0,
        phaseCount: KIRA_DOCTOR_JOINT_PHASES.length,
        results: Array.from(activeKiraDoctorExamState.results.values()),
      } : activeMarker?.userData?.doctorBodyExam || null,
      kiraComfortIdle: activeAvatarIsKiraLike() ? kiraComfortIdleStatus() : null,
      kiraDreamState: activeKiraDreamState || null,
      basketballPractice: basketballPracticeState ? {
        active: true,
        phase: basketballPracticeState.phase,
        secondsRemaining: Number(Math.max(0, basketballPracticeState.seconds - (clock.elapsedTime - basketballPracticeState.startedAt)).toFixed(2)),
      } : { active: false },
      basketballBounceSecondsRemaining: Number(Math.max(0, basketballBounceUntil - clock.elapsedTime).toFixed(2)),
    };
  },
  setOneBedroomFridgeOpen(open = true) {
    setOneBedroomFridgeOpen(open);
    return this.homeWorldActivityStatus().oneBedroomBlueprintHouse.refrigerator;
  },
  setOneBedroomClosetOpen(open = true) {
    setOneBedroomHangingClosetOpen(open);
    return this.homeWorldActivityStatus().oneBedroomBlueprintHouse.oneBedroomCloset;
  },
  removeOneBedroomNotebookArtifacts() {
    return removeHomeWorldNotebookFieldArtifacts();
  },
  objectBounds(filter = "") {
    const needle = String(filter || "").toLowerCase();
    const results = [];
    scene.traverse((node) => {
      const name = String(node.name || "");
      if (!name || (needle && !name.toLowerCase().includes(needle))) return;
      if (!node.isMesh && node.children.length === 0) return;
      try {
        const box = new THREE.Box3().setFromObject(node);
        if (!Number.isFinite(box.min.x) || box.isEmpty()) return;
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        results.push({
          name,
          x: Number(center.x.toFixed(3)),
          y: Number(center.y.toFixed(3)),
          z: Number(center.z.toFixed(3)),
          sx: Number(size.x.toFixed(3)),
          sy: Number(size.y.toFixed(3)),
          sz: Number(size.z.toFixed(3)),
          visible: node.visible !== false,
        });
      } catch (err) {
        // Ignore nodes that do not have stable world bounds.
      }
    });
    return results.slice(0, 200);
  },
  collisionProbe(points = []) {
    const previousFloor = player.floor;
    const results = points.map((point) => {
      player.floor = point.floor ?? 0;
      return {
        label: point.label || "",
        x: Number(point.x),
        z: Number(point.z),
        floor: player.floor,
        blocked: isBlocked(Number(point.x), Number(point.z)),
      };
    });
    player.floor = previousFloor;
    return results;
  },
  planOneBedroomInteriorRoute(options = {}) {
    const start = new THREE.Vector3(
      Number(options.start?.x ?? activeMarker?.position.x ?? 0),
      Number(options.start?.y ?? activeMarker?.position.y ?? ACTIVE_AVATAR_GROUND_Y),
      Number(options.start?.z ?? activeMarker?.position.z ?? 0),
    );
    const goal = new THREE.Vector3(
      Number(options.goal?.x ?? ONE_BEDROOM_COFFEE_STATION_USE_SPOT.x),
      Number(options.goal?.y ?? start.y),
      Number(options.goal?.z ?? ONE_BEDROOM_COFFEE_STATION_USE_SPOT.z),
    );
    const plan = planActiveAvatarOneBedroomInteriorRoute(start, goal, "non_mutating_debug_probe");
    return {
      ok: !!plan.ok,
      reason: plan.reason || null,
      mode: plan.mode || null,
      visitedNodes: Number(plan.visitedNodes || 0),
      directPathClear: activeAvatarDirectPathIsClear(start, goal, ACTIVE_AVATAR_COLLISION_RADIUS),
      startBlocked: isAvatarBlocked(start.x, start.z, start.y, ACTIVE_AVATAR_COLLISION_RADIUS),
      goalBlocked: isAvatarBlocked(goal.x, goal.z, goal.y, ACTIVE_AVATAR_COLLISION_RADIUS),
      start: { x: start.x, y: start.y, z: start.z },
      goal: { x: goal.x, y: goal.y, z: goal.z },
      waypoints: (plan.waypoints || []).map((point) => ({
        x: Number(point.x.toFixed(3)),
        y: Number(point.y.toFixed(3)),
        z: Number(point.z.toFixed(3)),
      })),
    };
  },
  startHomeKitchenCoffeeForTest(options = {}) {
    return startActiveAvatarKitchenCoffeeHold({ ...options, selfChosen: true });
  },
  startHomeKitchenDrinkForTest(options = {}) {
    return startActiveAvatarKitchenDrinkHold({ ...options, selfChosen: true });
  },
  publishPersonOwnedBodyIntentForTest(action = "") {
    return maybeStartBodyPracticeFromShellAction(action);
  },
  activeHomeRouteProgress() {
    return {
      route: activeAvatarPracticeRouteProgressSnapshot(),
      failure: activeMarker?.userData?.lastRouteFailureTruth || null,
      body: activeMarker ? {
        x: Number(activeMarker.position.x.toFixed(3)),
        y: Number(activeMarker.position.y.toFixed(3)),
        z: Number(activeMarker.position.z.toFixed(3)),
      } : null,
      interaction: activeSkillInteraction ? {
        id: activeSkillInteraction.id || null,
        action: activeSkillInteraction.action || null,
        kind: activeSkillInteraction.kind || null,
        heldPropKind: activeHeldProp?.visible ? activeHeldPropKind : null,
      } : null,
    };
  },
  openStarbucksDoor(open = true) {
    setStarbucksDoorOpen(open);
    return this.homeWorldActivityStatus();
  },
  focusStarbucks(offset = {}) {
    setStarbucksDoorOpen(true);
    const target = new THREE.Vector3(STARBUCKS_CENTER.x, 1.35, STARBUCKS_PUBLIC_FRONT_Z + 1.05);
    player.position.set(offset.x ?? STARBUCKS_CENTER.x - 2.8, offset.y ?? 1.55, offset.z ?? STARBUCKS_PUBLIC_FRONT_Z - 5.6);
    player.floor = 0;
    const dx = target.x - player.position.x;
    const dz = target.z - player.position.z;
    player.yaw = Math.atan2(-dx, -dz);
    player.pitch = -0.08;
    updateCamera();
    return this.homeWorldActivityStatus();
  },
  focusStarbucksInterior(offset = {}) {
    setStarbucksDoorOpen(true);
    const target = new THREE.Vector3(STARBUCKS_COUNTER_SPOT.x, 1.25, STARBUCKS_COUNTER_SPOT.z);
    player.position.set(offset.x ?? STARBUCKS_SEAT_SPOT.x - 2.1, offset.y ?? 1.45, offset.z ?? STARBUCKS_PUBLIC_FRONT_Z + 3.2);
    player.floor = 0;
    const dx = target.x - player.position.x;
    const dz = target.z - player.position.z;
    player.yaw = Math.atan2(-dx, -dz);
    player.pitch = -0.04;
    updateCamera();
    return this.homeWorldActivityStatus();
  },
  focusBasketballCourt(offset = {}) {
    if (HOME_WORLD_PRE_RAM_LIGHT_MODE) {
      show("Basketball court is disabled in pre-RAM light mode.");
      return this.homeWorldActivityStatus();
    }
    const target = new THREE.Vector3(PARK_BASKETBALL_CENTER.x, 1.5, PARK_BASKETBALL_CENTER.z);
    player.position.set(offset.x ?? PARK_BASKETBALL_CENTER.x - 7.2, offset.y ?? 1.75, offset.z ?? PARK_BASKETBALL_CENTER.z - 6.5);
    player.floor = 0;
    const dx = target.x - player.position.x;
    const dz = target.z - player.position.z;
    player.yaw = Math.atan2(-dx, -dz);
    player.pitch = -0.06;
    updateCamera();
    return this.homeWorldActivityStatus();
  },
  focusSchool(offset = {}) {
    const target = HOME_WORLD_PRE_RAM_LIGHT_MODE
      ? new THREE.Vector3(SCHOOL_CENTER.x, 1.25, SCHOOL_CENTER.z)
      : new THREE.Vector3(SCHOOL_DESK_SPOT.x, 1.25, SCHOOL_DESK_SPOT.z);
    player.position.set(offset.x ?? SCHOOL_ENTRY.x - 3.8, offset.y ?? 1.65, offset.z ?? SCHOOL_ENTRY.z - 4.6);
    player.floor = 0;
    const dx = target.x - player.position.x;
    const dz = target.z - player.position.z;
    player.yaw = Math.atan2(-dx, -dz);
    player.pitch = -0.05;
    updateCamera();
    return this.homeWorldActivityStatus();
  },
  focusKiraBungalow(offset = {}) {
    const target = new THREE.Vector3(KIRA_BUNGALOW_CENTER.x, 1.35, KIRA_BUNGALOW_FRONT_Z - 0.8);
    player.position.set(offset.x ?? KIRA_BUNGALOW_CENTER.x - 4.2, offset.y ?? 1.65, offset.z ?? KIRA_BUNGALOW_FRONT_Z + 5.2);
    player.floor = 0;
    const dx = target.x - player.position.x;
    const dz = target.z - player.position.z;
    player.yaw = Math.atan2(-dx, -dz);
    player.pitch = -0.08;
    updateCamera();
    return true;
  },
  focusDressShirtCloset(offset = {}) {
    const target = new THREE.Vector3(DRESS_SHIRT_CLOSET_POSITION.x, 1.25, DRESS_SHIRT_CLOSET_POSITION.z);
    player.position.set(offset.x ?? DRESS_SHIRT_CLOSET_POSITION.x + 2.35, offset.y ?? 1.45, offset.z ?? DRESS_SHIRT_CLOSET_POSITION.z - 0.2);
    player.floor = 0;
    const dx = target.x - player.position.x;
    const dz = target.z - player.position.z;
    player.yaw = Math.atan2(-dx, -dz);
    player.pitch = -0.04;
    updateCamera();
    return this.dressShirtState();
  },
  dressShirtState() {
    return {
      closet: prototypeCloset ? prototypeCloset.toJSON() : null,
      garment: prototypeDressShirt ? prototypeDressShirt.toJSON() : null,
      controller: avatarDressingController ? avatarDressingController.toJSON() : null,
    };
  },
  startDressShirtPrototype() {
    if (!prototypeCloset || !prototypeDressShirt || !avatarDressingController) return false;
    prototypeCloset.detachGarment(prototypeDressShirt);
    const started = avatarDressingController.startPutOn(prototypeDressShirt);
    syncPrototypeDressShirtPlacement(clock.elapsedTime);
    return started ? this.dressShirtState() : false;
  },
  reverseDressShirtPrototype(destination = "closet") {
    if (!prototypeDressShirt || !avatarDressingController) return false;
    if (!avatarDressingController.garment) avatarDressingController.garment = prototypeDressShirt;
    const started = avatarDressingController.startRemove(destination);
    syncPrototypeDressShirtPlacement(clock.elapsedTime);
    return started ? this.dressShirtState() : false;
  },
  buttonDressShirtPrototype() {
    if (!avatarDressingController) return false;
    return avatarDressingController.buttonShirt() ? this.dressShirtState() : false;
  },
  unbuttonDressShirtPrototype() {
    if (!avatarDressingController) return false;
    return avatarDressingController.unbuttonShirt() ? this.dressShirtState() : false;
  },
  dropDressShirtPrototype() {
    if (!avatarDressingController) return false;
    return avatarDressingController.dropHeldGarment() ? this.dressShirtState() : false;
  },
  sendDressShirtPrototypeToLaundry() {
    if (!avatarDressingController) return false;
    return avatarDressingController.sendToLaundry() ? this.dressShirtState() : false;
  },
  hangDressShirtPrototype() {
    if (!prototypeCloset || !prototypeDressShirt) return false;
    prototypeCloset.store(prototypeDressShirt);
    return this.dressShirtState();
  },
  startKiraEyeTest(seconds = 8.5) {
    return startKiraEyeMovementTest(seconds);
  },
  setKiraEyeDirection(direction = "center") {
    return setKiraEyeDirectionOverride(direction);
  },
  setKiraEyeBlink(side = "both", amount = 1) {
    return setKiraEyeBlinkOverride(side, amount);
  },
  clearKiraEyeOverride() {
    return clearKiraEyeOverrides();
  },
  probeKiraEyeBinding() {
    return kiraEyeBindingProbe();
  },
  focusKiraEyes(offset = {}) {
    return focusStagedKiraEyes(offset);
  },
  startKiraArmMobilityTest(seconds = 10) {
    return startActiveAvatarKiraArmMobilityTest(seconds);
  },
  startKiraDoctorBodyControlExam(options = {}) {
    return startKiraDoctorBodyControlExam(options);
  },
  probeKiraDoctorJointControl() {
    return probeKiraDoctorJointControl();
  },
  kiraDoctorBodyControlStatus() {
    return activeMarker?.userData?.doctorBodyExam || {
      running: false,
      version: KIRA_DOCTOR_BODY_EXAM_VERSION,
      structural: buildKiraDoctorStructuralReport(kiraDoctorRigContext()),
      results: [],
    };
  },
  kiraComfortIdleStatus() {
    return kiraComfortIdleStatus();
  },
  startLieOnCurrentGround(options = {}) {
    return startActiveAvatarGroundLieHold({ ...options, selfChosen: true });
  },
  startKiraSleepPractice() {
    return startActiveAvatarKiraSleepPractice();
  },
  kiraEyeStatus() {
    return kiraEyeBindingProbe();
  },
  focusSky(offset = {}) {
    const fallbackTarget = new THREE.Vector3(3, 34, -44);
    const visibleSkyRoot = homeWorldSkyMode === "night" ? homeWorldMoonRoot : homeWorldSunRoot;
    const target = visibleSkyRoot?.position || homeWorldSunRoot?.position || homeWorldMoonRoot?.position || fallbackTarget;
    player.position.set(offset.x ?? 0, offset.y ?? 1.65, offset.z ?? -90);
    player.floor = 0;
    const dx = target.x - player.position.x;
    const dz = target.z - player.position.z;
    const dy = target.y - player.position.y;
    const horizontal = Math.max(0.001, Math.hypot(dx, dz));
    player.yaw = Math.atan2(-dx, -dz);
    player.pitch = offset.pitch ?? Math.atan2(dy, horizontal);
    updateCamera();
    return this.homeWorldActivityStatus();
  },
  setSkyMode(mode = "day") {
    return setHomeWorldSkyMode(mode);
  },
  startCafeCoffeePractice() {
    return startActiveAvatarCafeCoffeePractice();
  },
  startCafeCoffeeHoldAtCounter() {
    if (!activeMarker) return false;
    setStarbucksDoorOpen(true);
    return startActiveAvatarHoldSkill({
      id: "drink_coffee_debug",
      label: "Starbucks cafe counter coffee",
      action: "drink_coffee",
      truthAction: "drink_coffee",
      seconds: 5.2,
      position: STARBUCKS_COUNTER_SPOT.clone(),
      yaw: Math.PI,
      postureState: {
        id: "drink_coffee_debug",
        posture: "stand_drink",
        rootTiltX: 0.02,
        rootYOffset: 0,
      },
      heldPropKind: "coffee_cup",
    });
  },
  startBasketballPractice() {
    return startActiveAvatarBasketballPractice();
  },
  startBasketballBenchSitStand() {
    return startActiveAvatarBasketballBenchSitStand();
  },
  startSchoolStudyPractice() {
    return startActiveAvatarSchoolStudyPractice();
  },
  startSchoolStudyHoldAtDesk() {
    if (!activeMarker) return false;
    if (HOME_WORLD_PRE_RAM_LIGHT_MODE) {
      return startActiveAvatarHoldSkill({
        id: "attend_school_empty_room_debug",
        label: "empty school learning room",
        action: "study",
        truthAction: "attend_school",
        seconds: 5.2,
        position: SCHOOL_CENTER.clone(),
        yaw: Math.PI,
      });
    }
    return startActiveAvatarHoldSkill({
      id: "attend_school_debug",
      label: "Kira school lesson desk",
      action: "study",
      truthAction: "attend_school",
      seconds: 5.2,
      position: SCHOOL_SEAT_SPOT.clone(),
      yaw: 0,
      postureState: {
        id: "attend_school_debug",
        posture: "sit",
        rootTiltX: 0.06,
        rootYOffset: -0.42,
      },
      heldPropKind: "notebook",
    });
  },
  startBasketballHoldAtCourt() {
    if (!activeMarker) return false;
    if (HOME_WORLD_PRE_RAM_LIGHT_MODE) {
      show("Basketball court is disabled in pre-RAM light mode.");
      return false;
    }
    basketballBounceUntil = clock.elapsedTime + 8.0;
    return startActiveAvatarHoldSkill({
      id: "play_basketball_debug",
      label: "future park basketball dribble spot",
      action: "dribble_basketball",
      truthAction: "play_basketball",
      seconds: 6.4,
      position: BASKETBALL_DRIBBLE_SPOT.clone(),
      yaw: Math.PI / 2,
      postureState: {
        id: "play_basketball_debug",
        posture: "athletic_ready",
        rootTiltX: 0.08,
        rootYOffset: -0.06,
      },
      heldPropKind: "basketball",
    });
  },
  activeAvatarModelNodeNames(filter = "") {
    if (!activeAvatarRoot) return [];
    const needle = String(filter || "").toLowerCase();
    const names = [];
    activeAvatarRoot.traverse((node) => {
      const name = String(node.name || "");
      if (!name) return;
      if (needle && !name.toLowerCase().includes(needle)) return;
      names.push(name);
    });
    return names.slice(0, 250);
  },
  activeAvatarVisualBounds() {
    if (!activeMarker || !activeAvatarRoot) return null;
    activeMarker.updateMatrixWorld(true);
    const bounds = meshOnlyWorldBounds(activeAvatarRoot) || new THREE.Box3().setFromObject(activeAvatarRoot, true);
    if (bounds.isEmpty()) return null;
    const size = bounds.getSize(new THREE.Vector3());
    const support = activeAvatarSupportAt(activeMarker.position);
    const number = (value) => Number(value.toFixed(6));
    return {
      min: { x: number(bounds.min.x), y: number(bounds.min.y), z: number(bounds.min.z) },
      max: { x: number(bounds.max.x), y: number(bounds.max.y), z: number(bounds.max.z) },
      size: { x: number(size.x), y: number(size.y), z: number(size.z) },
      supportY: Number.isFinite(support?.y) ? number(support.y) : null,
      minimumToSupportGap: Number.isFinite(support?.y) ? number(bounds.min.y - support.y) : null,
      markerPosition: {
        x: number(activeMarker.position.x),
        y: number(activeMarker.position.y),
        z: number(activeMarker.position.z),
      },
      rootPositionY: number(activeAvatarRoot.position.y),
      rootRotationX: number(activeAvatarRoot.rotation.x),
      postureState: activeMarker.userData?.postureState || null,
      note: "World-space mesh bounds diagnostic; this is contact evidence, not visual-naturalness approval.",
    };
  },
  setActiveAvatarPosition(position = {}) {
    if (!activeMarker) return false;
    activeMarker.position.set(
      position.x ?? activeMarker.position.x,
      position.y ?? activeMarker.position.y,
      position.z ?? activeMarker.position.z,
    );
    activePostureInteraction = null;
    activeDoorInteraction = null;
    activeFurnitureInteraction = null;
    activeSkillInteraction = null;
    clearDoorReachRig();
    activeMarker.userData.postureState = null;
    activeMarker.userData.doorInteraction = null;
    activeMarker.userData.furnitureInteraction = null;
    activeMarker.userData.skillInteraction = null;
    activeMarker.userData.gaitMode = null;
    if (!position.keepPracticeRoute) {
      activeMarker.userData.practiceRoute = null;
      activeMarker.userData.stairTraversalActive = false;
    }
    clearActiveAvatarAutonomousRoamTarget("debug_position_set");
    activeMarker.userData.roamReady = true;
    activeMarker.userData.waitUntil = Number.isFinite(position.waitSeconds) ? clock.elapsedTime + position.waitSeconds : 0;
    activeMarker.userData.stuckSince = null;
    activeMarker.userData.lastDistanceToTarget = null;
    activeMarker.userData.lastMoveT = clock.elapsedTime;
    if (position.roamZone) activeMarker.userData.roamZone = position.roamZone;
    if (Number.isFinite(position.roamIndex)) activeMarker.userData.roamIndex = position.roamIndex;
    setActiveAvatarAction("idle");
    applyActiveAvatarSupport(0.016);
    return true;
  },
  startFrontDoorReach() {
    if (!activeMarker) return false;
    return startActiveAvatarDoorInteraction(frontDoorInteractionSpec(activeMarker.position.y, activeMarker.position.x, activeMarker.position.z, "front_door_debug"));
  },
  startBackDoorReach() {
    if (!activeMarker) return false;
    return startActiveAvatarDoorInteraction(backDoorInteractionSpec(activeMarker.position.y, activeMarker.position.z, "back_door_debug"));
  },
  startPostureTest(name) {
    return startActiveAvatarPostureTest(name);
  },
  startJogPractice() {
    return startActiveAvatarJogPractice();
  },
  startWalkPractice() {
    return startActiveAvatarWalkPractice();
  },
  startRunPractice() {
    return startActiveAvatarRunPractice();
  },
  startSwimPractice() {
    return startActiveAvatarSwimPractice();
  },
  startLibraryReadPractice() {
    return startActiveAvatarLibraryReadPractice();
  },
  startDuckPractice() {
    return startActiveAvatarDuckPractice();
  },
  startDodgePractice() {
    return startActiveAvatarDodgePractice();
  },
  startJumpPractice() {
    return startActiveAvatarJumpPractice();
  },
  startCaptureFlagGamePractice() {
    return startActiveAvatarCaptureFlagGamePractice();
  },
  activeLimbDiagnostics() {
    return activeAvatarProceduralRigDiagnostics();
  },
  visibleDownstairsToiletCount() {
    let count = 0;
    scene.traverse((node) => {
      if (!node.visible) return;
      const name = String(node.name || "").toLowerCase();
      const world = node.getWorldPosition(new THREE.Vector3());
      const downstairsToiletByName = name.includes("toilet") && world.y < ACTIVE_AVATAR_SECOND_FLOOR_Y - 0.35;
      const inForbiddenZone = DOWNSTAIRS_TOILET_FORBIDDEN_ZONES.some((zone) => pointInsideRectZone(zone, world));
      if (downstairsToiletByName || suppressedDownstairsBathroomReason(node, world) || (inForbiddenZone && nodeLooksLikeLooseBathroomFixture(node))) count += 1;
    });
    return count;
  },
  downstairsToiletDebugSnapshot() {
    return downstairsToiletDebugSnapshot();
  },
  scrubDownstairsToilets() {
    removeSuppressedDownstairsToiletObjects();
    return this.downstairsToiletDebugSnapshot();
  },
  realisticBookshelfStatus() {
    return {
      ...realisticBookshelfStatus,
      visible: !!realisticHomeBookshelf?.visible,
    };
  },
  neighborHouseStatus() {
    return {
      ...neighborHouseReferenceStatus,
      doorInitialized: !!neighborDoorStatus.initialized,
      doorOpen: !!neighborHouseDoorOpen,
      doorPosition: neighborDoorStatus.position,
      importedDoorVisible: !!neighborEntryDoorReference?.visible,
      workingDoorVisible: !!neighborHouseDoorLeaf?.visible,
      fallbackDoorVisible: !!neighborFallbackDoorGroup?.visible,
    };
  },
  setNeighborHouseDoorOpen(open = true) {
    setNeighborHouseDoorOpen(open);
    return this.neighborHouseStatus();
  },
  focusNeighborHouse(options = {}) {
    if (!neighborDoorStatus.initialized) return false;
    if (options.openDoor !== undefined) setNeighborHouseDoorOpen(!!options.openDoor);
    const target = new THREE.Vector3(options.targetX ?? 30.2, options.targetY ?? 1.35, options.targetZ ?? 4.5);
    const eye = new THREE.Vector3(options.eyeX ?? 21.2, options.eyeY ?? 1.55, options.eyeZ ?? 13.0);
    player.position.copy(eye);
    player.floor = 0;
    const dx = target.x - eye.x;
    const dz = target.z - eye.z;
    player.yaw = Math.atan2(-dx, -dz);
    player.pitch = -0.08;
    updateCamera();
    return this.neighborHouseStatus();
  },
  focusNeighborLot(options = {}) {
    const target = new THREE.Vector3(options.targetX ?? 30.2, options.targetY ?? 1.25, options.targetZ ?? 3.2);
    const eye = new THREE.Vector3(options.eyeX ?? 19.8, options.eyeY ?? 1.6, options.eyeZ ?? 14.5);
    player.position.copy(eye);
    player.floor = 0;
    const dx = target.x - eye.x;
    const dz = target.z - eye.z;
    player.yaw = Math.atan2(-dx, -dz);
    player.pitch = -0.06;
    updateCamera();
    return this.neighborHouseStatus();
  },
  neighborHouseWalkInProbe() {
    if (!neighborDoorStatus.initialized) return { ok: false, reason: "neighbor door is not initialized" };
    const priorDoorOpen = neighborHouseDoorOpen;
    const priorFloor = player.floor;
    setNeighborHouseDoorOpen(true);
    player.floor = 0;
    const x = neighborDoorStatus.position.x;
    const z = neighborDoorStatus.position.z;
    const probes = [
      { name: "porch", x, z: z + 0.62 },
      { name: "threshold", x, z },
      { name: "foyer", x, z: z - 1.15 },
      { name: "living_room_clearance", x: x - 1.45, z: z - 2.45 },
    ].map((probe) => ({
      ...probe,
      blocked: isBlocked(probe.x, probe.z),
    }));
    player.floor = priorFloor;
    setNeighborHouseDoorOpen(priorDoorOpen);
    return {
      ok: probes.every((probe) => !probe.blocked),
      doorOpenedForProbe: true,
      probes,
    };
  },
  clearAutonomousRoamTarget() {
    clearActiveAvatarAutonomousRoamTarget("manual_debug_clear");
    return window.__kiraHomeWorldRuntime?.autonomousRoam || null;
  },
  startLimbSmokeSequence() {
    const queue = ["jog", "run", "dodge", "duck", "jump"];
    let delay = 0;
    for (const skill of queue) {
      window.setTimeout(() => window.kiraBodyPractice.startSkill(skill), delay);
      delay += skill === "dodge" ? 2400 : 3600;
    }
    return {
      queued: queue,
      diagnostics: activeAvatarProceduralRigDiagnostics(),
    };
  },
  setObserveFollow(enabled = true) {
    return setObserveFollow(enabled);
  },
  toggleObserveFollow() {
    return setObserveFollow(!observeFollowEnabled);
  },
  observationSample(reason = "debug_observation_sample") {
    return observationSample(reason);
  },
  embodimentEvidenceSnapshot(reason = "staged_embodiment_check") {
    const place = activeAvatarNamedPlaceSnapshot();
    return {
      reason,
      activeModelLoaded: !!activeAvatarRoot,
      bodyPresent: !!activeMarker,
      action: activeAvatarAction,
      activePosition: activeMarker ? {
        x: Number(activeMarker.position.x.toFixed(3)),
        y: Number(activeMarker.position.y.toFixed(3)),
        z: Number(activeMarker.position.z.toFixed(3)),
      } : null,
      place,
      affordances: activeAvatarAffordanceSnapshot(place),
      activeHeldProp: activeHeldPropEvidenceSnapshot(),
      postureState: activeMarker?.userData?.postureState || null,
      supportState: activeMarker?.userData?.supportState || null,
      transitionEvidence: activeMarker?.userData?.transitionEvidence || null,
      lastEmbodimentCapabilityBlock: activeMarker?.userData?.lastEmbodimentCapabilityBlock || null,
      fingerContacts: activeMarker?.userData?.fingerContacts || [],
      activityTruthByAction: {
        read_book: activityTruthForAction("read_book"),
        project_work: activityTruthForAction("project_work"),
        creative_write: activityTruthForAction("creative_write"),
        take_notes: activityTruthForAction("take_notes"),
        use_phone: activityTruthForAction("use_phone"),
        drink: activityTruthForAction("drink"),
        drink_coffee: activityTruthForAction("drink_coffee"),
        eat_food: activityTruthForAction("eat_food"),
      },
      anatomyAnimationSupported: false,
      privacyState: null,
      mindBodyTruth: activeMindBodyTruthSnapshot(reason, activeShellState?.active_action || activeAvatarAction),
      visualGroundContact: activeMarker?.userData?.visualGroundContact || null,
    };
  },
  startObservationReport(options = {}) {
    return startObservationReport(options);
  },
  stopObservationReport() {
    return stopObservationReport();
  },
  observationReportState() {
    return {
      ...observationReportState,
      samples: observationReportState.samples.slice(-10),
    };
  },
  enterCaptureFlagWorld() {
    travelToCaptureFlagWorld("player");
    return this.playerState();
  },
  returnFromCaptureFlagWorld() {
    returnToHomeWorldFromCaptureFlag();
    return this.playerState();
  },
  captureFlagState() {
    return {
      ...captureFlagState,
      bestSeconds: captureFlagState.bestSeconds === null ? null : Number(captureFlagState.bestSeconds.toFixed(2)),
      flagPosition: captureFlagFlagGroup?.visible ? {
        x: Number(captureFlagFlagGroup.position.x.toFixed(3)),
        y: Number(captureFlagFlagGroup.position.y.toFixed(3)),
        z: Number(captureFlagFlagGroup.position.z.toFixed(3)),
      } : null,
      npcPositions: captureFlagNpcs.map((npc) => ({
        name: npc.name,
        type: npc.type,
        x: Number(npc.group.position.x.toFixed(3)),
        z: Number(npc.group.position.z.toFixed(3)),
        alert: !!npc.group.userData.alert,
        modelAttached: !!npc.modelAttached,
        modelSuppressedReason: npc.modelSuppressedReason || null,
      })),
    };
  },
  stepActiveAvatarForTest(seconds = 1.0, steps = 30) {
    if (!activeMarker) return null;
    const safeSteps = Math.max(1, Math.min(900, Math.floor(steps || 30)));
    const dt = Math.max(0.01, Math.min(0.08, Number(seconds || 1) / safeSteps));
    let t = clock.elapsedTime;
    let colliderPenetrationSamples = 0;
    let obstructedActiveRouteSamples = 0;
    let routeLanguagePromotedToPlaceSamples = 0;
    const positionSamples = [];
    for (let i = 0; i < safeSteps; i += 1) {
      t += dt;
      updateActiveAvatarMovement(t);
      updateActiveAvatarLocomotionTransition(dt);
      updateCaptureFlagWorld(t, dt);
      const target = activeMarker.userData?.autonomousRoamTarget || null;
      const place = activeAvatarNamedPlaceSnapshot();
      if (isAvatarBlocked(activeMarker.position.x, activeMarker.position.z, activeMarker.position.y, 0.42)) {
        colliderPenetrationSamples += 1;
      }
      if (target && !activeAvatarDirectPathIsClear(activeMarker.position, new THREE.Vector3(target.x, target.y, target.z), 0.46)) {
        obstructedActiveRouteSamples += 1;
      }
      if (/route\s+toward|moving\s+or\s+waiting\s+near\s+the\s+route/i.test(String(place?.summary || ""))) {
        routeLanguagePromotedToPlaceSamples += 1;
      }
      if (i === 0 || i === safeSteps - 1 || i % Math.max(1, Math.floor(safeSteps / 12)) === 0) {
        positionSamples.push({
          step: i + 1,
          x: Number(activeMarker.position.x.toFixed(3)),
          y: Number(activeMarker.position.y.toFixed(3)),
          z: Number(activeMarker.position.z.toFixed(3)),
          target: target?.id || null,
          place: place?.summary || null,
        });
      }
    }
    updateActiveAvatarProceduralRig(t);
    applyActiveAvatarFootContactLocks();
    applyActiveAvatarVisualGroundContactCalibration(t, true);
    updateActiveHeldProp(t);
    return {
      state: this.activeAvatarState(),
      ctf: this.captureFlagState(),
      diagnostics: activeAvatarProceduralRigDiagnostics(),
      skill: activeSkillInteraction ? {
        id: activeSkillInteraction.id,
        kind: activeSkillInteraction.kind,
        action: activeSkillInteraction.action,
        phase: activeSkillInteraction.phase || null,
        index: activeSkillInteraction.index ?? null,
        didDodge: !!activeSkillInteraction.didDodge,
      } : null,
      motionSafety: {
        simulatedSeconds: Number((safeSteps * dt).toFixed(3)),
        samples: safeSteps,
        colliderPenetrationSamples,
        obstructedActiveRouteSamples,
        routeLanguagePromotedToPlaceSamples,
        collisionReplans: Number(activeMarker.userData?.autonomousCollisionReplans || 0),
        currentPlace: activeAvatarNamedPlaceSnapshot(),
        currentTarget: activeMarker.userData?.autonomousRoamTarget || null,
        armMotionEvidence: activeMarker.userData?.armMotionEvidence || null,
        visualGroundContact: activeMarker.userData?.visualGroundContact || null,
        positionSamples,
      },
    };
  },
  startDeskComputerSequence() {
    return startActiveAvatarDeskComputerSequence();
  },
  startStairPractice() {
    return startActiveAvatarStairPracticeRoute(false);
  },
  toggleKitchenFridge() {
    setKitchenFridgeOpen(!kitchenFridgeDoorOpen);
    return kitchenFridgeDoorOpen;
  },
  callTardis() {
    return callHomeTardisToUser();
  },
  callTardisForActiveAvatar() {
    return callHomeTardisToActiveAvatar();
  },
  enterTardis() {
    return tryEnterHomeTardis();
  },
  startActiveAvatarTardisEntryPractice() {
    return startActiveAvatarTardisEntryPractice();
  },
  startSoftGoodsPractice(kind = "robe") {
    return startActiveAvatarSoftGoodsDraftPractice(kind);
  },
  setLibraryDoorOpen(open = true) {
    setLibraryDoorOpen(open);
    return libraryDoorOpen;
  },
  activityTruth(action = activeAvatarAction) {
    return activityTruthForAction(action);
  },
  currentPlace() {
    return activeAvatarNamedPlaceSnapshot();
  },
  truthProps() {
    return activityTruthProps.map((prop) => truthPropSnapshot(prop)).filter(Boolean);
  },
  sceneObjectNames(pattern = "") {
    const needle = String(pattern).toLowerCase();
    const names = [];
    scene.traverse((obj) => {
      if (!obj.name) return;
      if (!needle || obj.name.toLowerCase().includes(needle)) names.push(obj.name);
    });
    return names;
  },
  sceneObjectSummaries(pattern = "") {
    const needle = String(pattern).toLowerCase();
    const items = [];
    const position = new THREE.Vector3();
    scene.traverse((obj) => {
      if (!obj.name) return;
      if (needle && !obj.name.toLowerCase().includes(needle)) return;
      obj.getWorldPosition(position);
      items.push({
        name: obj.name,
        visible: obj.visible,
        x: Number(position.x.toFixed(3)),
        y: Number(position.y.toFixed(3)),
        z: Number(position.z.toFixed(3)),
      });
    });
    return items;
  },
  setPlayerPosition(position = {}) {
    playerStairTraversalActive = false;
    playerStairTraversalDirection = null;
    player.position.set(
      position.x ?? player.position.x,
      position.y ?? player.position.y,
      position.z ?? player.position.z,
    );
    if (Number.isFinite(position.floor)) player.floor = position.floor;
    if (Number.isFinite(position.yaw)) player.yaw = position.yaw;
    if (Number.isFinite(position.pitch)) player.pitch = position.pitch;
    updateCamera();
    return this.playerState();
  },
  playerState() {
    return {
      x: Number(player.position.x.toFixed(3)),
      y: Number(player.position.y.toFixed(3)),
      z: Number(player.position.z.toFixed(3)),
      floor: player.floor,
    };
  },
  interactHere() {
    interact();
    return this.playerState();
  },
};

window.kiraBodyPractice = {
  skills: [
    "self_test",
    "door_reach",
    "back_door_reach",
    "library_door_reach",
    "stairs_step",
    "sit_couch",
    "lie_grass",
    "lie_bed",
    "sleep_bed",
    "arm_control",
    "doctor_body_exam",
    "lie_ground",
    "sit_bench",
    "desk_computer",
    "walk",
    "jog",
    "run",
    "swim_pool",
    "read_library",
    "get_coffee",
    "play_basketball",
    "attend_school",
    "dress_shirt",
    "duck",
    "dodge",
    "jump",
    "capture_flag_game",
    "call_tardis",
    "enter_tardis",
    "call_enter_tardis",
    "put_on_robe",
    "use_towel",
  ],
  startSkill(name) {
    if (name === "self_test") return startActiveAvatarSelfTest({ auto: false });
    if (name === "door_reach") return window.kiraHomeWorldDebug.startFrontDoorReach();
    if (name === "back_door_reach") return window.kiraHomeWorldDebug.startBackDoorReach();
    if (name === "library_door_reach") return startActiveAvatarDoorInteraction(libraryDoorInteractionSpec(activeMarker?.position.y || ACTIVE_AVATAR_GROUND_Y, 38.42, "library_door_debug"));
    if (name === "desk_computer") return window.kiraHomeWorldDebug.startDeskComputerSequence();
    if (name === "stairs_step") return window.kiraHomeWorldDebug.startStairPractice();
    if (name === "doctor_body_exam" || name === "doctor_exam" || name === "body_control_exam") return window.kiraHomeWorldDebug.startKiraDoctorBodyControlExam();
    if (name === "lie_ground" || name === "lie_on_ground" || name === "look_at_sky") return window.kiraHomeWorldDebug.startLieOnCurrentGround();
    if (name === "walk") return window.kiraHomeWorldDebug.startWalkPractice();
    if (name === "jog") return window.kiraHomeWorldDebug.startJogPractice();
    if (name === "run") return window.kiraHomeWorldDebug.startRunPractice();
    if (name === "swim_pool" || name === "swim") return window.kiraHomeWorldDebug.startSwimPractice();
    if (name === "read_library" || name === "read_book") return window.kiraHomeWorldDebug.startLibraryReadPractice();
    if (name === "get_coffee" || name === "drink_coffee" || name === "starbucks") return window.kiraHomeWorldDebug.startCafeCoffeePractice();
    if (name === "play_basketball" || name === "basketball") return window.kiraHomeWorldDebug.startBasketballPractice();
    if (name === "sit_bench" || name === "bench_sit") return window.kiraHomeWorldDebug.startBasketballBenchSitStand();
    if (name === "arm_control" || name === "arms" || name === "hand_control") return window.kiraHomeWorldDebug.startKiraArmMobilityTest();
    if (name === "attend_school" || name === "school" || name === "classroom" || name === "study") return window.kiraHomeWorldDebug.startSchoolStudyPractice();
    if (name === "dress_shirt" || name === "change_clothes" || name === "put_on_shirt") return window.kiraHomeWorldDebug.startDressShirtPrototype();
    if (name === "duck") return window.kiraHomeWorldDebug.startDuckPractice();
    if (name === "dodge") return window.kiraHomeWorldDebug.startDodgePractice();
    if (name === "jump") return window.kiraHomeWorldDebug.startJumpPractice();
    if (name === "capture_flag_game" || name === "play_capture_flag") return window.kiraHomeWorldDebug.startCaptureFlagGamePractice();
    if (name === "call_tardis") return window.kiraHomeWorldDebug.callTardisForActiveAvatar();
    if (name === "enter_tardis" || name === "call_enter_tardis" || name === "use_tardis") return window.kiraHomeWorldDebug.startActiveAvatarTardisEntryPractice();
    if (name === "put_on_robe" || name === "robe" || name === "wear_robe") return window.kiraHomeWorldDebug.startSoftGoodsPractice("robe");
    if (name === "use_towel" || name === "towel" || name === "wrap_towel") return window.kiraHomeWorldDebug.startSoftGoodsPractice("towel");
    return startActiveAvatarPostureTest(name);
  },
  startCoreSkillSequence() {
    const queue = ["jog", "run", "duck", "jump", "swim_pool", "read_library"];
    let delay = 0;
    for (const skill of queue) {
      window.setTimeout(() => this.startSkill(skill), delay);
      delay += skill === "swim_pool" ? 8200 : skill === "read_library" ? 9000 : 4200;
    }
    return true;
  },
  startSequence(queue = ["jog", "run", "dodge", "duck", "jump", "swim_pool", "read_library"]) {
    const skills = Array.isArray(queue) && queue.length ? queue : ["jog", "run", "dodge", "duck", "jump"];
    let delay = 0;
    for (const skill of skills) {
      window.setTimeout(() => this.startSkill(skill), delay);
      delay += skill === "swim_pool" ? 8200 : skill === "read_library" ? 9000 : skill === "dodge" ? 2600 : 3800;
    }
    return {
      queued: skills,
      diagnostics: window.kiraHomeWorldDebug.activeLimbDiagnostics(),
    };
  },
};

window.kiraSyntheticBodyActions = Object.freeze({
  actions: Object.freeze(["raise_hand", "sit_on_couch", "lie_on_couch", "lie_on_bed", "lie_on_ground", "sleep", "rest", "push_up"]),
  choose(intent, options = {}) {
    return startActiveAvatarVoluntaryBodyIntent(intent, {
      ...options,
      source: "subject_runtime_intent",
    });
  },
});

function move(dt) {
  if (observeFollowEnabled) {
    updateObserveFollowCamera();
    return;
  }
  const inPool = isInBackyardPool(player.position.x, player.position.z);
  const speed = (keys.has("ShiftLeft") || keys.has("ShiftRight") ? 5.2 : 2.5) * (inPool ? 0.55 : 1) * dt;
  let forward = 0;
  let strafe = 0;
  if (keys.has("KeyW")) forward += 1;
  if (keys.has("KeyS")) forward -= 1;
  if (keys.has("KeyA")) strafe -= 1;
  if (keys.has("KeyD")) strafe += 1;
  if (!forward && !strafe) {
    updateStairTraversal();
    return;
  }
  const dir = new THREE.Vector3(strafe, 0, -forward).normalize().applyAxisAngle(new THREE.Vector3(0, 1, 0), player.yaw);
  const nextX = player.position.x + dir.x * speed;
  const nextZ = player.position.z + dir.z * speed;
  if (!isBlocked(nextX, player.position.z)) player.position.x = nextX;
  if (!isBlocked(player.position.x, nextZ)) player.position.z = nextZ;
  updateStairTraversal();
}

function isInBackyardPool(x, z) {
  return x > backyardPoolBounds.xMin && x < backyardPoolBounds.xMax && z > backyardPoolBounds.zMin && z < backyardPoolBounds.zMax;
}

function setPlayerDefaultFloorHeight() {
  if (!player.floor && isInBackyardPool(player.position.x, player.position.z)) {
    player.position.y = 0.95 + Math.sin(clock.elapsedTime * 2.4) * 0.065;
  } else {
    player.position.y = player.floor ? 4.85 : 1.65;
  }
}

function updateStairTraversal() {
  if (!MAIN_TWO_STORY_HOUSE_ENABLED) {
    playerStairTraversalActive = false;
    playerStairTraversalDirection = null;
    if (player.floor !== 0) player.floor = 0;
    setPlayerDefaultFloorHeight();
    return;
  }
  const onStairFootprint = player.position.x > 0.85
    && player.position.x < 2.95
    && player.position.z < ACTIVE_AVATAR_STAIR_BOTTOM_Z + 0.18
    && player.position.z > ACTIVE_AVATAR_STAIR_TOP_Z - 0.42;
  if (!onStairFootprint) {
    playerStairTraversalActive = false;
    playerStairTraversalDirection = null;
    setPlayerDefaultFloorHeight();
    return;
  }

  const enteringFromBottom = player.floor === 0 && player.position.z >= ACTIVE_AVATAR_STAIR_BOTTOM_Z - 0.46;
  const enteringFromTop = player.floor === 1 && player.position.z <= ACTIVE_AVATAR_STAIR_TOP_Z + 0.5;
  if (!playerStairTraversalActive && !enteringFromBottom && !enteringFromTop) {
    setPlayerDefaultFloorHeight();
    return;
  }
  if (!playerStairTraversalActive) {
    playerStairTraversalActive = true;
    playerStairTraversalDirection = enteringFromBottom ? "up" : "down";
  }

  const t = THREE.MathUtils.clamp(
    (ACTIVE_AVATAR_STAIR_BOTTOM_Z - player.position.z) / (ACTIVE_AVATAR_STAIR_BOTTOM_Z - ACTIVE_AVATAR_STAIR_TOP_Z),
    0,
    1,
  );
  if ((playerStairTraversalDirection === "down" && player.floor === 0 && t > 0.42)
    || (playerStairTraversalDirection === "up" && player.floor === 1 && t < 0.58)) {
    playerStairTraversalActive = false;
    playerStairTraversalDirection = null;
    setPlayerDefaultFloorHeight();
    return;
  }
  player.position.y = THREE.MathUtils.lerp(1.65, 4.85, t);

  if (t >= 0.96 || player.position.z <= ACTIVE_AVATAR_STAIR_TOP_Z + 0.08) {
    player.floor = 1;
    player.position.y = 4.85;
  } else if (t <= 0.04 || player.position.z >= ACTIVE_AVATAR_STAIR_BOTTOM_Z - 0.08) {
    player.floor = 0;
    player.position.y = 1.65;
  } else if (player.floor === 0 && t > 0.64) {
    player.floor = 1;
  } else if (player.floor === 1 && t < 0.36) {
    player.floor = 0;
  }
}

function interact() {
  if (tryEnterHomeTardis()) return;
  for (const zone of interactZones) {
    if (zone.floor !== undefined && zone.floor !== null && zone.floor !== player.floor) continue;
    const d = Math.hypot(player.position.x - zone.x, player.position.z - zone.z);
    if (d <= zone.radius) {
      zone.action();
      return;
    }
  }
  show("Nothing to use here yet. Press B to review the home blueprint.");
}

function animate() {
  const dt = Math.min(clock.getDelta(), 0.05);
  move(dt);
  updateStairTraversal();
  updateImportedHouseReferenceVisibility();
  if (backyardPoolWater) {
    const t = clock.elapsedTime;
    backyardPoolWater.position.y = backyardPoolWater.userData.baseY + Math.sin(t * 1.7) * 0.018;
    backyardPoolWater.rotation.set(0, 0, 0);
  }
  if (backyardPoolSplash?.visible) {
    const age = clock.elapsedTime - (backyardPoolSplash.userData.startedAt || 0);
    backyardPoolSplash.scale.setScalar(1 + Math.min(age, 1.2) * 0.55);
    backyardPoolSplash.position.y = 0.25 + Math.sin(age * Math.PI) * 0.22;
    if (age > 1.6) backyardPoolSplash.visible = false;
  }
  const matchedVoicePlaying = voicePlaybackMatchesActiveAvatar();
  if (activeVoiceExpressionOwnsTalkingAction && activeAvatarAction !== "talking") {
    activeVoiceExpressionOwnsTalkingAction = false;
    activeVoiceExpressionReleaseAt = -Infinity;
  }
  if (activeVoiceExpressionOwnsTalkingAction
    && activeAvatarAction === "talking"
    && !matchedVoicePlaying
    && clock.elapsedTime >= activeVoiceExpressionReleaseAt) {
    activeVoiceExpressionOwnsTalkingAction = false;
    activeVoiceExpressionReleaseAt = -Infinity;
    setActiveAvatarAction("idle");
  } else if ((activeAvatarAction === "talking" || activeAvatarAction === "wave")
    && !matchedVoicePlaying
    && !activeVoiceExpressionOwnsTalkingAction
    && clock.elapsedTime - activeAvatarActionStarted > 10) {
    setActiveAvatarAction("idle");
  }
  updateActiveAvatarMovement(clock.elapsedTime);
  updateActiveOrbFallback(clock.elapsedTime);
  updateGroupPresenceOrbs(clock.elapsedTime);
  updateActiveAvatarLocomotionTransition(dt);
  updateCaptureFlagWorld(clock.elapsedTime, dt);
  if (observeFollowEnabled) updateObserveFollowCamera();
  else updateCamera();
  syncActiveWalkClipTiming();
  const walkPhaseSynced = syncActiveWalkClipPhase();
  if (activeAvatarMixer) {
    activeAvatarMixer.update(dt);
    if (walkPhaseSynced) {
      syncActiveWalkClipPhase();
      activeAvatarMixer.update(0);
    }
  }
  if (activeAvatarRoot) {
    const t = clock.elapsedTime;
    const baseY = activeAvatarRoot.userData.baseY ?? activeAvatarRoot.position.y;
    const locomotionBlend = THREE.MathUtils.clamp(Number(activeMarker?.userData?.locomotionBlend || 0), 0, 1);
    const moving = locomotionBlend > 0.012;
    const stepPhase = activeMarker?.userData?.walkCyclePhase ?? activeAvatarMovePhase;
    const postureState = activeMarker?.userData?.postureState;
    const visualGroundCorrectionY = Number(activeAvatarRoot.userData.visualGroundCorrectionY || 0);
    const syntheticVerticalBob = activeAvatarIsKiraLike()
      // A six-millimetre, distance-driven pelvis rise removes the old gliding
      // look while remaining inside the grounded-foot calibration tolerance.
      ? (moving ? Math.abs(Math.sin(stepPhase)) * 0.006 : Math.sin(t * 1.35) * 0.0015)
      : (moving ? Math.abs(Math.sin(stepPhase)) * 0.018 : Math.sin(t * 1.4) * 0.004);
    activeAvatarRoot.position.y = baseY + visualGroundCorrectionY + (postureState?.rootYOffset || 0) + syntheticVerticalBob;
    const forwardYawOffset = activeAvatarRoot.userData.forwardYawOffset || 0;
    if (!activeAvatarMixer) activeAvatarRoot.rotation.y = forwardYawOffset + (activeAvatarAction === "talking" ? Math.sin(t * 1.6) * 0.035 : 0);
    activeAvatarRoot.rotation.z = Math.sin(stepPhase) * (activeAvatarIsKiraLike() ? 0.016 : 0.01) * locomotionBlend;
    activeAvatarRoot.rotation.x = postureState ? postureState.rootTiltX : Math.sin(stepPhase * 2 + 0.65) * (activeAvatarIsKiraLike() ? 0.006 : 0.004) * locomotionBlend;
  }
  updateAvatarDressingController(clock.elapsedTime);
  if (activeAvatarUsesGenericProceduralRigForMarinette() || activeAvatarIsKiraLike()) {
    updateActiveAvatarProceduralRig(clock.elapsedTime);
    if (activeAvatarIsKiraLike()) applyActiveAvatarFootContactLocks();
    applyActiveDoorGripIK(clock.elapsedTime);
    updateActiveAvatarObjectFingerContacts();
  } else if (activeAvatarIsMarinetteLike()) {
    applyActiveAvatarRelaxedHands();
    applyActiveAvatarFootContactLocks();
    applyActiveDoorGripIK(clock.elapsedTime);
    updateActiveAvatarObjectFingerContacts();
  } else {
    updateActiveAvatarProceduralRig(clock.elapsedTime);
  }
  applyActiveAvatarVisualGroundContactCalibration(clock.elapsedTime);
  updateRuntimeMarinetteRig(clock.elapsedTime, !!activeMarker?.userData?.isMoving);
  updateKiraExistingMouthLipSync(clock.elapsedTime, dt);
  updateKiraEyeRig(clock.elapsedTime);
  updateKiraHairRig(clock.elapsedTime);
  updateActivePoseSprite(clock.elapsedTime);
  updateActiveHeldProp(clock.elapsedTime);
  updateHomeWorldActivityAnimations(clock.elapsedTime, dt);
  recordMindBodyTruthSnapshot(clock.elapsedTime);
  updateObservationReport(clock.elapsedTime);
  updateHomeWorldHudLocationTitle();
  window.__kiraHomeWorldRuntime = {
    activeLabel: activeMarker?.userData?.label || activeShellState?.active_label || null,
    activeForm: activeAvatarForm,
    activeAction: activeAvatarAction,
    activeShellClaim: activeShellState ? {
      action: activeShellState.active_action || null,
      location: activeShellState.location || null,
      model: activeShellState.model || null,
    } : null,
    activityTruth: activityTruthForAction(activeAvatarAction),
    activityTruthByAction: {
      read_book: activityTruthForAction("read_book"),
      use_phone: activityTruthForAction("use_phone"),
      drink_coffee: activityTruthForAction("drink_coffee"),
      attend_school: activityTruthForAction("attend_school"),
    },
    activeModelLoaded: !!activeAvatarRoot,
    activeMarkerKind: activeMarker?.userData?.kind || (activeAvatarRoot ? "loaded_model" : null),
    activeMarkerChildCount: activeMarker?.children?.length || 0,
    bodyLoadBlockedReason: activeMarker?.userData?.bodyLoadBlockedReason || null,
    proceduralRig: activeAvatarProceduralRig ? {
      id: activeAvatarProceduralRig.id,
      usable: !!activeAvatarProceduralRig.usable,
      hasWalkClip: !!activeAvatarProceduralRig.hasWalkClip,
      driving: !!activeMarker?.userData?.proceduralRigDriving,
      usingProceduralWalk: !!activeMarker?.userData?.usingProceduralWalk,
      gaitMode: activeMarker?.userData?.proceduralGaitMode || null,
      diagnostics: activeAvatarProceduralRigDiagnostics(),
    } : null,
    autonomousRoam: activeMarker ? {
      policy: activeMarker.userData?.roamPolicy || null,
      target: activeMarker.userData?.autonomousRoamTarget || null,
      gaitMode: activeMarker.userData?.autonomousGaitMode || activeMarker.userData?.gaitMode || null,
      goalsReached: activeMarker.userData?.autonomousGoalCount || 0,
      recentHistory: activeMarker.userData?.autonomousRoamHistory || [],
    } : null,
    activeSkillInteraction: activeSkillInteraction ? {
      id: activeSkillInteraction.id,
      kind: activeSkillInteraction.kind,
      action: activeSkillInteraction.action,
      age: Number((clock.elapsedTime - activeSkillInteraction.startedAt).toFixed(3)),
    } : activeMarker?.userData?.skillInteraction || null,
    persistentQuietActivity: persistentQuietActivitySnapshot(),
    activeGaitMode: activeMarker?.userData?.gaitMode || null,
    activeMoving: !!activeMarker?.userData?.isMoving,
    transitionEvidence: activeMarker?.userData?.transitionEvidence || null,
    lastEmbodimentCapabilityBlock: activeMarker?.userData?.lastEmbodimentCapabilityBlock || null,
    activeHeldProp: activeHeldPropEvidenceSnapshot(),
    visualGroundContact: activeMarker?.userData?.visualGroundContact || null,
    voluntaryBodyActions: window.kiraSyntheticBodyActions ? {
      actions: window.kiraSyntheticBodyActions.actions,
      subjectChoiceRequired: true,
      externalForceAllowed: false,
    } : null,
    activePosition: activeMarker ? {
      x: Number(activeMarker.position.x.toFixed(3)),
      y: Number(activeMarker.position.y.toFixed(3)),
      z: Number(activeMarker.position.z.toFixed(3)),
    } : null,
    kiraEyeRig: activeKiraEyeRig ? kiraEyeBindingProbe() : activeAvatarIsKiraLike() ? {
      active: false,
      disabledReason: KIRA_LIVE_EYE_RIG_ENABLED
        ? "Kira staged eye-rig v3.3 is enabled but is still loading or failed to attach."
        : KIRA_STAGED_EYE_RIG_VERSION === "off"
          ? "Kira's reviewed v3.3 eye rig was explicitly disabled for this page with ?kiraEyeRig=off."
          : `Unsupported Kira eye-rig request: ${KIRA_STAGED_EYE_RIG_VERSION}.`,
      version: KIRA_EYE_CONTROL_EXAM_VERSION,
      modelUrl: KIRA_STAGED_EYE_RIG_MODEL_URL,
      expectedSha256: KIRA_STAGED_EYE_RIG_SHA256,
      defaultEnabled: true,
      optOutFlag: "?kiraEyeRig=off",
      explicitVersionFlag: "?kiraEyeRig=v3.3",
    } : null,
    kiraExistingMouthLipSync: activeAvatarIsKiraLike() ? kiraExistingMouthLipSyncProbe() : null,
    kiraArmTest: activeKiraArmTestState ? {
      active: true,
      age: Number((clock.elapsedTime - activeKiraArmTestState.startedAt).toFixed(3)),
      seconds: activeKiraArmTestState.seconds,
    } : null,
    kiraDoctorBodyExam: activeKiraDoctorExamState ? {
      active: true,
      phase: activeMarker?.userData?.doctorBodyExam?.phase || null,
      phaseIndex: activeMarker?.userData?.doctorBodyExam?.index || 0,
      phaseCount: KIRA_DOCTOR_JOINT_PHASES.length,
      results: Array.from(activeKiraDoctorExamState.results.values()),
    } : activeMarker?.userData?.doctorBodyExam || null,
    kiraComfortIdle: activeAvatarIsKiraLike() ? kiraComfortIdleStatus() : null,
    groundLieClearance: activeMarker?.userData?.groundLieClearance || null,
    kiraDreamState: activeKiraDreamState || null,
    basketballPractice: basketballPracticeState ? {
      active: true,
      phase: basketballPracticeState.phase,
      age: Number((clock.elapsedTime - basketballPracticeState.startedAt).toFixed(3)),
      seconds: basketballPracticeState.seconds,
    } : null,
    walkCyclePhase: Number((activeMarker?.userData?.walkCyclePhase ?? activeAvatarMovePhase).toFixed(3)),
    walkSpeed: Number((activeMarker?.userData?.walkSpeed || 0).toFixed(3)),
    walkTimeScale: Number((activeMarker?.userData?.walkTimeScale || 0).toFixed(3)),
    walkPhaseLocked: !!activeMarker?.userData?.walkPhaseLocked,
    walkClipTime: Number((activeMarker?.userData?.walkClipTime || 0).toFixed(3)),
    doorInteraction: activeDoorInteraction ? {
      id: activeDoorInteraction.id,
      opened: !!activeDoorInteraction.opened,
      failed: !!activeDoorInteraction.failed,
      gripped: !!activeDoorInteraction.gripped,
      ikSolved: !!activeDoorInteraction.ikSolved,
      ikGripLocked: !!activeDoorInteraction.ikGripLocked,
      preferredHand: activeDoorInteraction.preferredHand || "R",
      handContact: activeDoorInteraction.handContact || null,
      age: Number((clock.elapsedTime - activeDoorInteraction.startedAt).toFixed(3)),
    } : null,
    tardisState: activeAvatarHomeTardisStateSnapshot(),
    furnitureInteraction: activeFurnitureInteraction ? {
      id: activeFurnitureInteraction.id,
      stage: activeFurnitureInteraction.stage,
      age: Number((clock.elapsedTime - activeFurnitureInteraction.startedAt).toFixed(3)),
      chairOffsetX: Number((ladybugDeskChairGroup?.position.x || 0).toFixed(3)),
    } : null,
    postureInteraction: activePostureInteraction ? {
      id: activePostureInteraction.id,
      action: activePostureInteraction.action,
      age: Number((clock.elapsedTime - activePostureInteraction.startedAt).toFixed(3)),
    } : null,
    mindBodyTruth: activeMarker?.userData?.lastMindBodyTruth || activeMindBodyTruthSnapshot("live_runtime_panel", activeShellState?.active_action || activeAvatarAction),
    postureState: activeMarker?.userData?.postureState || null,
    supportState: activeMarker?.userData?.supportState || null,
    footContacts: activeMarker?.userData?.footContacts || null,
    fingerContacts: activeMarker?.userData?.fingerContacts || [],
    selfTestState: activeMarker?.userData?.selfTestState || null,
    movementLearningSummary: window.kiraMovementLearning?.summary?.() || null,
    importedHouseReference: importedHouseReferenceStatus,
    realisticSofa: realisticSofaStatus,
    realisticBookshelf: realisticBookshelfStatus,
    neighborHouseReference: neighborHouseReferenceStatus,
    kiraBungalow: kiraBungalowStatus,
    captureFlag: {
      ...captureFlagState,
      bestSeconds: captureFlagState.bestSeconds === null ? null : Number(captureFlagState.bestSeconds.toFixed(2)),
      flagVisible: !!captureFlagFlagGroup?.visible,
      flagPosition: captureFlagFlagGroup?.visible ? {
        x: Number(captureFlagFlagGroup.position.x.toFixed(3)),
        y: Number(captureFlagFlagGroup.position.y.toFixed(3)),
        z: Number(captureFlagFlagGroup.position.z.toFixed(3)),
      } : null,
      playerInBattlefield: captureFlagPointInBounds(player.position),
      npcCount: captureFlagNpcs.length,
      npcModelsLoaded: {
        stormtrooper: !!captureFlagNpcModels.stormtrooper,
        dalek: !!captureFlagNpcModels.dalek,
      },
      npcPositions: captureFlagNpcs.map((npc) => ({
        name: npc.name,
        type: npc.type,
        x: Number(npc.group.position.x.toFixed(2)),
        z: Number(npc.group.position.z.toFixed(2)),
        alert: !!npc.group.userData.alert,
        modelAttached: !!npc.modelAttached,
        modelSuppressedReason: npc.modelSuppressedReason || null,
      })),
      battlefieldVisible: !!captureFlagBattlefieldGroup?.visible,
      observerMode: !!observeFollowEnabled,
    },
    observeFollow: {
      enabled: !!observeFollowEnabled,
      observationReportRunning: !!observationReportState.running,
      observationSamples: observationReportState.samples.length,
    },
    roamZone: activeMarker?.userData?.roamZone || "downstairs",
    roamIndex: activeMarker?.userData?.roamIndex ?? null,
    practiceRoute: activeMarker?.userData?.practiceRoute?.id || null,
    marinetteRuntimeRepair: activeMarker?.userData?.marinetteRuntimeRepair || null,
    spiderHeroMaterialRepair: !!activeMarker?.userData?.spiderHeroMaterialRepair,
    doorFailureCooldowns: Object.fromEntries([...activeDoorFailureCooldowns.entries()].map(([key, until]) => [key, Number(Math.max(0, until - clock.elapsedTime).toFixed(2))])),
    proceduralDoorArmVisible: !!activeDoorReachRig,
  };
  postActiveAvatarSnapshot(clock.elapsedTime);
  for (const obj of scene.children) {
    if (obj.userData?.billboard) obj.lookAt(camera.position);
  }
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

addLight();
addSite();
if (MAIN_TWO_STORY_HOUSE_ENABLED) {
  addHouseShell();
  loadImportedHouseReference();
  addInteriorWalls();
  addFixtures();
  addStairCore();
}
if (NEIGHBOR_BLUEPRINT_HOUSE_ENABLED) addNeighborBlueprintHouse();
addOneBedroomBlueprintHouseWithCopies();
if (KIRA_BUNGALOW_ENABLED) addKiraBungalow();
addHomeWorldActivities();
if (HOME_WORLD_LEGACY_STRIP_MALL_ENABLED) {
  addStripMall();
} else {
  homeWorldActivityStatus = {
    ...homeWorldActivityStatus,
    legacyStripMall: {
      ...homeWorldActivityStatus.legacyStripMall,
      enabled: false,
      loaded: false,
      skipped: true,
      mode: "empty_lot_default",
      sourceDeleted: false,
      spaPlacedHere: false,
      disabledReason: "Robert chose to leave the former strip-mall site visually empty for now.",
      restoreSwitch: "add ?stripMall=1 to restore the preserved legacy blockout for comparison",
      skippedItems: ["128 procedural meshes", "37 static colliders", "5 door colliders", "6 interaction zones", "5 canvas sign textures"],
    },
  };
}
addPublicLibrary();
if (CAPTURE_FLAG_SEPARATE_NOTEBOOK_WORLD_PENDING || HOME_WORLD_PRE_RAM_LIGHT_MODE) {
  markPreRamAssetSkipped("captureFlagParkingLot", {
    timeMachineCarUrl: CAPTURE_FLAG_TIME_CAR_MODEL_URL,
    asphaltCenter: { x: 43.8, z: 41.8 },
    disabledItems: ["parking lot asphalt", "parking stripes", "curbs", "capture flag portal wall", "game parking label", "imported time machine reference car"],
    restoreNote: "do not restore this into Home World; Capture The Flag should be rebuilt/launched as its own notebook world like Paris",
  });
} else {
  addCaptureFlagParkingLot();
}
if (CAPTURE_FLAG_WORLD_ENABLED) {
  addCaptureFlagBattlefield();
}
removeHomeWorldNotebookFieldArtifacts();
let oneBedroomNotebookCleanupAttempts = 0;
const oneBedroomNotebookCleanupTimer = window.setInterval(() => {
  oneBedroomNotebookCleanupAttempts += 1;
  removeHomeWorldNotebookFieldArtifacts();
  if (oneBedroomNotebookCleanupAttempts >= 32) window.clearInterval(oneBedroomNotebookCleanupTimer);
}, 250);
if (HOME_TARDIS_ARRIVED) moveHomeTardisTo(new THREE.Vector3(-12.8, 0, 12.4));
addInteractLabels();
createObserveFollowButton();
setStartPosition();
updateCamera();

// CODEX_HOME_WORLD_EMBODIED_SCREEN_BRIDGE_BEGIN
// Manual, private camera/library-to-screen foundation. A camera stream or an
// already-authorized opaque library grant may begin presentation only from
// Robert's trusted direct click on the control below. A trusted parent may
// prepare (but never play) a person-bound media grant. Every source attaches
// to one exact physical mesh and is never promoted to avatar perception,
// global sensory truth, a recording, stored media, or proof of attention.
const EMBODIED_SCREEN_CONTROL_MESSAGE = "kira-embodied-screen-control";
const EMBODIED_SCREEN_STATE_MESSAGE = "kira-embodied-screen-state";
const EMBODIED_SCREEN_MEDIA_PREPARE_MESSAGE = "kira-embodied-screen-media-prepare";
const EMBODIED_SCREEN_MEDIA_EVENT_MESSAGE = "kira-embodied-screen-media-event";
const EMBODIED_SCREEN_APPROVED_PARENT_ORIGINS = Object.freeze([
  "http://127.0.0.1:8767",
  "http://localhost:8767",
]);
const EMBODIED_SCREEN_APPROVED_TYPES = Object.freeze(["tv", "monitor", "tablet", "phone"]);
const EMBODIED_SCREEN_APPROVED_MEDIA_FAMILIES = Object.freeze(["timed_video", "timed_audio", "page_media"]);
const EMBODIED_SCREEN_MEDIA_EVENTS = Object.freeze(["play", "pause", "checkpoint", "ended", "page_presented"]);
const EMBODIED_SCREEN_MAX_PAGE_PRESENTATION_SECONDS = 21600;
const EMBODIED_SCREEN_STATES = Object.freeze({
  OFF: "off",
  REQUESTING: "requesting",
  ACTIVE: "active",
  PAUSED: "paused",
  ERROR: "error",
});
const EMBODIED_SCREEN_PARENT_TRUST = (() => {
  let detectedOrigin = "";
  let discovery = "";
  try {
    // Chromium exposes the exact embedding origin even when the shell's
    // Referrer-Policy is no-referrer. No arbitrary embedder is ever trusted.
    if (window.location.ancestorOrigins?.length) {
      detectedOrigin = String(window.location.ancestorOrigins[0] || "");
      discovery = "ancestor_origins";
    } else if (document.referrer) {
      detectedOrigin = new URL(document.referrer).origin;
      discovery = "document_referrer";
    }
  } catch (_error) {
    detectedOrigin = "";
  }
  if (EMBODIED_SCREEN_APPROVED_PARENT_ORIGINS.includes(detectedOrigin)) {
    return Object.freeze({ available: true, origin: detectedOrigin, discovery, reason: "" });
  }
  return Object.freeze({
    available: false,
    origin: "",
    discovery: discovery || "unavailable",
    reason: detectedOrigin
      ? "unapproved_parent_origin"
      : "trusted_parent_origin_unavailable_fail_closed",
  });
})();
const EMBODIED_SCREEN_PARENT_ORIGIN = EMBODIED_SCREEN_PARENT_TRUST.origin;
const embodiedScreenRuntime = {
  state: EMBODIED_SCREEN_STATES.OFF,
  screenId: "",
  screenType: "",
  requestId: "",
  requestSource: "",
  error: "",
  requestGeneration: 0,
  stream: null,
  video: null,
  texture: null,
  binding: null,
  sourceKind: "",
  mediaFamily: "",
  mediaElement: null,
  mediaImage: null,
  mediaId: "",
  pagePresentedAt: 0,
  lastMediaCheckpoint: 0,
  lastMediaTruthEvent: "",
  lastMediaTruthPosition: null,
  personBindingKey: "",
};
let embodiedScreenShellPersonKey = "";
let queuedEmbodiedScreenMedia = null;
let embodiedScreenControlElements = null;

function embodiedScreenPersonKey(shellState = {}) {
  const personId = String(shellState.active_candidate || "").trim();
  const activationRevision = String(shellState.last_activation_at || "").trim();
  return personId && activationRevision ? `${personId}|${activationRevision}` : "";
}

function embodiedScreenSafeTitle(value) {
  const title = String(value || "Library media").replace(/[\r\n\t]+/g, " ").trim().slice(0, 160);
  if (!title || title.includes("/") || title.includes("\\") || /(?:[a-z]:|file:)/i.test(title)) return "Library media";
  return title;
}

function embodiedScreenGrantUrl(value) {
  const source = String(value || "").trim();
  if (!/^(?:https?:\/\/[^/]+)?\/api\/media\/stream\?grant=[A-Za-z0-9_-]{24,512}$/.test(source)) return "";
  try {
    const grantBase = EMBODIED_SCREEN_PARENT_ORIGIN && EMBODIED_SCREEN_PARENT_ORIGIN !== "null"
      ? `${EMBODIED_SCREEN_PARENT_ORIGIN}/`
      : window.location.href;
    const resolved = new URL(source, grantBase);
    const approvedOrigins = new Set([
      window.location.origin,
      ...(EMBODIED_SCREEN_PARENT_ORIGIN ? [EMBODIED_SCREEN_PARENT_ORIGIN] : []),
    ]);
    if (!approvedOrigins.has(resolved.origin) || resolved.pathname !== "/api/media/stream") return "";
    if ([...resolved.searchParams.keys()].length !== 1) return "";
    if (!/^[A-Za-z0-9_-]{24,512}$/.test(resolved.searchParams.get("grant") || "")) return "";
    return resolved.origin === window.location.origin
      ? `${resolved.pathname}${resolved.search}`
      : resolved.href;
  } catch (_error) {
    return "";
  }
}

function embodiedScreenQueuedMediaPublicState() {
  if (!queuedEmbodiedScreenMedia) return null;
  return {
    mediaId: queuedEmbodiedScreenMedia.mediaId,
    family: queuedEmbodiedScreenMedia.family,
    mimeType: queuedEmbodiedScreenMedia.mimeType,
    title: queuedEmbodiedScreenMedia.title,
    personBound: true,
    pathExposed: false,
    readyToPresent: true,
    autoplay: false,
  };
}

function embodiedScreenLineage(mesh) {
  const names = [];
  let current = mesh;
  while (current && current !== scene) {
    const name = String(current.name || current.userData?.truthLabel || "").trim();
    if (name) names.unshift(name);
    current = current.parent;
  }
  return names.join(" / ");
}

function embodiedScreenType(mesh) {
  const lineage = embodiedScreenLineage(mesh).toLowerCase();
  if (/\b(tablet|ipad)\b/.test(lineage)) return "tablet";
  if (/\b(phone|telephone|smartphone)\b/.test(lineage)) return "phone";
  if (/\b(tv|television)\b/.test(lineage)) return "tv";
  if (/\b(monitor|computer|laptop|display)\b/.test(lineage)) return "monitor";
  return "";
}

function embodiedScreenMaterialLooksLikeDisplay(material) {
  if (!material) return false;
  return /screen|display|02.*default/i.test(String(material.name || ""))
    || Boolean(material.emissiveMap);
}

function embodiedScreenMeshLooksLikeDisplay(mesh, screenType) {
  if (!mesh?.isMesh || !screenType) return false;
  const meshName = String(mesh.name || "").toLowerCase();
  const materialsForMesh = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  if (/screen|display|body_02/.test(meshName)) return true;
  if (materialsForMesh.some(embodiedScreenMaterialLooksLikeDisplay)) return true;
  // Procedural monitors are authored as a single mesh named exactly for the
  // monitor. Do not classify their stands/arms/bases or TV furniture as feeds.
  return screenType === "monitor"
    && /\bmonitor\b/.test(meshName)
    && !/\b(stand|arm|base|foot|desk|keyboard|console|cabinet|remote)\b/.test(meshName);
}

function embodiedScreenSlug(value) {
  return String(value || "screen")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120) || "screen";
}

function embodiedScreenCandidates() {
  const candidates = [];
  const duplicateIds = new Map();
  scene.traverse((mesh) => {
    const screenType = embodiedScreenType(mesh);
    if (!embodiedScreenMeshLooksLikeDisplay(mesh, screenType)) return;
    const lineage = embodiedScreenLineage(mesh);
    const requestedId = String(mesh.userData?.embodiedScreenId || "").trim();
    const baseId = requestedId || `home-world:${screenType}:${embodiedScreenSlug(lineage)}`;
    const duplicateNumber = (duplicateIds.get(baseId) || 0) + 1;
    duplicateIds.set(baseId, duplicateNumber);
    const screenId = duplicateNumber === 1 ? baseId : `${baseId}:${duplicateNumber}`;
    candidates.push({
      screenId,
      screenType,
      label: lineage || mesh.name || screenId,
      mesh,
    });
  });
  return candidates.sort((left, right) => left.screenId.localeCompare(right.screenId));
}

function exactEmbodiedScreenCandidate(screenId) {
  const exactScreenId = String(screenId || "").trim();
  if (!exactScreenId) return null;
  return embodiedScreenCandidates().find((candidate) => candidate.screenId === exactScreenId) || null;
}

function embodiedScreenAttentionMetadata(screenId, personObject = activeMarker) {
  const candidate = exactEmbodiedScreenCandidate(screenId);
  if (!candidate) {
    return {
      screenId: String(screenId || ""),
      screenFound: false,
      attentionClaimed: false,
      reason: "exact_screen_id_not_found",
    };
  }
  const screenPosition = candidate.mesh.getWorldPosition(new THREE.Vector3());
  const screenQuaternion = candidate.mesh.getWorldQuaternion(new THREE.Quaternion());
  const screenForward = new THREE.Vector3(0, 0, 1).applyQuaternion(screenQuaternion).normalize();
  const personPosition = personObject?.getWorldPosition
    ? personObject.getWorldPosition(new THREE.Vector3())
    : null;
  const personQuaternion = personObject?.getWorldQuaternion
    ? personObject.getWorldQuaternion(new THREE.Quaternion())
    : null;
  const personForward = personQuaternion
    ? new THREE.Vector3(0, 0, 1).applyQuaternion(personQuaternion).normalize()
    : null;
  const personToScreen = personPosition
    ? screenPosition.clone().sub(personPosition)
    : null;
  const distanceMeters = personToScreen ? personToScreen.length() : null;
  const personToScreenDirection = personToScreen && distanceMeters > 0
    ? personToScreen.clone().multiplyScalar(1 / distanceMeters)
    : null;
  const screenToPersonDirection = personToScreenDirection
    ? personToScreenDirection.clone().multiplyScalar(-1)
    : null;
  const hierarchyVisible = (() => {
    let current = candidate.mesh;
    while (current && current !== scene) {
      if (!current.visible) return false;
      current = current.parent;
    }
    return true;
  })();
  return {
    screenId: candidate.screenId,
    screenType: candidate.screenType,
    screenFound: true,
    screenVisible: hierarchyVisible,
    distanceMeters: Number.isFinite(distanceMeters) ? Number(distanceMeters.toFixed(3)) : null,
    personFacingCosine: personForward && personToScreenDirection
      ? Number(personForward.dot(personToScreenDirection).toFixed(4))
      : null,
    screenFacingPersonCosine: screenToPersonDirection
      ? Number(screenForward.dot(screenToPersonDirection).toFixed(4))
      : null,
    screenWorldPosition: {
      x: Number(screenPosition.x.toFixed(3)),
      y: Number(screenPosition.y.toFixed(3)),
      z: Number(screenPosition.z.toFixed(3)),
    },
    orientationAvailable: Boolean(personForward),
    occlusionTested: false,
    lineOfSightProven: false,
    attentionClaimed: false,
    futureAttentionHookOnly: true,
  };
}

function embodiedScreenPublicState(extra = {}) {
  const availableScreens = embodiedScreenCandidates()
    .filter(({ screenType }) => EMBODIED_SCREEN_APPROVED_TYPES.includes(screenType))
    .map(({ screenId, screenType, label, mesh }) => ({
      screenId,
      screenType,
      label,
      visible: Boolean(mesh.visible),
    }));
  return {
    schemaVersion: 1,
    state: embodiedScreenRuntime.state,
    screenId: embodiedScreenRuntime.screenId || null,
    screenType: embodiedScreenRuntime.screenType || null,
    requestId: embodiedScreenRuntime.requestId || null,
    requestSource: embodiedScreenRuntime.requestSource || null,
    error: embodiedScreenRuntime.error || null,
    sourceKind: embodiedScreenRuntime.sourceKind || null,
    mediaFamily: embodiedScreenRuntime.mediaFamily || null,
    personBound: Boolean(embodiedScreenRuntime.personBindingKey),
    queuedMedia: embodiedScreenQueuedMediaPublicState(),
    parentIntegrationAvailable: EMBODIED_SCREEN_PARENT_TRUST.available,
    parentIntegrationReason: EMBODIED_SCREEN_PARENT_TRUST.reason || null,
    ownerInitiatedOnly: true,
    cameraRequestedAutomatically: false,
    mediaPlayedAutomatically: false,
    audioCaptureAllowed: false,
    recordingAllowed: false,
    storageAllowed: false,
    globalSensoryTruth: false,
    visualScope: "screen_bound_transient_feed_only",
    attention: embodiedScreenRuntime.screenId
      ? embodiedScreenAttentionMetadata(embodiedScreenRuntime.screenId)
      : null,
    availableScreens,
    ...extra,
  };
}

function embodiedScreenPostState(extra = {}) {
  const snapshot = embodiedScreenPublicState(extra);
  updateEmbodiedScreenOwnerControl(snapshot);
  if (EMBODIED_SCREEN_PARENT_TRUST.available && window.parent && window.parent !== window) {
    window.parent.postMessage(
      { type: EMBODIED_SCREEN_STATE_MESSAGE, bridge: snapshot },
      EMBODIED_SCREEN_PARENT_ORIGIN,
    );
  }
  return snapshot;
}

function embodiedScreenPostMediaEvent(eventName, positionSeconds = null, details = {}) {
  if (embodiedScreenRuntime.sourceKind !== "library_media" || !embodiedScreenRuntime.mediaId) return;
  if (!EMBODIED_SCREEN_MEDIA_EVENTS.includes(eventName)) return;
  if (!EMBODIED_SCREEN_PARENT_TRUST.available || !window.parent || window.parent === window) return;
  const exactPosition = Number.isFinite(Number(positionSeconds)) ? Number(positionSeconds) : null;
  const exactVisibleDuration = Number.isFinite(Number(details.visibleDurationSeconds))
    ? Number(details.visibleDurationSeconds)
    : null;
  window.parent.postMessage({
    type: EMBODIED_SCREEN_MEDIA_EVENT_MESSAGE,
    event: String(eventName || ""),
    mediaId: embodiedScreenRuntime.mediaId,
    positionSeconds: exactPosition,
    visibleDurationSeconds: exactVisibleDuration,
    durationClamped: details.durationClamped === true,
    screenId: embodiedScreenRuntime.screenId || null,
    personBound: true,
    presentationEventOnly: true,
    attentionClaimed: false,
    memoryCreated: false,
  }, EMBODIED_SCREEN_PARENT_ORIGIN);
  embodiedScreenRuntime.lastMediaTruthEvent = String(eventName);
  embodiedScreenRuntime.lastMediaTruthPosition = exactPosition;
}

function setEmbodiedScreenState(state, details = {}) {
  embodiedScreenRuntime.state = state;
  if (Object.prototype.hasOwnProperty.call(details, "screenId")) {
    embodiedScreenRuntime.screenId = String(details.screenId || "");
  }
  if (Object.prototype.hasOwnProperty.call(details, "screenType")) {
    embodiedScreenRuntime.screenType = String(details.screenType || "");
  }
  if (Object.prototype.hasOwnProperty.call(details, "requestId")) {
    embodiedScreenRuntime.requestId = String(details.requestId || "");
  }
  if (Object.prototype.hasOwnProperty.call(details, "requestSource")) {
    embodiedScreenRuntime.requestSource = String(details.requestSource || "");
  }
  embodiedScreenRuntime.error = String(details.error || "").slice(0, 300);
  return embodiedScreenPostState();
}

function embodiedScreenVideoMaterial(originalMaterial, texture) {
  const material = new THREE.MeshBasicMaterial({
    map: texture,
    side: originalMaterial?.side ?? THREE.FrontSide,
    toneMapped: false,
  });
  material.name = "Kira transient embodied screen material";
  return material;
}

function bindEmbodiedVideoTexture(candidate, texture) {
  const mesh = candidate.mesh;
  const originalMaterial = mesh.material;
  const videoMaterials = [];
  if (Array.isArray(originalMaterial)) {
    const displaySlots = originalMaterial.map((material) => embodiedScreenMaterialLooksLikeDisplay(material));
    const anyDisplaySlot = displaySlots.some(Boolean);
    mesh.material = originalMaterial.map((material, index) => {
      if (anyDisplaySlot && !displaySlots[index]) return material;
      const replacement = embodiedScreenVideoMaterial(material, texture);
      videoMaterials.push(replacement);
      return replacement;
    });
  } else {
    const replacement = embodiedScreenVideoMaterial(originalMaterial, texture);
    videoMaterials.push(replacement);
    mesh.material = replacement;
  }
  mesh.userData = mesh.userData || {};
  mesh.userData.embodiedScreenFeedActive = true;
  return { mesh, originalMaterial, videoMaterials };
}

function stopEmbodiedMediaTracks(stream) {
  if (!stream?.getTracks) return;
  stream.getTracks().forEach((track) => track.stop());
}

function closeEmbodiedScreenPresentationTruth() {
  if (embodiedScreenRuntime.sourceKind !== "library_media") return;
  const mediaElement = embodiedScreenRuntime.mediaElement;
  if (mediaElement) {
    const position = Number(mediaElement.currentTime || 0);
    const duration = Number(mediaElement.duration);
    const reachedEnd = mediaElement.ended === true
      || (Number.isFinite(duration) && duration > 0 && position >= duration - 0.05);
    const eventName = reachedEnd ? "ended" : "pause";
    if (embodiedScreenRuntime.lastMediaTruthEvent === "ended") return;
    if (eventName === "pause" && embodiedScreenRuntime.lastMediaTruthEvent === "pause") return;
    embodiedScreenPostMediaEvent(eventName, position);
    return;
  }
  if (embodiedScreenRuntime.mediaFamily === "page_media" && embodiedScreenRuntime.pagePresentedAt > 0) {
    if (embodiedScreenRuntime.lastMediaTruthEvent === "page_presented") return;
    const actualVisibleSeconds = Math.max(0, (performance.now() - embodiedScreenRuntime.pagePresentedAt) / 1000);
    const visibleDurationSeconds = Math.min(
      EMBODIED_SCREEN_MAX_PAGE_PRESENTATION_SECONDS,
      actualVisibleSeconds,
    );
    embodiedScreenPostMediaEvent("page_presented", null, {
      visibleDurationSeconds,
      durationClamped: actualVisibleSeconds > EMBODIED_SCREEN_MAX_PAGE_PRESENTATION_SECONDS,
    });
  }
}

function finalizeEmbodiedScreenPresentation() {
  closeEmbodiedScreenPresentationTruth();
  teardownEmbodiedScreenResources();
}

function teardownEmbodiedScreenResources() {
  const { binding, texture, video, stream, mediaElement, mediaImage } = embodiedScreenRuntime;
  if (binding?.mesh) {
    binding.mesh.material = binding.originalMaterial;
    binding.mesh.userData.embodiedScreenFeedActive = false;
    binding.videoMaterials.forEach((material) => material.dispose());
  }
  if (texture) texture.dispose();
  if (video) {
    video.pause();
    video.srcObject = null;
    video.removeAttribute("src");
  }
  if (mediaElement) {
    mediaElement.pause();
    mediaElement.removeAttribute("src");
    if (mediaElement.load) mediaElement.load();
  }
  if (mediaImage) mediaImage.removeAttribute("src");
  stopEmbodiedMediaTracks(stream);
  embodiedScreenRuntime.binding = null;
  embodiedScreenRuntime.texture = null;
  embodiedScreenRuntime.video = null;
  embodiedScreenRuntime.stream = null;
  embodiedScreenRuntime.mediaElement = null;
  embodiedScreenRuntime.mediaImage = null;
  embodiedScreenRuntime.mediaId = "";
  embodiedScreenRuntime.pagePresentedAt = 0;
  embodiedScreenRuntime.lastMediaCheckpoint = 0;
  embodiedScreenRuntime.lastMediaTruthEvent = "";
  embodiedScreenRuntime.lastMediaTruthPosition = null;
  embodiedScreenRuntime.sourceKind = "";
  embodiedScreenRuntime.mediaFamily = "";
  embodiedScreenRuntime.personBindingKey = "";
}

function turnOffEmbodiedScreen(reason = "owner_off", requestId = "") {
  embodiedScreenRuntime.requestGeneration += 1;
  finalizeEmbodiedScreenPresentation();
  queuedEmbodiedScreenMedia = null;
  return setEmbodiedScreenState(EMBODIED_SCREEN_STATES.OFF, {
    screenId: "",
    screenType: "",
    requestId,
    requestSource: reason,
    error: "",
  });
}

async function requestEmbodiedScreenAttach(
  screenId,
  requestId = "",
  requestSource = "owner_direct_click",
  ownerGestureProof = false,
) {
  if (!ownerGestureProof) {
    return embodiedScreenPostState({
      requestId,
      requestRejected: "owner_direct_click_required",
      requestedScreenId: String(screenId || ""),
      requestSource,
    });
  }
  const exactScreenId = String(screenId || "").trim();
  if (!embodiedScreenShellPersonKey) {
    return embodiedScreenPostState({
      requestId,
      requestRejected: "active_person_required",
      requestedScreenId: exactScreenId,
      requestSource,
    });
  }
  embodiedScreenRuntime.requestGeneration += 1;
  const requestGeneration = embodiedScreenRuntime.requestGeneration;
  finalizeEmbodiedScreenPresentation();
  const candidate = exactEmbodiedScreenCandidate(exactScreenId);
  if (!candidate) {
    return setEmbodiedScreenState(EMBODIED_SCREEN_STATES.ERROR, {
      screenId: exactScreenId,
      screenType: "",
      requestId,
      requestSource,
      error: "exact_screen_id_not_found",
    });
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    return setEmbodiedScreenState(EMBODIED_SCREEN_STATES.ERROR, {
      screenId: exactScreenId,
      screenType: candidate.screenType,
      requestId,
      requestSource,
      error: "camera_api_unavailable",
    });
  }

  setEmbodiedScreenState(EMBODIED_SCREEN_STATES.REQUESTING, {
    screenId: exactScreenId,
    screenType: candidate.screenType,
    requestId,
    requestSource,
    error: "",
  });

  let stream = null;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280, max: 1920 },
        height: { ideal: 720, max: 1080 },
        frameRate: { ideal: 24, max: 30 },
      },
      audio: false,
    });
    if (requestGeneration !== embodiedScreenRuntime.requestGeneration) {
      stopEmbodiedMediaTracks(stream);
      return embodiedScreenPublicState({ superseded: true });
    }

    const video = document.createElement("video");
    video.muted = true;
    video.autoplay = false;
    video.playsInline = true;
    video.disablePictureInPicture = true;
    video.setAttribute("aria-hidden", "true");
    video.srcObject = stream;
    await video.play();
    if (requestGeneration !== embodiedScreenRuntime.requestGeneration) {
      video.pause();
      video.srcObject = null;
      stopEmbodiedMediaTracks(stream);
      return embodiedScreenPublicState({ superseded: true });
    }

    embodiedScreenRuntime.stream = stream;
    embodiedScreenRuntime.video = video;
    embodiedScreenRuntime.sourceKind = "camera";
    embodiedScreenRuntime.personBindingKey = embodiedScreenShellPersonKey;
    const texture = new THREE.VideoTexture(video);
    embodiedScreenRuntime.texture = texture;
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.generateMipmaps = false;
    if ("colorSpace" in texture && THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
    const binding = bindEmbodiedVideoTexture(candidate, texture);
    embodiedScreenRuntime.binding = binding;
    return setEmbodiedScreenState(EMBODIED_SCREEN_STATES.ACTIVE, {
      screenId: candidate.screenId,
      screenType: candidate.screenType,
      requestId,
      requestSource,
      error: "",
    });
  } catch (error) {
    if (stream && stream !== embodiedScreenRuntime.stream) stopEmbodiedMediaTracks(stream);
    if (requestGeneration !== embodiedScreenRuntime.requestGeneration) {
      return embodiedScreenPublicState({ superseded: true });
    }
    teardownEmbodiedScreenResources();
    return setEmbodiedScreenState(EMBODIED_SCREEN_STATES.ERROR, {
      screenId: exactScreenId,
      screenType: candidate.screenType,
      requestId,
      requestSource,
      error: error?.name || error?.message || "camera_attach_failed",
    });
  }
}

function prepareEmbodiedScreenLibraryMedia(data) {
  const family = String(data?.family || "").trim();
  const mimeType = String(data?.mimeType || data?.mime_type || "").trim().toLowerCase().slice(0, 100);
  const mediaId = String(data?.mediaId || data?.media_id || "").trim().toLowerCase();
  const personId = String(data?.personId || data?.person_id || "").trim();
  const activationRevision = String(data?.activationRevision || data?.activation_revision || "").trim();
  const personBindingKey = personId && activationRevision ? `${personId}|${activationRevision}` : "";
  const grantUrl = embodiedScreenGrantUrl(data?.streamUrl || data?.stream_url);
  const requestId = String(data?.requestId || "");
  if (!embodiedScreenShellPersonKey || personBindingKey !== embodiedScreenShellPersonKey) {
    queuedEmbodiedScreenMedia = null;
    return embodiedScreenPostState({ requestId, mediaPrepareRejected: "active_person_binding_mismatch" });
  }
  if (!EMBODIED_SCREEN_APPROVED_MEDIA_FAMILIES.includes(family)) {
    queuedEmbodiedScreenMedia = null;
    return embodiedScreenPostState({ requestId, mediaPrepareRejected: "unsupported_media_family" });
  }
  if (!/^[a-f0-9]{64}$/.test(mediaId) || !grantUrl) {
    queuedEmbodiedScreenMedia = null;
    return embodiedScreenPostState({ requestId, mediaPrepareRejected: "opaque_local_grant_required" });
  }
  if (
    (family === "timed_video" && !mimeType.startsWith("video/"))
    || (family === "timed_audio" && !mimeType.startsWith("audio/"))
    || (family === "page_media" && !(mimeType.startsWith("image/") || mimeType === "application/pdf"))
  ) {
    queuedEmbodiedScreenMedia = null;
    return embodiedScreenPostState({ requestId, mediaPrepareRejected: "family_mime_mismatch" });
  }
  queuedEmbodiedScreenMedia = {
    mediaId,
    family,
    mimeType,
    title: embodiedScreenSafeTitle(data?.title),
    grantUrl,
    personBindingKey,
  };
  return embodiedScreenPostState({
    requestId,
    mediaPrepared: true,
    autoplay: false,
    pathExposed: false,
  });
}

function embodiedScreenSlateTexture(title, subtitle) {
  const canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 576;
  const context = canvas.getContext("2d");
  context.fillStyle = "#07111d";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.strokeStyle = "#2f9fd0";
  context.lineWidth = 10;
  context.strokeRect(24, 24, canvas.width - 48, canvas.height - 48);
  context.fillStyle = "#e8f2fb";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.font = "700 52px system-ui, sans-serif";
  context.fillText(embodiedScreenSafeTitle(title).slice(0, 34), canvas.width / 2, 240, 900);
  context.fillStyle = "#a9bfd2";
  context.font = "32px system-ui, sans-serif";
  context.fillText(String(subtitle || "Local library media").slice(0, 52), canvas.width / 2, 340, 900);
  const texture = new THREE.CanvasTexture(canvas);
  if ("colorSpace" in texture && THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function loadEmbodiedScreenImage(grantUrl) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.decoding = "async";
    if (new URL(grantUrl, window.location.href).origin !== window.location.origin) {
      image.crossOrigin = "anonymous";
    }
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("library_image_decode_failed"));
    image.src = grantUrl;
  });
}

function embodiedScreenImageTexture(image) {
  const maximumEdge = 2048;
  const scale = Math.min(1, maximumEdge / Math.max(image.naturalWidth || 1, image.naturalHeight || 1));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round((image.naturalWidth || 1) * scale));
  canvas.height = Math.max(1, Math.round((image.naturalHeight || 1) * scale));
  canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
  const texture = new THREE.CanvasTexture(canvas);
  if ("colorSpace" in texture && THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

async function requestEmbodiedLibraryMediaAttach(screenId, requestId = "", ownerGestureProof = false) {
  if (!ownerGestureProof) {
    return embodiedScreenPostState({ requestId, mediaAttachRejected: "owner_direct_click_required" });
  }
  const queued = queuedEmbodiedScreenMedia;
  if (!queued) return embodiedScreenPostState({ requestId, mediaAttachRejected: "no_prepared_media" });
  if (!embodiedScreenShellPersonKey || queued.personBindingKey !== embodiedScreenShellPersonKey) {
    queuedEmbodiedScreenMedia = null;
    return embodiedScreenPostState({ requestId, mediaAttachRejected: "active_person_binding_mismatch" });
  }
  const candidate = exactEmbodiedScreenCandidate(screenId);
  if (!candidate) {
    return embodiedScreenPostState({ requestId, mediaAttachRejected: "exact_screen_id_not_found" });
  }
  // The preview contains no PDF.js renderer. A browser PDF iframe cannot be
  // sampled safely into a WebGL texture, so PDF pages fail closed rather than
  // displaying a decorative slate that could be mistaken for the document.
  if (queued.mimeType === "application/pdf") {
    return embodiedScreenPostState({
      requestId,
      mediaAttachRejected: "pdf_renderer_unavailable",
      ownerPanelPresentationStillAvailable: true,
    });
  }

  embodiedScreenRuntime.requestGeneration += 1;
  const requestGeneration = embodiedScreenRuntime.requestGeneration;
  finalizeEmbodiedScreenPresentation();
  setEmbodiedScreenState(EMBODIED_SCREEN_STATES.REQUESTING, {
    screenId: candidate.screenId,
    screenType: candidate.screenType,
    requestId,
    requestSource: "owner_direct_media_click",
    error: "",
  });
  let texture = null;
  let mediaElement = null;
  let mediaImage = null;
  try {
    if (queued.family === "timed_video") {
      mediaElement = document.createElement("video");
      mediaElement.autoplay = false;
      mediaElement.controls = false;
      mediaElement.playsInline = true;
      mediaElement.disablePictureInPicture = true;
      if (new URL(queued.grantUrl, window.location.href).origin !== window.location.origin) {
        mediaElement.crossOrigin = "anonymous";
      }
      mediaElement.src = queued.grantUrl;
      await mediaElement.play();
      texture = new THREE.VideoTexture(mediaElement);
      texture.minFilter = THREE.LinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.generateMipmaps = false;
      if ("colorSpace" in texture && THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
    } else if (queued.family === "timed_audio") {
      mediaElement = document.createElement("audio");
      mediaElement.autoplay = false;
      mediaElement.controls = false;
      if (new URL(queued.grantUrl, window.location.href).origin !== window.location.origin) {
        mediaElement.crossOrigin = "anonymous";
      }
      mediaElement.src = queued.grantUrl;
      texture = embodiedScreenSlateTexture(queued.title, "Audio playing from the local library");
      await mediaElement.play();
    } else {
      mediaImage = await loadEmbodiedScreenImage(queued.grantUrl);
      texture = embodiedScreenImageTexture(mediaImage);
      mediaImage.removeAttribute("src");
    }
    if (requestGeneration !== embodiedScreenRuntime.requestGeneration) {
      mediaElement?.pause();
      mediaElement?.removeAttribute("src");
      mediaImage?.removeAttribute("src");
      texture?.dispose();
      return embodiedScreenPublicState({ superseded: true });
    }
    embodiedScreenRuntime.texture = texture;
    embodiedScreenRuntime.binding = bindEmbodiedVideoTexture(candidate, texture);
    embodiedScreenRuntime.mediaElement = mediaElement;
    embodiedScreenRuntime.mediaImage = mediaImage;
    embodiedScreenRuntime.mediaId = queued.mediaId;
    embodiedScreenRuntime.pagePresentedAt = mediaImage ? performance.now() : 0;
    embodiedScreenRuntime.lastMediaCheckpoint = mediaElement
      ? Number(mediaElement.currentTime || 0)
      : 0;
    embodiedScreenRuntime.sourceKind = "library_media";
    embodiedScreenRuntime.mediaFamily = queued.family;
    embodiedScreenRuntime.personBindingKey = queued.personBindingKey;
    queuedEmbodiedScreenMedia = null;
    const state = setEmbodiedScreenState(EMBODIED_SCREEN_STATES.ACTIVE, {
      screenId: candidate.screenId,
      screenType: candidate.screenType,
      requestId,
      requestSource: "owner_direct_media_click",
      error: "",
    });
    if (mediaElement) embodiedScreenPostMediaEvent("play", Number(mediaElement.currentTime || 0));
    if (mediaElement) {
      mediaElement.addEventListener("timeupdate", () => {
        if (embodiedScreenRuntime.mediaElement !== mediaElement || mediaElement.paused) return;
        const position = Number(mediaElement.currentTime || 0);
        if (position - embodiedScreenRuntime.lastMediaCheckpoint < 8) return;
        embodiedScreenRuntime.lastMediaCheckpoint = position;
        embodiedScreenPostMediaEvent("checkpoint", position);
      });
      mediaElement.addEventListener("ended", () => {
        if (embodiedScreenRuntime.mediaElement !== mediaElement) return;
        embodiedScreenPostMediaEvent("ended", Number(mediaElement.currentTime || 0));
        embodiedScreenRuntime.requestGeneration += 1;
        teardownEmbodiedScreenResources();
        setEmbodiedScreenState(EMBODIED_SCREEN_STATES.OFF, {
          screenId: "",
          screenType: "",
          requestSource: "library_media_ended",
          error: "",
        });
      });
    }
    return state;
  } catch (error) {
    if (mediaElement && mediaElement !== embodiedScreenRuntime.mediaElement) {
      mediaElement.pause();
      mediaElement.removeAttribute("src");
      if (mediaElement.load) mediaElement.load();
    }
    if (mediaImage && mediaImage !== embodiedScreenRuntime.mediaImage) mediaImage.removeAttribute("src");
    if (texture && texture !== embodiedScreenRuntime.texture) texture.dispose();
    if (requestGeneration !== embodiedScreenRuntime.requestGeneration) {
      return embodiedScreenPublicState({ superseded: true });
    }
    finalizeEmbodiedScreenPresentation();
    return setEmbodiedScreenState(EMBODIED_SCREEN_STATES.ERROR, {
      screenId: candidate.screenId,
      screenType: candidate.screenType,
      requestId,
      requestSource: "owner_direct_media_click",
      error: error?.name || error?.message || "library_media_attach_failed",
    });
  }
}

async function pauseEmbodiedScreen(requestId = "") {
  if (embodiedScreenRuntime.state !== EMBODIED_SCREEN_STATES.ACTIVE) {
    return embodiedScreenPostState({ requestId, ignoredReason: "screen_not_active" });
  }
  if (embodiedScreenRuntime.sourceKind === "library_media" && !embodiedScreenRuntime.mediaElement) {
    return embodiedScreenPostState({ requestId, ignoredReason: "static_page_has_no_pause_state" });
  }
  embodiedScreenRuntime.video?.pause();
  embodiedScreenRuntime.mediaElement?.pause();
  if (embodiedScreenRuntime.sourceKind === "library_media" && embodiedScreenRuntime.mediaElement) {
    embodiedScreenPostMediaEvent("pause", Number(embodiedScreenRuntime.mediaElement.currentTime || 0));
  }
  embodiedScreenRuntime.stream?.getVideoTracks().forEach((track) => {
    track.enabled = false;
  });
  return setEmbodiedScreenState(EMBODIED_SCREEN_STATES.PAUSED, {
    requestId,
    requestSource: "owner_pause",
    error: "",
  });
}

async function resumeEmbodiedScreen(requestId = "") {
  if (embodiedScreenRuntime.state !== EMBODIED_SCREEN_STATES.PAUSED) {
    return embodiedScreenPostState({ requestId, ignoredReason: "screen_not_paused" });
  }
  if (embodiedScreenRuntime.sourceKind === "library_media" && embodiedScreenRuntime.mediaElement) {
    try {
      await embodiedScreenRuntime.mediaElement.play();
      embodiedScreenPostMediaEvent("play", Number(embodiedScreenRuntime.mediaElement.currentTime || 0));
      return setEmbodiedScreenState(EMBODIED_SCREEN_STATES.ACTIVE, {
        requestId,
        requestSource: "owner_resume",
        error: "",
      });
    } catch (error) {
      finalizeEmbodiedScreenPresentation();
      return setEmbodiedScreenState(EMBODIED_SCREEN_STATES.ERROR, {
        requestId,
        requestSource: "owner_resume",
        error: error?.name || error?.message || "library_media_resume_failed",
      });
    }
  }
  if (!embodiedScreenRuntime.video || !embodiedScreenRuntime.stream) {
    return embodiedScreenPostState({ requestId, ignoredReason: "screen_source_cannot_resume" });
  }
  embodiedScreenRuntime.stream.getVideoTracks().forEach((track) => {
    track.enabled = true;
  });
  try {
    await embodiedScreenRuntime.video.play();
    return setEmbodiedScreenState(EMBODIED_SCREEN_STATES.ACTIVE, {
      requestId,
      requestSource: "owner_resume",
      error: "",
    });
  } catch (error) {
    teardownEmbodiedScreenResources();
    return setEmbodiedScreenState(EMBODIED_SCREEN_STATES.ERROR, {
      requestId,
      requestSource: "owner_resume",
      error: error?.name || error?.message || "camera_resume_failed",
    });
  }
}

function embodiedScreenMessageIsTrusted(event) {
  if (!EMBODIED_SCREEN_PARENT_TRUST.available || !EMBODIED_SCREEN_PARENT_ORIGIN) return false;
  if (!window.parent || window.parent === window || event.source !== window.parent) return false;
  return event.origin === EMBODIED_SCREEN_PARENT_ORIGIN;
}

function handleEmbodiedScreenControl(data) {
  const action = String(data?.action || "status").toLowerCase();
  const requestId = String(data?.requestId || "");
  if (action === "request" || action === "attach") {
    embodiedScreenPostState({
      requestId,
      requestRejected: "owner_direct_click_required",
      requestedScreenId: String(data?.screenId || ""),
    });
    return;
  }
  if (action === "pause") {
    void pauseEmbodiedScreen(requestId);
    return;
  }
  if (action === "resume") {
    void resumeEmbodiedScreen(requestId);
    return;
  }
  if (action === "off") {
    turnOffEmbodiedScreen("trusted_parent_message", requestId);
    return;
  }
  if (action === "status" || action === "list") {
    embodiedScreenPostState({ requestId });
    return;
  }
  embodiedScreenPostState({ requestId, protocolError: "unsupported_action" });
}

function syncEmbodiedScreenPersonBinding(shellState) {
  const nextPersonKey = embodiedScreenPersonKey(shellState);
  if (nextPersonKey === embodiedScreenShellPersonKey) return;
  embodiedScreenShellPersonKey = nextPersonKey;
  if (queuedEmbodiedScreenMedia && queuedEmbodiedScreenMedia.personBindingKey !== nextPersonKey) {
    queuedEmbodiedScreenMedia = null;
  }
  if (embodiedScreenRuntime.personBindingKey && embodiedScreenRuntime.personBindingKey !== nextPersonKey) {
    turnOffEmbodiedScreen("active_person_changed");
    return;
  }
  embodiedScreenPostState({ personBindingChanged: true });
}

window.kiraEmbodiedScreenBridge = Object.freeze({
  protocolVersion: 1,
  listScreens: () => embodiedScreenPublicState().availableScreens,
  state: () => embodiedScreenPublicState(),
  requestAttach: (screenId, requestId = "") => embodiedScreenPostState({
    requestId,
    requestRejected: "owner_direct_click_required",
    requestedScreenId: String(screenId || ""),
  }),
  pause: (requestId = "") => pauseEmbodiedScreen(requestId),
  resume: (requestId = "") => resumeEmbodiedScreen(requestId),
  off: (requestId = "") => turnOffEmbodiedScreen("owner_api", requestId),
  attentionMetadata: (screenId) => embodiedScreenAttentionMetadata(screenId),
  queuedMedia: () => embodiedScreenQueuedMediaPublicState(),
});

function updateEmbodiedScreenOwnerControl(snapshot = embodiedScreenPublicState()) {
  if (!embodiedScreenControlElements) return snapshot;
  const {
    select,
    cameraButton,
    mediaButton,
    pauseButton,
    offButton,
    status,
  } = embodiedScreenControlElements;
  const screens = snapshot.availableScreens || [];
  const previousSelection = select.value;
  const preferredSelection = snapshot.screenId || previousSelection;
  select.replaceChildren();
  for (const screen of screens) {
    const option = document.createElement("option");
    option.value = screen.screenId;
    option.textContent = `${screen.screenType.toUpperCase()} — ${screen.label}`;
    select.appendChild(option);
  }
  if (preferredSelection && screens.some((screen) => screen.screenId === preferredSelection)) {
    select.value = preferredSelection;
  }
  const noScreen = screens.length === 0;
  select.disabled = noScreen || snapshot.state === EMBODIED_SCREEN_STATES.REQUESTING;
  cameraButton.disabled = noScreen
    || !snapshot.parentIntegrationAvailable
    || !embodiedScreenShellPersonKey
    || snapshot.state === EMBODIED_SCREEN_STATES.REQUESTING;
  mediaButton.disabled = noScreen
    || !snapshot.parentIntegrationAvailable
    || !snapshot.queuedMedia
    || snapshot.state === EMBODIED_SCREEN_STATES.REQUESTING;
  const staticPagePresented = snapshot.sourceKind === "library_media"
    && snapshot.mediaFamily === "page_media";
  pauseButton.disabled = staticPagePresented || ![
    EMBODIED_SCREEN_STATES.ACTIVE,
    EMBODIED_SCREEN_STATES.PAUSED,
  ].includes(snapshot.state);
  pauseButton.textContent = snapshot.state === EMBODIED_SCREEN_STATES.PAUSED ? "Resume" : "Pause";
  offButton.disabled = snapshot.state === EMBODIED_SCREEN_STATES.OFF;
  if (!snapshot.parentIntegrationAvailable) {
    status.textContent = "Screen sharing is fail-closed: this browser did not expose the exact approved local Kira shell parent. Firefox requires a future bounded origin handshake.";
  } else if (snapshot.requestRejected === "owner_direct_click_required") {
    status.textContent = "Camera start rejected: use the Camera to screen button directly.";
  } else if (snapshot.requestRejected === "active_person_required") {
    status.textContent = "Start one person's conversation before placing a camera on their screen.";
  } else if (snapshot.mediaPrepareRejected || snapshot.mediaAttachRejected) {
    const reason = snapshot.mediaPrepareRejected || snapshot.mediaAttachRejected;
    status.textContent = reason === "pdf_renderer_unavailable"
      ? "This world cannot render a PDF page onto a 3D screen yet. The owner media panel may still present it; no in-world page claim was made."
      : `Media was not placed on the screen: ${reason}`;
  } else if (noScreen) {
    status.textContent = "No approved TV, monitor, tablet, or phone screen is available yet.";
  } else if (snapshot.state === EMBODIED_SCREEN_STATES.REQUESTING) {
    status.textContent = snapshot.requestSource === "owner_direct_media_click"
      ? "Preparing the selected local media for this exact screen…"
      : "Requesting camera permission…";
  } else if (snapshot.state === EMBODIED_SCREEN_STATES.ACTIVE) {
    status.textContent = snapshot.sourceKind === "library_media"
      ? `Library ${snapshot.mediaFamily} is presented on ${snapshot.screenType}. Presentation does not prove attention.`
      : `Camera active on ${snapshot.screenType}: ${snapshot.screenId}`;
  } else if (snapshot.state === EMBODIED_SCREEN_STATES.PAUSED) {
    status.textContent = snapshot.sourceKind === "library_media"
      ? `Library media paused on ${snapshot.screenType}.`
      : `Camera paused on ${snapshot.screenType}: ${snapshot.screenId}`;
  } else if (snapshot.state === EMBODIED_SCREEN_STATES.ERROR) {
    status.textContent = snapshot.requestSource === "owner_direct_media_click"
      ? `Media error: ${snapshot.error || "request failed"}`
      : `Camera error: ${snapshot.error || "request failed"}`;
  } else if (snapshot.queuedMedia) {
    status.textContent = `${snapshot.queuedMedia.title} is prepared for this person. Click Media to screen; nothing autoplays.`;
  } else {
    status.textContent = "Off. Camera and prepared library media start only from a direct click here.";
  }
  return snapshot;
}

function directEmbodiedScreenOwnerGesture(event) {
  if (!event?.isTrusted) return false;
  return !navigator.userActivation || navigator.userActivation.isActive === true;
}

function createEmbodiedScreenOwnerControl() {
  const root = document.createElement("section");
  root.id = "kira-embodied-screen-owner-control";
  root.setAttribute("aria-label", "Private camera and local library media to in-world screen control");
  root.style.cssText = [
    "position:fixed",
    "right:12px",
    "bottom:12px",
    "z-index:40",
    "width:min(310px,calc(100vw - 24px))",
    "color:#e8f2fb",
    "background:#07111ddd",
    "border:1px solid #34506a",
    "border-radius:8px",
    "box-shadow:0 8px 24px #0009",
    "font:12px/1.35 system-ui,sans-serif",
  ].join(";");

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.textContent = "Screen camera / media ▸";
  toggle.setAttribute("aria-expanded", "false");
  toggle.style.cssText = [
    "width:100%",
    "padding:7px 9px",
    "color:#e8f2fb",
    "background:#102438",
    "border:0",
    "border-radius:7px",
    "text-align:left",
    "font-weight:700",
    "cursor:pointer",
  ].join(";");

  const panel = document.createElement("div");
  panel.hidden = true;
  panel.style.cssText = "padding:8px;display:grid;gap:7px";

  const boundary = document.createElement("div");
  boundary.textContent = "Private webcam or opaque local-library grant → one exact screen. No recording, storage, autoplay, or automatic attention.";
  boundary.style.cssText = "color:#a9bfd2;font-size:11px";

  const select = document.createElement("select");
  select.setAttribute("aria-label", "Exact in-world screen");
  select.style.cssText = "width:100%;padding:6px;color:#e8f2fb;background:#0b1b2a;border:1px solid #34506a;border-radius:5px";

  const actions = document.createElement("div");
  actions.style.cssText = "display:flex;gap:6px;flex-wrap:wrap";
  const makeButton = (label) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.style.cssText = "padding:6px 8px;color:#e8f2fb;background:#17344f;border:1px solid #41627e;border-radius:5px;cursor:pointer";
    return button;
  };
  const cameraButton = makeButton("Camera to screen");
  const mediaButton = makeButton("Media to screen");
  const pauseButton = makeButton("Pause");
  const offButton = makeButton("Off");
  actions.append(cameraButton, mediaButton, pauseButton, offButton);

  const status = document.createElement("div");
  status.setAttribute("role", "status");
  status.style.cssText = "min-height:16px;color:#c8d8e6;overflow-wrap:anywhere";
  panel.append(boundary, select, actions, status);
  root.append(toggle, panel);
  document.body.appendChild(root);

  // Keep clicks on this owner control out of the world's pointer-lock path.
  for (const eventName of ["pointerdown", "mousedown", "click", "dblclick"]) {
    root.addEventListener(eventName, (event) => event.stopPropagation());
  }
  toggle.addEventListener("click", (event) => {
    event.preventDefault();
    const expanded = panel.hidden;
    panel.hidden = !expanded;
    toggle.setAttribute("aria-expanded", String(expanded));
    toggle.textContent = expanded ? "Screen camera / media ▾" : "Screen camera / media ▸";
    if (expanded) updateEmbodiedScreenOwnerControl();
  });
  cameraButton.addEventListener("click", (event) => {
    event.preventDefault();
    if (!directEmbodiedScreenOwnerGesture(event)) {
      embodiedScreenPostState({ requestRejected: "owner_direct_click_required" });
      return;
    }
    const screenId = select.value;
    if (!screenId) {
      embodiedScreenPostState({ requestRejected: "exact_screen_id_required" });
      return;
    }
    void requestEmbodiedScreenAttach(
      screenId,
      `owner-click-${Date.now()}`,
      "owner_direct_click",
      true,
    );
  });
  mediaButton.addEventListener("click", (event) => {
    event.preventDefault();
    if (!directEmbodiedScreenOwnerGesture(event)) {
      embodiedScreenPostState({ mediaAttachRejected: "owner_direct_click_required" });
      return;
    }
    const screenId = select.value;
    if (!screenId) {
      embodiedScreenPostState({ mediaAttachRejected: "exact_screen_id_required" });
      return;
    }
    void requestEmbodiedLibraryMediaAttach(
      screenId,
      `owner-media-click-${Date.now()}`,
      true,
    );
  });
  pauseButton.addEventListener("click", (event) => {
    event.preventDefault();
    if (embodiedScreenRuntime.state === EMBODIED_SCREEN_STATES.PAUSED) {
      void resumeEmbodiedScreen(`owner-click-${Date.now()}`);
    } else {
      void pauseEmbodiedScreen(`owner-click-${Date.now()}`);
    }
  });
  offButton.addEventListener("click", (event) => {
    event.preventDefault();
    turnOffEmbodiedScreen("owner_direct_click", `owner-click-${Date.now()}`);
  });

  embodiedScreenControlElements = {
    root,
    toggle,
    panel,
    select,
    cameraButton,
    mediaButton,
    pauseButton,
    offButton,
    status,
  };
  updateEmbodiedScreenOwnerControl();
  return root;
}

createEmbodiedScreenOwnerControl();

const unloadEmbodiedScreenBridge = () => {
  embodiedScreenRuntime.requestGeneration += 1;
  finalizeEmbodiedScreenPresentation();
  queuedEmbodiedScreenMedia = null;
};
window.addEventListener("pagehide", unloadEmbodiedScreenBridge);
window.addEventListener("beforeunload", unloadEmbodiedScreenBridge);
// CODEX_HOME_WORLD_EMBODIED_SCREEN_BRIDGE_END

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

document.body.addEventListener("click", (event) => {
  if (event.target?.closest?.("#kira-embodied-screen-owner-control")) return;
  renderer.domElement.requestPointerLock();
});
document.addEventListener("mousemove", (event) => {
  if (document.pointerLockElement !== renderer.domElement) return;
  player.yaw -= event.movementX * 0.0024;
  player.pitch = Math.max(-1.35, Math.min(1.35, player.pitch - event.movementY * 0.0024));
});
document.addEventListener("keydown", (event) => {
  keys.add(event.code);
  if (event.code === "KeyE") interact();
  if (event.code === "KeyC") callHomeTardisToUser();
  if (event.code === "KeyB") blueprintPanel.classList.toggle("visible");
});
document.addEventListener("keyup", (event) => keys.delete(event.code));
window.addEventListener("message", (event) => {
  if (event.data?.type === EMBODIED_SCREEN_MEDIA_PREPARE_MESSAGE) {
    if (!embodiedScreenMessageIsTrusted(event)) return;
    prepareEmbodiedScreenLibraryMedia(event.data);
    return;
  }
  if (event.data?.type === EMBODIED_SCREEN_CONTROL_MESSAGE) {
    if (!embodiedScreenMessageIsTrusted(event)) return;
    handleEmbodiedScreenControl(event.data);
    return;
  }
  if (event.data?.type === "kira-voice-playback") {
    setActiveVoicePlaybackState(event.data.playback || {});
    return;
  }
  if (event.data?.type === "kira-observe-follow-toggle") {
    setObserveFollow(!observeFollowEnabled);
    return;
  }
  if (event.data?.type === "kira-observe-follow-set") {
    setObserveFollow(!!event.data.enabled);
    return;
  }
  if (event.data?.type === "kira-request-active-avatar-snapshot") {
    postActiveAvatarSnapshot(clock.elapsedTime, true, String(event.data.requestId || ""));
    return;
  }
  if (event.data?.type !== "kira-shell-state") return;
  const shellState = event.data.state || {};
  // Preserve the legacy shell-state path for world movement, but never let an
  // untrusted state message establish or change a sensory/media person lease.
  if (embodiedScreenMessageIsTrusted(event)) syncEmbodiedScreenPersonBinding(shellState);
  setActiveMarker(shellState);
  syncGroupPresenceOrbs(shellState);
});

animate();

if (HEADLESS_MOTION_SMOKE_ENABLED) {
  const smokeState = {
    active_candidate: "kira",
    active_label: "Kira",
    active_action: "idle",
    active_form: "civilian",
    active_model_url: "/models/temp_ai/kira/avatar.glb",
    location: "home",
    active_resume_position: {
      candidate: "kira",
      location: "home",
      world: "home_world",
      position: { x: -1.261, y: ACTIVE_AVATAR_GROUND_Y, z: 26.27 },
      roamZone: "kira_home_world",
      roamIndex: 61,
    },
  };
  window.kiraHomeWorldDebug.injectShellState(smokeState);
  const smokeStartedAt = performance.now();
  const finishMotionSmoke = () => {
    const stepped = window.kiraHomeWorldDebug.stepActiveAvatarForTest(25, 500);
    const report = {
      schemaVersion: 1,
      mode: "headless_body_only_no_mind_no_voice",
      wallClockModelWaitMs: Number((performance.now() - smokeStartedAt).toFixed(1)),
      activeModelLoaded: !!activeAvatarRoot,
      result: stepped,
    };
    const output = document.createElement("pre");
    output.id = "kira-motion-smoke-result";
    output.textContent = JSON.stringify(report);
    document.body.appendChild(output);
    window.__kiraMotionSmokeResult = report;
  };
  const modelWait = window.setInterval(() => {
    if (activeAvatarRoot || performance.now() - smokeStartedAt >= 8000) {
      window.clearInterval(modelWait);
      finishMotionSmoke();
    }
  }, 100);
}

// CODEX_PHASE_20260703_MOVEMENT_FRONT_DOOR_BEGIN
// Runtime safety pass for the Home World shell. This is intentionally additive:
// it removes the small front-entry blocker if the current build names it, and
// exposes a movement-learning registry for the avatar builder.
(function () {
  const VERSION = "2026-07-06 desktop-model-inventory-roam-limb-v19";

  function getWorldPosition(obj) {
    if (!obj) return { x: 0, y: 0, z: 0 };
    if (window.THREE && obj.getWorldPosition) {
      const v = new window.THREE.Vector3();
      obj.getWorldPosition(v);
      return v;
    }
    return obj.position || { x: 0, y: 0, z: 0 };
  }

  function objectName(obj) {
    return String((obj && (obj.name || obj.userData && obj.userData.name)) || "").toLowerCase();
  }

  function isNamedFrontDoorBlocker(obj) {
    const name = objectName(obj);
    return (
      /front.*(stub|blocker|collision|loose|post|pillar|wall)/.test(name) ||
      /entry.*(stub|blocker|collision|loose|post|pillar)/.test(name) ||
      /foyer.*(stub|blocker|collision|loose|post|pillar)/.test(name)
    );
  }

  function hideObject(obj, reason) {
    obj.visible = false;
    obj.userData = obj.userData || {};
    obj.userData.kiraRemovedBy = VERSION;
    obj.userData.kiraRemovedReason = reason;
    obj.raycast = function () {};
    if (obj.children) {
      obj.children.forEach(function (child) {
        child.visible = false;
        child.raycast = function () {};
      });
    }
  }

  function removeFrontDoorBlocker(scene) {
    if (!scene || !scene.traverse) return 0;
    let removed = 0;
    scene.traverse(function (obj) {
      if (!obj || obj.userData && obj.userData.kiraRemovedBy === VERSION) return;
      if (isNamedFrontDoorBlocker(obj)) {
        hideObject(obj, "named front-entry blocker");
        removed += 1;
      }
    });
    return removed;
  }

  function sceneCandidates() {
    return [
      window.scene,
      window.worldScene,
      window.kiraScene,
      window.kiraWorld && window.kiraWorld.scene,
      window.KiraWorld && window.KiraWorld.scene,
      window.homeWorld && window.homeWorld.scene,
      window.app && window.app.scene
    ].filter(Boolean);
  }

  window.kiraRemoveFrontDoorBlocker = function () {
    return sceneCandidates().reduce(function (total, scene) {
      return total + removeFrontDoorBlocker(scene);
    }, 0);
  };

  function makeDefaultMovementMemory() {
    return {
      version: 1,
      updatedAt: new Date().toISOString(),
      promotedClips: {},
      attempts: [],
      momentDrafts: [],
      notes: [
        "Movement is goal-directed: navigation chooses a target, locomotion clips solve the body motion.",
        "Walk playback is phase-locked to actual meters moved so future bodies inherit distance-driven gait timing.",
        "Door interactions are staged as reach, grip, open, release moments before they are promoted.",
        "Stair practice records individual tread contacts instead of teleporting to the upstairs height.",
        "Body practice includes couch sit, controlled stair-up route, upstairs bed sleep cover, and desk chair/computer attempts; grass lie-down remains manual only.",
        "Avatar-builder validation now uses a bounded self-test battery with reward records instead of an infinite roam loop.",
        "Activity truth checks compare claimed actions against nearby physical props before reading/sketching/computer work is considered grounded.",
        "After a bounded self-test, Marinette waits at the upstairs design workbench instead of returning to a living-room pacing route.",
        "New learned clips should be reviewed, then promoted into Avatar/movement_library for future avatars."
      ]
    };
  }

  function loadMovementMemory() {
    const key = "kira.avatar.movementLearning.v1";
    try {
      return JSON.parse(window.localStorage.getItem(key)) || makeDefaultMovementMemory();
    } catch (err) {
      return makeDefaultMovementMemory();
    }
  }

  function saveMovementMemory(memory) {
    const key = "kira.avatar.movementLearning.v1";
    memory.updatedAt = new Date().toISOString();
    try {
      window.localStorage.setItem(key, JSON.stringify(memory));
    } catch (err) {
      // Local storage may be unavailable in some embedded shells.
    }
  }

  window.kiraMovementLearning = window.kiraMovementLearning || {
    version: VERSION,
    memory: loadMovementMemory(),
    recordAttempt: function (attempt) {
      const item = Object.assign({ at: new Date().toISOString() }, attempt || {});
      this.memory.attempts.push(item);
      if (this.memory.attempts.length > 250) this.memory.attempts.shift();
      saveMovementMemory(this.memory);
      return item;
    },
    recordMomentDraft: function (moment) {
      const item = Object.assign({ at: new Date().toISOString(), trusted: false }, moment || {});
      this.memory.momentDrafts = this.memory.momentDrafts || [];
      this.memory.momentDrafts.push(item);
      if (this.memory.momentDrafts.length > 120) this.memory.momentDrafts.shift();
      saveMovementMemory(this.memory);
      return item;
    },
    promoteClip: function (name, clip) {
      if (!name) return false;
      this.memory.promotedClips[name] = Object.assign({ promotedAt: new Date().toISOString() }, clip || {});
      saveMovementMemory(this.memory);
      return true;
    },
    summary: function () {
      const selfPractice = this.memory.selfPractice || [];
      const lastSelfPractice = selfPractice[selfPractice.length - 1] || null;
      return {
        attempts: (this.memory.attempts || []).length,
        momentDrafts: (this.memory.momentDrafts || []).length,
        promotedClips: Object.keys(this.memory.promotedClips || {}).length,
        selfPracticeRuns: selfPractice.length,
        lastSelfPractice: lastSelfPractice?.summary || null,
        updatedAt: this.memory.updatedAt || null,
      };
    },
    exportForAvatarBuilder: function () {
      return JSON.parse(JSON.stringify(this.memory));
    }
  };

  window.kiraFoundationMotion = window.kiraFoundationMotion || {
    version: VERSION,
    walkGroundedV6: {
      authoredClipSeconds: 2.5,
      runtimeGroundMetersPerSecond: ACTIVE_AVATAR_WALK_SPEED_GROUND,
      runtimeUpstairsMetersPerSecond: ACTIVE_AVATAR_WALK_SPEED_UPSTAIRS,
      strideMeters: ACTIVE_AVATAR_WALK_STRIDE_METERS,
      phaseLockedToDistance: ACTIVE_AVATAR_WALK_PHASE_LOCKED,
      kneeLiftDegrees: 48,
      kneePlantDegrees: 10,
      ankleToeOffDegrees: 20,
      elbowSwingDegrees: 28,
      shoulderSwingDegrees: 18,
      kiraRuntimeArmSwingRadians: 0.082,
      hipCounterRotationDegrees: 5,
      timeScaleRule: "timeScale = authoredClipSeconds / (strideMeters / actualMetersPerSecond)",
      phaseRule: "walk clip time is assigned from actual meters moved; the mixer does not free-run the walk cycle",
      footPlantRule: "support foot stays planted for 52% of the gait cycle; root motion must match strideMeters",
      reviewNote: "Next pass should add true IK contact locks; this pass removes timing drift first."
    },
    handPreviewV3: {
      visibleDebugFingerBones: false,
      preview: "one smoother skinned hand mesh per side is weighted to the hand and finger bones; invisible fingertip colliders provide contact points",
      nextUpgrade: "refine palm topology/skin weights and add object-level finger collision constraints"
    },
    doorHandleReachV2: {
      sequence: ["face_handle", "reach", "finger_grip", "door_rotates", "release"],
      reachSeconds: ACTIVE_AVATAR_DOOR_REACH_SECONDS,
      finishSeconds: ACTIVE_AVATAR_DOOR_FINISH_SECONDS,
      requiredHandDistanceMeters: ACTIVE_AVATAR_DOOR_HAND_TOUCH_METERS,
      learningRecord: "reach/grip/open/release attempts are stored as draft movement moments",
      successRule: "door opens only after the real hand IK pass locks a fingertip contact collider inside the handle threshold"
    },
    handContractV2: {
      digitsPerHand: 5,
      jointsPerFinger: 3,
      controls: ["curl", "spread", "thumbOppose", "pinch", "relax", "handleGrip"]
    },
    stairsStepV2: {
      mode: "step-by-step",
      runtimeTreads: ACTIVE_AVATAR_STAIR_STEPS,
      maxVerticalStepMeters: 0.23,
      requireFootContactBeforePelvisLift: true,
      phaseRule: "avatar y is quantized by stair tread index along the stair run"
    },
    bodyPracticeV1: {
      skills: window.kiraBodyPractice?.skills || [],
      postureClips: ["sit_foundation", "lie_down_foundation"],
      targets: Object.keys(ACTIVE_AVATAR_POSTURE_TESTS),
      furnitureSequences: ["desk_computer"],
      automaticRoute: ["bounded_self_test", "upstairs_design_workbench_wait_after_self_test"],
      manualOnly: ["lie_grass"],
      selfTest: {
        version: "2026-07-04.self-body-test-v1",
        steps: ACTIVE_AVATAR_SELF_TEST_STEPS.map((step) => step.id),
        scoring: "success phases become reward 1.0; known misses/timeouts become reward 0.0; partial starts remain draft moments"
      }
    }
  };
  window.kiraFoundationMotion.walkGroundedV5 = window.kiraFoundationMotion.walkGroundedV6;
  window.kiraFoundationMotion.walkGroundedV4 = window.kiraFoundationMotion.walkGroundedV6;
  window.kiraFoundationMotion.walkGroundedV3 = window.kiraFoundationMotion.walkGroundedV6;
  window.kiraFoundationMotion.stairsRuleV1 = window.kiraFoundationMotion.stairsStepV2;
  window.kiraFoundationMotion.handContractV1 = window.kiraFoundationMotion.handContractV2;

  let tries = 0;
  const timer = window.setInterval(function () {
    tries += 1;
    const count = window.kiraRemoveFrontDoorBlocker();
    if (count || tries > 40) window.clearInterval(timer);
  }, 250);
})();
// CODEX_PHASE_20260703_MOVEMENT_FRONT_DOOR_END
