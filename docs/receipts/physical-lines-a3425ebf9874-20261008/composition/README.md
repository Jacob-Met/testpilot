# Current-main composition receiving

The original source and independent review under the parent evidence directories
remain unchanged. Before publication, Python source-decoding PR #15 reached main.
Its implementation and all its tests/receipts are preserved here.

| Item | Exact pin |
| --- | --- |
| Current main parent | `d7c28b0ad261e78d681f40e355447dffa4d435ed` |
| Original independently reviewed source | `caab0c4d2f76f0a410edd9ac5f793b716a938212` |
| Composed source | `a9e8394bfeb8f70bcef61be8db27d249d0701c0b` |
| Preserved original evidence on that source | `2137ee30291af6ad0d5df581e0e7a03c8e62f952` |
| Composed diff.py blob | `f92280a9ad3f9f79713dce7ba7ae28c55414783a` |
| Composed diff.py SHA-256 | `659021d4a4b462b86eadc25957407b683c733fec60ae33c0703295cb7640a06c` |
| Unchanged physical-line regression blob | `d25916fd9bc0cf98647e2678ce942fa6f2d2ba1c` |

The composed file was compared exactly with the actual main file after applying
only the two reviewed line-splitting expressions/comments. The source-decoding
owner's tokenize import, encoding docstring and `tokenize.open` read are
unchanged. No other existing file is modified by the source commit.

A focused native composition run passed **27 tests**: the unchanged twelve
physical-line cases and the encoding owner's fifteen cases. The complete
78-case original qualification was not repeated. This additional receiving
addresses the concrete change to source ingestion since the original review.

Two new authored actual-Git consumers cover a UTF-8 BOM with U+2028 context and
a Latin-1 encoding cookie with U+0085 context. Both fixtures also include the
literal separator inside the changed function. Each compiles the input source,
checks the selected physical span and exact function text, then compiles and
executes the selected source. The same driver **fails both cases on current
main** and **passes both on the composition**. The source and input bytes remain
unchanged.

The fixtures decode their actual Git patch bytes using their known encoding
before calling the existing text-diff API. This is not a claim that the public
CLI accepts arbitrary undecoded Git bytes. The original real scripted CLI and
applied-patch receiving remain separately recorded under `../cli/`.

Replay the two source-composition controls with a new, absent work directory:

```sh
python -B receive_encoding_composition.py \
  --source /path/to/qualified/testpilot \
  --work /path/to/new-disposable-encoding-receiving
```

Expected corrected exit: 0, with both controls passing. The focused suite used:

```sh
python -B -m pytest -q -p no:cacheprovider \
  tests/test_physical_lines.py tests/test_python_source_encoding.py
```

Native Python was 3.14.4. These are authored source/consumer fixtures only, with no
provider, installed runtime, personal input, model evaluation or service action.
The exact source/parent diff and results are in `composition-pin.json`.
