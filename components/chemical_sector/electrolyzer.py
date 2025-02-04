import pyomo.environ as pyo
import numpy as np

from simulatable import Simulatable
from serializable import Serializable
from optimizable import Optimizable

class Electrolyzer(Serializable, Simulatable, Optimizable):
    """Relevant methods for the calculation of electrolyzer performance.

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    power_nominal : `int`
        [kW] Installed electrolyzer nominal electric power (P-in).
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Generic class, can be used for modeling of various electrolyzer technologies.
    - Currently it reflects PEM electrolyzer.
    """
    def __init__(self,
                 timestep,
                 power_nominal,
                 file_path = None):

         # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for battery model specified')
            self.name = "Electrolyzer"                                          # Component name
            self.specification = "PEM"                                          # Component technology type
            self.power_norm_min = 0.1                                           # Optimization: [1] Minimal partial load power in percentage of nominal electric power
            self.power_norm_max = 1.0                                           # Optimization: [1] Maximal partial load power in percentage of nominal electric power
            self.power_thermal_frac = 0.0                                       # Optimization: Ratio of total efficiency (el+th) to thermal efficiency
            self.efficiency_h2 = 0.5                                            # Optimization: [1] Electrolyzer static efficiency of transformation of el to h2
            self.performance_piecewise = "True"                                 # Optimization: PWA representation of performance curve
            self.pwa_alpha = [0.615927,0.559282,0.509012,0.458945]              # Optimization: PWA slopes of each line segment
            self.pwa_beta = [-0.022493,-0.006265,0.017629,0.055053]             # Optimization: PWA y-intercept of each line segment
            self.heating_value_kg = 33.33                                       # Simulation: [kWh/kg] Heating value of hydrogen
            self.heating_value_Nm = 3.0                                         # Simulation: [kWh/Nm3] Heating value of hydrogen
            self.efficiency_nominal = 0.6947                                    # Simulation: [1] Nominal efficiency
            self.efficiency_el_a = 0.732371                                     # Simulation: [] El. efficiency factor a
            self.efficiency_el_b = -0.236654                                    # Simulation: [] El. efficiency factor b
            self.efficiency_el_c = -1.57696                                     # Simulation: [] El. efficiency factor c
            self.efficiency_el_d = -29.832                                      # Simulation: [] El. efficiency factor d
            self.efficiency_el_e = 0.0                                          # Simulation: [] El. efficiency factor e
            self.efficiency_th_a = 0.0876978                                    # Simulation: [] Th. efficiency factor a
            self.efficiency_th_b = 0.329614                                     # Simulation: [] Th. efficiency factor b
            self.efficiency_th_c = -0.00676109                                  # Simulation: [] Th. efficiency factor c
            self.end_of_life_operation = 144000000                              # Aging model: [s] Number of operating hours until end of life
            self.end_of_life_cycles = 5000                                      # Aging model: [1] Number of on-off-cycles until end of life
            self.capex_p1 = 9396.5                                              # Economic model: [] Economic function factor a
            self.capex_p2 = -0.3550                                             # Economic model: [] Economic function factor b
            self.subsidy_percentage_capex = 0.0                                 # Economic model: [%] Capex subsidy
            self.subsidy_limit = 28000.0                                        # Economic model: [€/$] Max total capex subsidy
            self.opex_fix_p1 = 0.02                                             # Economic model: [1/CC/a] Share of omc costs of cc
            self.opex_var = 0.0                                                 # [€$/kWh] opex-variable: Specific variable opex dependent on energy

        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # [s] Timestep
        self.timestep = timestep

        ## Performance model
        # [kW] Nominal input power
        self.power_nominal = power_nominal

        ##Economic parameter
        # [kW] Nominal power
        self.size_nominal = self.power_nominal
        # Calculate specific cost only if installed capacity is not 0!
        if self.power_nominal != 0:
            # [$/kW] Electrolyzer specific investment costs
            self.capex_specific = (self.capex_p1 * self.size_nominal**self.capex_p2)
            # [€/kW] Electrolyzer specific operation and maintenance cost
            self.opex_fix_specific = (self.opex_fix_p1 * self.capex_specific)
        else:
            self.capex_specific = 0
            self.opex_fix_specific = 0


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
        Pyomo: MILP Electrolyzer block construction

        Parameters
        ----------
        model : pyomo.model class instance (defined in optimizabe.py)

        Returns
        -------
        None : `None`
        """

        # Central pyomo model
        self.model = model

        ## Electrolyzer block
        self.model.blk_ely = pyo.Block()

        # In case capacity is NOT 0 normal calculation
        if self.power_nominal != 0:
            # Define parameters
            self.model.blk_ely.power_nominal = pyo.Param(initialize=self.power_nominal)
            self.model.blk_ely.power_norm_min = pyo.Param(initialize=self.power_norm_min)
            self.model.blk_ely.power_norm_max = pyo.Param(initialize=self.power_norm_max)
            self.model.blk_ely.power_thermal_frac = pyo.Param(initialize=self.power_thermal_frac)       # Ratio of total efficiency (el+th) to thermal efficiency

            # Define variables
            self.model.blk_ely.on_off = pyo.Var(self.model.timeindex, domain=pyo.Binary)                # On/off status of component: 0=off and 1=on (needed for minimal and maximal power control
            self.model.blk_ely.power_el = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)
            self.model.blk_ely.power_h2 = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)
            self.model.blk_ely.power_th = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)

            ## Piecewise representation of electrolyzer performance
            if self.performance_piecewise == "True":

                # Define variables (only necessary for PWA representation)
                self.model.blk_ely.power_nominal_aux = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)     # Auxiliary component of nominal power

                # Define Constraints
                # Power aux constraint
                def pwa_power_aux_rule(_b, t):
                    return (_b.power_nominal_aux[t] == _b.on_off[t] * _b.power_nominal)
                self.model.blk_ely.pwa_power_aux_c = pyo.Constraint(self.model.timeindex, rule=pwa_power_aux_rule)

                # Min and Max operation range constraint
                def pwa_max_power_operation_rule(_b, t):
                    return (_b.power_el[t] <= _b.power_norm_max * _b.power_nominal_aux[t])
                self.model.blk_ely.pwa_max_power_op_c = pyo.Constraint(self.model.timeindex, rule=pwa_max_power_operation_rule)

                def pwa_min_power_operation_rule(_b, t):
                    return (_b.power_el[t] >= _b.power_norm_min * _b.power_nominal_aux[t])
                self.model.blk_ely.pwa_min_power_op_c = pyo.Constraint(self.model.timeindex, rule=pwa_min_power_operation_rule)

                # PWA constraints for each line segment
                # Iterate over all line segments and create constraint
                for segment in range(0,4):
                    # Define constraint rule
                    def pwa_constraint(_b, t):
                        return ((_b.power_h2[t] <= self.pwa_alpha[segment] * _b.power_el[t] + self.pwa_beta[segment] * _b.power_nominal_aux[t]))

                    setattr(self.model.blk_ely, f"Constraint_PWA_segment_{segment}", pyo.Constraint(self.model.timeindex, rule=pwa_constraint))


            ## Static representation of battery performance
            elif self.performance_piecewise == "False":

                # Define parameters
                self.model.blk_ely.efficiency_h2 = pyo.Param(initialize=self.efficiency_h2)

                # Define constraints
                # Performance of Transformation electricity-hydrogen
                def power_h2_rule(_b, t):
                    return (_b.power_h2[t] == (_b.power_el[t] * _b.efficiency_h2))
                self.model.blk_ely.power_h2_out_c = pyo.Constraint(self.model.timeindex, rule=power_h2_rule)

                # Max electric power according to nominal power
                def max_power_el_rule(_b, t):
                    return (_b.power_el[t] <= _b.on_off[t] * _b.power_norm_max * _b.power_nominal)
                self.model.blk_ely.max_power_el_c = pyo.Constraint(self.model.timeindex, rule=max_power_el_rule)

                # Min electric power to start component
                def min_power_el_rule(_b, t):
                    return (_b.power_el[t] >= _b.on_off[t] * _b.power_norm_min * _b.power_nominal)
                self.model.blk_ely.min_power_el_c = pyo.Constraint(self.model.timeindex, rule=min_power_el_rule)

            else:
                print('Error Electrolyzer pyomo model: Define ely parameter "performance_piecewise" correctly!')


            # Define constraints
            # Definition of thermal power output
            def power_th_out_rule(_b, t):
                if _b.power_thermal_frac > 0:
                    return (_b.power_th[t] == _b.power_el[t] * (_b.power_thermal_frac - 1))
                else:
                    return (_b.power_th[t] == 0)
            self.model.blk_ely.power_th_out_c = pyo.Constraint(self.model.timeindex, rule=power_th_out_rule)


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

                self.model.blk_ely.min_runtime_c = pyo.Constraint(self.model.timeindex, rule=min_runtime_constraint1)

            else:
                pass

         # Incase capacity is 0 - no variables - only params=0!
        else:
            self.model.blk_ely.on_off = pyo.Param(self.model.timeindex, initialize=0)
            self.model.blk_ely.power_el = pyo.Param(self.model.timeindex, initialize=0)
            self.model.blk_ely.power_h2 = pyo.Param(self.model.timeindex, initialize=0)
            self.model.blk_ely.power_th = pyo.Param(self.model.timeindex, initialize=0)
            if self.performance_piecewise == "True":
                self.model.blk_ely.power_nominal_aux = pyo.Param(self.model.timeindex, initialize=0)


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
        self.on_off_list = list(self.model.blk_ely.on_off.extract_values().values())
        self.power_el_list = list(self.model.blk_ely.power_el.extract_values().values())
        self.power_h2_list = list(self.model.blk_ely.power_h2.extract_values().values())
        self.power_th_list = list(self.model.blk_ely.power_th.extract_values().values())

        # Variables of PWA performance
        if self.performance_piecewise == 'True':
            self.power_nominal_aux_list = list(self.model.blk_ely.power_nominal_aux.extract_values().values())


    def get_power(self):
        """ Calculate the electrolyzer power and efficiencies.

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

        # Efficiency
        if self.power != 0:
            self.efficiency_el = self.efficiency_el_a * np.exp(self.efficiency_el_b * (self.power/self.power_nominal)) \
                                 + self.efficiency_el_c * np.exp(self.efficiency_el_d * (self.power/self.power_nominal)) \
                                 + self.efficiency_el_e
            if self.efficiency_el < 0:
                self.efficiency_el = 0

            self.efficiency_th = self.efficiency_th_a *(self.power/self.power_nominal)**2 \
                                 + self.efficiency_th_b * (self.power/self.power_nominal) \
                                 + self.efficiency_th_c
            if self.efficiency_th < 0:
                self.efficiency_th = 0

            self.hydrogen_produced_power = self.power * self.efficiency_el
            self.hydrogen_produced_kg = self.power * self.efficiency_el / self.heating_value_kg
            self.hydrogen_produced_Nl = self.power * self.efficiency_el / self.heating_value_Nm
            self.heat_produced = self.power * self.efficiency_th

        else:
            self.efficiency_el = 0
            self.efficiency_th = 0
            self.hydrogen_produced_power = 0
            self.hydrogen_produced_kg = 0
            self.hydrogen_produced_Nl = 0
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
            # Electrolyzer in operation
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