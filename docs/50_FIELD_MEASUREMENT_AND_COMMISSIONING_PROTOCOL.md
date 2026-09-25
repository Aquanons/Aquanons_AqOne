# 50 — Field Measurement and Commissioning Protocol

> **Status:** Approved Protocol for Phase 2 Deployment and Commissioning.  
> **Prepared:** 2026-09-15.  
> **Scope:** Physical instrument qualification, reference sites, calibration standards, clock uncertainty, and spatial representativeness across the New Washington and Batan Bay operating domain (D1).

---

## 1. Reference Sites and Spatial Layout

### 1.1 Geographic Operating Domain (D1 Reference)
The pilot operating domain covers 11.60°N to 11.75°N, 122.40°E to 122.55°E, encompassing:
1. **Outer Bay Exposed Waters:** High-energy maritime boundary subject to Habagat/Amihan sea swells and convective squalls.
2. **Lagatik Offshore Corridor:** Major transit channel connecting municipal landing ports to fishing grounds.
3. **Batan Estuary / Bay Inlet:** Constrained tidal channel characterized by strong reversing tidal currents (up to 2.5 m/s at spring tide) and freshwater stratification.
4. **Coastal Inshore Sectors:** Tambak, Poblacion, Pinamuk-an, Ochando, and Fatima shallows (< 5 m depth).

### 1.2 Reference Instrument Deployments

| Measurement | Instrument Class | Deployment Location | Coordinates | Mounting / Elevation | Reference Standard |
|---|---|---|---|---|---|
| **Surface Wind (10m)** | Ultrasonic 2-axis anemometer | Shore Gateway Tower | 11.6582°N, 122.4331°E | Top of tower, 10 m AGL, unobstructed 360° | WMO No. 8 Chapter 5; 10 Hz acquisition, 1-minute vector average, 3-second gust maximum |
| **Ocean Current Vector** | Bottom-mounted 600 kHz Acoustic Doppler Current Profiler (ADCP) | Batan Channel Throat (Core shipping lane) | 11.6740°N, 122.4790°E | Moored seabed pod at 14 m depth; upward-looking | True north alignment via fluxgate compass + magnetic declination (+1.2°E); 0.5 m bin resolution from 1.0 m to 12.0 m depth |
| **Ocean Waves (Directional)** | Calibrated directional wave buoy (spectral) | New Washington Outer Shoal | 11.7210°N, 122.4550°E | Surface compliant mooring in 18 m depth | WMO Guide to Wave Analysis No. 702; 20-minute burst processing: $H_s, T_p, T_z, \theta_{mean}$ |
| **Water Level / Tide** | Acoustic tide gauge with vented pressure backup | New Washington Municipal Pier | 11.6550°N, 122.4300°E | Still-well mounted on pier pylon | Tied to NAMRIA Tidal Benchmark (TBM-1); 6-minute epoch averages |
| **Vessel GNSS Truth** | Dual-frequency multi-constellation GNSS (L1/L5) | Consented pilot bancas (3 vessels) | Variable within D1 | Deck-mounted logged on flash memory | 1 Hz raw pseudorange/carrier phase logging; post-processed kinematic (PPK) accuracy < 0.1 m |

---

## 2. Sensor Commissioning and Calibration Standards

### 2.1 Squall Data Source (PAGASA Weather API)
- Buoys carry no barometer; there is no pressure sensor to commission.
- Squall alerts are sourced from the PAGASA weather API. Commissioning checks that advisories for the New Washington fishing grounds arrive, are timestamped, and are shown as stale once past the freshness threshold.

### 2.2 Wave Estimation from Buoy Motion
- **Qualification Rule:** Raw 6-axis IMU acceleration without wave-tank or reference wave-buoy calibration is strictly classified as `uncalibrated_motion`.
- Significant wave height ($H_s$) can only be derived after transfer-function validation against the reference directional wave buoy under at least 3 distinct sea states (calm: $H_s < 0.8\text{m}$; moderate: $0.8\text{m} \le H_s < 1.5\text{m}$; rough: $H_s \ge 1.5\text{m}$).
- Buoy pitch/roll and heave response amplitudes must be characterized to correct for buoy hull resonance.

### 2.3 Horizontal Current Vector Conventions
- **Coordinate Frame:** Oceanographic convention (direction towards which the current flows, degrees clockwise from True North).
- **Decomposition:**
  $$u = U \sin(\theta_{true}), \quad v = U \cos(\theta_{true})$$
  where $U$ is current speed in m/s and $\theta_{true}$ is True North direction in degrees.
- **Depth Stratification:** Current observations must explicitly report `depth_m`. Near-surface banca advection utilizes the top bin ($0.5\text{ m} - 1.5\text{ m}$). Deep tidal flows (> 3 m) must not be substituted for surface drift without shear modeling.
- **Forbidden Inferences:** Tidal height changes from tide tables must NEVER be converted to horizontal current velocity without direct ADCP verification.

---

## 3. Clock Uncertainty and Synchronization Protocol

### 3.1 Network Clock Boundaries
1. **Shore Gateway:** Synchronized via NTP with fallback to GNSS PPS. Maximum allowable clock error: $\pm 50 \text{ ms}$.
2. **Buoys:** Non-NTP nodes. Buoys adopt epoch timestamps from verified, signed gateway LoAM frames (`adoptClock()`). Maximum allowable drift: $\pm 5.0 \text{ seconds}$.
3. **Handsets:** Device clock synchronized to network time. The mobile client records both handset system time and GNSS fix time.

### 3.2 Decision Time and Replay Cutoff
- An incoming measurement with `observed_at > now() + 5 minutes` is rejected for clock skew.
- In historical replay or drift evaluation as of $T_{decision}$, any observation with `created_at > T_{decision}` is excluded, regardless of `observed_at`.
- Retrospective runs (reanalysis utilizing late-arrived data) must explicitly carry `is_retrospective: True`.

---

## 4. Estuarine and Channel Representativeness

### 4.1 Inlet Hydrodynamics
- The Batan estuary exhibits strong spatial gradients. Current observations taken inside the estuary throat cannot be extrapolated beyond the outer sandbar.
- Freshwater discharge during heavy monsoonal precipitation creates a buoyant surface layer that can decouple surface banca leeway from deeper tidal currents.

### 4.2 Minimum Qualifying Geometry for Spatial Interpolation
- To support spatial 2D current interpolation (e.g., IDW or Gaussian process):
  - At least 2 active qualified buoys must be reporting within 15 km of the target datum.
  - The observation age must not exceed 3600 seconds (1 hour).
  - If these criteria are not met, the system transitions to `insufficient_environmental_data` and suppresses operational drift contouring.
