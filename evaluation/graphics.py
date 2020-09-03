import matplotlib.pyplot as plt

class Graphics():

    def __init__(self, simulation):
        
        # Component specific parameter
        self.sim = simulation        
        
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

    def plot_load_data(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.sim.load_power_demand, '-b', label='power load demand')
        plt.xlabel('Time [date]')
        plt.ylabel('Power [W]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_pv_energy(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.sim.pv_power, '-b', label='pv power')
        #plt.plot(self.sim.timeindex, self.sim.pv_power_loss, 'r', label='pv power loss')
        plt.xlabel('Time [date]')
        plt.ylabel('Power [W]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_controller_energy(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.sim.charger_power, '-b', label='charger power')
        plt.xlabel('Time [date]')
        plt.ylabel('Power [W]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_main_energy(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.sim.power_junction_power, '-b', label='power junction')
        plt.xlabel('Time [date]')
        plt.ylabel('Power [W]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_battery_energy(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.sim.battery_management_power, '-g', label='bms power')
        plt.plot(self.sim.timeindex, self.sim.battery_power, '-b', label='battery power')
        plt.plot(self.sim.timeindex, self.sim.battery_power_loss, '-r', label='battery power loss')
        plt.xlabel('Time [date]')
        plt.ylabel('Power [W]')
        plt.legend(bbox_to_anchor=(0., 1.2), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_battery_eta(self):
        self.figure_format()

        fig, ax1 = plt.subplots(figsize=self.figsize)        
        ax1.plot(self.sim.timeindex, self.sim.battery_power_eta, 'ob', label='battery eta')
        ax1.set_ylabel('Efficiency [-]')
        ax1.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        ax2 = ax1.twinx()   
        ax2.plot(self.sim.timeindex, self.sim.battery_management_power_eta, 'xg', label='bms eta')
        ax2.set_xlabel('Time [date]')
        ax2.set_ylabel('Efficiency [-]')
        ax2.legend(bbox_to_anchor=(0.9, 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()
        
    def plot_battery_soc(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.sim.battery_state_of_charge, '-g', label='battery SoC')
        plt.xlabel('Time [date]')
        plt.ylabel('SoC [-]')
        plt.legend(bbox_to_anchor=(0., 1.2), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_components_temperature(self):
        self.figure_format()

        fig, ax1 = plt.subplots(figsize=self.figsize) 
        ax1.plot(self.sim.timeindex, self.sim.battery_temperature, '-b', label='temperature battery')
        ax1.set_ylabel('Temperature battery [C]')
        ax1.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        ax2 = ax1.twinx() 
        ax2.plot(self.sim.timeindex, self.sim.pv_temperature, ':g', label='temperature pv cell')
        ax2.set_xlabel('Time [date]')
        ax2.set_ylabel('Temperature pv [C]')
        ax2.legend(bbox_to_anchor=(0.9, 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()

    def plot_components_sod(self):
        self.figure_format()

        plt.figure(figsize=self.figsize)
        plt.plot(self.sim.timeindex, self.sim.photovoltaic_state_of_destruction, '-b', label='pv SoC')
        plt.plot(self.sim.timeindex, self.sim.battery_state_of_destruction, '-g', label='battery SoD')
        plt.plot(self.sim.timeindex, self.sim.charger_state_of_destruction, '-r', label='charger SoD')
        plt.plot(self.sim.timeindex, self.sim.battery_management_state_of_destruction, '-r', label='bms SoD')
        plt.xlabel('Time [date]')
        plt.ylabel('SoD [-]')
        plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=5)
        plt.grid()
        plt.show()