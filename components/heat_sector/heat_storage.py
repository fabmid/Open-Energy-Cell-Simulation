import pyomo.environ as pyo
import math
import numpy as np

import data_loader
from simulatable import Simulatable
from serializable import Serializable
from optimizable import Optimizable


class Heat_storage(Serializable, Simulatable, Optimizable):
    """Relevant methods to calculate heat storage temperature.
        
     Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    capacity_nominal_kwh : `int`
        [kWh] Installed storage capacity in kilo-watt-hours.
    environment : `class`
        To get access to solar irradiation, ambient temperature and windspeed data.
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
        None : `None`
    """

    def __init__(self,
                 timestep,
                 capacity_nominal_kwh,
                 env, 
                 file_path=None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for heat storage model specified')
            self.specification = "Heat Storage_Paradigma Aqua Expresso III"     # [-] Heat storage specification
            self.state_of_charge_initial = 0.5                                  # [] Initial SoC
            self.state_of_charge_balanced == "True"                             # [] Indicattion if SoC(0)==SoC(end) or not
            self.self_discharge_rate = 1.3888e-06                               # [] Self discharge rate, e.g. 0.5%/h = 0.005/(3600)
            self.coeff_loss_flex = 0.005                                        # [1/h] Energy loss coefficient dependent on charge level of TES        
            self.coeff_loss_static = 0.001                                      # [1/h] Energy loss coefficient of unusable energy content (between minimum storage and ambient temperature)
            self.end_of_charge_constant = 1.0                                   # [] End of charge SoC level
            self.end_of_discharge_constant = 0.0                                # [] End of discharge SoC level
            self.efficiency_constant = 0.9                                      # [] Charge and discharge efficiency    
            self.c_rate_max = 1.0                                               # [] Maxium charge/discharge c-Rate
            self.density_fluid = 1060                                           # [kg/m3] Dendity Fluid Heat Storage
            self.heat_capacity_fluid = 4182                                     # [J/(kg K)] Heat capacity Fluid Solar
            self.temperature_minimum = 298.15                                   # [K] Minimum heat storage temperature
            self.temperature_maximum = 323.15                                   # [K] Maximum heat storage temperature          
            self.temperature_ambient = 293.15                                   # [K] Heating room temperature
            self.eco_no_systems = 1                                             # [1] The number of systems the peak power is allocated on
            self.capex_p1 = 0.0                                                 # [€$/kWh] capex: Parameter1 (gradient) for specific capex definition (pendent on thermal output power)
            self.capex_p2 = 10.89                                               # [€$/kWh] capex: Parameter2 (y-intercept) for specific capex definition (dependent on thermal output power)
            self.subsidy_percentage_capex = 0.35                                           # Economic model: [%] Capex subsidy
            self.subsidy_limit = 100000.0                                       # Economic model: [€/$] Max total capex subsidy
            self.opex_fix_p1 = 0.0                                              # [€$/kWh/a] opex-fixed: % of capex
            self.opex_var = 0.0                                                 # [€$/kWh] opex-variable: Specific variable opex dependent on generated energy


        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
       
        # Integrate environment class
        self.env = env
        # [s] Timestep
        self.timestep = timestep
        
        ## Power model
        # [kWh] Storage nominal capacity between min and max temperature
        self.capacity_nominal_kwh = capacity_nominal_kwh
        # [kW] Maximum power ch/dch 
        self.power_max = self.capacity_nominal_kwh * self.c_rate_max
        
        # Determine storage dimensions
        # [m3] Storage volume
        self.volume = (self.capacity_nominal_kwh / (self.heat_capacity_fluid/1000
                      * (self.temperature_maximum-self.temperature_minimum) *(1/3600)))

        ## Economic model                                                   
        # [kWh] Initialize Nominal capacity
        self.size_nominal = self.capacity_nominal_kwh
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
        
        ## Initialization of parameter
        # Aging model
        self.replacement_set = 0
        
        ## List container to store simulation results for all timesteps
        self.state_of_destruction_list = list() 
        self.replacement_list = list()

        
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
        
        # Calculate State of Desctruction
        self.get_state_of_destruction()    
        
        ## Save component status variables for all timesteps to list 
        self.state_of_destruction_list.append(self.state_of_destruction)
        self.replacement_list.append(self.replacement)
        

    def optimization_get_block(self, model):
        """
        Pyomo: MILP Heat storage block construction
        
        Parameters
        ----------
        model : pyomo.model class instance (defined in optimizabe.py)

        Returns
        -------
        None : `None`
        """
        
        # Central pyomo model        
        self.model = model

        # Heat storage block
        self.model.blk_heat_storage = pyo.Block()

        # In case capacity is NOT 0, normal calculation  
        if self.capacity_nominal_kwh != 0:
            # Define parameters
            self.model.blk_heat_storage.capacity = pyo.Param(initialize=self.capacity_nominal_kwh)
            self.model.blk_heat_storage.power_max = pyo.Param(initialize=self.power_max)
            self.model.blk_heat_storage.efficiency = pyo.Param(initialize=self.efficiency_constant)
    
            self.model.blk_heat_storage.state_of_charge_initial = pyo.Param(initialize=self.state_of_charge_initial)        
            self.model.blk_heat_storage.end_of_charge = pyo.Param(initialize=self.end_of_charge_constant)
            self.model.blk_heat_storage.end_of_discharge = pyo.Param(initialize=self.end_of_discharge_constant)
            self.model.blk_heat_storage.coeff_loss_flex = pyo.Param(initialize=self.coeff_loss_flex)
            self.model.blk_heat_storage.coeff_loss_static = pyo.Param(initialize=self.coeff_loss_static)
            self.model.blk_heat_storage.temperature_minimum = pyo.Param(initialize=self.temperature_minimum)
            self.model.blk_heat_storage.temperature_maximum = pyo.Param(initialize=self.temperature_maximum)
            self.model.blk_heat_storage.temperature_ambient = pyo.Param(initialize=self.temperature_ambient)
    
            # Define variables
            self.model.blk_heat_storage.power_ch = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)                               # TES charging power
            self.model.blk_heat_storage.power_dch = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)                              # TES discharging power
            self.model.blk_heat_storage.state_of_charge = pyo.Var(self.model.timeindex, bounds=(self.model.blk_heat_storage.end_of_discharge, 
                                                                                                self.model.blk_heat_storage.end_of_charge))       # TES soc with end of ch/DCH levels 
            
            # Define constraints 
            # Heat storage SoC constraint
            def state_of_charge_rule(_b, t):
                # Get State of Charge/Energy
                if t == self.model.timeindex.first():
                    # Calculate energy losses
                    energy_loss = ((_b.state_of_charge_initial  * _b.capacity * _b.coeff_loss_flex
                                   + _b.capacity * ((_b.temperature_minimum-_b.temperature_ambient) 
                                    / (_b.temperature_maximum-_b.temperature_minimum)) * _b.coeff_loss_static) * (self.timestep/3600))
                    return (_b.state_of_charge[t] == _b.state_of_charge_initial 
                            + ((((_b.power_ch[t]*_b.efficiency) - (_b.power_dch[t]/_b.efficiency)) / _b.capacity) * (self.timestep/3600))
                            - (energy_loss / _b.capacity))
    
                # Calculate energy losses
                energy_loss = ((_b.state_of_charge[t-1]  * _b.capacity * _b.coeff_loss_flex
                               + _b.capacity * ((_b.temperature_minimum-_b.temperature_ambient) 
                                / (_b.temperature_maximum-_b.temperature_minimum)) * _b.coeff_loss_static) * (self.timestep/3600))              
                return (_b.state_of_charge[t] == _b.state_of_charge[t-1] 
                        + ((((_b.power_ch[t]*_b.efficiency) - (_b.power_dch[t]/_b.efficiency)) / _b.capacity) * (self.timestep/3600))
                        - (energy_loss / _b.capacity)) 
            
            self.model.blk_heat_storage.state_of_charge_c = pyo.Constraint(self.model.timeindex, rule=state_of_charge_rule)

            # Max thermal charging power
            def max_power_ch_rule(_b, t):
                return (_b.power_ch[t] <= _b.power_max)
            self.model.blk_heat_storage.max_power_ch_c = pyo.Constraint(self.model.timeindex, rule=max_power_ch_rule)
    
            # Max thermal discharging power
            def max_power_dch_rule(_b,t):
                return (_b.power_dch[t] <= _b.power_max)
            self.model.blk_heat_storage.max_power_dch_c = pyo.Constraint(self.model.timeindex, rule=max_power_dch_rule)
            
            # Constraint is only set in case first and last SoC level should be the same. Storage is balanced over simulation timeframe.
            if self.state_of_charge_balanced == "True":
                # Set the overall (of all optimized timesteps) first SoC to the overall last SoC
                def soc_last_initial_rule(_b, t):
                    if t == self.model.timeindex.last():
                        return (_b.state_of_charge[t] == _b.state_of_charge_initial)
                    else:
                        return pyo.Constraint.Skip
                self.model.blk_heat_storage.soc_last_initial_c = pyo.Constraint(self.model.timeindex, rule=soc_last_initial_rule)


        # Incase capacity is 0 - no variables - only params=0!    
        else:
            # Define variables
            self.model.blk_heat_storage.power_ch = pyo.Param(self.model.timeindex, initialize=0)
            self.model.blk_heat_storage.power_dch = pyo.Param(self.model.timeindex, initialize=0)
            self.model.blk_heat_storage.state_of_charge = pyo.Param(self.model.timeindex, initialize=0)
            
        
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
        
        ## Access of results#
        self.power_ch_list = list(self.model.blk_heat_storage.power_ch.extract_values().values())
        self.power_dch_list = list(self.model.blk_heat_storage.power_dch.extract_values().values())
        self.state_of_charge_list = list(self.model.blk_heat_storage.state_of_charge.extract_values().values())
 
        ## Transfer opti results to sim sign convention
        self.power_list = list(np.array(self.power_ch_list)-np.array(self.power_dch_list))
        

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
        if self.capacity_nominal_kwh != 0:
            # For single building scenarios - SB
            if self.eco_no_systems == 1:
                # [€$/kWh] Initialize specific capex
                self.capex_specific = (self.capex_p1 * (self.size_nominal/self.eco_no_systems)**self.capex_p2)
                # [€$/kWh] Initialize specific fixed opex
                self.opex_fix_specific = (self.opex_fix_p1 * self.capex_specific)
            # For neigborhood scenarios - NH
            else:
                # Get size distribution of PV systems in neighborhood
                self.size_nominal_distribution = self.nh_loader.get_tes_h_size_distribution()
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
            