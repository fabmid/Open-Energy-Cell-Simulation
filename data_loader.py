import pandas

class CSV:
    """Relevant methods of CSV loader in order to load csv file of \
    CAMS Radiation Service, MERRA Weather Data or load profile.

    Parameters
    ----------
    file_name : `str`
        File path and name of fiel to be loaded.
    start : `ind`
        First timestep of csv file to be loaded.
    end : `ind`
        Last timestep of csv file to be loaded.

    Note
    -----
    - Class is parent class of MeteoIrradiation, MeteoWeather and LoadDemand.
    
    """

    def read_pkl(self,
                 file_name):
        """Loads the pkl file and stores it in parameter __data_set

        Parameters
        -----------
        file_name : `str`
            File path and name of fiel to be loaded.

        Returns
        -------
        __data_set : `Pandas.Dataframe`
            Pandas Dataframe with extracted data rows.
        """

        self.__data_set = pandas.read_pickle(file_name)


    def read_csv(self,
                 file_name,
                 start,
                 end):
        """Loads the csv file and stores it in parameter __data_set

        Parameters
        -----------
        file_name : `str`
            File path and name of fiel to be loaded.
        start : `int`
            First timestep of csv file to be loaded.
        end : `int`
            Last timestep of csv file to be loaded.

        Returns
        -------
        __data_set : `Pandas.Dataframe`
            Pandas Dataframe with extracted data rows.
        """

        self.__data_set = pandas.read_csv(file_name, comment='#', header=None, decimal='.', sep=';')[start:end]


    def get_colomn(self,
                   i):
        """Extracts specific colomn of loaded Pandas Dataframe by read_csv().

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
        """Returns Timestamp of loaded irradiation dataset."""
        return super().get_colomn(0)

    def get_irradiance_toa(self):
        """ Returns [Wh/m2] Irradiation on horizontal plane at the top of atmosphere."""
        return super().get_colomn(1)

    def get_ghi_clear_sky(self):
        """Returns [Wh/m2] Clear sky global irradiation on horizontal plane at ground level."""
        return super().get_colomn(2)

    def get_bhi_clear_sky(self):
        """Returns [Wh/m2] Clear sky beam irradiation on horizontal plane at ground level."""
        return super().get_colomn(3)

    def get_dhi_clear_sky(self):
        """Returns [Wh/m2] Clear sky diffuse irradiation on horizontal plane at ground level."""
        return super().get_colomn(4)

    def get_bni_clear_sky(self):
        """Returns [Wh/m2] Clear sky beam irradiation on mobile plane following the sun at normal incidence."""
        return super().get_colomn(5)

    def get_ghi(self):
        """Returns [Wh/m2] Global irradiation on horizontal plane at ground level."""
        return super().get_colomn(6)

    def get_bhi(self):
        """Returns [Wh/m2] Beam irradiation on horizontal plane at ground level."""
        return super().get_colomn(7)

    def get_dhi(self):
        """Returns [Wh/m2] Diffuse irradiation on horizontal plane at ground level."""
        return super().get_colomn(8)

    def get_bni(self):
        """Returns [Wh/m2] Beam irradiation on mobile plane following the sun at normal incidence."""
        return super().get_colomn(9)

    def get_reliability(self):
        """Returns [1] Proportion of reliable data in the summarization (0-1)."""
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
        """Returns Date. format YYYY-MM-DD"""
        return super().get_colomn(0)

    def get_time(self):
        """Returns Time of day. format HH-MM"""
        return super().get_colomn(1)

    def get_temperature(self):
        """Returns Temperature (K);Temperature at 2 m above ground"""
        return super().get_colomn(2)

    def get_humidity(self):
        """Returns Relative humidity (%);Relative humidity at 2 m above ground"""
        return super().get_colomn(3)

    def get_air_pressure(self):
        """Returns Pressure (hPa);Pressure at ground level"""
        return super().get_colomn(4)

    def get_wind_speed(self):
        """Returns Wind speed (m/s);Wind speed at 10 m above ground"""
        return super().get_colomn(5)

    def get_wind_direction(self):
        """Returns Wind direction (deg);Wind direction at 10 m above ground (0 means from North, 90 from East...)"""
        return super().get_colomn(6)

    def get_rainfall(self):
        """Returns Rainfall (kg/m2);Rainfall (= rain depth in mm)"""
        return super().get_colomn(7)

    def get_snowfall():
        """Returns Snowfall (kg/m2);Snowfall"""
        return super().get_colomn(8)

    def get_snow_depth(self):
        """Returns Snow depth (m);Snow depth"""
        return super().get_colomn(9)


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
    power_profile : `pandas.series float`
        [W] Pandas series of load profile specifies power load demand per timestep in watt.
    cooling_profile : `pandas.series float`
        [W] Pandas series of load profile specifies cooling load demand per timestep in watt.
        
    Note
    ----
    - Implemented method is usually integrated in load class to directly load load profile data.
    - Heat load demand shall be placed in csv file with heating load in 0.column and hot water heat demand in 1.column.
    - Electricty load demand is a single column csv file for a timeframe of a day, week or year.
    
    """
    
    def get_heating_profile(self):
        """Returns load profile"""
        return super().get_colomn(0)

    def get_hotwater_profile(self):
        """Returns load profile"""
        return super().get_colomn(1)

    def get_power_profile(self):
        """Returns load profile"""
        return super().get_colomn(2)  
    
    def get_cooling_profile(self):
        """Returns load profile"""
        return super().get_colomn(3)  