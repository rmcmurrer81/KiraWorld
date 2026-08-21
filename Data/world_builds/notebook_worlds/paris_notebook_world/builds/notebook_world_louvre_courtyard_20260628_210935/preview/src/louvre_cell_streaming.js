/**
 * Fail-closed proximity streaming for the bounded Louvre owner-review slice.
 *
 * A transition is transactional: every destination module is staged, checked
 * for collision readiness and resource budgets, and committed before an old
 * module may unload.  Missing hooks, invalid metrics, or a budget/latency
 * failure leave the last proven loaded set untouched.
 */

function finitePosition(raw) {
  if (!raw || raw.length !== 3) throw new Error("A streaming presence needs exactly three coordinates.");
  const value = raw.map(Number);
  if (!value.every(Number.isFinite)) throw new Error("Streaming presence coordinates must be finite.");
  return value;
}

function monotonicNow() {
  return globalThis.performance?.now?.() ?? Date.now();
}

function distanceToBounds(position, bounds) {
  let squared = 0;
  for (let axis = 0; axis < 3; axis += 1) {
    if (position[axis] < bounds.min[axis]) squared += (bounds.min[axis] - position[axis]) ** 2;
    else if (position[axis] > bounds.max[axis]) squared += (position[axis] - bounds.max[axis]) ** 2;
  }
  return Math.sqrt(squared);
}

const RESOURCE_KEYS = ["asset_bytes", "triangles", "texture_bytes", "draw_calls"];

function finiteNonNegativeMetrics(raw, id) {
  if (!raw || typeof raw !== "object") throw new Error(`Louvre cell ${id} did not declare staged resource metrics.`);
  const metrics = {};
  for (const key of RESOURCE_KEYS) {
    const value = Number(raw[key]);
    if (!Number.isFinite(value) || value < 0) throw new Error(`Louvre cell ${id} has invalid ${key}.`);
    metrics[key] = value;
  }
  return metrics;
}

function addMetrics(total, metrics) {
  for (const key of RESOURCE_KEYS) total[key] += metrics[key];
  return total;
}

function emptyMetrics() {
  return Object.fromEntries(RESOURCE_KEYS.map((key) => [key, 0]));
}

function cloneJson(value) {
  if (value == null) return value;
  return JSON.parse(JSON.stringify(value));
}

export function createLouvreCellStreamingScaffold(contract) {
  if (contract.contract_kind !== "notebook_world_proximity_cell_streaming_contract") {
    throw new Error("Unexpected Louvre cell-streaming contract.");
  }
  if (contract.status !== "streaming_scaffold_only_not_complete") {
    throw new Error("The Louvre streaming contract must remain explicitly incomplete.");
  }
  if (!contract.resource_budgets?.active_set || !contract.resource_budgets?.per_cell) {
    throw new Error("The Louvre streaming contract needs explicit active-set and per-cell resource budgets.");
  }
  const cells = new Map(contract.cells.map((cell) => [cell.id, cell]));
  const loadable = [...cells.values()].filter((cell) => cell.runtime_loadable === true);
  const illegal = loadable.filter((cell) => !cell.bounds_m || !cell.runtime_binding || !contract.resource_budgets.per_cell[cell.id]);
  if (illegal.length) throw new Error(`Loadable Louvre cells lack bounds/bindings/budgets: ${illegal.map((cell) => cell.id).join(", ")}`);
  const registered = new Map();
  const loadedModules = new Map();
  const persistentState = new Map();
  const authorizedCells = new Set();
  let lastTransaction = {
    ok: true,
    phase: "not_started",
    message: "No streaming transaction has run yet.",
    retained_last_proven_cells: [],
    elapsed_ms: 0,
  };
  let transactionTail = Promise.resolve();

  function plan(rawPositions, current = new Set(loadedModules.keys())) {
    const positions = rawPositions.map(finitePosition);
    if (!positions.length) throw new Error("At least one physical presence or owner camera is required.");
    const policy = contract.streaming_policy;
    const eligible = loadable.filter((cell) => !cell.activation_gate || authorizedCells.has(cell.id) || current.has(cell.id));
    const distanceById = new Map(eligible.map((cell) => [
      cell.id,
      Math.min(...positions.map((position) => distanceToBounds(position, cell.bounds_m))),
    ]));
    const desired = [...distanceById]
      .filter(([, distance]) => distance <= policy.load_radius_m)
      .sort((a, b) => a[1] - b[1] || a[0].localeCompare(b[0]))
      .slice(0, policy.max_active_cells_per_presence * positions.length)
      .map(([id]) => id);
    const retained = [...current]
      .filter((id) => !desired.includes(id) && distanceById.has(id) && distanceById.get(id) <= policy.retain_radius_m)
      .sort();
    const target = new Set([...desired, ...retained]);
    const nearbyBlocked = [...cells.values()]
      .filter((cell) => cell.runtime_loadable !== true && cell.proximity_anchor_m)
      .map((cell) => ({
        id: cell.id,
        distance: Math.min(...positions.map((position) => Math.hypot(
          position[0] - cell.proximity_anchor_m.position[0],
          position[1] - cell.proximity_anchor_m.position[1],
          position[2] - cell.proximity_anchor_m.position[2],
        ))),
      }))
      .filter((item) => item.distance <= policy.blocked_cell_notice_radius_m)
      .sort((a, b) => a.distance - b.distance || a.id.localeCompare(b.id))
      .map((item) => item.id);
    return {
      desired_cells: desired,
      load_cells: [...target].filter((id) => !current.has(id)).sort(),
      retain_cells: retained,
      unload_cells: [...current].filter((id) => !target.has(id)).sort(),
      nearby_blocked_cells: nearbyBlocked,
    };
  }

  function registerCell(id, hooks) {
    const cell = cells.get(id);
    if (!cell) throw new Error(`Unknown Louvre cell: ${id}`);
    if (cell.runtime_loadable !== true) throw new Error(`Locked/unbuilt Louvre cell cannot register: ${id}`);
    if (!hooks || typeof hooks.load !== "function" || typeof hooks.preflightUnload !== "function" || typeof hooks.unload !== "function") {
      throw new Error(`Louvre cell ${id} needs explicit load, preflightUnload, and idempotent unload hooks.`);
    }
    if (registered.has(id)) throw new Error(`Louvre cell ${id} is already registered.`);
    registered.set(id, hooks);
  }

  function checkCellBudget(id, metrics, elapsedMs) {
    const budget = contract.resource_budgets.per_cell[id];
    for (const key of RESOURCE_KEYS) {
      const limit = Number(budget[`max_${key}`]);
      if (!Number.isFinite(limit) || metrics[key] > limit) {
        throw new Error(`Louvre cell ${id} exceeds ${key} budget (${metrics[key]} > ${limit}).`);
      }
    }
    if (elapsedMs > Number(budget.max_stage_latency_ms)) {
      throw new Error(`Louvre cell ${id} exceeds stage latency budget (${elapsedMs.toFixed(2)} ms).`);
    }
  }

  function checkActiveSetBudget(targetModules, elapsedMs) {
    const total = emptyMetrics();
    for (const record of targetModules.values()) addMetrics(total, record.metrics);
    const budget = contract.resource_budgets.active_set;
    for (const key of RESOURCE_KEYS) {
      const limit = Number(budget[`max_${key}`]);
      if (!Number.isFinite(limit) || total[key] > limit) {
        throw new Error(`Louvre active set exceeds ${key} budget (${total[key]} > ${limit}).`);
      }
    }
    if (elapsedMs > Number(budget.max_transaction_latency_ms)) {
      throw new Error(`Louvre streaming transaction exceeds latency budget (${elapsedMs.toFixed(2)} ms).`);
    }
    return total;
  }

  async function rollbackStaged(staged, committed = new Set()) {
    for (const [id, record] of [...staged].reverse()) {
      const hooks = registered.get(id);
      try {
        if (committed.has(id) && typeof hooks.rollback === "function") await hooks.rollback(record.module);
        else await hooks.unload(record.module, { rollback: true });
      } catch {
        // A rollback error must not replace the original transition blocker.
      }
    }
  }

  async function applyTransaction(rawPositions) {
    const startedAt = monotonicNow();
    const provenBefore = [...loadedModules.keys()].sort();
    const staged = new Map();
    let stagedRolledBack = false;
    let interest;
    try {
      interest = plan(rawPositions);
      const unloadBatch = interest.unload_cells.slice(0, 1);
      const missing = interest.load_cells.filter((id) => !registered.has(id));
      if (missing.length) throw new Error(`Desired Louvre cells are not registered: ${missing.join(", ")}`);

      for (const id of interest.load_cells) {
        const hooks = registered.get(id);
        const cellStartedAt = monotonicNow();
        const priorState = cloneJson(persistentState.get(id));
        let module = null;
        try {
          module = await hooks.load({
            cell: cells.get(id),
            prior_state: priorState,
            transaction_started_at_ms: startedAt,
          });
          const elapsedMs = monotonicNow() - cellStartedAt;
          if (!module || module.ready !== true || module.collision_ready !== true) {
            throw new Error(`Louvre cell ${id} did not stage ready geometry and collision together.`);
          }
          const metrics = finiteNonNegativeMetrics(module.metrics, id);
          checkCellBudget(id, metrics, elapsedMs);
          if (typeof hooks.validate === "function") await hooks.validate(module, { cell: cells.get(id), prior_state: priorState });
          staged.set(id, { module, metrics, staged_ms: elapsedMs });
        } catch (error) {
          if (module && !staged.has(id)) {
            try {
              await hooks.unload(module, { rollback: true });
            } catch {
              // Preserve the original validation/budget error.
            }
          }
          throw error;
        }
      }

      const peakModules = new Map(loadedModules);
      for (const [id, record] of staged) peakModules.set(id, record);
      checkActiveSetBudget(peakModules, monotonicNow() - startedAt);

      const targetModules = new Map(loadedModules);
      for (const id of unloadBatch) targetModules.delete(id);
      for (const [id, record] of staged) targetModules.set(id, record);
      const precommitElapsedMs = monotonicNow() - startedAt;
      const totals = checkActiveSetBudget(targetModules, precommitElapsedMs);

      // Unload preflight is read-only. At most one source cell is finalized in
      // an atomic transaction; additional stale cells drain through serialized
      // follow-up transactions, so a later failure retains that pass's proven set.
      for (const id of unloadBatch) {
        const record = loadedModules.get(id);
        const hooks = registered.get(id);
        if (record && hooks) await hooks.preflightUnload(record.module);
      }

      const committed = new Set();
      try {
        for (const [id, record] of staged) {
          const hooks = registered.get(id);
          if (typeof hooks.commit === "function") await hooks.commit(record.module);
          committed.add(id);
        }
      } catch (error) {
        await rollbackStaged(staged, committed);
        stagedRolledBack = true;
        throw error;
      }

      // Destination geometry is now visible and collision-ready.  Only now may
      // the prior source cells capture state and unload.
      for (const id of unloadBatch) {
        const record = loadedModules.get(id);
        const hooks = registered.get(id);
        if (!record || !hooks) continue;
        if (typeof hooks.captureState === "function") {
          persistentState.set(id, cloneJson(await hooks.captureState(record.module)));
        }
        await hooks.unload(record.module, { rollback: false });
        loadedModules.delete(id);
        if (cells.get(id)?.activation_gate?.authorization_expires_on_unload === true) authorizedCells.delete(id);
      }
      for (const [id, record] of staged) loadedModules.set(id, record);

      const elapsedMs = monotonicNow() - startedAt;
      lastTransaction = {
        ok: true,
        phase: "committed",
        message: "Destination cells validated and committed before prior cells unloaded.",
        loaded_cells: [...loadedModules.keys()].sort(),
        staged_cells: [...staged.keys()].sort(),
        unloaded_cells: [...unloadBatch],
        retained_last_proven_cells: provenBefore,
        resource_totals: totals,
        elapsed_ms: Number(elapsedMs.toFixed(3)),
      };
      return snapshot(rawPositions);
    } catch (error) {
      if (!stagedRolledBack && staged.size) await rollbackStaged(staged);
      const elapsedMs = monotonicNow() - startedAt;
      lastTransaction = {
        ok: false,
        phase: "blocked_before_source_unload",
        message: error instanceof Error ? error.message : String(error),
        loaded_cells: [...loadedModules.keys()].sort(),
        retained_last_proven_cells: provenBefore,
        elapsed_ms: Number(elapsedMs.toFixed(3)),
      };
      return snapshot(rawPositions);
    }
  }

  function apply(rawPositions) {
    const run = async () => {
      let snapshot = await applyTransaction(rawPositions);
      let remainingPasses = cells.size;
      while (snapshot.transaction.ok && snapshot.interest.unload_cells.length && remainingPasses > 0) {
        snapshot = await applyTransaction(rawPositions);
        remainingPasses -= 1;
      }
      return snapshot;
    };
    const result = transactionTail.then(run, run);
    transactionTail = result.then(() => undefined, () => undefined);
    return result;
  }

  function snapshot(rawPositions) {
    const metrics = emptyMetrics();
    for (const record of loadedModules.values()) addMetrics(metrics, record.metrics);
    return {
      contract_status: contract.status,
      geometry_scope: contract.truth.current_runtime_scope,
      managed_loaded_cells: [...loadedModules.keys()].sort(),
      registered_cells: [...registered.keys()].sort(),
      persistent_state_cells: [...persistentState.keys()].sort(),
      portal_authorized_cells: [...authorizedCells].sort(),
      interest: plan(rawPositions),
      active_resource_metrics: metrics,
      resource_budgets: cloneJson(contract.resource_budgets),
      transaction: cloneJson(lastTransaction),
      transactional_preload_before_unload: true,
      state_preserved_across_reload: true,
      interior_complete: false,
      gallery_rooms_proven: false,
      artwork_proven: false,
    };
  }

  function getLoadedModule(id) {
    return loadedModules.get(id)?.module || null;
  }

  function setPersistentState(id, state) {
    if (!cells.has(id)) throw new Error(`Unknown Louvre cell: ${id}`);
    persistentState.set(id, cloneJson(state));
  }

  function authorizeCell(id) {
    const cell = cells.get(id);
    if (!cell) throw new Error(`Unknown Louvre cell: ${id}`);
    if (!cell.activation_gate || cell.activation_gate.kind !== "explicit_portal_authorization") {
      throw new Error(`Louvre cell ${id} is not portal-authorized.`);
    }
    authorizedCells.add(id);
  }

  function revokeCellAuthorization(id) {
    authorizedCells.delete(id);
  }

  return { contract, plan, registerCell, apply, snapshot, getLoadedModule, setPersistentState, authorizeCell, revokeCellAuthorization };
}
