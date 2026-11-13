# NS-4A V2 Supervisor and Memory Integration Plan

## Status and boundary

This is an engineering-only compatibility package based on review commit
f7f0fc167960e9499e40785a9b2262295bfecabc. It does not modify the V2 scientific
configuration, protocol, seeds, runner, authorization validator, V7 source, or
historical results. It does not include a V2 production launch command, allocate
seeds, create authorization, or invoke a sampler.

The proposed NS-4A allocation and 1,800-second deadline remain unchanged.
Integrating these files later requires a new source/configuration identity
manifest and separate owner authorization; an authorization bound to the
existing runner cannot cover new executable source.

## Supervisor integration

v2_job_supervisor_v1.py is a separately named V2-compatible Windows process
supervisor derived from the reviewed V7 Job Object implementation. It starts a
monotonic timer before creating the workload Job Object and launching the child.
The child is created suspended, assigned to a Job configured with
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, and resumed only after assignment. The
runner's initialization, catalog construction, sampling calls, decoder work,
archive/checkpoint writes, independent audit, statistical analysis, and its own
completion commit all execute inside that child process and therefore inside
the supervisor's 1,800-second window.

After root exit, the supervisor keeps the V7 PID-list and active-count drain
logic, including PID creation-time checks, process liveness inspection,
fail-closed handling of inaccessible/unclassified members, and the bounded
post-exit grace period. A forced termination, a late-observed root exit, a
deadline overrun, an API error, or an undrained Job is never reported as
successful completion. A nonzero child exit remains a failure.

The implementation is not connected to run_ns4a_v2.py or
execute_authorized(). A future integration should wrap the already
authorization-gated runner process without changing its sampler capability or
scientific arguments. The runner's 1,800-second cooperative checks remain
defense in depth; the external Job Object supervisor supplies asynchronous
process termination when a child is blocked in sampling, decoder, analysis, or
file operations while the supervisor itself remains responsive.

### Future source/authorization steps

1. Keep this package immutable and review its manifest.
2. Create a superseding runner/source identity that includes the supervisor,
   memory provider, dependency lock, tests/auditor, and exact invocation
   wrapper.
3. Preserve the V2 resource threshold at 2 GiB and its 1,800-second wall clock.
4. Resolve the legacy peak_rss_bytes config key in a versioned execution
   schema: it currently names the threshold but not the Windows metric chosen
   here (per-process peak working set). Do not silently reinterpret an
   existing source freeze.
5. Allocate and collision-screen numeric seeds only through the separately
   approved metadata allowlist and a new immutable inventory.
6. Require a new exact-identity owner authorization. This package creates
   none.
7. Run a sampler-free no-sampling preflight first; sampling requires a distinct
   explicit authorization.

## Memory integration

The existing V2 configuration's numeric threshold remains
2,147,483,648 bytes. A future V2 runner revision should call
measure_current_process() at its existing resource-check boundaries and
apply enforce_peak_working_set() to peak_working_set_bytes. Because PSAPI
returns the process lifetime high-water value, a peak between checks remains
observable at the next check; this is stronger than polling only the current
working-set snapshot.

The current committed ResourceGuard is not replaced or edited in this
package. Its historical key and implementation remain intact pending a
versioned integration review.

## Recovery behavior after supervisor termination

The supervisor reports timeout/termination as failure even if Job cleanup
later drains. It does not resume a run. A terminated sampler or filesystem
transaction may leave an in-flight root, temporary file, or incomplete
checkpoint; that state must be examined with the existing exact-seed,
archive-and-marker recovery rules. No seed substitution or automatic retry is
permitted. If the persisted state is ambiguous, preserve it and stop for owner
review.
