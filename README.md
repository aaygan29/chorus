# CHORUS — Connectome-Held Organism Reconstruction & Unified Steering

An in-silico study of how much control a minimal implantable BCI could exert over a *Drosophila* swarm, when the dynamics are run on a **real connectome** rather than a hand-drawn motif. This is simulation and threat-model work: it exists to measure an attack surface, not to build one.

**Private repository.** This is dual-use neurosecurity research. Read [`THREAT_MODEL.md`](THREAT_MODEL.md) and [`RESPONSIBLE_DISCLOSURE.md`](RESPONSIBLE_DISCLOSURE.md) before sharing any part of it.

## What it does

- Builds a ring-attractor heading system (EPG/PEN/Δ7 compass) on the real central-complex connectome, as both a rate model and a leaky integrate-and-fire spiking model.
- Models a minimal implantable BCI actuation stack and a fly body model, then drives single-agent pointing, point-to-point reach, and trajectory tracking.
- Extends to a swarm driver (formation, split, shape) with no inter-agent communication.
- Quantifies control authority per actuation lever and the robustness of each result.

**The load-bearing caveat (structure is not dynamics):** the raw connectome weights collapse to a single pinned state. The wiring alone yields the ring *motif* but not a working attractor; a steerable continuous attractor emerges only after E/I gains are calibrated against measured tuning. The connectome constrains the circuit, it does not by itself specify the dynamics.

## Layout

```
PAPER.md              full control write-up (start here); figures render inline from figures/
code/                 cx_ring (rate compass), cx_spiking (LIF validation),
                      cx_actuation (BCI stack + body model + swarm driver),
                      cx_real_dynamics (attractor on the real connectome)
data/                 real CX subgraph, neuron table, actuation levers + citations,
                      results.json, spiking raster / pointing / walk data
figures/              generated figures
THREAT_MODEL.md       what this measures and who it is a risk to
RESPONSIBLE_DISCLOSURE.md
```

## Data & grounding

- **FlyWire v783** central-complex connectome (real, published connectome data) — the signed weight matrix and neuron table in `data/`.
- Actuation levers are literature-grounded, with citations in `data/control_levers.csv`.
- All dynamics, control, and swarm results are **simulated**; nothing here was run on a living animal.

## License

MIT — see [LICENSE](LICENSE).
