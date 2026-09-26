# Preliminary dependency and license inventory

Inspected 2026-09-26. This inventory separates upstream license evidence from
release approval. Final native binary dependency closure and license notices are
still required. No installer or model mirror has been approved by this record.

## Engine and model components

| Component | Frozen identity / evidence | Terms and packaging implications |
| --- | --- | --- |
| Official YuE2 0.1.6 | [source lock](source-pins.json), source LICENSE and THIRD_PARTY_NOTICES.md | Apache-2.0 code. Preserve Apache license/notices and identified MIT VAE/SnakeBeta notices. Bundle code at build time. |
| yue2.cpp | `f17d5268…`; inspected LICENSE | MIT. Preserve notice; independent implementation remains a candidate pending parity checks. |
| GGML fork | `765bc96f…`; exact upstream gitlink, inspected LICENSE | MIT; platform backends add their own runtime dependencies. |
| yyjson, cpp-httplib, mp3enc | Vendored at the frozen yue2.cpp revision; notices inspected | MIT notices. HTTP is unnecessary for Lagu's CLI/pipe path. WAV avoids a user-visible MP3 feature, but linked/header-included components still require an inventory. |
| minimp3 | Vendored header at the same revision | Public-domain dedication in header; preserve source provenance. |
| YuE2Mac reference | `a67de3ed…`; LICENSE.txt | MIT app code; MLX engine and model conversion sources need separate review if selected. No code copied into Lagu. |
| YuE2 generator/default VAE | [model lock](model-profiles.lock.json), upstream LICENSE downloaded at immutable revisions | CC-BY-NC-4.0 with additional individual-creator permission. App source licensing does not remove weight restrictions. |
| Q8 GGUF conversion | `Serveurperso/YuE2-GGUF` at `64b030e3…`; model LICENSE identical to official model LICENSE | Adapted weights retain model terms. Identify original sources and conversion/quantization. Verify provenance before release endorsement. |
| Tokenizer/config files | Hashes in reference profile | Do not assume the weight license covers every non-weight artifact; tokenizer provenance/terms require final confirmation. |

Official model license inspected:
[MODEL_LICENSE at the source pin](https://github.com/multimodal-art-projection/YuE/blob/72272f907522dcca2e97c848d6c8f0d343999183/MODEL_LICENSE).
It distinguishes individual output monetization, non-commercial academic use,
and company commercial use. Its additional permission does not extend to commercial
redistribution/sale of weights. Lagu must show these terms separately (APP-007,
UX-004); a free open-source app does not make all model uses unrestricted.

Use the public revision URLs on Hugging Face as research origins. Metadata reported
`gated: false` for both official repositories and the GGUF repository on the
inspection date. Successful small-file retrieval and a partial weight transfer
are availability evidence, not an availability guarantee or final release approval.
Do not create a mirror or redistribute unreviewed model packs during this phase.

## Python reference

The upstream direct pins are torch 2.10.0, transformers 4.57.6, huggingface-hub
0.36.2, safetensors 0.7.0, tiktoken 0.12.0, numpy 2.2.6, soundfile 0.13.1,
and accelerate 1.13.0. Windows research uses Python 3.12.9 and the CUDA 12.8
PyTorch wheel. vLLM and Triton are optional and were not installed for this test.

[Observed distribution lock](windows-python-packages.lock.json) records transitive
versions and artifact SHA-256 values from pip installation reports. It is specific
to Windows/CPython 3.12. Linux and Mac need their own resolved, hashed distributions.
Wheel hashes do not replace the license inventory of native code inside wheels.

PyTorch includes numerous CUDA/cuDNN/BLAS DLLs: inspection found `torch_cuda.dll`,
`cublasLt64_12.dll`, cuDNN engine DLLs, cuSPARSE, cuFFT, and cuSOLVER. Their size and
dependency closure make this a heavier packaging fallback than the proposed C++
worker. The benchmark environment is a developer venv, not proof of a standalone
Lagu install. Python, libsndfile, NumPy BLAS, OpenMP and all native wheel components
need licenses and clean-machine dependency checks if that backend ships.

## Native application/runtime candidates

| Component | Provisional basis | Release work |
| --- | --- | --- |
| .NET 10 / WinForms | LTS; SDK 10.0.401 installed locally | Self-contained publish; preserve .NET third-party notices; pin runtime servicing patch with the build. |
| Gir.Core 0.8.1 | MIT, source `abde56fad65ccc7f4a7fa40c480abd95f67d69c4` | Pin NuGet package closure/hashes in Phase 1. |
| GTK 4 / GLib stack | GTK uses LGPL; dependencies have separate terms | Bundle shared libraries and required resources, preserve notices and satisfy source/relinking obligations for exact builds. Audit Pango/Cairo/Harfbuzz/font and media dependencies. |
| Swift / Apple UI / Metal / Accelerate | Swift toolchain plus operating-system frameworks | Build on a Mac, inspect linked libraries, sign/notarize app and helpers, verify chosen deployment target. |
| MSVC runtime | Windows C++ build dependency; the built binaries import MSVCP140, VCRUNTIME140/140_1 and VCOMP140 (OpenMP) | Use permitted redistributables or validated static runtime strategy; no user-installed build tools. |
| CUDA runtime / cuBLAS | NVIDIA redistributables listed in the [CUDA EULA](https://docs.nvidia.com/cuda/eula/index.html). The CUDA 13.3 C++ build links cudart statically and imports `cublas64_13.dll` (52.7 MB), which needs `cublasLt64_13.dll` (463.7 MB); see [build record](windows-cpp-build.json) | Review the exact toolkit version's redistributable list and ship only permitted required files/notices. GPU driver stays an OS prerequisite. |

Lagu source license: **Apache-2.0**, selected by the user on 2026-09-26 and applied
in [LICENSE](../../../LICENSE). Tokenizer review, native-library versions, and
release redistribution approval remain open P0-06 work. Nothing here grants
rights beyond upstream terms.
