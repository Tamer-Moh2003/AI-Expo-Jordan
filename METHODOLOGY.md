# 🚦 Methodology & Engineering Assumptions for Wadi Saqra Intersection

This document outlines the traffic engineering principles, practical calculations, and baseline assumptions used to generate the synthetic dataset and signal timing models for the Wadi Saqra intersection. Our goal is to ensure the dataset strictly reflects real-world urban traffic dynamics rather than relying on naive random generation.

## 1. Traffic Volume & Peak Hour Estimation
To accurately model the traffic flow and congestion bottlenecks, we avoided arbitrary volume generation. Instead, we analyzed real-time and historical traffic layers using **Google Maps**.
* By examining the traffic color codes (Green, Orange, Red, Dark Red) at different times of the day, we identified the exact peak hours (AM/PM) and the specific approaches that suffer from the most severe congestion.
* This analysis formed the baseline for our vehicle generation rates, ensuring the synthetic data accurately mimics the real spatial and temporal distribution of vehicles at this specific intersection.

## 2. Signal Phase & Timing (SPaT) Calculations
Our cycle length and green duration assumptions are mathematically derived from standard traffic engineering practices, specifically incorporating realistic lost times and vehicle headway. 

Based on our intersection analysis, a full signal cycle was calculated at **220 seconds** (approximately 3.5 minutes), derived from the following breakdown:

* **Lost Time (Clearance Interval):** 
  Every phase includes a standard safety delay to ensure the intersection is completely cleared before releasing the next traffic stream. We allocated **5 seconds of lost time per phase** (3 seconds Yellow + 2 seconds All-Red). 
  For a standard 4-phase intersection, this results in a total of **20 seconds of dead time** per full cycle where no vehicles can move.

* **Phase Duration Allocation:**
  * **Arar Street (Northbound):** 60 seconds green + 5 seconds lost time = **65 seconds**
  * **Arar Street (Southbound):** 60 seconds green + 5 seconds lost time = **65 seconds**
  * **Side Street (Eastbound):** 40 seconds green + 5 seconds lost time = **45 seconds**
  * **Side Street (Westbound):** 40 seconds green + 5 seconds lost time = **45 seconds**
  * **Total Optimal Cycle Length ($C$):** 65 + 65 + 45 + 45 = **220 seconds**

## 3. Vehicle Crossing Capacity & Physical Bottlenecks
To calculate the exact number of vehicles that can clear the intersection during a green phase, we established a realistic reaction and movement time per vehicle, mapped directly to the physical geometry of the Wadi Saqra intersection.

* **Headway Assumption:** We assumed that one vehicle requires exactly **2 seconds** to cross the stop line (accounting for driver reaction time and acceleration).
* **Throughput per Lane:** During a 60-second green phase on the main approach, the maximum throughput is:
  $$ \text{Capacity per lane} = \frac{60 \text{ seconds}}{2 \text{ seconds/vehicle}} = 30 \text{ vehicles/lane} $$
* **Physical Bottleneck Modeling (Arar Street):** 
  The North, East, and West approaches at this intersection feature 5 lanes, while **the South Arar Street approach is restricted to 3 lanes**. This creates a severe structural bottleneck that our model explicitly accounts for.
  * Total capacity for 5-lane approaches: $30 \times 5 = 150 \text{ vehicles per green phase}$
  * Total capacity for Arar Street (3 lanes): $30 \times 3 = 90 \text{ vehicles per green phase}$
* This explicit geometric constraint (a 40% reduction in total throughput compared to the 5-lane approaches) is factored into the signal-advisor capacity calculation and explains why Arar Street can experience rapid queue buildup during peak hours.

## 4. Probabilistic Arrival Generation
While the maximum capacity is fixed, actual vehicle arrivals are randomized using the **Poisson Distribution Model**, a standard approach in traffic flow theory for uncongested to moderately congested states.
* The probability of exactly $k$ vehicles arriving in a specific time interval is:
  $$P(k) = \frac{\lambda^k e^{-\lambda}}{k!}$$
  Where $\lambda$ represents the expected vehicle count based on our Google Maps peak hour analysis.
