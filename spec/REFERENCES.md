# Research and design references

Inspected on 2026-09-26. This file records evidence, not additional requirements.
[FEATURES.md](FEATURES.md) is authoritative for Alunan behavior.

## Bunyi local source inspection

Reference checkout: `../bunyi-app` relative to this repository. Inspected HEAD:
`eb4b84ecb662263b48185ba255553a5da55d5d85`. The relevant tracked specs and
download files were clean when inspected. Bunyi was read only; no files there
were changed and its tests were not run.

| Reference at the inspected revision | Finding used for Alunan |
| --- | --- |
| [Feature spec](https://github.com/shaztechio/bunyi-app/blob/eb4b84ecb662263b48185ba255553a5da55d5d85/spec/FEATURES.md), model management section | Generate downloads missing models and automatically continues; live receipt feedback, overall/current-file progress, Stop, reconnect, source recovery, and offline reuse. |
| [Data formats](https://github.com/shaztechio/bunyi-app/blob/eb4b84ecb662263b48185ba255553a5da55d5d85/spec/DATA-FORMATS.md) | Completeness includes all required assets, manifests, partial markers, and runtime-specific layouts. |
| [ModelDownloader.cs](https://github.com/shaztechio/bunyi-app/blob/eb4b84ecb662263b48185ba255553a5da55d5d85/apps/dotnet/src/Core/Models/ModelDownloader.cs) | `EnsureModelAsync` checks local completeness before any network operation and returns the ready folder directly. |
| [HttpFileDownloader.cs](https://github.com/shaztechio/bunyi-app/blob/eb4b84ecb662263b48185ba255553a5da55d5d85/apps/dotnet/src/Core/Models/HttpFileDownloader.cs) | `.incomplete` files, HTTP Range, offset checking, whole-file checksums, and completed-file promotion. |
| [DownloadViewModel.cs](https://github.com/shaztechio/bunyi-app/blob/eb4b84ecb662263b48185ba255553a5da55d5d85/apps/dotnet/src/App/ViewModels/DownloadViewModel.cs) | Distinct setup stages, receipt age, rate windows, stall/slow status, elapsed time, and manual reconnect. |
| [MainViewModel.cs](https://github.com/shaztechio/bunyi-app/blob/eb4b84ecb662263b48185ba255553a5da55d5d85/apps/dotnet/src/App/ViewModels/MainViewModel.cs) | Missing-model notice, submitted-input snapshot before preparation, shared cancellation, and guarded late progress. |
| [DownloadServiceTests.cs](https://github.com/shaztechio/bunyi-app/blob/eb4b84ecb662263b48185ba255553a5da55d5d85/apps/dotnet/tests/Core.Tests/DownloadServiceTests.cs) | Retry deadlines, bounded retries, Stop during waits, resumed-file verification, and service errors that must not become missing metadata. Tests inspected, not executed. |
| [ModelDownloadProgress.swift](https://github.com/shaztechio/bunyi-app/blob/eb4b84ecb662263b48185ba255553a5da55d5d85/apps/macos/ModelDownloadProgress.swift) | Swift progress semantics corresponding to the C# experience, with a bounded receipt mailbox and independent rate sampling. |
| [Packaged defaults](https://github.com/shaztechio/bunyi-app/blob/eb4b84ecb662263b48185ba255553a5da55d5d85/spec/PACKAGED-DEFAULTS.md) | Packaged source defaults and user overrides; documentation explicitly tracks a remaining native UI parity follow-up. A spec is not proof every UI detail already matches. |

Adopted behavior: first-use preparation inside Generate; automatic continuation;
actual byte receipts; incremental reuse and range resume; integrity checks;
explicit slow/stalled/waiting states; Stop throughout; offline installed-model use.

Deliberate initial differences: Alunan has curated model profiles rather than
Bunyi's three TTS modes; all endorsed Alunan assets require pinned integrity data;
arbitrary source editing and operating a mirror are deferred. Bunyi can tolerate
custom servers without checksums; Alunan's curated-only MVP has no such legacy
compatibility requirement. No Bunyi source URLs, model files, or host credentials
are copied into Alunan configuration. No implementation code was copied in this task.

## YuE and native-app research

The preceding investigation inspected these primary sources. They describe
candidate capabilities; none establishes a tested Alunan release configuration.

- [YuE repository](https://github.com/multimodal-art-projection/YuE): `main` contains YuE2; the original implementation is preserved on `YuE-v1`.
- [YuE2 generation guide](https://github.com/multimodal-art-projection/YuE/blob/main/docs/generation.md): staged pipeline, saved artifacts, and explicit local-only model loading.
- [YuE2 pipeline](https://github.com/multimodal-art-projection/YuE/blob/main/src/yue2/pipeline.py): CUDA/MPS/CPU selection, local paths, cancellation, and output records.
- [YuE2 model license](https://github.com/multimodal-art-projection/YuE/blob/main/MODEL_LICENSE): weight terms differ from the Apache-licensed code.
- [YuE-v1](https://github.com/multimodal-art-projection/YuE/tree/YuE-v1): original model, hardware guidance, and Apache 2.0 code/weight release.
- [yue2.cpp](https://github.com/ServeurpersoCom/yue2.cpp): community C++ candidate with CLI and HTTP interfaces; a private pipe adapter is still needed for the proposed Alunan architecture.
- [YuE2Mac](https://github.com/arinltte/YuE2Mac): community native Mac app demonstrating an MLX integration; its bootstrap/dependency installation is not Alunan's packaging contract.
- [MPS issue 176](https://github.com/multimodal-art-projection/YuE/issues/176): reported attention correctness problem with the pinned PyTorch runtime; requires independent validation if that path is selected.
- [Gir.Core setup](https://gircore.github.io/docs/get-started.html) and [project status](https://github.com/gircore/gir.core): native GTK libraries remain a packaging responsibility and bindings must be pinned/tested.

Upstream branches can change. Implementation must freeze exact source, dependency,
and model revisions and re-check licenses before producing release packages.

Phase 0 began on 2026-09-26. Exact source/model pins and subsequent local evidence
are now maintained in [the Phase 0 report](../docs/validation/phase0/README.md).
The moving links above are background references, not build inputs.
