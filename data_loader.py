import pandas

class CSV:
    """Relevant methods of CSV loader in order to load csv file of \
    CAMS Radiation Service, MERRA Weather Data or load profile.

    Parameters
    ----------
    file_name : `str`
        File path and name of fiel to be loaded.
    simulation_steps : `ind`
        Number of steps to be simulated.

    Returns
    -------
    None : `None`

    Note
    -----
    - Class is parent class of MeteoIrradiation, MeteoWeather and LoadDemand.
    """

    def read_pkl(self,
                 file_name):
        """Load the pkl file and stores it in parameter __data_set

        Parameters
        -----------
        file_name : `str`
            File path and name of file to be loaded.

        Returns
        -------
        __data_set : `Pandas.Dataframe`
            Pandas Dataframe with extracted data rows.
        """

        self.__data_set = pandas.read_pickle(file_name)


    def read_csv(self,
                 file_name,
                 simulation_steps):
        """Load the csv file and stores it in parameter __data_set

        Parameters
        -----------
        file_name : `str`
            File path and name of fiel to be loaded.
        simulation_steps : `ind`
            Number of steps to be simulated.

        Returns
        -------
        __data_set : `Pandas.Dataframe`
            Pandas Dataframe with extracted data rows.
        """

        self.__data_set = pandas.read_csv(file_name, comment='#', header=None, decimal='.', sep=';')[0:simulation_steps]


    def get_colomn(self,
                   i):
        """Extract specific colomn of loaded Pandas Dataframe by read_csv().

        Parameters
        -----------
        i : `int`
            Colomn to be extracted from Pandas Dataframe __data_set.

        Returns
        -------
        __data_set : `Pandas.Series`
            Pandas Series with specified colomn in case loaded pandas Dataframe has multiple colomns.
        """

        return self.__data_set[:][i]



class MeteoIrradiation(CSV):
    """Relevant methods to extracte data from CAMS Radiation Service Dataset.

    Parameters
    ----------
    None : `None`

    Returns
    -------
    time : `pandas.series int`
        Timestamp of loaded irradiation dataset.
    irradiance_toa : `pandas.series float`
        [Wh/m2] Irradiation on horizontal plane at the top of atmosphere.
    ghi_clear_sky : `pandas.series float`
        [Wh/m2] Clear sky global irradiation on horizontal plane at ground level.
    bhi_clear_sky : `pandas.series float`
        [Wh/m2] Clear sky beam irradiation on horizontal plane at ground level.
    dhi_clear_sky : `pandas.series float`
        [Wh/m2] Clear sky diffuse irradiation on horizontal plane at ground level.
    bni_clear_sky : `pandas.series float`
        [Wh/m2] Clear sky beam irradiation on mobile plane following the sun at normal incidence.
    ghi : `pandas.series float`
        [Wh/m2] Global irradiation on horizontal plane at ground level.
    bhi : `pandas.series float`
        [Wh/m2] Beam irradiation on horizontal plane at ground level.
    dhi : `pandas.series float`
        [Wh/m2] Diffuse irradiation on horizontal plane at ground level.
    bni : `pandas.series float`
        [Wh/m2] Beam irradiation on mobile plane following the sun at normal incidence.
    reliability : `pandas.series float`
        [1] Proportion of reliable data in the summarization (0-1).

    Note
    -----
    - Implemented methods are usually integrated in other classes to directly load irradiance data.
    - Examples are the classes environment, load, photovoltaic or battery.
    - Cams irradiance datasets can be downloaded at:
        - http://www.soda-pro.com/web-services/radiation/cams-radiation-service
    """

    def get_time(self):
        """Return Timestamp of loaded irradiation dataset."""
        return super().get_colomn(0)

    def get_irradiance_toa(self):
        """ Return [Wh/m2] Irradiation on horizontal plane at the top of atmosphere."""
        return super().get_colomn(1)

    def get_ghi_clear_sky(self):
        """Return [Wh/m2] Clear sky global irradiation on horizontal plane at ground level."""
        return super().get_colomn(2)

    def get_bhi_clear_sky(self):
        """Return [Wh/m2] Clear sky beam irradiation on horizontal plane at ground level."""
        return super().get_colomn(3)

    def get_dhi_clear_sky(self):
        """Return [Wh/m2] Clear sky diffuse irradiation on horizontal plane at ground level."""
        return super().get_colomn(4)

    def get_bni_clear_sky(self):
        """Return [Wh/m2] Clear sky beam irradiation on mobile plane following the sun at normal incidence."""
        return super().get_colomn(5)

    def get_ghi(self):
        """Return [Wh/m2] Global irradiation on horizontal plane at ground level."""
        return super().get_colomn(6)

    def get_bhi(self):
        """Return [Wh/m2] Beam irradiation on horizontal plane at ground level."""
        return super().get_colomn(7)

    def get_dhi(self):
        """Return [Wh/m2] Diffuse irradiation on horizontal plane at ground level."""
        return super().get_colomn(8)

    def get_bni(self):
        """Return [Wh/m2] Beam irradiation on mobile plane following the sun at normal incidence."""
        return super().get_colomn(9)

    def get_reliability(self):
        """Return [1] Proportion of reliable data in the summarization (0-1)."""
        return super().get_colomn(10)


class MeteoWeather(CSV):
    """Relevant methods to extracte data from MERRA Dataset.

    Parameters
    ----------
    None : `None`

    Returns
    -------
    date : `pandas.seriesint`
        Date with format YYYY-MM-DD.
    time : `pandas.series int`
        Time of day with format HH-MM.
    temperature : `pandas.series float`
        [K] Ambient temperature at 2 m above ground.
    humidity : `pandas.series float`
        [%] Relative humidity at 2 m above ground.
    wind_speed : `pandas.series float`
        [m/s] Wind speed at 10 m above ground.
    wind_direction : `pandas.series float`
        [°] Wind direction at 10 m above ground (0 means from North, 90 from East...).
    rainfall : `pandas.series float`
        [mm] Rainfall (= rain depth in mm).
    snowfall : `pandas.series float`
        [kg/m2] Snowfall.
    snow_depth : `pandas.series float`
        [m] Snow depth.

    Note
    -----
    - Implemented methods are usually integrated in other classes to directly load weather data.
    - Examples are the classes environment, load, photovoltaic or battery.
    - MERRA datasets can be downloaded at:
        - http://www.soda-pro.com/web-services/meteo-data/merra
    """

    def get_date(self):
        """Return Date. format YYYY-MM-DD"""
        return super().get_colomn(0)

    def get_time(self):
        """Return Time of day. format HH-MM"""
        return super().get_colomn(1)

    def get_temperature(self):
        """Return Temperature (K);Temperature at 2 m above ground"""
        return super().get_colomn(2)

    def get_humidity(self):
        """Return Relative humidity (%);Relative humidity at 2 m above ground"""
        return super().get_colomn(3)

    def get_air_pressure(self):
        """Return Pressure (hPa);Pressure at ground level"""
        return super().get_colomn(4)

    def get_wind_speed(self):
        """Return Wind speed (m/s);Wind speed at 10 m above ground"""
        return super().get_colomn(5)

    def get_wind_direction(self):
        """Return Wind direction (deg);Wind direction at 10 m above ground (0 means from North, 90 from East...)"""
        return super().get_colomn(6)

    def get_rainfall(self):
        """Return Rainfall (kg/m2);Rainfall (= rain depth in mm)"""
        return super().get_colomn(7)

    def get_snowfall(self):
        """Return Snowfall (kg/m2);Snowfall"""
        return super().get_colomn(8)

    def get_snow_depth(self):
        """Return Snow depth (m);Snow depth"""
        return super().get_colomn(9)


class DWDIrradiation(CSV):
    """Relevant methods to extracte data from DWD Dataset.

    Parameters
    ----------
    None : `None`

    Returns
    -------
    time : `pandas.seriesint`
        Date time with format YYYYMMDDHH.

    ghi : `pandas.series float`
        [Wh/m2] Global irradiation on horizontal plane at ground level.

    dhi : `pandas.series float`
        [Wh/m2] Diffuse irradiation on horizontal plane at ground level.

    zenith : `pandas.series float`
        [°] Solar zenith angle at mid of interval.

    Note
    ----
    - DWD data needs to be in csv file format created with the helper class dwd_data_conversion
    - Additionally header row needs to be commented out
    - It shall include follwoig columns: index: MESS_DATUM; FD_LBERG, FG_LBERG, ZENIT
    """

    def get_time(self):
        """Return Date. format YYYYMMDDHH"""
        return super().get_colomn(1)

    def get_dhi(self):
        """Return [Wh/m2] Diffuse irradiation on horizontal plane at ground level."""
        return super().get_colomn(2)

    def get_ghi(self):
        """Return [Wh/m2] Global irradiation on horizontal plane at ground level."""
        return super().get_colomn(3)

    def get_zenith(self):
        """Return [°] solar zenith angle at mid of interval."""
        return super().get_colomn(4)


class DWDWeather(CSV):
    """Relevant methods to extracte data from MERRA Dataset.

    Parameters
    ----------
    None : `None`

    Returns
    -------
    time : `pandas.seriesint`
        Date time with format YYYYMMDD.

    temperature : `pandas.series float`
        [K] Ambient temperature at 2 m above ground.

    Note
    ----
    - DWD data needs to be in csv file format created with the helper class dwd_data_conversion
    - This already includes the combination of ambient temperature and wind speed data in weather csv
    - Additionally header row needs to be commented out
    - Check wind speed height adaption, should be 10m height
    """

    def get_time(self):
        """Return Date. format YYYYMMDDHH"""
        return super().get_colomn(1)

    def get_temperature(self):
        """Return Temperature (K);Temperature at 2 m above ground"""
        return super().get_colomn(2)

    def get_wind_speed(self):
        """Return Wind speed (m/s);Wind speed at 10 m above ground"""
        return super().get_colomn(5)

    def get_air_pressure(self):
        """Return Pressure (hPa);Pressure at ground level"""
        return super().get_colomn(7)


class LoadDemand(CSV):
    """Relevant method to load load profile from csv file.

    Parameters
    ----------
    None : `None`

    Returns
    -------
    heating_profile : `pandas.series float`
        [W] Pandas series of heating load profile specifies heating load demand per timestep in watt.
    hotwater_profile : `pandas.series float`
        [W] Pandas series of load profile specifies hot water load demand per timestep in watt.
    electriicty_profile : `pandas.series float`
        [W] Pandas series of load profile specifies electricity load demand (appliances) per timestep in watt.
    cooling_profile : `pandas.series float`
        [W] Pandas series of load profile specifies cooling load demand per timestep in watt.
    car_profile : `pandas.series float`
        [W] Pandas series of car load profile specifies electricity load demand of car per timestep in watt.

    Note
    ----
    - Implemented method is usually integrated in load class to directly load load profile data.
    - Be aware of correct columns for different load types
    """

    def get_heating_profile(self):
        """Return load profile"""
        return super().get_colomn(0)

    def get_hotwater_profile(self):
        """Return load profile"""
        return super().get_colomn(1)

    def get_electricity_profile(self):
        """Return load profile"""
        return super().get_colomn(2)

    def get_cooling_profile(self):
        """Return load profile"""
        return super().get_colomn(3)

    def get_car_profile(self):
        """Return load profile"""
        return super().get_colomn(4)


class ElectricityCost(CSV):
    """Relevant method to load time-dependent electricty buy/sell prices from csv file.

    Parameters
    ----------
    None : `None`

    Returns
    -------
    electricity_cost_sell_profile : `pandas.series float`
        [euro] Pandas series of electricity cost profile specifies sell cost per timestep in euro.
    electricity_cost_buy_profile : `pandas.series float`
        [euro] Pandas series of electricity cost profile specifies buy cost per timestep in euro.
    """
    def get_electricity_cost_sell(self):
        """Returns cost sell profile"""
        return super().get_colomn(0)

    def get_electricity_cost_buy(self):
        """Returns cost buy profile"""
        return super().get_colomn(1)


class NetworkCost(CSV):
    """Relevant method to load time-dependent grid charges for NH scenarios from csv file.

    Parameters
    ----------
    None : `None`

    Returns
    -------

    """
    def get_network_charge_profile(self):
        """Returns time-dependent network charge profile"""
        return super().get_colomn(0)


class StorageOpexCost(CSV):
    """Relevant method to load time-dependent storage opex_var cost profile from csv file.
    This may be the case for time-dependent grid charges in NH scenarios.

    Parameters
    ----------
    None : `None`

    Returns
    -------

    """
    def get_storage_opex_var_profile(self):
        """Return time-dependent opex_var profile"""
        return super().get_colomn(0)


class HeatCost(CSV):
    """Relevant method to load time-dependent heat buy/sell prices from csv file.

    Parameters
    ----------
    None : `None`

    Returns
    -------

    """
    def get_heat_cost_sell(self):
        """Return cost sell profile"""
        return super().get_colomn(2)

    def get_heat_cost_buy(self):
        """Return cost buy profile"""
        return super().get_colomn(3)


class NeighborhoodData(CSV):
    """Relevant method to load neighborhood data for economic calculation of multiple individual components.
    The data describes size distribution of decentral technologies as PV, heat pump or thermal storage.

    Parameters
    ----------
    None : `None`

    Returns
    -------

    """
    def get_house_id(self):
        """Return house id"""
        return super().get_colomn(0)

    def get_pv_size_distribution(self):
        """Return PV size share per house id"""
        return super().get_colomn(1)

    def get_hp_size_distribution(self):
        """Return HP size share per house id"""
        return super().get_colomn(2)

    def get_tes_h_size_distribution(self):
        """Return TES size share per house id"""
        return super().get_colomn(3)

    def get_grid_heat_size_distribution(self):
        """Return TES size share per house id"""
        return super().get_colomn(4)

    def get_pv_orient_distribution(self):
        """Return PV orientation per house id"""
        return super().get_colomn(5)


class hdf5():
    """Relevant methods to:
        - Store result data with meta data into hdf5 file format and load it later for results evaluation
        - Load house specific load profiles for neighborhood calculation

    Parameters
    ----------
    None : `None`

    Returns
    -------

    """

    def h5store(filename, df, **kwargs):
        store = pandas.HDFStore(filename)
        store.put('mydata', df)
        store.get_storer('mydata').attrs.metadata = kwargs
        store.close()

    def h5load(store):
        data = store['mydata']
        metadata = store.get_storer('mydata').attrs.metadata
        return data, metadata

    def get_load_houses(self,
                        file_name):
        """Load the hdf file and stores it in parameter __data_set

        Parameters
        -----------
        file_name : `str`
            File path and name of file to be loaded.

        Returns
        -------
        __data_set : `Pandas.Dataframe`
            Pandas Dataframe with extracted data rows.
        """

        self.data_set = (pandas.read_hdf(file_name, mode="r"))

        return(self.data_set)
