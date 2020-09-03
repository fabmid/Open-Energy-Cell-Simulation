import pvlib
from simulatable import Simulatable
from serializable import Serializable

class Photovoltaic(Serializable, Simulatable):
    """Relevant methods for the calculation of photovoltaic performance.

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    peak_power : `int`
        [Wp] Installed PV peak power.
    controller_type : `string`
        Type of charge controller PWM or MPPT.
    environment : `class`
        To get access to solar irradiation, ambient temperature and windspeed.
    file_name : `json`
        To load component parameters (optional).

    Note
    ----
    - Photovoltaic with MPPT assumption or fixed voltage (PWM) is possible.
    - Corresponding charge controller type mus be considered manually.
    - Models are based on pvlib libary version 0.7.1.
        - compare https://pvlib-python.readthedocs.io/en/stable/api.html
    - Photovoltaic model parameters based on SAM libary.
        - compare https://sam.nrel.gov/photovoltaic/pv-sub-page-2.html
    """

    def __init__(self,
                 timestep,
                 peak_power,
                 controller_type,
                 env,
                 file_path=None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for photovoltaic model specified')

            self.controller_method = "mppt"                                     # [-] Specification of photvoltaic charge controller (needed to call apropriate power method)
            self.temperature_a = -3.47                                          # [0] Thermal model: Numeric parameter a of Sandia PV Array Performance Model
            self.temperature_b = -0.0594                                        # [0] Thermal model: Numeric parameter b of Sandia PV Array Performance Model
            self.temperature_deltaT = 3                                         # [0] Thermal model: Numeric parameter dT of Sandia PV Array Performance Model
            self.params_name = "A10Green_Technology_A10J_S72_185"               # [-] Photovoltaic module specification
            self.params_V_mp_ref = 36.72                                        # [V] Photovoltaic voltage at MPP
            self.params_alpha_sc = 0.002253                                     # [A/C] Short-circuit current temperature coefficient
            self.params_a_ref = 1.98482                                         # [V] Product of the usual diode ideality factor (n, unitless), number of cells in series (Ns), and cell thermal voltage at reference conditions
            self.params_I_L_ref = 5.43568                                       # [A] The light-generated current (or photocurrent) at reference conditions
            self.params_I_o_ref = 1.16164e-09                                   # [A] The dark or diode reverse saturation current at reference conditions
            self.params_R_sh_ref = 298.424                                      # [Ohm] The shunt resistance at reference conditions
            self.params_R_s = 0.311962                                          # [Ohm] The series resistance at reference conditions
            self.params_pdc0 = 184.7016                                         # [W] Photovoltaic power of the modules at 1000 W/m2 and cell reference temperature
            self.params_gamma_pdc = -0.005                                      # [1/C] The temperature coefficient. Typically -0.002 to -0.005
            self.degradation_pv = 1.58154e-10                                   # [1/s] Photovoltaic degradation per second: deg_yearly=0.5% --> (1+0.005)**(1/365*24*3600)-1
            self.investment_costs_specific = 0.8                                # [$/Wp] Photovoltaic specific investment costs

        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # Integrate environment class
        self.env = env
        # Charge controller type
        self.controller_type = controller_type
        # [s] Timestep
        self.timestep = timestep

        ## Basic parameters
        self.peak_power = peak_power
        # [W] Current PV peak power dependent on aging
        self.peak_power_current = self.peak_power
        # [V] Battery voltage for PWM PV model
        self.battery_voltage = 12

        ## PV aging model
        # [W] End-of-Life condition of PV module
        self.end_of_life_photovoltaic = 0.8 * self.peak_power  #eingelesen

        ## Economic model
        # Nominal installed pv size for economic calculation
        self.size_nominal = self.peak_power


    def load_data(self):
        """Calulates all photovoltaic performance parameters by calling all
        methods based on pvlib.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        temperature_cell : `float`
            [K] Photovoltaic cell temperature, by calling method photovoltaic.temperature().
        power_module : `float`
            [W] Photvoltaic module power of specified module, by calling methods
            photovoltaic.power_mppt() or photovoltaic_pwm().

        Note
        ----
        - Photovoltaic power/temperature is calculated using pvlib libary.
        - This libary computes parameters not step by step but all in one for env data.
        - Method is equal to environment class, where all env data is loaded all in one.
        - Other paranmeters are caculated step by step in the method photovoltaic.calculate().
        """

        # Calculate photovoltaic temperature
        self.photovoltaic_temperature()

        # Calculate phovoltaic power dependent on controller type
        if self.controller_type == 'mppt':
            self.photovoltaic_power_mppt()
        elif self.controller_type == 'pwm':
            self.photovoltaic_power_pwm()
        else:
            print('Specify valid pv controller type!')


# =============================================================================
#     def start(self):
#         """Simulatable method.
# 
#         Note
#         ----
#         Still to be described in detail.s
#         """
# 
#         Simulatable.start(self)
# =============================================================================


    def calculate(self):
        """Calculates and extracts all photovoltaic performance parameters from
        implemented methods.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        temperature : `float`
            [K] Photovoltaic cell temperature, equals temperature_cell.
        power : `float`
            [W] Photvoltaic overall power of specified installed array specified
            by parameter peak_power.
        peak_power_current : `float`
            [W] Photovoltaic current peak power assuming power degradation by
            implemented method phovoltaic_aging()
        state_of_destruction : `float`
            [-] Phovoltaic state of destruction as fraction of current and
            nominal peak power.
        replacement : `float`
            [s] Time of replacement in case state_of_destruction equals 1.

        Note
        ----
        - Method mainly extracts parameters by calling implemented methods:
            - photovoltaic_aging()
            - photovoltaic_state_of_destruction()
        """

        # Photovoltaic cell temperature
        self.temperature = self.temperature_cell[self.time]
        # Power calculation with aging
        # Normalize power and multiplication with current peak power
        self.power = (self.power_module[self.time] / self.params_pdc0) * self.peak_power_current

        # Aging and State of Destruction
        self.photovoltaic_aging()
        self.photovoltaic_state_of_destruction()


    def photovoltaic_temperature(self):
        """Calculates photovoltaic cell temperature with the Sandia PV Array
        Performance Model integrated in pvlib.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        temperature_cell : `float`
            [K] Photovoltaic cell temperature (ATTENTION: not C as specified in pvlib)

        Note
        ----
        - The Sandia PV Array Performance Model is based on [1]_.
        - pvlib.temperature.sapm_cell is called with
            - pvlib.temperature.sapm_cell(poa_global, temp_air, wind_speed, a,
                                          b, deltaT, irrad_ref=1000)
            - compare, https://pvlib-python.readthedocs.io/en/stable/generated/pvlib.temperature.sapm_cell.html
        - For numerical values of different module configurations, call
            - pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS

        .. [1]	King, D. et al, 2004, “Sandia Photovoltaic Array Performance Model”,
                      SAND Report 3535, Sandia National Laboratories, Albuquerque, NM.
        """

        self.temperature_cell = pvlib.temperature.sapm_cell(poa_global=self.env.power ,
                                                            wind_speed=self.env.windspeed,
                                                            temp_air=self.env.temperature_ambient,
                                                            a=self.temperature_a,
                                                            b=self.temperature_b,
                                                            deltaT=self.temperature_deltaT)


    def photovoltaic_power_pwm(self):
        """Calculates the photovoltaic power at given voltage through the VI curve
        determination with the single diode model and gets parameter for single diode model.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        photocurrent : `float`
            [A] Light-generated current in amperes
        saturation_current : `float`
            [A] Diode saturation curent in amperes
        resistance_series : `float`
            [Ohm] Series resistance in ohms
        resistance_shunt : `float`
            [Ohm] Shunt resistance in ohms
        nNsVth : `float`
            (numeric) The product of the usual diode ideality factor (n, unitless),
            number of cells in series (Ns),
            and cell thermal voltage at specified effective irradiance and cell temperature.
        current : `np.ndarray/scalar`
            [A] Photovoltaic current in amperes at given voltage level.

        Note
        ----
        - To construct VI curve to determine power at given voltage level.
            - Is based on model by Jain et al. [2]_.
            - pvlib.pvsystem.i_from_v(resistance_shunt, resistance_series, nNsVth, \
            voltage, saturation_current, photocurrent, method='lambertw')
            - https://pvlib-python.readthedocs.io/en/stable/generated/pvlib.pvsystem.i_from_v.html#pvlib-pvsystem-i-from-v
        - Get values to construct single diode model.
            - Is based on five parameter model, by De Soto et al. described in [3]_.
            - Five values for the single diode equation at effective irradiance and
              cell temperature can be obtained by calling calcparams_desoto.
            - pvlib.pvsystem.calcparams_desoto(effective_irradiance, temp_cell, \
            alpha_sc, a_ref, I_L_ref, I_o_ref, R_sh_ref, R_s, EgRef=1.121, dEgdT=-0.0002677, irrad_ref=1000, temp_ref=25)
            - https://pvlib-python.readthedocs.io/en/stable/generated/pvlib.pvsystem.calcparams_desoto.html
            - results are returend as tubple of above listed returns.
        - To access pvlib module database and get parameters
            - modules_list = pvlib.pvsystem.retrieve_sam('CECMod') #'SandiaMod'
            - module = modules_list["NuvoSun_FL0912_100"]
        - Further references are [4]_ and [5]_.

        .. [2] A. Jain, A. Kapoor, “Exact analytical solutions of the parameters
               of real solar cells using Lambert W-function”, Solar Energy Materials
               and Solar Cells, 81 (2004) 269-277.
        .. [3] W. De Soto et al., “Improvement and validation of a model
               for photovoltaic array performance”, Solar Energy, vol 80, pp. 78-88, 2006.
        .. [4] System Advisor Model web page. https://sam.nrel.gov.
        .. [5] A. Dobos, “An Improved Coefficient Calculator for the California
               Energy Commission 6 Parameter Photovoltaic Module Model”,
               Journal of Solar Energy Engineering, vol 134, 2012.
        """

        # Call five parameter model
        [self.I_ph, self.I_sat, self.R_s, self.R_sh, self.nNsVth] = \
        pvlib.pvsystem.calcparams_desoto(effective_irradiance=self.env.power,
                                        temp_cell=(self.temperature_cell-273.15),
                                        alpha_sc=self.params_alpha_sc,
                                        a_ref=self.params_a_ref,
                                        I_L_ref=self.params_I_L_ref,
                                        I_o_ref=self.params_I_o_ref,
                                        R_sh_ref=self.params_R_sh_ref,
                                        R_s=self.params_R_s,
                                        EgRef=1.121,
                                        dEgdT=-0.0002677,
                                        irrad_ref=1000,
                                        temp_ref=25)

        # Define photovoltaic voltage
        self.singlediode_voltage = self.params_V_mp_ref
        # Call single diode model
        self.singlediode_current = pvlib.pvsystem.i_from_v(resistance_shunt=self.params_R_sh_ref,
                                                          resistance_series=self.params_R_s,
                                                          nNsVth=self.nNsVth,
                                                          voltage=self.singlediode_voltage,
                                                          saturation_current=self.I_sat,
                                                          photocurrent=self.I_ph,
                                                          method='lambertw')

        # Set negative current values (in case of no sun irradiance) to zero
        self.singlediode_current[self.singlediode_current<0] = 0

        # Calcuate power from I and V values
        self.singlediode_power = self.singlediode_current * self.singlediode_voltage

        self.power_module = self.singlediode_power # self.single_diode['p_mp']#self.single_diode_mpp['p_mp']#


    def photovoltaic_power_mppt(self):
        """Calculates the Photovoltaic Maximum Power.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        power : `float`
            [W] DC photovoltaic mpp power in watts.

        Note
        ----
        - Model is based on NREL’s PVWatts DC power model [6]_.
            - pvlib.pvsystem.pvwatts_dc(g_poa_effective, temp_cell, pdc0, gamma_pdc, temp_ref=25.0).
            - https://pvlib-python.readthedocs.io/en/stable/generated/pvlib.pvsystem.pvwatts_dc.html.

        .. [6] A. P. Dobos, “PVWatts Version 5 Manual” http://pvwatts.nrel.gov/downloads/pvwattsv5.pdf (2014).
        """

        self.power_module = pvlib.pvsystem.pvwatts_dc(g_poa_effective=self.env.power,
                                                      temp_cell=(self.temperature_cell-273.15),
                                                      pdc0=self.params_pdc0,
                                                      gamma_pdc=self.params_gamma_pdc)


    def photovoltaic_aging(self):
        """Calculates photovoltaic power degradation and current peak power in
        Watt [W] assuming aonstat power degradation.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        peak_power_current : `float`
            [Wp] Photovoltaic current peak power in watt peak.
        """

        # PV power degradation
        self.peak_power_current = (1 - (self.degradation_pv * self.timestep)) * self.peak_power_current


    def photovoltaic_state_of_destruction(self):
        """Calculates the photovoltaic state of destruction (SoD) and time of
        component replacement according to end of life criteria.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        state_of_destruction : `float`
            [1] Photovoltaic State of destruction with SoD=1 representing a broken component.
        replacement : `int`
            [s] Time of photovoltaic component replacement in seconds.

        Note
        ----
        - Replacement time is only set in timeseries array in case of a replacement, otherwise entry is 0.
        - In case of replacement current_peak_power is reset to nominal power.
        """

        # State of destruction
        self.state_of_destruction = (self.peak_power - self.peak_power_current) \
                                    / (self.peak_power -  self.end_of_life_photovoltaic)

        # Store time index in list replacement in case end of life criteria is met
        if self.state_of_destruction >= 1:
            self.replacement = self.time
            self.state_of_destruction = 0
            self.peak_power_current = self.peak_power
        else:
            self.replacement = 0