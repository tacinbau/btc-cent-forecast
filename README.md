# BTC cent forecast 01 — entry

Forecast Bitcoin's US-dollar price 240 minutes (4 hours) after each
checkpoint, from the 72 hours of 1-minute closes up to it. One program,
`main.py` (Python 3.13, standard library only, no network), reads each case
at `/input/<id>.in` and writes one guess to `/output/<id>.out`:

```json
{"forecasts": [{"case": "p00", "price": 74765.5594}]}
```

## Model

1. **Spike-robust base.** The checkpoint close comes from a single Orca pool
   and occasionally dislocates for a minute (a −1.63% one-minute print in the
   practice data reverts within minutes). If the last close deviates from the
   median of the last 15 closes by more than 0.3% (log terms), the close is
   treated as dislocated and the 15-minute median is used instead; otherwise
   the last close itself is the base.
2. **Damped trend.** OLS slope of log price on 15-minute medians over the last
   720 minutes, extrapolated 240 minutes and damped by 0.3, clamped to ±3%
   (never binds on practice data — a guard against a wild guess on unseen
   data).

Deterministic: two runs on the same case write identical bytes. Runs in
~0.01 s per case (limit 8 s).

## Validation (kit practice cases)

Walk-forward, checkpoints 4 hours apart inside each case's 72 h window
(90 points):

| model | mean abs error |
|---|---|
| persistence baseline | 41,787 cents |
| this entry | 33,315 cents (−20.3%) |

On the five practice answers reconstructable from the kit (each answer is
the next case's checkpoint close): persistence 47,055 cents, this entry
45,417 cents (−3.5%). It beats persistence in all six practice cases at
4-hour spacing. The stated practice baseline for the full six cases is
44,521.576667 cents.

## Run locally

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=kit/btc-cent-forecast-01-kit/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## License

MIT — see `LICENSE`.
