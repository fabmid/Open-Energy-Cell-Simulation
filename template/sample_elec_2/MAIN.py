import pandas as pd
from collections import OrderedDict
 
from simulation import Simulation
from evaluation.economics import Economics
from evaluation.performance import Performance
from evaluation.graphics import Graphics

#%% Define simulation settings

# Simulation timestep in seconds
timestep = 60*60
# Simulation number of timestep
simulation_steps = 24*365

#%% Create Simulation instance
sim = Simulation(simulation_steps=simulation_steps,
                 timestep=timestep)

#%% load hourly data
#Load timeseries irradiation data
sim.env.meteo_irradiation.read_csv(file_name='data/env/SoDa_Cams_Radiation_h_2006-2016_Arusha.csv',
                                   start=0, 
                                   end=simulation_steps)
#Load weather data
sim.env.meteo_weather.read_csv(file_name='data/env/SoDa_MERRA2_Weather_h_2006-2016_Arusha.csv', 
                               start=0, 
                               end=simulation_steps)

#Load load demand data
sim.load.load_demand.read_csv(file_name='data/load/load_dummy_h.csv', 
                              start=24, 
                              end=48)

#%% Call Main Simulation method
sim.simulate()

 
#%% Simulation results
# Summarize environmental data
results_env = pd.DataFrame(
              data=OrderedDict({'sun_elevation':sim.env.sun_position_pvlib['elevation'],
                                'sun_azimuth':sim.env.sun_position_pvlib['azimuth'],
                                'sun_angle_of_incident':sim.env.sun_aoi_pvlib,                               
                                'sun_ghi':sim.env.sun_ghi,
                                'sun_dhi':sim.env.sun_dhi,
                                'sun_bni':sim.env.sun_bni,
                                'temperature_ambient':sim.env.temperature_ambient,
                                'air_pressure':sim.env.air_pressure,
                                'windspeed':sim.env.windspeed,
                                'windspeed_hub':sim.wt.wind_speed_hub.values}), index=sim.timeindex)
# Summarize power flows
results_power = pd.DataFrame(
                data=OrderedDict({'sun_power_poa_global':sim.env.sun_irradiance_pvlib['poa_global'],
                                  'sun_power_poa_direct':sim.env.sun_irradiance_pvlib['poa_direct'],
                                  'sun_power_poa_diffuse':sim.env.sun_irradiance_pvlib['poa_diffuse'],
                                  'pv_power':sim.pv_power, 
                                  'pv_charger_power':sim.pv_charger_power,
                                  'wt_power':sim.wt_power, 
                                  'wt_charger_power':sim.wt_charger_power,
                                  'load_power':sim.load_power_demand,
                                  'power_junction_power':sim.power_junction_power, 
                                  'battery_management_power':sim.battery_management_power, 
                                  'battery_power':sim.battery_power,
                                  'battery_soc':sim.battery_state_of_charge}), index=sim.timeindex)

# Summarize SoD
results_sod = pd.DataFrame(
                data=OrderedDict({'pv_sod':sim.pv_state_of_destruction,
                                  'pv_charger_sod':sim.pv_charger_state_of_destruction,
                                  'wt_soc':sim.wt_state_of_destruction,
                                  'wt_charger':sim.wt_charger_state_of_destruction, 
                                  'bms_sod':sim.battery_management_state_of_destruction,
                                  'battery_sod':sim.battery_state_of_destruction}), index=sim.timeindex)

#%% Simulation evaluation

# Graphics
graph = Graphics(sim)
#graph.plot_load_data()
#graph.plot_pv_energy()
#graph.plot_battery_soc()

## Technical performance
tech = Performance(simulation=sim, 
                   timestep=timestep)
tech.calculate()
tech.plot_cut_off_days()
tech.plot_soc_days()
# Print main technical objective results
tech.print_technical_objective_functions()

## Economics
eco_pv = Economics(sim.pv, 
                   sim.pv_replacement, 
                   timestep)
eco_pv.calculate()

eco_pv_charger = Economics(sim.pv_charger, 
                        sim.pv_charger_replacement, 
                        timestep)
eco_pv_charger.calculate()

eco_wt = Economics(sim.wt,
                   sim.wt_replacement,
                   timestep)
eco_wt.calculate()

eco_wt_charger = Economics(sim.wt_charger,
                        sim.wt_charger_replacement,
                        timestep)
eco_wt_charger.calculate()

eco_bms = Economics(sim.battery_management, 
                    sim.battery_management_replacement, 
                    timestep)
eco_bms.calculate()
eco_bat = Economics(sim.battery, 
                    sim.battery_replacement, 
                    timestep)
eco_bat.calculate()

#Sum of each component LCoE
LCoE = (eco_pv.annuity_total_levelized_costs \
        + eco_pv_charger.annuity_total_levelized_costs \
        + eco_wt.annuity_total_levelized_costs \
        + eco_wt_charger.annuity_total_levelized_costs \
        + eco_bms.annuity_total_levelized_costs \
        + eco_bat.annuity_total_levelized_costs) \
        / ((sum(sim.load_power_demand)-sum(tech.loss_of_power_supply))*(timestep/3600)/1000 / (simulation_steps*(timestep/3600)/8760))

print('---------------------------------------------------------')
print('Objective functions - Technical')
print('---------------------------------------------------------')    
print('LCoE [$/kWh] =', round(LCoE,4))
