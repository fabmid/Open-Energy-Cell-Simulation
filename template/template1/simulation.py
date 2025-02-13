import sys # Define the absolute path for loading other modules
sys.path.insert(0,'../..')

from datetime import datetime

from simulatable import Simulatable
from environment import Environment

from components.electricity_sector.load_electricity import Load_Electricity
from components.electricity_sector.photovoltaic import Photovoltaic
from components.electricity_sector.power_component import Power_Component
from components.electricity_sector.battery import Battery
from components.electricity_sector.inverter_static import Inverter
from components.electricity_sector.grid import Grid

from components.chemical_sector.hydrogen_storage import Hydrogen_Storage
from components.chemical_sector.electrolyzer import Electrolyzer
from components.chemical_sector.fuelcell import Fuelcell

from components.heat_sector.load_heat import Load_Heat
from components.heat_sector.load_cool import Load_Cool
from components.heat_sector.heat_pump import Heat_Pump
from components.heat_sector.heat_storage import Heat_storage

from components.carrier_el import Carrier_el
from components.carrier_th import Carrier_th
from components.carrier_cool import Carrier_cool


class Simulation(Simulatable):
    '''
    Central Simulation class, where energy system is constructed
    Extractable system power flows are defined here
    
    Attributes
    ----------
    Simulatable : class. In order to simulate system
    
    Methods
    -------
    simulate
    '''    
    
    def __init__(self,
                 pv_peak_power,
                 battery_capacity,
                 electrolyzer_power,
                 fuelcell_power,
                 hydrogen_storage_capacity,
                 heat_pump_peak_power_th,
                 heat_storage_volume,
                 simulation_steps,
                 timestep,
                 pv_env):
        '''
        Parameters can be defined externally or inside class
        ----------
        pv_peak_power : int. Installed phovoltaic peak power in Watt peak [Wp]
        battery capacity : int. Installed nominal battery capacity in Watthours [Wh]
        pv_orientation : tuble of floats. PV oriantation with:
            1. tuble entry pv azimuth in degrees from north [°] (0°=north, 90°=east, 180°=south, 270°=west).
            2. tuble entry pv inclination in degrees from horizontal [°]
        system_location : tuble of floats. System location coordinates:
            1. tuble entry system longitude in degrees [°]
            2. tuble entry system latitude in degrees [°]
        simulation_steps : int. Number of simulation steps
        timestep: int. Simulation timestep in seconds
        '''
        
        #%% Define simulation settings

        # System specifications
        # Installed heat pump thermal power [Wth]
        self.heat_pump_peak_power_th = heat_pump_peak_power_th
        
        # Installed heat storage dimensions [m3] [1]
        self.heat_storage_volume = heat_storage_volume

        # Installed PV power [Wp] 
        self.pv_south_peak_power = pv_peak_power
        
        self.pv_charger_power = self.pv_south_peak_power
        # PV env vile fo location and orientation
        self.pv_env = pv_env
        
        # Installed battery capacity [Wh] 
        self.battery_capacity = battery_capacity           
        
        # Installed delectrolyzer nominal power input [W] 
        self.electrolyzer_power = electrolyzer_power
        # Installed fuel cell nominal power output [W] 
        self.fuelcell_power = fuelcell_power

        # Installed hydrogen storage capacity [Wh] 
        self.hydrogen_storage_capacity = hydrogen_storage_capacity
        
        # Installed inverter power [W] 
        self.inverter_power = self.pv_charger_power
        
        ## Define simulation time parameters     
        # Number of simulation timesteps
        self.simulation_steps = simulation_steps
        # [s] Simulation timestep 
        self.timestep = timestep
        
                
        #%% Initialize classes      

        ## Environment classes
        self.env_south = Environment(timestep=self.timestep,
                                     file_path=pv_env[0])
                
        ## HEAT        
        # Heat load class
        self.load_heat = Load_Heat(file_path='data/components/heat_load.json')
        # Cooling load class
        self.load_cool = Load_Cool()
        
        # Heat Pump class for heating mode
        self.heat_pump = Heat_Pump(timestep=self.timestep,
                                   peak_power_th=self.heat_pump_peak_power_th,
                                   env=self.env_south,
                                   file_path='data/components/heat_pump.json')
        # Heat Pump class for cooling mode
        self.heat_pump_c = Heat_Pump(timestep=self.timestep,
                                     peak_power_th=self.heat_pump_peak_power_th,
                                     env=self.env_south,
                                     file_path='data/components/heat_pump.json')
        
        # Heat storage class
        self.heat_storage = Heat_storage(storage_volume=self.heat_storage_volume,
                                         storage_number=1,
                                         timestep=self.timestep,
                                         env=self.env_south,
                                         file_path='data/components/heat_storage.json')

        
        ## ELECTRICITY and CHEMICAL
        # Electricity load class
        self.load_el = Load_Electricity()
        
        # Photovoltaic panel
        self.pv_south = Photovoltaic(timestep=self.timestep,
                                     peak_power=self.pv_south_peak_power,
                                     controller_type='mppt',
                                     env=self.env_south,
                                     file_path='data/components/photovoltaic_aleo_300Wp.json')

        # Photovoltaic charge controller
        self.pv_charger = Power_Component(timestep=self.timestep,
                                          power_nominal=self.pv_charger_power, 
                                          links=[self.pv_south], 
                                          file_path='data/components/mppt_pv_solaredge_370W.json')  
        
        # Battery class
        self.battery = Battery(timestep=self.timestep,
                               capacity_nominal_wh=self.battery_capacity, 
                               env=self.env_south,
                               file_path='data/components/battery_lfp.json')
               
        ## Hydrogen components  
        self.hydrogen_storage = Hydrogen_Storage(timestep=self.timestep, 
                                                 capacity_wh=self.hydrogen_storage_capacity,
                                                 file_path='data/components/hydrogen_storage.json')
        
        self.electrolyzer = Electrolyzer(timestep=self.timestep,
                                         power_nominal=self.electrolyzer_power,
                                         storage_link=self.hydrogen_storage,
                                         file_path='data/components/electrolyzer_pem.json')

        self.fuelcell = Fuelcell(timestep=self.timestep, 
                                 power_nominal=self.fuelcell_power,
                                 storage_link=self.hydrogen_storage,
                                 file_path='data/components/fuelcell_pem.json')
        
        # Central power inverter
        self.inverter = Inverter(timestep=self.timestep,
                                 power_nominal=self.inverter_power,
                                 file_path='data/components/inverter_solaredge_10kVA.json')  

        # Grid class
        self.grid = Grid(file_path='data/components/grid.json')
 
       
        ## CARRIER
        # Cooling carrier
        self.carrier_cool = Carrier_cool(output_links=[self.load_cool],
                                         heat_pump_link=self.heat_pump_c,
                                         env=self.env_south)
        # Heat carrier
        self.carrier_th = Carrier_th(input_links=[self.electrolyzer,
                                                  self.fuelcell],
                                      output_links=[self.load_heat],
                                      heat_pump_link=self.heat_pump,
                                      heat_storage_link=self.heat_storage,
                                      env=self.env_south)
        # Electricity carrier
        self.carrier_el = Carrier_el(input_links=[self.pv_charger],
                                      output_links=[self.load_el,
                                                    self.heat_pump,
                                                    self.heat_pump_c],
                                      battery_link=self.battery,
                                      electrolyzer_link=self.electrolyzer,
                                      fuelcell_link=self.fuelcell,
                                      inverter_link=self.inverter,
                                      grid_link= self.grid,
                                      env=self.env_south)
        
        ## Initialize Simulatable class and define needs_update initially to True
        self.needs_update = True
        
        Simulatable.__init__(self,
                             self.load_heat,
                             self.load_cool,
                             self.heat_pump,
                             self.heat_pump_c,
                             self.heat_storage,
                             self.load_el,
                             self.env_south,
                             self.pv_south,
                             self.pv_charger,
                             self.battery,
                             self.grid, 
                             self.hydrogen_storage,
                             self.electrolyzer,
                             self.fuelcell,
                             self.inverter,
                             self.carrier_th,
                             self.carrier_cool,
                             self.carrier_el
                             )


    #%% run simulation for every timestep
    def simulate(self):
        '''
        Central simulation method, which :
            initializes all list containers to store simulation results
            iterates over all simulation timesteps and calls Simulatable.start/update/end()
        
        Parameters
        ----------
        None        
        '''
        ## Initialization of list containers to store simulation results                               
        # Timeindex
        self.timeindex = list()

        ## HEAT
        # Heat load demand
        self.load_heat_power = list()
        self.load_heating_power = list()
        self.load_heating_temperature_flow = list()
        self.load_heating_volume_flow_rate = list()
        self.load_hotwater_power = list()
        self.load_hotwater_temperature_flow = list()
        self.load_hotwater_volume_flow_rate = list()
        
        # Cooling load power
        self.load_cooling_power = list()
        
        # Heat Pump - heating mode
        self.heat_pump_operation_mode = list()
        self.heat_pump_temperature_in_prim = list()
        self.heat_pump_temperature_in_sec = list()
        self.heat_pump_speed = list()
        self.heat_pump_power_th = list()
        self.heat_pump_power_el = list()
        self.heat_pump_cop = list()
        self.heat_pump_state_of_destruction = list()
        self.heat_pump_replacement = list()
        # Heat Pump - cooling mode
        self.heat_pump_c_operation_mode = list()
        self.heat_pump_c_temperature_in_prim = list()
        self.heat_pump_c_temperature_in_sec = list()
        self.heat_pump_c_power_th = list()
        self.heat_pump_c_power_el = list()
        self.heat_pump_c_eer = list()
        self.heat_pump_c_power_adjustment = list()
        
        # Heat storage
        self.heat_storage_temperature_mean = list()
        self.heat_storage_power = list()
        self.heat_storage_state_of_destruction = list()
        self.heat_storage_replacement = list()
        
        # Heat carrier
        self.carrier_th_input_links_power = list()
        self.carrier_th_output_links_power = list()
        self.carrier_th_power_0 = list()
        self.carrier_th_power_1 = list()
        self.carrier_th_power_2 = list()
        
        ## ELECRICTY and CHEMICAL
        # Electricity load demand 
        self.load_el_power = list()        
        
        # PV 
        self.pv_south_power = list()
        self.pv_south_peak_power_current = list()
        self.pv_south_state_of_destruction = list()
        self.pv_south_replacement = list()
        self.pv_east_power = list()
        self.pv_east_peak_power_current = list()
        self.pv_east_state_of_destruction = list()
        self.pv_east_replacement = list()
        self.pv_west_power = list()
        self.pv_west_peak_power_current = list()
        self.pv_west_state_of_destruction = list()
        self.pv_west_replacement = list()
        
        # PV charger
        self.pv_charger_power = list()
        self.pv_charger_efficiency = list()  
        self.pv_charger_state_of_destruction = list()
        self.pv_charger_replacement = list()
        
        # Battery
        self.battery_power = list()
        self.battery_power_stored = list()
        self.battery_efficiency = list()
        self.battery_state_of_charge = list()
        self.battery_state_of_destruction = list()
        self.battery_replacement = list()
        
        # Hydrogen storage
        self.hydrogen_storage_state_of_charge = list()
        self.hydrogen_storage_state_of_destruction = list()
        self.hydrogen_storage_replacement = list()
        
        # Electrolyzer
        self.electrolyzer_power = list()
        self.electrolyzer_heat = list()    
        self.electrolyzer_efficiency_el = list()
        self.electrolyzer_efficiency_th = list()
        self.electrolyzer_hydrogen_produced_power = list()
        self.electrolyzer_hydrogen_produced_kg = list()
        self.electrolyzer_hydrogen_produced_Nl = list()   
        self.electrolyzer_operation = list()
        self.electrolyzer_state_of_destruction = list()
        self.electrolyzer_replacement = list()
        
        # Fuel cell
        self.fuelcell_power = list()
        self.fuelcell_power_to_battery = list()
        self.fuelcell_power_to_load = list()  
        self.fuelcell_heat = list()
        self.fuelcell_efficiency_el = list()
        self.fuelcell_efficiency_th = list()
        self.fuelcell_power_hydrogen = list()
        self.fuelcell_operation = list()
        self.fuelcell_state_of_destruction = list()
        self.fuelcell_replacement = list()
        
        # Inverter
        self.inverter_power_load = list()
        self.inverter_efficiency_load = list()
        self.inverter_power_grid= list()
        self.inverter_efficiency_grid = list()
        self.inverter_state_of_destruction = list()
        self.inverter_replacement = list()
        
        # Grid
        self.grid_power = list()

        # Electricty Carrier
        self.carrier_el_input_links_power = list()
        self.carrier_el_output_links_power = list()
        self.carrier_el_power_0 = list()
        self.carrier_el_power_1 = list()
        self.carrier_el_power_2 = list()

        
        # As long as needs_update = True simulation takes place
        if self.needs_update:
            #print(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), ' Start')
            
            ## Call start method (inheret from Simulatable) to start simulation
            self.start()

            ## Timeindex from irradiation data file
            time_index = self.env_south.time_index                              
            ## Iteration over all simulation steps
            for t in range(0, self.simulation_steps):
                
                ## Call calculate method to call calculation method of all components and carriers
                self.calculate()
                
                # Time index
                self.timeindex.append(time_index[t])

                ## HEAT                
                # Heat load demand
                self.load_heat_power.append(self.load_heat.power)
                self.load_heating_power.append(self.load_heat.heating_power)
                self.load_heating_temperature_flow.append(self.load_heat.heating_temperature_flow)
                self.load_heating_volume_flow_rate.append(self.load_heat.heating_volume_flow_rate)
                self.load_hotwater_power.append(self.load_heat.hotwater_power)
                self.load_hotwater_temperature_flow.append(self.load_heat.hotwater_temperature_flow)
                self.load_hotwater_volume_flow_rate.append(self.load_heat.hotwater_volume_flow_rate)

                # Cooling load
                self.load_cooling_power.append(self.load_cool.power)
                
                # Heat Pump
                self.heat_pump_operation_mode.append(self.heat_pump.operation_mode)
                self.heat_pump_temperature_in_prim.append(self.heat_pump.temperature_in_prim)
                self.heat_pump_temperature_in_sec.append(self.heat_pump.temperature_in_sec_heating_mode)
                self.heat_pump_power_th.append(self.heat_pump.power_th)
                self.heat_pump_power_el.append(self.heat_pump.power)
                self.heat_pump_cop.append(self.heat_pump.cop)
                self.heat_pump_state_of_destruction.append(self.heat_pump.state_of_destruction)
                self.heat_pump_replacement.append(self.heat_pump.replacement)
                # Heat Pump - cooling mode
                self.heat_pump_c_operation_mode.append(self.heat_pump_c.operation_mode)
                self.heat_pump_c_temperature_in_prim.append(self.heat_pump_c.temperature_in_prim)
                self.heat_pump_c_temperature_in_sec.append(self.heat_pump_c.temperature_in_sec_cooling_mode)
                self.heat_pump_c_power_th.append(self.heat_pump_c.power_th)
                self.heat_pump_c_power_el.append(self.heat_pump_c.power)
                self.heat_pump_c_eer.append(self.heat_pump_c.eer)
                self.heat_pump_c_power_adjustment.append(self.heat_pump_c.power_adjustment)
                
                # Heat storage
                self.heat_storage_temperature_mean.append(self.heat_storage.temperature)
                self.heat_storage_power.append(self.heat_storage.power)
                self.heat_storage_state_of_destruction.append(self.heat_storage.state_of_destruction)
                self.heat_storage_replacement.append(self.heat_storage.replacement)
                
                # Heat carrier
                self.carrier_th_input_links_power.append(self.carrier_th.input_links_power)
                self.carrier_th_output_links_power.append(self.carrier_th.output_links_power)
                self.carrier_th_power_0.append(self.carrier_th.power_0)
                self.carrier_th_power_1.append(self.carrier_th.power_1)
                self.carrier_th_power_2.append(self.carrier_th.power_2)
                
                ## ELECTRICITY and CHEMICAL
                # Electricity load demand
                self.load_el_power.append(self.load_el.power) 
                
                # PV
                self.pv_south_power.append(self.pv_south.power)
                self.pv_south_peak_power_current.append(self.pv_south.peak_power_current)
                self.pv_south_state_of_destruction.append(self.pv_south.state_of_destruction)
                self.pv_south_replacement.append(self.pv_south.replacement)
                       
                # PV charger
                self.pv_charger_power.append(self.pv_charger.power)
                self.pv_charger_efficiency.append(self.pv_charger.efficiency)
                self.pv_charger_state_of_destruction.append(self.pv_charger.state_of_destruction)
                self.pv_charger_replacement.append(self.pv_charger.replacement)
        
                # Battery
                self.battery_power.append(self.battery.power)
                self.battery_power_stored.append(self.battery.power_battery)
                self.battery_efficiency.append(self.battery.efficiency)
                self.battery_state_of_charge.append(self.battery.state_of_charge)
                self.battery_state_of_destruction.append(self.battery.state_of_destruction)
                self.battery_replacement.append(self.battery.replacement)
                
                # Hydrogen storage
                self.hydrogen_storage_state_of_charge.append(self.hydrogen_storage.state_of_charge)
                self.hydrogen_storage_state_of_destruction.append(self.hydrogen_storage.state_of_destruction)
                self.hydrogen_storage_replacement.append(self.hydrogen_storage.replacement)
               
                # Electrolyzer
                self.electrolyzer_power.append(self.electrolyzer.power)
                self.electrolyzer_heat.append(self.electrolyzer.heat_produced)      
                self.electrolyzer_efficiency_el.append(self.electrolyzer.efficiency_el)
                self.electrolyzer_efficiency_th.append(self.electrolyzer.efficiency_th)
                self.electrolyzer_hydrogen_produced_power.append(self.electrolyzer.hydrogen_produced_power)
                self.electrolyzer_hydrogen_produced_kg.append(self.electrolyzer.hydrogen_produced_kg)
                self.electrolyzer_hydrogen_produced_Nl.append(self.electrolyzer.hydrogen_produced_Nl)              
                self.electrolyzer_operation.append(self.electrolyzer.operation)
                self.electrolyzer_state_of_destruction.append(self.electrolyzer.state_of_destruction)
                self.electrolyzer_replacement.append(self.electrolyzer.replacement)
                
                # Fuel cell
                self.fuelcell_power.append(self.fuelcell.power)
                self.fuelcell_power_to_battery.append(self.fuelcell.power_to_battery)
                self.fuelcell_power_to_load.append(self.fuelcell.power_to_load)
                self.fuelcell_heat.append(self.fuelcell.heat_produced)
                self.fuelcell_efficiency_el.append(self.fuelcell.efficiency_el)
                self.fuelcell_efficiency_th.append(self.fuelcell.efficiency_th)
                self.fuelcell_power_hydrogen.append(self.fuelcell.power_hydrogen)
                self.fuelcell_operation.append(self.fuelcell.operation)
                self.fuelcell_state_of_destruction.append(self.fuelcell.state_of_destruction)
                self.fuelcell_replacement.append(self.fuelcell.replacement)
                
                # Inverter
                self.inverter_power_load.append(self.inverter.power_load)
                self.inverter_efficiency_load.append(self.inverter.efficiency_load)
                self.inverter_power_grid.append(self.inverter.power_grid)
                self.inverter_efficiency_grid.append(self.inverter.efficiency_grid)
                self.inverter_state_of_destruction.append(self.inverter.state_of_destruction)
                self.inverter_replacement.append(self.inverter.replacement)
                
                # Grid
                self.grid_power.append(self.grid.power)
                
                # Carrier
                self.carrier_el_input_links_power.append(self.carrier_el.input_links_power)
                self.carrier_el_output_links_power.append(self.carrier_el.output_links_power)
                self.carrier_el_power_0.append(self.carrier_el.power_0)
                self.carrier_el_power_1.append(self.carrier_el.power_1)
                self.carrier_el_power_2.append(self.carrier_el.power_2)
                
                
                ## Call update method to go one timestep further for all components and carriers
                self.update()
                
            ## Simulation over: set needs_update to false and call end method
            self.needs_update = False
            #print(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), ' End')
            self.end()
            
            ## System components (economic model)
            self.components = [[self.heat_pump, self.heat_pump_replacement],
                               [self.heat_storage, self.heat_storage_replacement],
                               [self.pv_south, self.pv_south_replacement],
                               [self.battery, self.battery_replacement],
                               [self.hydrogen_storage, self.hydrogen_storage_replacement],
                               [self.electrolyzer, self.electrolyzer_replacement],
                               [self.fuelcell, self.fuelcell_replacement],
                               [self.inverter, self.inverter_replacement]]
        