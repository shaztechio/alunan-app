@echo off
rem Developer research build of the pinned yue2.cpp CUDA candidate (Phase 0).
rem Not a release build. Expects: VS 2022 Build Tools (C++ workload), CUDA
rem toolkit at CUDA_PATH, .phase0\build-tools-venv with cmake+ninja, and a
rem detached .phase0\yue2-cpp-git checkout at the pinned commit + submodule.
setlocal
set ROOT=%~dp0..\..
set SRC=%ROOT%\.phase0\yue2-cpp-git
set BUILD=%ROOT%\.phase0\yue2-cpp-build-cuda-sm89
set TOOLS=%ROOT%\.phase0\build-tools-venv\Scripts
if exist "%BUILD%" (echo Refusing to reuse existing build directory %BUILD% & exit /b 1)
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" || exit /b 1
set PATH=%TOOLS%;%CUDA_PATH%\bin;%PATH%
cmake -S "%SRC%" -B "%BUILD%" -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DGGML_CUDA=ON -DGGML_NATIVE=OFF -DCMAKE_CUDA_ARCHITECTURES=89 ^
  -DCUDAToolkit_ROOT="%CUDA_PATH%" || exit /b 1
cmake --build "%BUILD%" --target yue-synth -j %NUMBER_OF_PROCESSORS% || exit /b 1
