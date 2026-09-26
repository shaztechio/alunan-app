# Alunan

Local workspace: **alunan-app**. See the [relocation note](docs/workspace-relocation.md)
for the active path, recovered files, and research environment follow-up.

A planned free, open-source desktop app for local music generation with YuE.
Website: [alunan.app](https://alunan.app/) (see [docs/README.md](docs/README.md)).

Native interfaces: WinForms on Windows, GTK 4/Gir.Core on Linux, and Swift on
macOS. The application includes its runtime dependencies and manages its own
generation process. It downloads required models when the user first generates
music, then reuses them offline.

**[The shared feature specification](spec/FEATURES.md) is the source of truth
for observable behavior on every platform.**

- [Data formats](spec/DATA-FORMATS.md): shared projects, model identities, and cache records.
- [Phased implementation plan](spec/IMPLEMENTATION-PLAN.md): eight phases with deliverables, dependencies, acceptance gates, and requirement coverage.
- [Research references](spec/REFERENCES.md): Bunyi download behavior and YuE investigation.
- [Phase 0 findings](docs/validation/phase0/README.md): test hardware, evidence, and remaining feasibility gates.
- [Engine decision record](docs/decisions/0001-engine-feasibility.md): candidate engines and packaging baselines.

Status: Phase 0 feasibility investigation in progress. Native applications have
not been implemented, and no platform is release-qualified.

Alunan source is licensed under [Apache-2.0](LICENSE). Model weights and third-party
components retain their separate terms; see the [dependency inventory](docs/validation/phase0/dependencies.md).
