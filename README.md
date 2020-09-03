Introduction
============
OpEnCellS (Open energy cell simulation) is a open-source modeling framework for the simulation of energy systems.
The tool is developed by Fabian Schmid, written in Python and follows an object-oriented modeling approach.


OpEnCellS
---------
OpEnCellS enables a detailed simulation of various renewable energy technologies with a temporal resolution of one minute or one hour.
Electricity sector components involves models for:

 * Photovoltaic
 * Power components
 * Batteries

Power component technologies can be:
 * Pulse-Width-Modulation (PWM) charge controller
 * Maximum Power Point Tracker (MPPT) charge controller
 * Battery Management Systems (BMS)

Models of heat sector components involve solarthermal collectors, pipes and stratified heat storages, which are currently under development.
Future releases will include further hydrogen and wind turbine systems.


To Dos
------
 * Include Installation instructions in file with command "pip install module" or list of necessary external libaries.
 * Clean code: Start method of Simulatable in components necessary ?!
 * Include good workflow for sensitivity analysis, where for every sensi run own json is generated and no separate sensitivty class is needed.
"# Open-Energy-Cell-Simulation-OpEnCellS-" 
"# Open-Energy-Cell-Simulation" 
