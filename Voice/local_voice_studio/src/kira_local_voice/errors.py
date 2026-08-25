"""Stable error vocabulary shared by the service and HTTP adapter."""


class VoiceStudioError(Exception):
    code = "voice_studio_error"
    http_status = 400


class ValidationError(VoiceStudioError):
    code = "validation_error"


class NotFoundError(VoiceStudioError):
    code = "not_found"
    http_status = 404


class ConflictError(VoiceStudioError):
    code = "conflict"
    http_status = 409


class CancelledError(VoiceStudioError):
    code = "cancelled"
    http_status = 409


class BackendUnavailableError(VoiceStudioError):
    code = "backend_unavailable"
    http_status = 503


class AuthenticationError(VoiceStudioError):
    code = "authentication_required"
    http_status = 401
