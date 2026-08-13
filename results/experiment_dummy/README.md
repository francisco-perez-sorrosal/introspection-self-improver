# experiment_dummy — pre-freeze bring-up bucket

The default experiment for runs produced while `benchmark_lock.yaml` is `PROVISIONAL`.
Nothing here is a reportable result: the runs under it were produced under shifting
bring-up configurations (including one deliberate model excursion, `task_001_sonnet5`),
so the directory carries no `experiment.yaml` freeze snapshot and never will — snapshot
enforcement starts with the first non-`PROVISIONAL` lock.

The real experiment begins when the freeze is re-decided before G0: a new `experiment.id`
in the lock, a sibling `results/experiment_<id>/` directory, and a snapshot written on its
first run.
