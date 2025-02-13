import pyomo.environ as pyo
import numpy as np

from simulatable import Simulatable
from serializable import Serializable
from optimizable import Optimizable

class Hydrogen_Storage(Serializable, Simulatable, Optimizable):
    """ Relevant methods for the calculation of hydrogen storage performance.

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    capacity_kwh : `int`
        [kWh] Installed hydrogen capacity (chemical energy).
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    None
    """

    def __init__(self,
                 timestep,
                 capacity_kwh,
                 file_path = None):

         # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for hydrogen storage model specified')
            self.specification = "Hydrogen Storage"
            self.state_of_charge_balanced = "True"                              # Optimization: True:SoC(start)=SoC(end)
            self.state_of_charge_initial = 0.0                                  # Optimization: [1] Initial storage SoC
            self.end_of_charge = 1.0                                            # Optimization: [1] Storage end of charge level
            self.end_of_discharge = 0.1                                         # Optimization: [1] Storage end of discharge level
            self.self_discharge_rate = 0.0                                      # Optimization/Simulation´: [1/s] Storage self discharge rate, e.g. 1%/monat = 0.01/(30.4*24*3600)
            self.heating_value_kg = 33.33                                       # Optimization/Simulation: [kWh/kg] LHV hydrogen
            self.heating_value_Nm = 3.0                                         # Optimization/Simulation: [kWh/Nm³] LHV hydrogen
            self.end_of_life = 946080000                                        # Aging model: [s] End of life
            self.capex_p1 = 19.5                                                # [€$/kWh] capex: Parameter1 (gradient) for specific capex definition
            self.capex_p2 = -0.0420                                             # [€$/kWh] capex: Parameter2 (y-intercept) for specific capex definition
            self.subsidy_percentage_capex = 0.0                                 # Economic model: [%] Capex subsidy
            self.subsidy_limit = 28000.0                                        # Economic model: [€/$] Max total capex subsidy
            self.opex_fix_p1 = 0.02                                             # [€$/kWh/a] opex-fixed:  % of capex
            self.opex_var = 0.0                                                 # [€$/kWh] opex-variable: Specific variable opex dependent on generated energy

        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # [s] Timestep
        self.timestep = timestep

        ## Performance model
        # [kWh&kg] Storage capacity
        self.capacity_kwh = capacity_kwh
        self.capacity_kg = self.capacity_kwh / self.heating_value_kg

        ## Economic model
        # [kWh] Initialize Nominal capacity
        self.size_nominal = self.capacity_kwh
        # Calculate specific cost only if installed capacity is not 0!
        if self.capacity_kwh != 0:
            # [€$/kWh] Initialize specific capex
            self.capex_specific = (self.capex_p1 * self.size_nominal**self.capex_p2)
            # [€$/kWh] Initialize specific fixed opex
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

        # Initialize values
        ## Aging model
        self.replacement_set = 0 # Ist das notwendig? andere Klassen haben das nciht!?


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
        # Calculate electrolyzer state of destruction
        self.get_state_of_destruction()

        ## Save component status variables for all timesteps to list
        self.state_of_destruction_list.append(self.state_of_destruction)
        self.replacement_list.append(self.replacement)


    def optimization_get_block(self, model):
        """
        Pyomo: MILP H2 storage block construction

        Parameters
        ----------
        model : pyomo.model class instance (defined in optimizabe.py)

        Returns
        -------
        None : `None`

        Note
        ----
        None : `None`
        """

        # Central pyomo model
        self.model = model

        # H2 storage block
        self.model.blk_hydrogen_storage = pyo.Block()

        # In case capacity is NOT 0, normal calculation
        if self.capacity_kwh != 0:
            # Define parameters
            self.model.blk_hydrogen_storage.capacity = pyo.Param(initialize=self.capacity_kwh)
            self.model.blk_hydrogen_storage.end_of_charge = pyo.Param(initialize=self.end_of_charge)
            self.model.blk_hydrogen_storage.end_of_discharge = pyo.Param(initialize=self.end_of_discharge)
            self.model.blk_hydrogen_storage.self_discharge_rate = pyo.Param(initialize=self.self_discharge_rate)
            self.model.blk_hydrogen_storage.state_of_charge_initial = pyo.Param(initialize=self.state_of_charge_initial)

            # Define variables
            self.model.blk_hydrogen_storage.power_ch = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)                               # h2 storage charging power
            self.model.blk_hydrogen_storage.power_dch = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)                              # h2 storage discharging power
            self.model.blk_hydrogen_storage.state_of_charge = pyo.Var(self.model.timeindex, bounds=(self.model.blk_hydrogen_storage.end_of_discharge,
                                                                                                    self.model.blk_hydrogen_storage.end_of_charge))       # h2 storage soc with end of ch/DCH levels

            # H2 storage SoC constraint
            def state_of_charge_rule(_b, t):
                if t == self.model.timeindex.first():
                    return (_b.state_of_charge[t] == _b.state_of_charge_initial
                                                     + (((_b.power_ch[t] - _b.power_dch[t]) / _b.capacity) * (self.timestep/3600))
                                                     - (_b.self_discharge_rate * self.timestep))
                return (_b.state_of_charge[t] == _b.state_of_charge[t-1]
                                                 + (((_b.power_ch[t] - _b.power_dch[t]) / _b.capacity) * (self.timestep/3600))
                                                 - (_b.self_discharge_rate * self.timestep))
            self.model.blk_hydrogen_storage.state_of_charge_c = pyo.Constraint(self.model.timeindex, rule=state_of_charge_rule)

            # Constraint is only set in case first and last SoC level should be the same. Storage is balanced over simulation timeframe.
            if self.state_of_charge_balanced == "True":
                # Set the overall (of all optimized timesteps) first SoC to the overall last SoC
                def soc_last_initial_rule(m, t):
                    if t == m.timeindex.last():
                        return (m.blk_hydrogen_storage.state_of_charge[t] == m.blk_hydrogen_storage.state_of_charge_initial)
                    else:
                        return pyo.Constraint.Skip
                self.model.hydrogen_storage_soc_last_initial_c = pyo.Constraint(self.model.timeindex, rule=soc_last_initial_rule)


        # Incase capacity is 0 - no variables - only params=0!
        else:
            self.model.blk_hydrogen_storage.power_ch = pyo.Param(self.model.timeindex, initialize=0)                               # h2 storage charging power
            self.model.blk_hydrogen_storage.power_dch = pyo.Param(self.model.timeindex, initialize=0)                              # h2 storage discharging power
            self.model.blk_hydrogen_storage.state_of_charge = pyo.Param(self.model.timeindex, initialize=0)


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
        self.power_ch_list = list(self.model.blk_hydrogen_storage.power_ch.extract_values().values())
        self.power_dch_list = list(self.model.blk_hydrogen_storage.power_dch.extract_values().values())
        self.state_of_charge_list = list(self.model.blk_hydrogen_storage.state_of_charge.extract_values().values())

        ## Transfer opti results to sim sign convention
        self.power_list = list(np.array(self.power_ch_list)-np.array(self.power_dch_list))


    def get_state_of_charge(self):
        """Calculate the hydrogen storage state of charge.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

        Note
        ----
        - Model is based on simple energy balance using an off-line book-keeping method.
        """

        # save soc of last timestep
        self.state_of_charge_old = self.state_of_charge

        # caculate soc of current timestep
        self.state_of_charge = self.state_of_charge + (self.power / (self.capacity_kwh) * (self.timestep/3600))

        self.state_of_charge = self.state_of_charge



    def get_state_of_destruction(self):
        """Calculate the component state of destruction (SoD) and time of
        component replacement according to end of life criteria.
        
        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `-`

        Note
        ----
        - replacement_set stays at last replacement timestep for correct sod calculation after first replacement.
        """
        
        # Calculate state of desctruction (end_of_life is given in seconds)
        self.state_of_destruction = ((self.time+1) - self.replacement_set) / (self.end_of_life/self.timestep)

        if self.state_of_destruction >= 1:
            self.replacement_set = self.time+1
            self.replacement = self.time+1
            self.state_of_destruction = 0
        else:
            self.replacement = 0
