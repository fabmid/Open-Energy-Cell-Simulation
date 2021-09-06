import pandas as pd
from collections import OrderedDict
 
from simulation import Simulation
from evaluation.performance import Performance
from evaluation.graphics import Plot_simple, Plot_imshow

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
# Performance
tech = Performance(simulation=sim, 
                   timestep=timestep)

tech.technical_objectives()
tech.days_with_cut_offs()
tech.print_technical_objective_functions()

# Graphics
Plot_simple(sim.timeindex, sim.pv_charger_power,'Time [date]','Power [W]','PV MPPT Power').generate()
Plot_simple(sim.timeindex, sim.wt_charger_power,'Time [date]','Power [W]','WT MPPT Power').generate()
Plot_simple(sim.timeindex, sim.load_power_demand,'Time [date]','Power [W]','Load Power').generate()
Plot_simple(sim.timeindex, sim.grid_power,'Time [date]','Power [W]','Grid Power').generate()
Plot_imshow(tech.cut_off_day,'Time [date]','Power [W]','Days with Cut offs').generate()