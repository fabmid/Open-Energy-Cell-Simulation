import sys  # Define the absolute path for loading other modules
sys.path.insert(0, '../..')

import pandas as pd
import numpy as np
from collections import OrderedDict
import pyomo.environ as pyo

from serializable import Serializable
from simulatable import Simulatable
from optimizable import Optimizable

from environment import Environment
from components.electricity_sector.load_electricity import Load_Electricity
from components.electricity_sector.photovoltaic import Photovoltaic
from components.electricity_sector.battery import Battery
from components.electricity_sector.grid_electricity import Grid_Electricity
from components.heat_sector.load_heat import Load_Heat
from components.heat_sector.heat_pump import Heat_Pump
from components.heat_sector.heat_storage import Heat_storage
from components.chemical_sector.hydrogen_storage import Hydrogen_Storage
from components.chemical_sector.electrolyzer import Electrolyzer
from components.chemical_sector.fuelcell import Fuelcell

from evaluation.economics import Economics

class Milp_Problem(Serializable, Simulatable, Optimizable):
    """
    Central System class, where energy system is constructed

    Attributes
    ----------
    Serializable : class. In order to serialize system
    Simulatable : class. In order to simulate system
    Optimizable : class. In order to optimize system operation

    Methods
    -------
    simulate_non_dispatchables
    optimize_operation
    simulate_dispatchables
    calculate_economics

    Note
    ----
    """

    def __init__(self,
                 res_vars,
                 config):

        # Read config file and set key/value pairs to class attributes
        for key, value in config.items():
            setattr(self, key, value)

        ## Get component sizes from GA res
        self.pv_peak_power = [i * res_vars[0] for i in self.pv_direction_dist] # split total PV power to directions
        self.hp_power_th_nom = res_vars[1]
        self.heat_storage_capacity = res_vars[2]
        self.battery_capacity = res_vars[3]
        self.electrolyzer_power = res_vars[4]
        self.fuelcell_power = res_vars[5]
        self.hydrogen_storage_capacity = res_vars[6]

        ## Initialize system component classes
        # Environment and Load irradiation and weather timeseries data
        self.env = Environment(timestep=self.timestep)
        self.env.meteo_irradiation.read_csv(file_name=self.file_path_irradiation,
                                            simulation_steps=self.simulation_steps)
        self.env.meteo_weather.read_csv(file_name=self.file_path_weather,
                                        simulation_steps=self.simulation_steps)

        ## Electricity sector - Component classes
        # Electricity load
        self.load_electricity = Load_Electricity()
        self.load_electricity.load_demand.read_csv(file_name=self.file_path_load,
                                                   simulation_steps=self.simulation_steps)
        # Photovoltaic
        self.pv = Photovoltaic(timestep=self.timestep,
                               peak_power_arrays=self.pv_peak_power,
                               env=self.env,
                               file_path=self.file_path_components['pv'])

        # Battery
        self.battery = Battery(timestep=self.timestep,
                               capacity_nominal_kwh=self.battery_capacity,
                               env=self.env,
                               file_path=self.file_path_components['bat'])

        # Electricity grid
        self.grid_electricity = Grid_Electricity(pv=self.pv,
                                                 file_path=self.file_path_components['grid_el'])

        ## Heat sector - Component classes
        # Heat load
        self.load_heat = Load_Heat()
        self.load_heat.load_demand.read_csv(file_name=self.file_path_load,
                                            simulation_steps=self.simulation_steps)

        # Heat Pump
        self.heat_pump = Heat_Pump(timestep=self.timestep,
                                   power_th_nom=self.hp_power_th_nom,
                                   env=self.env,
                                   file_path=self.file_path_components['hp'])

        # Thermal storage
        self.heat_storage = Heat_storage(timestep=self.timestep,
                                         capacity_nominal_kwh=self.heat_storage_capacity,
                                         env=self.env,
                                         file_path=self.file_path_components['tes_h'])

        ## Hydrogen sector - Component classes
        # Electrolyzer
        self.electrolyzer = Electrolyzer(timestep=self.timestep,
                                         power_nominal=self.electrolyzer_power,
                                         file_path=self.file_path_components['ely'])
        # Fuel cell
        self.fuelcell = Fuelcell(timestep=self.timestep,
                                 power_nominal=self.fuelcell_power,
                                 file_path=self.file_path_components['fc'])
        # Hydrogen storage
        self.hydrogen_storage = Hydrogen_Storage(timestep=self.timestep,
                                                 capacity_kwh=self.hydrogen_storage_capacity,
                                                 file_path=self.file_path_components['h2'])


        # Neighborhood specific component sizes and component costs (PV, HP, TES)
        if hasattr(self, 'file_path_neighborhood_component_sizes'):
            self.pv.nh_loader.read_csv(file_name=self.file_path_neighborhood_component_sizes,
                                       simulation_steps=self.pv.eco_no_systems)
            self.heat_storage.nh_loader.read_csv(file_name=self.file_path_neighborhood_component_sizes,
                                                 simulation_steps=self.heat_storage.eco_no_systems)
            self.heat_pump.nh_loader.read_csv(file_name=self.file_path_neighborhood_component_sizes,
                                              simulation_steps=self.heat_pump.eco_no_systems)


        ## Initialize Simulatable and Optimizable class
        # Define simulatable_kwargs dict with:
        # non-dispatchables: Are simulated before operational optimization
        # dispatchables: Are simulated after operational optimization
        self.simulatable_kwargs = {'non_dispatchables': [self.env,
                                                         self.load_electricity,
                                                         self.load_heat,
                                                         self.pv,
                                                         self.grid_electricity
                                                         ],
                                   'dispatchables': [self.battery,
                                                     self.heat_pump,
                                                     self.heat_storage,
                                                     self.electrolyzer,
                                                     self.fuelcell,
                                                     self.hydrogen_storage
                                                     ]}
        Simulatable.__init__(self, **self.simulatable_kwargs)

        # Define potimizable_kwargs dict with:
        # optimizables: Need to be considered inside operational optimization
        # timestep and simulation_steps
        self.optimizable_kwargs = {'optimizables': [self.load_electricity,
                                                    self.load_heat,
                                                    self.pv,
                                                    self.battery,
                                                    self.grid_electricity,
                                                    self.heat_pump,
                                                    self.heat_storage,
                                                    self.electrolyzer,
                                                    self.fuelcell,
                                                    self.hydrogen_storage
                                                    ],
                                   'timestep': self.timestep,
                                   'simulation_steps': self.simulation_steps,
                                   'milp_solver_options': self.milp_solver_options
                                   }
        Optimizable.__init__(self, **self.optimizable_kwargs)


    # %% run simulation of non_dispatchables for every timestep
    def simulate_non_dispatchables(self):
        """
        Central simulation method for non_dispatchable components, which :
        iterates over all simulation timesteps and calls Simulatable.start/update/end()

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Performance model and Aging models inside non-dispatchable component classes are called via calculate() method
        """

        ## Define needs_update initially to True
        self.simulation_needs_update = True

        # As long as needs_update = True simulation takes place
        if self.simulation_needs_update:
            ## Simulatable: Define which childs shall be simulated
            self.childs = self.childs_non_dispatchables

            ## Call simulation.test() method to exclude all components with capacity=0 from calculation
            self.simulation_test()
            ## Call simulation.load() method (inheret from Simulatable) to load data (pvlib, windpowerlib)
            self.simulation_init()
            ## Call start method (inheret from Simulatable) to start simulation
            self.simulation_start()

            ## Iteration over all simulation steps
            for t in range(0, self.simulation_steps):
                ## Call calculate method to call calculation method of all components and carriers
                self.simulation_calculate()
                ## Call update method to go one timestep further for all components
                self.simulation_update()

            ## Simulation over: set needs_update to false and call end method
            self.simulation_needs_update = False
            self.simulation_end()


    # %% run operational optimization
    def optimize_operation(self):
        """
        Central optimization method for optimizable components.
        Operation is optimized based on MILP formulation

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        """

        ## Define pyomo blocks of all components
        self.optimization_get_block()

        ## Define the Bus constraints
        # Balanced electricity bus rule
        def balanced_bus_electricity_rule(m, t):
            return (0 == (- m.blk_electricity_load.power[t]
                          - m.blk_hp_h.power_el_h[t]
                          + m.blk_pv.power[t]
                          + m.blk_battery.power_dch[t]
                          - m.blk_battery.power_ch[t]
                          + m.blk_grid_electricity.power_feed_out[t]
                          - m.blk_grid_electricity.power_feed_in[t]
                          - m.blk_ely.power_el[t]
                          + m.blk_fc.power_el[t]
                          ))

        self.model.bus_electricity_c = pyo.Constraint(self.model.timeindex, rule=balanced_bus_electricity_rule)

        # Balanced heat bus rule
        try:
            def balanced_bus_heat_rule(m, t):
                return (0 == (- m.blk_heat_load.power[t]
                              + m.blk_ely.power_th[t]
                              + m.blk_fc.power_th[t]
                              + m.blk_hp_h.power_th_h[t]
                              + m.blk_heat_storage.power_dch[t]
                              - m.blk_heat_storage.power_ch[t]
                              ))

            self.model.bus_heat_c = pyo.Constraint(self.model.timeindex, rule=balanced_bus_heat_rule)
        except:
            print('No heat bus constraint constructed')

        # Balanced hydrogen bus rule
        try:
            def balanced_bus_hydrogen_rule(m, t):
                return (0 == (m.blk_ely.power_h2[t]
                              - m.blk_fc.power_h2[t]
                              + m.blk_hydrogen_storage.power_dch[t]
                              - m.blk_hydrogen_storage.power_ch[t]
                              ))

            self.model.bus_hydrogen_c = pyo.Constraint(self.model.timeindex, rule=balanced_bus_hydrogen_rule)
        except:
            print('No hydrogen bus constraint constructed')


        ## Energy arbitrage constraint with Big M formulation
        # Define variables and params
        self.model.arbitrage_y = pyo.Var(self.model.timeindex, domain=pyo.Binary)
        self.model.arbitrage_expr = pyo.Var(self.model.timeindex, domain=pyo.NonNegativeReals)
        # Define value of BigM param
        self.bigM = max([max((load+self.hp_power_th_nom), pv) for (load, pv) in zip(self.load_electricity.power_list, self.pv.power_list)])
        self.model.arbitrage_M = pyo.Param(self.model.timeindex, initialize=self.bigM)

        # Energy arbitrage constraint
        def constraint_arbitrage_energy_rule(m, t):
            return (m.blk_grid_electricity.power_feed_out[t] <= m.arbitrage_expr[t])
        self.model.arbitrage_energy_c = pyo.Constraint(self.model.timeindex, rule=constraint_arbitrage_energy_rule)

        # representing expr in energy arbitrage constraint
        def constraint_arbitrage_1_rule(m, t):
            return (m.arbitrage_expr[t] >= 0)
        self.model.arbitrage_1_c = pyo.Constraint(self.model.timeindex, rule=constraint_arbitrage_1_rule)

        def constraint_arbitrage_2_rule(m, t):
            return (m.arbitrage_expr[t] >= (m.blk_electricity_load.power[t] + m.blk_hp_h.power_el_h[t] - m.blk_pv.power[t]))
        self.model.arbitrage_2_c = pyo.Constraint(self.model.timeindex, rule=constraint_arbitrage_2_rule)

        def constraint_arbitrage_3_rule(m, t):
            return (m.arbitrage_expr[t] <= (0 + m.arbitrage_M[t] * (1 - m.arbitrage_y[t])))
        self.model.arbitrage_3_c = pyo.Constraint(self.model.timeindex, rule=constraint_arbitrage_3_rule)

        def constraint_arbitrage_4_rule(m, t):
            return (m.arbitrage_expr[t] <= ((m.blk_electricity_load.power[t] + m.blk_hp_h.power_el_h[t] - m.blk_pv.power[t])
                                            + m.arbitrage_M[t] * m.arbitrage_y[t]))
        self.model.arbitrage_4_c = pyo.Constraint(self.model.timeindex, rule=constraint_arbitrage_4_rule)

        # Hydrogen charge-discharge constraint
        # Electrolyzer and fuel cell are not allowed to be operated parallel
        def constraint_hydrogen_ch_dch_rule(m, t):
            return (m.blk_ely.power_el[t] *  m.blk_fc.power_el[t] == 0)

        self.model.hydrogen_ch_dch_rule_c = pyo.Constraint(self.model.timeindex, rule=constraint_hydrogen_ch_dch_rule)


        # %% Define the objective function

        def obj_rule(m):
            """
            Define the MILP objective function.

            Parameters
            ----------
            None : `None`

            Returns
            -------
            None : `None`

            Note
            ----
            - different objective functions can be defined here.
            """

            # Obj1: Min opex
            if self.milp_obj_fct == 'min_opex':
                opex_min = pyo.quicksum((m.blk_grid_electricity.power_feed_out[t] * (self.timestep / 3600) *
                                          m.blk_grid_electricity.cost_buy[t])
                                          - (m.blk_grid_electricity.power_feed_in[t] * (self.timestep / 3600) *
                                          m.blk_grid_electricity.cost_sell[t])
                                        for t in m.timeindex)
                return opex_min

            else:
                print('MILP objective function definition not correctly defined!')

        ## Define objective function fro MILP model
        self.model.obj = pyo.Objective(rule=obj_rule, sense=1)  # minimize=1, maximize=-1

        if self.milp_debug == "True":
            self.model.write('results/gurobi/model_' + self.name + '.mps')
        elif self.milp_debug == "False":
            pass
        else:
            print('Solver debug parameter not correctly set')

        ## Run model and save results
        self.optimization_run_model()
        self.optimization_save_results()

        if self.milp_debug == "True":
            with open('results/pyomo/model_' + self.name + '.txt', 'w') as output_file:
                self.model.pprint(output_file)
        elif self.milp_debug == "False":
            pass
        else:
            print('Solver debug parameter not correctly set')


    # %% run simulation of dispatchables for every timestep
    def simulate_dispatchables(self):
        """
        Central simulation method for dispatchable components, which:
        iterates over all simulation timesteps and calls Simulatable.start/update/end()

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Optimized performance model parameters are included in dispatchable component classes
        - Then Aging models inside dispatchable component classes are called via calculate() method
        """

        ## Define needs_update initially to True
        self.simulation_needs_update = True

        # As long as needs_update = True simulation takes place
        if self.simulation_needs_update:
            ## Simulatable: Define which childs shall be simulated
            self.childs = self.childs_dispatchables

            ## Call simulation.test() method to exclude all components with capacity=0 from calculation
            self.simulation_test()
            ## Call simulation.load() method (inheret from Simulatable) to create empty result lists
            self.simulation_init()
            ## Call start method (inheret from Simulatable) to start simulation
            self.simulation_start()

            ## Iteration over all simulation steps
            for t in range(0, self.simulation_steps):
                ## Call calculate method to call calculation method of all components and carriers
                self.simulation_calculate()
                ## Call update method to go one timestep further for all components
                self.simulation_update()

            ## Simulation over: set needs_update to false and call end method
            self.simulation_needs_update = False
            self.simulation_end()


    # %% calculate economic performance indicators
    def calculate_economics(self):
        """
        Calculation of of system economics

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        """

        # Components with capital costs
        self.eco_components = {'grid_el': self.grid_electricity,
                               'pv': self.pv,
                               'bat': self.battery,
                               'ely': self.electrolyzer,
                               'fc': self.fuelcell,
                               'h2': self.hydrogen_storage,
                               'hp': self.heat_pump,
                               'tes_h': self.heat_storage
                               }

        # Total load [kWh]
        self.load_total = (sum(self.load_electricity.power_list)
                           + sum(self.load_heat.power_list)) * (self.timestep / 3600)

        # Initialize economics class
        self.neighborhood = None
        self.eco = Economics(components=self.eco_components,
                             load_total=self.load_total,
                             timestep=self.timestep,
                             simulation_steps=self.simulation_steps,
                             file_path=self.file_path_economic,
                             neighborhood=self.neighborhood)

        # Calculate economic performance
        self.eco.calculate()

        # Get capacity and amrginal cost components
        self.eco_results_capacity = self.eco.results_capacity_costs
        self.eco_results_capacity_buildings = self.eco.capacity_costs_buildings
        self.eco_results_marginal = self.eco.results_marginal_costs
        self.eco_results_marginal_buildings = self.eco.marginal_costs_buildings
        self.eco_results_marginal_nh = self.eco.results_marginal_costs_nh


    #%% Calculate technical performance
    def calculate_performance(self):
        """
        Calculation of of system technical performance

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        """

        # Get shared pwer timeseries from neighborhood
        if self.neighborhood != None:
            self.neighborhood_power_shared_direct_nh = self.neighborhood.power_shared_direct_nh
        else:
            self.neighborhood_power_shared_direct_nh = list(np.zeros(len(self.env.timeindex_list)))

        # Summarize most important parameters
        self.results_main = pd.DataFrame(
                        data=OrderedDict({'index':np.arange(1,self.simulation_steps+1),
                                          'load_el_power':self.load_electricity.power_list,
                                          'load_th_h_power':self.load_heat.power_list,
                                          'pv_power':self.pv.power_list,
                                          'hp_power_el':self.heat_pump.power_el_list,
                                          'hp_cop':self.heat_pump.cop_list,
                                          'hp_power_th_h':self.heat_pump.power_th_h_list,
                                          'tes_h_power':self.heat_storage.power_list,
                                          'tes_h_soc':self.heat_storage.state_of_charge_list,
                                          'bat_power':self.battery.power_list,
                                          'bat_power_ch':self.battery.power_ch_list,
                                          'bat_power_dch':self.battery.power_dch_list,
                                          'bat_soc':self.battery.state_of_charge_list,
                                          'ely_power_el':self.electrolyzer.power_el_list,
                                          'ely_power_h2':self.electrolyzer.power_h2_list,
                                          'ely_power_th':self.electrolyzer.power_th_list,
                                          'fc_power_el':self.fuelcell.power_el_list,
                                          'fc_power_h2':self.fuelcell.power_h2_list,
                                          'fc_power_th':self.fuelcell.power_th_list,
                                          'h2_power':self.hydrogen_storage.power_list,
                                          'h2_power_ch':self.hydrogen_storage.power_ch_list,
                                          'h2_power_dch':self.hydrogen_storage.power_dch_list,
                                          'h2_soc':self.hydrogen_storage.state_of_charge_list,
                                          'grid_power':self.grid_electricity.power_list,
                                          'grid_power_feed_in':self.grid_electricity.power_feed_in_list,
                                          'grid_power_feed_out':self.grid_electricity.power_feed_out_list,
                                          'pv_sod':self.pv.state_of_destruction_list,
                                          'hp_sod':self.heat_pump.state_of_destruction_list,
                                          'tes_h_sod':self.heat_storage.state_of_destruction_list,
                                          'bat_sod':self.battery.state_of_destruction_list,
                                          'ely_sod':self.electrolyzer.state_of_destruction_list,
                                          'fc_sod':self.fuelcell.state_of_destruction_list,
                                          'h2_sod':self.hydrogen_storage.state_of_destruction_list,
                                          'nh_power_shared':self.neighborhood_power_shared_direct_nh
                                          }), index=self.env.timeindex_list)

        # Calculate grid feed-out energy [kWh]
        self.grid_feed_out_energy = self.results_main['grid_power_feed_out'].resample('H').mean().sum()