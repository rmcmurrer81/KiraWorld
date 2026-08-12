/*
 * Trusted-build input only.  This forces the exact native anchor source
 * through its V3R29_MATERIALIZED=1 branch for /W4 /WX and /analyze.  Any
 * resulting object or executable is a DO_NOT_RUN analyzer product and has no
 * Audit-A, Audit-B, Blender, body, save, reload, render, or activation authority.
 */
#define V3R29_BINDINGS_HEADER "POST_AUDIT_BINDINGS_MATERIALIZED_ANALYSIS_v3r29.h"
#include "post_audit_native_anchor_template_v3r29.c"
