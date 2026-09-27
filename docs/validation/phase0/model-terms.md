# YuE2 model terms review (draft for P0-06)

Date: 2026-09-27. Status: **draft; origin and user-facing terms decided 2026-09-27, other items open**. This records what the
pinned license files say and what they imply for Alunan. It is not legal advice.

## What the files say

| Source (pinned) | Text | Finding |
| --- | --- | --- |
| `m-a-p/YuE2-3B` and `m-a-p/YuE2-Vae` `LICENSE` at the pinned revisions | "YuE2 model-weight license" + unmodified CC BY-NC 4.0 legal code | Weights are CC BY-NC 4.0. No additional permission in these files |
| `Serveurperso/YuE2-GGUF` `LICENSE` at `64b030e3` | Byte-identical to the m-a-p `LICENSE` | The GGUF conversion carries the same terms |
| YuE2 source repository `MODEL_LICENSE` at `72272f90` | Same weight license plus "Individual creator permission and academic use (2026-09-16)" | Adds permissions for individuals (below) |
| `THIRD_PARTY_NOTICES.md` and `licenses/` | stable-audio-tools (Stability AI, MIT) and SnakeBeta/BigVGAN (NVIDIA, MIT) | Code notices to keep with the VAE implementation |

The weight license states that it "does not replace separately applicable
licenses for code, text tokenization files, evaluation assets or other bundled
material".

### Individual creator permission (source repository, 2026-09-16)

- Individuals (personal users, content creators, musicians acting in an
  individual capacity) may generate outputs free of charge and publish,
  distribute, sell, license or otherwise monetize them. The NonCommercial
  restriction is waived for these activities.
- Academic users may use YuE2 for non-commercial research and education.
- Crediting YuE2 on outputs is encouraged but optional; attribution for sharing
  weights or adapted weights still applies.
- It does **not** authorize commercial use of the weights by companies (contact
  the authors for a commercial license) and does **not** extend to commercial
  redistribution or sale of the weights.
- Responsible use is a condition: no illegal, harmful, deceptive or unethical
  use, including fraud, harassment or deceptive impersonation.
- Generated outputs are not subject to the NonCommercial restriction solely
  because they were generated with YuE2.

## Implications for Alunan

| Area | Implication | Where it lands |
| --- | --- | --- |
| Distribution | Alunan never ships weights (APP-006); users download them from the pinned origin. Alunan does not sell the weights. | Consistent with the spec |
| App price | A free, Apache-2.0 app that downloads CC BY-NC weights is compatible with the weight terms as long as the app itself is not a commercial offering of the weights | APP-007 |
| Users | Individuals may monetize their songs under the creator permission; companies using the app commercially need their own license from the YuE2 authors | Help text and model settings (MOD-011, UX-004) |
| Attribution | Show YuE2, model names, source repositories, CC BY-NC 4.0, and the creator permission and responsible-use conditions | Credits (UX-004) |
| Code notices | Include MIT notices for stable-audio-tools and SnakeBeta/BigVGAN with the engine; yue2.cpp and ggml are MIT | Installer notices (P7-01) |
| Responsible use | The conditions bind users; the app should show them before first generation or in model settings | UX decision |

## Open questions and decisions

1. **Tokenizer terms.** `qwen.tiktoken` (151,643 ordinary tokens) is a Qwen
   tokenizer file, also embedded in the GGUF. Its license is not stated in the
   pinned files; identify its origin and terms.
2. **GGUF origin (decided).** The project converts the official weights itself
   and hosts them on its Cloudflare R2 mirror, with Hugging Face as the explicit
   alternate. The conversion is adapted material under CC BY-NC 4.0: host it
   with the LICENSE, notices, attribution and a note of the change, free and
   non-commercial.
3. **Permission coverage.** Confirm with the authors that the individual creator
   permission covers use through the project's GGUF conversion; the model
   repositories' own LICENSE files do not repeat it.
4. **User-facing text (decided).** A one-time acknowledgement before the first
   model download summarizes the license, the creator permission, the
   company-use limit, and the responsible-use conditions, with the full terms
   linked; they stay in model settings and credits (FEATURES.md UX-005).
