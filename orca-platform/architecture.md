# ORCA — Architecture & Design Notes
### SIH 2026 #176 · ISRO · Disaster Management

## Design principles

1. **Agentic, not RAG.** The platform decomposes a query into tasks, routes them
   to specialists, and correlates outputs — not a single retrieval step.
2. **Explainable by construction.** Every recommendation carries the evidence
   chain: which agents fired, which data points supported it, what trade-offs
   were considered.
3. **Safety-first for fishermen.** Risk agent gates recommendations: if weather
   or sea-state crosses thresholds, the answer surfaces alerts before fishing
   advice.
4. **Geofencing always on.** Any coordinate-based result is checked against
   EEZ boundaries, marine protected areas, and restricted zones before surfacing.
5. **Regional-language first.** Language detection at ingest; response in same
   language. Indian regional languages prioritised (Tamil, Malayalam, Telugu,
   Kannada, Hindi, Marathi, Gujarati, Bengali, Odia).

## Agent contract

Every agent implements:

```python
class Agent:
    def run(self, task: dict, context: dict) -> dict:
        """Return {status, result, evidence, next_tasks?}."""
```

`task` carries the sub-problem (parameters, required outputs, constraints).
`context` carries session state: user location, language, conversation history,
previously retrieved data.

## Reasoning flow (example: "Is it safe to venture into the sea tomorrow morning?")

```
User → Orchestrator
  ├─ detect language
  ├─ classify intent = safety_assessment
  └─ set context {location, time_window: tomorrow morning}

Orchestrator → Planning Agent
  ├─ decompose into:
  │   T1 weather_agent: wind, wave, swell for location × tomorrow morning
  │   T2 ocean_agent:   SST, chlorophyll context (productivity background)
  │   T3 geospatial_agent: geofence check at location
  │   T4 risk_agent:   safety synthesis from T1–T3
  └─ return task graph

Leaf agents run (parallel where independent):
  ├─ weather_agent → {wind_kt, wave_m, swell_m, gust_kt, alarm: none/alert/warning}
  ├─ ocean_agent   → {sst_c, chl_mg_m3, pfz_nearby, trend}
  ├─ geospatial_agent → {in_eez, in_mpa, in_restricted, distance_to_boundary_km}

Risk agent fuses:
  ├─ if wave_m > 2.5 OR wind_kt > 25 OR alarm in (alert,warning) → NOT SAFE
  ├─ else if wave_m > 1.5 OR wind_kt > 15 → CAUTION
  └─ else → SAFE, with caveats from ocean + geospatial context

Response agent → plain-language answer + evidence chain + alert if any.
```

## Data model (sample artifacts in `data/`)

- `sst_sample.csv` — gridded SST snapshot (lat, lon, sst_c)
- `chlorophyll_sample.csv` — gridded chlorophyll (lat, lon, chl_mg_m3)
- `pfz_sample.csv` — PFZ points (lat, lon, day, productivity_index)
- `weather_sample.csv` — point forecast rows (lat, lon, valid_time, wind_kt,
  wave_m, swell_m, gust_kt, lightning_risk, cyclone_alert)
- `geozones.csv` — geofence polygons simplified as bounding boxes
  (zone_name, type, min_lat, max_lat, min_lon, max_lon)

Production would substitute live API/Earth Observation product access; the agent
contract stays the same.

## Geospatial reasoning primitives

- **PointInPolygon** — is a coordinate inside a geofence zone?
- **Nearest** — nearest PFZ point / nearest hazardous region to user location.
- **Distance** — great-circle distance between two coordinates.
- **RouteSafety** — segment a candidate route into waypoints, run weather+risk
  at each, flag hazardous segments.

## Safety & geofencing behaviour

- Before any "go to sea" or "fishing zone" answer, geospatial agent checks:
  - International maritime boundary / EEZ limit proximity → geofencing alert.
  - Marine protected area / ecologically sensitive zone → avoidance advisory.
  - Restricted waters (fishery regulation zones) → advisory.
- Risk agent emits at minimum: GO / CAUTION / NO-GO, plus the triggering
  evidence (wind, wave, alert, zone).

## Multilingual handling

1. Ingest: detect language (user location + query text; explicit locale hint
   from session).
2. Plan: pass language to all agents so any data labels / advisories are
   rendered in that language.
3. Respond: Response agent emits final text in detected language; falls back to
   English if a language is not yet supported.

## Demo scenarios covered by `orca.py --demo`

| # | Query | Agents exercised |
|---|---|---|
| 1 | Nearest PFZ today from a given coastal point | planning, ocean, geospatial, response |
| 2 | Safe to venture tomorrow morning? | planning, weather, ocean, geospatial, risk, response |
| 3 | Tide, weather, sea conditions near my location | weather, ocean, geospatial, response |
| 4 | Cyclone / lightning alerts in my area | weather, risk, response |
| 5 | High chlorophyll + favourable SST regions | ocean, geospatial, response |
| 6 | Safest route for a fishing vessel | planning, weather, geospatial, risk, response |
| 7 | Why fish productivity declined in a region | ocean, planning, response (trend + correlation) |
| 8 | Zones to avoid (hazardous + geofencing) | weather, geospatial, risk, response |
