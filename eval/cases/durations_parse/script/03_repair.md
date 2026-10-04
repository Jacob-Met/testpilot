VERDICT: CODE_BUG
The run timed out, and the only input containing a space is "1h 30m 5s". In parse_duration the `elif ch == " ": continue` branch never increments `i`, so the loop spins forever on the first space. The docstring says spaces are allowed, so the test is right; the branch needs `i += 1`.
