VERDICT: CODE_BUG
slugify("Hello, World!") returns "hello--world". The docstring promises that each *run* of non-alphanumerics becomes a single '-', but the regex `[^a-z0-9]` has no `+` quantifier. The test expectation is correct; fix the regex to `[^a-z0-9]+`.
