"""Figure for the anchored-model control results and specificity ablation.
Reads data/anchored_results.json (and the malecns companion if present).
New file, does not touch plot_ablation.py."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

FLY = '../data/anchored_results.json'
MALE = '../data/anchored_results_malecns.json'
OUT = '../figures/anchored_control.png'


def load(p):
    try:
        with open(p) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def main():
    fly = load(FLY)
    male = load(MALE)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))

    # panel 1: pointing error, anchored vs published vs uncalibrated baseline
    ax = axes[0]
    labels, means, sds, colors = [], [], [], []
    labels.append('published\nRingCX\n(uncalibrated,\n4 free params)'); means.append(0.41); sds.append(0.0); colors.append('#95a5a6')
    labels.append('RealCX\nbaseline\n(uncalibrated)'); means.append(71.1); sds.append(7.8); colors.append('#e67e22')
    if fly:
        labels.append('anchored\n(FlyWire)'); means.append(fly['control']['pointing_mean']); sds.append(fly['control']['pointing_sd']); colors.append('#2b6cb0')
    if male:
        labels.append('anchored\n(MaleCNS)'); means.append(male['control']['pointing_mean']); sds.append(male['control']['pointing_sd']); colors.append('#8e44ad')
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=sds, color=colors, capsize=4)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylabel('pointing error (deg)')
    ax.set_title('Control: pointing error')

    # panel 2: fig8 rms
    ax = axes[1]
    labels2, means2, sds2, colors2 = [], [], [], []
    labels2.append('published\nRingCX'); means2.append(0.17); sds2.append(0.0); colors2.append('#95a5a6')
    labels2.append('RealCX\nbaseline'); means2.append(9.86); sds2.append(1.0); colors2.append('#e67e22')
    if fly:
        labels2.append('anchored\n(FlyWire)'); means2.append(fly['control']['fig8_mean']); sds2.append(fly['control']['fig8_sd']); colors2.append('#2b6cb0')
    if male:
        labels2.append('anchored\n(MaleCNS)'); means2.append(male['control']['fig8_mean']); sds2.append(male['control']['fig8_sd']); colors2.append('#8e44ad')
    x2 = np.arange(len(labels2))
    ax.bar(x2, means2, yerr=sds2, color=colors2, capsize=4)
    ax.set_xticks(x2); ax.set_xticklabels(labels2, fontsize=7.5)
    ax.set_ylabel('figure-8 cross-track RMS (units)')
    ax.set_title('Control: figure-8 tracking')

    # panel 3: specificity ablation cohen's d at anchored point
    ax = axes[2]
    if fly:
        conds = ['sign_scramble', 'edge_shuffle', 'degree_matched_random']
        ds = [fly['ablation']['stats_vs_intact'][c]['pointing_deg']['cohens_d'] for c in conds]
        cis = [fly['ablation']['stats_vs_intact'][c]['pointing_deg']['cohens_d_ci95'] for c in conds]
        mde = fly['ablation']['min_detectable_effect_d_n20']
        yerr = np.array([[d - lo, hi - d] for d, (lo, hi) in zip(ds, cis)]).T
        xp = np.arange(len(conds))
        ax.errorbar(xp, ds, yerr=yerr, fmt='o', color='#c0392b', capsize=4)
        ax.axhline(0, color='k', lw=0.8)
        ax.axhline(mde, color='#7f8c8d', ls='--', lw=1, label=f'MDE n=20 (d={mde:.2f})')
        ax.axhline(-mde, color='#7f8c8d', ls='--', lw=1)
        ax.set_xticks(xp); ax.set_xticklabels(conds, fontsize=7.5, rotation=15)
        ax.set_ylabel("Cohen's d (null vs intact), pointing error")
        ax.set_title('Specificity at anchored operating point')
        ax.legend(fontsize=7)
        ax.set_ylim(-1.2, 1.2)

    fig.suptitle('Anchored model (W_syn frozen pre-control): control performance and connectome specificity')
    fig.tight_layout()
    fig.savefig(OUT, dpi=150)
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
