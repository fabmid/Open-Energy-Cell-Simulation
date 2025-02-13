import pandas as pd
import numpy as np
from datetime import datetime
import pvlib

import data_loader
from simulatable import Simulatable
from serializable import Serializable

class Environment(Serializable, Simulatable):
    """Relevant methods for the loading and formatting of data for irradiation (Photovoltaic model) and wind speed (Wind turbine model).

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.

    Returns
    -------
    None : `None`

    Note
    ----
    """

    def __init__(self,
                 timestep):

        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)

        ## Data loader
        # Integrate irradiation and temperature/wind data loader for photovoltaic and windtubrine model
        self.meteo_irradiation = data_loader.MeteoIrradiation()
        self.meteo_weather = data_loader.MeteoWeather()

        # [s] Timestep
        self.timestep = timestep


    def simulation_init(self):
        """Simulatable method.
        Loads all relevant environment data, including total, beam, sky, ground irradiation (pvlib), temperature in [K] and windspeed data in [m/s].

        Parameters
        ----------
        None : `None`

        Returns
        -------

        Note
        ----
        - Ambient tempertaure for pvlib calculation is handeled in °C, for other components as battery it is handeled in K.
        - Class data_loader
            - Integrated and its method MeteoIrradiation() and MeteoWeather() to integrate csv weather data.
            - This method is called externally before the central method simulate() \
            of the class simulation is called.
        """

        ## List container to store results for all timesteps
        self.timeindex_list = list()
        self.temperature_ambient_list = list()
        self.windspeed_list = list()
        self.air_pressure_list = list()
        self.sun_ghi_list = list()
        self.sun_dhi_list = list()
        self.sun_bni_list = list()

        ## Time indexing
        # Extract environment values with data_loader from csv file
        self.time_step = self.meteo_irradiation.get_time()
        # List comprehension to get first timeindex of timestep
        self.timeindex = [datetime.strptime(i.split('/')[0], '%Y-%m-%dT%H:%M:%S.%f') for i in self.time_step]

        ## Environmental data
        # Windspeed, temperature, pressure and roughness data
        self.windspeed = pd.Series(self.meteo_weather.get_wind_speed().values, index=self.timeindex)
        self.temperature_ambient = pd.Series(self.meteo_weather.get_temperature().values, index=self.timeindex)
        self.air_pressure = pd.Series(self.meteo_weather.get_air_pressure().values, index=self.timeindex)*100

        ## Pvlib: Photovoltaic model: Irradiation, temperature, wind data
        # Irradiation: convert Irradiation [Wh] to irradiance [W]
        self.sun_bni = pd.Series((self.meteo_irradiation.get_bni().values) / (self.timestep/3600), index=self.timeindex)
        self.sun_ghi = pd.Series((self.meteo_irradiation.get_ghi().values) / (self.timestep/3600), index=self.timeindex)
        self.sun_dhi = pd.Series((self.meteo_irradiation.get_dhi().values) / (self.timestep/3600), index=self.timeindex)

        # Create df with solar input data (format necessary for pvlib)
        # Ambient temperature for pvlib in °C
        self.data_solar = pd.DataFrame({'ghi':self.sun_ghi,
                                        'dhi':self.sun_dhi,
                                        'dni':self.sun_bni,
                                        'temp_air':self.temperature_ambient-273,
                                        'wind_speed':self.windspeed
                                        })


        ## Windpowerlib: Windturbine model: Create Wind data DataFrame multiindex for WindTurbine
        # Fixed roughness length as long as datasource does not provide data
        self.roughness_length = np.ones(len(self.windspeed))*0.1

        # Needs to include wind_speed, temperature, pressure and roughness_length at given heights
        arrays = [['wind_speed', 'temperature', 'pressure', 'roughness_length'],
                  [10, 2, 0, 0]]
        index=pd.MultiIndex.from_arrays(arrays, names=('name', 'value'))

        self.wind_data = pd.DataFrame({index[0]: self.windspeed,
                                       index[1]: self.temperature_ambient,
                                       index[2]: self.air_pressure,
                                       index[3]: self.roughness_length}
                                      )


    def simulation_calculate(self):
        """Simulatable method.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        """

        ## Save component status variables for all timesteps to list
        # Time index
        self.timeindex_list.append(self.timeindex[self.time])
        self.temperature_ambient_list.append(self.temperature_ambient[self.time])
        self.air_pressure_list.append(self.air_pressure[self.time])
        self.windspeed_list.append(self.windspeed[self.time])
        self.sun_ghi_list.append(self.sun_ghi[self.time])
        self.sun_dhi_list.append(self.sun_dhi[self.time])
        self.sun_bni_list.append(self.sun_bni[self.time])



class Environment_DWD(Serializable, Simulatable):
    """Relevant methods for the loading and formatting of data for irradiation (Photovoltaic model) using DWD data source.

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.

    Returns
    -------
    None : `None`

    Note
    ----
    - DWD data needs to be first transfered from txt to csv and column seperator changed from ',' to ';'.
    """

    def __init__(self,
                 timestep):

        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)

        ## Data loader
        # Integrate irradiation and temperature/wind data loader for photovoltaic and windtubrine model
        self.DWD_irradiation = data_loader.DWDIrradiation()
        self.DWD_weather = data_loader.DWDWeather()

        # [s] Timestep
        self.timestep = timestep


    def simulation_init(self):
        """Simulatable method.
        Load all relevant environment data, including global an diffuse irradiation.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Ambient tempertaure for pvlib calculation is handeled in °C, for other components as battery it is handeled in K.
        - Class data_loader
            - Integrated and its method DWDIrradiation() and DWDWeather() to integrate csv weather data.
            - This method is called externally before the central method simulate() \
            of the class simulation is called.
        """

        ## List container to store results for all timesteps
        self.timeindex_list = list()
        self.temperature_ambient_list = list()
        self.windspeed_list = list()
        self.air_pressure_list = list()
        self.sun_ghi_list = list()
        self.sun_dhi_list = list()
        self.sun_bni_list = list()
        self.sun_zenith_list = list()

        ## Time indexing
        # Extract environment values with data_loader from csv file
        self.time_step = self.DWD_irradiation.get_time()
        # List comprehension to get first timeindex of timestep
        self.timeindex = [datetime.strptime(str(i), '%Y%m%d%H') for i in self.time_step]

        # Extract environment values with data_loader from csv file
        # Windspeed in [m/s] at 10m height
        self.windspeed = pd.Series(self.DWD_weather.get_wind_speed().values, index=self.timeindex)
        # Ambient temperature in [°C] at 2m height
        self.temperature_ambient = pd.Series(self.DWD_weather.get_temperature().values, index=self.timeindex)
        # Air pressure transfer from hPa to Pa
        self.air_pressure = pd.Series(self.DWD_weather.get_air_pressure().values, index=self.timeindex) * 100

        # Irradiation in [Wh]: convert Irradiation [Wh] to irradiance [W]
        self.sun_ghi = pd.Series((self.DWD_irradiation.get_ghi().values) / (self.timestep/3600), index=self.timeindex)
        self.sun_dhi = pd.Series((self.DWD_irradiation.get_dhi().values) / (self.timestep/3600), index=self.timeindex)
        self.sun_zenith = pd.Series((self.DWD_irradiation.get_zenith().values), index=self.timeindex)

        # Calculation of dni [Wh]
        self.sun_bni = pvlib.irradiance.dirint(ghi=self.sun_ghi,
                                               solar_zenith=self.sun_zenith,
                                                times=pd.DatetimeIndex(self.timeindex),
                                                pressure=self.air_pressure,
                                                use_delta_kt_prime=True,
                                                temp_dew=None,
                                                min_cos_zenith=0.065,
                                                max_zenith=87)
        # Replace nan with 0
        self.sun_bni = self.sun_bni.replace(to_replace = np.nan, value = 0)

        # Create df with solar input data (format necessary for pvlib)
        # Ambient temperature for pvlib in °C
        self.data_solar = pd.DataFrame({'ghi':self.sun_ghi,
                                        'dhi':self.sun_dhi,
                                        'dni':self.sun_bni,
                                        'temp_air':self.temperature_ambient,
                                        'wind_speed':self.windspeed
                                        })

    def simulation_calculate(self):
        """Simulatable method.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        """

        ## Save component status variables for all timesteps to list
        # Time index
        self.timeindex_list.append(self.timeindex[self.time])
        self.temperature_ambient_list.append(self.temperature_ambient[self.time])
        self.windspeed_list.append(self.windspeed[self.time])
        self.air_pressure_list.append(self.air_pressure[self.time])
        self.sun_ghi_list.append(self.sun_ghi[self.time])
        self.sun_dhi_list.append(self.sun_dhi[self.time])
        self.sun_bni_list.append(self.sun_bni[self.time])
        self.sun_zenith_list.append(self.sun_zenith[self.time])
