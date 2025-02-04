import pandas as pd
import numpy as np
import statistics
import scipy
from scipy import stats


class Performance():
    """
    Provides all relevant methods for the technical performance evaluation

    Methods
    -------

     Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.

    Returns
    -------
    None : `None`

    Note
    ----
    - For all annual values the provided data neeeds to have a length of 1 year!!!
    """

    def __init__(self, timestep):

        self.timestep = timestep


    def fct_day_profile(self, data):
        """
        Calculate day arrays over full year operation
        Input data is always resampled to 1H timestep

        Parameters
        ----------
        data : `pd.Series`
            [1] input data as timeseries over 1 year

        Returns
        -------
        data_dayarray : `np.array`
            [1] 2d numpy array with day timeseries of input data

        data_day_max : `list`
            [1] list of input data daily max value

        data_day_min: `list`
            [1] list of input data daily min value

        Note
        ----
        - Function can compute pandas.Series and also pandas.DataFrame with multiple columns at once.
        """

        # Include data
        self.data = data
        # resample to hourly
        self.data = self.data.resample('H').mean()

        # Split series into day arrays and save it in 2d array
        self.data_dayarray = np.array(np.array_split(np.array(self.data),
                                                     int((len(self.data))/24)))

        # Find max/min values of each day array
        self.data_day_max  = list()
        self.data_day_min  = list()

        for i in range(0,len(self.data_dayarray)):
            self.data_day_max.append(max(self.data_dayarray[i][:]))
            self.data_day_min.append(min(self.data_dayarray[i][:]))

        return (self.data_dayarray, self.data_day_max, self.data_day_min)


    def fct_source_eva(self, data_source, data_grid):
        """
        Calculate following performance indicators of sources, which can be PV or WT:
            - PV/WT annual production
            - PV/WT self-consumption rate as direct use and no direct use

        Parameters
        ----------
        data_source : `pd.Series` or `pd.DataFrame`
            [kW] containing PV/WT AC power (can be hourly or 15min values or others)

        data_grid : `pd.Series` or `pd.DataFrame`
            [kW] containing electricity grid AC power (can be hourly or 15min values or others)

        Returns
        -------
        energy_overall_kWh_a : `float`
            [kWh/a] Annual total source production
        share_direct use : `float`
            [1] Share of direct use source generation
        share_non_direct use : `float`
            [1] Share of non direct use source generation

        Note
        ----
        - Direct use means Pv energy can be used directly by load or saved in storage technology, for NH scenario it includes sharing via grid
        - Incase multiple sources are considered data_source needs to be power timeseries of all componnets combined!
        """

        # Include data
        self.data_source = data_source
        self.data_grid = data_grid

        # Resample input data to hours (W --> Wh)
        self.data_source.resample('H').mean()
        self.data_grid.resample('H').mean()

        # Annual pv production [kWh/a]
        self.energy_overall_kWh_a = sum(np.asarray(self.data_source)) / (len(self.data_source)/8760)

        # Take only grid feed-in
        self.data_grid_feed_in = self.data_grid.clip(lower=0)

        # Calculate direct use of local generated energy [Wh] and share of it
        self.power_direct_use = [(l1 - l2) for l1, l2 in zip(self.data_source, self.data_grid_feed_in)]
        self.share_direct_use = sum(self.power_direct_use) / self.data_source.sum()
        # Calculate non direct use of local generated energy [Wh] and share of it
        self.power_non_direct_use = [x1 - x2 for (x1, x2) in zip(self.data_source, self.power_direct_use)]
        self.share_non_direct_use = sum(self.power_non_direct_use) / self.data_source.sum()


    def fct_storage_soc_eva(self, data):
        """
        Calculate SoC day arrays from

        Parameters
        ----------
        data : `pd.Series`
            [1] storage SoC data as timeseries over 1 year

        Returns
        -------
        soc_dayarray : `np.array`
            [1] 2d numpy array with SoC day timeseries

        soc_day_max : `list`
            [1] list of SoC daily max value

        soc_day_min: `list`
            [1] list of SoC daily min value

        Note
        ----
        - Function can compute pandas.Series and also pandas.DataFrame with multiple columns at once.
        """

        ## Include data
        self.storage_soc = data

        # Call day profile function
        self.soc_dayarray = self.fct_day_profile(self.storage_soc)[0]
        self.soc_day_max = self.fct_day_profile(self.storage_soc)[1]
        self.soc_day_min = self.fct_day_profile(self.storage_soc)[2]


    def fct_storage_energy_eva(self, data_soc, data_capacity):
        """
        Calculate yearly and mean dayly stored energy and number of charge cycles per year

        Parameters
        ----------
        data_soc : `pd.Series`
            [-] power data as timeseries over 1 year
        data_capacity : `pd.Series`
            [kWh] total capacity of storage

        Returns
        -------
        energy_year : `float`
            [kWh] Total energy stored per year
        energy_day : `float`
            [kWh] Mean energy stored per day

        Note
        ----
        - The energy year represents the energy charged/discharged from the storage
        - It is NOT the sum of charged and discharged energy!
        """

        ## Include data
        self.storage_soc = data_soc
        self.storage_capacity = data_capacity

        # Cycled energy per year/day
        self.energy = 0
        for i in range(0, len(self.storage_soc)-1):
            # Calculate stored energy per timestep in kWh
            self.energy += abs(self.storage_soc[i] - self.storage_soc[i+1]) * self.storage_capacity

        # Calculate stored energy per year and day (/2 to account only for charged energy)
        self.energy_year = self.energy / 2
        self.energy_day = self.energy_year / (len(self.storage_soc) * (self.timestep/3600) / 24)

        # Calculate charge cycles per year
        self.charge_cycles_year = self.energy_year / self.storage_capacity


    def fct_roundtrip_eff(self, data_ch, data_dch):
        """
        Calculate roundtrip efficiency of storage system

        Parameters
        ----------
        data_ch : `pd.Series`
            [-] charge power data, as input to storage system
        data_dch : `pd.Series`
            [kWh] discharge power data, as output of storage system

        Returns
        -------
        eff_roundtrip : `float`
            [1] Roundtrip efficiency
        energy_loss : `float`
            [kWh] Energy loss over considered timeframe
        """

        # Include data
        self.data_ch = data_ch
        self.data_dch = data_dch

        # Calculate roundtrip efficiency
        self.eff_roundtrip = self.data_dch.resample('H').mean().sum() /self.data_ch.resample('H').mean().sum()

        # Calculate energy loss
        self.energy_loss = self.data_ch.resample('H').mean().sum()- self.data_dch.resample('H').mean().sum()


    def fct_runtime_eva(self, data):
        """
        Caluclate the runtime of any component

        Parameters
        ----------
        data : `pd.Series` or `pd.DataFrame`
            [kW] Power timeseries of single component (pd.Series) or multiple components with each component one column (pd.df)

        Returns
        -------
        operation_hours_a : `pd.Series`
            [h/a] Annual operation hours of all components considered in data
        """

        # Include data
        self.data = data

        # Resample input data to hours (W --> Wh)
        #self.data.resample('H').mean()

        # Calculate runtime in h (Count number of non zero values)
        self.operation_hours_a = self.data.astype(bool).sum(axis=0) * (self.timestep/3600)


    def fct_runtime_eva_cyclelength(self, data):
        """
        Compute length of all operation cycles over simulation timeframe.

        Parameters
        ----------
        data : `pd.Series`
            Contains hourly power values of 1 year operation with DateTimeIndex of single component

        Returns
        -------
        operation_cyclelength : `pd.Series`
            [] Series containing the length of each operation cycle

        Note
        ----
        - DataFrame need to have DateTimeIndex
        - If power values are not 0, operation of component is considered!
        """

        # Include data
        self.data = data.copy()

        # Repalce all non zero values with 1
        self.data[self.data!= 0] = 1

        # Define counter for operaton length per cycle
        num1 = 0
        # Define list to store length of all operation cycles
        self.data_result = []

        # Loop over length of df
        for i in range(len(self.data)):
          if(self.data.iloc[i])==0:
              if self.data.iloc[i-1] == 0:
                  pass
              else:
                  self.data_result.append(num1)
                  num1 = 0
          if(self.data.iloc[i])==1:
              num1 = num1+1

        # Convert result data to pd.Series
        self.operation_cyclelength = pd.Series(self.data_result)


    def fct_peak_power(self, data):
        """
        Compute peak power of provided component data over considered timeframe

        Parameters
        ----------
        data : `pd.Series`
            [kW] Power timeseries of component

        Returns
        -------
        peak_power : `float`
            [] Peak power of power timeseries

        Note
        ----
        """

        # Include data
        self.data = data

        # Calculate peak power
        self.peak_power = self.data.max()


    def fct_grid_eva(self, data):
        """
        Compute:
            - dayarray of grid power
            - grid feed-in/out daily distribution
            - grid annual load curve

        Parameters
        ----------
        data : `pd.Series`
            [kW] Grid power timeseries

        Returns
        -------
        annual_load_curve : `pd.Series
            [] Sorted annual power curve
        annual_import_curve : `pd.Series
            [] Sorted annual grid import (feed-out) power curve
        annual_export_curve : `pd.Series
            [] Sorted annual grid export (feed-in) power curve

        feed_in_energy_total : `float`
            [kWh] Total grid feed-out energy
        feed_out_energy_total : `float`
            [kWh] Total grid feed-in energy
        grid_energy_balance : `float`
            [kWh] Grid energy balance

        power_dayarray : `np.array`
            [1] 2d numpy array with day timeseries of grid power

        feed_in_dist_d : `list`
            [] Normalized (to total feed in energy) feed-in power over day
        feed_in_dist_d_mean : `list`
            [] Mean feed-in power over day
        feed_in_dist_d_max : `list`
            [] Max feed-in power of each hour of the day over year
        feed_in_dist_d_min : `list`
            [] Min feed-in power of each hour of the day over year
        feed_in_dist_d_mean : `list`
            [] Mean feed-in power over day
        feed_in_dist_stdv : `list`
            [] Standard deviation of feed-in power over day
        feed_in_dist_ki : `np.array`
            [] Arry with lower and upper bound of confidence interval of feed-in power over day

        feed_out_dist_d : `list`
            [] Normalized (to total feed in power) feed-out power over day
        feed_out_dist_d_mean : `list`
            [] Mean feed-out power over day
        feed_out_dist_d_max : `list`
            [] Max feed-out power of each hour of the day over year
        feed_out_dist_d_min : `list`
            [] Min feed-out power of each hour of the day over year
        feed_out_dist_stdv : `list`
            [] Standard deviation of feed-out power over day
        feed_out_dist_ki : `np.array`
            [] Arry with lower and upper bound of confidence interval of feed-out power over day

        Note
        ----
        - Grid power feed-in considered positive (+) and feed-out negative (-)
        - Can be used with various temporal resolution
        - Parameters could also be normalized to installed peak power for comparision of different system sizes
        """

        # Ignore scipy warning of function scipy.stats.norm.interval() when Ki shall be computed for mean value of 0.
        import warnings
        warnings.filterwarnings("ignore", message="invalid value encountered in multiply")

        # Include data
        self.data = data

        ## Calculate annual load curve
        self.annual_load_curve = self.data.sort_values(ascending=False, ignore_index=True)

        ## Calculate annual grid power feed-in (export) and feed-out (import) curve
        self.annual_import_curve = abs(self.data[self.data<0].sort_values(ascending=False, ignore_index=True))
        self.annual_export_curve = self.data[self.data>0].sort_values(ascending=False, ignore_index=True)

        ## Calculate grid total feed-in energy
        self.feed_in_energy_total = sum([x for x in self.data.resample('H').mean() if x > 0]) / (len(self.data.resample('H').mean())/8760)
        self.feed_out_energy_total = sum([x for x in self.data.resample('H').mean() if x < 0]) / (len(self.data.resample('H').mean())/8760)
        self.energy_balance = sum([x for x in self.data.resample('H').mean()])

        ## Split series into day arrays and save it in 2d array
        #self.power_dayarray = self.fct_day_profile(self.data)[0]
        if self.data.index[1] - self.data.index[0] == pd.Timedelta(minutes=60):
            self.power_dayarray = np.array(np.array_split(np.array(self.data),
                                                         int((len(self.data))/24)))
        elif self.data.index[1] - self.data.index[0] == pd.Timedelta(minutes=15):
            self.power_dayarray = np.array(np.array_split(np.array(self.data),
                                                         int((len(self.data))/4/24)))

        ## Daily distribution of grid feed-in and feed-out
        self.power_dist_d = list()
        self.power_dist_d_min = list()
        self.power_dist_d_max = list()
        self.power_dist_d_mean = list()
        self.power_dist_d_stdv = list()
        self.power_dist_d_ki = list()

        self.feed_in_dist_d = list()
        self.feed_in_dist_d_max = list()
        self.feed_in_dist_d_min = list()
        self.feed_in_dist_d_mean = list()
        self.feed_in_dist_d_stdv = list()
        self.feed_in_dist_d_ki = list()

        self.feed_out_dist_d = list()
        self.feed_out_dist_d_max = list()
        self.feed_out_dist_d_min = list()
        self.feed_out_dist_d_mean = list()
        self.feed_out_dist_d_stdv = list()
        self.feed_out_dist_d_ki = list()

        # Define considered confidence interval
        KI_interval = 0.95

        # Calculate for each dayhour of year
        for i in range(0,self.power_dayarray.shape[1]):
            # If only zeros - no calculation
            if all(x==0 for x in self.power_dayarray[:,i]):
                self.power_dist_d.append(0)
                self.power_dist_d_min.append(0)
                self.power_dist_d_max.append(0)
                self.power_dist_d_mean.append(0)
                self.power_dist_d_stdv.append(0)

                self.feed_in_dist_d.append(0)
                self.feed_in_dist_d_max.append(0)
                self.feed_in_dist_d_min.append(0)
                self.feed_in_dist_d_mean.append(0)
                self.feed_in_dist_d_stdv.append(0)

                self.feed_out_dist_d.append(0)
                self.feed_out_dist_d_max.append(0)
                self.feed_out_dist_d_min.append(0)
                self.feed_out_dist_d_mean.append(0)
                self.feed_out_dist_d_stdv.append(0)

            # Separation of feed-in and feed-out calculation
            else:
                self.power_dist_d.append(sum([x for x in self.power_dayarray[:,i]]) / sum([x for x in self.data]))
                try:
                    self.feed_in_dist_d.append(sum([x for x in self.power_dayarray[:,i] if x > 0])
                                               / sum([x for x in self.data if x > 0]))
                except: # if no feed-in at all -> ZeroDivisionError
                    self.feed_in_dist_d.append(None)
                try:
                    self.feed_out_dist_d.append(sum([x for x in self.power_dayarray[:,i] if x < 0])
                                                / sum([x for x in self.data if x < 0]))
                except: # if no feed-out at all -> ZeroDivisionError
                    self.feed_out_dist_d.append(None)
                self.power_dist_d_min.append(min([x for x in self.power_dayarray[:,i]]))
                self.power_dist_d_max.append(max([x for x in self.power_dayarray[:,i]]))
                self.power_dist_d_mean.append(statistics.mean([x for x in self.power_dayarray[:,i]]))
                self.power_dist_d_stdv.append(statistics.stdev([x for x in self.power_dayarray[:,i]]))


                ## Feed-in
                # Calculate hourly mean value of day array
                try:
                    self.feed_in_dist_d_mean.append(statistics.mean([x for x in self.power_dayarray[:,i] if x > 0]))
                except:
                    self.feed_in_dist_d_mean.append(0)
                # Calculate hourly stdv of day array
                try:
                    self.feed_in_dist_d_stdv.append(statistics.stdev([x for x in self.power_dayarray[:,i] if x > 0]))
                except:
                    self.feed_in_dist_d_stdv.append(0)
                # Calculate hourly max value of day array
                try:
                    self.feed_in_dist_d_max.append(max([x for x in self.power_dayarray[:,i] if x > 0]))
                except:
                    self.feed_in_dist_d_max.append(0)
                # Calculate hourly min value of day array
                try:
                    self.feed_in_dist_d_min.append(min([x for x in self.power_dayarray[:,i] if x > 0]))
                except:
                    self.feed_in_dist_d_min.append(0)

                ## Feed-out
                # Calculate hourly mean value of day array
                try:
                    self.feed_out_dist_d_mean.append(abs(statistics.mean([x for x in self.power_dayarray[:,i] if x < 0])))
                except:
                    self.feed_out_dist_d_mean.append(0)
                # Calculate hourly stdv of day array
                try:
                    self.feed_out_dist_d_stdv.append(statistics.stdev([x for x in self.power_dayarray[:,i] if x < 0]))
                except:
                    self.feed_out_dist_d_stdv.append(0)
                # Calculate hourly max value of day array
                try:
                    self.feed_out_dist_d_max.append(abs(max([x for x in self.power_dayarray[:,i] if x < 0])))
                except:
                    self.feed_out_dist_d_max.append(0)
                # Calculate hourly min value of day array
                try:
                    self.feed_out_dist_d_min.append(abs(min([x for x in self.power_dayarray[:,i] if x < 0])))
                except:
                    self.feed_out_dist_d_min.append(0)

        # Calculate confidence interval and replace all nan with 0 (nan result from cal with mean of 0)
        self.power_dist_d_ki.append(np.nan_to_num(scipy.stats.norm.interval(alpha=KI_interval,
                                                                            loc=self.power_dist_d_mean,
                                                                            scale=self.power_dist_d_stdv)))
        self.feed_in_dist_d_ki.append(np.nan_to_num(scipy.stats.norm.interval(alpha=KI_interval,
                                                                              loc=self.feed_in_dist_d_mean,
                                                                              scale=self.feed_in_dist_d_stdv)))
        self.feed_out_dist_d_ki.append(np.nan_to_num(scipy.stats.norm.interval(alpha=KI_interval,
                                                                               loc=self.feed_out_dist_d_mean,
                                                                               scale=self.feed_out_dist_d_stdv)))

        self.power_dist_d_perc_1 = (np.percentile(self.power_dayarray, 1, axis=0))
        self.power_dist_d_perc_99 = (np.percentile(self.power_dayarray, 99, axis=0))
        self.power_dist_d_perc_5 = (np.percentile(self.power_dayarray, 5, axis=0))
        self.power_dist_d_perc_95 = (np.percentile(self.power_dayarray, 95, axis=0))


    def fct_grid_seasonal_eva(self, data):
        """
        Convert annual timeseries into mean seasonal dayprofile.
        Further computer standard deviation and confidence interval.
        Can be used for power values or gradient values or others.

        Parameters
        ----------
        data : `pd.DataFrame`
            [kW] contains power values of 1 year operation with dateTimeIndex

        Returns
        -------
        data_seasonal : `pd.DataFrame`
            [] DataFrame containing for each month the mean and stdv day profile

        Note
        ----
        - DataFrame need to have DateTimeIndex
        - Should have only single column (which holds the power values), not multiple!
        - Can be used with various temporal resolution
        """

        # Include data
        self.data = data

        # Define KI Interval
        KI_interval = 0.90

        # Add year, month, day and hour of each timestep to df
        self.data["Year"]  = self.data.index.year
        self.data['Month']  = self.data.index.month
        self.data['Day']  = self.data.index.day_name()
        self.data['Hour']  = self.data.index.hour

        # Define season months
        winter_months = [12,1,2]
        spring_months = [3,4,5]
        summer_months = [6,7,8]
        automn_months = [9,10,11]

        # Create individual dfs for each season
        self.data_winter = self.data[self.data.index.map(lambda t: t.month in winter_months)]
        self.data_spring = self.data[self.data.index.map(lambda t: t.month in spring_months)]
        self.data_summer = self.data[self.data.index.map(lambda t: t.month in summer_months)]
        self.data_automn = self.data[self.data.index.map(lambda t: t.month in automn_months)]

        # Calculate mean and stdv and Confidence Interval of day hours of each season and save it to result df
        self.winter_mean = self.data_winter.groupby([self.data_winter.index.hour]).mean().iloc[:,0]
        self.winter_stdv = self.data_winter.groupby([self.data_winter.index.hour]).std().iloc[:,0]
        self.winter_KI = scipy.stats.norm.interval(alpha=KI_interval,
                                                   loc=self.winter_mean,
                                                   scale=self.winter_stdv)
        self.spring_mean = self.data_spring.groupby([self.data_spring.index.hour]).mean().iloc[:,0]
        self.spring_stdv = self.data_spring.groupby([self.data_spring.index.hour]).std().iloc[:,0]
        self.spring_KI = scipy.stats.norm.interval(alpha=KI_interval,
                                                   loc=self.spring_mean,
                                                   scale=self.spring_stdv)
        self.summer_mean = self.data_summer.groupby([self.data_summer.index.hour]).mean().iloc[:,0]
        self.summer_stdv = self.data_summer.groupby([self.data_summer.index.hour]).std().iloc[:,0]
        self.summer_KI = scipy.stats.norm.interval(alpha=KI_interval,
                                                   loc=self.summer_mean,
                                                   scale=self.summer_stdv)
        self.automn_mean = self.data_automn.groupby([self.data_automn.index.hour]).mean().iloc[:,0]
        self.automn_stdv = self.data_automn.groupby([self.data_automn.index.hour]).std().iloc[:,0]
        self.automn_KI = scipy.stats.norm.interval(alpha=KI_interval,
                                                   loc=self.automn_mean,
                                                   scale=self.automn_stdv)

        # Result
        self.data_seasonal = pd.DataFrame(data={'winter_mean': self.winter_mean,
                                                'winter_stdv': self.winter_stdv,
                                                'winter_KI_low': self.winter_KI[0],
                                                'winter_KI_top': self.winter_KI[1],
                                                'spring_mean': self.spring_mean,
                                                'spring_stdv': self.spring_mean,
                                                'spring_KI_low': self.spring_KI[0],
                                                'spring_KI_top': self.spring_KI[1],
                                                'summer_mean': self.summer_mean,
                                                'summer_stdv': self.summer_mean,
                                                'summer_KI_low': self.summer_KI[0],
                                                'summer_KI_top': self.summer_KI[1],
                                                'automn_mean': self.automn_mean,
                                                'automn_stdv': self.automn_mean,
                                                'automn_KI_low': self.automn_KI[0],
                                                'automn_KI_top': self.automn_KI[1],
                                                })



    def fct_grid_gradient_eva(self, data):
        """
        Compute daily grid power gradients and its distribution

        Parameters
        ----------
        data : `pd.Series`
            [kW/t] Grid power timeseries in kW per timestep

        Returns
        -------
        power_gradient : `list`
            [W] Grid power gradient
        power_gradient_dist_d : `list`
            [] Nornalized grid power gradient over day
        power_gradient_dist_d_mean : `list`
            [] Mean of grid power gradient over day
        power_gradient_dist_d_stdv : `list`
            [] Stdv of grid power gradient over day
        power_gradient_dist_d_ki : `list`
            [] 90% confidence interval of grid power gradient over day

        Note
        ----
        - Can be used with various temporal resolution
        """

        # Include data
        self.data = data

        # Caluclate power gradient
        self.power_gradient = list()
        for i in range(0,len(self.data)-1):
            self.power_gradient.append(self.data[i+1]-self.data[i])
        self.power_gradient.append((0-self.data[-1]))

        # Split power gradient into day arrays and save it in 2d array
        self.power_gradient_dayarray = self.fct_day_profile(self.power_gradient)[0]

        # Calculate power gradient distribution (normalized, mean, stdv, KI90)
        KI_interval = 0.9
        self.power_gradient_dist_d = list()
        self.power_gradient_dist_d_mean = list()
        self.power_gradient_dist_d_stdv = list()
        self.power_gradient_dist_d_ki = list()

        for i in range(0,self.power_gradient_dayarray.shape[1]):
            self.power_gradient_dist_d.append(sum([x for x in self.power_gradient_dayarray[:,i]])
                                              / sum([abs(ele) for ele in self.power_gradient]))
            self.power_gradient_dist_d_mean.append(statistics.mean([x for x in self.power_gradient_dayarray[:,i]]))
            self.power_gradient_dist_d_stdv.append(statistics.stdev([x for x in self.power_gradient_dayarray[:,i]]))

        # Calculate confidence interval and replace all nan with 0 (nan result from cal with mean of 0)
        self.power_gradient_dist_d_ki.append(np.nan_to_num(scipy.stats.norm.interval(alpha=KI_interval,
                                                                              loc=self.power_gradient_dist_d_mean,
                                                                              scale=self.power_gradient_dist_d_stdv)))


    def fct_grid_power_bins_eva(self, data, bins, labels):
        """
        Compute distribution of feed-in and feed-out power
        categorized into bins and dependent on total feed-in/out energy

        Parameters
        ----------
        data : `pd.DataFrame`
            [kW] Grid power timeseries

        Returns
        -------
        energy_share_feed_in = `pd.DataFrame`
            [] Containing two columns with feed-in power bins and energy content of each power bin

        energy_share_feed_out = `pd.DataFrame`
            [] Containing two columns with feed-out power bins and energy content of each power bin

        Note
        ----
        """

        # Include data
        self.data = data
        self.bins = bins
        self.labels = labels

        # Get data into own df and resample  to hours (W --> Wh)
        x = self.data.resample('H').mean()

        # Sort values
        self.x_sort = x.sort_values(by='grid_power', axis=0, ascending=True)

        # Bin data
        self.x_sort['bins'] = pd.cut(x=self.x_sort['grid_power'],
                                     bins=self.bins,
                                     labels=self.labels,
                                     include_lowest=True)

        # Create df with positive and negative binned values
        self.x_sort_feed_in = self.x_sort[self.x_sort.grid_power > 0].copy()
        self.x_sort_feed_out = self.x_sort[self.x_sort.grid_power < 0].copy()

        # Calculate energy share of each datapoint
        self.x_sort_feed_in['e_share'] = self.x_sort_feed_in['grid_power'] / self.x_sort_feed_in['grid_power'].sum()
        self.x_sort_feed_out['e_share'] = self.x_sort_feed_out['grid_power'] / self.x_sort_feed_out['grid_power'].sum()

        # Sum energy share of each bin and append to list
        self.e_share_bin_feed_in = list()
        for i in range(0, len(self.x_sort_feed_in.bins.unique())):
            self.e_share_bin_feed_in.append(self.x_sort_feed_in.loc[self.x_sort_feed_in.bins==self.x_sort_feed_in.bins.unique()[i], 'e_share'].sum())

        self.e_share_bin_feed_out = list()
        for i in range(0, len(self.x_sort_feed_out.bins.unique())):
            self.e_share_bin_feed_out.append(self.x_sort_feed_out.loc[self.x_sort_feed_out.bins==self.x_sort_feed_out.bins.unique()[i], 'e_share'].sum())

        # Result df composes of bin and energy share of each bin
        self.energy_share_feed_in = pd.DataFrame({'bins': self.x_sort_feed_in.bins.unique(),
                                                  'e_share_bin': self.e_share_bin_feed_in})

        self.energy_share_feed_out = pd.DataFrame({'bins': self.x_sort_feed_out.bins.unique(),
                                                   'e_share_bin': self.e_share_bin_feed_out})


    def fct_grid_interaction_indiactor_Lu(self, data_load, data_grid):
        """
        Compute Grid Interaction Index, as Stdv of net exported energy to Stdv of load profile
        According to Lu_2015

        Parameters
        ----------
        data_load : `pd.DataFrame` or `pd.Series`
            [kW] Total el load power (direct electricity load, heat pump electricity and e-mobility)

        data_grid : `pd.DataFrame` or `pd.Series`
            [kW] Grid power timeseries


        Returns
        -------
        GII : `float`
            [1] Grid Interaction Index

        Note
        ----
        - Source: Lu: Renewable energy system optimization of low/zero energy buildings using single-objective and multi-objective optimization methods, 2015
        - Net export energy: export +, import -
        """

        # Include data
        self.data_load = data_load
        self.data_grid = data_grid

        # Calculate Building Grid Interaction (BGI) Index
        self.bgi_lu = (self.data_grid) / (self.data_load)

        # Calculate Grid Interaction Index (GII)
        self.gii_lu = statistics.stdev([x for x in self.bgi_lu])


    def fct_grid_interaction_indiactor_McK(self, data_load, data_grid):
        """
        Compute Grid Interaction Index, as Stdv of net exported energy
        and Grid Interaction Index, as Stdv of net exported energy referred to as Stdv of electricity load

        Parameters
        ----------
        data_load : `pd.DataFrame` or `pd.Series`
            [kW] Total load power (direct electricity load, heat pump electricity and e-mobility)

        data_grid : `pd.DataFrame` or `pd.Series`
            [kW] Grid power timeseries


        Returns
        -------
        gii_McK : `float`
            [1] Grid Interaction Index according to Mc Kenna_2017
        gii_ref McK : `float`
            [1] Reference Grid Interaction Index according to Mc Kenna_2017
        Note
        ----
        - Source: McKenna: Energy autonomy in residential buildings: A techno-economic model-based analysis of the scale effects, 2017
        """

        # Include data
        self.data_load = data_load
        self.data_grid = data_grid

        # Calculate GII
        self.gii_McK = statistics.stdev((data_grid) / max(abs(data_grid)))

        # Calculate GII ref, normalized to Stdv of load
        self.gii_ref_McK = self.gii_McK / statistics.stdev((data_load) / max(abs(data_load)))


    def fct_grid_interaction_indiactor_sato(self, data_load, data_grid):
         """
         Compute Grid Interaction Index

         Parameters
         ----------
         data_load : `pd.DataFrame` or `pd.Series`
             [kW] Total load power (direct electricity load, heat pump electricity and e-mobility)

         data_grid : `pd.DataFrame` or `pd.Series`
             [kW] Grid power timeseries

         Returns
         -------
         GII : `float`
             [1] Grid Interaction Index

         Note
         ----
         - Indicator is based on Sato_2020, which argues that cost of transmission is mainly influenced by infrastructure investment,
           therefore regarding maximum power exchange rather than total energy exchanged
         - Electric power from heat pump needs to be static and independent from operation to compare different operation modes
             - Therefore maximum value of thermal power/cop tiomeseries should be used!
         """

         # Include data
         self.data_load = data_load
         self.data_grid = data_grid

         # Calculate Grid Interaction Index
         self.gii_sato = max(abs(self.data_grid)) / max(self.data_load)


    def fct_self_sufficiency(self, data_load, data_grid):
        """
        Compute total level self-sufficiency

        Parameters
        ----------
        data_load : `pd.DataFrame` or `pd.Series`
            [kW] Total load power

        data_grid : `pd.DataFrame` or `pd.Series`
            [kW] Grid power timeseries

        Returns
        -------
        self-sufficiency : `float`
            [] Level of self-sufficiency (1 all energy demands are covered by local energy, 0 all energy demands are covered by grid energy)

        Note
        ----
        - According to Weniger et al: Dezentrale Solarstromspeicher für die Energiewende, 2015
        - In case of a elecricity-heat-cold carrier system, which is solely supplied by heat pumps,
          the total load power is the sum of direct electricity demand and heat pump consumed electricity power
        """

        # Include data
        self.data_load = data_load
        self.data_grid = data_grid

        # Get grid feed-out timeseries
        self.data_grid_feed_out = abs(self.data_grid[self.data_grid< 0].copy())

        # Calculate level of self-sufficiency
        self.self_sufficiency = ((self.data_load.sum() - self.data_grid_feed_out.sum()) / self.data_load.sum())


    def fct_self_consumption(self, data_source, data_grid):
        """
        Compute total level of self-consumption

        Parameters
        ----------
        data_source : `pd.DataFrame` or `pd.Series`
            [kW] Total generation power

        data_grid : `pd.DataFrame` or `pd.Series`
            [kW] Grid power timeseries

        Returns
        -------
        self-consumption : `float`
            [1] Level of self-consumption (1 all local energy is consumed locally, 0 no local energy is consumed locally)

        Note
        ----
        - According to Weniger et al: Dezentrale Solarstromspeicher für die Energiewende, 2015
        """

        # Include data
        self.data_source = data_source
        self.data_grid = data_grid

        # Take only grid feed-in
        self.data_grid_feed_in = self.data_grid.clip(lower=0)

        # Calculate direct use of local generated energy [Wh] and share of it
        self.power_direct_use = [(l1 - l2) for l1, l2 in zip(self.data_source, self.data_grid_feed_in)]
        self.share_direct_use = sum(self.power_direct_use) / self.data_source.sum()

        # Self-consumption
        self.self_consumption = self.share_direct_use



    def electricity_balance(self,
                            data_pv,
                            data_load_el,
                            data_hp_power_el,
                            data_grid,
                            data_bat=0,
                            data_ely=0,
                            data_fc=0):
        """
        Compute electricity energy balance

        Parameters
        ----------
        data_pv : `pd.DataFrame` or `pd.Series`
            [kW] Pv output power
        data_load_el : `pd.DataFrame` or `pd.Series`
            [kW] Electricity load power
        data_hp_power_el : `pd.DataFrame` or `pd.Series`
            [kW] HP electric power input
        data_grid : `pd.DataFrame` or `pd.Series`
            [kW] Electricity grid power (feed-in+, feed-out-)
        data_bat : `pd.DataFrame` or `pd.Series`
            [kW] Bat power (charge+, discharge-)
        data_ely : `pd.DataFrame` or `pd.Series`
            [kW] Electrolyzer electric power
        data_fc : `pd.DataFrame` or `pd.Series`
            [kW] Fuelcell electric power

        Returns
        -------
        balance_el : `float`
            [kW] electricity balance power
        """

        self.data_pv = data_pv
        self.data_load_el = data_load_el
        self.data_hp_power_el = data_hp_power_el
        self.data_grid = data_grid

        self.data_bat = data_bat
        self.data_ely = data_ely
        self.data_fc = data_fc

        if type(self.data_bat) == int:
            self.data_bat = 0*self.data_pv
        if type(self.data_ely) == int:
            self.data_ely = 0*self.data_pv
        if type(self.data_fc) == int:
            self.data_fc = 0*self.data_pv

        # Calculate electricity energy balance
        self.balance_el = (self.data_pv.resample('H').mean().sum()
                           -self.data_load_el.resample('H').mean().sum()
                           -self.data_hp_power_el.resample('H').mean().sum()
                           +abs(self.data_grid[self.data_grid<0].resample('H').mean().sum())
                           -abs(self.data_grid[self.data_grid>0].resample('H').mean().sum())
                           -abs(self.data_bat[self.data_bat>0].resample('H').mean().sum())
                           +abs(self.data_bat[self.data_bat<0].resample('H').mean().sum())
                           -self.data_ely.resample('H').mean().sum()
                           +self.data_fc.resample('H').mean().sum()
                           )


def apply_performance_singlevalue(data, metadata, timestep):
    """
    Apply performance class to hdf5 data and add single value performance indicators to meta_data

    Parameters
    ----------
    data : `pd.DataFrame`
        [kW] Columns holding all timeseries output of system MILP
    metadata : `dictionary`
        [-] Metadata doctionary with component sizes
    timestep : `int`
        [s] Timestep of model results

    Returns
    -------
    perf_indicators : `dictionary`
        [-] All single value performance indicators

    Note
    ----
    """

    # indlucde function arguments
    data = data
    metadata = metadata

    # timestep of hdf5 file in seconds
    timestep = timestep

    # initialize performance class
    perf = Performance(timestep=timestep)

    # create empty dict to store all single value performance indicators
    perf_indicators = {}

    ##Load types
    perf_indicators['load'] = {}
    perf_indicators['load']['load_peak_load_el'] = max(data.load_el_power)
    perf_indicators['load']['load_peak_load_th_h'] = max(data.load_th_h_power)
    perf_indicators['load']['load_sum_load_el'] = (data.load_el_power.resample('H').mean().sum())
    perf_indicators['load']['load_sum_load_th_h'] = (data.load_th_h_power.resample('H').mean().sum())

    if 'hp_power_el' in data.columns:
        perf_indicators['load']['load_sum_hp_power_el'] = (data.hp_power_el.resample('H').mean().sum())
        perf_indicators['load']['load_peak_hp_power_el'] = max(data.hp_power_el)

    ##PV
    # Call pv evaluation function
    perf.fct_source_eva(data_source=data.pv_power,
                        data_grid=data.grid_power)
    # PV annual production, PV (Non) direct use of energy
    perf_indicators['pv'] = {'pv_annual_yield': perf.energy_overall_kWh_a,
                             'pv_peak_power': max(data.pv_power),
                             'pv_share_direct_use': perf.share_direct_use,
                             'pv_share_non_direct_use': perf.share_non_direct_use}

    ##Grid
    perf_indicators['grid'] = {}
    # Grid max feed-in and feed-out power
    perf.fct_peak_power(data['grid_power'][data['grid_power']>0])
    perf_indicators['grid']['grid_peak_power_feed_in'] = perf.peak_power
    perf.fct_peak_power(abs(data['grid_power'][data['grid_power']<0]))
    perf_indicators['grid']['grid_peak_power_feed_out'] = perf.peak_power

    # Grid annual feed-in / feed-out
    perf.fct_grid_eva(data['grid_power'])
    perf_indicators['grid']['grid_energy_feed_in'] = perf.feed_in_energy_total
    perf_indicators['grid']['grid_energy_feed_out'] = perf.feed_out_energy_total

    # Grid Interaction Indicator (Own definition!)
    # Without HP_el load consideration
    perf.fct_grid_interaction_indiactor_sato(data_load=data.load_el_power,
                                              data_grid=data.grid_power)
    perf_indicators['grid']['grid_gii_sato'] = perf.gii_sato

    # Grid Interaction indicator according to McKenna
    # Without HP_el load consideration
    perf.fct_grid_interaction_indiactor_McK(data_load=data.load_el_power,
                                            data_grid=data.grid_power)
    perf_indicators['grid']['grid_gii_ref_McK'] = perf.gii_ref_McK

    # Grid Interaction indicator according to Lu
    # Without HP_el load consideration
    perf.fct_grid_interaction_indiactor_Lu(data_load=data.load_el_power,
                                            data_grid=data.grid_power)
    perf_indicators['grid']['grid_gii_ref_Lu'] = perf.gii_lu

    ## Components tramsformers
    perf_indicators['components_transformers'] = {}
    # Operation hours and peak power of transformers - HEAT PUMP
    if 'hp_power_el' in data.columns:
        perf.fct_runtime_eva(data[['hp_power_el']])
        perf_indicators['components_transformers']['hp_operation_hours'] = perf.operation_hours_a.values[0]
        perf.fct_peak_power(data[['hp_power_el']])
        perf_indicators['components_transformers']['hp_peak_power'] = perf.peak_power.values[0]
    # Operation hours and peak power of transformers - ELECTROLYZER
    if 'ely_power_el' in data.columns:
        perf.fct_runtime_eva(data[['ely_power_el']])
        perf_indicators['components_transformers']['ely_operation_hours'] = perf.operation_hours_a.values[0]
        perf.fct_peak_power(data[['ely_power_el']])
        perf_indicators['components_transformers']['ely_peak_power'] = perf.peak_power.values[0]
    # Operation hours and peak power of transformers - FUELCELL
    if 'fc_power_el' in data.columns:
        perf.fct_runtime_eva(data[['fc_power_el']])
        perf_indicators['components_transformers']['fc_operation_hours'] = perf.operation_hours_a.values[0]
        perf.fct_peak_power(data[['fc_power_el']])
        perf_indicators['components_transformers']['fc_peak_power'] = perf.peak_power.values[0]


    ## Components storages
    perf_indicators['components_storages'] = {}
    # Storage energy evaluation - TES
    if 'tes_h_soc' in data.columns:
        perf.fct_storage_energy_eva(data_soc=data.tes_h_soc,
                                    data_capacity=metadata['tes_h_capacity'])
        perf.fct_roundtrip_eff(data_ch=data.tes_h_power.clip(lower=0),
                               data_dch=abs(data.tes_h_power.clip(upper=0)))         # dch negative, ch positive
        perf_indicators['components_storages']['tes_h_energy_year'] = perf.energy_year
        perf_indicators['components_storages']['tes_h_energy_day'] = perf.energy_day
        perf_indicators['components_storages']['tes_h_charge_cycles_year'] = perf.charge_cycles_year
        perf_indicators['components_storages']['tes_h_eff_roundtrip'] = perf.eff_roundtrip
        perf_indicators['components_storages']['tes_h_enegry_loss_year'] = perf.energy_loss

    # Storage energy evaluation - BATTERY
    if 'bat_soc' in data.columns:
        perf.fct_storage_energy_eva(data_soc=data.bat_soc,
                                    data_capacity=metadata['bat_capacity'])
        perf.fct_roundtrip_eff(data_ch=data.bat_power_ch,
                               data_dch=data.bat_power_dch)
        perf_indicators['components_storages']['bat_energy_year'] = perf.energy_year
        perf_indicators['components_storages']['bat_energy_day'] = perf.energy_day
        perf_indicators['components_storages']['bat_charge_cycles_year'] = perf.charge_cycles_year
        perf_indicators['components_storages']['bat_eff_roundtrip'] = perf.eff_roundtrip
        perf_indicators['components_storages']['bat_energy_loss_year'] = perf.energy_loss

    # Storage energy evaluation - BATTERY
    if 'h2_soc' in data.columns:
        perf.fct_storage_energy_eva(data_soc=data.h2_soc,
                                    data_capacity=metadata['h2_capacity'])
        perf.fct_roundtrip_eff(data_ch=data.ely_power_el,
                                data_dch=data.fc_power_el)
        perf_indicators['components_storages']['h2_energy_year'] = perf.energy_year
        perf_indicators['components_storages']['h2_energy_day'] = perf.energy_day
        perf_indicators['components_storages']['h2_charge_cycles_year'] = perf.charge_cycles_year
        perf_indicators['components_storages']['h2_eff_roundtrip'] = perf.eff_roundtrip
        perf_indicators['components_storages']['h2_energy_loss_year'] = perf.energy_loss


    ## General performance
    perf_indicators['general'] = {}

    # Self-sufficiency
    if 'hp_power_el' in data.columns:
        perf.fct_self_sufficiency(data_load=(data.load_el_power+data.hp_power_el),
                                  data_grid=data.grid_power)
    else:
        perf.fct_self_sufficiency(data_load=(data.load_el_power),
                                  data_grid=data.grid_power)
    perf_indicators['general']['self_sufficiency'] = perf.self_sufficiency
    # Self-consumption
    perf.fct_self_consumption(data_source=data.pv_power,
                              data_grid=data.grid_power)
    perf_indicators['general']['self_consumption'] = perf.self_consumption


    ## Neighborhood
    if 'nh_power_shared' in data.columns:
        # Annual shared energy and max shared power
        perf_indicators['neighborhood'] = {'nh_annual_energy_shared': data.nh_power_shared.resample('H').mean().sum(),
                                           'nh_peak_power_shared': data.nh_power_shared.max()}

    return perf_indicators