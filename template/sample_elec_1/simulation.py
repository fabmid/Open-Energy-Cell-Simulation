import sys # Define the absolute path for loading other modules
sys.path.insert(0,'../..')

import pvlib
from datetime import datetime

from simulatable import Simulatable
from environment import Environment
from components.electricity_sector.load_electricity import Load_Electricity
from components.electricity_sector.photovoltaic import Photovoltaic
from components.electricity_sector.power_component import Power_Component
from components.electricity_sector.battery import Battery
from components.electricity_sector.grid import Grid

from components.carrier import Carrier

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
                 simulation_steps,
                 timestep):
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
        # System location
        # Latitude: Positive north of equator, negative south of equator.
        # Longitude: Positive east of prime meridian, negative west of prime meridian.
        self.system_location = pvlib.location.Location(latitude=52.5210,longitude=13.3929,
                                                       tz='Europe/Berlin', altitude=80)
        # [Wp] Installed PV power
        self.pv_peak_power = 10000        
        #  PV orientation : tuble of floats. PV oriantation with:
        # 1. pv azimuth in degrees [°] (0°=north, 90°=east, 180°=south, 270°=west). & 2. pv inclination in degrees [°]
        self.pv_orientation = (0,0)
        # Installed inverter peak power
        self.inverter_peak_power = 1000
        
        # [Wh] Installed battery capacity
        self.battery_capacity = 10000      
        
        ## Define simulation time parameters     
        # Number of simulation timesteps
        self.simulation_steps = simulation_steps
        # [s] Simulation timestep 
        self.timestep = timestep
        
                
        #%% Initialize classes      
        
        # Environment class
        self.env = Environment(timestep=self.timestep,
                               system_orientation=self.pv_orientation,
                               system_location=self.system_location)

        # Component classes
        self.pv = Photovoltaic(timestep=self.timestep,
                               peak_power=self.pv_peak_power,
                               controller_type='mppt',
                               env=self.env,
                               file_path='data/components/photovoltaic_resonix_120Wp.json')
        
        # PV MPPT charger
        self.charger = Power_Component(timestep=self.timestep,
                                       power_nominal=self.pv_peak_power, 
                                       input_link=self.pv, 
                                       file_path='data/components/power_component_mppt.json')  
        

        # load class
        self.load = Load_Electricity()
        
        # Inverter class
        self.inverter = Power_Component(timestep=self.timestep,
                                       power_nominal=self.inverter_peak_power, 
                                       input_link=self.load, 
                                       file_path='data/components/power_component_inverter.json')  
        
        # Grid class
        self.grid = Grid()
        
        # Electricity carrier
        self.carrier = Carrier(input_link_1=self.charger, 
                               input_link_2=None, 
                               output_link_1=self.inverter,
                               grid_link= self.grid)
       
        # Battery system components
        self.battery_management = Power_Component(timestep=self.timestep,
                                                  power_nominal=self.pv_peak_power, 
                                                  input_link=self.carrier, 
                                                  file_path='data/components/power_component_bms.json')

        self.battery = Battery(timestep=self.timestep,
                               capacity_nominal_wh=self.battery_capacity, 
                               input_link=self.battery_management, 
                               carrier_link=self.carrier,
                               env=self.env,
                               file_path='data/components/battery_lfp.json')
        
        ## Initialize Simulatable class and define needs_update initially to True
        self.needs_update = True
        
        Simulatable.__init__(self,self.env,self.pv,self.charger,
                             self.load,self.inverter,self.carrier,
                             self.battery_management, self.battery)


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

        # PV 
        self.pv_power = list()
        self.pv_temperature = list()
        self.pv_peak_power_current = list()
        # charger
        self.charger_power = list()
        self.charger_efficiency = list()

        # Load demand 
        self.load_power_demand = list()  
        # Inverter power
        self.inverter_power = list()
        
        # Carrier
        self.carrier_power = list()
        self.carrier_power_storage = list()
        
        # Grid
        self.grid_power = list()

        # BMS
        self.battery_management_power = list()
        # Battery
        self.battery_power = list()
                
        # Component state of destruction            
        self.photovoltaic_state_of_destruction = list()
        self.charger_state_of_destruction = list()
        # Component replacement
        self.photovoltaic_replacement = list()
        self.charger_replacement = list()
        self.inverter_replacement = list()
        self.battery_management_replacement = list()
        self.battery_replacement = list()
       
        # As long as needs_update = True simulation takes place
        if self.needs_update:
            print(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), ' Start')
            
            ## pvlib: irradiation and weather data
            self.env.load_data()
            ## Timeindex from irradiation data file
            time_index = self.env.time_index   
            ## pvlib: pv power
            self.pv.load_data()
            
            ## Call start method (inheret from Simulatable) to start simulation
            #self.start()
                             
            ## Iteration over all simulation steps
            for t in range(0, self.simulation_steps):
                ## Call update method to call calculation method and go one simulation step further
                self.update()
                ## Call balance method to balance carrier and determine grid power
                self.balance()
                
                # Time index
                self.timeindex.append(time_index[t])

                # PV
                self.pv_power.append(self.pv.power)
                self.pv_temperature.append(self.pv.temperature)
                self.pv_peak_power_current.append(self.pv.peak_power_current)
                # charger
                self.charger_power.append(self.charger.power)
                self.charger_efficiency.append(self.charger.efficiency)
                
                # Load demand
                self.load_power_demand.append(self.load.power) 
                # Inverter
                self.inverter_power.append(self.inverter.power)
                
                # Carrier
                self.carrier_power.append(self.carrier.power)
                self.carrier_power_storage.append(self.carrier.power_storage)
                
                # Grid
                self.grid_power.append(self.grid.power)

                # BMS
                self.battery_management_power.append(self.battery_management.power)
                # Battery
                self.battery_power.append(self.battery.power_battery)
                
                # Component state of destruction
                self.photovoltaic_state_of_destruction.append(self.pv.state_of_destruction)
                self.charger_state_of_destruction.append(self.charger.state_of_destruction)
                # Component replacement
                self.photovoltaic_replacement.append(self.pv.replacement)
                self.charger_replacement.append(self.charger.replacement)
                self.inverter_replacement.append(self.inverter.replacement)
                self.battery_management_replacement.append(self.battery_management.replacement)
                self.battery_replacement.append(self.battery.replacement)

            ## Simulation over: set needs_update to false and call end method
            self.needs_update = False
            print(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), ' End')
            #self.end()
        