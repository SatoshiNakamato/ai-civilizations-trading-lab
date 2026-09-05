# Changelog

All notable changes to this project are documented here.

## [Unreleased]
- Twenty-system civilization dynamics integrated into the autonomous life loop: identity, needs, goals, memory, reflection, relationships, culture, organizations, economy, jobs, contracts, research, experiments, discoveries, reputation, innovation, lineage, migration, governance and endurance.
- Endurance telemetry now distinguishes current RSS from peak RSS on Linux/Android, avoiding false pressure caused by `ru_maxrss` being a peak measurement.
- Normal operation persists state less frequently while still forcing a save at the end of multi-tick runs and during memory pressure.
- Added bounded system-integration tests for contracts, market state, migration, discoveries and the twenty-system registry.
- Release documentation updated for constrained Voroa/mobile environments.
- Live execution remains isolated and disabled by default.

## [0.1.0] - 2026-09-04
### Added
- Continuous civilization runtime.
- Independent agent research and hypothesis scoring.
- Cross-agent challenge and evidence verification components.
- Opportunity ranking and risk governor.
- Deployment policy and Bankr agent integration scaffolding.
- Portfolio, audit, observation, stale-data, replay, and strategy metrics infrastructure.
- Persistent simulation state and dashboard primitives.
