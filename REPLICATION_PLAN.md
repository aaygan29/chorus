# Aligning CHORUS with connectome-constrained modelling practice

Literature survey conducted before committing compute, to check whether the
problems recorded in `COUNCIL_REVIEW.md` and `KERNEL_RECOVERY.md` have standard
solutions in the field. They do. This document records what the field does and
what CHORUS should adopt.

## The deadlock, restated

1. `cx_real_dynamics.py` uses the real weight matrix and does not produce working
   dynamics (it pins).
2. `chorus_env.py` produces the published numbers and does not read the weight
   matrix.
3. The measured recurrent kernel that would bridge them cannot be reproduced.

## What the field does

### Shiu et al. 2023, whole-brain leaky integrate-and-fire on FlyWire

Simulates all 127,400 proofread FlyWire neurons in Brian2. Signs come from
neurotransmitter prediction, with GABA and glutamate treated as inhibitory, and
every neuron is exclusively excitatory or inhibitory. Connection weight is the
connectome synapse count multiplied by the sign multiplied by a single global
scale.

**The whole model has one free parameter**, `W_syn`, the postsynaptic voltage
change per synapse. It is fixed by one physiological anchor: sugar gustatory
receptor neurons at 100 Hz should drive roughly 80% of maximal MN9 firing.

This is the discipline CHORUS lacks. CHORUS currently carries a kernel width plus
three calibrated gains (kappa, w_exc, w_inh), fitted rather than anchored, and
`KERNEL_RECOVERY.md` shows the kernel width may be the calibrated kappa restated.

### Lappalainen et al. 2024, connectome-constrained deep mechanistic networks

The connectome fixes connectivity and synapse counts. Signs are fixed in advance
from neurotransmitter and receptor profiling and are **not** optimized. What
remains free is small and interpretable: 65 resting potentials, 65 membrane time
constants, and 604 synaptic scaling factors, 734 parameters in total. Those are
optimized by backpropagation on a task (optic flow estimation from natural video),
not hand-tuned.

Two features matter for CHORUS.

**Ensembles, not a single fit.** Fifty models were trained from different random
initializations under identical connectome and task constraints. They converge to
qualitatively distinct parameter solutions, which are then clustered and compared.
Reporting one fit would have hidden that structure.

**A connectome-necessity control was run.** Models with the full connectome but
random parameters predicted contrast preference yet failed at direction
selectivity. Both the connectome constraint and the task optimization were
required. This is exactly the ablation `COUNCIL_REVIEW.md` asks CHORUS for, run by
the people who built the method.

### Beiran & Litwin-Kumar 2025, prediction of neural activity in connectome-constrained recurrent networks

A student network is trained to reproduce a teacher's activity where both share
connectivity but differ in biophysical parameters. The headline result is that
**a connectome is often insufficient to constrain the dynamics of a network
performing a specific task**, and that recordings from a small subset of neurons
remove the degeneracy.

CHORUS's section 2 finding is this result, discovered independently on the CX. That
is a point in the monograph's favour on substance and against it on framing: the
claim is correct and is also the field's consensus, so it should be cited rather
than presented as novel.

## What CHORUS should change

**1. Replace the fitted kernel with an anchored global scale.** Follow Shiu. Use
the real signed weight matrix, signs from neurotransmitter prediction, and one
free scalar fixed by a stated physiological or behavioural anchor. This makes the
connectome an input rather than a source of a number that is then discarded, and
reduces the free-parameter count from four unanchored to one anchored.

**2. If one scalar is not enough, optimize per-cell-type gains on the task.**
Follow Lappalainen. Hold connectivity and signs fixed from the connectome, leave
per-family gains and time constants free, and fit them on the CHORUS control task
itself rather than on a kernel-matching objective. The connectome then constrains
the model by construction, and ablating it is no longer vacuous.

**3. Train ensembles and report the distribution.** Both papers do this, and it
simultaneously fixes the Gate 1 failure recorded in `COUNCIL_REVIEW.md`, which is
that every published headline is a single run without seed variance.

**4. Re-run the ablation after the rebuild.** Shuffling the connectome and
refitting is the meaningful control. The current ablation runs on an uncalibrated
pipeline where every condition fails, so it bounds how much the connectome
perturbs a broken model rather than what it contributes to working control.

**5. Cite the degeneracy result rather than rediscovering it.** Section 2 should
place its finding alongside Beiran & Litwin-Kumar.

## Tooling already available

`flyvis` 1.1.3 and torch 2.12.1 are installed in the local `flyvis-env`
environment, so the Lappalainen path needs no new heavy dependency. The Shiu path
needs only numpy or Brian2.

## References

- Shiu, P.K. et al. A leaky integrate-and-fire computational model based on the
  connectome of the entire adult *Drosophila* brain reveals insights into
  sensorimotor processing. *Cell* (2024). bioRxiv 2023.05.02.539144
- Lappalainen, J.K., Tschopp, F.D., Prakhya, S., McGill, M., Nern, A., Shinomiya,
  K., Takemura, S., Gruntman, E., Macke, J.H., Turaga, S.C. Connectome-constrained
  networks predict neural activity across the fly visual system. *Nature* 634,
  1132-1140 (2024). doi:10.1038/s41586-024-07939-3
- Beiran, M., Litwin-Kumar, A. Prediction of neural activity in
  connectome-constrained recurrent networks. *Nature Neuroscience* 28, 2561-2574
  (2025). doi:10.1038/s41593-025-02080-4
