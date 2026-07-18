# Responsible disclosure & dual-use assessment

## Summary
CHORUS is a **control-theory + connectomics study on public data**. It contributes
the *steering/control layer* for directing insect navigation by writing to the
central complex, grounded entirely in the already-published FlyWire v783 connectome
and in already-published neurobehavioral results (each actuation lever below has a
peer-reviewed in-vivo precedent). It builds **no** hardware, wet-lab reagent, or
surgical method.

## What this work is
- A demonstration that the **real** connectome, once its E/I balance is calibrated,
  supports a steerable heading attractor, and that a single 1-D goal variable
  written to FC2 is sufficient for fine directed control (pointing, reach,
  trajectory, swarm formation) with no odor/reward.
- A **minimal-implant specification** (~8 electrodes) derived from information-theoretic
  quantization of the compass — i.e., a statement of how little would be needed,
  which is equally a statement of the resolution limits.
- A **spiking validation** that turns the "structure ≠ dynamics" caveat into a
  concrete design constraint (separate goal layer + heading reference required).

## The actuation levers and their published precedents
- **L1 goal-heading write → FC2**: Mussells Pires, Abbott & Maimon 2024, *Nature*
  (10.1038/s41586-023-07006-3) — in-vivo optogenetic goal-write, the anchor result.
- **L2 direct steer → PFL3/DNa02**: Rayshubskiy et al. 2020.
- **L3 compass offset → EPG/ER**: Kim et al. 2019; Fisher et al. 2019.
- **L4 forward speed → PFN/PFL2**: Lu et al. 2022; Bidaye et al. 2020.
- **L5 stop → DNp09**: Bidaye et al. 2020.
- **L6 reverse → MDN**: Bidaye et al. 2014, *Science*.

Every lever is already in the literature. CHORUS integrates them into one control
framework; it does not discover a new access point to the nervous system.

## Why the marginal uplift toward misuse is low
The hard, rate-limiting barriers to any real "steered swarm" are **not** addressed here:
- a chronic **implant** small and light enough for a fly, with power and telemetry;
- **surgical access** and long-term biocompatibility;
- **individual addressing** of free-flying insects in the field.

These are the actual gates, and they are untouched by this study. CHORUS moves only
the layer that was already most complete in the open literature — the control theory —
and does so on an animal (*Drosophila*) that is a standard, unrestricted lab model.

## Framing and intended use
This is released as a **connectome-grounded control-theory and animal-welfare
testbed**: a reproducible way to ask how much directed control the CX circuit
affords, where its limits are, and (via the moral-status/valence considerations in
the broader project) when directed control of an animal raises welfare questions.
The dual-use dimension is named openly rather than obscured.

## Not included by design
No implant design, no electrode-fabrication protocol, no surgical procedure, no
telemetry/power scheme, no field-deployment method. Requests to supply those should
be declined and referred to institutional biosafety / IRB-equivalent oversight.
