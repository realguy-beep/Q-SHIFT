# Q-SHIFT Core Upgrade — Teacher-Friendly Summary

This update improves the software structure behind Q-SHIFT. A decoder is a method that reads error-check measurements and predicts whether the encoded logical result flipped. The new shared interface makes different decoders return the same kind of prediction, records which model and noise assumptions they use, and checks that every input and output has the right shape.

The project’s existing PyMatching decoder remains the trusted comparison. New adapter code keeps its current correlation setting consistent when the matching graph is built and when it is used. A cautious controller interface can accept a detector-based estimate, wait for evidence from earlier blocks, and fall back to fixed PyMatching when confidence or support is insufficient.

The update also rejects malformed settings instead of quietly converting them, adds clearer errors if a simulation batch fails, and explains on the dashboard that a predicted logical bit is not a physical instruction for individual qubits.

This was a software reliability task. It did not run a research experiment, train a model, connect quantum hardware, or prove that adaptive decoding is better. Existing evidence still does not show a reliable adaptive or neural improvement over strong fixed PyMatching.
