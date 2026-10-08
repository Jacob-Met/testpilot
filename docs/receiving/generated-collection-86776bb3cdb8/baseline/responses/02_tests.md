```python path=tests/test_generated.py
from normalizer import normalize

def test_generated_must_run():
    assert normalize(" X ") == "INTENTIONAL_FAILURE"
```
