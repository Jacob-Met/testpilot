# Portable POSIX interruption receiving

The interruption tests exercise real child processes and their inherited output
pipe. They use a random file challenge to establish that the fixture child is
responsive before cancelling the caller, then issue a new challenge only after
the caller has returned.

- A same-group child must not answer the new challenge during the 0.75-second
  observation interval.
- An intentionally detached child must answer after return, demonstrating that
  cancellation did not wait for its pipe to close. It then stops through its own
  fixture control file.
- The caller must observe `KeyboardInterrupt`, return promptly, and have reaped
  its direct child before returning.

Waiting and exiting leaders are both covered. The exit marker is written just
before `SystemExit`, so this covers the exit race rather than proving that the
leader is already dead before cancellation. Each fixture sends about
0.6 MiB through the pipe before interruption. An additional negative control
deliberately omits cleanup; the receiver must reject it.

These observations replace `ps`/procfs PID lookups. Some execution environments
return child IDs from one PID namespace while mounting procfs from another,
which can make a correct interrupted run appear to have no detached child.
Signals from the receiver target only its own `Popen` caller. Child-authored PID
and process-group fields are used to check fixture relationships and for the
caller's native `waitpid` reaping observation, never to signal another process.

Run with the project's pytest environment:

```sh
python -m pytest -q tests/test_sandbox_interrupt.py
```

This is bounded evidence of fixture behavior and cleanup, not containment of
arbitrary escaped processes. The fixture has a ten-second self-expiry for
startup or observation failures. Production sandbox behavior is unchanged.
