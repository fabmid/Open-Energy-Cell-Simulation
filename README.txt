Introduction
============
OpEnCellS (Open energy cell simulation) is a open-source energy system model for the simulation and optimization of multi energy carrier supply systems.
The tool is written in Python and follows an object-oriented modeling approach. 

OpEnCellS
--------- 
OpEnCellS enables a detailed simulation of various renewable energy technologies, the operation optimization based on a MILP approach and the sizing optimization based on genetic algorithms. T
he temporal resolution can be flexible defined. OpEnCellS covers components of the electricity, heat/cold and chemical sector.

Electricity sector involves models for:
* Photovoltaic
* Wind turbines
* Batteries
* Electricity grid

Heat sector involves models for:
* Heat pump
* Heat storage
* Cold storage
* Heat grid

Chemical sector involves models for:
* Fuel cell
* Electrolyzer
* Hydrogen storage


Release v0.3-alpha
---------
Compared to previous releases v0.3-alpha includes a operation optimization based on a MILP problem using the linear optimization framework pyomo. Further a genetic design optimization using the framework plytspus is included.
The repository includes a template how to set up a operation and design optimization.

For any comments or question, please contact: Fabian Schmid
