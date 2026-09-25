# Lagu repository guidance

This repository currently contains planning documents only. Do not start
application implementation unless the user requests it.

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
