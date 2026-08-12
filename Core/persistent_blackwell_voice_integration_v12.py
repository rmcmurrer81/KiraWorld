"""Default-off parent integration for canonical Blackwell V12."""

from __future__ import annotations

from pathlib import Path

from Core.persistent_blackwell_voice_integration_v8 import (
    _static_environment as _v8_static_environment,
)
from Core.persistent_blackwell_voice_integration_v9 import BlackwellV9Coordinator
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v9 import (
    candidate_contract as v9_contract,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12 import (
    candidate_contract as v12_contract,
)


FEATURE_FLAG = "KIRA_ENABLE_BLACKWELL_CANONICAL_TYPED_MEMORY_CANDIDATE_V12"
PRODUCTION_ROUTING_AUTHORIZED = False
LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE = False
PLAYBACK_AUTHORIZED = False


class BlackwellV12Coordinator(BlackwellV9Coordinator):
    """Exact V9 static topology; all V12 live construction remains refused."""

    def __init__(self, process, *, static_fixture: bool) -> None:
        super().__init__(process, static_fixture=static_fixture)
        self.v12_config = v12_contract.load_canonical_config()

    @classmethod
    def production_candidate(cls):
        raise v12_contract.V12ContractError(
            "v12 is not production routing; the approved route remains unchanged"
        )

    @classmethod
    def static_fixture_candidate(cls, *, nonce: str):
        if not v12_contract.is_sha256(nonce):
            raise v12_contract.V12ContractError("static fixture nonce must be SHA-256")
        config = v12_contract.load_canonical_config()
        v12_contract.verify_preserved_bytes(config)
        v12_contract.verify_v11_rejection(config)
        identities = v9_contract.verify_topology_executables(
            v9_contract.load_canonical_config()
        )
        launcher = Path(identities["launcher"]["executable_path"])
        command = (
            str(launcher), "-u", "-m", config["worker_module"],
            "--static-fixture", "--nonce", nonce,
        )
        process = cls._v9_process(
            command=command,
            environment=_v8_static_environment(nonce, startup_descendant=False),
            config=v9_contract.load_canonical_config(),
            nonce=nonce,
            expected_static=True,
            expected_launcher_identity=identities["launcher"],
            expected_worker_identity=identities["worker"],
        )
        return cls(process, static_fixture=True)

    @classmethod
    def bounded_engineering_candidate(cls, **_kwargs):
        raise v12_contract.V12ContractError(
            "v12 authorizes no live run; a separately sealed and audited successor is required"
        )


__all__ = [
    "BlackwellV12Coordinator",
    "FEATURE_FLAG",
    "LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE",
    "PLAYBACK_AUTHORIZED",
    "PRODUCTION_ROUTING_AUTHORIZED",
]
