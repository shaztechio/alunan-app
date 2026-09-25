# Lagu

A planned free, open-source desktop app for local music generation with YuE.

Native interfaces: WinForms on Windows, GTK 4/Gir.Core on Linux, and Swift on
macOS. The application includes its runtime dependencies and manages its own
generation process. It downloads required models when the user first generates
music, then reuses them offline.

**[The shared feature specification](spec/FEATURES.md) is the source of truth
for observable behavior on every platform.**

- [Data formats](spec/DATA-FORMATS.md): shared projects, model identities, and cache records.
- [Phased implementation plan](spec/IMPLEMENTATION-PLAN.md): eight phases with deliverables, dependencies, acceptance gates, and requirement coverage.
- [Research references](spec/REFERENCES.md): Bunyi download behavior and YuE investigation.

Status: specification and planning only. No application or inference engine has
been implemented or validated in this repository.
