# Blackwell canonical typed-memory integration candidate V12

V12 is an append-only static successor to rejected V11. It does not trust a
normal import of the V8 live adapter or V10 memory module. Exact sealed source
bytes are read through stable file handles, compiled into private module
objects that never enter `sys.modules`, and bound to their original function,
code, defaults, globals, builtins, closure, loader, spec, and source identity.

Normal module/package poisoning, forged proxies, swapped callables or code,
changed defaults/globals/closures, and source/import TOCTOU fail closed. The
binding revalidates before and after install and every telemetry use. Failed
installation rolls back to the exact original probe or quarantines.

V12 remains default-off and is not production routing. Both parent and worker
refuse live mode. Static tests may load inert definitions and query only the
current process's Windows memory; they may not construct a live backend,
contact Qwen/Ollama, load Torch/CUDA/Chatterbox, synthesize/play audio, or touch
person, body, media, or Blender state. A different fresh audit is required.
