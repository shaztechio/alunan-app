# Workspace relocation (2026-09-26)

The active local repository and Codex project folder is now:

`C:\Users\shazron\Documents\git\github.com\shaztechio\alunan-app`

It replaces `C:\Users\shazron\Documents\git\github.com\shaztechio\lagu-app`.
Codex project configuration confirms the new primary folder. Existing chats may
retain the old working directory: explicitly set the new working directory for
all commands and resolve repository files from this root. Do not resume work in
the old copy. The Phase 0 heartbeat has the same explicit path instruction.

During verification, spec/, docs/, tools/, and .phase0/{runs,yue2,yue2-cpp,yue2-mac}
were missing from the new folder. They were copied from the old folder without
overwriting existing destinations. The old copy was retained; no files deleted.

Research scripts discover the repository root or use relative paths, so no
hardcoded old repository paths needed replacement in specs, tools, or tracked
benchmark reports. Existing chat links and historical logs can still contain
the old absolute path; substitute the root above when locating those artifacts.
Do not rewrite historical measurements or third-party source to rename paths.

The full-song WAV is now at `.phase0/runs/windows-full-eager/take-1/audio.wav`.
Models remain under `.phase0/models/`; do not redownload verified assets merely
because the directory moved. Completed benchmarks do not need to be repeated.

The copied `.phase0/reference-venv` is NOT relocation-qualified: pyvenv.cfg and
activation/launcher files can retain old absolute paths. Recreate the research
venv using the documented pinned dependencies before further inference work;
do not treat a working interpreter alone as proof the whole environment moved.
No environment recreation or new inference was performed for this relocation.

The user subsequently confirmed the GitHub repository rename on 2026-09-26.
The Git remote is now `git@github.com:shaztechio/alunan-app.git`, and the root
README uses Alunan. Historical evidence, proposed namespaces, and persisted-format
identifiers retain their existing names pending a separate contract-wide rename.
