# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant **custom integration** (HACS, `integration_type: service`) that routes weight readings from an existing weight-sensor entity to the correct household member. It owns no hardware: it subscribes to a source sensor's state changes, matches each reading against per-user weight history, and either auto-assigns it or holds it as a *pending* measurement and asks the user (mobile actionable notification + persistent notification).

All code lives under `custom_components/multi_user_scale_router/`. The matching/tolerance logic is **not** in this repo — it's the pip dependency `multi-user-scale-core` (pinned in `manifest.json` and `requirements.txt`), imported as `multi_user_scale_core` (`WeightRouter`, `WeightMeasurement`, `UserProfile`, `RouterConfig`, `MeasurementCandidate`, errors). This repo is the HA glue around that engine.

## Commands

```bash
# Lint + format (CI runs these on every push/PR — see .github/workflows/lint.yaml)
ruff check .
ruff format . --check     # use `ruff format .` to apply

# Validate HACS metadata / manifest (mirrors CI; requires Docker)
# .github/workflows/{validate,hassfest}.yaml run these via GitHub Actions.
```

There is **no test suite** in this repo (logic that would be unit-tested lives in `multi-user-scale-core`). Ruff (config-less, defaults) is the only enforced check besides hassfest/HACS validation. Python 3.12, minimum HA `2024.1.0`.

The `.venv` has both `multi_user_scale_core` (to inspect the engine's API) and `homeassistant` installed. The latter means `coordinator.py` can be imported and driven directly, which is the only practical way to verify a change to the capture pipeline. Write a throwaway script that: builds real `homeassistant.core.State` objects (set `last_updated`/`last_changed` **in the past**, otherwise the freshness window rejects everything); passes a fake `hass` exposing `.states.get()`; monkeypatches `coordinator.async_call_later` to neutralize the settling timer; and monkeypatches `router.evaluate_measurement` to capture the resulting `WeightMeasurement`. Feed events through `_async_handle_source_update`, then call `_async_capture_and_route_pending()` by hand. Run the same script against `git stash` to confirm the old behaviour actually failed.

## Architecture

The data flow has one central object, `RouterRuntime` (`coordinator.py`), created per config entry in `async_setup_entry` and stored in `hass.data[DOMAIN][entry_id]` (also aliased under `hass.data[DATA_ROUTER]`). It is the single source of truth and the bridge between HA callbacks and the core engine.

**Capture pipeline** (`coordinator.py`, the heart of the integration):
1. `async_track_state_change_event` on the source sensor → `_async_handle_source_update`. Noise/duplicate events (no meaningful weight or tracked-attribute change, unit-only changes) are filtered here.
2. Updates are **debounced** into a `PendingCapture` for `settling_delay` seconds (default 2.0); each accepted update resets the timer. Within a burst, the winning value is the heaviest or lightest depending on `capture_strategy` (default `highest`, which defeats trailing "step-off" readings). This is *not* the same thing as a pending *measurement*.
3. On settle, `_async_capture_and_route` snapshots tracked metrics, applies a freshness window so stale sibling/attribute values are dropped, builds a `WeightMeasurement`, and calls `router.evaluate_measurement`.
4. Candidates are filtered by location (`_filter_user_ids_by_location` excludes only people whose linked `person.*` is exactly `not_home`, with a fallback to all users if filtering empties the list). One candidate → auto-record. Multiple → `_store_pending_measurement`.

**Pending measurements** (ambiguous readings, capped at `MAX_PENDING_MEASUREMENTS`) live only in `RouterRuntime._pending_measurements`. Each spawns a persistent notification *and* per-candidate actionable mobile notifications. They are resolved by:
- Mobile notification action → `mobile_app_notification_action` bus event → listener in `__init__.py` (`_register_mobile_action_listener`). Actions are encoded as `ROUTER_ASSIGN_<entry>|<measurement>|<user>` / `ROUTER_NOT_ME_...` (URL-quoted parts, `|` delimiter); see `_decode_router_action`.
- Service calls (below).

**State persistence:** the entire engine state is serialized via `router.to_dict()` and written back into the **config entry's `data`** under `CONF_ROUTER_STATE` (`persist_router_state`). There is no separate storage file — config-entry data *is* the database. Anything that mutates history must call `persist_router_state()`.

**Services** (`__init__.py` `_register_services`, schemas at top of file, definitions in `services.yaml`): `assign_measurement`, `reassign_measurement`, `remove_measurement`, `move_measurement_component`, `remove_measurement_component`. All take a `device_id` and resolve the runtime via the device registry (`_get_runtime_for_call`). The `*_component` services operate on `weight` vs `tracked_metric` (the latter keyed by `metric_key`, auto-selected when only one exists). Validation errors raise `HomeAssistantError` with the valid options inlined so the user can copy/paste.

**Config flow** (`config_flow.py`): unique-id is the source entity id (one router per source sensor). Setup picks a source sensor (filtered/scored by `_source_sensor_relevance_score` — weight device_class and "weight"/"scale" in name rank higher), optional tracked metrics, then adds users. Options flow is a menu (add/edit/remove user, router settings) and **reloads the entry** on every change. `_sync_router_state` re-serializes engine state when config changes so users/config stay in sync with stored history.

**Sensors** (`sensor.py`): per user, a `RouterUserWeightSensor` plus one sensor per tracked entity/attribute; two diagnostic sensors (`Pending Measurements`, `User Directory`). Sensors are push-based — they register listener callbacks on the runtime (`add_listener`/`add_diagnostic_listener`) and the runtime calls `_notify()` after mutations. Tracked-attribute sensors infer unit/device_class/icon from the **key name** (e.g. `impedance`→Ω, `fat`/`water`→%, `bmr`→kcal).

**Repairs** (`repairs.py`): `async_scan_repair_issues` runs at setup (deferred via `async_at_started` so `notify.mobile_app_*` services are registered first) and surfaces config drift on Settings → Repairs — broken `person_entity` links and missing `notify` services. Read the module docstring before touching it: it documents exactly which issues are fixable and why (the location filter only excludes on exact `not_home`, so broken links degrade rather than break routing).

## Conventions specific to this codebase

- **Units:** the engine and all stored data are in **kilograms**. `display_unit` is derived at the edge (from the source sensor's `unit_of_measurement`, falling back to pending/history); conversion happens only on display via `display_weight_value` / `format_weight`. Don't store pounds.
- **User profiles** are dicts in `entry.data["users"]` with keys `user_id` (slugified from display name), `display_name`, optional `person_entity`, optional `mobile_notify_services`. By convention optional keys are **omitted when empty**, not stored as null/empty — preserve this when mutating profiles (see `_build_user` and the repair fix flows).
- **Tracked metrics** come in two kinds, distinguished by a `.` in the value: an entity id (`sensor.foo`, a sibling on the same device) → `tracked_entities`; otherwise a source-sensor attribute name → `tracked_attributes` (lowercased). Stored on each measurement's `raw` payload under those two dict keys.
- The runtime guards heavily against partial/odd `hass` objects (`getattr(hass, "services", None)`, `hasattr(...)`) because it's exercised with lightweight fakes; keep new HA interactions similarly defensive.
- Bump `version` in `manifest.json` for any user-facing change (the recent git history is almost entirely version bumps accompanying fixes).

## Idioma

Responda sempre em português do Brasil.

## Regras Gerais

- Tome cuidado para não quebrar o que já está funcionando;
- Os comites não será você que irá fazer;
