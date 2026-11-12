# HAMLD resource and feasibility record

## Measured work

- CPython 3.10.18 was installed in an isolated uv-managed environment; the parser-only environment pins 14 packages in `parser_environment.lock`.
- Installing the parser-only wheel set took 26.5 seconds as reported by the command process. This is environment setup time, not HAMLD build time.
- The deterministic DEM round-trip script completed successfully on two DEMs (p=0 and .01), 891 error mechanisms total. It performed structural parsing and comparison only. This wall time does not estimate decoder construction or inference.
- Machine: Windows 11 x64, Ryzen 7 170, 8 cores / 16 threads, 16,312,253,952 bytes RAM. No peak-memory instrumentation was applicable because no build or decoder ran.

## Not measured / blocked

No Bazel, Bazelisk, JDK compiler, C++ compiler, CMake/Ninja, Docker, or installed WSL Linux distribution was available. An Oracle Java 8 runtime was present, but no javac/JDK was found. The upstream README documents Linux C++ extension build steps; the pinned source's package initializer requires the resulting extension at import. No reproducible full build, decoder construction, fixture inference, Q-SHIFT inference, build resource use, or runtime measurement is available. Do not extrapolate the parser's 891 mechanism checks into a decoding-cost claim.

## Bounded next build gate

If an authorized follow-up is opened, use a disposable Linux environment with Python 3.10.x, Bazel 8.2.1, a pinned C++ compiler/OpenMP toolchain, and pinned Abseil/robin-map/robin-hood source commits. First reconcile the MIT metadata versus Apache LICENSE and the manual dependency instructions versus WORKSPACE versions. Record and verify the `ghfast.top` downloader mirror or remove it only through upstream-authorized source changes. Build the precise `//main:hamld_pybind11` target, install/link the extension into the isolated pinned checkout, verify import and Python ABI, then run the toy deterministic fixtures. Set a one-day engineering ceiling for that distinct build gate; exceeding it or needing a scientific representation rewrite is a stop condition. This is a proposal, not authorization to install WSL, alter upstream, or run decoding now.
