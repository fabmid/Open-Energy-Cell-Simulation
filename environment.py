import pandas as pd
from datetime import datetime
import pvlib
from simulatable import Simulatable
import data_loader

class Environment(Simulatable):
    """Relevant methods for the calculation of the global irradiation and sun position.

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    system_orientation : `floats`
        [°] Tuble of floats definiing the system oriantation with system azimuth and inclination.
    system_location : `floats`
        [°] Tuble of floats defining the system location coordinates with longitude and latitude.

    Note
    ----
    - System orientation (tuble of floats)
        - 1. tuble entry system azimuth in degrees [°] (180°=north, 0°=south, 270°=east, 90°west).
        - 2. tuble entry system inclination in degrees [°].
    - System location (tuble of floats)
        - 1. tuble entry system longitude in degrees [°].
        - 2. tuble entry system latitude in degrees [°].        
    """


    def __init__(self,
                 timestep,
                 system_orientation,
                 system_location):

        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # Integrate irradiation and weather Data loader to load environmental data
        self.meteo_irradiation = data_loader.MeteoIrradiation()
        self.meteo_weather = data_loader.MeteoWeather()
        
        # [s] Timestep
        self.timestep = timestep

        # PV module azimuth and inclination angle:
        # Azimuth angle in degrees [°] (180°=north, 0°=south, 270°=east, 90°west)
        self.system_azimuth = system_orientation[0]
        self.system_tilt = system_orientation[1]
        # System location
        self.system_location = system_location


    def load_data(self):
        """Loads and calculates all relevant environment data, including total, \
        beam, sky, ground irradiation (pvlib), temperature in [K] and windspeed data in [m/s] \
        sun position (pvlib) and angle of inclination (pvlib).

        Parameters
        ----------
        None : `None`

        Returns
        -------
        sun_position_pvlib : `floats`
            [°] Tuble of floats, defining the sun position with its elevation and azimuth angle.
        sun_aoi_pvlib : `floats`
            [°] Angle of incidence of the solar vector on the module surface.
        sun_irradiance_pvlib : `floats`
            [W/m2] Plane on array irradiation (total, beam, sky, ground).
        power : `float`
            [Wh] Total plane on array irradiation.

        Note
        ----
        - All models are based on pvlib libary version 0.7.1.        
        - Solar position calculator (pvlib)
            - pvlib.solarposition.get_solarposition(time, latitude, longitude, \
            altitude=None, pressure=None, method='nrel_numpy', temperature=12, kwargs)
            - https://pvlib-python.readthedocs.io/en/stable/generated/pvlib.solarposition.get_solarposition.html
            - Further details, compare [1]_, [2]_ and [3]_.            
        - Angle of incident calculator (pvlib)
            - The angle of incidence of the solar vector and the module surface normal.
            - pvlib.irradiance.aoi(surface_tilt, surface_azimuth, solar_zenith, solar_azimuth)
            - https://pvlib-python.readthedocs.io/en/stable/generated/pvlib.irradiance.aoi.html
        - Total, beam, sky diffuse and ground reflected in-plane irradiance
            - Calculated using the specified sky diffuse irradiance model (pvlib).
            - pvlib.irradiance.get_total_irradiance(surface_tilt, surface_azimuth, \
            solar_zenith, solar_azimuth, dni, ghi, dhi, dni_extra=None, airmass=None, \
            albedo=0.25, surface_type=None, model='isotropic', model_perez='allsitescomposite1990', kwargs)
            - https://pvlib-python.readthedocs.io/en/stable/generated/pvlib.irradiance.get_total_irradiance.html
        - Class data_loader 
            - Integrated and its method MeteoIrradiation() and MeteoWeather() to integrate csv weather data.
            - This method is called externally before the central method simulate() \
            of the class simulation is called.       
            
        .. [1] I. Reda and A. Andreas, Solar position algorithm for solar
           radiation applications. Solar Energy, vol. 76, no. 5, pp. 577-589, 2004.
        .. [2] I. Reda and A. Andreas, Corrigendum to Solar position algorithm
           for solar radiation applications. Solar Energy, vol. 81, no. 6, p. 838, 2007.
        .. [3]	NREL SPA code: http://rredc.nrel.gov/solar/codesandalgorithms/spa/
        """

        ## Extract environment values with data_loader from csv file
        self.time_step = self.meteo_irradiation.get_time()
        # List comprehension to get first timeindex of timestep
        self.time_index = [datetime.strptime(i.split('/')[0], '%Y-%m-%dT%H:%M:%S.%f') for i in self.time_step]
        # Load environmental values (Irradiation, temperature and windspeed)
        self.sun_ghi = pd.Series((self.meteo_irradiation.get_ghi().values) / (self.timestep/3600), index=self.time_index)
        self.sun_bhi = pd.Series((self.meteo_irradiation.get_bhi().values) / (self.timestep/3600), index=self.time_index)
        self.sun_dhi = pd.Series((self.meteo_irradiation.get_dhi().values) / (self.timestep/3600), index=self.time_index)

        self.temperature_ambient = pd.Series(self.meteo_weather.get_temperature().values, index=self.time_index)
        self.windspeed = pd.Series(self.meteo_weather.get_wind_speed().values, index=self.time_index)

        # pvlib: Calculate sun position
        self.sun_position_pvlib = pvlib.solarposition.get_solarposition(time=self.time_index,
                                                                        latitude=self.system_location.latitude,
                                                                        longitude=self.system_location.longitude)

        # pvlib: Calculate sun angle of incident
        self.sun_aoi_pvlib = pvlib.irradiance.aoi(surface_tilt=self.system_tilt,
                                                  surface_azimuth=self.system_azimuth,
                                                  solar_zenith=self.sun_position_pvlib['elevation'],
                                                  solar_azimuth=self.sun_position_pvlib['azimuth'])

        # pvlib: Calculate plane of array irradiance (total, beam, sky, ground)
        self.sun_irradiance_pvlib = pvlib.irradiance.get_total_irradiance(surface_tilt=self.system_tilt,
                                                                    surface_azimuth=self.system_azimuth,
                                                                    solar_zenith=self.sun_position_pvlib['elevation'],
                                                                    solar_azimuth=self.sun_position_pvlib['azimuth'],
                                                                    dni=self.sun_bhi, ghi=self.sun_ghi, dhi=self.sun_dhi)
        # extract global plane of array irradiance
        self.power = self.sun_irradiance_pvlib['poa_global']
        self.power_poa_direct = self.sun_irradiance_pvlib['poa_direct']
        self.power_poa_diffuse = self.sun_irradiance_pvlib['poa_sky_diffuse']