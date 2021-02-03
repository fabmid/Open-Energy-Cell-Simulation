Introduction
============
This example shows how to optimize a hybrid energy system consisting of a PV array and Small Scale Windturbine.
Inside the simulation.py file the system configuration is specified.
The component parameters are specified inside the folder data/components/...json.
The optimization is done in MAIN.py using the ramework Platypus.
A sizing optimization of the PV array, WT capacity and battery bank capacity is done.

The file MAIN.py can oonly be processed from the terminal: 
 * python MAIN.py

The optimization results will be saved to the csv file 'optimization_results.csv'

Attention
---------
Currently the optimization algporithm is specified as follows:

 * alg_rund=1000 (MAIN.py line 204)
 * population_sie=1000 (MAIN.py line 202)

For fast computing and debugging values need to be set to lower values e.g. 10.
