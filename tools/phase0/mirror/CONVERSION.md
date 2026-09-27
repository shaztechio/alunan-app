# YuE2 GGUF conversion for Alunan

These files are an adaptation of the official YuE2 model weights, published for
the free Alunan desktop app. They are distributed non-commercially under the
same terms as the original weights: Creative Commons Attribution-NonCommercial
4.0 International (CC BY-NC 4.0). See `LICENSE`. The YuE2 authors' individual
creator permission and responsible-use conditions are described in the YuE2
source repository's `MODEL_LICENSE`.

## Source

- YuE2-3B by m-a-p: https://huggingface.co/m-a-p/YuE2-3B at revision
  `14fc6c6f146441b1dd6363fcb2e01e82a6914cb7`
- YuE2-Vae by m-a-p: https://huggingface.co/m-a-p/YuE2-Vae at revision
  `9a94e1d0ea9f8087e98f77fa88df4a4068104d2a`

## Changes made

- `YuE2-3B-Q8_0.gguf`: the YuE2-3B weights converted to GGUF with the model
  configuration and the `qwen.tiktoken` tokenizer embedded, then quantized to
  Q8_0 (398 tensors quantized, 229 kept at F32). The sinusoidal
  `latent_pos_embed.pe` table is not stored; the engine rebuilds it.
- `YuE2-Vae-F32.gguf`: the YuE2-Vae weights converted to GGUF in their native
  F32, with tensor names mapped for the engine. Values are unchanged.

Tools: `convert.py` and `quantize` from yue2.cpp
(https://github.com/ServeurpersoCom/yue2.cpp) at commit
`f17d5268483db25c9d79a9d53967f9d31fd1ccd3`, with Python `gguf` 0.19.0 and
`numpy` 2.2.6.

`THIRD_PARTY_NOTICES.md` and `licenses/` are the original notices from the
YuE2 repositories and cover the VAE implementation's source code. The
tokenizer file embedded in `YuE2-3B-Q8_0.gguf` keeps its own terms.
`SHA256SUMS` lists every file's digest.
