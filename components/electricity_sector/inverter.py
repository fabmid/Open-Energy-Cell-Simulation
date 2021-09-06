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

            self.specification = "Inverter_generic"                        # [-] Specification of power component
            self.efficiency_nominal = 0.951                                     # [1] Nominal power component efficeincy
            self.voltage_loss = 0.009737                                        # [-] Dimensionless parameter for component model
            self.resistance_loss = 0.031432                                     # [-] Dimensionless parameter for component model
            self.power_self_consumption = 0.002671                              # [-] Dimensionless parameter for component model
            self.end_of_life = 315360000                       # [s] End of life time in seconds
            self.investment_costs_specific = 0.2                              # [$/Wp] Specific investment costs

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
        
        #Calculate star parameters of efficeincy curve
        self.voltage_loss_star =  self.voltage_loss
        self.resistance_loss_star  = self.resistance_loss / self.efficiency_nominal
        self.power_self_consumption_star  =  self.power_self_consumption * self.efficiency_nominal

        ## Power model
        # Initialize power
        self.link_power = 0
        
        self.power_load = 0
        self.efficiency_load = 0
        
        self.power_grid = 0
        self.efficiency_grid = 0
        
        ## Economic model
        # Nominal installed component size for economic calculation
        self.size_nominal = power_nominal

        ## Aging model
        self.replacement_set = 0


    def start(self):
        """Simulatable method, sets time=0 at start of simulation.       
        """


    def end(self):
        """Simulatable method, sets time=0 at end of simulation.    
        """

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
            self.efficiency = -((1 + self.voltage_loss_star) / (2 * self.resistance_loss_star * power_input)) \
                              + (((1 + self.voltage_loss_star)**2 / (2 * self.resistance_loss_star * power_input)**2) \
                              + ((power_input - self.power_self_consumption_star) / (self.resistance_loss_star * power_input**2)))**0.5
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

        self.efficiency = power_output / (power_output + self.power_self_consumption + (power_output * self.voltage_loss) \
                   + (power_output**2 * self.resistance_loss))
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
        self.state_of_destruction = (self.time - self.replacement_set) / (self.end_of_life/self.timestep)

        if self.state_of_destruction >= 1:
            self.replacement_set = self.time
            self.replacement = self.time
            self.state_of_destruction = 0
        else:
            self.replacement = 0
            