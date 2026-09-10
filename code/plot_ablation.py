"""Plot figures/ablation_specificity.png from data/ablation_results.json.
Does not modify any existing figure or file."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

r = json.load(open('../data/ablation_results.json'))
conds = ['intact', 'sign_scramble', 'edge_shuffle', 'degree_matched_random']
labels = ['intact', 'sign\nscramble', 'edge\nshuffle', 'degree-matched\nrandom']
metrics = [('pointing_deg', 'pointing error (deg)'), ('fig8_rms', 'figure-8 cross-track RMS'),
           ('p2p_err', 'point-to-point final error')]

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax, (key, title) in zip(axes, metrics):
    data = [r['conditions'][c][key] for c in conds]
    parts = ax.violinplot(data, showmeans=True, showextrema=True)
    for pc in parts['bodies']:
        pc.set_alpha(0.5)
    for i, d in enumerate(data):
        m = np.mean(d); sd = np.std(d, ddof=1); n = len(d)
        ci = 1.96 * sd / np.sqrt(n)
        ax.errorbar(i + 1, m, yerr=ci, fmt='o', color='black', capsize=4, zorder=5)
    ax.axhline(np.mean(r['conditions']['intact'][key]), color='crimson', ls='--', lw=1,
               label='intact mean')
    male_val = np.mean(r['intact_male'][key])
    ax.axhline(male_val, color='steelblue', ls=':', lw=1, label='intact_male mean')
    ax.set_xticks(range(1, len(conds) + 1)); ax.set_xticklabels(labels, fontsize=8)
    ax.set_title(title, fontsize=10)
    ax.set_ylabel(key)
    ax.legend(fontsize=7)

fig.suptitle('RealCX specificity ablation (n=20 seeds/condition). W-sensitivity confirmed: '
             f"intact={r['sanity_check']['intact']:.1f} deg, "
             f"x0.1 W={r['sanity_check']['scaled_0p1']:.1f} deg, "
             f"zero W={r['sanity_check']['zeroed']:.1f} deg", fontsize=9)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig('../figures/ablation_specificity.png', dpi=150)
print('wrote ../figures/ablation_specificity.png')
