from simulatable import Simulatable
from serializable import Serializable


class Heat_Pump(Serializable, Simulatable):
    """Relevant methods for the calculation of heat pump performance.
    
    Parameters
    ----------
    timestep : 'int'
        [s] Simulation timestep in seconds.
    peak_power_th : `int`
        [Wp] Installed wind turbine peak power.
    env : 
    
    file_path : `json`
        To load component parameters (optional).     
        
    Note
    ----
    - Peak thermal power is defined at the point L+2/W35 and 100% speed.
        - Parameter is used to scale heat pump with given specification power_th (also at L+2/W35)
    - Fitting of thermal, electric power and cop is done with temperatures in °C.
    - Ambient temperature is loaded in K and therfore transfered inside this class to °C.
    """

    def __init__(self,
                 timestep,
                 peak_power_th,
                 env,
                 file_path=None):

        # Read component parameters of wind turbine from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for wind turbine model specified')
            self.type = "ratiotherm_WP Max-Air"                                 # [-] Heat pump specification
            self.power_th = 17700                                               # [W] Thermal power output at L+2/W35
            self.temperature_flow = 318.15                                      # [K] Heat pump flow temperature
            self.temperature_threshold_icing = 276.15                           # [K] Temperature under which icing occurs
            self.factor_icing = 0.0                                             # [1] COP reduction/ power_el increase due to icing
            self.temperature_heat_storage_target = 308.15                       # [K] Heat storage target temperature    
            self.temperature_hysterese = 5                                      # [K] Heat management hysterese temperature
            
            self.density_fluid = 1060                                           # [kg/m3] Density fuild (heating fluid-water)
            self.heat_capacity_fluid = 4182                                     # [J/(kg K)] Heat capacity fluid (heating fluid-water)

            self.cop_data = {"speed_100": [64.231900, 0.494216, -0.805786, -0.002182, 0.000502, 0.002091],
                             "speed_75": [77.914900, 0.544389, -0.932084, -0.002481, 0.000605, 0.002401],
                             "speed_50": [40.391500, 1.054150, -1.120120, -0.002327, -0.000423, 0.002618],
                             "speed_25": [99.130900, 0.698248, -1.188390, -0.002778, 0.000516, 0.002908]}
            self.power_el_data = {"speed_100": [64.231900, 0.494216, -0.805786, -0.002182, 0.000502, 0.002091],
                                  "speed_75": [77.914900, 0.544389, -0.932084, -0.002481, 0.000605, 0.002401],
                                  "speed_50": [40.391500, 1.054150, -1.120120, -0.002327, -0.000423, 0.002618],
                                  "speed_25": [99.130900, 0.698248, -1.188390, -0.002778, 0.000516, 0.002908]},
            self.power_th_data = {"speed_100": [87.028000, 0.933585, -1.448790, -0.001991, 0.000000, 0.003000],
                                  "speed_75": [47.157700, 1.008630, -1.239850, -0.002398, -0.000006, 0.002865],
                                  "speed_50": [87.495000, 0.464321, -0.988795, -0.000991, -0.000004, 0.001905],
                                  "speed_25": [-112.740000, 0.471240, 0.285696, -0.001299, 0.000032, 0.000068]}
            
            self.end_of_life = 473040000                                        # [s] End of life time in seconds
            self.investment_costs_specific = 0.69817                           # [$/Wp] Heat pump specific investment costs
            self.operation_maintenance_costs_share = 0.01                       # [1] Share of omc costs of cc
            
        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # [s] Timestep
        self.timestep = timestep
        # Integrate environment class
        self.env = env

        ## Basic parameters
        # Thermal power output
        self.peak_power_th = peak_power_th
        # Scaling of thermal power output
        self.power_scaling = self.peak_power_th / self.power_th
        # Icing factor
        self.icing = 0
        
        # Return temperature of heat load
#        self.temperature_return = 20 
   
        ## Initial values
        self.operation_mode = 'Off'
        self.power = 0
        self.power_el = 0
        self.power_th = 0
        
        # Economic model
        # [Wth] Nominal power
        self.size_nominal = self.peak_power_th
        # [$/Wth] Heat Pump specific investment costs
        self.investment_costs_specific = self.investment_costs_specific
        # [$/W] Electrolyzer specific operation and maintenance cost
        self.operation_maintenance_costs_specific = self.operation_maintenance_costs_share \
                                                    * self.investment_costs_specific
                                                    
        # Aging model
        self.replacement_set = 0
        
    def start(self):
        """Simulatable method, sets time=0 at start of simulation.       
        """


    def end(self):
        """Simulatable method, sets time=0 at end of simulation.    
        """       

        
    def calculate(self):
        """Simulatable method.
        Calculation is done inside energy management of heat carrier.
        """
             
        # Calculate State of Desctruction
        self.get_state_of_destruction()

        
    def get_power_thermal(self):
        """Calculates thermal power output of heat pump
        
        Parameters
        ----------
        None : `None`

        Returns
        -------
        power_th : `float`
            [W] Heat pump thermal power output.
            
        Note
        ----
        - Calculation is done according to fiting to manufacturer data.
        """
        
        # Calculation of thermal energy
        self.power_th = self.power_scaling * 1000 * (self.power_th_data[self.speed_set][0] \
                        + self.power_th_data[self.speed_set][1] * self.temperature_evap \
                        + self.power_th_data[self.speed_set][2] * self.temperature_cond \
                        + self.power_th_data[self.speed_set][3] * self.temperature_evap * self.temperature_cond \
                        + self.power_th_data[self.speed_set][4] * self.temperature_evap**2 \
                        + self.power_th_data[self.speed_set][5] * self.temperature_cond**2)
        
        # Flow/return temperatures and volume flow rate
#        self.volume_flow_rate = self.power_th / (self.heat_capacity_fluid * self.density_fluid \
#                                * (self.temperature_flow - self.temperature_return))                
#        self.temperature_input = self.temperature_return
#        self.temperature_output = self.temperature_flow
 
       
    def get_power_electric(self):
        """Calculates electric power consumption of heat pump
        
        Parameters
        ----------
        None : `None`

        Returns
        -------
        power_el : `float`
            [W] Heat pump electric power input.
            
        Note
        ----
        - Calculation is done according to fiting to manufacturer data.
        """
        
        # Calculation of electric energy
        self.power_el = (1+self.icing) * self.power_scaling * 1000 * (self.power_el_data[self.speed_set][0] \
                        + self.power_el_data[self.speed_set][1] * self.temperature_evap \
                        + self.power_el_data[self.speed_set][2] * self.temperature_cond \
                        + self.power_el_data[self.speed_set][3] * self.temperature_evap * self.temperature_cond \
                        + self.power_el_data[self.speed_set][4] * self.temperature_evap**2 \
                        + self.power_el_data[self.speed_set][5] * self.temperature_cond**2)

        # Define electric heat pump power as load power (negative)
        self.power = -self.power_el
        
    def get_coefficient_of_performance(self):
        """Calculates the coefficient of performance of heat pump
        
        Parameters
        ----------
        None : `None`

        Returns
        -------
        cop : `float`
            [1] Heat pump coefficient of performance.
            
        Note
        ----
        - Calculation is done according to fiting to manufacturer data.
        """
        
        # Calculation of electric energy
        self.cop = self.cop_data[self.speed_set][0] \
                    + self.cop_data[self.speed_set][1] * self.temperature_evap \
                    + self.cop_data[self.speed_set][2] * self.temperature_cond \
                    + self.cop_data[self.speed_set][3] * self.temperature_evap * self.temperature_cond \
                    + self.cop_data[self.speed_set][4] * self.temperature_evap**2 \
                    + self.cop_data[self.speed_set][5] * self.temperature_cond**2

                        
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
            