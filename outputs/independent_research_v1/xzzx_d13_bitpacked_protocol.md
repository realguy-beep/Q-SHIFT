# Bit-packed Stim/PyMatching throughput screen for the d13 stop

## Question

The ordinary d13 four-cell preflight projected 454.7 seconds for 500,000 shots/cell. Can Stim's bit-packed detector sampler plus PyMatching's bit-packed batch API preserve exactly the same predictions while bringing this fixed screen under the 300-second cap?

## Fixed screen

Use the same four d13 cells (CSS-X/Z and native-XCX XZZX-X/Z), distance 13/25 rounds, X-bias ratio 10:1, p=.003, and resource/probability gates as the stopped protocol. Preflight 50,000 shots/cell at seeds 2026115001–2026115004. For each exact seed, compare Stim unpacked and bit-packed sampler outputs byte-for-byte after little-endian `np.packbits`; compare ordinary and bit-packed PyMatching outputs exactly; require scalar/batch agreement on 100 shots/cell. If equivalence fails or projected 500k/cell bit-packed sample+decode time exceeds 300 seconds, stop without a main run.

If the preflight passes, run 500,000 fresh shots/cell using seeds 2026115011–2026115014. Report LERs, rate ratios, runtime, and peak RSS. This is a decoder API/throughput ablation; it does not change the decoder algorithm or the physical noise model, and it is development-only.
