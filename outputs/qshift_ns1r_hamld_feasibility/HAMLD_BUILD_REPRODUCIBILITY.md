# HAMLD build reproducibility gate

## Decision: BUILD BLOCKED in this environment

The pinned HAMLD decoder was **not** built, imported, or decoded. No build command was reported as failed because the required toolchain was absent before invocation. The blocking preflight was:

- Host: Windows 11 Home Single Language, build 26300, x64; AMD Ryzen 7 170, 8 cores / 16 logical processors, 16,312,253,952 bytes RAM.
- WSL2 is installed, but `wsl -l -v` returned no installed Linux distribution. No Docker executable was present.
- No `bazel`, `bazelisk`, C++ compiler (`cl`, `clang`, `gcc`, `g++`), CMake or Ninja command was available. An Oracle Java 8 runtime (`1.8.0_511`) is on PATH, but `javac`/a JDK was not found. Bazel itself was absent; no claim is made that Java 8 would satisfy the chosen Bazel distribution.
- No compiled `hamld_pybind11` `.so` or `.pyd` exists in the pinned upstream tree. `src/hamld/__init__.py` imports `hamld_pybind11` unconditionally.

The package calls for Python `>=3.10,<3.11`; the host's pre-existing Python was 3.12.10. To keep deterministic parser testing isolated, CPython **3.10.18** was installed with uv into an external venv. A pinned parser-only dependency environment is recorded in `parser_environment.lock` (Stim 1.16.0, NumPy 1.26.4, NetworkX 3.4.2, Matplotlib 3.9.4 plus transitive pins). This is not a full HAMLD runtime environment and did not provide the missing extension.

## Upstream build contract inspected

At HAMLD commit `b80c627220773c5b8371fc2753ddf2d4d3773a10`:

- `README.md` specifies Python 3.10, Bazel 8.2.1, recommends Linux for high-performance builds, instructs manual cloning of Abseil, robin-map and robin-hood hashing, and builds `//main:hamld_pybind11` before linking `hamld_pybind11.so` into `src/hamld`.
- The documented Python packaging route installs Hatch and runs `hatch build`; the C++ extension remains a separate Bazel target and must be linked into `src/hamld` before the documented Python import works.
- `pyproject.toml` uses Hatchling and declares unpinned runtime dependencies: Stim, Sinter, NumPy, NetworkX, Matplotlib, Pandas and Jupyter. It includes `src/hamld/*.so`; the actual extension build is a separate Bazel step.
- The PyPI/runtime Stim dependency is unpinned while the C++ WORKSPACE pins a separate Stim commit. No lock file ties the Python Stim wheel/version to the C++ source revision.
- `src/cpp/.bazelrc` selects C++20, disables Bzlmod, enables legacy WORKSPACE, and uses `bazel_downloader.cfg`. That downloader config rewrites GitHub URLs through `ghfast.top`, adding an external mirror to the nominal dependency path.
- The active legacy `WORKSPACE` pins Stim commit `bd60b73525fd5a9b30839020eb7554ad369e4337`, rules_python 0.39.0 and rules_proto 7.1.0 by archive SHA, and pybind11 2.13.6 by archive SHA. Its Abseil archive is tag 20240116.1 without an archive SHA. The README's manually cloned robin-map and robin-hood dependencies are not pinned to commits. Thus a successful build would still need a recorded dependency checkout and mirror/hash verification to be reproducible.
- `MODULE.bazel` declares different Abseil/pybind11_bazel versions, but the committed `.bazelrc` disables Bzlmod and selects WORKSPACE for the documented build. `MODULE.bazel.lock` is therefore not the active lock for that invocation.
- `pyproject.toml` declares MIT while the pinned `LICENSE` file is Apache License 2.0. This metadata discrepancy needs maintainer clarification before packaging or redistribution.
- Although the project metadata labels the package OS Independent, the documented extension build/link instructions are Linux `.so` commands; no verified Windows extension build path was found in the inspected pinned instructions.
- The C++ BUILD targets refer to local `bit_set/robin-map` and `bit_set/robin-hood-hashing` include trees. The checked-in globs allow empty results; the README says to create/populate those directories manually. No upstream commit pins are supplied for those clones.

## Bounded effort and resource record

The bounded attempt covered environment inventory, fetching only the pinned build/source files, installing isolated CPython 3.10.18 and the four pinned parser dependencies, and running a deterministic source-parser round-trip. We did not expand scope to install a Linux distribution, a compiler toolchain, Bazel, or unpinned C++ dependency clones. That would be a materially larger environment setup, and the direct source pin/mirror/metadata issues would still need resolution. No build time, decoder startup time, inference latency or decoder memory measurement exists. Host RAM/CPU figures above are machine specifications, not measured HAMLD requirements.

### Sources inspected

`README.md`, `pyproject.toml`, `LICENSE`, `src/hamld/__init__.py`, `src/cpp/.bazelrc`, `src/cpp/bazel_downloader.cfg`, `src/cpp/WORKSPACE`, `src/cpp/MODULE.bazel`, `src/cpp/MODULE.bazel.lock`, `src/cpp/BUILD`, `src/cpp/main/BUILD`, and `src/cpp/main/hamld_pybind11.cc`, all fetched from the exact upstream commit. Bazel 8 disables WORKSPACE by default absent an opt-in, but HAMLD's `.bazelrc` explicitly enables WORKSPACE and disables Bzlmod for its build ([Bazel 8.2 command reference](https://bazel.build/versions/8.2.0/reference/command-line-reference)).
