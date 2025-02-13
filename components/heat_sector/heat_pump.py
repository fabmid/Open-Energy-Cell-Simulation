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
    - Model is based on hplib
        - https://github.com/RE-Lab-Projects/hplib/tree/v1.9
    - Peak thermal power is defined at the point -7/55 and 100% speed.
        - Parameter is used to scale heat pump with given specification power_th (also at L+2/W35) --> revise this.
    - Fitting parameters for thermal, electric power and cop/eer are for equations with temperatures in °C.
    - Important temperatures: 
        - Primary input temperature (t_in_prim) - ambient conditions in case of air-water HP
        - Ambient / outdoor temperature (t_amb) in °C 
        - Secondary input temperature (t_in_secondary) - return of heating system (assumed 5K below flow temperature)
        - Output temperature
            - Heating mode: The t_in_sec is supposed to be heated up by 5 K which results in the output flow temperature
            - Cooling mode: The t_in_sec is supposed to be cooled down by 5 K which results in the output flow temperature
    - Coolign mode: In case no cooling storage is implemented, the thermal/electric power is scaled to exactly meet the cooling demand.
    - Currently two instances of the heat pump class needs to be defined in roder to simulate heat pump in heating and coolign mode
        - This shall be imporved in future versions
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
            print('Attention: No json file for heat pump model specified')
            self.type = "Heatpump_air-water"                                    # [-] Heat pump type
            self.specification = "hplib: Generic"                               # [-] Heat pump specification
            self.temperature_in_sec_heating_mode = 313.15                       # [K] Heating mode: Heat pump secondary temperature, will be heated up by 5K: 40+5=45°C
            self.temperature_in_sec_cooling_mode = 288.15                       # [K] Cooling mode: Heat pump secondary temperature, will be cooled down by 5K: 20-5=15°C
            self.temperature_delta = 5                                          # [K] Heating/Cooling mode: temperature increase/decrease through heat pump: 5K      
            self.temperature_threshold_icing = 276.15                           # [K] Temperature under which icing occurs
            self.factor_icing = 0.0                                             # [1] COP reduction/ power_el increase due to icing
            self.temperature_heat_storage_target = 308.15                       # [K] Heat storage target temperature    
            self.temperature_hysterese = 5                                      # [K] Heat management hysterese temperature           
            self.density_fluid = 1060                                           # [kg/m3] Density fuild (heating fluid-water)
            self.heat_capacity_fluid = 4182                                     # [J/(kg K)] Heat capacity fluid (heating fluid-water)

            self.p_th_ref = 10168.8                                             # [W] Thermal heating power at -7°C / 52°C 
            self.p_el_h_ref = 7193.432575                                       # [W] Electrical power at -7°C / 52°C 
            self.p_el_c_ref = 4928.94
            
            self.p1_p_el_h = 65.24998302                                        # [-] Fit-Parameters for electrical power in heating mode
            self.p2_p_el_h = 0.011364929                                        # [-] Fit-Parameters for electrical power in heating mode
            self.p3_p_el_h = 0.047006715                                        # [-] Fit-Parameters for electrical power in heating mode
            self.p4_p_el_h = -65.29932854                                       # [-] Fit-Parameters for electrical power in heating mode
            self.p1_cop	= 46.374629                                             # [-] Fit-Parameters for COP
            self.p2_cop	= -0.087566678                                          # [-] Fit-Parameters for COP
            self.p3_cop	= 7.045435211                                           # [-] Fit-Parameters for COP
            self.p4_cop	= -46.22057939                                          # [-] Fit-Parameters for COP
            
            self.p1_p_el_c = 69.60060772                                        # [-] Fit-Parameters for electrical power in cooling mode         
            self.p2_p_el_c = -0.009207906                                       # [-] Fit-Parameters for electrical power in cooling mode                 
            self.p3_p_el_c = -1.368637967                                       # [-] Fit-Parameters for electrical power in cooling mode         
            self.p4_p_el_c = -69.53274109                                       # [-] Fit-Parameters for electrical power in cooling mode         
            self.p1_eer	= -13.20985038                                          # [-] Fit-Parameters for EER
            self.p2_eer	= 0.064839857                                           # [-] Fit-Parameters for EER
            self.p3_eer	= 11.52004943                                           # [-] Fit-Parameters for EER
            self.p4_eer	= 12.96140005                                           # [-] Fit-Parameters for EER
            
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
        self.power_scaling = self.peak_power_th / self.p_th_ref
        # Icing factor
        self.icing = 0
        
        # Return temperature of heat load
#        self.temperature_return = 20 
   
        ## Initial values
        self.operation_mode = 'Off'
        self.power_cooling_mode = 0
        self.power_heating_mode = 0
        self.power_el = 0
        self.power_th = 0
        
        # Heating or cooling mode 0='Standby', 1='heating', 2='cooling'
        self.working_mode = 1
        
        # Power adjustment factor for cooling mode
        self.power_adjustment = 0
        
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
        
#    def start(self):
#        """Simulatable method, sets time=0 at start of simulation.       
#        """
#
#
#    def end(self):
#        """Simulatable method, sets time=0 at end of simulation.    
#        """       

        
    def calculate(self):
        """Simulatable method.
        Calculation is done inside energy management of heat carrier.
        """
             
        # Calculate State of Desctruction
        self.get_state_of_destruction()

        
        
    def get_power_heating_mode(self):
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
        - Calculation is done according to fitting paraneters from hplib.
            - https://github.com/RE-Lab-Projects/hplib
        """

        ## Heating mode
        # Calculate heat pump output (flow) tempertaure
        self.temperature_out = (self.temperature_in_sec_heating_mode + self.temperature_delta)
        
        if self.working_mode == 1:
            # Calculate COP
            self.cop = (self.p1_cop * (self.temperature_in_prim-273.15)
                       + self.p2_cop * (self.temperature_out-273.15)
                       + self.p3_cop
                       + self.p4_cop * (self.temperature_in_prim-273.15))
            
            # Calculate electric power
            self.power_el = (self.power_scaling
                            * (self.p_el_h_ref  * (self.p1_p_el_h*(self.temperature_in_prim-273.15)
                            + self.p2_p_el_h * (self.temperature_out-273.15) 
                            + self.p3_p_el_h 
                            + self.p4_p_el_h * (self.temperature_in_prim-273.15))))
            
            # Minimal operating point: 25% part load reference power
            self.power_el_25 = (self.power_scaling
                            * 0.25 * (self.p_el_h_ref * (self.p1_p_el_h*(-7)
                            + self.p2_p_el_h * (self.temperature_out-273.15) 
                            + self.p3_p_el_h 
                            + self.p4_p_el_h * (-7))))
            
            if self.power_el < self.power_el_25:
                self.power_el = self.power_el_25
            
            # Calculate thermal power
            self.power_th = self.power_el * self.cop
        
            # Low COP check
            if self.cop <= 1:
                # Das muss überarbeitet werden , HP wird ja bei diesn Bedingungen nicht P_th_ref erreichen
                self.cop = 1
                self.power_el = self.p_th_ref
                self.power_th = self.p_th_ref
        
        else:
             print('HP operation mode not specified!')
        
        # Define electric heat pump power as load power (negative)
        self.power = -self.power_el
        
 
    def get_power_cooling_mode(self):
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
        - Calculation is done according to fitting paraneters from hplib.
        - https://github.com/RE-Lab-Projects/hplib
        """
          
        ## Cooling mode    
        # Calculate heat pump output (flow) tempertaure
        self.tempertuare_out = (self.temperature_in_sec_cooling_mode - self.temperature_delta)
        
        if self.working_mode == 2:
            # Calculate EER
            self.eer = (self.p1_eer * (self.temperature_in_prim -273.15)
                        + self.p2_eer * (self.tempertuare_out-273.15) 
                        + self.p3_eer 
                        + self.p4_eer * (self.temperature_in_prim-273.15))
            
            # Calculate electric power
            # Minimal temperature operating point 25°C (298.15K) for input/ambient temperature
            if self.temperature_in_prim < 298.15:
                self.temperature_in_prim = 298.15                    
                self.power_el = (self.power_scaling 
                                * (self.p_el_c_ref * (self.p1_p_el_c*(self.temperature_in_prim-273.15)
                                + self.p2_p_el_c * (self.tempertuare_out-273.15)
                                + self.p3_p_el_c 
                                + self.p4_p_el_c * (self.temperature_in_prim-273.15))))
            else:            
                self.power_el = (self.power_scaling 
                                * (self.p_el_c_ref * (self.p1_p_el_c*(self.temperature_in_prim-273.15)
                                + self.p2_p_el_c * (self.tempertuare_out-273.15)
                                + self.p3_p_el_c 
                                + self.p4_p_el_c * (self.temperature_in_prim-273.15))))
            
            # Check for negative elec power
            if self.power_el < 0:
                    self.eer = 0
                    self.power_el = 0
            
            # Check for low EER (in tghis case heat pump can not be operated - too hot temperatures)
            if self.eer < 1:
                    self.eer = 0
                    self.power_el = 0
                    self.power_th = 0
                    
            # Calculate thermal power    
            self.power_th = self.power_el * self.eer
        
        else:
             print('HP operation mode not specified!')
        
        # Define electric heat pump power as load power (negative)
        self.power = -self.power_el
 
                        
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
            