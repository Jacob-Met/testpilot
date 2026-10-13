# Building and installing TestPilot

TestPilot requires a setuptools backend that accepts the existing SPDX license
string in `pyproject.toml`. The declared build dependency is:

```toml
[build-system]
requires = ["setuptools>=77.0.3"]
build-backend = "setuptools.build_meta"
```

The [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
lists setuptools 77.0.3 for this license metadata support. This is the exact
minimum qualified here. Setuptools documents the feature's introduction in its
[pyproject configuration guide](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html).
The receiving record does not claim that every intervening release was tested.

## Normal installation and package builds

With Python 3.12 or newer, install from the source directory with:

```sh
python -m pip install .
```

To build a wheel without installing TestPilot's runtime dependencies:

```sh
python -m pip wheel --no-deps --wheel-dir dist .
```

Pip's normal build isolation prepares the declared backend separately from the
calling environment. For an offline build, supply a local directory containing
an appropriate setuptools wheel:

```sh
python -m pip wheel --no-index --find-links /path/to/backend-wheels --no-deps --wheel-dir dist .
```

When using `--no-build-isolation`, prepare the compatible backend in the calling
environment yourself. Pip describes that responsibility in its
[build-system interface documentation](https://pip.pypa.io/en/stable/reference/build-system/).

This change updates only the build backend minimum. Python `>=3.12`, runtime
`pytest>=8`, optional `coverage>=7`, the SPDX license, and the
`testpilot = testpilot.__main__:main` console entry point are preserved.

## Qualification

The final receiving used the complete 1,545-file source at
`478f68adf01658a94a3ede22526da00f580785bd`. Two separate real isolated builds used
setuptools 77.0.3, first with the original declaration and then with the corrected
minimum. Both produced the same complete wheel:

- `testpilot-0.1.0-py3-none-any.whl`, 75,408 bytes.
- SHA-256 `3c349ebcbaa48f644bb1b8a6a04efc89da3b1e21105d93581ca6c6a2f5e6c90c`.
- All fourteen current Python modules, including the comparison modules, match
  their source bytes. Both `LICENSE` and `NOTICE` are present with their exact
  original bytes and declared in the wheel metadata.
- All 1,545 input source bytes and modification times are preserved.

An earlier four-build fixture demonstrated that the original declaration admits
setuptools 69, which rejects the existing license format, and that the corrected
declaration refuses an old-only backend depot. That fixture omitted `NOTICE`.
Its original logs and reduced-fixture wheel remain retained with this explicit
scope correction; the final complete-source pair supplies the package
preservation evidence.

The actual build frontend was Python 3.12.14 with pip 26.2.1. These are package
build results. The separately pinned installed Windows CLI receiving and Windows
cancellation course retain their own source identities and qualifications. See
[the complete build receiving record](receiving/build-backend-floor-efcb69c0f058/README.md)
for the unchanged history, correction, hashes and independent review.
