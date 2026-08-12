"""Default-off parent integration for Blackwell typed-memory candidate v11.

This module preserves the exact v9 dual-process Windows topology and v8
semantic worker.  It only changes the worker module to the v11 shim that can
install the separately accepted v10 pointer-width memory probe.  Importing the
module is inert; production routing and live execution remain unauthorized.
"""

from __future__ import annotations

from pathlib import Path

from Core.persistent_blackwell_voice_integration_v8 import (
    _static_environment as _v8_static_environment,
)
from Core.persistent_blackwell_voice_integration_v9 import BlackwellV9Coordinator
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v9 import (
    candidate_contract as v9_contract,
)
from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v11 import (
    candidate_contract as v11_contract,
)


FEATURE_FLAG = "KIRA_ENABLE_BLACKWELL_TYPED_MEMORY_INTEGRATION_CANDIDATE_V11"
PRODUCTION_ROUTING_AUTHORIZED = False
LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE = False
PLAYBACK_AUTHORIZED = False


class BlackwellV11Coordinator(BlackwellV9Coordinator):
    """V9 topology with the audited v10 memory repair installed in-child."""

    def __init__(self, process, *, static_fixture: bool) -> None:
        super().__init__(process, static_fixture=static_fixture)
        self.v11_config = v11_contract.load_canonical_config()

    @classmethod
    def production_candidate(cls):
        raise v11_contract.V11ContractError(
            "v11 is not production routing; the approved route remains unchanged"
        )

    @classmethod
    def static_fixture_candidate(cls, *, nonce: str):
        if not v11_contract.is_sha256(nonce):
            raise v11_contract.V11ContractError("static fixture nonce must be SHA-256")
        config = v11_contract.load_canonical_config()
        v11_contract.verify_preserved_bytes(config)
        v9_config = v9_contract.load_canonical_config()
        identities = v9_contract.verify_topology_executables(v9_config)
        launcher = Path(identities["launcher"]["executable_path"])
        command = (
            str(launcher), "-u", "-m", config["worker_module"],
            "--static-fixture", "--nonce", nonce,
        )
        process = cls._v9_process(
            command=command,
            environment=_v8_static_environment(nonce, startup_descendant=False),
            config=v9_config,
            nonce=nonce,
            expected_static=True,
            expected_launcher_identity=identities["launcher"],
            expected_worker_identity=identities["worker"],
        )
        return cls(process, static_fixture=True)

    @classmethod
    def bounded_engineering_candidate(cls, **_kwargs):
        raise v11_contract.V11ContractError(
            "v11 is static integration only and does not authorize a live run; "
            "a separately sealed and audited successor harness is required"
        )


__all__ = [
    "BlackwellV11Coordinator",
    "FEATURE_FLAG",
    "LIVE_EXECUTION_AUTHORIZED_BY_THIS_MODULE",
    "PLAYBACK_AUTHORIZED",
    "PRODUCTION_ROUTING_AUTHORIZED",
]
