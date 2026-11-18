# Fast flagged logistic selector: independent train/validation replication

## Replication result

Using wholly fresh training and validation streams, the fixed selector reduced equal-weight macro LER from .0051550 to .0043212 (16.18%; paired macro delta -0.000834, 95% interval [-0.000866, -0.000802]). Per-condition relative reductions were 12.1%, 34.2%, 31.5%, 18.9%, 12.4%, and 3.9%; all six paired intervals excluded zero, and none was harmed by more than 5%. The flag rate ranged 0.08%–0.52%, and all six fixed logistic fits converged.

Full inference cost (both matching passes plus classifier on flags) averaged 1.36x correlation-enabled matching, below the 2x limit. Training and fitting took 7.32 seconds total.

## Same-validation stronger comparator

On the exact same six-million-shot validation stream, flagged BP+LSD produced macro LER .004468 (13.34% reduction versus correlated matching), compared with .004321 (16.18%) for the learned selector. The learned selector had fewer errors in five cells; BP+LSD was better for Z memory under Z bias. BP+LSD's mean decode-time ratio was 8.28x, versus 1.36x for logistic selection. No BP+LSD syndrome-invalid outputs occurred.

## Decision and limits

The logistic selector independently passes its LER and runtime gates and beats fixed correlation-enabled matching on these six known simulator conditions. This is now a replicated low-cost development lead. It remains a supervised per-condition method trained on synthetic observable labels. It has not been challenged under measurement-noise mismatch, changing bias, different distances, or device data; an independent robustness challenge is next. No novelty or hardware claim follows.
