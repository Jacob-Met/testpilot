```python path=tests/test_slugify.py
from text_utils import slugify


def test_simple():
    assert slugify("Hello World") == "hello-world"


def test_punctuation_runs_collapse():
    assert slugify("Hello, World!") == "hello-world"


def test_strip_edges():
    assert slugify("  --Rock & Roll--  ") == "rock-roll"


def test_idempotent():
    assert slugify("already-a-slug") == "already-a-slug"
```
