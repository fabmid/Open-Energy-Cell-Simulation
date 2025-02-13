import pyomo.environ as pyo
import pandas as pd
import numpy as np

from simulatable import Simulatable
from serializable import Serializable
from optimizable import Optimizable
import data_loader


class Grid_Heat(Serializable, Simulatable, Optimizable):
    """Relevant methods to define the heat grid component.

     Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    power_max : `int`
        [kW] Max grid power in kilo-watt.
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Class can not be initialized with power_max=0
    - Buying and Selling prices are loaded as timeseries or static values
    - self.power_list represents the feed in/out power to the grid
        - power feed-in is defined positive and feed-out negative
    """

    def __init__(self,
                 timestep,
                 power_max,
                 file_path = None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for heat grid model specified')
            self.name = 'Grid_generic'
            self.power_max = 100                                                # [kW] Maximum installed grid power capacity
            self.cost_buy = 13.38                                              # [Cents/kWh] Static heat buying price (normally loaded via csv as timeseries)
            self.cost_sell = 0.0                                                # [Cents/kWh] Static heat selling price (normally loaded via csv as timeseries)
            self.eco_no_systems = 1                                             # [1] The number of systems the peak power is allocated on
            self.capex_p1 = 55.0                                                # [€$/kW] capex: Parameter1 (gradient) for specific capex definition
            self.capex_p2 = 18000.0                                             # [€$/kW] capex: Parameter2 (y-intercept) for specific capex definition
            self.subsidy_percentage_capex = 30.0                                # Economic model: [%] Capex subsidy
            self.subsidy_limit = 113000.0                                       # Economic model: [€/$] Max total capex subsidy


        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for simulation of component
        Simulatable.__init__(self)

        # [s] Timestep
        self.timestep = timestep

        # [kW] Maximal thermal power
        self.power_max = power_max

        # Integrate load demand data_loader for csv load profile integration
        self.grid_cost = data_loader.HeatCost()

        # [kW] Initialize grid power
        self.cost_sell_list = None
        self.cost_buy_list = None

        ## Economic model
        # [kW] Initialize Nominal power (in this case max power is nominal power for cost calcualtion with specific cost components)
        self.size_nominal = self.power_max

        # Integrate data_loader for NH size distribution csv loading
        self.nh_loader = data_loader.NeighborhoodData()
        # Get the number of individual systems on which the peak power is installed
        # if attribute is not specified in json, set it to 1
        if not hasattr(self, 'eco_no_systems'):
            self.eco_no_systems = 1


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

        # Get economic parameters
        self.get_economic_parameters()

        ## List container to store results for all timesteps
        self.cost_sell_list = list()
        self.cost_buy_list = list()
        self.state_of_destruction_list = list()
        self.replacement_list = list()

        # Time-dependent cost profiles for buying/selling, no FIT dependent on PV peak power
        if self.cost_dynamic == "True":
            # Electricity sell prices
            self.cost_sell_list = self.grid_cost.get_heat_cost_sell()
            # Electricity buy prices
            self.cost_buy_list = self.grid_cost.get_heat_cost_buy()

        # Static buying sellign prices
        elif self.cost_dynamic == "False":
            # Electricity sell prices
            self.cost_sell = self.cost_sell
            # Electricity buy price
            self.cost_buy = self.cost_buy

        else:
            print('Heat grid price modus not correctly defined!')

        ## Initialization of parameter
        # Aging model
        self.replacement_set = 0


    def simulation_calculate(self):
        """Extracts time dependent heat cost for each timestep .

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Timeseries cost data is already loaded as list in simulation_init class.
        """

        if self.cost_dynamic == "True":
            pass

        elif self.cost_dynamic == "False":
            ## Save component status variables for all timesteps to list
            self.cost_sell_list.append(self.cost_sell)
            self.cost_buy_list.append(self.cost_buy)

        else:
            pass

        # Calculate State of Desctruction
        self.get_state_of_destruction()

        ## Save component status variables for all timesteps to list
        self.state_of_destruction_list.append(self.state_of_destruction)
        self.replacement_list.append(self.replacement)


    def optimization_get_block(self, model):
        """
        Pyomo: MILP electricity grid block construction

        Parameters
        ----------
        model : pyomo.model class instance (defined in optimizabe.py)

        Returns
        -------
        None : `None`
        """

        # Central pyomo model
        self.model = model

        ## Grid block
        self.model.blk_grid_heat = pyo.Block()

        # Define parameters
        self.model.blk_grid_heat.power_max = pyo.Param(initialize=self.power_max)
        self.model.blk_grid_heat.cost_buy = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.cost_buy_list))
        self.model.blk_grid_heat.cost_sell = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.cost_sell_list))

        # Define variables
        self.model.blk_grid_heat.im_ex = pyo.Var(self.model.timeindex, domain=pyo.Binary)                                        # feed-out-->0, if feed-in-->1
        self.model.blk_grid_heat.power_feed_out = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)                     # grid import power
        self.model.blk_grid_heat.power_feed_in = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)                      # grid export power

        # Define constraints
       # Grid power max import constraint
        def power_feed_out_max_rule(_b, t):
            return (_b.power_feed_out[t] + _b.im_ex[t] * _b.power_max <= _b.power_max)
        self.model.blk_grid_heat.power_feed_out_max_c = pyo.Constraint(self.model.timeindex, rule=power_feed_out_max_rule)

        # Grid power max export constraint
        def power_feed_in_max_rule(_b, t):
            return (_b.power_feed_in[t] - _b.im_ex[t] * _b.power_max <= 0)
        self.model.blk_grid_heat.power_feed_in_max_c = pyo.Constraint(self.model.timeindex, rule=power_feed_in_max_rule)


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
        self.im_ex_list = list(self.model.blk_grid_heat.im_ex.extract_values().values())
        self.power_feed_out_list = list(self.model.blk_grid_heat.power_feed_out.extract_values().values())
        self.power_feed_in_list = list(self.model.blk_grid_heat.power_feed_in.extract_values().values())

        ## Transfer opti results to sim sign convention
        self.power_list = list(np.array(self.power_feed_in_list)-np.array(self.power_feed_out_list))


    def get_state_of_destruction(self):
        """Calculate the component state of destruction (SoD) and time of
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

        # Calculate state of desctruction (end_of_life is given in seconds)
        self.state_of_destruction = ((self.time+1) - self.replacement_set) / (self.end_of_life/self.timestep)

        if self.state_of_destruction >= 1:
            self.replacement_set = self.time+1
            self.replacement = self.time+1
            self.state_of_destruction = 0
        else:
            self.replacement = 0


    def get_economic_parameters(self):
        """Calculate the component specific capex and fixed opex for a neighborhood scenario where multiple systems are installed.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

        Note
        ----
        """
        # Calculate specific cost only if installed capacity is not 0!
        if self.power_max != 0:
            # For single building scenarios - SB
            if self.eco_no_systems == 1:
                # [€$/Wth] Initialize specific capex
                self.capex_specific = ((self.capex_p1 * (self.size_nominal/self.eco_no_systems) + self.capex_p2) / (self.size_nominal/self.eco_no_systems))
                # [€$/Wth] Initialize specific fixed opex
                self.opex_fix_specific = (self.opex_fix_p1 * self.capex_specific)

            # For neigborhood scenarios - NH
            else:
                # Get size distribution of PV systems in neighborhood
                self.size_nominal_distribution = self.nh_loader.get_grid_heat_size_distribution()
                # Calculate specific capex distribution for different PV sizes
                self.capex_specific_distribution = [((self.capex_p1 * (self.size_nominal*j) + self.capex_p2) / (self.size_nominal/self.eco_no_systems)) if j>0 else 0 for j in self.size_nominal_distribution]
                # [€$/kWp] Get NH specific capex as mean value of distribution
                self.capex_specific =  np.mean([i for i in self.capex_specific_distribution if i != 0])
                # [€$/kWp] Initialize specific fixed opex
                self.opex_fix_specific = (self.opex_fix_p1 * self.capex_specific)
        # No capex/opex fix in case of no installation
        else:
            self.capex_specific = 0
            self.opex_fix_specific = 0