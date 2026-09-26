# Engine feasibility investigation

Date: 2026-09-26. Status: **in progress; no production backend selected**.
Scope: Phase 0. [FEATURES.md](../../spec/FEATURES.md) remains authoritative.

## Direction

Evaluate `yue2.cpp` with Q8_0 generator and F32 decoder as the preferred compact
candidate for Windows/Linux CUDA and macOS Metal. Keep the official YuE2 BF16
pipeline as the numerical and listening reference. This is an evaluation order,
not a claim that the C++ implementation meets Lagu's quality or platform gates.

Initial Windows evidence: the pinned official default `torch` backend fails at
CUDA graph decode because the Windows wheel was built without its required flash
attention. Explicit `torch-eager` completes the short fixture twice and the full
fixture once. Use that
backend for the Windows reference experiments; it does not select the production
worker. See [measured results](../validation/phase0/README.md).

The reference callback probes also expose integration gaps: an already-cancelled
planning call loads the model before checking cancellation, and `decode()` has no
cancellation parameter. Do not treat the Python pipeline alone as satisfying
Lagu's Stop contract. Retain pre-load cancellation checks and bounded process
termination in the planned coordinator/worker design.

The C++ `yue-synth` CLI accepts local model paths and a request file and writes
audio without a server. Its generator GGUF embeds configuration and tokenizer
data. The HTTP server and web UI need not be shipped. A responsive private-pipe
adapter, cancellation protocol, and app supervision remain Phase 3 work.

If Metal fails measured correctness, quality, memory, or latency checks, evaluate
MLX next, with its runtime bundled at build time. YuE2Mac is a source reference,
not a packaging solution: its documented setup requires Homebrew and creates a
Python environment/downloads engine code at first use. Those steps conflict with
APP-002 and MOD-013. Do not adopt that bootstrap flow.

The official pinned PyTorch MPS route remains an unvalidated fallback. Upstream
[issue 176](https://github.com/multimodal-art-projection/YuE/issues/176), open when
checked, reports BF16 causal attention errors with torch 2.10.0. Reproduce and
validate a remedy on a real Mac before selecting this route; do not infer that
successful execution implies correct attention.

## Reproducibility

[Source pins](../validation/phase0/source-pins.json) freeze the inspected engine,
GGML submodule, and Mac reference. [Model profiles](../validation/phase0/model-profiles.lock.json)
freeze required files, canonical revision URLs, exact lengths, and SHA-256 values.
They are research inputs, not a production catalog or redistribution approval.

| Profile | Required asset bytes | Contents |
| --- | ---: | --- |
| Official BF16 reference | 7,794,565,436 | Generator, decoder, configs, tokenizer, weight manifests, notices |
| C++ Q8 candidate | 4,340,749,717 | Q8_0 generator GGUF, F32 decoder GGUF, model license |

Do not equate file size with peak RAM/VRAM. Neither profile includes SheetSage2,
MERT2, alternate quantizations, examples, or downloaded Python source. YuE's
Python modules belong in the packaged engine, not the model cache. Default VAE
is pinned; the legacy benchmark decoder is not silently substituted.

Source archives exclude submodule content. Fetch GGML at its recorded gitlink.
The C++ version generator searches for a parent Git repository: a bare archive
inside this checkout can accidentally embed Lagu's commit. Build from a detached
upstream checkout at the pinned commit or patch the version source explicitly,
and record that patch; never label a candidate binary with an inferred revision.

## Provisional application and packaging baselines

These are engineering candidates to validate, not advertised minimum support.

| Target | Initial baseline | Bundling investigation |
| --- | --- | --- |
| Windows x64 | Windows 11; .NET 10 LTS / WinForms; SDK 10.0.401 available locally | Self-contained .NET publish in a signed installer; C++ runtime and permitted CUDA libraries colocated with worker. Verify on a machine without a toolkit. |
| Linux x64 | Ubuntu 24.04 compatibility target; .NET 10; GirCore.Gtk-4.0 0.8.1; GTK 4.14 API floor proposed | Self-contained .NET plus private GTK/GLib/Pango/Cairo and audio dependencies. Test a self-contained application bundle and installer; package format remains open. No Flatpak/FUSE/runtime installation delegated to user. |
| macOS arm64 | macOS 14+ candidate; Swift 6 toolchain with SwiftUI/AppKit | Signed/notarized app in DMG; bundle engine and any required Swift/native/Python libraries; use OS Metal/Accelerate frameworks. Exact SDK/toolchain awaits Mac access. |

Gir.Core 0.8.1 explicitly targets net8.0/net9.0/net10.0. Its native libraries are
separate dependencies. GTK 4.14 is an API-floor proposal for Ubuntu 24.04, not
proof all bindings work against it. Pin a serviced GTK build and its full closure,
restrict called APIs accordingly, and verify runtime symbol availability in
Phase 1. Avoid relying on distro-installed GTK or a developer's PATH.

CUDA toolkits are build-machine tools. A working GPU driver is the user's machine
prerequisite; redistributable runtime libraries belong in the application package.
Validate exact DLL/SO imports and their license terms before final packaging.

## Decisions still required to close Phase 0

1. Complete native Windows and native Linux C++ builds and short/full-song runs.
2. Compare official and candidate stages/outputs; conduct recorded listening.
3. Obtain an Apple Silicon Mac and test Metal before choosing a Mac backend.
4. Measure startup, memory, repeated jobs, cancellation/failures, and disk peaks.
5. Freeze final dependency binaries/hashes and approve model origins/notices.
6. Agree on quality/latency limits from measurements.

The user selected **Apache-2.0** for Lagu source on 2026-09-26; the full text is
in the repository [LICENSE](../../LICENSE). Model licenses remain separate. See
the [dependency inventory](../validation/phase0/dependencies.md).

## Primary sources

- [Pinned YuE2 source](https://github.com/multimodal-art-projection/YuE/tree/72272f907522dcca2e97c848d6c8f0d343999183)
- [Pinned yue2.cpp CLI and build](https://github.com/ServeurpersoCom/yue2.cpp/tree/f17d5268483db25c9d79a9d53967f9d31fd1ccd3)
- [Pinned YuE2Mac requirements](https://github.com/arinltte/YuE2Mac/tree/a67de3ed5d29d26f24aa85f8f5ed77772a2ffd41)
- [Gir.Core library targets](https://github.com/gircore/gir.core/blob/abde56fad65ccc7f4a7fa40c480abd95f67d69c4/properties/GirCore.Libraries.props)
- [.NET support policy](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core)
- [.NET self-contained publishing](https://learn.microsoft.com/en-us/dotnet/core/deploying/)
- [GTK Linux packaging guidance](https://www.gtk.org/docs/installations/linux/)
