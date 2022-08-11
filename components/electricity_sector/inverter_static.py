from simulatable import Simulatable
from serializable import Serializable


class Inverter(Serializable, Simulatable):
    """Relevant methods for the calculation of power components performance.

    Parameters
    ----------
    timestep: `int`
        [s] Simulation timestep in seconds.
    power_nominal : `int`
        [W] Nominal power of power component in watt.
    links : `float`
        [W] Power of linked component.
    file_path : `json`
        To load components parameters (optional).

    Note
    ----
    - Model is based on method by Sauer and Schmid [1]_.
    - Model can be used for all power components with a power dependent efficiency.
        - e.g. Charge controllers, BMS, power inverters...

    .. [1] D. U. Sauer and H. Schmidt, "Praxisgerechte Modellierung und
                    Abschätzung von Wechselrichter-Wirkungsgraden’,
                    in 9. Internationales Sonnenforum - Tagungsband I, 1994, pp. 550–557
    """

    def __init__(self,
                 timestep,
                 power_nominal,
                 file_path = None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for inverter specified')
            self.type = "Inverter"                                              # [-] Power component type
            self.specification = "SolarEdge_10k"                                # [-] Specification of power component
            self.efficiency_nominal = 0.98                                      # [1] Nominal power component efficeincy
            self.efficiency_weighted = 0.976                                    # [1] Weighted power component efficeincy
            self.end_of_life = 315360000                                        # [s] End of life time in seconds
            self.investment_costs_specific = 0.484                              # [$/Wp] Specific investment costs
            self.operation_maintenance_costs_share = 0.0                        # [1] Share of omc costs of cc
            
        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate Serializable for serialization of component parameters
        Serializable.__init__(self)
        # Integrate Simulatable class for time indexing
        Simulatable.__init__(self)

        # [s] Timestep
        self.timestep = timestep
        # Nominal power of inverter
        self.power_nominal = power_nominal
        
        ## Power model
        # Initialize power
        self.link_power = 0
        
        self.power_load = 0
        self.efficiency_load = 0
        
        self.power_grid = 0
        self.efficiency_grid = 0
        
        ## Economic model
        # [W] Nominal installed component size for economic calculation
        self.size_nominal = power_nominal
        # [$/W] Inverter specific investment costs
        self.investment_costs_specific = self.investment_costs_specific
         # [$/W] Electrolyzer specific operation and maintenance cost
        self.operation_maintenance_costs_specific = self.operation_maintenance_costs_share \
                                                    * self.investment_costs_specific
                                                    
        ## Aging model
        self.replacement_set = 0



    def calculate(self):
        """Calls state of destruction calculation of inverter

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`
        """
            
        # Calculate State of Desctruction
        self.get_state_of_destruction()


    def get_power_output (self):
        """Calculates power component efficiency and output power (AC), dependent on Power Input eff(P_in).

        Parameters
        ----------
        None : `-`

        Returns
        -------
        efficiency : `float`
            [W] Component efficiency.
        """

        if self.link_power == 0:
            self.efficiency = 0.
            self.power_norm = 0.
        else:
            power_input = min(1, self.link_power / self.power_nominal)
            self.efficiency = self.efficiency_weighted
            self.power_norm = power_input * self.efficiency
            
            # In case of negative eta it is set to zero
            if self.efficiency < 0:
                self.efficiency = 0
                self.power_norm = 0

        self.power = self.power_norm * self.power_nominal
        

    def get_power_input (self):
        """Calculates power component efficiency and input power (DC), dependent on Power Output eff(P_out).

        Parameters
        ----------
        None : `-`

        Returns
        -------
        efficiency : `float`
            [W] Component efficiency.

        Note
        ----
        - Calculated power output is NEGATIVE but fuction can only handle Positive value.
        - Therefore first abs(), at the end -
        """

        #power_output = min(1, abs(self.input_link.power) / self.power_nominal)
        power_output = (abs(self.link_power) / self.power_nominal)

        self.efficiency = self.efficiency_weighted
        self.power_norm = power_output / self.efficiency

        self.power = - (self.power_norm * self.power_nominal)


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
        self.state_of_destruction = ((self.time+1) - self.replacement_set) / (self.end_of_life/self.timestep)
        
        if self.state_of_destruction >= 1:
            self.replacement_set = (self.time+1)
            self.replacement = (self.time+1)
            self.state_of_destruction = 0
        else:
            self.replacement = 0
            