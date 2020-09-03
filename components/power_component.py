from simulatable import Simulatable
from serializable import Serializable


class Power_Component(Serializable, Simulatable):
    """Relevant methods for the calculation of power components performance.

    Parameters
    ----------
    timestep: `int`
        [s] Simulation timestep in seconds.
    power_nominal : `int`
        [W] Nominal power of power component in watt.
    input_link : `class`
        [-] Class of component which supplies input power.
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
                 input_link,
                 file_path = None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for power component efficiency specified')

            self.specification = "MPPT_HQST_40A_12V_34V"                        # [-] Specification of power component
            self.efficiency_nominal = 0.951                                     # [1] Nominal power component efficeincy
            self.voltage_loss = 0.009737                                        # [-] Dimensionless parameter for component model
            self.resistance_loss = 0.031432                                     # [-] Dimensionless parameter for component model
            self.power_self_consumption = 0.002671                              # [-] Dimensionless parameter for component model
            self.end_of_life_power_components = 315360000                       # [s] End of life time in seconds
            self.investment_costs_specific = 0.036                              # [$/Wp] Specific investment costs

        # Integrate Serializable for serialization of component parameters
        Serializable.__init__(self) # not needed !?
        # Integrate Simulatable class for time indexing
        Simulatable.__init__(self) # not needed !?
        # Integrate input power
        self.input_link = input_link
        # [s] Timestep
        self.timestep = timestep

        #Calculate star parameters of efficeincy curve
        self.voltage_loss_star =  self.voltage_loss
        self.resistance_loss_star  = self.resistance_loss / self.efficiency_nominal
        self.power_self_consumption_star  =  self.power_self_consumption * self.efficiency_nominal

        ## Power model
        # Initialize power
        self.power = 0
        # set nominal power of power component
        self.power_nominal = power_nominal

        ## Economic model
        # Nominal installed component size for economic calculation
        self.size_nominal = power_nominal


    def calculate(self):
        """Calculates all power component performance parameters from
        implemented methods. Decides weather input_power or output_power method is to be called

        Parameters
        ----------
        None : `None`

        Returns
        -------
        efficiency : `float`
            [1] Component efficieincy
        power : `float`
            [W] Component input/output power in watts.
        state_of_destruction : `float`
            [-] Component state of destruction.
        replacement : `float`
            [s] time of replacement in case state_of_destruction equals 1.
        """

        input_link_power = self.input_link.power

        # Calculate the Power output or input
        if self.input_link.power >= 0:
            self.calculate_efficiency_output(input_link_power)
            self.calculate_power_output(input_link_power)

        if self.input_link.power < 0:
            self.calculate_efficiency_input(input_link_power)
            self.calculate_power_input(input_link_power)

        # Calculate State of Desctruction
        self.power_component_state_of_destruction()


    def calculate_efficiency_output (self, input_link_power):
        """Calculates power component efficiency, dependent on Power Input eff(P_in).

        Parameters
        ----------
        None : `-`

        Returns
        -------
        efficiency : `float`
            [W] Component efficiency.
        """

        if input_link_power == 0:
            self.efficiency = 0.

        else:
            power_input = min(1, input_link_power / self.power_nominal)
            self.efficiency = -((1 + self.voltage_loss_star) / (2 * self.resistance_loss_star * power_input)) \
                              + (((1 + self.voltage_loss_star)**2 / (2 * self.resistance_loss_star * power_input)**2) \
                              + ((power_input - self.power_self_consumption_star) / (self.resistance_loss_star * power_input**2)))**0.5

            # In case of negative eta it is set to zero
            if self.efficiency < 0:
                self.efficiency = 0


    def calculate_power_output (self, input_link_power):
        """Calculates power component output power, dependent on Power Input P_out(P_in).

        Parameters
        ----------
        None : `-`

        Returns
        -------
        power : `float`
            [W] Component output power in watts.

        """

        if input_link_power == 0:
            self.power_norm = 0.

        else:
            power_input = min(1, input_link_power / self.power_nominal)
            self.power_norm = power_input * self.efficiency

            # no negative power flow as output possible
            # Assumption component goes to stand by mode and self consumption is reduced
            if self.power_norm < 0:
                self.power_norm = 0

        self.power = self.power_norm * self.power_nominal


    def calculate_efficiency_input (self, input_link_power):
        """Calculates power component efficiency, dependent on Power Output eff(P_out).

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
        power_output = (abs(input_link_power) / self.power_nominal)

        self.efficiency = power_output / (power_output + self.power_self_consumption + (power_output * self.voltage_loss) \
                   + (power_output**2 * self.resistance_loss))


    def calculate_power_input (self, input_link_power):
        """Calculates power component input power, dependent on Power Output P_in(P_out).

        Parameters
        ----------
        None : `-`

        Returns
        -------
        power : `float`
            [W] Component input power in watts.

        Note
        ----
        - Calculated power output is NEGATIVE but fuction can only handle Positive value.
        - Therefore first abs(), at the end -
        """

        #power_output = min(1, abs(self.input_link.power) / self.power_nominal)
        power_output = (abs(input_link_power) / self.power_nominal)

        self.power_norm = power_output / self.efficiency
        self.power = - (self.power_norm * self.power_nominal)


    def power_component_state_of_destruction(self):
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
        """

        # Calculate state of desctruction (end_of_life is given in seconds)
        self.state_of_destruction = self.time / (self.end_of_life_power_components/self.timestep)

        if self.state_of_destruction >= 1:
            self.replacement = self.time
            self.state_of_destruction = 0
            self.end_of_life_power_components = self.end_of_life_power_components + self.time
        else:
            self.replacement = 0