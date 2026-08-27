# Aegean Fuel Command v3.0

Single-file Streamlit prototype for PPC island fuel-delivery planning.

## Included

- Embedded PPC Generation Operations Transformation Department logo (no separate image file required)
- Stations & Fleet Data tab
- Vessel availability calendars for PPC Star Delos, PPC Star Naxos and PPC Star Chios
- Rolling-horizon inventory planning across the entire selected planning period
- Repeat replenishment voyages as stations approach safety stock
- Multi-island voyages from Lavrio and back to Lavrio
- Voyage maps with ship-specific colours, ship labels and direction arrows on every leg
- Full vessel schedule and stop-by-stop ETA / cargo details
- Planned inventory trajectory including scheduled deliveries

## Local / PyCharm

Place `main.py` in the project and press **Run**. The script launches itself through Streamlit when executed as ordinary Python.

Or run:

```bash
streamlit run main.py
```

## Streamlit Community Cloud

Upload these files to the root of a GitHub repository:

- `main.py`
- `requirements.txt`
- `README.md`

Then select `main.py` as the Streamlit Cloud entrypoint.

## Important

All operating data in this prototype are hypothetical. Straight-line nautical distances are used for demonstration and are not navigational routes.
