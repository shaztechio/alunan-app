@echo off
rem Phase 0 prototype build (research only): the pinned yue2.cpp source with
rem patches\yue-synth-gpu-runtime-dir.patch applied, and ggml-cuda linked with
rem /DELAYLOAD:cublas64_13.dll so cuBLAS loads only when ALUNAN_GPU_RUNTIME_DIR
rem (or, without it, the normal search order) provides it. Expects
rem .phase0\yue2-cpp-proto-src: a copy of the pinned checkout with the patch applied.
setlocal
set ROOT=%~dp0..\..
set SRC=%ROOT%\.phase0\yue2-cpp-proto-src
set BUILD=%ROOT%\.phase0\yue2-cpp-build-runtime-proto
set TOOLS=%ROOT%\.phase0\build-tools-venv\Scripts
if exist "%BUILD%" (echo Refusing to reuse existing build directory %BUILD% & exit /b 1)
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" || exit /b 1
set PATH=%TOOLS%;%CUDA_PATH%\bin;%PATH%
cmake -S "%SRC%" -B "%BUILD%" -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DGGML_CUDA=ON -DGGML_NATIVE=OFF -DCMAKE_CUDA_ARCHITECTURES=89 ^
  "-DCMAKE_SHARED_LINKER_FLAGS=/DELAYLOAD:cublas64_13.dll delayimp.lib" ^
  -DCUDAToolkit_ROOT="%CUDA_PATH%" || exit /b 1
cmake --build "%BUILD%" --target yue-synth -j %NUMBER_OF_PROCESSORS% || exit /b 1
