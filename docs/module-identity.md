# Automatic target module identity

TestPilot maps each changed Python function to an importable module for generated
tests. Its sandbox uses the repository root and, when present, the repository's
`src/` directory as import roots.

Only a leading `src/` is removed from the path when forming the module name.
A directory named `lib` remains part of the package name. A package's
`__init__.py` selects the package itself.

| Selected source | Target module |
| --- | --- |
| `pricing.py` | `pricing` |
| `shop/pricing.py` | `shop.pricing` |
| `src/shop/pricing.py` | `shop.pricing` |
| `lib/pricing.py` | `lib.pricing` |
| `src/lib/pricing.py` | `lib.pricing` |
| `lib/__init__.py` | `lib` |

For example, a changed function in a regular `lib/pricing.py` package is
advertised as `lib.pricing`. If the repository also has a top-level
`pricing.py`, generated tests for the selected function retain the package
identity instead of importing that top-level namesake.

This follows the existing root and `src/` layout support. It does not add
`lib/` as another import root or infer a project's custom packaging rules.
Function selection, changed line numbers, source encoding, and diff path
validation retain their existing behavior.

## Regression

Run the focused native tests with:

```sh
python -m pytest -q tests/test_module_identity.py
```

The regression selects functions through the real diff selector and imports
them in fresh Python processes using the sandbox environment. It checks the
physical module path and the function's result for root modules, regular
packages, `src/` packages, `lib/` packages, a root namesake, and
`lib/__init__.py`. Two additional cases run generated tests through
`run_pytest` and require a passing generated test with native JUnit results.
Every case verifies that the original project files and modes are unchanged.
