import pyomo.environ as pyo
import numpy as np

import data_loader
from simulatable import Simulatable
from serializable import Serializable
from optimizable import Optimizable

class Battery(Serializable, Simulatable, Optimizable):
    """Relevant methods for the calculation of battery performance.

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    capacity_nominal_kwh : `int`
        [kWh] Installed battery capacity in kilo-watt-hours.
    environment : `class`
        To get access to solar irradiation, ambient temperature and windspeed.
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Different battery technologies can be modeled with this generic model approach.
    - Model parameter need to be loaded and parametrized externally.
    - self.power_list represents the dis/charge power at the battery terminals (output of optimization)
        - Charging power is defined positive, discharge power negative!
        - while self.power_cell the stored dis/charge battery power at cell level (output of simulation).
    """

    def __init__(self,
                 timestep,
                 capacity_nominal_kwh,
                 env,
                 file_path = None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for battery model specified')

            self.specification = "lithium_lfp"                                  # [-] Specification of battery

            self.state_of_charge_balanced = "True"                              # Optimization: True:SoC(start)=SoC(end)
            self.state_of_charge_initial = 1.0                                  # Optimization: [1] Initial battery SoC
            self.c_rate_max = 3                                                 # Optimization: [1] Maxium charge/discharge c-Rate
            self.end_of_discharge = 0.1                                         # Optimization: [1] Battery constant end of discharge parameter (linear model)
            self.end_of_charge = 1.0                                            # Optimization: [1] Battery constant end of charge parameter (linear model)
            self.power_efficiency = 0.95                                        # Optimization: [1] Battery static ch/dch efficeincy (linear model)
            self.performance_piecewise = "True"                                 # Optimization: PWA representation of performance curve
            self.performance_piecewise_method = 'CC'                            # Optimization: PWA method used
            self.pwa_alpha_ch = [0.98515, 0.96758, 0.94861, 0.92841]            # Optimization: PWA slopes charge case for each segment
            self.pwa_beta_ch = [-0.00132, 0.00342, 0.01336, 0.02886]            # Optimization: PWA y-intercept charge case for each segment
            self.pwa_alpha_dch = [0.98592, 0.96449, 0.94326, 0.92222]           # Optimization: PWA slopes charge discase for each segment
            self.pwa_beta_dch = [-0.00157, 0.00376, 0.01433, 0.03006]           # Optimization: PWA y-intercept charge discase for each segment
            self.power_ch_norm_min = 0.00134                                    # Optimization: PWA first breakpoint, equals minimal partload of battery charge case
            self.power_dch_norm_min = 0.00160                                   # Optimization: PWA first breakpoint, equals minimal partload of battery discharge case
            self.power_norm_max = 1.0                                           # Optimization: PWA maximal partload of battery for charge and discharge case
            self.pwa_efficiency_ref = 0.95228                                   # Optimization: PWA reference efficeincy in discharge case at last breakpoint (nominal power)
            self.self_discharge_rate = 3.8072e-09                               # Optimization/Simulation [1/s] Battery self discharge rate, e.g. 1%/monat = 0.01/(30.4*24*3600)
            self.charge_power_efficiency_a = -0.0224                            # Simulation: [1] Battery CELL charge efficiency parameter - gradient of linear function
            self.charge_power_efficiency_b = 1.0                                # Simulation: [1] Battery CELL charge efficiency parameter - intercept of linear function
            self.discharge_power_efficiency_a = -0.0281                         # Simulation: [1] Battery CELL discharge efficiency parameter - gradient of linear function
            self.discharge_power_efficiency_b = 1.0                             # Simulation: [1] Battery CELL discharge efficiency parameter - intercept of linear function
            self.end_of_discharge_a = 0.0394                                    # Simulation: [1] Battery end of discharge parameter - gradient of linear function
            self.end_of_discharge_b = -0.0211                                   # Simulation: [1] Battery end of discharge parameter - itercept of linear function
            self.end_of_charge_a = -0.0361                                      # Simulation: [1] Battery end of charge parameter - gradient of linear function
            self.end_of_charge_b = 1.1410                                       # Simulation: [1] Battery end of charge parameter - itercept of linear function
            self.end_of_life_condition = 0.8                                    # Aging model: [1] Batter end of life condition with 80% of initial capacity
            self.counter_mc = 0                                                 # Aging model: [1] Initialization counter for
            self.energy_mc = 0                                                  # Aging model: [Wh] Initialization of energy of micro cacle
            self.depth_of_discharge_mc = 0                                      # Aging model: [1] Initialization of depth of discharge of micro cycle
            self.temperature_mc = 0                                             # Aging model: [1] Initialization of temperature of micro cycle
            self.cycle_life_loss = 0                                            # Aging model: [Wh] Initialization capacity loss
            self.cycle_aging_p4 = 0.0                                           # Cycle aging model: [1] polynomial parameter 4th degree
            self.cycle_aging_p3 = -19047.619                                    # Cycle aging model: [1] polynomial parameter 3th degree
            self.cycle_aging_p2 = 47142.8571                                    # Cycle aging model: [1] polynomial parameter 2th degree
            self.cycle_aging_p1 = -43380.9523                                   # Cycle aging model: [1] polynomial parameter 1th degree
            self.cycle_aging_p0 = 17285.7142                                    # Cycle aging model: [1] polynomial parameter 0th degree
            self.cycle_aging_pl0 = 1.0                                          # Cycle aging model: [1] linear temperature function - intersection
            self.cycle_aging_pl1 = 0.0                                          # Cycle aging model: [1] linear temperature function - gradient
            self.calendric_aging_p5 = 0.0                                       # Calendric aging model: [1] polynomial parameter 5th degree
            self.calendric_aging_p3 = 0.0                                       # Calendric aging model: [1] polynomial parameter 3th degree
            self.calendric_aging_p1 = 0.0                                       # Calendric aging model: [1] polynomial parameter 1th degree
            self.calendric_aging_p0 = 0.0                                       # Calendric aging model: [1] polynomial parameter 0th degree
            self.heat_transfer_coefficient = 2                                  # Temperature model: [W/m2K] Heat transfer coefficeint battery - environment
            self.heat_capacity = 850                                            # Temperature model: [J/kgK] Battery heat capacity
            self.energy_density_kg = 0.256                                      # Temperature model: [kWh/kg] Batery mass specific energy density
            self.energy_density_m2 = 5.843                                      # Temperature model: [kWh/m2] Battery surface specific energy density
            self.capex_p1 = 0.0                                                 # [€$/kWh] capex: Parameter1 (gradient) for specific capex definition
            self.capex_p2 = 200.0                                               # [€$/kWh] capex: Parameter2 (y-intercept) for specific capex definition
            self.subsidy_percentage_capex = 0.19                                # Economic model: [%] Capex subsidy
            self.subsidy_limit = 1000000.0                                      # Economic model: [€/$] Max total capex subsidy
            self.opex_fix_p1 = 0.0                                              # [€$/kWh/a] opex-fixed: % of capex
            self.opex_var = 0.0                                                 # [€$/kWh] opex-variable: Specific variable opex dependent on energy


        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)

        # Integrate environment class
        self.env = env
        # [s] Timestep
        self.timestep = timestep

        ## Power model
        # [kWh] Battery nominal capacity at nominal C-Rate
        self.capacity_nominal_kwh = capacity_nominal_kwh
        # [kWh] Current battery nominal capacity at nominal C-Rate
        self.capacity_current_kwh = capacity_nominal_kwh
        # [kW] Nomnial power ch/dch (equals maximum power ch and dch)
        self.power_nominal = self.capacity_current_kwh * self.c_rate_max

        ## Temperature model
        # [kg] Mass of the battery
        self.mass =  self.capacity_nominal_kwh / self.energy_density_kg
        # [m^2] Battery area
        self.surface = self.capacity_nominal_kwh / self.energy_density_m2

        ## Aging model
        # [kWh] End-of-Life condition of battery
        self.end_of_life_battery_kwh = self.end_of_life_condition * self.capacity_nominal_kwh

        ## Economic model
        # [kWh] Initialize Nominal capacity
        self.size_nominal = self.capacity_nominal_kwh
        # Calculate specific costs if capacity is not 0
        if self.capacity_nominal_kwh != 0:
            # [€$/kWh] Initialize specific capex
            self.capex_specific = (self.capex_p1 * self.size_nominal**self.capex_p2)
            # [€$/kWh] Initialize specific fixed opex
            self.opex_fix_specific = (self.opex_fix_p1 * self.capex_specific)
        else:
            self.capex_specific = 0
            self.opex_fix_specific = 0

        # Integrate opex_var profile loader
        self.opex_var_cost = data_loader.StorageOpexCost()


    def simulation_init(self):
        """Simulatable method.
        Initialize list containers to store simulation results.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`
        """
        
        ## List container to store simulation results for all timesteps
        self.power_loss_list = list()
        self.temperature_list = list()
        self.capacity_loss_kwh_list = list()
        self.capacity_current_kwh_list = list()
        self.state_of_destruction_list = list()
        self.replacement_list = list()

        # Initialize values
        self.temperature = 298.25


    def simulation_calculate(self):
        """Simulatable method.
        Extract optimized battery operation parameters and stores it in list containers.
        Further computes aging of battery component.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
            - Power loss values are newly calculated with cell efficiency parameters in order to consider only ohmic cell losses for temperature model (no inverter losses).
        """

        ## Get optimized values
        # Power values (with ch+ and dch-)
        self.power = self.power_list[self.time]
        # State of charge
        self.state_of_charge = self.state_of_charge_list[self.time]

        ## Calculate power loss
        self.get_power()
        ## Calculate temperature
        self.get_temperature()

        ## Battery Aging
        #self.power_cell_lst.append(self.power_cell)
        # Cycling Aging
        if self.power_cell != 0.:
            # Call cycling aging method to evaluate timestep of micro cycle
            self.get_aging_cycling()

            # Capacity loss is 0, as micro cycle is running, values are set to 0 for continious array creation in simulation
            self.capacity_loss_kwh = 0
            self.float_life_loss = 0
            self.cycle_life_loss = 0

        # Calendric Aging and micro cycle evaluation
        else:
            # Call calendric aging method
            self.get_aging_calendar()
            # Call cycling aging method
            self.get_aging_cycling()
            # Capacity loss due to cycling of finished micro cycle AND calendaric aging
            self.capacity_loss_kwh = self.cycle_life_loss + self.float_life_loss

        # Current battery capacity with absolute capacity loss per timestep
        self.capacity_current_kwh = self.capacity_current_kwh - self.capacity_loss_kwh
        self.state_of_health = self.capacity_current_kwh / self.capacity_nominal_kwh

        # Current State of Destruction
        self.get_state_of_destruction()

        ## Save component status variables for all timesteps to list
        self.power_loss_list.append(self.power_loss)
        self.temperature_list.append(self.temperature)
        self.capacity_loss_kwh_list.append(self.capacity_loss_kwh)
        self.capacity_current_kwh_list.append(self.capacity_current_kwh)
        self.state_of_destruction_list.append(self.state_of_destruction)
        self.replacement_list.append(self.replacement)


    def optimization_get_block(self, model):
        """
        Pyomo: MILP Battery block construction

        Parameters
        ----------
        model : pyomo.model class instance (defined in optimizabe.py)

        Returns
        -------
        None : `None`
        """

        # Central pyomo model
        self.model = model

        ## Battery block
        self.model.blk_battery = pyo.Block()

        # In case capacity is NOT 0, normal calculation
        if self.capacity_nominal_kwh != 0:

            # Define parameters
            self.model.blk_battery.capacity = pyo.Param(initialize=self.capacity_current_kwh)
            self.model.blk_battery.power_nominal = pyo.Param(initialize=self.power_nominal)
            self.model.blk_battery.end_of_charge = pyo.Param(initialize=self.end_of_charge)
            self.model.blk_battery.end_of_discharge = pyo.Param(initialize=self.end_of_discharge)
            self.model.blk_battery.self_discharge_rate = pyo.Param(initialize=self.self_discharge_rate)
            self.model.blk_battery.state_of_charge_initial = pyo.Param(initialize=self.state_of_charge_initial)

            # Variable opex (only relevant for obj fct considering storage opex_var)
            if self.opex_var == 'dynamic_tariff':
                print('Battery dynamic opex_var')
                self.opex_var_cost.read_csv(file_name=self.file_path_opex_var,
                                            simulation_steps=len(self.model.timeindex))
                self.opex_var = self.opex_var_cost.get_storage_opex_var_profile()
                # Define pyomo parameter
                self.model.blk_battery.opex_var = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.opex_var))

            elif isinstance(self.opex_var, (int, float)):
                self.opex_var = [self.opex_var] * len(self.model.timeindex)
                # Define pyomo parameter
                self.model.blk_battery.opex_var =pyo.Param(self.model.timeindex, initialize=self.data_prep(self.opex_var))

                    # Define variables
            self.model.blk_battery.power_ch = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)                           # battery charging power (AC electricity side)
            self.model.blk_battery.power_dch = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)                          # battery discharging power (AC electricity side)
            self.model.blk_battery.state_of_charge = pyo.Var(self.model.timeindex, bounds=(self.model.blk_battery.end_of_discharge,
                                                                                           self.model.blk_battery.end_of_charge))  # battery soc with end of ch/DCH levels

            ## Piecewise representation of battery CH and DCH performance
            if self.performance_piecewise == "True":
                # Defina parameter
                self.model.blk_battery.power_ch_norm_min = pyo.Param(initialize=self.power_ch_norm_min)
                self.model.blk_battery.power_dch_norm_min = pyo.Param(initialize=self.power_dch_norm_min)
                self.model.blk_battery.power_norm_max = pyo.Param(initialize=self.power_norm_max)

                # Define variables (only necessary for PWA representation)
                self.model.blk_battery.on_off_ch = pyo.Var(self.model.timeindex, domain=pyo.Binary)                             # ch: On/off status of component: 0=off and 1=on
                self.model.blk_battery.on_off_dch = pyo.Var(self.model.timeindex, domain=pyo.Binary)                            # dch: On/off status of component: 0=off and 1=on

                self.model.blk_battery.power_nominal_ch_aux = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)        # ch: Auxiliary variable of nominal power
                self.model.blk_battery.power_nominal_dch_aux = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)       # dch: Auxiliary variable of nominal power
                self.model.blk_battery.power_ch_cell = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)               # battery charging power (Cell side)
                self.model.blk_battery.power_dch_cell = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)              # battery discharging power (Cell side)

                ## Charge case
                # Define Constraints
                # Power aux constraint
                def pwa_power_ch_aux_rule(_b, t):
                    return (_b.power_nominal_ch_aux[t] == _b.on_off_ch[t] * _b.power_nominal)
                self.model.blk_battery.pwa_power_ch_aux_c = pyo.Constraint(self.model.timeindex, rule=pwa_power_ch_aux_rule)

                # Min and Max operation range constraint
                def pwa_max_power_ch_operation_rule(_b, t):
                    return (_b.power_ch[t] <= _b.power_norm_max * _b.power_nominal_ch_aux[t])
                self.model.blk_battery.pwa_max_power_ch_op_c = pyo.Constraint(self.model.timeindex, rule=pwa_max_power_ch_operation_rule)

                def pwa_min_power_ch_operation_rule(_b, t):
                    return (_b.power_ch[t] >= _b.power_ch_norm_min * _b.power_nominal_ch_aux[t])
                self.model.blk_battery.pwa_min_power_ch_op_c = pyo.Constraint(self.model.timeindex, rule=pwa_min_power_ch_operation_rule)

                # PWA constraints for each line segment
                # Iterate over all line segments and create constraint
                for segment in range(0,4):
                    # Define constraint rule
                    def pwa_ch_constraint(_b, t):
                        return ((_b.power_ch_cell[t] <= self.pwa_alpha_ch[segment] * _b.power_ch[t] + self.pwa_beta_ch[segment] * _b.power_nominal_ch_aux[t]))

                    setattr(self.model.blk_battery, f"Constraint_PWA_ch_segment_{segment}", pyo.Constraint(self.model.timeindex, rule=pwa_ch_constraint))

                ## Discharge case
                # Define Constraints
                # Power aux constraint
                def pwa_power_dch_aux_rule(_b, t):
                    return (_b.power_nominal_dch_aux[t] == _b.on_off_dch[t] * _b.power_nominal)
                self.model.blk_battery.pwa_power_dch_aux_c = pyo.Constraint(self.model.timeindex, rule=pwa_power_dch_aux_rule)

                # Min and Max operation range constraint
                def pwa_max_power_dch_operation_rule(_b, t):
                    return (_b.power_dch[t] <= _b.power_norm_max * _b.power_nominal_dch_aux[t])
                self.model.blk_battery.pwa_max_power_dch_op_c = pyo.Constraint(self.model.timeindex, rule=pwa_max_power_dch_operation_rule)

                def pwa_min_power_dch_operation_rule(_b, t):
                    return (_b.power_dch[t] >= _b.power_dch_norm_min * _b.power_nominal_dch_aux[t])
                self.model.blk_battery.pwa_min_power_dch_op_c = pyo.Constraint(self.model.timeindex, rule=pwa_min_power_dch_operation_rule)

                # PWA constraints for each line segment
                # Iterate over all line segments and create constraint
                for segment in range(0,4):
                    # Define constraint rule
                    def pwa_dch_constraint(_b, t):
                        return ((_b.power_dch[t] <= self.pwa_alpha_dch[segment] * _b.power_dch_cell[t] + self.pwa_beta_dch[segment] * (_b.power_nominal_dch_aux[t]/self.pwa_efficiency_ref)))

                    setattr(self.model.blk_battery, f"Constraint_PWA_dch_segment_{segment}", pyo.Constraint(self.model.timeindex, rule=pwa_dch_constraint))


                ## Additional constraint to hinder parallel ch and dch operation
                def pwa_parallel_op_rule(_b, t):
                    return ((_b.on_off_ch[t] + _b.on_off_dch[t]) <= 1)
                self.model.blk_battery.pwa_parallel_operation_c = pyo.Constraint(self.model.timeindex, rule=pwa_parallel_op_rule)


                # SoC constraint
                def state_of_charge_rule(_b, t):
                    if t == self.model.timeindex.first():
                        return (_b.state_of_charge[t] == _b.state_of_charge_initial
                                + (((_b.power_ch_cell[t] - _b.power_dch_cell[t])
                                / _b.capacity) * (self.timestep/3600))
                                - (_b.self_discharge_rate *self.timestep))

                    return (_b.state_of_charge[t] == _b.state_of_charge[t-1]
                            + (((_b.power_ch_cell[t] - _b.power_dch_cell[t])
                            / _b.capacity) * (self.timestep/3600))
                            - (_b.self_discharge_rate *self.timestep))
                self.model.blk_battery.state_of_charge_c = pyo.Constraint(self.model.timeindex, rule=state_of_charge_rule)


            ## Static representation of battery performance
            elif self.performance_piecewise == "False":

                # Define parameters
                self.model.blk_battery.efficiency = pyo.Param(initialize=self.power_efficiency)
                # Define variables
                self.model.blk_battery.ch_dch = pyo.Var(self.model.timeindex, domain=pyo.Binary)                                       # if ch-->0, if dch-->1 (needed that storage can only be charged or discharged but not both simultaniously)

                # Battery SoC constraint
                def state_of_charge_rule(_b, t):
                    if t == self.model.timeindex.first():
                        return (_b.state_of_charge[t] == _b.state_of_charge_initial
                                + ((((_b.power_ch[t]*_b.efficiency) - (_b.power_dch[t]/_b.efficiency)) / _b.capacity) * (self.timestep/3600))
                                - (_b.self_discharge_rate *self.timestep))

                    return (_b.state_of_charge[t] == _b.state_of_charge[t-1]
                            + ((((_b.power_ch[t]*_b.efficiency) - (_b.power_dch[t]/_b.efficiency)) / _b.capacity) * (self.timestep/3600))
                            - (_b.self_discharge_rate *self.timestep))
                self.model.blk_battery.state_of_charge_c = pyo.Constraint(self.model.timeindex, rule=state_of_charge_rule)


                # Battery power CH max constraint
                def power_ch_max_rule(_b, t):
                    return (_b.power_ch[t] + _b.ch_dch[t] * _b.power_nominal <= _b.power_nominal)
                self.model.blk_battery.power_ch_max_c = pyo.Constraint(self.model.timeindex, rule=power_ch_max_rule)

                # Battery power DCH max constraint
                def power_dch_max_rule(_b, t):
                    return (_b.power_dch[t] - _b.ch_dch[t] * _b.power_nominal <= 0)
                self.model.blk_battery.power_dch_max_c = pyo.Constraint(self.model.timeindex, rule=power_dch_max_rule)

            else:
                print('Error Battery pyomo model: Define battery parameter "performance_piecewise" correctly!')


            # Constraint is only set in case first and last SoC level should be the same. Storage is balanced over simulation timeframe.
            if self.state_of_charge_balanced == "True":
                # Set the overall (of all optimized timesteps) first SoC to the overall last SoC
                def soc_last_initial_rule(_b, t):
                    if t == self.model.timeindex.last():
                        return (_b.state_of_charge[t] == _b.state_of_charge_initial)
                    else:
                        return pyo.Constraint.Skip
                self.model.blk_battery.soc_last_initial_c = pyo.Constraint(self.model.timeindex, rule=soc_last_initial_rule)

        # Incase battery capacity  is 0 - no variables - only params=0!
        else:
            self.model.blk_battery.power_ch = pyo.Param(self.model.timeindex, initialize=0)               # battery charging power (AC electricity side)
            self.model.blk_battery.power_dch = pyo.Param(self.model.timeindex, initialize=0)              # battery discharging power (AC electricity side)
            self.model.blk_battery.state_of_charge = pyo.Param(self.model.timeindex, initialize=0)        # battery soc with end of ch/DCH levels
            # Variables of PWA performance
            if self.performance_piecewise == 'True':
                self.on_off_ch_list = pyo.Param(self.model.timeindex, initialize=0)
                self.on_off_dch_list = pyo.Param(self.model.timeindex, initialize=0)
                self.power_nominal_ch_aux_list = pyo.Param(self.model.timeindex, initialize=0)
                self.power_nominal_dch_aux_list = pyo.Param(self.model.timeindex, initialize=0)
                self.power_ch_cell_list = pyo.Param(self.model.timeindex, initialize=0)
                self.power_dch_cell_list = pyo.Param(self.model.timeindex, initialize=0)


    def optimization_save_results(self):
        """
        Method to store optimization results

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`
        """
        
        ## Access of results
        #self.ch_dch_list = list(self.model.blk_battery.ch_dch.extract_values().values())
        self.power_ch_list = list(self.model.blk_battery.power_ch.extract_values().values())
        self.power_dch_list = list(self.model.blk_battery.power_dch.extract_values().values())
        self.state_of_charge_list = list(self.model.blk_battery.state_of_charge.extract_values().values())

        # Variables of PWA performance
        if self.performance_piecewise == 'True':
            self.on_off_ch_list = list(self.model.blk_battery.on_off_ch.extract_values().values())
            self.on_off_dch_list = list(self.model.blk_battery.on_off_dch.extract_values().values())
            self.power_nominal_ch_aux_list = list(self.model.blk_battery.power_nominal_ch_aux.extract_values().values())
            self.power_nominal_dch_aux_list = list(self.model.blk_battery.power_nominal_dch_aux.extract_values().values())
            self.power_ch_cell_list = list(self.model.blk_battery.power_ch_cell.extract_values().values())
            self.power_dch_cell_list = list(self.model.blk_battery.power_dch_cell.extract_values().values())

        ## Transfer opti results to sim sign convention
        self.power_list = list(np.array(self.power_ch_list) - np.array(self.power_dch_list))


    def get_temperature(self):
        """Calculate the battery temperature in Kelvin.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

        Note
        ----
        - Thermal model is based on general heat blalance and convetcive heat
        transport to the environment.
        - Compare heat balance by [1]_.

        .. [1] Bernardi, E. Pawlikowski, and J. Newman, ‘A General Energy Balance \
        for Battery Systems’, J. Electrochem. Soc., vol. 132, no. 1, p. 5, 1985.
        """

        # Battery temperature
        self.temperature = self.temperature + ((np.abs(self.power_loss) - \
                           self.heat_transfer_coefficient * self.surface * \
                           (self.temperature -  self.env.temperature_ambient[self.time])) / \
                           (self.heat_capacity * self.mass / self.timestep))


    def get_power(self):
        """Calculate the battery efficiency & charging/discharging power in kilo-Watt.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

        Note
        ----
        - The model describes a power-dependent efficiency.
        - For a detailed description of the parametrization approach [2].

        .. [2] Schmid et al. "An open-source modeling tool for multi-objective \
        optimization of renewable nano/micro-off-grid power supply system", Energy, 2020
        """

        # Ohmic losses for charge or discharge
        if self.power > 0.: #charge
            self.efficiency = self.charge_power_efficiency_a * (self.power/self.capacity_nominal_kwh) + self.charge_power_efficiency_b
            self.power_cell = self.power * self.efficiency

        elif self.power == 0.: #idle
            self.efficiency = 0
            self.power_cell = self.power * self.efficiency

        elif self.power < 0.: #discharge
            self.efficiency = self.discharge_power_efficiency_a*(abs(self.power)/self.capacity_nominal_kwh) + self.discharge_power_efficiency_b
            self.power_cell = self.power / self.efficiency

        # Calculation of battery power loss
        self.power_loss = self.power - self.power_cell


    def get_state_of_charge(self):
        """Calculate the battery state of charge.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

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
                               + (self.power / (self.capacity_current_kwh) * (self.timestep/3600)) \
                               - (self.self_discharge_rate * self.timestep)
        self.state_of_charge = self.state_of_charge



    def get_charge_discharge_boundary(self):
        """Calculats battery charge/discharge boundaries.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

        Note
        ----
        - The model describes the power-dependent charge and discharge boundaries.
        - For a detailed description of the parametrization approach [2].
        """
        if self.linear == 'True':
            #Discharge
            if self.power < 0.:
                self.charge_discharge_boundary = self.end_of_discharge_constant

            #Charge
            else:
                self.charge_discharge_boundary = self.end_of_charge_constant

        else:
            #Discharge
            if self.power < 0.:
                self.charge_discharge_boundary = self.end_of_discharge_a * (abs(self.power_cell)/self.capacity_nominal_kwh) + self.end_of_discharge_b

            #Charge
            else:
                self.charge_discharge_boundary = self.end_of_charge_a * (self.power_cell/self.capacity_nominal_kwh) + self.end_of_charge_b


    def get_state_of_destruction(self):
        """Calculate the battery state of destruction (SoD) and time of
        component replacement according to end of life criteria.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

        Note
        ----
        - Replacement time is only set in timeseries array in case of a replacement, otherwise entry is 0.
        - In case of replacement current_peak_power is reset to nominal power.
        """

        # Calculate State of Destruction
        self.state_of_destruction = (self.capacity_nominal_kwh - self.capacity_current_kwh) / (self.capacity_nominal_kwh - self.end_of_life_battery_kwh)

        if self.state_of_destruction >= 1:
            self.replacement = self.time
            self.state_of_destruction = 0
            self.capacity_current_kwh = self.capacity_nominal_kwh
        else:
            self.replacement = 0


    def get_aging_calendar(self):
        """Calculate battery calendar aging according to specified float lifetime.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

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
            # Float life loss in kWh
            self.float_life_loss = ((self.capacity_nominal_kwh-self.end_of_life_battery_kwh) / (self.float_life*365*24*(3600/self.timestep)))
        else:
            # Float life loss in kWh
            self.float_life_loss = 0.


    def get_aging_cycling(self):
        """Calculate battery cycling aging according to micro cycle approach.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

        Note
        ----
        - Cycle life dependent on DoD and temperature if specified
        - The model is described in detailed in [4]_ and [5]_.

        Attention
        ---------
        - At this point the EoL capacity needs to be the same as for the cycle life assumed EoL criteria
            - For LFP data shows cycles until 80% capacity, so for calculation of cycle_life_loss also 80% Capacity at EoL needs to be considered!

        .. [4] Narayan et al. "A simple methodology for estimating battery
            lifetimes in Solar Home System design", IEEE Africon 2017 Proceedings, 2017.
        .. [5] Narayan et al. "Estimating battery lifetimes in Solar Home System design using a practical
            modelling methodology, Applied Energy 228, 2018.
        """

        # Micro cycle is running
        if self.power_cell != 0:
            # Add up energy [kWh] , counter, DoD amnd temperature of micro cycle
            self.energy_mc += abs(self.power_cell*(self.timestep/3600))
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
                #self.depth_of_discharge_mc_mean_lst.append(self.depth_of_discharge_mc_mean)
                #self.energy_mc_lst.append(self.energy_mc)

                self.temperature_mc_mean = (self.temperature_mc/self.counter_mc)

                # Calculate cycle_life/_mc/_loss for micro cycle evaluation
                self.cycle_life_mc = self.energy_mc / (2*self.capacity_nominal_kwh*self.depth_of_discharge_mc_mean)
                #self.cycle_life_mc_lst.append(self.cycle_life_mc)

                self.cycle_life = (self.cycle_aging_p4*self.depth_of_discharge_mc_mean**4 + self.cycle_aging_p3*self.depth_of_discharge_mc_mean**3 \
                                   + self.cycle_aging_p2*self.depth_of_discharge_mc_mean**2 + self.cycle_aging_p1*self.depth_of_discharge_mc_mean + self.cycle_aging_p0) \
                                   * ((self.cycle_aging_pl1*self.temperature_mc_mean) + self.cycle_aging_pl0)
                #self.cycle_life_lst.append(self.cycle_life)

                self.cycle_life_rel_loss = (self.cycle_life_mc / self.cycle_life)
                self.cycle_life_loss = (self.cycle_life_rel_loss * (self.capacity_nominal_kwh-(0.8*self.capacity_nominal_kwh)))#self.end_of_life_battery_kwh))

            # Reset parameter to initial values
            self.counter_mc = 0
            self.energy_mc = 0
            self.depth_of_discharge_mc = 0
            self.temperature_mc = 0
