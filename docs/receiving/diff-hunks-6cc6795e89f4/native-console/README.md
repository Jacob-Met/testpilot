# TestPilot: qualified native build on ThinkPad

The installed project console command is:

```
/home/jacob/testpilot-native-6cc6795e89f4/40860534a8fd/bin/testpilot
```

This versioned environment installs the project's declared `testpilot.__main__:main` entry point from source commit `40860534a8fdc760b105ac9bc7d14ac9087172dd`. The source includes canonical TestPilot main `cec50d8df4499ba509615e179d82ef3861379bd2` and the received complete-hunk input boundary. Native Python is 3.14.4; the environment uses the recorded system pytest 9.0.2. All eleven installed Python source files match the exact Git archive.

To inspect the retained real Git example:

```
/home/jacob/testpilot-native-6cc6795e89f4/40860534a8fd/bin/testpilot targets --repo /home/jacob/testpilot-native-6cc6795e89f4/receiving/project --git-base HEAD --json
```

To inspect the supported native commands:

```
/home/jacob/testpilot-native-6cc6795e89f4/40860534a8fd/bin/testpilot --help
```

The actual local ScriptedModel receiving run generated and executed one passing test. Its report is `receiving/valid-result/report.html` (also JSON and Markdown), with the emitted patch alongside it. The changed sample function and authored replies remain in `receiving/project` and `receiving/script`. No live provider call or paid inference was used.

The damaged-diff receiving cases exited 2 before loading a nonexistent model configuration. They preserved every successful result file and created no new result directory. `receiving/receiving.json` and the raw console outputs retain those observations.

`artifacts/installation.json` records the exact Git tree, source archive, built wheel, installed source hashes, interpreter, entry point and offline build/install commands. The wheel SHA-256 is `83c756b33833e004c6421c203888c54862a4eb4995dba1e08bfea3128dec9c4b`.

The source contribution and its receiving history live at `/home/jacob/testpilot-hunks-integration-6cc6795e89f4`; canonical source publication is coordinated separately by the parent worker. This versioned installation is directly runnable by its absolute command path.
