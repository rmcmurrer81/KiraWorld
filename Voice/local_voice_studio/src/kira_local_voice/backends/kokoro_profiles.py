"""Owner-auditioned built-in Kokoro declarations; no identity/reference claim."""
from ..models import AuditionStatus, ConsentBasis, ConsentRecord, SourceBasis, VoiceProfile

def builtin_kokoro_profiles() -> tuple[VoiceProfile, ...]:
    # Date-level owner listening approval supplied in America/New_York.
    approval_at="2026-08-25T00:00:00-04:00"
    def make(voice_id, display, description):
        return VoiceProfile(voice_id=voice_id,display_name=display,source_basis=SourceBasis.GENERIC_FALLBACK,
            audition_status=AuditionStatus.OWNER_APPROVED,language="en-US",description=description,
            consent=ConsentRecord(basis=ConsentBasis.GENERIC_NO_IDENTITY,subject_id="no-human-identity-claim",
                authority="Kira Labs built-in upstream voice policy",scope="Local built-in Kokoro synthesis only",
                recorded_at=approval_at,evidence_sha256=None,reference_recording_permitted=False,
                generated_audio_permitted=True,revocable=True))
    approved = "Built-in upstream voice; product-owner sound audition approved; no identity or cloning claim."
    return (make("af_heart","Kokoro Heart — calm female",approved),
            make("am_fenrir","Kokoro Fenrir — warm male",approved))
