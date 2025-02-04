import pyomo.environ as pyo
import numpy as np

import data_loader
from simulatable import Simulatable
from serializable import Serializable
from optimizable import Optimizable

class Fuelcell(Serializable, Simulatable, Optimizable):
    """ Relevant methods for the calculation of Fuel Cell performance.

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    power_nominal : `int`
        [kW] Installed fuel cell nominal electric power (P-out).
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Generic class, can be used for modeling of various fuel cell technologies.
    - Currently it reflects PEM fuel cells.
    """

    def __init__(self,
                 timestep,
                 power_nominal,
                 file_path = None):

         # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for fuelcell model specified')
            self.name = "Fuel cell"                                             # Component name
            self.specification = "PEM"                                          # Component technology type
            self.power_norm_min = 0.1                                           # Optimization: [1] Minimal partial load power in percentage of nominal electric power
            self.power_norm_max = 1.0                                           # Optimization: [1] Maximal partial load power in percentage of nominal electric power
            self.power_thermal_frac = 1.5                                       # Optimization: Ratio of total efficiency (el+th) to thermal efficiency
            self.efficiency_el = 0.5                                            # Optimization: [1] Fuel cell static efficiency of transformation of h2 to el
            self.performance_piecewise = "True"                                 # Optimization: PWA representation of performance curve
            self.pwa_alpha = [0.615927,0.559282,0.509012,0.458945]              # Optimization: PWA slopes of each line segment
            self.pwa_beta = [-0.022493,-0.006265,0.017629,0.055053]             # Optimization: PWA y-intercept of each line segment
            self.pwa_efficiency_ref = 0.4310                                    # Optimization: PWA efficiency at nominal conditions (last breakpoint)
            self.heating_value_kg = 33.33                                       # Simulation: [kWh/kg] Heating value of hydrogen
            self.heating_value_Nm = 3.0                                         # Simulation: [kWh/Nm3] Heating value of hydrogen
            self.operation_point_optimum = 0.3                                  # Simulation: [] Optimal operation point (max eff)
            self.battery_soc_min = 0.6                                          # Simulation: [] Minimal battery SoC, at which FC starts
            self.efficiency_el_a = 0.780853                                     # Simulation: [] El. efficiency factor a
            self.efficiency_el_b = -0.76438                                     # Simulation: [] El. efficiency factor b
            self.efficiency_el_c = -0.800804                                    # Simulation: [] El. efficiency factor c
            self.efficiency_el_d = -9.55679                                     # Simulation: [] El. efficiency factor d
            self.efficiency_el_e = 0.0                                          # Simulation: [] El. efficiency factor e
            self.efficiency_th_a = 0.291707                                     # Simulation: [] Th. efficiency factor a
            self.efficiency_th_b = 0.586111                                     # Simulation: [] Th. efficiency factor b
            self.efficiency_th_c = -0.292195                                    # Simulation: [] Th. efficiency factor c
            self.efficiency_th_d = -6.57437                                     # Simulation: [] Th. efficiency factor d
            self.efficiency_th_e = 0.0                                          # Simulation: [] Th. efficiency factor e
            self.end_of_life_operation = 108000000                              # Aging model: [s] Number of operating hours until wnd of life
            self.end_of_life_cycles = 10000                                     # Aging model: [1] Number of on-off-cycles until end of life
            self.capex_p1 = 3708.5                                              # Economic model: [] Economic function factor a
            self.capex_p2 = -0.2430                                             # Economic model: [] Economic function factor b
            self.subsidy_percentage_capex = 0.0                                 # Economic model: [%] Capex subsidy
            self.subsidy_limit = 28000.0                                        # Economic model: [€/$] Max total capex subsidy
            self.opex_fix_p1 = 0.02                                             # Economic model: [1/CC/a] Share of omc costs of cc
            self.opex_var = 0.0                                                 # [€$/Wh] opex-variable: Specific variable opex dependent on energy

       # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # [s] Timestep
        self.timestep = timestep

        ## Performance model
        # [kW] Nominal output power
        self.power_nominal = power_nominal

        ## Economic parameter
        # [kW] Nominal power
        self.size_nominal = self.power_nominal
        # Calculate specific cost only if installed capacity is not 0!
        if self.power_nominal != 0:
            # [€/kW] Specific investment costs
            self.capex_specific = (self.capex_p1 * self.size_nominal**self.capex_p2)
            # [€/kW] Specific operation and maintenance cost
            self.opex_fix_specific = self.opex_fix_p1 * self.capex_specific
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
        self.state_of_destruction_list = list()
        self.replacement_list = list()
        self.operation_list = list()
        self.cycle_indicator_list = list()
        self.cycle_on_off_list = list()

        # Initialize values
        ## Lifetime model
        # Operation hours
        self.operation = 0
        # Cycle_on_off_indicator
        self.cycle_indicator = 0
        # Counter on-off-cycles
        self.cycle_on_off = 0


    def simulation_calculate(self):
        """Simulatable method.
        Calculate simulation results.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`
        """

        ## Get optimized values
        self.power = self.power_el_list[self.time]

        # Calculate electrolyzer state of destruction
        self.get_state_of_destruction()

        ## Save component status variables for all timesteps to list
        self.state_of_destruction_list.append(self.state_of_destruction)
        self.replacement_list.append(self.replacement)
        self.operation_list.append(self.operation)
        self.cycle_indicator_list.append(self.cycle_indicator)
        self.cycle_on_off_list.append(self.cycle_on_off)


    def optimization_get_block(self, model):
        """
        Pyomo: MILP Fuel cell block construction

        Parameters
        ----------
        model : pyomo.model class instance (defined in optimizabe.py)

        Returns
        -------
        None : `None`
        """

        # Central pyomo model
        self.model = model

        # Fuel cell block
        self.model.blk_fc = pyo.Block()

        # In case capacity is NOT 0, normal calculation
        if self.power_nominal != 0:
            # Define parameters
            self.model.blk_fc.power_nominal = pyo.Param(initialize=self.power_nominal)
            self.model.blk_fc.power_norm_min = pyo.Param(initialize=self.power_norm_min)
            self.model.blk_fc.power_norm_max = pyo.Param(initialize=self.power_norm_max)
            self.model.blk_fc.power_thermal_frac = pyo.Param(initialize=self.power_thermal_frac) # Ratio of total efficiency (el+th) to thermal efficiency

            # Variable opex (only relevant for obj fct considering storage opex_var)
            if self.opex_var == 'dynamic_tariff':
                print('FC dynamic opex_var')
                self.opex_var_cost.read_csv(file_name=self.file_path_opex_var,
                                            simulation_steps=len(self.model.timeindex))
                self.opex_var = self.opex_var_cost.get_storage_opex_var_profile()
                # Define pyomo parameter
                self.model.blk_fc.opex_var = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.opex_var))

            elif isinstance(self.opex_var, (int, float)):
                self.opex_var = [self.opex_var] * len(self.model.timeindex)
                # Define pyomo parameter
                self.model.blk_fc.opex_var =pyo.Param(self.model.timeindex, initialize=self.data_prep(self.opex_var))

            # Define variables
            self.model.blk_fc.on_off = pyo.Var(self.model.timeindex, domain=pyo.Binary)                                # On/off status of component: 0=off and 1=on (needed for minimal and maximal power control
            self.model.blk_fc.power_h2 = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)
            self.model.blk_fc.power_el = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)
            self.model.blk_fc.power_th = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)


            ## Piecewise representation of electrolyzer performance
            if self.performance_piecewise == "True":

                # Define variables (only necessary for PWA representation)
                self.model.blk_fc.power_nominal_aux = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)     # Auxiliary component of nominal power

                # Define Constraints
                # Power aux constraint
                def pwa_power_aux_rule(_b, t):
                    return (_b.power_nominal_aux[t] == _b.on_off[t] * _b.power_nominal)
                self.model.blk_fc.pwa_power_aux_c = pyo.Constraint(self.model.timeindex, rule=pwa_power_aux_rule)

                # Min and Max operation range constraint
                def pwa_max_power_operation_rule(_b, t):
                    return (_b.power_el[t] <= _b.power_norm_max * _b.power_nominal_aux[t])
                self.model.blk_fc.pwa_max_power_op_c = pyo.Constraint(self.model.timeindex, rule=pwa_max_power_operation_rule)

                def pwa_min_power_operation_rule(_b, t):
                    return (_b.power_el[t] >= _b.power_norm_min * _b.power_nominal_aux[t])
                self.model.blk_fc.pwa_min_power_op_c = pyo.Constraint(self.model.timeindex, rule=pwa_min_power_operation_rule)

                # PWA constraints for each line segment
                # Iterate over all line segments and create constraint
                for segment in range(0,4):
                    # Define constraint rule
                    def pwa_constraint(_b, t):
                        return ((_b.power_el[t] <= self.pwa_alpha[segment] * _b.power_h2[t] + self.pwa_beta[segment] * (_b.power_nominal_aux[t])/self.pwa_efficiency_ref))

                    setattr(self.model.blk_fc, f"Constraint_PWA_segment_{segment}", pyo.Constraint(self.model.timeindex, rule=pwa_constraint))


            ## Static representation of fuelcell performance
            elif self.performance_piecewise == "False":

                # Define parameters
                self.model.blk_fc.efficiency_el = pyo.Param(initialize=self.efficiency_el)

                # Define constraints
                # Performance of Transformation electricity-hydrogen
                def power_h2_rule(_b, t):
                    return (_b.power_el[t] == (_b.power_h2[t] * _b.efficiency_el))
                self.model.blk_fc.power_h2_out_c = pyo.Constraint(self.model.timeindex, rule=power_h2_rule)

                # Max electric power according to nominal power
                def max_power_el_rule(_b, t):
                    return (_b.power_el[t] <= _b.on_off[t] * _b.power_norm_max * _b.power_nominal)
                self.model.blk_fc.max_power_el_c = pyo.Constraint(self.model.timeindex, rule=max_power_el_rule)

                # Min electric power to start component
                def min_power_el_rule(_b, t):
                    return (_b.power_el[t] >= _b.on_off[t] * _b.power_norm_min * _b.power_nominal)
                self.model.blk_fc.min_power_el_c = pyo.Constraint(self.model.timeindex, rule=min_power_el_rule)

            else:
                print('Error Fuel cell pyomo model: Define fc parameter "performance_piecewise" correctly!')


            # Define constraints
            # Definition of thermal power output
            def power_th_out_rule(_b, t):
                if _b.power_thermal_frac > 0:
                    return (_b.power_th[t] == _b.power_el[t] * (_b.power_thermal_frac - 1))
                else:
                    return (_b.power_th[t] == 0)
            self.model.blk_fc.power_th_out_c = pyo.Constraint(self.model.timeindex, rule=power_th_out_rule)

            # Definition of minimal runtime constraint (static to 1h with 15min resolution)
            if self.timestep == 900:
                # Define constraint rule
                min_runtime_steps = 4                                               #  equals 4x15min=1h
                # Define constraint rule
                def min_runtime_constraint1(_b, t):
                    if (t == self.model.timeindex.last()
                        or t == (self.model.timeindex.last()-1)
                        or t == (self.model.timeindex.last()-2)):
                        return (pyo.Constraint.Skip)

                    elif t == self.model.timeindex.first():
                        return ((_b.on_off[t]+_b.on_off[t+1]+_b.on_off[t+2]+_b.on_off[t+3]) >= (min_runtime_steps * (_b.on_off[t])))

                    else:
                        return ((_b.on_off[t]+_b.on_off[t+1]+_b.on_off[t+2]+_b.on_off[t+3]) >= (min_runtime_steps * (_b.on_off[t]-_b.on_off[t-1])))

                self.model.blk_fc.min_runtime_c = pyo.Constraint(self.model.timeindex, rule=min_runtime_constraint1)

            else:
                pass


        # Incase capacity is 0 - no variables - only params=0!
        else:
            self.model.blk_fc.on_off = pyo.Param(self.model.timeindex, initialize=0)                                # On/off status of component: 0=off and 1=on (needed for minimal and maximal power control
            self.model.blk_fc.power_h2 = pyo.Param(self.model.timeindex, initialize=0)
            self.model.blk_fc.power_el = pyo.Param(self.model.timeindex, initialize=0)
            self.model.blk_fc.power_th = pyo.Param(self.model.timeindex, initialize=0)
            if self.performance_piecewise == "True":
                self.model.blk_fc.power_nominal_aux = pyo.Param(self.model.timeindex, initialize=0)


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
        self.on_off_list = list(self.model.blk_fc.on_off.extract_values().values())
        self.power_h2_list = list(self.model.blk_fc.power_h2.extract_values().values())
        self.power_el_list = list(self.model.blk_fc.power_el.extract_values().values())
        self.power_th_list = list(self.model.blk_fc.power_th.extract_values().values())
        # Variables of PWA performance
        if self.performance_piecewise == 'True':
            self.power_nominal_aux_list = list(self.model.blk_fc.power_nominal_aux.extract_values().values())


    def get_power(self):
        """ Calculate the fuel cell power and efficiencies.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

        Note
        ----
        Model is based on RLI Smooth model, compare [1]_.

        References
        ----------
        .. [1] https://github.com/rl-institut/smooth/blob/dev/smooth/components/component_pem_electrolyzer.py
        """
        ### System vom RLI
        ### https://github.com/rl-institut/smooth/blob/dev/smooth/components/component_pem_electrolyzer.py
        # The CHP an electrical efficiency and a thermal efficiency, both over
        # the load point, according to: Scholta, J. et.al. Small Scale PEM Fuel
        # Cells in Combined Heat/Power Co-generation. RCUB Afrodita.
        # http://afrodita.rcub.bg.ac.rs/~todorom/tutorials/rad24.html


        # Coefficients for efficiency function
        # Efficiency
        if self.power != 0:
            self.efficiency_el = self.efficiency_el_a * np.exp(self.efficiency_el_b * (self.power/self.power_nominal)) \
                                 + self.efficiency_el_c * np.exp(self.efficiency_el_d * (self.power/self.power_nominal)) \
                                 + self.efficiency_el_e

            self.efficiency_th = self.efficiency_th_a * np.exp(self.efficiency_th_b * (self.power/self.power_nominal)) \
                                 + self.efficiency_th_c * np.exp(self.efficiency_th_d * (self.power/self.power_nominal)) \
                                 + self.efficiency_th_e
            # Hydrogen power consumed
            self.power_hydrogen = - (self.power / self.efficiency_el)

            # Heat produced
            self.heat_produced = abs(self.power_hydrogen) * self.efficiency_th

        else:
            self.efficiency_el = 0
            self.efficiency_th = 0
            self.power_hydrogen = 0
            self.heat_produced = 0


    def get_state_of_destruction(self):
        """ Calculate the electrolyer state of destruction (SoD) and time of
        component replacement according to end of life criteria.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

        Note
        ----
        - replacement_set stays at last replacement timestep for correct sod calculation after first replacement.
        """

        # Calculate operating hours
        if self.power != 0:
            # FuelCell in operation
            self.operation += 1
        else:
            pass

        # Calculate on-off cycles
        if self.power != 0:
            self.cycle_indicator = 1

        elif self.power == 0 and self.cycle_indicator == 1:
            self.cycle_indicator = 0
            self.cycle_on_off += 1

        # Calculate state of destruction (sum of operating and on-off-cycles)
        self.state_of_destruction = (((self.operation*self.timestep) / self.end_of_life_operation)
                                     #+ (self.cycle_on_off/self.end_of_life_cycles)
                                     )

        # In case component reached its end of life
        if self.state_of_destruction >= 1:
            self.replacement = self.time
            self.state_of_destruction = 0
            self.operation = 0
        else:
            self.replacement = 0