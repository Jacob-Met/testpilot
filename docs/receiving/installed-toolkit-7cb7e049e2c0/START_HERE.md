# Install the received TestPilot toolkit

This packet contains an installable wheel for the exact composed source
f27ad21fa1f130e74defdda4403028d3ed11806e, tree
8e1038af7288d1a85f87b666b4b9b4ed774a7179. The ordinary setuptools build preserves
all sixteen Python modules exactly, including bounded output, configuration
isolation, optional live progress and current-main recheck recovery.

It is an explicit review distribution of that source, not a package-index or
installed-estate release. Package version remains 0.1.0. The wheel's SHA256,
source commit and module hashes identify this build; the version string alone
does not distinguish it from an older 0.1.0 installation.

## Install in your own fresh environment

Requires Python 3.12 or later and pytest 8 or later. Coverage measurement is
optional and requires coverage 7 or later. The fixed-response demonstration
also needs Git; it uses no model account or API key.

Create a fresh virtual environment, then use its Python to install the included
wheel. For example, on POSIX from this extracted packet:

```sh
python3.12 -m venv /path/to/new-testpilot-env
/path/to/new-testpilot-env/bin/python -m pip install ./testpilot-0.1.0-py3-none-any.whl
/path/to/new-testpilot-env/bin/python -I -m testpilot --version
/path/to/new-testpilot-env/bin/python -I -m testpilot run --help
```

Normal pip installation resolves pytest if it is absent. If your chosen
environment already provides the required dependency, --no-deps --no-index can
be added for offline installation. Our receiving used an existing read-only
pytest 9.1.1 / coverage 7.16.2 provider and downloaded no dependencies. It did not
change any shared environment. On Windows, use the chosen environment's
Scripts/python.exe path; this packet's executed receiving is POSIX only.

## Run the complete fixed-response example

Use the installed Python to report its site-packages directory:

```sh
/path/to/new-testpilot-env/bin/python -I -c "import sysconfig; print(sysconfig.get_path('purelib'))"
```

Pass that returned directory to the included receiver, with a fresh output
directory outside site-packages:

```sh
/path/to/new-testpilot-env/bin/python -I -B receive_installed_toolkit.py \
  --source /path/reported/above --out /path/to/new-toolkit-review
```

The receiver creates its own small fictional calculator project and fixed
responses. It runs actual installed TestPilot CLI generation, intentionally
repairs one failed generated test, applies the resulting patch to an isolated
adopted project, then rechecks exact retained tests with zero model calls. It
uses -I and no PYTHONPATH for both TestPilot commands. The --source directory is
the installed module identity to verify, not an alternate source import path.

Open the resulting generated/report.html and recheck/recheck.html, or inspect
the JSON reports, saved patch, phase output and receiving.json. The receiver is
a POSIX receiving example: its deliberately noisy native test writes 16 MiB per
execution through the pipe, checks the bounded final diagnostic, and places a
restrictive pytest.ini above native temp files to check configuration isolation.
Original project files and pre-existing adopted files are preserved.

## Actual recorded result

The supplied wheel is 78,834 bytes, SHA256
cdb743f38fc17fd4caee4f3d0d98761cf8495f8992e2cbb5703444674578f54d.
Build tools were Python 3.12.14, setuptools 84.0.0 and wheel 0.48.0. Twenty source
and packaging files match their exact published Git blobs; all sixteen wheel
modules and installed modules match the source before and after execution.

The fresh installation ran outside source with isolated Python. --version
reported 0.1.0 despite deliberately unusable provider configuration. Actual
fixed-response generation made one repair and finished with three native passes,
including the legacy test despite the unrelated ancestor configuration. The
older unisolated-source negative control remains historical evidence; this
installation ran the composed candidate only. The saved patch applied and
native recheck passed all three tests,
with zero model calls. The final diagnostic remained in a 3,000-character saved
tail after each 16 MiB native output. Progress phase notices were received.

The actual saved reports and patch are under examples/installed-run. Their
absolute paths identify the original receiving environment; run the receiver
above to produce fresh paths and files. Its detailed receipt, wheel/build
metadata and source mapping are retained. The first packaging attempt built a
wheel but could not copy it to the full shared filesystem; it stopped before
installation and supplies no consumer result. That setup outcome is kept in the
accepted receipt instead of being described as a test failure.

The source-based refreshed toolkit and the older d2596c1a fourteen-module wheel
under issue #105 remain separate immutable deliveries. This new sixteen-module
wheel qualifies f27ad21f specifically. No Windows, installed-estate, live-provider,
public package-index or scientific-result claim follows from this local course.
