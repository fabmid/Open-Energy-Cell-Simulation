Introduction
============
This example shows how to model a hybrid energy system consisting of a Pv array and Small Scale Windturbine.
Inside the simulation.py file the system configuration is specified.
The component parameters are specified inside the folder data/components/...json.

Attention
---------
Current environmental data has following restrictions:

 * No roughness_length is given and assumed currently to be static 0.1
 * Wind speed is given only at 10m height, in case of high hub height calculation might be inaccurate

Current component data has followign restrictions:
 * Values in general need to be revised with current publications.
 * Maximum Power Point Tracker for Wind turbine data is set to same specifications as PV MPPT for simplification.