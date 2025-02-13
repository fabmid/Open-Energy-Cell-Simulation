import pyomo.environ as pyo
import pandas as pd
import numpy as np

from simulatable import Simulatable
from serializable import Serializable
from optimizable import Optimizable
import data_loader

class Grid_Electricity(Serializable, Simulatable, Optimizable):
    """Relevant methods to define the electricity grid component.

    Parameters
    ----------
    pv : `class`
        To pv class.
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - So far nor capacity cost caluclation for electricity included.
    - Buying prices are loaded as timeseries, no static float computation anymore, in case you consider static values create timeseries of static value.
    - Selling prices can be:
        - Loaded as timeseries (recommended but no differentation between diferent selling prices, e.g. FIT of PV and Wind)
        - Define fixed FIT for pv and wind electricity:
            - Further adaptions need to be done in objective fucntion, add constraint included and economics class!
    - self.power_list represents the feed in/out power to the grid
        - power feed-in is defined positive and feed-out negative
    """

    def __init__(self,
                 pv,
                 file_path = None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for electricity grid model specified')
            self.name = 'Grid_generic'
            self.power_max = 100                                                # [kW] Maximum installed grid power capacity
            self.cost_buy_base = 169.70                                         # [€$/a] Fix price (Grundpreis) for network charges and measurement devices
            self.cost_dynamic = False                                           # [] Indicator weather timeseries of sell/buy costs shall be loaded
            self.cost_buy = 37.3                                                # [€$ cent/kWh] Static electricity buying price (Arbeitspreis)
            self.cost_sell_10 = 8.2                                             # [€$ cent/kWh] Static electricity selling price
            self.cost_sell_40 = 7.1                                             # [€$ cent/kWh] Static electricity selling price
            self.cost_sell_100 = 5.8                                            # [€$ cent/kWh] Static electricity selling price
            self.capex_p1 = 0.0                                                 # Economic model:[€$] capex as absolute value
            self.subsidy_percentage_capex = 0.0                                 # Economic model: [%] Capex subsidy
            self.subsidy_limit = 0.0                                            # Economic model: [€/$] Max total capex subsidy
            self.opex_p1 = 169.70                                               # Economic model:[€$/a] capex as absolute value

        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for simulation of component
        Simulatable.__init__(self)

        # Define installed PV peak power for FIT definition (Sum of all orientations)
        self.pv = pv
        self.pv_peak_power = self.pv.peak_power_nominal

        # Integrate data_loader for cost profile integration
        self.grid_cost = data_loader.ElectricityCost()

        # [kW] Initialize grid power
        self.power = 0

        ## Economic model
        # [kWp] Initialize Nominal power
        # Attention: absolute cost values are onsidered here, therefore size_nominal=1, as in economic.py class specific costs are multiplied with nominal_value!
        self.size_nominal = 1
        # [€$] Initialize absolute capex
        self.capex_specific = self.capex_p1
        # [€$] Initialize absolute fixed opex
        self.opex_fix_specific = self.opex_fix_p1


    def simulation_init(self):
        """Simulatable method.
        Initialize list containers to store simulation results.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
            - Calculate peak pwoer dependent FIT for PV
            - Load timeseries of buying/selling prices if chosen
        """

        ## List container to store results for all timesteps
        self.cost_sell_list = list()
        self.cost_buy_list = list()

        # For single building scenarios - SB
        if self.pv.eco_no_systems == 1:

            # Time-dependent cost profiles for buying/selling, no FIT dependent on PV peak power
            if self.cost_dynamic == "True":

                # Electricity buy prices
                self.cost_buy_data = self.grid_cost.get_electricity_cost_buy()
                # Electricity sell prices
                self.cost_sell_data = self.grid_cost.get_electricity_cost_sell()

                # if cost_sell_data is empty -> static EEG sell tariff:
                if self.cost_sell_data.isna().any():
                    print('No dynamic PV FIT tariff')
                    # Define Feed-in tarif dependent on PV size
                    if self.pv_peak_power <= 10: # Until 10kW
                        self.cost_sell = round(self.cost_sell_10,2)

                    elif self.pv_peak_power > 10 and self.pv_peak_power <= 40: # Until 40kW
                        self.cost_sell = round(((10*self.cost_sell_10 + ((self.pv_peak_power-10)*self.cost_sell_40)) / self.pv_peak_power),2)

                    else:   # Bigger than 40kW
                        self.cost_sell = round(((10*self.cost_sell_10 + 30*self.cost_sell_40 + (self.pv_peak_power-40)*self.cost_sell_100) / self.pv_peak_power),2)

                    self.cost_sell_data = pd.Series([self.cost_sell] * len(self.cost_sell_data))

            # Static buying sellign prices, FIT according to PV peak power
            elif self.cost_dynamic == "False":
                # Electricity buy price
                self.cost_buy = self.cost_buy
                self.cost_buy_data = pd.Series([self.cost_buy] * len(self.pv.power_ac_mc))

                # Electricity sell prices
                # Define Feed-in tarif dependent on PV size
                if self.pv_peak_power <= 10: # Until 10kW
                    self.cost_sell = round(self.cost_sell_10,2)

                elif self.pv_peak_power > 10 and self.pv_peak_power <= 40: # Until 40kW
                    self.cost_sell = round(((10*self.cost_sell_10 + ((self.pv_peak_power-10)*self.cost_sell_40)) / self.pv_peak_power),2)

                else:   # Bigger than 40kW
                    self.cost_sell = round(((10*self.cost_sell_10 + 30*self.cost_sell_40 + (self.pv_peak_power-40)*self.cost_sell_100) / self.pv_peak_power),2)

                self.cost_sell_data = pd.Series([self.cost_sell] * len(self.pv.power_ac_mc))

            else:
                print('Electricity grid price modus not correctly defined!')


        # For neigborhood scenarios - NH
        else:
            # Get size distribution of PV systems in neighborhood
            self.size_nominal_distribution = self.pv.size_nominal_distribution
            # Calculate different PV sizes
            self.pv_size_distribution = [(self.pv_peak_power*j) if j>0 else 0 for j in self.size_nominal_distribution]


            # Time-dependent cost profiles for buying/selling, no FIT dependent on PV peak power
            if self.cost_dynamic == "True":

                # Electricity buy prices
                self.cost_buy_data = self.grid_cost.get_electricity_cost_buy()
                # Electricity sell prices
                self.cost_sell_data = self.grid_cost.get_electricity_cost_sell()

                # if cost_sell_data is empty -> static EEG sell tariff:
                self.cost_sell_lst = list()
                if self.cost_sell_data.isna().any():
                    print('No dynamic PV FIT tariff')
                    # Define Feed-in tarif dependent on PV size
                    self.cost_sell_lst = list()
                    for j in range(0,len(self.pv_size_distribution)):
                        if self.pv_size_distribution[j] == 0:
                            self.cost_sell = 0

                        elif self.pv_size_distribution[j] > 0 and self.pv_size_distribution[j] <= 10: # Until 10kW
                            self.cost_sell = round(self.cost_sell_10,2)

                        elif self.pv_size_distribution[j] > 10 and self.pv_size_distribution[j] <= 40: # Until 40kW
                            self.cost_sell = round(((10*self.cost_sell_10 + ((self.pv_size_distribution[j]-10)*self.cost_sell_40)) / self.pv_size_distribution[j]),2)

                        else:   # Bigger than 40kW
                            self.cost_sell = round(((10*self.cost_sell_10 + 30*self.cost_sell_40 + (self.pv_size_distribution[j]-40)*self.cost_sell_100) / self.pv_size_distribution[j]),2)

                        # Save each house specific FIT in list
                        self.cost_sell_lst.append(self.cost_sell)

                    # Defining df with FIT tarif for each pv system
                    self.cost_sell_data_df = pd.DataFrame({i: [entry] * len(self.cost_sell_data) for i, entry in enumerate(self.cost_sell_lst)})
                    self.cost_sell_data_df.columns = pd.Index(self.cost_sell_data_df.columns, dtype='int64', name='houses')
                    # Calculate simple mean value of all pv system specific
                    data = self.cost_sell_data_df.values
                    # Replace 0 with NaN
                    data = np.where(data == 0, np.nan, data)
                    # Calculate the mean of each row excluding NaNs
                    mean_values_per_row = np.nanmean(data, axis=1)
                    # Convert the result back to a DataFrame if needed
                    self.cost_sell_data = pd.DataFrame(mean_values_per_row, columns=['Mean'])


            # Static buying sellign prices, FIT according to PV peak power
            elif self.cost_dynamic == "False":
                # Electricity buy price
                self.cost_buy = self.cost_buy
                self.cost_buy_data = pd.Series([self.cost_buy] * len(self.pv.power_ac_mc))

                # Electricity sell prices
                # Define Feed-in tarif dependent on PV size
                self.cost_sell_lst = list()
                for j in range(0,len(self.pv_size_distribution)):
                    if self.pv_size_distribution[j] == 0:
                        self.cost_sell = 0

                    elif self.pv_size_distribution[j] > 0 and self.pv_size_distribution[j] <= 10: # Until 10kW
                        self.cost_sell = round(self.cost_sell_10,2)

                    elif self.pv_size_distribution[j] > 10 and self.pv_size_distribution[j] <= 40: # Until 40kW
                        self.cost_sell = round(((10*self.cost_sell_10 + ((self.pv_size_distribution[j]-10)*self.cost_sell_40)) / self.pv_size_distribution[j]),2)

                    else:   # Bigger than 40kW
                        self.cost_sell = round(((10*self.cost_sell_10 + 30*self.cost_sell_40 + (self.pv_size_distribution[j]-40)*self.cost_sell_100) / self.pv_size_distribution[j]),2)

                    # Save each house specific FIT in list
                    self.cost_sell_lst.append(self.cost_sell)

                # Defining df with FIT tarif for each pv system
                self.cost_sell_data_df = pd.DataFrame({i: [entry] * len(self.pv.power_ac_mc) for i, entry in enumerate(self.cost_sell_lst)})
                self.cost_sell_data_df.columns = pd.Index(self.cost_sell_data_df.columns, dtype='int64', name='houses')
                # Calculate simple mean value of all pv system specific
                data = self.cost_sell_data_df.values
                # Replace 0 with NaN
                data = np.where(data == 0, np.nan, data)
                # Calculate the mean of each row excluding NaNs
                mean_values_per_row = np.nanmean(data, axis=1)
                # Convert the result back to a DataFrame if needed
                self.cost_sell_data = pd.DataFrame(mean_values_per_row, columns=['Mean'])


            else:
                print('Electricity grid price modus not correctly defined!')


    def simulation_calculate(self):
        """Extract time dependent electricity cost for each timestep.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        """

        # Get cost for sell/buy of timestep
        self.cost_sell = self.cost_sell_data.values[self.time % len(self.cost_sell_data)]
        self.cost_sell_list.append(self.cost_sell)

        self.cost_buy = self.cost_buy_data.values[self.time % len(self.cost_buy_data)]
        self.cost_buy_list.append(self.cost_buy)


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
        self.model.blk_grid_electricity = pyo.Block()

        # Define parameters
        self.model.blk_grid_electricity.power_max = pyo.Param(initialize=self.power_max)
        self.model.blk_grid_electricity.cost_buy = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.cost_buy_list))
        self.model.blk_grid_electricity.cost_sell = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.cost_sell_list))

        # Define variables
        self.model.blk_grid_electricity.im_ex = pyo.Var(self.model.timeindex, domain=pyo.Binary)                                        # feed-out-->0, if feed-in-->1
        self.model.blk_grid_electricity.power_feed_out = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)                     # grid feed-out power
        self.model.blk_grid_electricity.power_feed_in = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)                      # grid feed-in power

        # Define constraints
        # Grid power max feed-out constraint
        def power_feed_out_max_rule(_b, t):
            return (_b.power_feed_out[t] + _b.im_ex[t] * _b.power_max <= _b.power_max)
        self.model.blk_grid_electricity.power_feed_out_max_c = pyo.Constraint(self.model.timeindex, rule=power_feed_out_max_rule)

        # Grid power max feed-in constraint
        def power_feed_in_max_rule(_b, t):
            return (_b.power_feed_in[t] - _b.im_ex[t] * _b.power_max <= 0)
        self.model.blk_grid_electricity.power_feed_in_max_c = pyo.Constraint(self.model.timeindex, rule=power_feed_in_max_rule)


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
        self.im_ex_list = list(self.model.blk_grid_electricity.im_ex.extract_values().values())
        self.power_feed_out_list = list(self.model.blk_grid_electricity.power_feed_out.extract_values().values())
        self.power_feed_in_list = list(self.model.blk_grid_electricity.power_feed_in.extract_values().values())

        ## Transfer opti results to sim sign convention
        self.power_list = list(np.array(self.power_feed_in_list)-np.array(self.power_feed_out_list))


    def get_economic_parameters(self):
        """Calculate the component specific FIT tariff for a neighborhood scenario where multiple systems are installed.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        cost_sell : float
            [1] House-specific FIT tariff dependent on PV size.

        Note
        ----
        """

        # For single building scenarios - SB
        if self.pv.eco_no_systems == 1:
            # [€$/kWp] Initialize specific capex
            self.capex_specific = (self.capex_p1 * (self.size_nominal/self.eco_no_systems)**self.capex_p2)
            # [€$/kWp] Initialize specific fixed opex
            self.opex_fix_specific = (self.opex_fix_p1 * self.capex_specific)
        # For neigborhood scenarios - NH
        else:
            # Get size distribution of PV systems in neighborhood
            self.size_nominal_distribution = self.nh_loader.get_pv_size_distribution()
            # Calculate specific capex distribution for different PV sizes
            self.capex_specific_distribution = [(self.capex_p1 * (self.size_nominal*j)**self.capex_p2) if j>0 else 0 for j in self.size_nominal_distribution]
            # [€$/kWp] Get NH specific capex as mean value of distribution
            self.capex_specific =  np.mean([i for i in self.capex_specific_distribution if i != 0])
            # [€$/kWp] Initialize specific fixed opex
            self.opex_fix_specific = (self.opex_fix_p1 * self.capex_specific)
