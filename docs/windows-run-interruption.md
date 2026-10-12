# Windows interruption cleanup

When `testpilot.sandbox._run` has launched a Windows child and its initial
`communicate` call raises `KeyboardInterrupt`, it attempts to terminate that
launched process and wait for its exit for at most one second. It then raises
the original interruption object. An `OSError` or `subprocess.TimeoutExpired`
during this cleanup does not replace the cancellation.

The cleanup owns the process represented by that `Popen` handle. It does not
terminate a Windows process group, traverse a process tree, or promise to stop
a descendant that retained the output pipe.

The Windows cancellation arm does not close, drain or join the buffered output
reader. A communication reader thread can own that reader's lock while another
process retains a pipe writer; closing the stream there could wait for EOF and
delay the caller's cancellation. Such a helper can continue to run after the
launched leader has exited. A caller that needs stronger process-tree isolation
must supply that isolation outside this helper.

This behavior applies to an interruption raised during the initial communication
call after successful process creation. It does not establish hardware Ctrl-C,
CTRL_BREAK, a shared-console signal route, or behavior before `Popen` returns.
The timeout arm is unchanged, including its existing Windows behavior.
The POSIX process-group cancellation contract is separate and remains described
in [run-cancellation.md](run-cancellation.md).

The focused maintained regression tests use controlled communication exceptions
and explicit mocks for cleanup ordering, bounded wait, exception identity and
reader preservation. Native receiving uses an actual Windows child, real pipes
and a live communication reader before injecting a controlled exception; those
cases distinguish the product's leader cleanup from the observer's later release
and joining of its own retained-pipe helper. Neither test route uses a broadcast
console signal or proves cleanup of descendants.

This change does not alter pytest execution, generated-test attribution, result
parsing, model/provider calls, repository selection or output publication.
