# Independent TestPilot targets receiving

The exact frozen candidate passed 34 conditions over five candidate CLI cases, paired with five baseline children. The old parser leaves 11 conditions unsatisfied. The baseline and candidate existing-run dispatch controls match exactly.

`review.json` records source/support custody and the review disposition. `results.json` preserves every actual child output, tripwire/process trace, selected native record and check. `receive_targets.py` creates its own disposable Git repository and repeats only this receiving boundary:

```sh
python -B receive_targets.py --baseline /path/to/baseline --candidate /path/to/candidate --out /path/to/new-results.json
```

The receiver refuses source/support pins other than the reviewed baseline and candidate. It uses no authored test suite, model/provider, pytest or live service. Run-dispatch consumers are declared doubles; preview selection and Git are native. Source trees are unchanged.
