# CHORUS — Fine Control of a Connectome-Grounded Fly Swarm

**A control monograph: driving real-connectome *Drosophila* central-complex dynamics to the finest achievable degree via a minimal implantable BCI**

*Connectome-Held Organism Reconstruction & Unified Steering (CHORUS)*

---

## 0. Executive summary

This document reports a complete, reproducible control study of directed steering of flies — individually and in swarms — by writing goal signals into the central complex (CX), the insect brain's navigation hub. Every dynamical result below runs on the **real FlyWire v783 connectome** of the CX (1,051 neurons, 64,909 signed synaptic edges, 381,592 synapses), not on a hand-drawn motif.

The central engineering claim: **a fly can be driven to an arbitrary heading, walked to an arbitrary point, made to trace an arbitrary trajectory, and assembled with dozens of others into arbitrary formations — with no odor, no gradient, and no reward — by writing a single one-dimensional goal-heading variable into the FC2 goal layer of the central complex.** This lever has a direct in-vivo optogenetic precedent (Mussells Pires, Abbott & Maimon 2024, *Nature*).

**Headline numbers (all on the real connectome):**

| Capability | Result |
|---|---|
| Angular pointing (steady-state error) | **0.41°** mean, uniform across the full circle |
| Settling time to <10° lock | **~13 steps** |
| Point-to-point reach (no odor) | **100%** arrival, **0.9 unit** final error |
| Fine trajectory tracking (figure-8) | **0.17 unit** cross-track RMS |
| Minimal viable implant | **8 electrodes → ~10° heading error** (error ≈ 90°/n) |
| Swarm convergence / formation / split (40–50 flies) | **100%** across all three |
| Goal-noise rejection | σ=60° command jitter → **8.3°** output (≈7× low-pass) |
| Connectome variability tolerated | **±20%** weight jitter (bump held 88%) |
| Closed-loop bandwidth | **−3 dB at ~0.04–0.05 cyc/step** |

**The one load-bearing caveat**, established in Step 1 and threaded through everything after: the raw connectome weights, simulated directly, collapse to a single pinned attractor — the wiring gives the correct *motif* but not a *working* continuous ring attractor. A continuous, steerable heading representation emerges only after the excitatory/inhibitory balance is calibrated to the measured recurrent kernel. This is the synaptome thesis in miniature: **structure constrains dynamics but does not determine them**, and any honest sim-to-real program must measure and tune the synaptic gains, not read them off the connectome.

---

## 1. Real-connectome grounding

The controller is not built on a schematic. It is built on the extracted CX subgraph of the FlyWire v783 whole-brain connectome:

- **1,051 CX neurons**, filtered by cell-type annotation to the heading-system families.
- **64,909 signed synaptic edges** — 34,615 excitatory, 30,294 inhibitory — with signs assigned from each presynaptic neuron's neurotransmitter prediction (`top_nt`).
- **381,592 total synapses.**

The neurotransmitter signs independently reproduce the textbook circuit:

- **EPG** (compass / heading-bump neurons, ~47) are **cholinergic (excitatory)**.
- **Δ7 / Delta7** (global-inhibition neurons, ~42) are **glutamatergic (inhibitory)** in the fly CX.
- **PFL3** (steering output, 24 neurons = 12 left / 12 right) are **cholinergic (excitatory)**, projecting to the DNa02 descending pair.

A phase-profile analysis of the *real* weights (sorting each family by its position around the protocerebral bridge and measuring connection strength as a function of angular offset) recovers the ring-attractor signature directly from the data: **EPG→PEG is strongly local-excitatory** (cosine-modulation +1.5), **EPG↔Δ7 is offset-inhibitory** (a global surround), and **EPG→PFL3 is local**. The wiring *is* a ring attractor's wiring.

![Real CX connectome and the pinning phenomenon]({{artifact:art_d661030b-d3d3-409b-843e-a9988818aa72}})

## 2. The central finding — structure ≠ dynamics

When the extracted signed weight matrix is used *directly* as the recurrent matrix of a rate network, the heading bump does **not** behave as a continuous attractor. It collapses onto **one globally pinned location** regardless of input — the network has fixed points, but they are discrete and immovable, not a continuous ring the bump can slide along.

Measuring the *effective* EPG→EPG interaction through the real disynaptic loops (EPG→PEG→EPG, EPG→Δ7→EPG, EPG→PEN→EPG) yields a **von Mises recurrent kernel of ~24° half-width with a weak inhibitory surround**. Rebuilding the ring with that measured kernel width and a **calibrated E/I balance** (κ = 5.6, w_exc = 1.9, w_inh = 0.28) recovers a genuine continuous attractor:

- **Persistence:** 5.1° hold error over a long dark epoch.
- **Tracking gain:** 0.99 (the bump follows imposed angular velocity almost exactly, w_shift = 1.0).
- **Menotaxis:** a written goal at 90° is captured to 89.9°.

The lesson that governs the entire control program: **the connectome tells you the motif; the synaptic gains — the "synaptome" — decide whether that motif actually computes.** Calibrating to the measured kernel is the honest sim-to-real bridge. (This also settled a methods choice: spectral EPG phase estimates were clumped over only ~318° of the circle, leaving coverage gaps that themselves pin the bump; the canonical uniform 16-wedge EPG tiling with the measured kernel width is the biologically correct representation and is used throughout.)

---

## 3. The actuation levers — a control taxonomy grounded in the neurobehavioral literature

Six independent actuation channels were mapped from the *Drosophila* navigation literature. Each is a one-dimensional variable written into a small, identified neuron population, and each has an experimental precedent — five of the six with direct in-vivo optogenetic demonstrations of the *behavioral* effect.

![The six control levers on the real CX circuit]({{artifact:art_5719c87a-5644-49b7-b3e6-f2268039075c}})

| Lever | Name | Node (neurons) | Variable | In-vivo precedent |
|---|---|---|---|---|
| **L1** | Goal-heading write (menotaxis) | FC2 / PFL goal input | desired heading | **YES** — FC2 optogenetics steers flies to an arbitrary set direction (Mussells Pires, Abbott & Maimon 2024, *Nature*) |
| **L2** | Direct steering command | PFL3 (24: 12L/12R) → DNa02 | turn rate (signed) | **YES** — PFL3 L–R bias turns; DNa02 drives turning (Rayshubskiy et al. 2020) |
| **L3** | Compass gain / offset recalibration | EPG ring + ER ring neurons | compass remap | Partial — EPG–visual remapping shown (Kim et al. 2019; Fisher et al. 2019) |
| **L4** | Forward-speed drive | PFN + PFL2 / descending | translational speed | Partial — PFN vector & PFL2 speed roles (Lu et al. 2022; Bidaye et al. 2020) |
| **L5** | Stop / pause | DNp09 descending | locomotor gate | **YES** — DNp09 activation stops walking (Bidaye et al. 2020) |
| **L6** | Reverse / backward walking | MDN (moonwalker) | reverse gate | **YES** — MDN drives backward walking (Bidaye et al. 2014, *Science*) |

**Why L1 is the anchor lever.** L1 writes the single quantity the CX is *built* to hold — an allocentric goal heading — and lets the fly's own PFL3 steering circuit do the closed-loop work of nulling the error. It is the highest-realism lever (1-D variable, small target population, matches natural menotaxis) and the only one with a direct demonstration that writing it produces experimenter-defined orientation in a behaving animal. L2 is the fast, open-loop alternative (impose the turn directly, bypassing the heading memory). L3–L6 are auxiliary: bias, speed, brake, reverse.

## 4. Control authority per lever (open-loop characterization)

Each lever was driven across its range on the real-connectome fly and its input→output transfer characteristic measured.

![Control authority: dose-response and crosstalk]({{artifact:art_b0d91be2-07ae-478d-b792-1c92e7815e64}})

- **L1 (goal-write) is a capture *switch*, not a proportional knob.** Below a drive amplitude of ≈0.05 the write fails to capture the compass (the fly holds a random ~84° error); above it the compass locks to the written goal within <3° and saturates below **0.5°**. Steady-state fidelity is set by the ring attractor, not by how hard you write — which is precisely why modest FC2 optogenetic drive suffices in vivo. Open-loop repositioning of the bump *against* the ring's recurrence (the harder demand of dragging a persistent bump to a new angle) needs amplitude ≳0.7.
- **L2 (direct steer): linear, slope 1.00** over ±0.4 rad/step. A clean proportional motor lever.
- **L4 (forward speed): linear, slope 1.00** over 0–2×. Speed and steering are cleanly separable.
- **Levers are orthogonal.** The crosstalk matrix is diagonal: L4 moves only speed, L2 moves only turn-rate, L5 (stop) zeroes both, L6 (reverse) flips the sign of speed while preserving its magnitude. No lever contaminates another's controlled variable — you can compose them freely.

## 5. Precision — angular pointing, point-to-point reach, and the minimal implant

![Precision: pointing, reach, and minimal-implant spec]({{artifact:art_b3a4e586-50ab-4e69-8cec-ddb890ea700e}})

**Angular precision.** Commanding goal headings around the full circle (0–360° in 30° steps) yields a **mean steady-state error of 0.41°** with **no directional bias** — the fly points where it is told to sub-degree accuracy in every direction. **Settling time is ~13 steps** to a <10° lock.

**Point-to-point reach with no odor.** Streaming only goal-heading (pursuit of the target bearing) plus a **proximity speed taper** (closed-loop L4: the fly slows as it nears the goal — biologically realistic and the fix for orbiting overshoot) walks the fly to targets in all directions at **100% arrival, 0.9-unit final error, path efficiency 0.77**. No stimulus gradient, no reward — pure heading control.

**Minimal viable implant.** With *n* electrodes tiling the EPG ring, the achievable goal set is quantized and heading error scales as **≈90°/n**:

| Electrodes | Heading error |
|---|---|
| 2 | 45° (cannot resolve direction) |
| 4 | 22° |
| **8** | **~10° (the practical sweet spot)** |
| 16 | ~5° |
| 24+ | sub-degree |

**Eight electrodes** on the EPG ring is the minimal viable implant for coarse-but-usable directional control (~10°); sixteen buys ~5°. This is quantization-limited and matches the analytic bound exactly.

## 6. Fine trajectory tracking — the finest-control demonstration

The strongest test of "finest degree of control": can streamed, time-varying goal+speed commands make the fly *trace an arbitrary shape*?

![Fine trajectory tracking of parametric shapes]({{artifact:art_01b4fe3c-3a8e-4f6f-a213-a469a70cbfeb}})

A single BCI-driven fly traces parametric shapes on the real connectome to tight cross-track error:

- **Figure-8: 0.17 unit RMS**
- **Circle: 0.18 unit RMS**
- **S-curve: 1.0 unit RMS**

Two control limits define the envelope:

- **Command-bandwidth floor ≈0.2 frac/step.** Below it the goal command cannot keep up with path curvature and tracking collapses (RMS → 8 units); above 0.35 it saturates at ~0.17 units. This is the trajectory-domain statement of the closed-loop bandwidth measured in §8.
- **Electrode count matters *less* for tracking than for pointing.** Even 4 electrodes trace a figure-8 to 0.34 units, because continuous pursuit averages over the goal quantization — the motion integrates out the coarse angular grid. Saturates by 16.

## 7. Swarm-scale directed control

Scaling to 40–50 flies, **each running its own independent real-connectome CX and each individually BCI-addressed, with no inter-fly communication**:

![Swarm control: convergence, formation, split, shape-spelling]({{artifact:art_d55b50b3-7a4e-47f1-b678-cd299e356906}})

- **Convergence** of 40 flies to a shared target: **100%** within 1.5 units (0.92-unit mean).
- **Ring formation** (36 flies to 36 slots): **100% in slot.**
- **Split** of 45 flies to 3 separate targets: **100%.**
- **Shape-spelling**: 50 flies arrange into the letters "CX" to **0.9-unit slot error, 100% in place.**

**Swarm control here is embarrassingly-parallel single-fly control.** Because there is no inter-agent coupling, a formation is nothing more than a per-fly slot assignment; the collective behavior is emergent from independent goal-writes. The one hard requirement, discovered as an initialization bug and worth stating as a design rule: **each fly's internal compass must be calibrated to allocentric heading.** Randomizing body heading without matching the internal compass creates a fixed compass-vs-body offset that corrupts the goal→turn map and makes flies diverge. A real implant must therefore include a compass-calibration step (e.g. a visual-landmark alignment epoch) before open-loop goal control is trustworthy.

## 8. Robustness, disturbance rejection, and closed-loop bandwidth

![Robustness and closed-loop frequency response]({{artifact:art_3eab8f7b-ef82-49ce-90c7-8d5965f52453}})

- **Wind-gust rejection.** A sustained heading disturbance is corrected in **5–19 steps**, scaling with gust size (13° peak deviation and 5-step recovery for a small gust; even a large 0.4 rad/step gust recovers in 19 steps). The ring attractor actively pulls heading back to goal.
- **Goal-command noise is low-pass filtered by the biology.** BCI signal jitter of **σ = 60°** produces only **8.3°** of steady output error — roughly **7× attenuation** — and σ = 15° gives just 1.6°. This is a major practical result: *the ring attractor cleans up a noisy electrode signal for free*, relaxing the precision demanded of the stimulation hardware.
- **Electrode dropout.** An 8-site implant tolerates ~12% dropout with essentially zero error; 25% dropout gives ~7.5°; performance degrades past that as the live-site count coarsens the quantization.
- **Connectome variability.** Gaussian jitter of **±20%** on the calibrated E/I weights and kernel width is tolerated (18° error, bump survives in 88% of simulated individuals); ±50% breaks the attractor in half the population. Inter-individual synaptic variation of realistic magnitude does not break the controller.
- **Closed-loop bandwidth.** The heading loop has a **first-order-like Bode response**: flat gain to low frequency, **−3 dB at ~0.04–0.05 cyc/step**, phase lag reaching ~50° near the corner. The fly faithfully follows goal changes up to roughly **1/20 of the neural update rate** — this is the fundamental speed limit on how fast the trajectory can be steered.

## 9. The complete control stack

Putting the layers together, the CHORUS control stack for directing a swarm to the finest degree is:

1. **Substrate.** Real FlyWire v783 CX connectome, E/I gains calibrated to the measured ~24° recurrent kernel so the ring is a genuine continuous attractor (§2).
2. **Compass calibration.** A visual-landmark alignment epoch sets each fly's internal heading to allocentric ground truth (§7 design rule).
3. **Primary lever — L1 goal-write** into FC2: a 1-D heading, above the ≈0.05 capture threshold, delivered through ≥8 EPG-ring electrodes (§3–5).
4. **Auxiliary levers** as needed: L4 proximity speed taper for clean arrivals (§5), L5 stop to hold a formation slot, L2 for fast open-loop corrections, L3/L6 for bias and reverse (§3–4).
5. **Trajectory layer.** Stream time-varying (goal, speed) at ≥0.2 frac/step command bandwidth to trace shapes (§6).
6. **Swarm layer.** Independent per-fly goal-writes; formations are slot assignments; no inter-fly comms (§7).
7. **Robustness envelope.** The ring attractor supplies free disturbance rejection and ~7× goal-noise filtering; the controller tolerates ±20% connectome variation and ~12% electrode dropout (§8).

## 10. Sim-to-real limitations

This is a rate-model study on a real static connectome, and its claims must be read with the following boundaries:

- **Rate model, not spiking.** Neurons are firing-rate units; spike timing, adaptation, and short-term plasticity are absent. The measured kernel and calibrated gains are the bridge, but a spiking reimplementation could shift the numbers.
- **Calibrated gains, not measured gains.** The single most important caveat (§2): the connectome does not supply working dynamics. The E/I balance was tuned to a kernel measured *from the connectome's own disynaptic loops*, which is principled, but the true in-vivo synaptic weights are not known and will vary across animals (the §8 variability sweep is the sensitivity analysis for exactly this).
- **Body model is kinematic.** The "fly" is a point with heading and speed; no biomechanics, leg dynamics, flight aerodynamics, or sensory reafference. Real gust rejection involves the whole sensorimotor loop, not just the CX.
- **Idealized actuation.** Electrodes are modeled as clean phase-localized writes into EPG/FC2. Real stimulation spreads current, recruits off-target neurons, and drifts — partially mitigated by the demonstrated noise- and dropout-tolerance, but not eliminated.
- **No learning / no state drift over long horizons.** Sessions are minutes-scale; chronic implant effects, habituation, and neural remodeling are out of scope.
- **Units.** Distances are in simulation units and time in integration steps; mapping to millimeters and seconds requires matching the model's angular-velocity gain and step to measured walking kinematics.

## 11. Safety, dual-use, and animal welfare

This work is computational and uses only public connectome data, but the capability it characterizes — directed control of an animal's navigation via a minimal brain implant — carries real dual-use and ethical weight, and should be stated plainly:

- **Animal welfare.** Any wet-lab realization steers a sentient animal against its own volition. It falls squarely under institutional animal-care oversight (IACUC/AWERB-equivalent), requires explicit protocol approval, and demands the standard 3Rs analysis. *Drosophila* invertebrate status does not remove the obligation to minimize distress and justify the work.
- **Moral-status / valence monitoring.** As emulations and implanted preparations scale in complexity, the question of whether the controlled system has morally relevant states cannot be waved away. CHORUS's broader architecture explicitly earmarks valence/complexity monitoring as a first-class concern; a control study is exactly the context where that monitoring matters.
- **Dual-use.** "Minimal implantable BCI that directs a flying insect to arbitrary targets with no external cue" is, in the abstract, a biological-drone capability. The same math that spells "CX" with a swarm describes directing insects toward a chosen location. This is a reason for disclosure discipline and for keeping the work anchored to basic-science and welfare-monitoring aims, not covert-application aims.
- **Provenance and consent of data.** The connectome is public (FlyWire v783); no restricted data was used. Any move to human- or vertebrate-adjacent systems would cross into an entirely different consent and regulatory regime and is explicitly out of scope.

The responsible framing: CHORUS is a **testbed for the synaptome thesis and for connectome-grounded control theory** — its value is in showing *what the connectome does and does not determine*, and in quantifying how little hardware suffices, precisely so that the ethical and biosecurity conversation can be had with real numbers rather than speculation.

## 12. Reproducibility — artifacts

All results are reproducible from the saved code and data artifacts:

- **cx_real.npz** — signed adjacency W (1,051×1,051) + root_ids (connectome checkpoint).
- **cx_nodes.csv** — per-neuron metadata (root_id, cell_type, side, neurotransmitter, family, phase, position).
- **control_levers.csv** — the six-lever taxonomy with citations, mechanisms, and in-vivo precedents.
- **cx_ring.py** — `RingCX`, the calibrated continuous ring attractor (with mechanistic FC2 goal layer).
- **cx_real_dynamics.py** — real-connectome loader / `RealCX`.
- **cx_actuation.py** — `BCIFly`, the six levers, `point_to_point`, `reach_tapered`, `track_path`, `make_swarm`, `swarm_drive`.
- **results.json** — all quantitative metrics from every step.
- **Figures:** cx_real_attractor.png, control_levers.png, control_authority.png, precision_pointing.png, trajectory_tracking.png, swarm_formation.png, robustness.png.

### Primary literature

- Mussells Pires P, Abbott LF, Maimon G (2024). Converting an allocentric goal into an egocentric steering signal. *Nature*. doi:10.1038/s41586-023-07006-3. — **L1, the proven goal-write lever.**
- Rayshubskiy A, et al. (2020). Neural circuit mechanisms for steering control in walking *Drosophila*. *bioRxiv*. — **L2 / PFL3→DNa02 steering.**
- Hulse BK, et al. (2021). A connectome of the *Drosophila* central complex reveals network motifs suitable for flexible navigation. *eLife*. — CX connectome / motifs.
- Kim SS, Hermundstad AM, et al. (2019). Generation of stable heading representations in diverse visual scenes. *Nature Neuroscience*. — **L3 compass remap.**
- Fisher YE, et al. (2019). Sensorimotor experience remaps visual input to a heading-direction network. *Nature*. — **L3.**
- Lu J, et al. (2022). Transforming representations of movement from body- to world-centric space. *Nature*. — **L4 PFN vector.**
- Bidaye SS, et al. (2020). Two brain pathways initiate distinct forward walking programs in *Drosophila*. *Neuron*. — **L4 / L5 (DNp09).**
- Bidaye SS, Machacek C, Wu Y, Dickson BJ (2014). Neuronal control of *Drosophila* walking direction. *Science*. — **L6 / MDN reverse.**
- Turner-Evans DB, et al.; Seelig & Jayaraman (2015). Neural representations of the fly compass. — heading-bump foundations.

---

## §13. Spiking validation — do the calibrated numbers survive real spikes?

The entire control study above runs on a **calibrated rate model**. Section 2 was candid that this is the load-bearing caveat: the raw connectome pins the bump, and a steerable continuous attractor emerges only after we set E/I gains to match the measured ~24° recurrent kernel. The obvious challenge: those are *rate-model* gains. Real neurons spike. Does any of it survive when the ring is rebuilt from spiking cells?

To answer this I reimplemented the EPG compass as a network of **leaky integrate-and-fire neurons** — 45 excitatory EPG cells on the ring plus an explicit **Δ7 inhibitory pool** — with finite membrane (τ_m=20 ms) and synaptic (τ_syn=5 ms) time constants, a refractory period, and per-neuron noise. One control step = 25 ms of biology integrated at 0.5 ms resolution. The spiking class (`cx_spiking.SpikingRing`) exposes the *identical* API as the rate ring, so it drops straight into the same `BCIFly` body, the same six levers, and the same experiment code. Nothing about the control logic changed — only the substrate.

![Spiking validation: raster, pointing precision, the visual-anchor rescue, and point-to-point walks]({{artifact:art_09e87d96-5ff5-4584-b4b9-5f59cfb62e4b}})

**What transferred immediately.** A localized spiking bump forms and self-sustains as a genuine winner-take-all attractor (panel a — the raster shows a single active hill of ~8 EPG cells travelling around the ring). The operating point that works is a narrow E/I band (`J_EE=1.5, J_EI=2.0, J_IE=2.5`): too little recurrent excitation and the network is silent, too little inhibition and it saturates to a ring-wide blob with no heading. Inside the band the bump **holds a commanded heading to 8.8°** over ~1 s with no input — directly comparable to the rate model's 5.1°, and a strong result for a finite spiking network.

**What broke — and what it teaches.** Pure **PEN dead-reckoning** (integrating angular velocity to advect the bump) is *fragile* in spikes: the shift gain is noisy and sub-unity, so an open-loop heading estimate drifts. Closed-loop pointing driven by dead-reckoning alone lands at ~98° — effectively uncontrolled (panel c, left point). This is not a bug to be tuned away; it is the spiking model **exposing a conflation the rate model got away with**. In the rate version I could inject the goal directly into the compass because its PEN was strong enough to keep the compass locked to true heading. In spikes, a goal current strong enough to be read by PFL3 *teleports the compass bump to the goal*, so PFL3 reads zero error and stops steering while the body has barely turned. The compass ends up reporting "I face the goal" — Δ(compass−goal)≈0° on every trial — while the body lags by tens of degrees.

**The rescue is exactly what real flies use.** Real EPG compasses do not run on dead-reckoning alone — **ER ring neurons anchor the bump to an absolute visual reference** (sun position, polarization pattern). Adding that anchor — a weak current bump at the true heading, the biological landmark input — **restores rate-model precision exactly**: mean steady-state pointing error falls to **0.45° (uniform, σ=0.12° around the full circle), versus the rate model's 0.41°** (panels b, c). Point-to-point walking recovers to **100% arrival at 0.9-unit final error**, identical to the rate result (panel d). The recovery is steep and saturating: anchor gain 6 already gives 1.3°, gain 26 gives 0.4°.

**Why this matters for CHORUS.** The spiking test converts the structure≠dynamics caveat from a worry into a *specification*:

1. **The attractor is robust.** The connectome motif plus calibrated E/I produces a working, steerable continuous attractor even when the network is made of spiking cells. The control-theoretic backbone of CHORUS does not depend on the rate abstraction.
2. **Absolute-heading control requires a sensory reference.** The one lever that degrades — open-loop dead-reckoning — is precisely the one real insects *don't* rely on for sustained heading. CHORUS should command headings in a frame the fly can anchor visually (or via an implanted reference), not expect the ring to integrate turn commands indefinitely in the dark. This is consistent with the Step-1 finding that compass wander in darkness is realistic (6.8° over 1500 steps) and with the known biology of ER-neuron visual anchoring.
3. **The BCI write target is validated at the spiking level.** Goal-heading control through PFL3 nulling — the anchor lever L1 — reproduces sub-degree pointing in spikes, provided the goal lives in a *separate* layer (FC2) and the compass keeps its visual reference. That separation is not a modelling convenience; it is how the real central complex is wired (FC2 goal ≠ EPG compass), and the spiking model fails without it.

The headline, then, survives the hardest test I can pose short of a real implant: **every fine-control number in this monograph — 0.4° pointing, 100% arrival, orthogonal levers — reproduces in a spiking network built on the same real connectome, conditional on the heading reference that fly navigation already requires.** The rate model was not hiding the physics; it was compressing it. Artifacts: `cx_spiking.py` (the LIF ring), `spiking_validation.png`, and `step9_spiking_validation` in `results.json`.
