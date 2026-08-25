"""Local-only, backend-neutral voice generation contracts for Kira Labs."""

from .models import (
    AuditionStatus,
    ConsentBasis,
    ConsentRecord,
    JobState,
    SourceBasis,
    SynthesisRequest,
    VoiceProfile,
)
from .service import LocalVoiceService
from .approved_starter_release import ApprovedStarterRoute, ApprovedStarterVoiceRelease
from .avatar_voice_integration import (
    AvatarTemporaryCreatorVoiceIntegration,
    build_live_avatar_voice_plan,
)
from .candidate_audio_queue import CandidateAudioQueue
from .runtime_resolver import ExactRuntimeVoiceResolver
from .temporary_creator_adapter import TemporaryCreatorVoiceAdapter
from .voice_design import (
    AgeBand,
    AssignmentMode,
    AvatarSourceAttestation,
    BodyPresence,
    EraContext,
    Gender,
    IdentityKind,
    LanguageProvenance,
    VoiceDesignBrief,
    VoiceDesignEngine,
    VoiceDesignStore,
)

__all__ = [
    "AuditionStatus",
    "AgeBand",
    "AssignmentMode",
    "AvatarSourceAttestation",
    "AvatarTemporaryCreatorVoiceIntegration",
    "ApprovedStarterRoute",
    "ApprovedStarterVoiceRelease",
    "BodyPresence",
    "CandidateAudioQueue",
    "ConsentBasis",
    "ConsentRecord",
    "EraContext",
    "ExactRuntimeVoiceResolver",
    "Gender",
    "IdentityKind",
    "JobState",
    "LanguageProvenance",
    "LocalVoiceService",
    "SourceBasis",
    "SynthesisRequest",
    "TemporaryCreatorVoiceAdapter",
    "VoiceDesignBrief",
    "VoiceDesignEngine",
    "VoiceDesignStore",
    "VoiceProfile",
    "build_live_avatar_voice_plan",
]
