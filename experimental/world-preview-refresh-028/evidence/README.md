# Current saved-preview presentation028

The explicit native button is now labelled **Open current preview**. It validates
the saved job and selected immutable preview, then creates or reuses a separate
preview with the currently installed presentation assets. It uses exactly the
saved geometry, blueprint, research packet and cache bindings. No research,
planner, model, saved-layout state or selected pipeline pointer is changed.
Historical previews keep their exact renderer/assets. Native output says the
result is a prototype and explains preservation without claiming final quality.

The fresh server owns the refresh and the loopback lifetime. Its startup timeout
is32 seconds to accommodate the existing20-second Node preflight maximum. There
is no polling or automatic generation worker. Concurrent metadata/selection
changes, tampered/missing bindings, unsupported jobs and build failures fail
closed while retaining old data. Reopening the unchanged result reuses its
content-addressed manifest.

Fourteen tests use synthetic jobs and actual preview builders with real Node
navigation preflight. They exercise changed renderer assets, stable reuse,
metadata and source rejection, failure preservation, concurrent selection
changes, the real server main callback and the extracted native button method.
They do not open a browser, call models or touch owner data. The original source
files are retained under baseline. Installed native visual review is pending.
