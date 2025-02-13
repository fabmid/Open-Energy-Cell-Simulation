import sys
import json
import pandas as pd
import pyomo.environ as pyo
from datetime import datetime

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# Specifying importing directory for data_loader
sys.path.insert(0, '../..')
from data_loader import hdf5
from evaluation.performance import apply_performance_singlevalue

# Specify importing directory with problem statements
sys.path.insert(0, './data/cases/template1')
from milp_problem import Milp_Problem

"""
Sample script to run template1
"""

#%% Create Simulation instance
# Load config data
filepath_config = "data/cases/template1/config/main_config_template1.json"

with open(filepath_config, "r") as json_file:
     config = json.load(json_file)

# Define component sizes
res_vars = [17.2,
            10,
            100,
            25,
            5,
            5,
            1000]
						
# Add component sizes to config
config["pv_power_nominal"]=res_vars[0]
config["hp_power_nominal"]= res_vars[1]
config["tes_h_capacity"]=res_vars[2]
config["bat_capacity"]= res_vars[3]
config["ely_power"]= res_vars[4]
config["fc_power"]= res_vars[5]
config["h2_capacity"]= res_vars[6]


# Initialize milp problem
system = Milp_Problem(res_vars=res_vars,
                      config=config)

#%% Call Main Simulation method (non-dispatchables)
print('Start: ', datetime.today().strftime('%Y-%m-%d %H:%M:%S'))
system.simulate_non_dispatchables()
print('Dispatchables End: ', datetime.today().strftime('%Y-%m-%d %H:%M:%S'))

#%% Call Optimization model
system.optimize_operation()
print('MILP End: ', datetime.today().strftime('%Y-%m-%d %H:%M:%S'))

#%% Call Main Simulation method (dispatchables)
system.simulate_dispatchables()
print('Non-dispatchables End:', datetime.today().strftime('%Y-%m-%d %H:%M:%S'))

#%% Call economic evaluation
system.calculate_economics()
print('Economic calc End:', datetime.today().strftime('%Y-%m-%d %H:%M:%S'))

#%% Call performance evaluation
system.calculate_performance()
print('Performance calc End:', datetime.today().strftime('%Y-%m-%d %H:%M:%S'))

#%% Apply single value performance indicators
config['perf_indicators'] = apply_performance_singlevalue(data=system.results_main,
                                                          metadata=config,
                                                          timestep=config['timestep'])
print('Perf indicator single value calc End:', datetime.today().strftime('%Y-%m-%d %H:%M:%S'))

#%% Main Results
print('Optimization obj:',pyo.value(system.model.obj))
print('Annuity [€/a]:', system.eco.annuity_total)
print('LCoE [€/kWh]:', system.eco.levelized_cost_energy)
print('Grid feed-out [kWh/a]:', system.grid_feed_out_energy)

results_main = system.results_main

print('End: ', datetime.today().strftime('%Y-%m-%d %H:%M:%S'), ' Start')