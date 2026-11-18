# Exact tensor-train compressibility audit

## Question

The exact P(s), Z(s) parity representation handles 20 touched detector bits at seven layers. Before implementing a spacetime tensor decoder, assess whether these exact arrays are low-rank when detector bits retain their natural temporal order. A low rank would support an MPS prototype; high rank would argue against this contraction order.

## Fixed method

Reconstruct the exact seven-layer P and signed Z arrays from the frozen signature map and previously validated protocol. For each binary cut k=1..19 in the stored compact detector order, form the exact matricization (2^k by 2^(20-k)) and compute its singular values. Report numerical rank at relative Frobenius truncation tolerances 1e-6 and 1e-10, exact nonzero rank under a fixed machine-precision threshold, and discarded Frobenius mass. Do not reorder detector bits or choose cuts after seeing results.

## Resource and advancement gate

Proceed only if max matrix dimension <=1,048,576, total SVD wall time <=300 seconds, and memory estimate <=1 GiB. The MPS prototype is worth pursuing at this ordering only if both P and Z require rank <=64 for relative Frobenius truncation error <=1e-10 at every cut. Otherwise record a negative compressibility result and move to another representation/family. This is deterministic analysis of existing exact development data; no stochastic samples or new posterior claims are generated.
