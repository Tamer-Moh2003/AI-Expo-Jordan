# 🚦 Methodology & Engineering Assumptions

This document outlines the traffic engineering principles, formulas, and baseline assumptions used by the M2 (Data & Forecasting) team to generate the synthetic dataset for the Wadi Saqra intersection and compute signal phase recommendations. 

## 1. Synthetic Traffic Data Generation
To accurately simulate vehicle arrivals at the intersection without relying on naive random generation, we utilized the **Poisson Distribution Model**, a standard probabilistic approach in traffic flow theory for modeling isolated vehicle arrivals in uncongested to moderately congested states.

* **Mathematical Model:**
  The probability of exactly $k$ vehicles arriving in a specific time interval is given by:
  $$P(k) = \frac{\lambda^k e^{-\lambda}}{k!}$$
  Where $\lambda$ represents the expected (average) vehicle count based on the predefined time-of-day and day-of-week volume profiles (e.g., AM/PM peaks, Friday prayer drop-offs).

* **Source/Reference:** Gerlough, D. L., & Huber, M. J. (1975). *Traffic Flow Theory: A Monograph*. Transportation Research Board.

## 2. Signal Phase & Timing (SPaT) Calculations
For the recommendation engine, the green duration and optimal cycle length are not arbitrarily chosen. They are grounded in **Webster’s Optimum Cycle Length Equation**, a globally recognized traffic engineering standard.

* **Optimal Cycle Length Equation:**
  $$C_{opt} = \frac{1.5L + 5}{1 - Y}$$
  Where:
  * $C_{opt}$ = Optimal cycle length (in seconds).
  * $L$ = Total lost time per cycle (assumed 4 seconds per phase).
  * $Y = \sum \left(\frac{q_i}{s_i}\right)$ = Sum of the critical flow ratios for all phases.

* **Explicit Labelled Assumption (Saturation Flow Rate):**
  We establish a constant **Saturation Flow Rate ($s$)** of **1,800 vehicles/hour/lane**. This is a standard baseline assumption for urban intersections with mixed traffic conditions similar to Amman.

* **Source/Reference:**
  * Webster, F.V. (1958). *Traffic Signal Settings*. Road Research Technical Paper No. 39.
  * *Highway Capacity Manual (HCM)*. Transportation Research Board, National Academies of Science.

## 3. Incident Queue Estimation
When an incident (e.g., stalled vehicle, accident) is detected by the M1 vision pipeline, the queue estimation heavily relies on the interrupted flow mechanics. The reduction in the saturation flow rate ($s$) forces the queue to build up at a rate proportional to the base demand minus the restricted capacity.