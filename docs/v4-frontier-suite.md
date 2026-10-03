# V4 frontier discovery suite

V4 is the integrated controlled-research layer of WorldModel.

## What it tests

The suite asks whether the same discovery architecture can:

1. recover intervention-relevant latent coordinates across several synthetic domains;
2. beat a PCA representation baseline;
3. infer useful environment changes from passive natural experiments;
4. recover compact symbolic latent dynamics;
5. jointly choose an ontology and a dynamical law;
6. assign high probability to `__unknown__` when the supplied hypothesis family is incomplete;
7. invent a missing symbolic interaction from residual structure;
8. split or merge latent concepts when the evidence warrants it;
9. prefer an experiment that trades information gain against performative feedback;
10. seal a prospective claim before its synthetic outcome is revealed.

Run:

```bash
worldmodel frontier --seed 7
```

The returned `checks` dictionary is the falsification gate. The canonical seed is expected to make every gate pass.

## Scientific boundary

Passing V4 means the implementation succeeds on controlled worlds whose hidden structure is known to the evaluator. It does **not** establish autonomous discovery of a previously unknown law in nature, economics, or markets.

The next scientifically meaningful step is a frozen prospective protocol on external real-world data, followed by independent replication.
