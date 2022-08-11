from simulatable import Simulatable
from serializable import Serializable

import numpy as np
import pandas as pd
from scipy.integrate import odeint
import math

class Heat_storage(Serializable, Simulatable):
    """Relevant methods to calculate heat storage temperature.
        
     Parameters
    ----------
    storage_volume : `int`
        [l] : Storage volume.
    storage_number : `int`
        [-] : Number of storages.
    timestep : `int`
        [s] Simulation timestep in seconds.
    environment : `class`
        To get access to solar irradiation, ambient temperature and windspeed.
    input_link_1: `class`
        Class of component which supplies input flow.
        (e.g. Pipe output temperature == storage input temperature.)
    load_link : `class`
        Class of component which defines heat/hot water load.
    file_path : `json`
        To load component parameters (optional).
        
    Note
    ----

    """

    def __init__(self,
                 storage_volume,
                 storage_number,
                 timestep,
                 env, 
                 file_path=None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for heat storage model specified')
            self.specification = "Heat Storage_Paradigma Aqua Expresso III"     # [-] Heat storage specification
            self.share_height_volume = 1.9866                                   # [m/m3] Share of storage height / storage volume
            self.share_diameter_volume = 0.8118                                 # [m/m3] Share of storage diameter / storage volume            
            self.density_fluid = 1060                                           # [kg/m3] Dendity Fluid Heat Storage
            self.heat_capacity_fluid = 4182                                     # [J/(kg K)] Heat capacity Fluid Solar
            self.heat_transfer_coef_storage = 0.4                               # [W/(m2 K)] Heat transition coefficient heat storages
            self.temperature_heating_room = 293.15                              # [K] Heating room temperature
            self.temperature_initial_perfectly_mixed = 313.15                   # [K] Initial storage temperature of perfectly mixed storage
            self.temperature_minimum = 333.15                                   # [K] Minimum heat storage temperature for charge algorithm
            self.temperature_maximum = 373.15                                   # [K] Maximum heat storage temperature for charge algorithm
            self.temperature_target = 313.15                                    # [K] Heat storage target temperature
            self.temperature_hysterese = 5.0                                    # [K] Heat management hysterese temperature
            self.investment_costs_specific = 0.01089                            # [$/Wh] Specific investment costs
            self.operation_maintenance_costs_share = 0.015                      # [1] Share of omc costs of cc
            
        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # Integrate environment class
        self.env = env

        # [s] Timestep
        self.timestep = timestep
        # [l] Storage volume
        self.storage_volume = storage_volume
        # [-] Number of storages
        self.storage_number = storage_number
        
        # Determine storage dimensions
        # [m3] Storage volume
        self.volume = self.storage_volume * self.storage_number / 1000
        # [m] Storage height        
        self.height_storage = self.volume * self.share_height_volume    
        # [m] Storage diameter
        self.diameter_storage = self.volume * self.share_diameter_volume 
        # [m2] Storage surface
        self.surface = (self.height_storage * (math.pi*self.diameter_storage)) \
                               + (math.pi*(self.diameter_storage/2)**2)         
                               
               
        ## Initialize initial parameters
        self.power = 0
        self.temperature = self.temperature_initial_perfectly_mixed
        
        # Economic model
        # [Wh] Nominal capacity
        self.size_nominal = self.volume * self.density_fluid * self.heat_capacity_fluid \
                            * (self.temperature_maximum-298.15) / 3600
        # [$/Wh] Storage specific investment costs
        self.investment_costs_specific = self.investment_costs_specific
        # [$/W] Electrolyzer specific operation and maintenance cost
        self.operation_maintenance_costs_specific = self.operation_maintenance_costs_share \
                                                    * self.investment_costs_specific
                                                    
        # Aging model
        self.replacement_set = 0
           
       
    def calculate(self):
        """Simulatable method.
        Calculation is done inside energy management of heat carrier.
        """
        
        # Calculate State of Desctruction
        self.get_state_of_destruction()    
        
        
    def get_temperature(self):
        '''
        Perfect Mixed Heat Storage.
 
        Parameters
        ----------
        None
        
        Note
        ----
        - Assumption that productive components get low static return tempertaure, which comes from low tempertaure niveau of storage.
        - This temperature distribution is not modelled but assumed to be always apparent at the bottom of the storage.
        - Therefore productive components power is calculated with its static temperature input and not with current mean storage temperature.
        '''

        # Heat storage temperature change per time
        self.temperature_change = ((1/(self.density_fluid * self.volume * self.heat_capacity_fluid)) \
                                   * self.power) * (self.timestep)            

      # Heat storage temperature
        self.temperature = self.temperature + self.temperature_change
        
 
    def get_temperature_loss(self):
        """ Perfect Mixed Heat Storage.
 
        Parameters
        ----------
        None
        
        Note
        ----
        - self discharge energy loss is considered.
        """

        # Heat storage temperature change per time through self discharge                                  
        self.temperature_change = ((1/(self.density_fluid * self.volume * self.heat_capacity_fluid)) \
                                   * (- self.surface * self.heat_transfer_coef_storage \
                                   * (self.temperature - self.temperature_heating_room))) \
                                   * (self.timestep)
                                   
      # Heat storage temperature
        self.temperature = self.temperature + self.temperature_change
        
        
    def get_state_of_destruction(self):
        """Calculates the component state of destruction (SoD) and time of
        component replacement according to end of life criteria.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        state_of_destruction : `float`
            [1] Component state of destruction.
        replacement : `int`
            [s] Time of component replacement in seconds.
        
        Note
        ----
        - replacement_set stays at last replacement timestep for correct sod calculation after first replacement.

        """

        # Calculate state of desctruction (end_of_life is given in seconds)
        self.state_of_destruction = (self.time - self.replacement_set) / (self.end_of_life/self.timestep)

        if self.state_of_destruction >= 1:
            self.replacement_set = self.time
            self.replacement = self.time
            self.state_of_destruction = 0
        else:
            self.replacement = 0