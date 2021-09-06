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
    storage_model : `-`
        [.] : Type of storage mode. `perfectly_mixed` or `stratified`.
    storage_volume : `int`
        [m3] : Storage volume.
    storage_number : `int`
        [-] : Number of storages.
    timestep : `int`
        [s] Simulation timestep in seconds.
    environment : `class`
        To get access to solar irradiation, ambient temperature and windspeed.
    input_link_1: `class`
        Class of component which supplies input flow.
        (e.g. Pipe output temperature == storage input temperature.)
    input_link_2 : `class`
        Class of component which supplies input flow. (Auxiliary component)
    load_link : `class`
        Class of component which defines heat/hot water load.
    file_path : `json`
        To load component parameters (optional).
        
    Note
    ----
    - Following storage model types are implemented:
        - Perfectly mixed storage with mean temperature.
        - Stratified storage with temperature distribution.
    - Stratified storage model:
        - Differential equation is used to calculate heat transport to environment.
        - Loading/disloading and energy transport between different storage layers.
        - Definition of Input / Output matrix:
            - Row 0=Input and Row 1=Output.
            - Column 0=input link 1, Column 1=input link 2, Column 2=Heating, Column 3=Hot water.
            - Set relative storage height (between 0 & 1) of input/output flows for all components.
            - Meaningful relative storage height is dependent on numbers of storagye layers.
        - Input link 1 should represent fluctuating energy source.
        - Input link 2 should represent back-up energy source.
    """

    def __init__(self,
                 storage_model,
                 storage_volume,
                 storage_number,
                 timestep,
                 env, 
                 input_link_1,
                 input_link_2,
                 output_link,
                 load_link,
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
            self.temperature_initial_perfectly_mixed = 353.15                   # [K] Initial storage temperature of perfectly mixed storage
            self.temperature_initial_stratified_bottom = 353.15                 # [K] Initial storage temperature of stratified storage at bottom
            self.temperature_initial_stratified_top = 353.15                    # [K] Initial storage temperature of stratified storage at top    
            self.layers_storage = 3                                             # [1] Number of layers in stratified heat storage
            self.temperature_minimum = 333.15                                   # [K] Minimum heat storage temperature for charge algorithm
            self.temperature_maximum = 373.15                                   # [K] Maximum heat storage temperature for charge algorithm
            self.input_input_link_1 = 0.99                                      # [1] Relative storage height for input of input Link 1 (dependent on layers_storage)
            self.output_input_link_1 = 0.01                                     # [1] Relative storage height for output of input Link 1 (dependent on layers_storage)
            self.input_input_link_2 = 0.99                                      # [1] Relative storage height for input of input Link 2 (dependent on layers_storage)
            self.output_input_link_2 = 0.01                                     # [1] Relative storage height for output of input Link 2 (dependent on layers_storage)
            self.input_heating = 0.01                                           # [1] Relative storage height for input of heating system (dependent on layers_storage)    
            self.output_heating = 0.99                                          # [1] Relative storage height for output of heating system (dependent on layers_storage)
            self.input_water = 0.01                                             # [1] Relative storage height for input of hot water system (dependent on layers_storage)
            self.output_water = 0.99                                            # [1] Relative storage height for output of hot water system (dependent on layers_storage)
         
        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # Integrate environment class
        self.env = env
        # Integrate flucutating energy technology
        # pipe coming from solarthermal/pipe as input link 1
        self.input_link_1 = input_link_1
        # Integrate auxiliary component as input link 2
        self.input_link_2 = input_link_2  
        # Integrate load_heat as load_link
        self.load_link = load_link
        # Storage model type
        self.storage_model = storage_model
        # [s] Timestep
        self.timestep = timestep
        # [m3] Storage volume
        self.storage_volume = storage_volume
        # [-] Number of storages
        self.storage_number = storage_number
        
        # Determine storage dimensions
        # [m3] Storage volume
        self.volume_storage = self.storage_volume * self.storage_number 
        # [m] Storage height        
        self.height_storage = self.volume_storage * self.share_height_volume    
        # [m] Storage diameter
        self.diameter_storage = self.volume_storage * self.share_diameter_volume 
        # [m2] Storage surface
        self.surface_storage = (self.height_storage * (math.pi*self.diameter_storage)) \
                               + (math.pi*(self.diameter_storage/2)**2)         
                               
        # Define number of storage layers and volume and surface area per layer
        # [m3] Volume heat storage layer
        self.volume_storage_layer = self.volume_storage/self.layers_storage 
        # [m2] Surface heat storage layer
        self.surface_storage_layer = self.surface_storage/self.layers_storage   
               
        ## Decision for storage model and loading of initial values
        if storage_model == 'stratified':
            ## Get matrixes for discretized storage model and initial storage temperature
            self.storage_discretized_load_matrix()
        
        elif storage_model == 'perfectly_mixed':
            ## Initialize initial parameters
            self.temperature_mean = self.temperature_initial_perfectly_mixed
        
        else:
            pass
       
        
    def calculate(self):
        """Calculates all heat storage performance parameters by calling implemented methods.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`
            
        Note
        ----
        - According to specified control type implemented methods are called.
        - For both model types maximum heat storage temperature threshold is verified.
        - Stratified storage model:
            - 1. Input temperature niveaus for productive and load components are defined. get_links_condition().
            - 2. Input/output volume flow rates for productive and load components are defined. get_links_condition(): 
                - Input = Output flows due to conservation of mass.
                - Load component flow rates need to be re-calculated with current storage temperature to cover heat demand.
            - 3. Load matrix for heat storage differential equation system is build. storage_discretized_load_matrix().
            - 4. Differential equation system is solved. storage_temperature_discretized().
        - Perfecly mixed storage modeL.
            - 1. Temperature change per timestep is calculated. storage_temperature_perfectly_mixed().
            - 2. Mean temperature is updated according to temperature change. storage_temperature_perfectly_mixed().
        """
                
        ## Storage charge algorithm:
        if self.storage_model == 'stratified':
            ## Supervision of maximum storage temperature
            if max(self.temperature_distribution) > self.temperature_maximum:
                # No volume flow from productive components
                self.input_link_1.volume_flow_rate = 0
                self.input_link_2.volume_flow_rate = 0       
            else:
                pass
            
            # Get conditions of all connceted input and load links
            self.get_links_condition()
            ## Call discetized storage temperature model
            self.storage_temperature_discretized()
               
        elif self.storage_model == 'perfectly_mixed':             
            ## Supervision of maximum storage temperature
            if self.temperature_mean > self.temperature_maximum:
                # No volume flow from productive components
                self.input_link_1.volume_flow_rate = 0
                self.input_link_2.volume_flow_rate = 0       
            else:
                pass
            
            ## Call perfectly mixed storage model
            self.storage_temperature_perfectly_mixed()
        
        else:
            print('Heat storage model type undefined! Set perfectly_mixed or stratified.')
        
            
    def get_links_condition(self):
        """Stratified Storage model: Defines temperatures and flow rates of physical heat storage set-up.
        Consumption and production values of connected productive and load components
        
        Parameters
        ----------
        None : `None`

        Returns
        -------
        temperature_input_link_1 : `float`
            [K] Input link 1 flow temperature.
        temperature_input_link_2 : `float`
            [K] Input link 2 flow temperature.
        temperature_water : `float`
            [K] Fresh water temperature.
        temperature_heating : `float`
            [K] Heating system return temperature.
        volume_flow_rate_input_link_1 : `float`
            [K] Input link 1 volume_flow_rate.
        volume_flow_rate_input_link_2 : `float`
            [K] Input link 2 volume_flow_rate.
        volume_flow_rate_water : `float`
            [K] Fresh water volume_flow_rate.
        volume_flow_rate_heating : `float`
            [K] Heating system volume_flow_rate.    
            
        Note
        ----
        - Load volume flow rate gets re-calculated to current load flow temperature, 
          which is dependent on dynamic heat storage temperature.
          
        """
        
        ## Storage Input temperatures & flow rates from productive components
        # [K] Input link 1 flow temperature (e.g. solarthermal/pipe)
        self.temperature_input_link_1 = self.input_link_1.temperature_output
        # [K] Input link 2 flow temperature (e.g. auxiliary component)
        self.temperature_input_link_2 = self.input_link_2.temperature_output   
        # [m3/s] Input link 1 volume flow (e.g. solarthermal(pipe))
        self.volume_flow_rate_input_link_1 = self.input_link_1.volume_flow_rate
        # [m3/s] Input link 2 volume flow (e.g. auxiliary component)    
        self.volume_flow_rate_input_link_2 = self.input_link_2.volume_flow_rate  
          
        ## Storage Input temperatures as return temperature or fresh water from load components
        # [K] Hot water "fresh water" temperature
        self.temperature_water = self.load_link.hotwater_temperature_return     
        # [K] Heating system return temperature 
        self.temperature_heating = self.load_link.heating_temperature_return    
      
        ## Storage Output flow rates of load components        
        # Set load hot water flow temperature to current storage out temperature at output niveau
        self.load_link.hotwater_temperature_flow = self.temperature_output[3]
        # Call load link method to re-calculate volume flow rate for hot water demand
        self.load_link.re_calculate()
        # Get re-caluclated volume flow rate for hot water demand [m3/s] 
        self.volume_flow_rate_water = self.load_link.hotwater_volume_flow_rate
 
        # Set load heating flow temperature to current storage out temperature at output niveau
        self.load_link.heating_temperature_flow = self.temperature_output[2]
        # Call load link method to re-calculate volume flow rate for heating demand
        self.load_link.re_calculate()
        # Get re-caluclated volume flow rate for heating demand   
        self.volume_flow_rate_heating = self.load_link.heating_volume_flow_rate # [m3/s] Volume flow heating system


    def storage_discretized_load_matrix(self):
        """Stratified Storage model: Defines load matrix for heat storage differential equation system.
        
        Parameters
        ----------
        None : `None`
        
        Returns
        -------
        matrix_in : `nd.array`
            [-] Input/output matrix of heat storage for differential equation solver.
        matrix_transfer : `nd.array`
            [-] Transfer matrix of heat storage for differential equation solver.
            
        Note
        ----
        - Definition of:
            - Input/output matrix with storage heights of input/outputs flows.
            - Initial storage temperature distribution.
            - Transfer matrix.
        - Input/output matrix includes:
            - Row 0: Input and Row 1: Output.
            - Column 0: Input link 1 (e.g. solarthermal).
            - Column 1: Input link 2 (e.g.Boiler).
            - Column 2: Heating.
            - Column 3: Hot water.
        - Same indices need to be sued for access of storage output temperature.
            - For heating flow temperature access temperature_putput[2].

        """
        
        ## Definition of Input/Output matrix
        ## Set relative storage height (between 0 & 1) of input/output flows
        ## Row 0: Input and Row 1: Output
        # Column 0: Input link 1 (e.g. solarthermal)
        # Column 1: Input link 2 (e.g.Boiler)
        # Column 2: Heating
        # Column 3: Hot water
        
        self.in_out = np.zeros([2,4])
        
        # Input link 1 (e.g. Solarthermal)
        self.in_out[0,0] = self.input_input_link_1
        self.in_out[1,0] = self.output_input_link_1
        # Input link 1 (e.g. Boiler)
        self.in_out[0,1] = self.input_input_link_2
        self.in_out[1,1] = self.output_input_link_2
        # Heating
        self.in_out[0,2] = self.input_heating
        self.in_out[1,2] = self.output_heating
        # Hot water
        self.in_out[0,3] = self.input_water
        self.in_out[1,3] = self.output_water

        ## Define initial temperature distribution
        # Temperature layers list
        self.temperature_distribution = np.full(self.layers_storage, np.nan)
        # Initial temperature for given layers and linear interpolation
        self.temperature_distribution[0] = self.temperature_initial_stratified_bottom
        self.temperature_distribution[self.layers_storage-1] = self.temperature_initial_stratified_top
        self.temperature_distribution = pd.Series(self.temperature_distribution)
        self.temperature_distribution = self.temperature_distribution.interpolate(method='linear')
        self.temperature_distribution = self.temperature_distribution.values

        ## Intitialization of Input/Output matrix
        # Relative step width of storage height
        self.stepwidth_relative_storage_height = (self.height_storage / self.layers_storage) / self.height_storage
        # Realtive storage height vector between 0 and 1 with stepwidth
        self.vector_relative_storage_height = np.arange(0, 1, self.stepwidth_relative_storage_height)

        ## Filling of Input/Output Matrix
        # Define empty matrix
        self.matrix_in_out = np.zeros([self.layers_storage, 5])
        # Set Index: Relative storage height in column 0
        self.matrix_in_out[0:,0] = self.vector_relative_storage_height

        # Iteration over all components: Input/output links
        for j in range(0, len(self.in_out[0,:])):

            # Iteration over all storage layers
            for i in range(0, self.layers_storage-1):
                
                # Searching of component input layer --> set 1
                if self.matrix_in_out[i,0] <= self.in_out[0,j] < self.matrix_in_out[i+1,0]:
                    self.matrix_in_out[i,j+1] = 1
                
                # Searching of component output layer --> set -1
                if self.matrix_in_out[i,0] <= self.in_out[1,j] < self.matrix_in_out[i+1,0]:
                    self.matrix_in_out[i,j+1] = -1
                
                # In case component relative heght is above maximum relative height
                elif self.in_out[1,j] >= self.matrix_in_out[-1,0]:
                    self.matrix_in_out[-1,j+1] = -1
                elif self.in_out[0,j] >= self.matrix_in_out[-1,0]:
                    self.matrix_in_out[-1,j+1] = 1
                    
        # Display in/output matrix definition
        #print('F_in_out:', self.matrix_in_out)

        # Get relative height of input and output flows (returns tuble with list of row number and list of column number)
        self.index_in = np.where(self.matrix_in_out == 1)
        self.index_out = np.where(self.matrix_in_out == -1)

        ## Intitialization of Transfer matrix
        # Filling of Transfer Matrix
        self.matrix_transfer = np.zeros([self.layers_storage, 5])
        # Set Index: Relative storage height in column 0
        self.matrix_transfer[0:,0] = self.vector_relative_storage_height

        # Iteration over all components: Input/output links
        for j in range(0, len(self.in_out[0,:])):
            
            # Get input rows of component
            row_in = self.index_in[0][j]
            # Get component column
            component = self.index_in[1][j]
            # Get output row of component
            row_out =  self.index_out[0][component-1]

            # Iteration over all storage layers
            for i in range(0,self.layers_storage):
                
                # Consumer components: Set 1 between input and output row
                if row_out == i and (component == 3 or component == 4):
                    self.matrix_transfer[i,component] = 1
                elif row_out >= i > row_in:
                    self.matrix_transfer[i,component] = 1
                
                # Producer component: Set -1 between input and output row
                elif row_out == i and (component == 1 or component == 2):
                    self.matrix_transfer[i,component] = -1
                elif row_out < i < row_in:
                    self.matrix_transfer[i,component] = -1

        ## Intitialization of Input matrix
        self.matrix_in = self.matrix_in_out
        # Deleting all output flows
        self.matrix_in[self.index_out] = 0

        ## Initialize storage temperature distribution at outputs
        # Heat storage temperature at output flow layers
        self.temperature_output = self.temperature_distribution[self.index_out[0]]
        
        
    def storage_temperature_discretized(self):
        """Stratified Storage model: Calculates storage temperature distribution 
        through solving of differential equation system.
        
        Parameters
        ----------
        None : `None`

        Returns
        -------
        temperature_distribution : `float`
            [K] Heat storage temperature distribution over all layers.
        temperature_output : `float`
            [K] Heat storage output temperature at specified output layers.
        temperature_mean : `float`
            [K] Heat storage mean temperature over all layers.
        
        Note
        ----
        - Solver differential equation system is defined in storage_discretized_load_matrix()
        - For storage output temperatures going to connected components use following indices:
            - Column 0: Input link 1 (e.g. Solarthermal).
            - Column 1: Input link 2 (e.g.Aux component).
            - Column 2: Heating.
            - Column 3: Hot water       
        """
        ## Definition of differential equation system
        def storage_temperature_discretized_fct(temperature, t, 
                                                volume_storage_layer, 
                                                surface_storage_layer,
                                                heat_transfer_coef_storage, 
                                                temperature_heating_room, 
                                                density_fluid, 
                                                heat_capacity_fluid, 
                                                temperature_input_link_1,
                                                temperature_input_link_2, 
                                                temperature_water, 
                                                temperature_heating,
                                                volume_flow_rate_input_link_1, 
                                                volume_flow_rate_input_link_2, 
                                                volume_flow_rate_water, 
                                                volume_flow_rate_heating,
                                                matrix_in, 
                                                matrix_transfer, 
                                                layers_storage):

            # Define empty storage temperature array
            dT_Sdt = np.zeros(layers_storage)
            
            # Boundary condition BOTTOM
            dT_Sdt[0] = 1/volume_storage_layer * (( heat_transfer_coef_storage * surface_storage_layer \
                        / (heat_capacity_fluid * density_fluid)) * (temperature_heating_room - temperature[0]) \
                        + matrix_in[0,1] * volume_flow_rate_input_link_1 * (temperature_input_link_1 - temperature[0]) \
                        + matrix_in[0,2] * volume_flow_rate_input_link_2 * (temperature_input_link_2 - temperature[0]) \
                        + matrix_in[0,3] * volume_flow_rate_heating * (temperature_heating - temperature[0]) \
                        + matrix_in[0,4] * volume_flow_rate_water * (temperature_water - temperature[0]) \
                        + matrix_transfer[0,1] * volume_flow_rate_input_link_1 * (temperature[0] - temperature[1]) \
                        + matrix_transfer[0,2] * volume_flow_rate_input_link_2 * (temperature[0] - temperature[1]))

            # All layers between bottom and top layer
            dT_Sdt[1:-1] = 1/volume_storage_layer * (( heat_transfer_coef_storage * surface_storage_layer \
                           / (heat_capacity_fluid * density_fluid)) * (temperature_heating_room - temperature[1:-1]) \
                           + matrix_in[1:-1,1] * volume_flow_rate_input_link_1 * (temperature_input_link_1 - temperature[1:-1]) \
                           + matrix_in[1:-1,2] * volume_flow_rate_input_link_2 * (temperature_input_link_2 - temperature[1:-1]) \
                           + matrix_in[1:-1,3] * volume_flow_rate_heating * (temperature_heating - temperature[1:-1]) \
                           + matrix_in[1:-1,4] * volume_flow_rate_water * (temperature_water - temperature[1:-1]) \
                           + matrix_transfer[1:-1,1] * volume_flow_rate_input_link_1 * (temperature[1:-1] - temperature[2:]) \
                           + matrix_transfer[1:-1,2] * volume_flow_rate_input_link_2 * (temperature[1:-1] - temperature[2:]) \
                           + matrix_transfer[1:-1,3] * volume_flow_rate_heating * (temperature[0:-2] - temperature[1:-1]) \
                           + matrix_transfer[1:-1,4] * volume_flow_rate_water * (temperature[0:-2] - temperature[1:-1]))

            # Boundary condition TOP
            dT_Sdt[-1] = 1/volume_storage_layer * (( heat_transfer_coef_storage * surface_storage_layer \
                         / (heat_capacity_fluid * density_fluid)) * (temperature_heating_room - temperature[-1]) \
                         + matrix_in[-1,1] * volume_flow_rate_input_link_1 * (temperature_input_link_1 - temperature[-1]) \
                         + matrix_in[-1,2] * volume_flow_rate_input_link_2 * (temperature_input_link_2 - temperature[-1]) \
                         + matrix_in[-1,3] * volume_flow_rate_heating * (temperature_heating - temperature[-1]) \
                         + matrix_in[-1,4] * volume_flow_rate_water * (temperature_water - temperature[-1]) \
                         + matrix_transfer[-1,3] * volume_flow_rate_heating * (temperature[-2] - temperature[-1]) \
                         + matrix_transfer[-1,4] * volume_flow_rate_water * (temperature[-2] - temperature[-1]))

            return dT_Sdt
        
        ## Solving of differential equation system    
        # Time vector: defines the times for which equation shall be solved in seconds.
        self.time_vector = np.linspace(0,self.timestep,self.timestep)
        # Call numeric solver
        self.storage_temperature_solve = odeint(storage_temperature_discretized_fct, 
                                                self.temperature_distribution,
                                                self.time_vector, 
                                                args=(self.volume_storage_layer,
                                                      self.surface_storage_layer,
                                                      self.heat_transfer_coef_storage,
                                                      self.temperature_heating_room,
                                                      self.density_fluid,
                                                      self.heat_capacity_fluid,
                                                      self.temperature_input_link_1,
                                                      self.temperature_input_link_2,
                                                      self.temperature_water,
                                                      self.temperature_heating,
                                                      self.volume_flow_rate_input_link_1,
                                                      self.volume_flow_rate_input_link_2,
                                                      self.volume_flow_rate_water,
                                                      self.volume_flow_rate_heating,
                                                      self.matrix_in, 
                                                      self.matrix_transfer,
                                                      self.layers_storage))

        # Heat storage temperature
        self.temperature_distribution = self.storage_temperature_solve.T[:,-1]
        # Heat storage temperature at output flow layers
        self.temperature_output = self.temperature_distribution[self.index_out[0]]
        # Heat storage mean temperature
        self.temperature_mean = np.sum(self.temperature_distribution) / len(self.temperature_distribution)
        

    def storage_temperature_perfectly_mixed(self):
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
        self.temperature_change = ((1/(self.density_fluid * self.volume_storage * self.heat_capacity_fluid)) \
                                   * ((self.input_link_1.volume_flow_rate * self.density_fluid * self.heat_capacity_fluid \
                                   * (self.input_link_1.temperature_output - self.input_link_1.temperature_input)) \
                                   + (self.input_link_2.volume_flow_rate * self.density_fluid * self.heat_capacity_fluid \
                                   * (self.input_link_2.temperature_output - self.input_link_2.temperature_input)) \
                                   - self.surface_storage * self.heat_transfer_coef_storage * (self.temperature_mean - self.temperature_heating_room) \
                                   - self.load_link.heating_power - self.load_link.hotwater_power)) \
                                   * (self.timestep)
            
        # Solar power stored into storage
        self.input_link_1.power_to_storage = (self.input_link_1.volume_flow_rate * self.density_fluid * self.heat_capacity_fluid \
                                             * (self.input_link_1.temperature_output - self.input_link_1.temperature_input))
        # Heat storage temperature
        self.temperature_mean = self.temperature_mean + self.temperature_change