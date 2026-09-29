# ORCA — Marine EcOsystem Reasoning with Collaborative Agents
### SIH 2026 · Problem #176 · ISRO Sponsor · Disaster Management Theme

**Agentic AI-powered conversational platform** for marine decision support —
fishermen, coastal authorities, disaster management agencies, researchers.

[Architecture](architecture.md) · [Full research notes](orca-research.md)
· [Problem statement extract](problem_statement.txt)

---

## What it does

Natural-language platform that interprets a marine query, decomposes it across
specialized AI agents, retrieves satellite/ocean/weather/geospatial data,
performs spatial-temporal reasoning, and returns explainable recommendations
with maps and alerts.

Example queries handled:

- "Where is the nearest Potential Fishing Zone today?"
- "Is it safe to venture into the sea tomorrow morning?"
- "Tide, weather, and sea conditions near my fishing location?"
- "Lightning or cyclone alerts in my area?"
- "Which regions show high chlorophyll and favourable SST?"
- "Safest route for a fishing vessel considering weather and sea-state?"
- "Why has fish productivity declined in this coastal region?"
- "Which fishing zones to avoid due to hazardous conditions or geofencing?"

## Multi-agent architecture

```
                    User query (natural language / regional language)
                              │
                    ┌─────────┴─────────┐
                    │   ORCHESTRATOR     │
                    │  intent + lang ID  │
                    └─────────┬─────────┘
                              │ decompose
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────┴───┐  ┌───────┴───────┐  ┌────┴────────┐
    │  PLANNING   │  │   OCEAN      │  │  WEATHER    │
    │  AGENT      │  │  AGENT       │  │  AGENT      │
    │ decompose,  │  │ SST, Chl,    │  │ wind, wave, │
    │ task graph, │  │ PFZ, trends, │  │ cyclone,    │
    │ routing     │  │ correlations │  │ alerts      │
    └───────┬─────┘  └───────┬───────┘  └──────┬──────┘
            │                 │                 │
            └────────┬────────┴─────────────────┘
                     │ aggregate + correlate
            ┌────────┴────────┐
            │  GEOSPATIAL     │
            │  AGENT          │
            │ geofencing,    │
            │ routing, coords │
            └────────┬────────┘
                     │
            ┌────────┴────────┐
            │  RISK + RESP.   │
            │  ASSESS → reply │
            │ alerts, evidence│
            │ multilingual    │
            └─────────────────┘
```

- **Orchestrator** — language identification, intent classification, multi-turn
  context, agent routing.
- **Planning Agent** — decomposes complex requests into an executable task graph,
  decides ordering and which agents to invoke.
- **Ocean Agent** — Sea Surface Temperature, chlorophyll concentration, PFZ
  detection, productivity trend analysis, cross-parameter correlation.
- **Weather Agent** — wind speed/direction, wave height, swell, lightning,
  cyclone alerts, forecast windows.
- **Geospatial Agent** — lat/lon ops, distance, geofencing (international
  boundaries, marine protected areas, restricted waters), route reasoning.
- **Risk Agent** — synthesizes safety assessment from weather + ocean + geospatial,
  generates alerts and avoidance recommendations.
- **Response Agent** — assembles evidence-backed answer, explains reasoning chain,
  responds in detected language (Indian regional language support), renders
  map/chart pointers.

### Data sources integrated (public domain)

| Source | Used for |
|---|---|
| ISRO satellite EO (SST, chlorophyll) — Bhuvan OGC | ocean agent |
| INCOIS PFZ advisories | ocean agent |
| IMD weather forecasts / alerts — api.imd.gov.in | weather agent |
| Open-Meteo Marine API (global wave/wind) | weather agent |
| Survey of India nautical charts / boundaries — Marine Regions EEZ | geospatial agent |
| Marine protected area / EEZ geofences | geospatial agent |

## Getting started

```bash
python3 orca.py --demo     # run all 8 demo queries from the problem statement
python3 orca.py            # interactive conversational mode
```

No external dependencies — pure Python 3 stdlib. Sample marine data embedded
to demonstrate the full agentic reasoning pipeline. Real API integrations
(Bhuvan, INCOIS, IMD, Open-Meteo, Marine Regions) plug in behind the same
agent interfaces.

## Demo output

```
DEMO 1: Where is the nearest potential fishing zone today near Kochi?

  ORCA [English]:
  Recommendation: Nearest Potential Fishing Zone (PFZ): high productivity
  for mackerel, sardine at (10.5, 76.8), 25.0 km from your location...
```

Full 8-query demo runs in < 1 second.

## Submission

`orca_submission.pdf` — 6-slide AICTE-format proposal (platform overview,
architecture, agent design, data integration, safety & geofencing, demo scenarios).

Built for **SIH 2026 · Problem #176 · ISRO · Disaster Management**.
