import numpy as np
import pandas as pd
import data_loader

from serializable import Serializable

class Economics(Serializable):
    """
    Provides all relevant methods for the Total system cost Annuity and Levelized Costs of Energy calculation

    Methods
    -------
    calculate

    capital_recovery_factor
    constant_escalation_levelisation_factor
    annuity_investment_costs
    annuity_operation_maintenance_costs
    annuity_total_levelized_costs

    Parameters
    ----------
    components : `dict`
        [] Dictionary holding all system components with capital costs,
        should hold also Heat/Electricity grid component (holds all grid import and export power values)
        -> necessary for marginal cost calculation
    load_total : `int`
        [Wh] Total load
    timestep : `int`
        [s] Simulation timestep in seconds.
    simulation_steps : `int`
        [1] Number of timesteps simulated.
    file_path : `string`
        [-] filepath to economic json
    neighborhood : `class`
        [-] Optional Class representing a neighborhood object

    Returns
    -------
    None : `None`

    Note
    ----
    - Timeframe for economic calculation is defined as the number of years of the simulated timeframe
        - For correct calculation simulation should involve aging and replacement/residual calculation.
    - Alternative1: definition of component specific timeframe (and annual percentage rate) dependent on mean component lifetime (without aging and replacement/residual value consideration).
                -  Needs to be defined in component json
    - Alternative2: Define general timeframe as mean project lifetime assuming equal lifetime of all components (without aging and replacement/residual value consideration).
                -  Needs to be defined in economic json
    """

    def __init__(self,
                 components,
                 load_total,
                 timestep,
                 simulation_steps,
                 file_path,
                 neighborhood=None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for economic model specified')

            self.name = "Economic_generic"
            self.annual_percentage_rate= 0.05                                   # [-] Annual percentage rate/effektiver Jahreszins
            self.price_escalation_nominal= 0.03                                 # [-] Nominal price escalation rate

        # Get components list
        self.components = components
        # Get total load
        self.load_total = load_total
        # Get timestep
        self.timestep = timestep
        # Get simulation steps
        self.simulation_steps = simulation_steps
        # Get Neighborhood class
        self.neighborhood = neighborhood

        # Calculate timeframe for economic calculation (equals simulated timeframe)
        self.timeframe = (self.simulation_steps*(self.timestep/3600)/8760)


    def calculate(self):
        """Calls all methods to calculate overall CC and MC cost.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        """

        ## Call economic methods
        # calculate economic parameter
        self.get_capital_recovery_factor()
        self.get_constant_escalation_levelisation_factor()

        ## Calculate CAPACITY costs
        self.get_annuity_capacity_costs()
        ## Summarize CAPACITY cost components
        self.results_capacity_costs = pd.DataFrame(data=self.capacity_costs,
                                                   index=['Comp_name',
                                                          'size_nom',
                                                          'capex',
                                                          'opex_fix',
                                                          'capex_replace',
                                                          'capex_residual',
                                                          'A_capex',
                                                          'A_opex_fix',
                                                          'A_capex_replace',
                                                          'A_capex_residual',
                                                          'A_capacity'])

        ## Calculate MARGINAL costs
        self.get_annuity_marginal_costs()
        ## Summarize MARGINAL cost components
        self.results_marginal_costs = pd.DataFrame(data=self.marginal_costs,
                                                   index=['Comp_name',
                                                          'A_feed-out or opex_var',
                                                          'A_feed-in or energy_opex_var',
                                                          'A_marginal'])
        ## Calculate MARGINAL Neighborhood costs
        # NH exists - NH grid cost occur
        if self.neighborhood != None:
            self.get_annuity_nh_grid_costs()
            # print('NH exists :')
            # print('Shared energy :', sum(self.neighborhood.power_shared_direct_nh))
            # print('Cost :', self.annuity_grid_neighborhood_costs)
        # NH NOT exists - No NH grid cost
        else:
            self.marginal_costs_nh = {}
            self.marginal_costs_nh['NH'] = [0,0,0]
            # print('NH does not exist')
        ## Summarize MARGINAL_NH cost components
        self.results_marginal_costs_nh = pd.DataFrame(data=self.marginal_costs_nh,
                                                      index=['Comp_name',
                                                             'energy_shared',
                                                             'A_marginal'])



        ## Calculate overall annuity as sum of all CAPACITY and MARGINAL costs
        self.annuity_total = (self.results_capacity_costs.loc['A_capacity'].sum()
                              +self.results_marginal_costs.loc['A_marginal'].sum()
                              +self.results_marginal_costs_nh.loc['A_marginal'].sum())

        ## Calculate Levelized Cost of Energy [€/kWh]
        self.levelized_cost_energy = (self.annuity_total / abs(self.load_total))


    def get_annuity_marginal_costs(self):
        """
        Marginal costs: Calculates grid feed-in and feed-out costs and variable opex costs of components

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - variable opex are not calculated for grid components based on parameter opex_var
        - variable opex for other components need to be defined in json in parameter opex_var
        """

        # Define empty dictionary to store all capacity cost components
        self.marginal_costs = {}
        self.marginal_costs_buildings = {}
        #for i in range(0,len(self.components)):
        for key in self.components:
            # Get one component
            self.component = self.components[key]
            # Get component id and class name for identification
            self.component_id = self.components[key].name
            self.name = type(self.components[key]).__name__

            ## Calculate marginal costs for electricity grid (buy/sellign of electricity/heat)
            if key == 'grid_el' or key == 'grid_th':
                # Get grid feed out costs [$/a]
                self.get_annuity_grid_feed_out_costs()
                # Get grid feed in income [$/a]
                self.get_annuity_grid_feed_in_costs()

                # Sum annual variable OPEX cost (costs - income) [$/a]
                self.annuity_marginal = self.annuity_grid_feed_out_costs - self.annuity_grid_feed_in_costs

                # Add results to MARGINAL dict
                self.marginal_costs[self.component_id] = [self.name,
                                                          self.annuity_grid_feed_out_costs,
                                                          self.annuity_grid_feed_in_costs,
                                                          self.annuity_marginal]

            ## Calculate marginal costs for other components (variable opex for battery, fuelcell - grid fees)
            else:
                # Check if component has opex_var, if not set to 0
                if not hasattr(self.component, 'opex_var'):
                    self.component.opex_var = np.zeros(len(self.simulation_steps))

                # Check if opex_var is single value -> transfer to timeseries
                if isinstance(self.component.opex_var, (int, float)):
                    self.component.opex_var = np.ones(self.simulation_steps) * self.component.opex_var

                # Calculate opex var of component
                # Attention: opex_var is in cents and here transfered to €$
                # Get amount of energy of relevant components (only var opex for battery and fuel cell)
                if key == 'bat' and hasattr(self.neighborhood, 'power_shared_direct_nh'): # for NH Battery storage
                    self.energy_opex_var = sum(abs(self.neighborhood.power_feed_out_overview['bat_dch'].sum(axis=1).values)) * (self.timestep/3600)
                    self.opex_var = sum([(abs(x) * (self.timestep/3600) * y / 100) for x,y in zip(self.neighborhood.power_feed_out_overview['bat_dch'].sum(axis=1).values
                                                                                             ,self.component.opex_var)])
                elif key == 'fc' and hasattr(self.neighborhood, 'power_shared_direct_nh'): #  for NH H2 storage
                    self.energy_opex_var = sum(abs(self.neighborhood.power_feed_out_overview['fc'].sum(axis=1).values)) * (self.timestep/3600)
                    self.opex_var = sum([(abs(x) * (self.timestep/3600) * y / 100) for x,y in zip(self.neighborhood.power_feed_out_overview['fc'].sum(axis=1).values
                                                                                             ,self.component.opex_var)])
                else:
                    self.energy_opex_var = 0
                    self.opex_var = 0

                # Calculate annuity of opex var
                self.annuity_marginal = (self.opex_var / self.timeframe)

                # Add results to MARGINAL dict
                self.marginal_costs[self.component_id] = [self.name,
                                                          np.mean(self.component.opex_var),
                                                          self.energy_opex_var,
                                                          self.annuity_marginal]


    def get_annuity_grid_feed_out_costs(self):
        """
        Marginal costs: Get variable operation costs through electricity feed-out (buying)

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Price escalation of grid electricity considered through CELF
        """

        # Calculate grid feed out costs [$/a] Attention: grid cost buy is in cents and here transfered to €$
        self.grid_feed_out_costs = (np.array(self.component.power_feed_out_list) * (self.timestep/3600)) * self.component.cost_buy_list / 100
        # Calculate grid feed out annuity [$/a] - divide total costs with number of years
        #self.annuity_grid_feed_out_costs = (sum(self.grid_feed_out_costs) / self.timeframe)
        self.annuity_grid_feed_out_costs = (sum(self.grid_feed_out_costs) / self.timeframe * self.constant_escalation_levelisation_factor)


    def get_annuity_grid_feed_in_costs(self):
        """
        Marginal costs: Get variable operation costs through electricity feed-in (selling)

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Static Feed-in tariff, does not consider different tariffs for different technologies.
        - Does not guarantee that stored grid electricity can be fed back into the grid and FIT earned
        """

        # NH scenario with many different systems
        if hasattr(self.component, 'cost_sell_data_df'):
            # Use the same index for both house-specific dfs
            self.component.cost_sell_data_df.index = self.neighborhood.power_feed_in_overview['grid'].index
            # Calculate grid feed in income [$/a] Attention: grid cost buy is in cents and here transfered to €$
            self.grid_feed_in_costs = (self.neighborhood.power_feed_in_overview['grid'] * (self.timestep/3600)) * self.component.cost_sell_data_df / 100
            # Calculate grid feed in annuity [$/a] - divide total costs with number of years
            self.annuity_grid_feed_in_costs = (self.grid_feed_in_costs.sum().sum() / self.timeframe)

            # Create building specific A_feed-in df
            self.marginal_costs_buildings[self.name] = pd.DataFrame(data={'grid_feed_in': list((self.neighborhood.power_feed_in_overview['grid']*(self.timestep/3600)).sum()),
                                                                          'A_grid_feed_in_sbs': list(self.grid_feed_in_costs.sum() / self.timeframe)})


        else:
            # Calculate grid feed in income [$/a] Attention: grid cost buy is in cents and here transfered to €$
            self.grid_feed_in_costs = (np.array(self.component.power_feed_in_list) * (self.timestep/3600)) * self.component.cost_sell_list / 100
            # Calculate grid feed in annuity [$/a] - divide total costs with number of years
            self.annuity_grid_feed_in_costs = (sum(self.grid_feed_in_costs) / self.timeframe)



    def get_annuity_nh_grid_costs(self):
        """
        Marginal costs: Get variable operation costs through electricity sharing in neighborhood

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Price escalation of grid fees considered through CELF
        """

        # Dict to save results
        self.marginal_costs_nh = {}

        # Calculate NH grid costs [$/a] Attention: NH grid cost is in cents and here transfered to €$
        self.grid_neighborhood_costs = (self.neighborhood.power_shared_direct_nh * (self.timestep/3600) * self.neighborhood.opex_var / 100)
        # Calculate NH grid annuity [$/a] - divide total costs with number of years
        self.annuity_grid_neighborhood_costs = (sum(self.grid_neighborhood_costs) / self.timeframe * self.constant_escalation_levelisation_factor)

        # Add results to MARGINAL dict
        self.marginal_costs_nh['NH'] = ['Grid_Electricity_NH',
                                        (sum(self.neighborhood.power_shared_direct_nh) * (self.timestep/3600)),
                                        self.annuity_grid_neighborhood_costs]


    def get_annuity_capacity_costs(self):
        """
        Annuity calculation of Total Capacity costs:
            - CAPEX: Investment costs
            - OPEX-fixed: Operation and maintenance costs
            - Optional:
                - CAPEX: Replacement costs
                - CAPEX: Residual value

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Replacement and residual costs are only considered in case aging calculation is performed
        """

        # Define empty dictionary to store all capacity cost components
        self.capacity_costs = {}
        self.capacity_costs_buildings = {}
        #for i in range(0,len(self.components)):
        for key in self.components:
            # Get one component
            self.component = self.components[key]
            # Get component id and class name for identification
            self.component_id = self.components[key].name
            self.name = type(self.components[key]).__name__

            # Get all CAPACITY cost components
            self.get_annuity_capex()
            self.get_annuity_opex_fix()

            # In case aging is calculated get repalcement costs and residual costs
            try:
                self.get_annuity_capex_replacements()
                self.get_annuity_capex_residual()
            except:
                self.capex_replacements = 0
                self.annuity_capex_replacements = 0
                self.capex_residual = 0
                self.annuity_capex_residual = 0

            # Get total capacity cost
            self.annuity_capacity_costs = (self.annuity_capex
                                           + self.annuity_opex_fix
                                           + self.annuity_capex_replacements
                                           - self.annuity_capex_residual)

            # Add results to dict
            self.capacity_costs[self.component_id] = [self.name,
                                                      self.component.size_nominal,
                                                      self.capex,
                                                      self.opex_fix,
                                                      self.capex_replacements,
                                                      self.capex_residual,
                                                      self.annuity_capex,
                                                      self.annuity_opex_fix,
                                                      self.annuity_capex_replacements,
                                                      self.annuity_capex_residual,
                                                      self.annuity_capacity_costs]


    def get_annuity_capex(self):
        """
        Capacity costs: Annuity calculation of capex

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - The capex and capex subsidy calculation for NH scenarios needs to be done for each system, as often system sizes are not distributed equally
        - df self.capacity_costs_buildings shows deteiled results
        """

        # [€$] Total capex calculation
        self.capex = self.component.capex_specific * self.component.size_nominal

        # Check for subsidy possibility
        if self.component.subsidy_percentage_capex != 0:

            # NH scenario with many different systems
            if hasattr(self.component, 'size_nominal_distribution'):

                # Iterate over all component sizes
                self.capex_lst = list()
                self.subsidy_lst = list()
                self.capex_sbs_lst = list()
                for i in range(0, len(self.component.size_nominal_distribution)):
                    self.capex_lst.append(self.component.capex_specific_distribution[i] * (self.component.size_nominal_distribution[i]*self.component.size_nominal))
                    # Take lower value between subsidy (as percentage of capex) and subsidy limit
                    self.subsidy_lst.append(min((self.component.subsidy_percentage_capex * self.capex_lst[i]), self.component.subsidy_limit))
                    # Calculate capex substracted by subsidy
                    self.capex_sbs_lst.append((self.capex_lst[i] - self.subsidy_lst[i]))

                # Calculate overall capex substracted by subsidy
                self.capex = np.sum(self.capex_sbs_lst)

                # CHECK capacity_costs_component
                self.capacity_costs_buildings[self.name] = pd.DataFrame(data={'size': [(i*self.component.size_nominal) for i in self.component.size_nominal_distribution],
                                                                                    'capex_spec': self.component.capex_specific_distribution,
                                                                                    'capex_lst': self.capex_lst,
                                                                                    'subsidy_lst': self.subsidy_lst,
                                                                                    'capex_sbs_lst': self.capex_sbs_lst})

            # SB scenario with single system
            else:
                # Take lower value between subsidy (as percentage of capex) and subsidy limit
                self.subsidy = min((self.component.subsidy_percentage_capex * self.capex),
                                   self.component.subsidy_limit)
                # Substract subsidy from capex
                self.capex = (self.capex - self.subsidy)


        # No subsidy possibility
        else:
            pass

        # [€$/a] Annuity of capex
        self.annuity_capex = self.capital_recovery_factor * self.capex


    def get_annuity_opex_fix(self):
        """
        Capacity costs: Annuity calculation of fixed opex

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Fixed OPEX represent OPEX per year at first year, so it can be directly used with the CELF without considering future recurring costs or nivelization.
        - CELF is only used in combination with first year cost.
        - See: Tashtoush: Exergy and Exergoeconomic Analysis of a Cogeneration Hybrid Solar Organic Rankine Cycle with Ejector, 2018
        """

        # NH scenario with many different systems
        if hasattr(self.component, 'size_nominal_distribution'):
            self.opex_fix_lst = list()
            for i in range(0, len(self.component.size_nominal_distribution)):
                self.opex_fix_lst.append(self.component.opex_fix_specific * (self.component.size_nominal_distribution[i]*self.component.size_nominal))

            # Calculate overall capex substracted by subsidy
            self.opex_fix = np.sum(self.opex_fix_lst)
        # SB scenario with single system
        else:
            # [€$/a] Total annual fixed opex calculation
            self.opex_fix = self.component.opex_fix_specific * self.component.size_nominal

        # [€$/a] Annuity of fixed opex with price escalation consideration
        self.annuity_opex_fix = self.opex_fix * self.constant_escalation_levelisation_factor


    def get_annuity_capex_replacements(self):
        """
        Annuity calculation of Replacement Costs

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
            - Price escalation rate is considered!
        """

        # Define empty array for calculatiom of each replacement
        rc = np.zeros(len(self.component.replacement_list))

        # Cost calc for every replacement
        for k in range(0,len(self.component.replacement_list)):
            if self.component.replacement_list[k] != 0:
                # Cost of each replacement with escalation rate r
                cc = (self.capex * (1 + self.price_escalation_nominal) \
                      **(self.component.replacement_list[k] / (8760*(3600/self.timestep))))

                # Present value of replacement cost
                rc[k] = cc / (1+self.annual_percentage_rate) \
                        **(self.component.replacement_list[k] /(8760*(3600/self.timestep)))
            else:
                rc[k] = 0

        # Annuity of present value
        self.capex_replacements = sum(rc)
        self.annuity_capex_replacements = self.capital_recovery_factor * self.capex_replacements


    def get_annuity_capex_residual(self):
        """
        Annuity calculation of Residual value

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`
        """

        self.capex_residual = ((1 - self.component.state_of_destruction_list[-1]) * self.capex)

        self.annuity_capex_residual = self.capex_residual \
                                      / ((1+self.annual_percentage_rate)**self.timeframe) \
                                      * self.capital_recovery_factor


    def get_capital_recovery_factor(self):
        """
        Capital recovery factor
        Can be uniforme with defined parameters in economic class or
        component specific in case annual_percentage_rate and timeframe are defined in component class.

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - So far a uniform CRF is calculated for all components. But it is possible to implement here a component specific annual percentage rate.
        - Timeframe represents the number of annuities (equals number of simulated years)!
        """

        # In case of 1 year timeframe, simple CRF calculation
        # Uniform CRF (based on basic assumptions in economics)
        if self.timeframe == 1:
            self.capital_recovery_factor = (1 + self.annual_percentage_rate)

        else:
            self.capital_recovery_factor = (self.annual_percentage_rate* (1 + self.annual_percentage_rate)**self.timeframe) \
                                           / (((1 + self.annual_percentage_rate)**self.timeframe)-1)

        # # Component specific CRF
        # try:
        #     self.capital_recovery_factor = (self.component.annual_percentage_rate* (1 + self.component.annual_percentage_rate)**self.component.timeframe) \
        #                                    / (((1 + self.component.annual_percentage_rate)**self.component.timeframe)-1)
        #     print('Component specific CRF used for ', self.component)
        # --> needs different structure of capacity cost calculation, as crf calc needs to be called for each component

    def get_constant_escalation_levelisation_factor(self):
        """
        Constant Escalation Levelisation Factor - CELF (Nivelierungsfaktor)

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        """

        k = (1 + self.price_escalation_nominal) / (1 + self.annual_percentage_rate)
        self.constant_escalation_levelisation_factor = ((k*(1-k**self.timeframe)) / (1-k)) * self.capital_recovery_factor


    def print_economic_objectives(self):
        """
        Simple print function of main results.

        Parameter
        ---------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        """

        print('---------------------------------------')
        print('Economic functions')
        print('---------------------------------------')
        print('Considered timeframe for eco= ', self.timeframe)
        print('Total annuity [$/a]=', round(self.annuity_total, 2))
        print('Levelized Cost of Energy [$/kWh]=', round(self.levelized_cost_energy, 4))
