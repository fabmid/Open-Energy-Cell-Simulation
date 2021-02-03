import sys # Define the absolute path for loading other modules
sys.path.insert(0,'../..')

import pvlib
from datetime import datetime

from simulatable import Simulatable
from environment import Environment
from components.load import Load
from components.photovoltaic import Photovoltaic
from components.power_component import Power_Component
from components.power_junction import Power_Junction
from components.battery import Battery

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
        # [Wp] Installed PV power
        self.pv_peak_power = 100
        # [Wh] Installed battery capacity
        self.battery_capacity = 600            
        #  PV orientation : tuble of floats. PV oriantation with:
        # 1. pv azimuth in degrees [°] (0°=north, 90°=east, 180°=south, 270°=west). & 2. pv inclination in degrees [°]
        self.pv_orientation = (0,0)
        
        # System location
        # Latitude: Positive north of equator, negative south of equator.
        # Longitude: Positive east of prime meridian, negative west of prime meridian.
        self.system_location = pvlib.location.Location(latitude=-3.386925,
                                                       longitude=36.682995,
                                                       tz='Africa/Dar_es_Salaam',
                                                       altitude=1400)

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
        
        # load class
        self.load = Load()
        
        # Component classes
        self.pv = Photovoltaic(timestep=self.timestep,
                               peak_power=self.pv_peak_power,
                               controller_type='mppt',
                               env=self.env,
                               file_path='data/components/photovoltaic_resonix_120Wp.json')
        
        self.charger = Power_Component(timestep=self.timestep,
                                       power_nominal=self.pv_peak_power, 
                                       input_link=self.pv, 
                                       file_path='data/components/power_component_mppt.json')  
        
        self.power_junction = Power_Junction(input_link_1=self.charger, 
                                             input_link_2=None, 
                                             load=self.load)
        
        self.battery_management = Power_Component(timestep=self.timestep,
                                                  power_nominal=self.pv_peak_power, 
                                                  input_link=self.power_junction, 
                                                  file_path='data/components/power_component_bms.json')

        self.battery = Battery(timestep=self.timestep,
                               capacity_nominal_wh=self.battery_capacity, 
                               input_link=self.battery_management, 
                               env=self.env,
                               file_path='data/components/battery_lfp.json')
       
        ## Initialize Simulatable class and define needs_update initially to True
        self.needs_update = True
        
        Simulatable.__init__(self,self.env,self.load,self.pv,self.charger,
                             self.power_junction, self.battery_management, self.battery)


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
        # Load demand 
        self.load_power_demand = list()        
        # PV 
        self.pv_power = list()
        self.pv_temperature = list()
        self.pv_peak_power_current = list()
        # charger
        self.charger_power = list()
        self.charger_efficiency = list()
        # Power junction
        self.power_junction_power = list()
        # BMS
        self.battery_management_power = list()
        self.battery_management_efficiency = list()
        # Battery
        self.battery_power = list()
        self.battery_efficiency = list()
        self.battery_power_loss = list()
        self.battery_temperature = list()
        self.battery_state_of_charge = list()
        self.battery_state_of_health = list()
        self.battery_capacity_current_wh = list()
        self.battery_capacity_loss_wh = list()
        self.battery_voltage = list()
        # Component state of destruction            
        self.photovoltaic_state_of_destruction = list()
        self.battery_state_of_destruction = list()
        self.charger_state_of_destruction = list()
        self.battery_management_state_of_destruction = list()
        # Component replacement
        self.photovoltaic_replacement = list()
        self.battery_replacement = list()
        self.charger_replacement = list()
        self.battery_management_replacement = list()

       
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
            self.start()
                             
            ## Iteration over all simulation steps
            for t in range(0, self.simulation_steps):
                ## Call update method to call calculation method and go one simulation step further
                self.update()
                
                # Time index
                self.timeindex.append(time_index[t])
                # Load demand
                self.load_power_demand.append(self.load.power) 
                # PV
                self.pv_power.append(self.pv.power)
                self.pv_temperature.append(self.pv.temperature)
                self.pv_peak_power_current.append(self.pv.peak_power_current)
                # charger
                self.charger_power.append(self.charger.power)
                self.charger_efficiency.append(self.charger.efficiency)
                # Power jundtion
                self.power_junction_power.append(self.power_junction.power)
                # BMS
                self.battery_management_power.append(self.battery_management.power)
                self.battery_management_efficiency.append(self.battery_management.efficiency)
                # Battery
                self.battery_power.append(self.battery.power_battery)
                self.battery_efficiency.append(self.battery.efficiency)
                self.battery_power_loss.append(self.battery.power_loss)
                self.battery_temperature.append(self.battery.temperature)
                self.battery_state_of_charge.append(self.battery.state_of_charge)
                self.battery_state_of_health.append(self.battery.state_of_health)
                self.battery_capacity_current_wh.append(self.battery.capacity_current_wh)
                self.battery_capacity_loss_wh.append(self.battery.capacity_loss_wh)
                self.battery_voltage.append(self.battery.voltage)
                # Component state of destruction
                self.photovoltaic_state_of_destruction.append(self.pv.state_of_destruction)
                self.battery_state_of_destruction.append(self.battery.state_of_destruction)
                self.charger_state_of_destruction.append(self.charger.state_of_destruction)
                self.battery_management_state_of_destruction.append(self.battery_management.state_of_destruction)
                # Component replacement
                self.photovoltaic_replacement.append(self.pv.replacement)
                self.battery_replacement.append(self.battery.replacement)
                self.charger_replacement.append(self.charger.replacement)
                self.battery_management_replacement.append(self.battery_management.replacement)


            ## Simulation over: set needs_update to false and call end method
            self.needs_update = False
            print(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), ' End')
            self.end()
        