# Cancelling an active test subprocess

On POSIX systems, a KeyboardInterrupt received while TestPilot is communicating with an active test subprocess now stops that subprocess's process group before propagating the interrupt. This covers pytest launched by the ordinary run and saved-test recheck paths, and commands using the same sandbox runner.

TestPilot starts the subprocess in a new session. The cancellation handler sends SIGKILL to that launched process group, waits up to one additional second to reap its leader, closes the output pipe, and re-raises KeyboardInterrupt. It does not wait for stdout to reach EOF: a helper that has deliberately created a separate session may still hold the pipe open. Python's own brief interrupt wait and ordinary scheduling overhead are additional to the one-second leader-wait bound.

The interrupt remains an exception. It is not returned as a successful run or converted into a timeout result. The run CLI does not reach its normal report-publication step for that interrupted attempt. Earlier test effects or model calls are not rolled back. Process termination does not guarantee that test teardown code runs.

## Boundaries

The process group created by the sandbox is the cancellation boundary. A helper that leaves that group is outside this cleanup; the sandbox remains process-level isolation, not a security boundary. An already-exited leader does not exempt children that remain in its group.

This change applies to KeyboardInterrupt during the sandbox's initial subprocess communication on POSIX. It does not add SIGTERM or SIGKILL handling, cover interruption before the subprocess is created, change Windows signal behavior, or change the existing timeout result and output-drain rules. If the operating system refuses cleanup or the leader cannot be reaped within the bounded wait, the original cancellation still propagates.

## Receiving evidence

The native receiver uses an isolated Mac fixture with the repository's existing Python language and an already installed pytest interpreter. A real SIGINT targets only the fixture's TestPilot caller. The original CLI returns while its separately launched pytest later completes work; the uninterrupted ScriptedModel control succeeds.

The focused regression cases exercise a live and an already-exited leader with a same-group child. Equivalent detached-session cases preserve the explicit containment limit and ensure the caller does not wait for a retained pipe. The fixture owns every signaled process, binds cleanup to its unique script paths and recorded process groups, and gives its workers finite lifetimes.

The original executed source is pinned separately from the current-main composition. The current parent includes the merged report-staging implementation unchanged. Exact source hashes, native commands, retained failures, candidate results and scope limits are recorded under [the cancellation receipt directory](receipts/run-cancellation-18a24bf0c281/).
