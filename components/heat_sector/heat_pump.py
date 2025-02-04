import pyomo.environ as pyo
import pandas as pd
import numpy as np

import data_loader
from simulatable import Simulatable
from serializable import Serializable
from optimizable import Optimizable

class Heat_Pump(Serializable, Simulatable, Optimizable):
    """Relevant methods for the calculation of heat pump performance.

    Parameters
    ----------
    timestep : 'int'
        [s] Simulation timestep in seconds.
    power_th_nom : `int`
        [kWp] Installed heat pump nominal thermal output power.
    env : `class`
        [-] To load ambient tempertaure [K]
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Model is based on hplib functions, which are directly implemented here
    - hplib parameters are given in [W], therefore transormation from W to kW is at some points necessary!
    - power values in OpEnCellS are in kW
    - Be aware of transformation of temperature from K t °C, all hplib functions use °C
    """

    def __init__(self,
                 timestep,
                 power_th_nom,
                 env,
                 file_path=None):

        # Read component parameters of wind turbine from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for heat pump model specified')
            self.type = "Heatpump_generic"
            self.specification = "Heatpump: hplib: Viessmann_AWO-M-AC_(AF)_101.A14"    # [-] Heat pump specification
            self.source_type = "air-water"                                      # [-] Heat pump type specification: air-water or brine-water possible
            self.cop_constant = 3.5
            self.part_load_min = 0.0                                            # [1] Min allowed part-load power in percentage, Hint: Can not be 0, otherwise MILP constraint does not work.
            self.cooling_mode = "False"                                         # True: HP operates also in cooling mode, False: only heating mode
            self.temperature_out_sec_heating_mode = 50.0                        # [°C] Flow temperature in heating mode
            self.temperature_out_sec_cooling_mode = 15.0                        # [°C] Flow temperature in cooling mode
            self.p_th_h_ref = 10168.8                                           # [W] Ref. Thermal heating power at -7°C / 52°C
            self.p_el_h_ref = 7193.432575                                       # [W] Ref. Electrical power heating mode at -7°C / 52°C
            self.p1_p_el_h = 65.24998302                                        # [-] Fit-Parameters for electrical power in heating mode
            self.p2_p_el_h = 0.011364929                                        # [-] Fit-Parameters for electrical power in heating mode
            self.p3_p_el_h = 0.047006715                                        # [-] Fit-Parameters for electrical power in heating mode
            self.p4_p_el_h = -65.29932854                                       # [-] Fit-Parameters for electrical power in heating mode
            self.p1_cop	= 46.374629                                             # [-] Fit-Parameters for COP
            self.p2_cop	= -0.087566678                                          # [-] Fit-Parameters for COP
            self.p3_cop	= 7.045435211                                           # [-] Fit-Parameters for COP
            self.p4_cop	= -46.22057939                                          # [-] Fit-Parameters for COP
            self.p_th_c_ref = 11480                                             # [W] Ref. Thermal cooling power in cooling mode
            self.p_el_c_ref = 4928.94                                           # [W] Ref. Electrical power in cooling mode
            self.p1_p_el_c = 69.60060772                                        # [-] Fit-Parameters for electrical power in cooling mode
            self.p2_p_el_c = -0.009207906                                       # [-] Fit-Parameters for electrical power in cooling mode
            self.p3_p_el_c = -1.368637967                                       # [-] Fit-Parameters for electrical power in cooling mode
            self.p4_p_el_c = -69.53274109                                       # [-] Fit-Parameters for electrical power in cooling mode
            self.p1_eer	= -13.20985038                                          # [-] Fit-Parameters for EER
            self.p2_eer	= 0.064839857                                           # [-] Fit-Parameters for EER
            self.p3_eer	= 11.52004943                                           # [-] Fit-Parameters for EER
            self.p4_eer	= 12.96140005                                           # [-] Fit-Parameters for EER
            self.end_of_life = 473040000                                        # [s] End of life time in seconds
            self.eco_no_systems = 1                                             # [1] The number of systems the peak power is allocated on
            self.capex_p1 = 0.0                                                 # [€$/kW_th] capex: Parameter1 (gradient) for specific capex definition (pendent on thermal output power)
            self.capex_p2 = 698.17                                              # [€$/kW_th] capex: Parameter2 (y-intercept) for specific capex definition (dependent on thermal output power)
            self.subsidy_percentage_capex = 0.35                                           # Economic model: [%] Capex subsidy
            self.subsidy_limit = 100000.0                                       # Economic model: [€/$] Max total capex subsidy
            self.opex_fix_p1 = 0.0                                              # [€$/kW/a] opex-fixed: % of capex
            self.opex_var = 0.0                                                 # [€$/kWh] opex-variable: Specific variable opex dependent on generated energy


        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)

        # Integrate environment class
        self.env = env
        # [s] Timestep
        self.timestep = timestep

        ## Basic parameters
        # Thermal power output - heating mode
        self.power_th_h_nom = power_th_nom
        # Scaling of thermal power output (hplib values in W)
        self.power_scaling = self.power_th_h_nom / (self.p_th_h_ref/1000)
        # Thermal power output - cooling mode (hplib values in W)
        if self.cooling_mode == 'True':
            self.power_th_c_nom = self.power_scaling * (self.p_th_c_ref/1000)
        else:
            pass

        ## Economic model
        # [W_th] Initialize Nominal powern (thermal output power)
        self.size_nominal = self.power_th_h_nom
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

        ## Initialize values
        # Aging model
        self.replacement_set = 0

        ## List container to store results for all timesteps
        self.state_of_destruction_list = list()
        self.replacement_list = list()


    def simulation_calculate(self):
        """Simulatable method.
        Initialize list containers to store simulation results.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`
        """

        # Calculate State of Desctruction
        self.get_state_of_destruction()

        ## Save component status variables for all timesteps to list
        self.state_of_destruction_list.append(self.state_of_destruction)
        self.replacement_list.append(self.replacement)


    def optimization_get_block(self, model):
        """
        Pyomo: MILP Heat pump block construction

        Parameters
        ----------
        model : pyomo.model class instance (defined in optimizabe.py)

        Returns
        -------
        None : `None`

        Note:
        -----
        - Blocks of heating/cooling mode are run after each other. First all timesteps in heating mode, then all timesteps in cooling mode!
        """

        ## Max thermal output power and CoP/EER calculation
        # Calculate primary input temperature (dependent on heat pump type)
        self.get_temperature_in_prim()
        self.temperature_in_prim = self.temperature_in_prim_list
        # Calculate max possible thermal output power
        self.get_power_h()

        # Central pyomo model
        self.model = model

        # Heat pump block (heating mode)
        self.model.blk_hp_h = pyo.Block()

        # In case capacity is NOT 0, normal calculation
        if self.power_th_h_nom != 0:

            # Define parameters
            self.model.blk_hp_h.power_th_h_max = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.power_th_h_max))
            self.model.blk_hp_h.power_th_h_min = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.power_th_h_min))
            self.model.blk_hp_h.cop = pyo.Param(self.model.timeindex, initialize=self.data_prep(list(self.cop)))
            # Define variables
            self.model.blk_hp_h.on_off_h = pyo.Var(self.model.timeindex, domain=pyo.Binary)                               # On/off status of component: 0=off and 1=on (needed for minimal and maximal power control)
            self.model.blk_hp_h.power_th_h = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)
            self.model.blk_hp_h.power_el_h = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)

            # Define constraints
            # Heat pump max power thermal output
            def max_power_th_rule(_b, t):
                return (_b.power_th_h[t] <= _b.on_off_h[t] * _b.power_th_h_max[t])
            self.model.blk_hp_h.max_power_th_c = pyo.Constraint(self.model.timeindex, rule=max_power_th_rule)

            # Heat pump min power thermal output
            def min_power_th_rule(_b, t):
                return (_b.power_th_h[t] >= _b.on_off_h[t] * _b.power_th_h_min[t])
            self.model.blk_hp_h.min_power_el_c = pyo.Constraint(self.model.timeindex, rule=min_power_th_rule)

            # Transformation (input-output) correlation
            def transform_in_out_rule(_b, t):
                return (_b.power_th_h[t] == (_b.power_el_h[t] * _b.cop[t]))
            self.model.blk_hp_h.transform_in_out_c = pyo.Constraint(self.model.timeindex, rule=transform_in_out_rule)

            # Definition of minimal runtime constraint
            if self.timestep == 900:
                ## Heating mode
                # Define constraint rule
                min_runtime_steps = 4                                               #  equals 4x15min=1h
                # Define constraint rule
                def min_runtime_constraint1(_b, t):
                    if (t == self.model.timeindex.last()
                        or t == (self.model.timeindex.last()-1)
                        or t == (self.model.timeindex.last()-2)):
                        return (pyo.Constraint.Skip)
                    elif t == self.model.timeindex.first():
                        return ((_b.on_off_h[t]+_b.on_off_h[t+1]+_b.on_off_h[t+2]+_b.on_off_h[t+3]) >= (min_runtime_steps * (_b.on_off_h[t])))
                    else:
                        return ((_b.on_off_h[t]+_b.on_off_h[t+1]+_b.on_off_h[t+2]+_b.on_off_h[t+3]) >= (min_runtime_steps * (_b.on_off_h[t]-_b.on_off_h[t-1])))
                self.model.blk_hp_h.min_runtime_c = pyo.Constraint(self.model.timeindex, rule=min_runtime_constraint1)
            else:
                pass


            ## Heat pump in cooling mode
            if self.cooling_mode == "True":
                ## Max thermal output power and CoP/EER calculation
                # Get primary input tempertaure
                self.temperature_in_prim = self.temperature_in_prim_list
                # Calculate max possible thermal output power
                self.get_power_c()

                # Heat pump block (cooling mode)
                self.model.blk_hp_c = pyo.Block()

                # Define parameters
                self.model.blk_hp_c.power_th_c_max = pyo.Param(self.model.timeindex, initialize=self.data_prep(list(self.power_th_c_max)))
                self.model.blk_hp_c.power_th_c_min = pyo.Param(self.model.timeindex, initialize=self.data_prep(list(self.power_th_c_min)))
                self.model.blk_hp_c.eer = pyo.Param(self.model.timeindex, initialize=self.data_prep(list(self.eer)))
                # Define variables
                self.model.blk_hp_c.on_off_c = pyo.Var(self.model.timeindex, domain=pyo.Binary)                               # On/off status of component: 0=off and 1=on (needed for minimal and maximal power control)
                self.model.blk_hp_c.power_th_c = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)
                self.model.blk_hp_c.power_el_c = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)

                # Define constraints
                # Heat pump max power thermal output
                def max_power_th_rule(_b, t):
                    return (_b.power_th_c[t] <= _b.on_off_c[t] * _b.power_th_c_max[t])
                self.model.blk_hp_c.max_power_th_c = pyo.Constraint(self.model.timeindex, rule=max_power_th_rule)

                # Heat pump min power thermal output
                def min_power_th_rule(_b, t):
                    return (_b.power_th_c[t] >= _b.on_off_c[t] * _b.power_th_c_min[t])
                self.model.blk_hp_c.min_power_el_c = pyo.Constraint(self.model.timeindex, rule=min_power_th_rule)

                # Transformation (input-output) correlation
                def transform_in_out_rule(_b, t):
                    return (_b.power_th_c[t] == (_b.power_el_c[t] * _b.eer[t]))
                self.model.blk_hp_c.transform_in_out_c = pyo.Constraint(self.model.timeindex, rule=transform_in_out_rule)


                ## Additional constraint to hinder parallel operation in heating and cooling mode
                def hp_operation_rule(m, t):
                    return ((m.blk_hp_h.on_off_h[t] + m.blk_hp_c.on_off_c[t]) <= 1)
                self.model.hp_operation_c = pyo.Constraint(self.model.timeindex, rule=hp_operation_rule)


                # Definition of minimal runtime constraint
                if self.timestep == 900:
                    # Define constraint rule
                    min_runtime_steps = 4                                               #  equals 4x15min=1h
                    # Define constraint rule
                    def min_runtime_constraint1(_b, t):
                        if (t == self.model.timeindex.last()
                            or t == (self.model.timeindex.last()-1)
                            or t == (self.model.timeindex.last()-2)):
                            return (pyo.Constraint.Skip)
                        elif t == self.model.timeindex.first():
                            return ((_b.on_off_c[t]+_b.on_off_c[t+1]+_b.on_off_c[t+2]+_b.on_off_c[t+3]) >= (min_runtime_steps * (_b.on_off_c[t])))
                        else:
                            return ((_b.on_off_c[t]+_b.on_off_c[t+1]+_b.on_off_c[t+2]+_b.on_off_c[t+3]) >= (min_runtime_steps * (_b.on_off_c[t]-_b.on_off_c[t-1])))
                    self.model.blk_hp_c.min_runtime_c = pyo.Constraint(self.model.timeindex, rule=min_runtime_constraint1)
                else:
                    pass


        # Incase capacity is 0 - no variables - only params=0!
        else:
            self.model.blk_hp_h.on_off_h = pyo.Param(self.model.timeindex, initialize=0)
            self.model.blk_hp_h.power_th_h = pyo.Param(self.model.timeindex, initialize=0)
            self.model.blk_hp_h.power_el_h = pyo.Param(self.model.timeindex, initialize=0)
            self.model.blk_hp_h.cop = pyo.Param(self.model.timeindex, initialize=0)
            if self.cooling_mode == "True":
                self.model.blk_hp_c.on_off_c = pyo.Param(self.model.timeindex, initialize=0)
                self.model.blk_hp_c.power_th_c = pyo.Param(self.model.timeindex, initialize=0)
                self.model.blk_hp_c.power_el_c = pyo.Param(self.model.timeindex, initialize=0)
                self.model.blk_hp_c.eer = pyo.Param(self.model.timeindex, initialize=0)


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
        self.on_off_h_list = list(self.model.blk_hp_h.on_off_h.extract_values().values())
        self.power_el_h_list = list(self.model.blk_hp_h.power_el_h.extract_values().values())
        self.power_th_h_list = list(self.model.blk_hp_h.power_th_h.extract_values().values())
        self.cop_list = list(self.model.blk_hp_h.cop.extract_values().values())
        ## Maximum possible values can be used for validation with direct usage of hplib
        self.power_th_h_max_list = list(self.model.blk_hp_h.power_th_h_max.extract_values().values())
        self.power_th_h_min_list = list(self.model.blk_hp_h.power_th_h_min.extract_values().values())
        # Total electric power list
        self.power_el_list = list(np.array(self.power_el_h_list))

        if self.cooling_mode == "True":
            self.on_off_c_list = list(self.model.blk_hp_c.on_off_c.extract_values().values())
            self.power_el_c_list = list(self.model.blk_hp_c.power_el_c.extract_values().values())
            self.power_th_c_list = list(self.model.blk_hp_c.power_th_c.extract_values().values())
            self.eer_list = list(self.model.blk_hp_c.eer.extract_values().values())
            ## Maximum possible values can be used for validation with direct usage of hplib
            self.power_th_c_max_list = list(self.model.blk_hp_c.power_th_c_max.extract_values().values())
            self.power_th_c_min_list = list(self.model.blk_hp_c.power_th_c_min.extract_values().values())
            # Total electric power list
            self.power_el_list = list(np.array(self.power_el_h_list) + np.array(self.power_el_c_list))


    def get_temperature_in_prim(self):
        """To get heat pump primary-side input temperature.
        In case of air-water heat pumps this is the ambient temperature.
        In case of brine-water heat pumps this is the brine tempertaure

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Function computes temperature_in_prim_list as a batch for all timesteps at once, as tempertaure_Ambient is pandas.Series of howl timeframe
        - In this function transformation from K to °C takes place, as hplib functions use °C and env.temperature_ambient has K.
        - Brinw temperature calculation is based on hplib
        - Original source: „WP Monitor“ Feldmessung von Wärmepumpenanlagen S. 115, Frauenhofer ISE, 2014
        """

        # Air-water heat pumps
        if self.source_type == 'air-water':
            # Set primary input tempertuare to air tempertaure
            self.temperature_in_prim_list = self.env.temperature_ambient - 273.15

        # Brine-water heat pumps
        elif self.source_type == 'brine-water':
            ## Resample ambient temperature h to d
            self.temperature_ambient = self.env.temperature_ambient - 273.15
            self.temperature_ambient_d = self.temperature_ambient.resample('1d').mean()

            ## Calculate daily brine temperature
            self.temperature_brine_d = (-0.0003*self.temperature_ambient_d**3
                                        + 0.0086*self.temperature_ambient_d**2
                                        + 0.3047*self.temperature_ambient_d
                                        + 5.0647)
            # Prevent rising brine temperature at air temperatures below -10°C
            # Fitting function is not valid below -10°C ambient temperature
            for i in range(0, len(self.temperature_ambient_d)):
                if self.temperature_ambient_d[i] <= -10:
                    self.temperature_brine_d[i] = 3

            ## Resample brine temperature d to h
            # Add dummy last timestep (needed to upsample from D to H correctly)
            last_value = pd.Series(data=0.0,
                                   index=[self.temperature_brine_d.index[-1] + 1*self.temperature_brine_d.index.freq])

            self.temperature_brine_d = pd.concat([self.temperature_brine_d, last_value])
            self.temperature_brine = self.temperature_brine_d.resample('1H', closed='left').ffill()
            # Drop last dummy timestep
            self.temperature_brine = self.temperature_brine.head(-1)

            ## Set primary input temperature to brine tempertaure
            self.temperature_in_prim_list = self.temperature_brine

        else:
            print('Heat pump specification is unvalid, air-water or brine-water allowed!')


    def get_power_h(self):
        """Heating mode: Calculate maximum thermal power output and cop/eer of heat pump

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - hplib functions are in W, transfrmation to kW necessary
        - Function computes temperature_in_prim_list as a batch for all timesteps at once, as tempertaure_ambient is pandas.Series of howl timeframe
        - Calculation is done according to fitting paraneters from hplib.
            - https://github.com/RE-Lab-Projects/hplib
            - hplib assumes that return temp needs to be heated up by 5K to flow temp, this does not work with heat storage, but has only influence on mass flow, which is not considered here.
        - hplib enables only calculation of CoP/EER and P_el with coefficeints, therefore P_th is calculated via P_th_h=P_el*CoP
        - One could implement here further restrictions on max power output dependent on temperatures, see hplib for details.
        """

        ## Heating mode
        # Get heat pump sec output (flow) temperature [°C]
        self.temperature_out_sec = self.temperature_out_sec_heating_mode

        # Calculate COP
        self.cop = (self.p1_cop * self.temperature_in_prim
                   + self.p2_cop * self.temperature_out_sec
                   + self.p3_cop
                   + self.p4_cop * self.temperature_in_prim)

        # [kW] Calculate electric power (hplib function is in W, transofmration to kW)
        self.power_el_h_max = (self.power_scaling * (self.p_el_h_ref  *
                            (self.p1_p_el_h * self.temperature_in_prim
                            + self.p2_p_el_h * self.temperature_out_sec
                            + self.p3_p_el_h
                            + self.p4_p_el_h * self.temperature_in_prim))) / 1000


        # Operation restriction: compare hplib Z.591-612)
        # [kW] 25% part load electric power at -7 primary input temperature
        self.power_el_h_25 = (self.power_scaling * 0.25 * (self.p_el_h_ref *
                             (self.p1_p_el_h * (-7)
                             + self.p2_p_el_h * self.temperature_out_sec
                             + self.p3_p_el_h
                             + self.p4_p_el_h * (-7)))) / 1000

        for i in range(0, len(self.power_el_h_max)):
            if self.power_el_h_max[i] < self.power_el_h_25:
                self.power_el_h_max[i] = self.power_el_h_25

        # Calculate thermal power
        self.power_th_h_max = self.power_el_h_max * self.cop
        self.power_th_h_min = self.power_th_h_max * self.part_load_min

        # Operation restriction: check for low COP
        for i in range(0, len(self.cop)):
            if self.cop[i] <= 1:
                print('Attention: Heat pump heating mode shows COP < 1. Can not be operated!')
                self.cop[i] = 1
                self.power_el_h_max[i] = (self.p_th_h_ref/1000) * self.power_scaling
                self.power_th_h_max[i] = (self.p_th_h_ref/1000) * self.power_scaling
                self.power_th_h_min[i] = (self.p_th_h_ref/1000) * self.part_load_min

        ## Weitere operating range Einschränkungen vernachlässigt (siehe hplib Z.630-637)


    def get_power_c(self):
        """Cooling mode: Calculates maximum thermal power output and cop/eer of heat pump

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - hplib functions are in W, transfrmation to kW necessary
        - Function computes temperature_in_prim_list as a batch for all timesteps at once, as tempertaure_Ambient is pandas.Series of howl timeframe
        - Calculation is done according to fitting paraneters from hplib.
            - https://github.com/RE-Lab-Projects/hplib
        - hplib enables only calculation of CoP/EER and P_el with coefficeints, therefore P_th is calculated via P_th_h=P_el*CoP
        - One could imple,ent here further restrictions on max power output dependent on temperatures, see hplib for details.
        """

        ## Cooling mode
        # Get heat pump output (flow) tempertaure [°C]
        self.temperature_out_sec = self.temperature_out_sec_cooling_mode

        # Calculate EER
        self.eer = (self.p1_eer * self.temperature_in_prim
                    + self.p2_eer * self.temperature_out_sec
                    + self.p3_eer
                    + self.p4_eer * self.temperature_in_prim)

        # Calculate electric power
        # Operation restriction: Minimal temperature operating point 25°C (298.15K) for input/ambient temperature (Compare hplib Z.640-662)
        for i in range(0, len(self.temperature_in_prim)):
            if self.temperature_in_prim[i] < 25:
                self.temperature_in_prim[i] = 25

        # [kW] Electric power
        self.power_el_c_max = (self.power_scaling * (self.p_el_c_ref *
                            (self.p1_p_el_c * self.temperature_in_prim
                            + self.p2_p_el_c * self.temperature_out_sec
                            + self.p3_p_el_c
                            + self.p4_p_el_c * self.temperature_in_prim))) / 1000

        # [kW] Calculate thermal power
        self.power_th_c_max = self.power_el_c_max * self.eer
        self.power_th_c_min = self.power_th_c_max * self.part_load_min


        # Operation restriction: Check for low EER
        for i in range(0, len(self.eer)):
            if self.eer[i] < 1 or self.power_el_c_max[i] < 0:
                print('Attention: Heat pump cooling mode shows EER < 1 or negative electric power. Can not be operated!')
                self.eer[i] = 0
                self.power_el_c_max[i] = 0
                self.power_th_c_max[i] = 0
                self.power_th_c_min[i] = 0


    def get_state_of_destruction(self):
        """Calculates the component state of destruction (SoD) and time of
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
        - as self.time starts at 0 (due to Python), time+1 is sued for SoD calculation. Otherwise no aging occurs at first tiestep (self.time=0)

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
        """Calculates the component specific capex and fixed opex for a neighborhood scenario where multiple systems are installed.

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
        if self.power_th_h_nom != 0:
            # For single building scenarios - SB
            if self.eco_no_systems == 1:
                # [€$/Wth] Initialize specific capex
                self.capex_specific = (self.capex_p1 * (self.size_nominal/self.eco_no_systems)**self.capex_p2)
                # [€$/Wth] Initialize specific fixed opex
                self.opex_fix_specific = (self.opex_fix_p1 * self.capex_specific)
            # For neigborhood scenarios - NH
            else:
                # Get size distribution of PV systems in neighborhood
                self.size_nominal_distribution = self.nh_loader.get_hp_size_distribution()
                # Calculate specific capex distribution for different PV sizes
                self.capex_specific_distribution = [(self.capex_p1 * (self.size_nominal*j)**self.capex_p2) if j>0 else 0 for j in self.size_nominal_distribution]
                # [€$/kWp] Get NH specific capex as mean value of distribution
                self.capex_specific =  np.mean([i for i in self.capex_specific_distribution if i != 0])
                # [€$/kWp] Initialize specific fixed opex
                self.opex_fix_specific = (self.opex_fix_p1 * self.capex_specific)
        # No capex/opex fix in case of no installation
        else:
            self.capex_specific = 0
            self.opex_fix_specific = 0
