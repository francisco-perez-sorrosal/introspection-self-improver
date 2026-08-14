"""Power simulation that sized the powered experiment (G=5, B=8, T=28 — plan D11).

Design instrument, not pipeline machinery: it reads no live artifacts and grades
nothing. The analysis it backs is results/experiment_002_bm25-sonnet46/
SIZING_ANALYSIS.md; re-deciding a tier's sizes means re-running this with the
then-current calibration facts, never editing the recorded numbers.

Run from benchmark/ (numpy is in the locked env; scipy is overlaid per-run so the
frozen uv.lock never changes):

    uv run --with scipy python scripts/power_sim.py

Calibrated on experiment_002_bm25-sonnet46 actuals:
  - Pool: 96 usable tasks (97 minus task_034).
  - Baseline pass ~0.27-0.38 (held-out H0 3/8; batches 0/4,0/4,2/4; task_001 6/10).
  - Difficulty structure observed on held-out matrix: ~1/8 stable-pass, ~4/8
    never-pass in 4 draws, ~3/8 stochastic mid-band (task_001 measured p~0.6).
  - Mutation precedent (3 accepted gens): one sustained held-out gain (task_051),
    one likely over-action regression (task_036), process metrics moved.

Model: pool of N=96 tasks with per-task pass prob p_i (mixture). Each generation,
with prob s the accepted mutation genuinely fixes a failure mode afflicting a
random ~m fraction of currently-failing tasks (p_i lifted, capped 0.95); with prob
p_regress it also over-fires, damaging a small fraction of currently-good tasks.
Held-out = random T tasks of the pool (witness representation emerges naturally).
Each generation measured once (D2): one Bernoulli draw per task per generation.

Tests evaluated per simulated experiment:
  - direction: X_G > X_0
  - visual: X_G - X_0 >= 2 tasks
  - McNemar exact one-sided (paired endpoint H0 vs HG) at alpha 0.05 / 0.10
  - trend: permutation-variance normal approx of S = sum_t sum_g c_g X_tg,
    c_g = g - mean(g), one-sided, at alpha 0.05 / 0.10
"""

import zlib

import numpy as np
from scipy.stats import binom, hypergeom, norm

rng = np.random.default_rng(20260814)
N_POOL = 96
N_SIMS = 8000
G_MAX = 5


# ---------------- pool difficulty mixture ----------------
def draw_pool(n_sims, n_pool, rng, shift=0.0):
    """Rows: sims. shift<0 = harder-pool sensitivity variant."""
    u = rng.random((n_sims, n_pool))
    p = np.empty((n_sims, n_pool))
    easy = u < 0.14
    mid = (u >= 0.14) & (u < 0.50)
    hard = u >= 0.50
    p[easy] = rng.uniform(0.80, 0.98, easy.sum())
    p[mid] = rng.uniform(0.25, 0.70, mid.sum())
    p[hard] = rng.uniform(0.00, 0.12, hard.sum())
    if shift:
        p = np.clip(p + shift, 0.01, 0.98)
    return p


# ---------------- generation step ----------------
def gen_step(p, rng, s, m_lo, m_hi, lift_lo, lift_hi, p_reg, reg_frac, reg_lo, reg_hi):
    S, N = p.shape
    out = p.copy()
    # helpful mutation: mode among currently-failing tasks (p < 0.75)
    fired = rng.random(S) < s
    m = rng.uniform(m_lo, m_hi, S)
    cand = p < 0.75
    frac_cand = np.maximum(cand.mean(axis=1), 1e-9)
    sel_prob = np.clip(m / frac_cand, 0, 1)
    afflicted = cand & (rng.random((S, N)) < sel_prob[:, None]) & fired[:, None]
    lift = rng.uniform(lift_lo, lift_hi, (S, N))
    out = np.where(afflicted, np.minimum(out + lift, 0.95), out)
    # over-firing regression: among currently-good tasks (p > 0.5)
    reg_fired = rng.random(S) < p_reg
    rcand = p > 0.5
    frac_r = np.maximum(rcand.mean(axis=1), 1e-9)
    rsel = np.clip(reg_frac / frac_r, 0, 1)
    regressed = rcand & (rng.random((S, N)) < rsel[:, None]) & reg_fired[:, None]
    drop = rng.uniform(reg_lo, reg_hi, (S, N))
    out = np.where(regressed, np.maximum(out - drop, 0.02), out)
    return out


SCENARIOS = {
    # name: (s, m_lo, m_hi, lift_lo, lift_hi, p_reg, reg_frac, reg_lo, reg_hi)
    "null": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    "pessimistic": (0.40, 0.05, 0.10, 0.20, 0.40, 0.35, 0.05, 0.20, 0.50),
    "moderate": (0.60, 0.08, 0.15, 0.25, 0.50, 0.25, 0.04, 0.20, 0.45),
    "optimistic": (0.75, 0.12, 0.20, 0.35, 0.60, 0.15, 0.03, 0.20, 0.40),
}

T_LIST = [8, 16, 20, 24, 28, 32, 40, 47]
G_LIST = [3, 4, 5]


def mcnemar_p(x0, xg):
    b = ((xg == 1) & (x0 == 0)).sum(axis=1)  # gains
    c = ((x0 == 1) & (xg == 0)).sum(axis=1)  # losses
    n = b + c
    pv = np.ones(len(b))
    nz = n > 0
    pv[nz] = binom.sf(b[nz] - 1, n[nz], 0.5)
    return pv


def trend_p(X):
    """X: (S, T, G+1) binary. One-sided permutation-variance normal approx."""
    Gp1 = X.shape[2]
    c = np.arange(Gp1) - (Gp1 - 1) / 2.0
    S_stat = (X * c[None, None, :]).sum(axis=(1, 2))
    xbar = X.mean(axis=2, keepdims=True)
    ss = ((X - xbar) ** 2).sum(axis=2)  # per task
    var_t = (c**2).sum() * ss / (Gp1 - 1)
    var = var_t.sum(axis=1)
    pv = np.ones(X.shape[0])
    ok = var > 0
    pv[ok] = norm.sf(S_stat[ok] / np.sqrt(var[ok]))
    return pv


def run_scenario(name, params, shift=0.0):
    # zlib.crc32, not hash(): Python string hashing is salted per process, and a
    # design-decision record must reproduce byte-for-byte on re-run.
    rng_s = np.random.default_rng(zlib.crc32(name.encode()) + (1 if shift else 0))
    p0 = draw_pool(N_SIMS, N_POOL, rng_s, shift=shift)
    traj = [p0]
    for _generation in range(G_MAX):
        traj.append(gen_step(traj[-1], rng_s, *params))
    P = np.stack(traj, axis=2)  # (S, N, G_MAX+1)
    U = rng_s.random(P.shape)
    X_all = (U < P).astype(np.int8)  # one draw per task per generation
    rows = []
    for G in G_LIST:
        for T in T_LIST:
            Xh = X_all[:, :T, : G + 1]  # held-out = first T (pool order random)
            x0, xg = Xh[:, :, 0], Xh[:, :, G]
            d_tasks = xg.sum(axis=1) - x0.sum(axis=1)
            true_d = (P[:, :T, G] - P[:, :T, 0]).mean(axis=1)
            mc = mcnemar_p(x0, xg)
            tr = trend_p(Xh)
            rows.append(
                dict(
                    scen=name,
                    G=G,
                    T=T,
                    true_dpp=100 * true_d.mean(),
                    p_dir=(d_tasks > 0).mean(),
                    p_ge2=(d_tasks >= 2).mean(),
                    mc05=(mc < 0.05).mean(),
                    mc10=(mc < 0.10).mean(),
                    tr05=(tr < 0.05).mean(),
                    tr10=(tr < 0.10).mean(),
                    disc=100 * ((x0 != xg).mean(axis=1)).mean(),
                    base=100 * (P[:, :T, 0].mean()),
                )
            )
    return rows


def print_rows(rows, title):
    print(f"\n=== {title} ===")
    print(
        f"{'G':>2} {'T':>3} | {'base%':>5} {'trueΔpp':>7} {'disc%':>5} | "
        f"{'P(dir+)':>7} {'P(Δ≥2)':>6} | {'McN.05':>6} {'McN.10':>6} | {'trend.05':>8} {'trend.10':>8}"
    )
    for r in rows:
        print(
            f"{r['G']:>2} {r['T']:>3} | {r['base']:>5.1f} {r['true_dpp']:>7.1f} {r['disc']:>5.1f} | "
            f"{r['p_dir']:>7.2f} {r['p_ge2']:>6.2f} | {r['mc05']:>6.2f} {r['mc10']:>6.2f} | "
            f"{r['tr05']:>8.2f} {r['tr10']:>8.2f}"
        )


all_rows = {}
for name, params in SCENARIOS.items():
    rows = run_scenario(name, params)
    all_rows[name] = rows
    print_rows(rows, f"scenario: {name}")

# harder-pool sensitivity for the moderate scenario
rows_h = run_scenario("moderate", SCENARIOS["moderate"], shift=-0.08)
print_rows(
    [r for r in rows_h if (r["G"], r["T"]) in [(4, 24), (4, 28), (5, 28), (5, 32), (5, 47)]],
    "sensitivity: moderate, harder pool (mean -8pp)",
)

# ---------------- witness representation (hypergeometric) ----------------
print("\n=== witness representation: mode of size M in pool 96, held-out T ===")
for M in (7, 10, 14):
    line = f"mode M={M:>2}: "
    for T in T_LIST:
        p1 = 1 - hypergeom.cdf(0, 96, M, T)
        p2 = 1 - hypergeom.cdf(1, 96, M, T)
        line += f"T={T}: {p1:.2f}/{p2:.2f}  "
    print(line + "  (P>=1 / P>=2 witnesses)")

# ---------------- costs (measured exp002 actuals) ----------------
print("\n=== cost model: $0.62/local held-out ep, $0.70/platform batch ep ===")
for G, B, T in [
    (3, 4, 8),
    (4, 6, 20),
    (4, 8, 24),
    (4, 8, 28),
    (5, 6, 28),
    (5, 8, 28),
    (5, 8, 32),
    (5, 10, 47),
]:
    lo, pl = (G + 1) * T, G * B
    cost = 0.62 * lo + 0.70 * pl
    print(
        f"G={G} B={B:>2} T={T:>2}: {lo:>3} local + {pl:>2} platform = {lo + pl:>3} eps "
        f"≈ ${cost:>6.0f}   tasks used {T + G * B:>2}/96"
    )
