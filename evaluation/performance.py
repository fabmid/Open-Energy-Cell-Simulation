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


    def calculate(self):        
        '''
        Parameters
        ----------
        None
        '''         
        self.state_of_charge_evaluation()
        self.technical_objectives()
        self.days_with_cut_offs()


    def state_of_charge_evaluation(self):
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
            Power of load supplied
            Power of PV which is unused
            Loss of Load Probability
            Level of Autonomy
            
        Parameters
        ----------
        None
        '''
        self.loss_of_power_supply = list()
        self.power_load_supplied = list()
        self.power_pv_unused = list()
        self.level_of_autonomy_list = list()
        
        ## Calculation of loss of power supply and pv energy not used
        for i in range(0,len(self.sim.power_junction_power)):
            
            # Battery discharge case
            if self.sim.power_junction_power[i] < 0: 
                self.loss_of_power_supply.append(abs(self.sim.power_junction_power[i] \
                                                 - self.sim.battery_management_power[i] * self.sim.battery_management_efficiency[i]))
                self.power_pv_unused.append(0)
                
            # Battery charge case
            elif self.sim.power_junction_power[i] > 0:
                self.loss_of_power_supply.append(0)
                # Check if bms efficeincy is > 0
                if self.sim.battery_management_efficiency[i] > 0:
                    self.power_pv_unused.append(abs(self.sim.power_junction_power[i] \
                                                - self.sim.battery_management_power[i] / self.sim.battery_management_efficiency[i]))
                else:
                    self.power_pv_unused.append(abs(self.sim.power_junction_power[i]))
            
            # Idle case       
            else:
                self.loss_of_power_supply.append(0)
                self.power_pv_unused.append(0)

            # Determination of level of autonomy
            # Case loss of power supply - LA == 1
            if self.loss_of_power_supply[i] > 0.0001:
                self.level_of_autonomy_list.append(1)  
            # Case no loss of power supply - LA == 0
            else:
                self.level_of_autonomy_list.append(0)  
                
        # Loss of Load Probability
        self.loss_of_load_probability = sum(self.loss_of_power_supply) / sum(self.sim.load_power_demand)

        # PV energy not used per day
        self.energy_pv_unused_day = sum(self.power_pv_unused) \
                                / (len(self.power_pv_unused) / (24*(3600/self.timestep)))

        # Level of autonomy
        self.level_of_autonomy = 1 - (sum(self.level_of_autonomy_list)/np.count_nonzero(self.sim.load_power_demand)) 


    def days_with_cut_offs(self):
        '''
        Calculates Number of days with power cut offs
        
        Parameters
        ----------
        None
        '''
        # Day arrays of power cut offs
        self.cut_off_day = np.array(np.split(np.array(self.level_of_autonomy_list), 
                                             (len(self.level_of_autonomy_list)/(24*(3600/self.timestep)))
                                             ))

        # Number and percentage of days with cut offs
        self.cut_off_day_list = list()
        for i in range(0,len(self.cut_off_day)):
            self.cut_off_day_list.append(max(self.cut_off_day[i,:]))

        self.cut_off_day_number = sum(self.cut_off_day_list) \
                                  / ((self.sim.simulation_steps*(self.timestep/3600))/8760)
        self.cut_off_day_percentage = sum(self.cut_off_day_list) / len(self.cut_off_day_list)

        # Daily distribution of cut offs
        self.cut_off_day_distribution_daily = list()
        for i in range(0,24):
            if sum(self.cut_off_day[:,i]) == 0:
                self.cut_off_day_distribution_daily.append(0)
            else:
                self.cut_off_day_distribution_daily.append((self.cut_off_day[:,i]) / sum(self.cut_off_day[:,i]))


    def figure_format(self):
        MEDIUM_SIZE = 10
        BIGGER_SIZE = 12
        plt.rc('font', size=MEDIUM_SIZE)          # controls default text sizes
        plt.rc('axes', titlesize=BIGGER_SIZE)     # fontsize of the axes title
        plt.rc('axes', labelsize=BIGGER_SIZE)    # fontsize of the x and y labels
        plt.rc('xtick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
        plt.rc('ytick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
        plt.rc('legend', fontsize=MEDIUM_SIZE)    # legend fontsize
        plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
        self.figsize = (5,3)


    def plot_loss_of_power_supply(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.loss_of_power_supply, '-b', label='loss _of_power_supply')
        plt.xlabel('Time [date]')
        plt.ylabel('Loss of Power Supply [Wh]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()
        plt.show()


    def plot_soc_days(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        #Carpet plot
        plt.title('Battery state of Charge')
        plt.imshow(self.state_of_charge_dayarray, aspect='auto')
        plt.colorbar()
        plt.xlabel('Time of day [h]')
        plt.ylabel('Day of simulation timeframe')
        plt.grid()
        plt.show()
        
    def plot_cut_off_days(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        #Carpet plot
        plt.title('Power Cut offs')
        plt.imshow(self.cut_off_day, aspect='auto')
        plt.colorbar()
        plt.xlabel('Time of day [h]')
        plt.ylabel('Day of simulation timeframe')
        plt.grid()
        plt.show()


    def print_technical_objective_functions(self):
        print('---------------------------------------------------------')
        print('Objective functions - Technical')
        print('---------------------------------------------------------')
        print('Loss of power Supply [Wh]=', sum(self.loss_of_power_supply).round(2))
        print('Loss of load propability [1]=', (self.loss_of_load_probability).round(4))
        print('level of autonomy [1]=', round(self.level_of_autonomy,4))
        print('No. of days with cut off per year [d/a]=', self.cut_off_day_number)

        print('---------------------------------------------------------')
        print('Components')
        print('---------------------------------------------------------')
        print('PV Energy not used [Wh/day]', round(self.energy_pv_unused_day,2))
        print('SoC mean =', round(np.mean(self.state_of_charge_dayarray),2))
