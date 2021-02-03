"""
Example 1

This script presents a simple solarthermal heat storage model for a Single Family House load case.
The system consists of:
    - Solarthermal heat pipe collector
    - Perfectly Mixed heat storage
    - Heat and warm water load

The solarthermal model assumes:
    - static solar collector input, mean and output temperature
    
The perfectly mixed heat storage model assumes:
    - that a low temperature niveau is always appararent, which supplies the solarthermal collector witha low static input temperature.
    
It can be used to generate fast energy yield estimations on a hourly timeseries basis.
Environmental and load data is given for the year 2019 with an hourly resolution.
"""

import pvlib
import pandas as pd
from collections import OrderedDict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from simulation import Simulation

#%% Simulation parameter 
# System location
system_location = pvlib.location.Location(latitude=52.521,
                                          longitude=13.39286,
                                          tz='Europe/Berlin',
                                          altitude=80)

## Solarthermal orientation : tuble of floats. ST oriantation with:
# 1. pv azimuth in degrees [°] (0°=north, 90°=east, 180°=south, 270°=west) 
# 2. pv inclination in degrees [°]
st_orientation=(180,30)

# Simulation timestep in seconds
timestep = 60*60
# Start timestep 
start = 0
# Simulation number of timesteps
simulation_steps = 8760
# End timestep 
end = start + simulation_steps

## Solarthermal parameters               
# Number of solarthermal collectors
number_collectors = 2
# Solar pump control type
control_type='no_control'

## Heat storage parameters
# Heat storage model
storage_model='perfectly_mixed'
# Heat storage volume m3
storage_volume = 2.047
# Number of heat storages
storage_number = 1

## Aux component 
# Nominal power
aux_component_power = 5000

#%% Initialize Simulation
# Create Simulation instance
sim = Simulation(number_collectors=number_collectors,
                 control_type=control_type,
                 storage_model=storage_model,
                 storage_volume=storage_volume,
                 storage_number=storage_number,
                 aux_component_power=aux_component_power,
                 system_location=system_location,
                 st_orientation=st_orientation,
                 simulation_steps=simulation_steps,
                 timestep=timestep)

#Load timeseries irradiation data
sim.env.meteo_irradiation.read_csv(file_name='data/env/SoDa_Cams_Radiation_h_2019_Berlin.csv',
                                   start=start, 
                                   end=end)
#Load weather data
sim.env.meteo_weather.read_csv(file_name='data/env/SoDa_MERRA2_Weather_h_2019_Berlin.csv', 
                               start=start, 
                               end=end)
#Load load demand data
sim.load_heat.load_demand.read_csv(file_name='data/load/201116_heat_load_EFH_h_sample.csv', 
                              start=start, 
                              end=end)

## Call Main Simulation method
sim.simulate()

#%% Simulation result data

# Summarize load data
results_load = pd.DataFrame(
                  data=OrderedDict({'load_heating_power':sim.load_heating_power_demand,
                                    'load_heating_temperature_flow':sim.load_heating_temperature_flow,
                                    'load_heating_volume_flow_rate':sim.load_heating_volume_flow_rate,
                                    'load_hotwater_power':sim.load_hotwater_power_demand,
                                    'load_hotwater_temperature_flow':sim.load_hotwater_temperature_flow,
                                    'load_hotwater_volume_flow_rate':sim.load_hotwater_volume_flow_rate
                                    }), index=sim.timeindex)
                
# Summarize environmental data
results_env = pd.DataFrame(
                  data=OrderedDict({'sun_elevation':sim.env.sun_position_pvlib['elevation'],
                                    'sun_azimuth':sim.env.sun_position_pvlib['azimuth'],
                                    'sun_angle_of_incident':sim.env.sun_aoi_pvlib,                               
                                    'sun_ghi':sim.env.sun_ghi,
                                    'sun_dhi':sim.env.sun_dhi,
                                    'sun_bni':sim.env.sun_bni,
                                    'sun_power':sim.env.power,
                                    'temperature_ambient':sim.env.temperature_ambient,
                                    'windspeed':sim.env.windspeed
                                    }), index=sim.timeindex)

# Summarize power flows
results_solarthermal = pd.DataFrame(
                 data=OrderedDict({'st_power_theo':sim.solarthermal_power_theo, 
                                   'st_power_real':sim.solarthermal_power_real,
                                   'st_power_to_storage':sim.solarthermal_power_to_storage,
                                   'st_efficiency_iam':sim.solarthermal_efficiency_iam,                                  
                                   'st_volume_flow_rate':sim.solarthermal_volume_flow_rate, 
                                   'st_temperature_input':sim.solarthermal_temperature_input,
                                   'st_temperature_output':sim.solarthermal_temperature_output,
                                   'heat_storage_temperature_mean':sim.heat_storage_temperature_mean
                                   }), index=sim.timeindex)
 
# Summarize power flows
results_aux_component = pd.DataFrame(
                data=OrderedDict({'aux_component_power':sim.aux_component_power,
                                  'aux_component_volume_flow_rate':sim.aux_component_volume_flow_rate,
                                  'aux_component_temperature_input':sim.aux_component_temperature_input,
                                  'aux_component_energy_fuel':sim.aux_component_energy_fuel
                                  }), index=sim.timeindex)


#%% Result plotting

figsize=(4,2)
## Solarthermal power
fig1 = plt.figure(figsize=figsize)
plt.title('Solarthermal power')
plt.plot(sim.timeindex, sim.solarthermal_power_theo, label='ST power_theo')
plt.plot(sim.timeindex, sim.env.power.values, label='env power') 
plt.legend(bbox_to_anchor=(1.0, 1.0), loc=2, borderaxespad=0., ncol=1)
plt.ylabel('Power [W]')
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=2))
fig1.autofmt_xdate()
plt.grid()
plt.show()

## Load power
fig2 = plt.figure(figsize=figsize)
plt.title('Load power')
plt.plot(sim.timeindex, sim.load_hotwater_power_demand, label='hot water')
plt.plot(sim.timeindex, sim.load_heating_power_demand, label='heating') 
plt.legend(bbox_to_anchor=(1.0, 1.0), loc=2, borderaxespad=0., ncol=1)
plt.ylabel('Power [W]')
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=2))
fig2.autofmt_xdate()
plt.grid()
plt.show()

## Solarthermal temperartures
fig3 = plt.figure(figsize=figsize)
plt.title('Solarthermal temperatures')
plt.plot(sim.timeindex, sim.solarthermal_temperature_input, label='st_temp_in')
plt.plot(sim.timeindex, sim.solarthermal_temperature_mean, label='st_temp_mean')
plt.plot(sim.timeindex, sim.solarthermal_temperature_output, label='st_temp_out')
plt.legend(bbox_to_anchor=(1.0, 1.0), loc=2, borderaxespad=0., ncol=1)
plt.ylabel('Temp [K]')
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=2))
fig3.autofmt_xdate()
plt.grid()
plt.show()

## Solarthermal and aux_component flow rate
fig4, ax1 = plt.subplots(figsize=figsize)        
ax1.plot(sim.timeindex, sim.solarthermal_volume_flow_rate, '-b', label='solarthermal') 
ax1.set_ylabel('Flow rate [m3 s]')
ax1.legend(bbox_to_anchor=(0., 1.2), loc=2, borderaxespad=0., ncol=4)
ax2 = ax1.twinx()   
ax2.plot(sim.timeindex, sim.aux_component_volume_flow_rate, 'og', label='aux_component')
ax2.legend(bbox_to_anchor=(0.7, 1.2), loc=2, borderaxespad=0., ncol=4)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=2))
fig4.autofmt_xdate()
plt.grid()
plt.show()

## Storage output temperature to solarthermal/water/heating
fig5 = plt.figure(figsize=figsize)
plt.title('Storage temps')
plt.plot(sim.timeindex, sim.heat_storage_temperature_mean, label='storage_temp_mean')
plt.hlines(y=sim.heat_storage.temperature_minimum, 
           xmin=min(sim.timeindex), xmax=max(sim.timeindex), colors='red', linestyles=':', label='storage_min')
plt.hlines(y=(sim.heat_storage.temperature_minimum+sim.aux_component.temperature_offset_heat_storage), 
           xmin=min(sim.timeindex), xmax=max(sim.timeindex), colors='orange', linestyles=':', label='aux comp offset')
plt.legend(bbox_to_anchor=(1.0, 1.0), loc=2, borderaxespad=0., ncol=1)
plt.ylabel('Temp [K]')
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=2))
fig5.autofmt_xdate()
plt.grid()
plt.show()


#%% Evaluation
# Solarthermal energy yield 
energy_yield_solarthermal_theo = sum(sim.solarthermal_power_theo) * (timestep/3600)
energy_yield_solarthermal_real = sum(sim.solarthermal_power_real) * (timestep/3600)
energy_yield_solarthermal_to_storage = sum(sim.solarthermal_power_to_storage) * (timestep/3600)
energy_yield_solarthermal_thump = number_collectors * sim.solarthermal.area_collector_aperture \
                                * 0.50 * sim.env.power.sum() *(timestep/3600)

# Auxilliary component energy yield
energy_yield_auxiliary = sum(sim.aux_component_power) * (timestep/3600)

# Load energy
energy_load = sum(sim.load_heating_power_demand + sim.load_hotwater_power_demand) * (timestep/3600)
energy_load_heating = sum(sim.load_heating_power_demand) * (timestep/3600)
energy_load_hotwater = sum(sim.load_hotwater_power_demand) * (timestep/3600)

# Coverage ratio of ST-load
coverage_ratio = energy_yield_solarthermal_to_storage / energy_load


print('Solarthermal energy yield theo= ', round(energy_yield_solarthermal_theo/1000,2), 'kWh')
print('Solarthermal energy yield real= ', round(energy_yield_solarthermal_real/1000,2), 'kWh')
print('Solarthermal energy yield to storage= ', round(energy_yield_solarthermal_to_storage/1000,2), 'kWh')
print('Solarthermal energy yield thump= ', round(energy_yield_solarthermal_thump/1000,2), 'kWh')

print('Load energy demand= ', round(energy_load/1000,2), 'kWh')
print('Load heating energy demand= ', round(energy_load_heating/1000,2), 'kWh')
print('Load howater energy demand= ', round(energy_load_hotwater/1000,2), 'kWh')

print('Coverage ratio ST-Load= ', round(coverage_ratio,2))