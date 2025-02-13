import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class Performance():
    '''
    Provides all relevant methods for the technical evaluation
    according to own methods and methods cited in:
        T. Khatib, I. A. Ibrahim, and A. Mohamed, 
        ‘A review on sizing methodologies of photovoltaic array and storage battery in a standalone photovoltaic system’, 
        Energy Convers. Manag., vol. 120, pp. 430–448, Jul. 2016.
    
    Methods
    -------
    calculate
    
    state_of_charge_evaluation
    technical_objectives
    days_with_cut_offs
    '''
    
    def __init__(self, simulation, timestep):
        '''
        Parameters
        ----------
        simulation : class. Main simulation class
        timestep: int. Simulation timestep in seconds
        '''        
        self.sim = simulation
        self.timestep = timestep


    def pv_evaluation(self):
        '''
        Calculate direct used and unused Pv energy
        '''
        self.pv_energy_overall_kWh_a = sum(np.asarray(self.sim.pv_charger_power)  * (self.timestep/3600)) / 1000 \
                                        / (self.sim.simulation_steps / (8760*(3600/self.timestep)))

        if self.sim.pv_charger_power == 0:
            self.pv_power_direct_use = 0
            self.pv_power_no_direct_use = 0
        else:
            # Take min value between two lists (pv_power_charger & inverter_power_load)
            self.pv_power_direct_use = [min(l1, l2) for l1, l2 in zip(self.sim.pv_charger_power, [-x for x in self.sim.inverter_power_load])]
            self.pv_power_no_direct_use = [x1 - x2 for (x1, x2) in zip(self.sim.pv_charger_power, self.pv_power_direct_use)]
  
      
    def battery_evaluation(self):
        '''
        Calculate Battery State of Charge at specific daytime
        
        Parameters
        ----------
        None
        '''   
        # Maximum & Minimum battery SoC every day
        self.state_of_charge_dayarray = np.array_split(self.sim.battery_state_of_charge, 
                                                  int((len(self.sim.battery_state_of_charge))/(24*(3600/self.timestep))))
        #Find max/min values of each day array
        self.state_of_charge_day_max  = list()
        self.state_of_charge_day_min  = list()

        for i in range(0,len(self.state_of_charge_dayarray)):
            self.state_of_charge_day_max.append(max(self.state_of_charge_dayarray[i][:]))
            self.state_of_charge_day_min.append(min(self.state_of_charge_dayarray[i][:]))


    def technical_objectives(self):
        '''
        Determines different technical objective evaluation parameters 
        Calculates:
            Loss of Power supply (LPS)
            Loss of Load Probability
            Level of Autonomy
            Autonomy_power: Amounf of power supplied (-) and taken (+) from the grid
            Autonomy_list: Time of power supplied (-1) and taken (+1) from the grid
            Grid feed- in energy [Wh]
            Grid feed-out energy [Wh]
            Grid energy balance [Wh]
            
        Parameters
        ----------
        None
        '''
        self.loss_of_power_supply_list = list()
        self.level_of_autonomy_list = list()
        # Amounf of power supplied (-) and taken (+) from the grid
        self.autonomy_power = list()
        # Time of power supplied (-1) and taken (+1) from the grid
        self.autonomy_list = list()
        
        ## Calculation of loss of power supply and pv energy not used
        for i in range(0,len(self.sim.grid_power)):
        
            # Days with grid demand
            if self.sim.grid_power[i] > 0.01: 
                self.loss_of_power_supply_list.append(self.sim.grid_power[i])
                self.level_of_autonomy_list.append(1)
                self.autonomy_power.append(self.sim.grid_power[i])
                
                self.autonomy_list.append(1)
                
            # Days with grid supply
            elif self.sim.grid_power[i] < -0.01:
                self.loss_of_power_supply_list.append(0)
                self.level_of_autonomy_list.append(0) 
                self.autonomy_power.append(self.sim.grid_power[i])
            
                self.autonomy_list.append(-1)
            # Idle case       
            else:
                self.loss_of_power_supply_list.append(0)
                self.level_of_autonomy_list.append(0) 
                self.autonomy_power.append(0)
                
                self.autonomy_list.append(0)
                
        # Loss of power Supply [kWh]
        self.loss_of_power_supply_kWh = sum(np.asarray(self.loss_of_power_supply_list)*(self.timestep/3600)) / 1000
        
        # Loss of Load Probability
        self.loss_of_load_probability = sum(self.loss_of_power_supply_list) \
                                        / (abs(sum(self.sim.load_el_power))+abs(sum(self.sim.heat_pump_power_el))+abs(sum(self.sim.heat_pump_c_power_el)))

        # Level of autonomy
        self.level_of_autonomy = 1 - (sum(self.level_of_autonomy_list)/np.count_nonzero(self.sim.load_el_power)) 

        # Grid energy feed-in [kWh/a]
        self.grid_energy_feed_in_kWh_a = sum(np.asarray([x for x in self.autonomy_power if x < 0]) * (self.timestep/3600)) / 1000 \
                                        / (self.sim.simulation_steps / (8760*(3600/self.timestep)))
        # Grid energy feed-out [kWh/a]
        self.grid_energy_feed_out_kWh_a = sum(np.asarray([x for x in self.autonomy_power if x > 0]) * (self.timestep/3600)) / 1000 \
                                        / (self.sim.simulation_steps / (8760*(3600/self.timestep)))
                                        
        # Grid energy balance feed_in - feed_out [kWh/a]
        self.grid_energy_balance_kWh_a = sum(np.asarray(self.autonomy_power)*(self.timestep/3600)) / 1000 \
                                        / (self.sim.simulation_steps / (8760*(3600/self.timestep))) 
      
    def grid_evaluation(self):
        '''
        Detailed evaluation of time of power supplied (-1) and taken (+1) from the grid
        
        Parameters
        ----------
        None
        '''
        # Day arrays of autonomy
        self.autonomy_list_day = np.array(np.split(np.array(self.autonomy_list), 
                                                   (len(self.autonomy_list)/(24*(3600/self.timestep)))
                                        ))

#        self.cut_off_day
#        # Number and percentage of days with cut offs
#        self.cut_off_day_list = list()
#        for i in range(0,len(self.cut_off_day)):
#            self.cut_off_day_list.append(max(self.cut_off_day[i,:]))
#
#        self.cut_off_day_number = sum(self.cut_off_day_list) \
#                                  / ((self.sim.simulation_steps*(self.timestep/3600))/8760)
#        self.cut_off_day_percentage = sum(self.cut_off_day_list) / len(self.cut_off_day_list)

        # Daily distribution of grid feed-in and feed-out
        self.feed_in_distribution_daily = list()
        self.feed_out_distribution_daily = list()
        
        for i in range(0,self.autonomy_list_day.shape[1]):
            # If only zeros - no calculation
            if all(x==0 for x in self.autonomy_list_day[:,i]):
                self.feed_in_distribution_daily.append(0)
                self.feed_out_distribution_daily.append(0)
            else:
                self.feed_in_distribution_daily.append(sum([x for x in self.autonomy_list_day[:,i] if x < 0]) / self.autonomy_list_day.shape[0])
                self.feed_out_distribution_daily.append(sum([x for x in self.autonomy_list_day[:,i] if x > 0]) / self.autonomy_list_day.shape[0])


    def technical_evaluation(self):
        """
        Determines different technical evaluation parameters 
        Calculates:
            Electric and heat load energy [kWh]
            Inverter energy [kWh]
            PV energy provided by the panel [kWh]
            Battery energy provided by discharge [kWh]
            Fuel cell energy provided [kWh]
            Battery energy stored by charge [kWh]
            Electrolyzer energy produced through hydrogen production [kWh]
            
            Electrolyzer mean operating hours per year [h/a]
            Fuel cell mean operation hours per year [h/a]
            
        Parameters
        ----------
        None
        """
        ## Load
        self.load_energy_el_kWh_a = abs(sum(np.asarray(self.sim.load_el_power)*(self.timestep/3600)/1000)) \
                                  / (self.sim.simulation_steps / (8760*(3600/self.timestep)))

        self.load_energy_heating_kWh_a = abs(sum(np.asarray(self.sim.load_heating_power)*(self.timestep/3600)/1000)) \
                                        / (self.sim.simulation_steps / (8760*(3600/self.timestep)))
        self.load_energy_hotwater_kWh_a = abs(sum(np.asarray(self.sim.load_hotwater_power)*(self.timestep/3600)/1000)) \
                                        / (self.sim.simulation_steps / (8760*(3600/self.timestep)))        
        self.load_energy_heat_kWh_a = self.load_energy_heating_kWh_a + self.load_energy_hotwater_kWh_a

        self.load_energy_cooling_kWh_a = abs(sum(np.asarray(self.sim.load_cooling_power)*(self.timestep/3600)/1000)) \
                                        / (self.sim.simulation_steps / (8760*(3600/self.timestep)))  
                                        
        ## Electricty
        self.inverter_energy_kWh = (sum(np.asarray(self.sim.inverter_power_load)*(self.timestep/3600)/1000))
        
        self.pv_energy_provided_kWh = (sum(np.asarray(self.pv_power_direct_use)\
                                       *(self.timestep/3600)/1000))

        self.battery_energy_provided_kWh = abs(sum(np.asarray([x for x in self.sim.battery_power if x < 0])\
                                           *(self.timestep/3600)/1000))

        self.fuelcell_energy_provided_kWh = (sum(np.asarray(self.sim.fuelcell_power_to_load) \
                                            *(self.timestep/3600)/1000))
        
#        self.fuelcell_energy_provided_kWh = (sum(np.asarray(self.sim.pv_charger_power) \
#                                        *(self.timestep/3600)/1000))

        self.battery_energy_stored_kWh = (sum(np.asarray([x for x in self.sim.battery_power if x > 0])\
                                          *(self.timestep/3600)/1000))
 
        self.electrolyzer_energy_prouced_kWh = (sum(np.asarray(self.sim.electrolyzer_power) \
                                                *(self.timestep/3600)/1000))

        ## cooling
        self.heat_pump_c_energy_el_consumed_kWh = abs(sum(np.asarray(self.sim.heat_pump_c_power_el) \
                                                *(self.timestep/3600)/1000))
        self.heat_pump_c_energy_el_consumed_kWh_a = abs(sum(np.asarray(self.sim.heat_pump_c_power_el) \
                                                *(self.timestep/3600)/1000)) \
                                                / (self.sim.simulation_steps / (8760*(3600/self.timestep)))
        self.heat_pump_c_energy_th_provided_kWh = (sum(np.asarray(self.sim.heat_pump_c_power_th) \
                                                *(self.timestep/3600)/1000))
        
        ## Heat
        self.heat_pump_energy_el_consumed_kWh = abs(sum(np.asarray(self.sim.heat_pump_power_el) \
                                                *(self.timestep/3600)/1000))
        self.heat_pump_energy_el_consumed_kWh_a = abs(sum(np.asarray(self.sim.heat_pump_power_el) \
                                                *(self.timestep/3600)/1000)) \
                                                / (self.sim.simulation_steps / (8760*(3600/self.timestep)))
        self.heat_pump_energy_th_provided_kWh = (sum(np.asarray(self.sim.heat_pump_power_th) \
                                                *(self.timestep/3600)/1000))
        
        self.electrolyzer_energy_th_provided_kWh = (sum(np.asarray(self.sim.electrolyzer_heat) \
                                                *(self.timestep/3600)/1000))
        self.fuelcell_energy_th_provided_kWh = (sum(np.asarray(self.sim.fuelcell_heat) \
                                                *(self.timestep/3600)/1000))
        
        ## Operation time
        self.electrolyzer_operating_hours_year = max(self.sim.electrolyzer_operation) * (self.timestep/3600) \
                                                 / (self.sim.simulation_steps / (8760*(3600/self.timestep)))   

        self.fuelcell_operating_hours_year = max(self.sim.fuelcell_operation) * (self.timestep/3600) \
                                             / (self.sim.simulation_steps / (8760*(3600/self.timestep)))  
         
                                        
    def print_technical_objective_functions(self):
        print('---------------------------------------------------------')
        print('Objective functions - Technical')
        print('---------------------------------------------------------')
        print('Loss of power Supply [kWh]=', round(self.loss_of_power_supply_kWh, 2))
        print('Loss of load propability [1]=', round(self.loss_of_load_probability,2))
        print('level of autonomy [1]=', round(self.level_of_autonomy,4))

        print('Grid energy feed-in [kWh/a]', round(self.grid_energy_feed_in_kWh_a, 2))
        print('Grid energy feed-out [kWh/a]', round(self.grid_energy_feed_out_kWh_a, 2))
        print('Grid energy balance [kWh/a]', round(self.grid_energy_balance_kWh_a, 2))


    def print_technical_evaluation(self):
        print('---------------------------------------------------------')
        print('Evaluation - Technical')
        print('---------------------------------------------------------')
        print('Electricty load energy [kWh/a]=',  round(self.load_energy_el_kWh_a, 2))
        print('Heating Load energy [kWh/a]=', round(self.load_energy_heating_kWh_a, 2))
        print('HotWater Load energy [kWh/a]=', round(self.load_energy_hotwater_kWh_a, 2))
        print('Heat pump energy el consumed [kWh/a]=', round(self.heat_pump_energy_el_consumed_kWh_a, 2))
        print('Cooling energy [kWh/a]=', round(self.load_energy_cooling_kWh_a, 2))
        print('Heat pump_c energy el consumed [kWh/a]=', round(self.heat_pump_c_energy_el_consumed_kWh_a, 2))
        print('---------------------------------------------------------')        
        print('PV energy produced [kWh/a]', round(self.pv_energy_overall_kWh_a, 2))
        print('---------------------------------------------------------')
        print('Inv Load el energy [kWh]=', round(self.inverter_energy_kWh, 2))
        print('PV energy provided [kWh]=', round(self.pv_energy_provided_kWh, 2))
        print('Bat energy provided (DCH) [kWh]=', round(self.battery_energy_provided_kWh, 2))
        print('FC energy provided [kWh]=', round(self.fuelcell_energy_provided_kWh, 2))
        print('Bat energy stored (CH) [kWh]=', round(self.battery_energy_stored_kWh, 2))
        print('Ely H2 energy produced [kWh]=', round(self.electrolyzer_energy_prouced_kWh, 2))
        print('---------------------------------------------------------')
        print('Heat pump energy el consumed [kWh]=', round(self.heat_pump_energy_el_consumed_kWh, 2))
        print('Heat pump energy th provided [kWh]=', round(self.heat_pump_energy_th_provided_kWh, 2))
        print('Heat pump_c energy el consumed [kWh]=', round(self.heat_pump_c_energy_el_consumed_kWh, 2))
        print('Heat pump_c energy th provided [kWh]=', round(self.heat_pump_c_energy_th_provided_kWh, 2))
        
        print('Electrolyzer energy th provided [kWh]=', round(self.electrolyzer_energy_th_provided_kWh, 2))
        print('Fuelcell energy th provided [kWh]=', round(self.fuelcell_energy_th_provided_kWh, 2))
        print('---------------------------------------------------------')
        print('Ely operation hours per year [h/a]=', round(self.electrolyzer_operating_hours_year, 2))
        print('FC operation hours per year [h/a]=', round(self.fuelcell_operating_hours_year, 2))
        