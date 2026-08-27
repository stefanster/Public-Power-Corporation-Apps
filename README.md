# Aegean Fuel Command v2.1

A single-file Streamlit prototype for planning fuel deliveries from **Lavrio** to power stations on **Sifnos, Milos, Paros, Santorini, and Limnos** using the vessels **PPC Star Delos, PPC Star Naxos, and PPC Star Chios**.

The app includes synthetic station inventories and demand history, vessel data, ship-availability calendars, multi-island voyages, dispatch planning, voyage maps with ship labels, ETA/cargo tables, and scenario controls.

## Files

```text
.
├── main.py
├── requirements.txt
└── README.md
```

No CSV files, database, API keys, or external data files are required for this demonstration build.

## Run locally in PyCharm

1. Create/open a PyCharm project and put these three files in the project root.
2. Select your Python virtual environment/interpreter.
3. Recommended: install the dependencies once:

```bash
pip install -r requirements.txt
```

4. Open `main.py` and press **Run**.

`main.py` detects an ordinary Python/PyCharm launch and relaunches itself correctly through Streamlit. If a required package is missing, the launcher will attempt to install it into the active interpreter.

You can also start it explicitly from a terminal:

```bash
streamlit run main.py
```

## Publish it so anyone with the link can view it

### 1. Create a GitHub repository

Create a repository such as:

```text
aegean-fuel-command
```

Upload the three files from this package to the repository root and commit them.

### 2. Deploy on Streamlit Community Cloud

1. Go to **https://share.streamlit.io/** and sign in with GitHub.
2. Choose **Create app**.
3. Select your GitHub repository and branch (normally `main`).
4. Set the app entrypoint/file path to:

```text
main.py
```

5. Choose an available app subdomain, for example `aegean-fuel-command`.
6. Deploy the app.
7. Make sure the app's sharing/visibility setting is **public** if you want anyone with the URL to open it.

Your public link will look similar to:

```text
https://aegean-fuel-command.streamlit.app
```

Anyone with that public URL can use the dashboard in a browser; they do not need Python, PyCharm, or Streamlit installed.

## Updating the public app

GitHub is the source for the deployed application. Edit `main.py`, commit, and push the change to the same repository. Streamlit Community Cloud will pick up the update while the app URL remains the same.

## Prototype disclaimer

All vessel, station, inventory, capacity, demand, consumption, handling, and voyage assumptions are hypothetical. Distances are simplified for demonstration. Production deployment should add validated operational data, navigational routing, berth/port windows, weather restrictions, vessel compatibility, costs, bunker consumption, regulatory constraints, and a formal optimization engine.
