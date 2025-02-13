import pandas as pd
import numpy as np
from collections import OrderedDict
import matplotlib.pyplot as plt
 
from simulation import Simulation
from evaluation.performance import Performance
from evaluation.graphics import Plot_simple, Plot_imshow
from evaluation.economics import Economics

#%% Define simulation settings

# Simulation years
years = 1
# Simulation timestep in seconds
timestep = 900
# Simulation number of timestep
simulation_steps = int(years * 8760 * (3600/timestep))

#%% Define component sizes
heat_pump_peak_power_th = 2100
heat_storage_volume = 1060
pv_peak_power = 23900
battery_capacity = 24000
electrolyzer_power = 3250
fuelcell_power = 7250
hydrogen_storage_capacity = 3254961

pv_env = ['data/env/env_pv_south_Oslo.json']

#%% Create Simulation instance
sim = Simulation(pv_peak_power=pv_peak_power,
                 battery_capacity=battery_capacity,
                 electrolyzer_power=electrolyzer_power,
                 fuelcell_power=fuelcell_power,
                 hydrogen_storage_capacity=hydrogen_storage_capacity,
                 heat_pump_peak_power_th=heat_pump_peak_power_th,
                 heat_storage_volume=heat_storage_volume,
                 simulation_steps=simulation_steps,
                 timestep=timestep,
                 pv_env=pv_env)

#%% load data
## EXCEL CSV
# Data files
irradiation_file = 'data/env/SoDa_Cams_Radiation_15min_2010_20_Oslo.csv'
weather_file = 'data/env/SoDa_MERRA2_Weather_15min_2010_20_Oslo.csv'
load_file = 'data/load/profile_NEH_Oslo.csv'

# Load timeseries irradiation data and  weather data
sim.env_south.meteo_irradiation.read_csv(file_name=irradiation_file,
                                         start=0, 
                                         end=simulation_steps)
sim.env_south.meteo_weather.read_csv(file_name=weather_file, 
                                     start=0, 
                                     end=simulation_steps)

#Load cooling demand data
sim.load_cool.load_demand.read_csv(file_name=load_file, 
                                   start=0, 
                                   end=simulation_steps)
#Load heat demand data
sim.load_heat.load_demand.read_csv(file_name=load_file, 
                                   start=0, 
                                   end=simulation_steps)

#Load electricty demand data
sim.load_el.load_demand.read_csv(file_name=load_file, 
                                 start=0, 
                                 end=simulation_steps)

#%% Call Main Simulation method
sim.simulate()

 
#%% Simulation evaluation - Performance
tech = Performance(simulation=sim, 
                   timestep=timestep)

tech.battery_evaluation()
tech.pv_evaluation()

tech.technical_objectives()
tech.grid_evaluation()
tech.technical_evaluation()
tech.print_technical_objective_functions()
tech.print_technical_evaluation()

#%% Simulation evaluation - Economics

# Initialize and calculate economics
eco = Economics(simulation=sim,
                performance=tech,
                file_path='data/eco/economics_oslo.json')
eco.calculate()
eco.print_economic_objectives()
