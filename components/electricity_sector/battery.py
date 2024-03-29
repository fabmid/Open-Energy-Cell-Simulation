import numpy as np
from simulatable import Simulatable
from serializable import Serializable

class Battery(Serializable, Simulatable):
    """Relevant methods for the calculation of battery performance.

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    capacity_nominal_wh : `int`
        [Wh] Installed battery capacity in watthours.
    environment : `class`
        To get access to solar irradiation, ambient temperature and windspeed.
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Different battery technologies can be modeled with this generic model approach.
    - Model parameter need to be loaded and parametrized externally.
    - self.power represents the dis/charge power, while self.power_battery the stored dis/charge battery.
    """

    def __init__(self,
                 timestep,
                 capacity_nominal_wh,
                 env,
                 file_path = None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for battery model specified')

            self.specification = "lithium_lfp"                                  # [-] Specification of battery
            self.voltage_nominal = 3.2                                          # [V] Nominal battery voltage
            self.state_of_charge_initial = 1.0                                  # [1] Initial battery SoC
            self.power_self_discharge_rate = 3.8072e-09                         # [1/s] Battery self discharge rate, e.g. 1%/monat = 1/(30.4*24*3600)
            self.energy_density_kg = 256.0                                      # [Wh/kg] Batery mass specific energy density
            self.energy_density_m2 = 5843.0                                     # [Wh/m2] Battery surface specific energy density
            self.charge_power_efficiency_a = -0.0224                            # [1] Battery charge efficiency parameter - gradient of linear function
            self.charge_power_efficiency_b = 1.0                                # [1] Battery charge efficiency parameter - intercept of linear function
            self.discharge_power_efficiency_a = -0.0281                         # [1] Battery discharge efficiency parameter - gradient of linear function
            self.discharge_power_efficiency_b = 1.0                             # [1] Battery discharge efficiency parameter - intercept of linear function
            self.end_of_discharge_a = 0.0394                                    # [1] Battery end of discharge parameter - gradient of linear function
            self.end_of_discharge_b = -0.0211                                   # [1] Battery end of discharge parameter - itercept of linear function
            self.end_of_charge_a = -0.0361                                      # [1] Battery end of charge parameter - gradient of linear function
            self.end_of_charge_b = 1.1410                                       # [1] Battery end of charge parameter - itercept of linear function
            self.temperature_operation_min = 233.15                             # [K] Minimal battery temperature
            self.temperature_operation_max: 343.15                              # [K] Maximum battery temperature
            self.heat_transfer_coefficient = 2                                  # [W/m2K] Heat transfer coefficeint battery - environment
            self.heat_capacity = 850                                            # [J/kgK] Battery heat capacity
            self.counter_mc = 0                                                 # [1] Aging model: Initialization counter for
            self.energy_mc = 0                                                  # [Wh] Aging model: Initialization of energy of micro cacle
            self.depth_of_discharge_mc = 0                                      # [1] Aging model: Initialization of depth of discharge of micro cycle
            self.temperature_mc = 0                                             # [1] Aging model: Initialization of temperature of micro cycle
            self.cycle_life_loss = 0                                            # [Wh] Aging model: Initialization capacity loss
            self.cycle_aging_p4 = 0.0                                           # [1] Cycle aging model: polynomial parameter 4th degree
            self.cycle_aging_p3 = -19047.619                                    # [1] Cycle aging model: polynomial parameter 3th degree
            self.cycle_aging_p2 = 47142.8571                                    # [1] Cycle aging model: polynomial parameter 2th degree
            self.cycle_aging_p1 = -43380.9523                                   # [1] Cycle aging model: polynomial parameter 1th degree
            self.cycle_aging_p0 = 17285.7142                                    # [1] Cycle aging model: polynomial parameter 0th degree
            self.cycle_aging_pl0 = 1.0                                          # [1] Cycle aging model: linear temperature function - intersection
            self.cycle_aging_pl1 = 0.0                                          # [1] Cycle aging model: linear temperature function - gradient
            self.calendric_aging_p5 = 0.0                                       # [1] Calendric aging model: polynomial parameter 5th degree
            self.calendric_aging_p3 = 0.0                                       # [1] Calendric aging model: polynomial parameter 3th degree
            self.calendric_aging_p1 = 0.0                                       # [1] Calendric aging model: polynomial parameter 1th degree
            self.calendric_aging_p0 = 0.0                                       # [1] Calendric aging model: polynomial parameter 0th degree
            self.voltage_charge_a = -0.50580                                    # [1] Voltage model: charge case parameter a
            self.voltage_charge_b = -7.92750e-07                                # [1] Voltage model: charge case parameter b
            self.voltage_charge_c = 0.00021                                     # [1] Voltage model: charge case parameter c
            self.voltage_charge_d = 0.73013                                     # [1] Voltage model: charge case parameter d
            self.voltage_charge_e = 0.00079                                     # [1] Voltage model: charge case parameter e
            self.voltage_charge_f = 3.17644                                     # [1] Voltage model: charge case parameter f
            self.voltage_discharge_a = -0.41009                                 # [1] Voltage model: discharge case parameter a
            self.voltage_discharge_b = 2.13015e-06                              # [1] Voltage model: discharge case parameter b
            self.voltage_discharge_c = -0.00013                                 # [1] Voltage model: discharge case parameter c
            self.voltage_discharge_d = 0.69962                                  # [1] Voltage model: discharge case parameter d
            self.voltage_discharge_e = -0.00161                                 # [1] Voltage model: discharge case parameter e
            self.voltage_discharge_f = 3.03234                                  # [1] Voltage model: discharge case parameter f
            self.end_of_life_condition = 0.8                                    # [1] Batter end of life condition with 80% of initial capacity
            self.investment_costs_specific = 0.21175                            # [$/Wh] Battery specific investment costs
            self.operation_maintenance_costs_share = 0.05                       # [1] Share of omc costs of cc
            
        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # Integrate environment class
        self.env = env
        # [s] Timestep
        self.timestep = timestep

        ##Basic parameters for EMS
        self.input_link_power = 0
        self.power = 0
        
        ##Power model
        # [Wh] Battery nominal capacity at nominal C-Rate
        self.capacity_nominal_wh = capacity_nominal_wh
        # [Wh] Current battery nominal capacity at nominal C-Rate
        self.capacity_current_wh = capacity_nominal_wh


        ## Temperature model
        # [kg] Mass of the battery
        self.mass =  self.capacity_nominal_wh / self.energy_density_kg
        # [m^2] Battery area
        self.surface = self.capacity_nominal_wh / self.energy_density_m2

        # Initialize initial parameters
        self.state_of_charge = self.state_of_charge_initial
        self.temperature = 298.15
        self.power_loss = 0.

        ## Aging model
        # [Wh] End-of-Life condition of battery
        self.end_of_life_battery_wh = self.end_of_life_condition * self.capacity_nominal_wh

        ## Economic model
        # [Wh] Nominal capacity
        self.size_nominal = self.capacity_nominal_wh
        # [$/Wh] Storage specific investment costs
        self.investment_costs_specific = self.investment_costs_specific
        # [$/W] Electrolyzer specific operation and maintenance cost
        self.operation_maintenance_costs_specific = self.operation_maintenance_costs_share \
                                                    * self.investment_costs_specific



    def calculate(self):
        """Simulatable method.
        Calculation is done inside energy management of electricty carrier.
        """        
        pass
                
    def get_temperature(self):
        """Calculates the battery temperature in Kelvin.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        temperature : `float`
            [K] Battery temperature in Kelvin.

        Note
        ----
        - Thermal model is based on general heat blalance and convetcive heat
        transport to the environment.
        - Compare heat balance by [1]_.

        .. [1] Bernardi, E. Pawlikowski, and J. Newman, ‘A General Energy Balance \
        for Battery Systems’, J. Electrochem. Soc., vol. 132, no. 1, p. 5, 1985.
        """

        #Battery temperature
        self.temperature = self.temperature + ((np.abs(self.power_loss) - \
                           self.heat_transfer_coefficient * self.surface * \
                           (self.temperature -  self.env.temperature_ambient[self.time])) / \
                           (self.heat_capacity * self.mass / self.timestep))


    def get_power(self):
        """Calculates the battery efficiency & charging/discharging power in Watt.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        power : `float`
            [W] Battery charge/discharge power extracted from the battery.
        efficiency : `float`
            [1] Battery charge/discharge efficiency.

        Note
        ----
        - The model describes a power-dependent efficiency.
        - For a detailed description of the parametrization approach [2].

        .. [2] Schmid et al. "An open-source modeling tool for multi-objective \
        optimization of renewable nano/micro-off-grid power supply system", Energy, 2020
        """

        #ohmic losses for charge or discharge
        if self.power > 0.: #charge
            self.efficiency = self.charge_power_efficiency_a * (self.power/self.capacity_nominal_wh) + self.charge_power_efficiency_b
            self.power_battery = self.power * self.efficiency

        elif self.power == 0.: #idle
            self.efficiency = 0
            self.power_battery = self.power * self.efficiency

        elif self.power < 0.: #discharge
            self.efficiency = self.discharge_power_efficiency_a*(abs(self.power)/self.capacity_nominal_wh) + self.discharge_power_efficiency_b
            self.power_battery = self.power / self.efficiency

        #Calculation of battery power loss
        self.power_loss = self.power - self.power_battery


    def get_state_of_charge(self):
        """Calculates the battery state of charge.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        state_of_charge : `float`
            [1] Battery state of charge.

        Note
        ----
        - Model is based on simple energy balance using an off-line book-keeping method.
        - Considers charge/discharge terminal power, power losses, self-discharge rate.
        - For a detailed description of the model [2]_.
        """

        # save soc of last timestep
        self.state_of_charge_old = self.state_of_charge

        #caculate soc of current timestep
        self.state_of_charge = self.state_of_charge \
                               + (self.power / (self.capacity_current_wh) * (self.timestep/3600)) \
                               - (self.power_self_discharge_rate * self.timestep)
        self.state_of_charge = self.state_of_charge



    def get_charge_discharge_boundary(self):
        """Calculates battery charge/discharge boundaries.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        charge_discharge_boundary : `float`
            [1] Battery charge/discharge boundary.

        Note
        ----
        - The model describes the power-dependent charge and discharge boundaries.
        - For a detailed description of the parametrization approach [2].
        """

        #Discharge
        if self.power < 0.:
            self.charge_discharge_boundary = self.end_of_discharge_a * (abs(self.power_battery)/self.capacity_nominal_wh) + self.end_of_discharge_b

        #Charge
        else:
            self.charge_discharge_boundary = self.end_of_charge_a * (self.power_battery/self.capacity_nominal_wh) + self.end_of_charge_b


    def get_voltage(self):
        """Calculates battery voltage dependent on battery power and State of charge.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        voltage : `float`
            [V] Battery voltage level.

        Note
        ----
        - The model describes the voltage dependent on charge/discharge power and state of charge.
        """

        # Charge case
        if self.power_battery > 0:
            self.voltage = self.voltage_charge_a * self.state_of_charge**2 \
                          + self.voltage_charge_b * self.power_battery**2 \
                          + self.voltage_charge_c * self.state_of_charge * self.power_battery \
                          + self.voltage_charge_d * self.state_of_charge \
                          + self.voltage_charge_e * self.power_battery \
                          + self.voltage_charge_f
        # Discharge case
        if self.power_battery < 0:
            self.voltage = self.voltage_discharge_a * self.state_of_charge**2 \
                          + self.voltage_discharge_b * abs(self.power_battery)**2 \
                          + self.voltage_discharge_c * self.state_of_charge * abs(self.power_battery) \
                          + self.voltage_discharge_d * self.state_of_charge \
                          + self.voltage_discharge_e * abs(self.power_battery) \
                          + self.voltage_discharge_f

        # No Power case: voltage stays constant
        if self.power_battery == 0:
            self.voltage = self.voltage



    def get_state_of_destruction(self):
        """Calculates the battery state of destruction (SoD) and time of
        component replacement according to end of life criteria.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        state_of_destruction : `float`
            [1] Battery State of destruction with SoD=1 representing a broken component.
        replacement : `int`
            [s] Time of battery component replacement in seconds.

        Note
        ----
        - Replacement time is only set in timeseries array in case of a replacement, otherwise entry is 0.
        - In case of replacement current_peak_power is reset to nominal power.
        """

        # Calculate State of Destruction
        self.state_of_destruction = (self.capacity_nominal_wh - self.capacity_current_wh) / (self.capacity_nominal_wh - self.end_of_life_battery_wh)

        if self.state_of_destruction >= 1:
            self.replacement = self.time
            self.state_of_destruction = 0
            self.capacity_current_wh = self.capacity_nominal_wh
        else:
            self.replacement = 0


    def get_aging_calendar(self):
        """Calculates battery calendar aging according to specified float lifetime.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        float_life : `float`
            [a] Battery float lifetime according to battery temperature.
        float_life_loss : `float`
            [Wh] Battery absolute capacity loss per timestep due to calendar aging.

        Note
        ----
        - Model is based on numerical fitting of float lifetime data given in battery datasheet.
        - For detailed description of model parametrization, compare [3]_.

        References
        ----------
        .. [3] F.Schmid, F.Behrendt "Optimal Sizing of Solar Home Systems:
            Charge Controller Technology and Its Influence on System Design" Under development.
        """

        # Float life at battery temperature
        self.float_life = self.calendric_aging_p5*(self.temperature)**5 + self.calendric_aging_p3*(self.temperature)**3 \
                        + self.calendric_aging_p1*(self.temperature) + self.calendric_aging_p0

        # Check if calendaric model is implemented
        if self.float_life != 0:
            # Float life loss in Wh
            self.float_life_loss = ((self.capacity_nominal_wh-self.end_of_life_battery_wh) / (self.float_life*365*24*(3600/self.timestep)))
        else:
            # Float life loss in Wh
            self.float_life_loss = 0.


    def get_aging_cycling(self):
        """Calculates battery cycling aging according to micro cycle approach.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        cycle_life : `float`
            [a] Battery cycle lifetime according to last micro cycle.
        cycle_life_loss : `float`
            [Wh] Battery absolute capacity loss per timestep due to cycling aging.

        Note
        ----
        - Cycle life dependent on DoD and temperature if specified
        - The model is described in detailed in [4]_ and [5]_.

        .. [4] Narayan et al. "A simple methodology for estimating battery
            lifetimes in Solar Home System design", IEEE Africon 2017 Proceedings, 2017.
        .. [5] Narayan et al. "Estimating battery lifetimes in Solar Home System design using a practical
            modelling methodology, Applied Energy 228, 2018.
        """

        # Micro cycle is running
        if self.power_battery != 0:
            # Add up energy, counter, DoD amnd temperature of micro cycle
            self.energy_mc += abs(self.power_battery*(self.timestep/3600))
            self.counter_mc += 1
            # Get current dod calculated with maximum SoC possible at P=0 and current SoC
            self.depth_of_discharge_mc += (self.end_of_charge_b - self.state_of_charge)
            self.temperature_mc += (self.temperature)

            # During micro cycle cycle_life/_mc is still 0
            self.cycle_life_mc = 0
            self.cycle_life = 0

        # Micro cycle is ending (in case of no power flow)
        else:
            self.cycle_life_mc = 0
            self.cycle_life = 0
            self.cycle_life_rel_loss = 0
            self.cycle_life_loss = 0

            # Evaluate micro cycle cycle_life/_mc and cycle_life_loss
            if self.counter_mc != 0:
                # Calculate mean value of DoD and temperature
                self.depth_of_discharge_mc_mean = (self.depth_of_discharge_mc/self.counter_mc)
                self.temperature_mc_mean = (self.temperature_mc/self.counter_mc)

                # Calculate cycle_life/_mc/_loss for micro cycle evaluation
                self.cycle_life_mc = self.energy_mc / (2*self.capacity_nominal_wh*self.depth_of_discharge_mc_mean)

                self.cycle_life = (self.cycle_aging_p4*self.depth_of_discharge_mc_mean**4 + self.cycle_aging_p3*self.depth_of_discharge_mc_mean**3 \
                                   + self.cycle_aging_p2*self.depth_of_discharge_mc_mean**2 + self.cycle_aging_p1*self.depth_of_discharge_mc_mean + self.cycle_aging_p0) \
                                   * ((self.cycle_aging_pl1*self.temperature_mc_mean) + self.cycle_aging_pl0)

                self.cycle_life_rel_loss = (self.cycle_life_mc / self.cycle_life)
                self.cycle_life_loss = (self.cycle_life_rel_loss * (self.capacity_nominal_wh-self.end_of_life_battery_wh))

            # Reset parameter to initial values
            self.counter_mc = 0
            self.energy_mc = 0
            self.depth_of_discharge_mc = 0
            self.temperature_mc = 0
