# Historical one-game sensitivity (educational)

The mobile **Instant stats** panel computes a leave-one-out sensitivity for each
historical points, rebounds and assists mean. After selecting completed-game
records through a date cutoff, it recalculates the mean after omitting each
selected record in turn. The diagnostic reports the smallest resulting mean,
the largest resulting mean and the greatest absolute change from the original mean.

For values `10, 10, 10, 10, 30`, the sample mean is `14`, the
leave-one-out means range from `10` to `15`, and the largest change is `4`.

This is a **small-sample fragility diagnostic**, not a standard error, confidence
interval, estimated uncertainty of the next game, independence adjustment or
predictive model. It does not fix dataset selection bias, missing minutes,
missing games, provider identity or data rights. No odds, wagers or future-game
probabilities are generated.

The calculation is browser-local, uses only selected historical game logs at
or before the chosen cutoff, does not mutate stored drafts or fetch data,
and preserves independent CSV identity validation.

## Verification

```bash
node --test tests/instant-research.test.cjs
PYTHONPATH=src python3 -m unittest discover -s tests
```

An independently verified source and chronological validation are still
required before interpreting the underlying data as representative.
