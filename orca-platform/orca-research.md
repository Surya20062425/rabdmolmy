# ORCA Research Notes — SIH 2026 #176 · ISRO · Disaster Management
### Research only — no build. Findings consolidated for submission prep.

---

## 1. Problem restatement (own words)

Build an **Agentic AI-powered conversational platform** that lets marine
stakeholders (fishermen, coastal authorities, disaster management agencies,
researchers, maritime operators) ask natural-language questions and get
*reasoned, evidence-backed* answers — not document retrieval.

Core tension from the statement:
- Not "retrieve a PFZ map" — must *interpret intent, decompose into tasks,
  coordinate multiple specialized agents, retrieve multiple data sources,
  perform spatial-temporal reasoning, synthesize and explain*.
- Must support **Indian regional languages** (detect + respond in same lang).
- Must do **multi-turn** context.
- Must integrate **satellite EO, GIS, weather, oceanographic, marine advisory**
  data from public domain.
- Must be **explainable** — show the reasoning + evidence behind each rec.
- Safety: proactive alerts (weather, waves, lightning, cyclone), geofencing
  (EEZ boundaries, MPAs, restricted waters).

SIH constraints:
- Team of exactly 6 from same college; min 1 female.
- Submission = PDF, max 6 slides, AICTE PPT template.
- Deadline 30 Sep 2026.

---

## 2. Data sources that actually exist (verified via web)

### 2a. Oceanographic — ISRO / NRSC / INCOIS

**Bhuvan (ISRO geoportal)** — `bhuvan-app1.nrsc.gov.in/api/`
- OGC WMS/WFS/WMTS services for Indian EO data.
- WMS endpoints: `https://bhuvan-vec1.nrsc.gov.in/bhuvan/wms`,
  `https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms`,
  `https://bhuvan-ras1.nrsc.gov.in/bhuvan/wms`.
- GetCapabilities `...?SERVICE=WMS&REQUEST=GetCapabilities` lists all layers.
- WFS for vector layers (districts, admin boundaries) — login required for WFS,
  WMS is open.
- **Bhuvan Store** has downloadable SST and chlorophyll products:
  - Chlorophyll OC2/OC4 global 4km, North Indian Ocean 1km — 2-day, 8-day,
    monthly composites. EOS-06 OCM-3 ocean chlorophyll global 4km daily/8-day/
    monthly (Apr 2023–Mar 2026).
  - SST products available similarly.
- Download limits: NRSC open data policy — 20 tiles/day for AWiFS, 20 tiles/
  15'x15' per day for LISS-III, 20 tiles for Cartosat-1 DEM. Moderate-res data
  (LISS-III, AWiFS) free; 1m high-res visualization only.
- Bhuvan accounts: registration optional for viewing; required for download.
- Data access via **Bhoonidhi portal** (`bhoonidhi.nrsc.gov.in`) — free & paid
  EO data ordering.

**EOS-06 (OCM-3)** — ISRO's ocean colour monitor; provides SST + chlorophyll.
This is the ISRO-native SST/chl source the statement points at.

**INCOIS PFZ advisories** — `incois.gov.in/MarineFisheries/PfzAdvisory`
- Daily PFZ advisories for 586 landing centres across 14 sectors (Gujarat →
  Nicobar).
- Based on SST (NOAA-AVHRR, MetOp, MODIS Aqua, Oceansat-II) + chlorophyll +
  surface currents.
- Daily since 2011; now include wind for PFZ shift guidance.
- Distributed via SAMUDRA app, GEMINI devices, SMS, WhatsApp, Telegram, website,
  radio, harbour boards — in regional languages per sector.
- **Sagar Vani** system: multi-channel dissemination, ~8 lakh fishermen covered,
  5-day ocean state forecasts, tsunami alerts, storm surge warnings.
- PFZ effectiveness: 60–70% search-time reduction for pelagic shoals, 30–40%
  for commercial species; CPUE inside PFZ ~2x outside (purse seiners: 3260 kg
  vs 1616 kg per haul). Extra ~₹18,000/trip average.
- Advisories suspended during fishing bans, cyclones, high waves, tsunamis;
  excluded from MPAs and turtle nesting grounds.

**INCOIS data/products** — research publications, ocean state forecasts.
The SAMUDRA app and Sagar Vani are existing dissemination infrastructure ORCA
could *augment* with conversational + agentic reasoning, not replace.

### 2b. Weather — IMD

**IMD APIs** — `api.imd.gov.in`
- Marine APIs: Port Warning, Sea Area Bulletin, Coastal Bulletin, Fishermen
  Warning.
- City weather forecast (7-day), lat/lon forecast, subdivision rainfall, state
  district rainfall, all-India bulletin.
- Requires account; terms & conditions; contact nodal officer.
- NWP division: WRF 3km, GFS T-1534, GEFS — marine products include 10m wind,
  rainfall, MSLP charts.
- Marine forecast pages: `mausam.imd.gov.in/responsive/marine_forecast.php`
  — fishermen warnings by coastal sector, sea area bulletins for Bay of Bengal
  & Arabian Sea.

**Open-Meteo Marine API** — `open-meteo.com/en/docs/marine-weather-api`
- Free for non-commercial; hourly wave forecasts 5km resolution.
- Sources: MeteoFrance MFWAM (global 3-5km), ECMWF WAM (9km), NCEP GFS Wave
  (0.25°), DWD EWAM (Europe 5km).
- Variables: wind speed/direction, wave height, swell, currents, tides.
- 7-day default, up to 16-day. No API key for non-commercial.
- Good fallback/supplement to IMD for global models; for an ISRO-sponsored
  Indian-domain solution, IMD + INCOIS are the primary sources, Open-Meteo as
  cross-check.

### 2c. Geospatial — boundaries, EEZ, MPAs

**Marine Regions / Flanders Marine Institute** — `marineregions.org`
- World EEZ v12 (2023, 122MB shapefile/GeoPackage) — global EEZ polygons.
- India EEZ: MRGID 8480, bounds ~4.79°N–24.09°N, 65.64°E–89.37°E.
- Contiguous zone (24nm), territorial seas (12nm) also available.
- Also: IHO sea areas, Longhurst marine provinces, UNESCO marine sites.
- REST/OGC services available; shapefiles downloadable.

**ESRI Maritime Boundaries** — ArcGIS REST service,
`services6.arcgis.com/62zavqsrcK71xG8O/ArcGIS/rest/services/Maritime_Boundaries_(low_Res)/MapServer`
- EEZ, territorial seas, contiguous zones, internal waters, archipelagic
  waters, high seas — as ArcGIS MapServer (WMS-like). Good for web map tiling.

**Bhuvan** also has Indian admin boundaries (districts, villages) as WMS/WFS —
useful for coastal district-level context.

**MPAs / restricted waters** — India has coastal MPAs (e.g., Gahirmatha,
Bhitarkanika, Gulf of Kutch, Malvan, etc.), turtle nesting grounds, seasonal
fishing closure zones (mandatory monsoon bans on east & west coasts). These need
to be compiled — some from Wildlife Institute of India / MoEFCC, some from
INCOIS PFZ exclusions (INCOIS already excludes MPAs and turtle nesting grounds
from PFZ).

### 2d. Other relevant sources

- **NASA Earthdata / CMR** — GHRSST L4 SST (AVHRR_OI), MODIS chlorophyll,
  OpenDAP/ERDDAP access. `earthaccess` Python library for search & download.
- **Copernicus Marine Service** — global SST, chlorophyll, wave, current
  reanalysis/forecast (free for registered users).
- **ERDDAP servers** — NOAA CoastWatch, PIFSC, many ocean data providers serve
  subsettable netCDF/CSV via ERDDAP; good for point/time-series extraction.
- **pygeofetch** — unified CLI/Python for 22+ EO providers including `isro_bhuvan`
  (Resourcesat, Cartosat), Sentinel, Landsat, etc. Production-oriented with
  auth, STAC, parallel download, preprocessing.

---

## 3. Agentic AI — framework landscape (2025–2026)

Three dominant open-source frameworks, each with a different orchestration shape:

**LangGraph** (LangChain ecosystem, MIT, ~30k stars)
- Shape: explicit directed graph (StateGraph). Nodes = functions/LLM calls/
  tools; edges = deterministic or conditional transitions. Shared `State` object.
- Strengths: fine-grained control, checkpointing/recovery (checkpointer → SQLite/
  Postgres, resume after failure), human-in-the-loop breakpoints, LangSmith
  observability (traces, token analytics, time-travel debugging), parallel
  branches, production maturity (used at Klarna/Replit/Elastic).
- Weaknesses: steeper learning curve; you design the graph yourself.
- 1.0 GA Oct 2025. Current recommendation for production stateful multi-agent.

**CrewAI** (MIT, ~50k stars, v1.14.3 Apr 2026)
- Shape: role-based crews. Agent = role + goal + backstory; Task; Crew with
  process = sequential | hierarchical (manager agent) | consensual. Flows add
  deterministic control on top.
- Strengths: fastest prototype; intuitive mental model; built-in tools (web
  search, file ops); SQLite persistence; 100+ integrations; MCP support; Ollama
  local runtime.
- Weaknesses: less fine-grained control; state management basic; no checkpoint/
  recovery; role drift risk.
- Good for rapid prototyping, content/support/research pipelines.

**AutoGen / Microsoft Agent Framework** (CC-BY-4.0, ~57k stars)
- AutoGen v0.4: async event-driven, ConversableAgent + GroupChat. Conversational
  multi-agent; built-in code execution (Python in sandbox); GroupChat with
  speaker selection.
- Status: AutoGen in **maintenance mode** (bug fixes only). Successor = **Microsoft
  Agent Framework (MAF)** 1.0 GA Apr 2026 — merges AutoGen + Semantic Kernel;
  graph-based workflows, OpenTelemetry, Python + .NET.
- Strengths: agent-to-agent negotiation; code execution loop; cross-process.
- Weaknesses: AutoGen is maintenance; MAF is Microsoft-stack-oriented.

**OpenAI Agents SDK** — lightweight, tool-centric, agent handoffs, MCP support,
built-in tracing. Good for tightly scoped assistants.

**Google ADK** — Apache 2.0, GCP-native, opinionated agent runtime.

**ReAct pattern** (Reason + Act) — the dominant agent design: interleave
reasoning (chain-of-thought) with action (tool call), observe, repeat. Most
frameworks implement variants. CoT decomposes; ReAct interleaves plan+execute.

**Key architectural primitives across all**:
- Planner: decomposes goal → steps (CoT-based).
- Memory: short-term context + longer-term facts; frameworks vary (LangGraph
  State+checkpointer strongest; CrewAI per-run + entity memory; AutoGen shared
  message context).
- Tool layer: wrap APIs/functions with schemas the model calls (function calling,
  `@tool` decorators, Extensions).
- Orchestrator: decides what runs next (graph edges / crew process / async dispatch).
- Executor: performs the action.

**Hybrid pattern common in practice**: LangGraph as orchestration backbone (state,
control, observability) + specialized agent teams (CrewAI roles or AutoGen
conversations) for subtasks. For ORCA: a graph orchestrator with ocean/weather/
geospatial/risk specialist nodes is the natural fit — ORCA's flow is a directed
pipeline with conditional branches (safe/unsafe/caveat), exactly what LangGraph
edges model well.

**Open-source local LLM option**: Ollama — CrewAI and LangChain integrations
exist; relevant if the submission wants to claim "runs on modest hardware / offline
capability for fishing communities with poor connectivity."

---

## 4. Conversational + domain reasoning patterns

What ORCA needs beyond simple RAG:

1. **Intent classification + slot filling** at ingest — is the user asking for
   PFZ, safety, conditions, alerts, route, trend explanation? Extract location,
   time window, vessel type if mentioned.

2. **Language detection + multilingual response** — detect Indian regional lang;
   respond in same. INCOIS already does regional-language PFZ text per sector —
   ORCA can build on that. Fallback to English.

3. **Multi-turn context** — user refines ("tomorrow morning" → "actually evening"),
   adds location, asks follow-up ("why?").

4. **Tool-using agents** — agents call real data APIs (Bhuvan OGC, INCOIS PFZ,
   IMD marine APIs, Open-Meteo, Marine Regions) as tools, not just retrieve docs.

5. **Spatial-temporal reasoning** — correlate SST + chlorophyll + wind + wave at
   a location and time; compare today vs forecast; find nearest PFZ; check geofence.

6. **Explainable output** — every recommendation carries evidence chain: which
   agents fired, which data points, what thresholds, what trade-offs. Not just
   "go" / "no-go" — the *why*.

7. **Synthesis over retrieval** — the statement explicitly says "should not merely
   retrieve information from individual datasets but intelligently correlate
   observations from multiple sources." The value is in the correlation + reasoning,
   e.g., "SST is favourable and chlorophyll is high here, BUT wave height forecast
   exceeds 2.5m tomorrow morning and you're within 15km of the EEZ boundary, so
   NO-GO with these reasons."

---

## 5. What a strong SIH submission for ORCA should contain

### Architecture (the differentiator)

Multi-agent with clear roles + a coordinator. The statement explicitly suggests:
planning, marine data discovery, weather intelligence, ocean analytics, geospatial
reasoning, risk assessment, visualization, reporting, user interaction agents.

A defensible architecture:

```
User (NLW / regional lang) → Orchestrator
  ├─ language detection + intent classification + slot fill
  ├─ planning agent → task graph
  ├─ parallel leaf agents:
  │     ocean agent (SST, chl, PFZ, trends, correlations)
  │     weather agent (wind, wave, swell, lightning, cyclone, forecast window)
  │     geospatial agent (coords, distance, geofence: EEZ/MPA/restricted)
  ├─ risk agent → GO/CAUTION/NO-GO + evidence
  └─ response agent → NL answer in detected lang + evidence chain + map/chart refs
```

Explainable by construction: the response agent emits the reasoning chain
(explicitly requested in the problem).

### Data integration story (ISRO credibility)

Lead with ISRO sources: Bhuvan OGC services + EOS-06 OCM-3 SST/chlorophyll +
Bhuvan admin boundaries. supplement with INCOIS PFZ + IMD marine APIs + Marine
Regions EEZ shapefile. This shows you understand the actual ISRO ecosystem, not
just generic "satellite data."

### Agentic AI credibility

Don't just say "multi-agent." Show:
- The decomposition (example: "safe to venture tomorrow" → task graph with 4 leaf
  agents + risk fusion).
- Tool selection (which API each agent calls).
- Collaboration (orchestrator routes; risk agent fuses weather+ocean+geospatial).
- Explainability (evidence chain in every response).
- Optionally name a framework: LangGraph for the graph+checkpoint+observability
  backbone, or CrewAI for rapid role-based prototype. Given SIH is a proposal +
  6-slide PDF, naming the framework + justifying it is a plus.

### Safety & geofencing (disaster management theme)

- Safety gates: risk agent must surface alerts before fishing advice.
- Geofencing always-on: EEZ boundary proximity, MPAs, restricted zones, turtle
  nesting grounds (INCOIS already excludes these from PFZ — align with that).
- Proactive alerts: adverse weather, high waves, lightning, cyclone.
- Route optimization with safety: segment route into waypoints, check each.

### Regional language + accessibility

- Language detection + regional-language response (INCOIS already does this per
  sector — leverage their existing translations as a data source, extend to
  conversational).
- Low-connectivity consideration: conversational interface that can work with
  cached/advisory data when live APIs are unavailable (fishing communities often
  have poor connectivity at sea).

### Demo scenarios (cover the 8 example queries from the statement)

1. Nearest PFZ today
2. Safe to venture tomorrow morning?
3. Tide/weather/sea conditions near my location
4. Lightning/cyclone alerts in my area
5. High chlorophyll + favourable SST regions
6. Safest route for a fishing vessel
7. Why fish productivity declined in a region
8. Zones to avoid (hazardous + geofencing)

### What makes this #5 for ISRO specifically

- ISRO sponsor = space/satellite credibility. Anchor data story in ISRO sources
  (Bhuvan, EOS-06 OCM-3, NavIC for positioning/safety-of-life alerts — NavIC
  IRNSS-1A does safety-of-life alert dissemination + INCOIS messages via NavIC
  messaging, IMO recognized NavIC for maritime).
- Agentic AI is the current frontier — multi-agent orchestration, not just RAG.
- Marine + geospatial + conversational is an unusual combo; the integration story
  is the novelty.
- Real deployment target: fishing community decision support — tangible social
  impact (aligns with disaster management theme + ISRO's societal applications
  mandate).

NavIC angle worth mentioning: IRNSS-1A safety-of-life alert dissemination service
+ INCOIS messages via NavIC messaging (ICD exists) — ORCA could be positioned as
the *conversational reasoning layer* that consumes NavIC/INCOIS safety messages +
satellite EO data and explains them to fishermen in their language. That's a
concrete ISRO integration beyond generic "satellite data."

---

## 6. Submission format reality check

- PDF, max 6 slides, AICTE PPT template. That's ~6 slides of content. So the
  proposal must be tight: problem understanding, architecture diagram, agent
  design, data sources, safety/geofencing, demo scenarios. No room for lengthy
  prose — diagram-heavy.

- 6 team members from same college, min 1 female. Role split opportunity:
  1× architecture/agent design lead, 1× ocean+PFZ data integration, 1× weather+
  safety, 1× geospatial+geofencing, 1× conversational+multilingual+UI, 1×
  integration/testing/submission lead. Adjust to actual team.

---

## 7. Open questions / gaps to resolve before finalizing proposal

- **Which LLM backend?** Submission can propose: cloud LLM API (OpenAI/Gemini)
  for the conversational reasoning layer, with Ollama-local fallback for
  offline-capability demo. Decision affects feasibility claims.
- **Live data access in demo?** Bhuvan OGC WMS is open; WFS needs login; INCOIS
  PFZ is web-accessible (maps + text); IMD APIs need account. For a 6-slide
  proposal, showing the *integration design* with these sources is enough; a
  working demo connecting all of them is likely out of scope for the submission
  itself (SIH usually expects a working prototype at later stages, but the
  submission is the PDF proposal). Clarify stage: is this just the submission PDF,
  or does the team need a working prototype by submission deadline (30 Sep)?
- **Multilingual — which languages?** Statement says "emphasis on Indian regional
  languages." INCOIS covers Tamil, Malayalam, Telugu, Kannada, Hindi, Marathi,
  Gujarati, Bengali, Odia for PFZ per sector. Align ORCA's language list to that.
- **Geofencing data completeness** — India's MPA list + seasonal fishing closures
  + EEZ boundary need to be compiled from WII/MoEFCC + Marine Regions EEZ shapefile
  + INCOIS PFZ exclusion zones. This is real work; for the proposal, list the
  sources and the approach.
- **NavIC integration depth** — mentioning INCOIS messages via NavIC messaging +
  safety-of-life alerts as a data source is credible; building an actual NavIC
  receiver integration is hardware (out of scope for software track). Position as
  "consumes NavIC/INCOIS safety messages as an input channel" not "builds a NavIC
  receiver."

---

## 8. Sources (for citation in proposal)

- INCOIS PFZ Advisory: https://incois.gov.in/MarineFisheries/PfzAdvisory
- INCOIS Sagar Vani / SAMUDRA / coverage: UPSC current affairs summaries (Apr &
  Jul 2026), INCOIS research publication RP_2026.
- Bhuvan API & OGC services: https://bhuvan-app1.nrsc.gov.in/api/ ,
  https://bhuvan-vec1.nrsc.gov.in/bhuvan/wms , India Data Atlas Bhuvan OGC guide.
- Bhuvan Store SST/chlorophyll products: https://bhuvan-app1.nrsc.gov.in/
  2dresources/bhuvanstore.php (EOS-06 OCM-3, OC2/OC4 products).
- NRSC open data policy / Bhoonidhi: https://bhuvan.nrsc.gov.in/wiki/
  Frequently_Asked_Questions , https://www.isro.gov.in/
  SpaceBasedEarthObservationServices.html
- IMD marine APIs: https://api.imd.gov.in/api/v1/seabulletin , API reference,
  NWP marine products.
- Open-Meteo Marine API: https://open-meteo.com/en/docs/marine-weather-api
- Marine Regions EEZ v12 / India EEZ (MRGID 8480): https://www.marineregions.org/
- ESRI Maritime Boundaries ArcGIS service.
- NavIC / IRNSS safety-of-life alert + INCOIS messaging: https://new1.isro.gov.in/
  SatelliteNavigationServices.html , https://www.isro.gov.in/Navigation.html ,
  IMO MSC.449(99) IRNSS receiver performance standards.
- Agentic frameworks: JetThoughts LangGraph/CrewAI/AutoGen 2025 comparison;
  Meta-Intelligence 2026 comparison; Galileo AutoGen/CrewAI/LangGraph/OpenAI;
  LangChain "best AI agent frameworks in 2026"; BestAIWeb agent framework deep dive.
- Python geospatial SST/chl extraction: NOAA CoastWatch EDMW 2024 tutorial
  (earthaccess + xarray + geopandas + regionmask), ERDDAP shapefile extraction
  tutorial, Python Geospatial raster sampling guide.
- pygeofetch: https://pypi.org/project/pygeofetch (unifies ISRO Bhuvan + 22+
  providers).
