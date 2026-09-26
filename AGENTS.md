# Lagu repository guidance

Phase 0 feasibility work is authorized and in progress. The repository contains
specifications and developer research tools; native application implementation
has not started. Keep Phase 0 experiments separate from production app code.

- Read `spec/FEATURES.md` before changing observable behavior. It is the shared
  source of truth for Windows, Linux, and macOS.
- Update the specification first when changing a feature. Keep requirement IDs
  stable and update the corresponding acceptance scenarios.
- `spec/DATA-FORMATS.md` defines shared persisted contracts;
  `spec/IMPLEMENTATION-PLAN.md` records engineering decisions and open questions.
  Neither should introduce product behavior that conflicts with the feature spec.
- Record platform differences explicitly in the shared specification. A feature
  implemented on one platform is not complete across platforms until the other
  implementations pass its acceptance scenarios or have a documented exception.
- Treat bunyi-app as a read-only reference unless separately authorized to edit it.
- Preserve the requested UI stack: Windows WinForms, Linux GTK 4/Gir.Core, macOS
  Swift with native Apple UI frameworks.
- Bundle runtime dependencies. Models are downloaded on demand by the app;
  users must not manage terminals, dependency installers, or inference servers.
- Keep research weights, environments, source checkouts, and generated audio in
  ignored `.phase0/`. Track compact measurements, source/model pins, and findings
  under `docs/validation/phase0/`; never count missing hardware as passing.

## Active workspace

The repository moved to `C:\Users\shazron\Documents\git\github.com\shaztechio\alunan-app`.
Use that explicit working directory if this chat still starts in `lagu-app`.
Read `docs/workspace-relocation.md` before resuming Phase 0; the copied research
venv must be recreated before further inference. Keep historical evidence intact.
