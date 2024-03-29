from simulatable import Simulatable

class Carrier_el(Simulatable):
    """Relevant methods of the power junction to compute all power input and
    output flows and the resulting battery power flow.

    Parameters
    ----------
    input_link_1 : `class`
        [-] Component 1 that provides input power to carrier
    input_link_2 : `class`
        [-] Component 2 that provides input power to carrier
    output_link_1 : `class`
        [-] Component 1 that provides output power to carrier
    output_link_2 : `class`
        [-] Component 2 that provides output power to carrier

    Note
    ----
    - Carrier can be electricity or heat carrier.
    - It's input and output flows are in each timestep balanced and itself has no storage cap.
    - Power flow sign is defined as carrier inputs (+) and outputs (-).
    """

    def __init__(self,
                 input_links,
                 output_links,
                 battery_link,
                 electrolyzer_link,
                 fuelcell_link,
                 inverter_link,
                 grid_link,
                 env):

        # Integrate simulatable class and connected component classes
        Simulatable.__init__(self)

        self.input_links = input_links
        self.output_links = output_links
        self.battery = battery_link
        self.electrolyzer = electrolyzer_link
        self.fuelcell = fuelcell_link
        self.inverter = inverter_link
        self.grid = grid_link
        
        # Integrate environment class
        self.env = env
        
        # Initialize power flow
        self.power_0 = 0
        self.power_storage = 0
        self.power_fc_to_battery = 0
        self.power_fc_to_load = 0

        
    def calculate(self):
        """Energy Management system.
        
        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`
        
        Note
        ----
        - Calculates power difference of input and output power flows of carrier.
        - Runs battery, fuel cell and electrolyzer EMS according to implemented algorithm.
        """

        ## Energy Management System          
        # Summation of input links power
        self.input_links_power = 0
        for i in range(len(self.input_links)):
            self.input_links_power += self.input_links[i].power
            
        # Summation of output links power
        self.output_links_power = 0
        for i in range(len(self.output_links)):
            self.output_links_power += self.output_links[i].power
        
        # Load Inverter: Convert output links AC power to DC
        self.inverter.link_power = self.output_links_power
        self.inverter.get_power_input()
        
        self.inverter.power_load = self.inverter.power
        self.inverter.efficiency_load = self.inverter.efficiency
        
        self.output_links_power = self.inverter.power_load
        
        # Calculate power difference of input/output links
        self.power_0 = self.input_links_power + self.output_links_power

      
        ## Surplus energy
        if self.power_0 > 0:           
            # Call battery EMS system
            self.ems_battery(input_link_power=self.power_0)        
               
            # Recalc power after battery usage (1.component)
            self.power_1 = round((self.power_0 - self.battery.power),4)
            
            # Call electrolyzer EMS systen
            self.ems_electrolyzer(input_link_power=self.power_1)
            self.ems_fuelcell(output_link_power=0)

            # Recalc power after hydrogen system usage (2.component)
            self.power_2 = self.power_1 + self.fuelcell.power_to_load - self.electrolyzer.power       
            
       
        ## Demand energy
        elif self.power_0 < 0:
            # Battery provides demand energy
            if self.battery.state_of_charge >= self.fuelcell.battery_soc_min:
                # Call battery EMS system
                self.ems_battery(input_link_power=self.power_0)  
                
                # Recalc power after battery usage (1.component)
                self.power_1 = round((self.power_0 - self.battery.power),4)
                
                # Call fuel cell EMS system
                self.ems_fuelcell(output_link_power=self.power_1)
                self.ems_electrolyzer(input_link_power=0)   
                
                # Recalc power after hydrogen system usage (2.component)
                self.power_2 = self.power_1 + self.fuelcell.power_to_load - self.electrolyzer.power    
            
            
            # Fuel cell provides demand energy and perhaps battery charge energy
            else:
                # Call fuel cell EMS system
                self.ems_fuelcell(output_link_power=self.power_0)
                self.ems_electrolyzer(input_link_power=0)   

                # Recalc power after hydrogen system usage (1.component)
                self.power_1 = round((self.power_0 + self.fuelcell.power - self.electrolyzer.power),4) 
                
                # Call battery EMS system
                self.ems_battery(input_link_power=self.power_1)  
            
                # Recalc power after hydrogen system usage
                self.power_2 = self.power_1 - self.battery.power          


        ## Grid inverter    
        # Rest power is supplied to grid (consider Inverter)
        if self.power_2 >= 0:
            # Inverter: Convert input power(DC) to output power (AC)
            self.inverter.link_power = abs(self.power_2)
            self.inverter.get_power_output()
            self.inverter.power_grid = self.inverter.power
            self.inverter.efficiency_grid = self.inverter.efficiency
          
        # Rest power is taken from grid (substract initial assumed inverter losses for load)
        elif self.power_2 < 0:           
            self.inverter.power_grid = self.power_2 * self.inverter.efficiency_load
            self.inverter.efficiency_grid = self.inverter.efficiency_load

        # Set grid power (Einspeisung -) (Ausspeisung +)
        self.grid.power = - (self.inverter.power_grid)

        
    def ems_battery(self, input_link_power):
        """
        Energy Management System for battery.       
        Calculates all battery performance parameters from implemented methods.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        temperature : `float`
            [K] Battery temperature in Kelvin.
        power : `float
            [W] Battery charge/discharge power extracted from the battery.
        efficiency : `float`
            [1] Battery charge/discharge efficiency.
        state_of_charge : `float`
            [1] Battery state of charge.
        charge_discharge_boundary : `float`
            [1] Battery charge/discharge boundary.
        capacity_current_wh : `float`
            [Wh] Battery capacity of current timestep.
        state_of_healt : `float`
            [1] Battery state of health.
        state_of_destruction : `float`
            [1] Battery state of destruction.
        voltage : `float`
            [V] Battery voltage level.

        Note
        ----
        - Method mainly extracts parameters by calling implemented methods of battery class:
            - battery_temperature()
            - battery_power()
            - battery_state_of_charge()
            - battery_charge_discharge_boundary()
            - battery_voltage()
            - battery_aging_cycling()
            - battery_aging_calendar()
            
        -ATTENTION:
            - self.battery.power stays at theoretical power level
            - real power dis/charged to battery is stored in self.battery.power_battery.
        """

        # Integrate battery class and theoretical input power to battery.
        self.input_link_power = input_link_power
        
        
        # Get Battery temperature
        self.battery.get_temperature()
        
        ## Calculate theoretical battery power and state of charge with available input power
        self.battery.power = self.input_link_power
        # Get effective charge/discharge power
        self.battery.get_power()
        # Set power to battery power
        self.battery.power = self.battery.power_battery
        # Get State of charge and boundary
        self.battery.get_state_of_charge()
        self.battery.get_charge_discharge_boundary()

        ## Check weather battery is capable of discharge/charge power provided
        # Discharge case
        if self.battery.power < 0:
            # Calculated SoC is under boundary - EMPTY
            if (self.battery.state_of_charge < self.battery.charge_discharge_boundary):
                # Recalc power
                self.battery.power_battery = (self.battery.power + ((abs(self.battery.state_of_charge - self.battery.charge_discharge_boundary)
                                    - self.battery.power_self_discharge_rate) * self.battery.capacity_current_wh / (self.battery.timestep/3600))).round(4)

                # Validation if power can be extracted or new soc is higher than old soc (positiv battery_power for discharge case)
                if self.battery.power_battery > 0: # new boundary is higher than current soc, stay at old soc, no battery power
                    self.battery.power_battery = 0.
                    self.battery.state_of_charge = self.battery.state_of_charge_old
                else:
                    self.battery.state_of_charge = self.battery.charge_discharge_boundary
                
        # Charge case
        elif self.battery.power > 0:
            # Calculated SoC is above boundary - FULL
            if (self.battery.state_of_charge > self.battery.charge_discharge_boundary):
                # Recalc power and set state of charge to maximum charge boundary
                self.battery.power_battery = (self.battery.power - ((abs(self.battery.state_of_charge - self.battery.charge_discharge_boundary)
                                    + self.battery.power_self_discharge_rate) * self.battery.capacity_current_wh / (self.battery.timestep/3600))).round(4)

                # Validation if power can be added or new soc is lower than old soc (negative battery_power for charge case)
                if self.battery.power_battery < 0: # new boundary is lower than current soc, stay at old soc, no battery power
                    self.battery.power_battery = 0.
                    self.battery.state_of_charge = self.battery.state_of_charge_old
                else:
                    self.battery.state_of_charge = self.battery.charge_discharge_boundary
        # Idle case
        else:
            self.battery.power_battery = self.battery.power
            self.battery.state_of_charge = self.battery.state_of_charge_old
            
        # Set power to real battery dis/charge power
        if self.battery.power_battery <= 0:
            self.battery.power = self.battery.power_battery * self.battery.efficiency
        else:
            self.battery.power = self.battery.power_battery / self.battery.efficiency
        
        ## Battery Aging
        # Cycling Aging
        if self.battery.power_battery != 0.:
            # Call cycling aging method to evaluate timestep of micro cycle
            self.battery.get_aging_cycling()

            # Capacity loss is 0, as micro cycle is running, values are set to 0 for continious array creation in simulation
            self.battery.capacity_loss_wh = 0
            self.battery.float_life_loss = 0
            self.battery.cycle_life_loss = 0

        # Calendric Aging and micro cycle evaluation
        else:
            # Call calendric aging method
            self.battery.get_aging_calendar()
            # Call cycling aging method
            self.battery.get_aging_cycling()
            # Capacity loss due to cycling of finished micro cycle AND calendaric aging
            self.battery.capacity_loss_wh = self.battery.cycle_life_loss + self.battery.float_life_loss

        # Current battery capacity with absolute capacity loss per timestep
        self.battery.capacity_current_wh = self.battery.capacity_current_wh - self.battery.capacity_loss_wh
        self.battery.state_of_health = self.battery.capacity_current_wh / self.battery.capacity_nominal_wh

        # Current State of Destruction
        self.battery.get_state_of_destruction()
     

    def ems_electrolyzer(self, input_link_power):
        """
        Energy Management System for electrolyzer.
        
        Note
        ----
        
        """
        # Integrate electrolyzer class and theoretical input power to electrolyzer.
        self.input_link_power = input_link_power
        
        # Set initial values
        self.hydrogen_produced_power = 0
        self.hydrogen_produced_kg = 0
        self.hydrogen_produced_Nl = 0
        self.heat_produced = 0
        
        # [kg] Max. possible hydrogen production (electrolyzer full capacity) 
        self.electrolyzer.hydrogen_max = (self.electrolyzer.power_nominal * (self.electrolyzer.timestep/3600) \
                                          * self.electrolyzer.efficiency_nominal) / self.electrolyzer.heating_value_kg 
        # [W] Max. compressor power for compression of max possible hydrogen production
        self.electrolyzer.compressor_power_max = self.electrolyzer.compressor_spec_compression_energy \
                                                * self.electrolyzer.hydrogen_max * (3600/self.electrolyzer.timestep)
        
        # Calculate the available Power for Electrolyser, max nominal power         
        self.electrolyzer.power_available = min((self.input_link_power + self.electrolyzer.compressor_power_max), \
                                                (self.electrolyzer.power_nominal + self.electrolyzer.compressor_power_max))
         
        
        ## Energy Management of electrolyzer
        # Electrolyser reaches minimal power
        if  self.electrolyzer.power_available >= ((self.electrolyzer.partial_power_min * self.electrolyzer.power_nominal) + self.electrolyzer.compressor_power_max) \
        and self.input_link_power > 0:  
            
            # Hydrogen storage capacity available
            if self.electrolyzer.storage_link.state_of_charge < (1 - ((self.electrolyzer.power_nominal*(self.electrolyzer.timestep/3600)) / self.electrolyzer.storage_link.capacity_wh)):
                                    
                # Get available electrolyzer power
                self.electrolyzer.power = self.electrolyzer.power_available - self.electrolyzer.compressor_power_max
                
            # Hydrogen storage capacity FULL
            else:
                #pass
                #print('H2 storage full')
                self.electrolyzer.power = 0 
        # Electrolyser does NOT reach minimal power
        else:
            # No available electrolyzer power
            self.electrolyzer.power = 0
            
            
        # Calculate electrolyzer efficiency and hydrogen amount produced
        self.electrolyzer.get_power()
        
        # Calculate hydrogen storage state of charge
        self.electrolyzer.storage_link.power = self.electrolyzer.hydrogen_produced_power
        self.electrolyzer.storage_link.get_state_of_charge()
        
        # Re-calculate compressor power
        self.electrolyzer.compressor_power = self.electrolyzer.compressor_spec_compression_energy * self.electrolyzer.hydrogen_produced_kg 

        # Calculate electrolyzer state of destruction            
        self.electrolyzer.get_state_of_destruction()     

        # Calculate hydrogen storage state of destruction            
        self.electrolyzer.storage_link.get_state_of_destruction() 
        
  
          
    def ems_fuelcell(self, output_link_power):
        """
        Energy Management System for fuel cell.
        
        Note
        ----

        """         

        # Integrate fuelcell class and theoretical output power demand of fuelcell.
        self.output_link_power = output_link_power
           
        ## Energy management        
        # Set fuelcell power to power demand
        self.fuelcell.power = abs(self.output_link_power)
        
        # Power demand
        if self.fuelcell.power > 0:
            # Power demand is below optimal operation point
            if self.fuelcell.power < (self.fuelcell.operation_point_optimum  * self.fuelcell.power_nominal):
                self.fuelcell.power = (self.fuelcell.operation_point_optimum  * self.fuelcell.power_nominal)

            # Power demand exceeds nominal power
            elif self.fuelcell.power > self.fuelcell.power_nominal:
                #print('Attention: Fuelcell maximum power exceeded, Battery deep discharge danger')
                self.fuelcell.power = self.fuelcell.power_nominal
                
            else:
                self.fuelcell.power = self.fuelcell.power     

            # FC power split (battery & load)
            self.fuelcell.power_to_load = min(abs(self.output_link_power), self.fuelcell.power_nominal)
            self.fuelcell.power_to_battery = self.fuelcell.power - self.fuelcell.power_to_load        

        # No power demand
        else:
            self.fuelcell.power_to_load = 0
            self.fuelcell.power_to_battery = 0
        
        # Get fuelcell efficiency, power and hydrogen consumption
        self.fuelcell.get_power()
        # Update hydrogen storage soc
        self.electrolyzer.storage_link.power = self.fuelcell.power_hydrogen
        self.fuelcell.storage_link.get_state_of_charge()
        
        # Check hydrogen availability
        if self.fuelcell.storage_link.state_of_charge >= 0.:
            pass
        # No hydrogen available
        else:
            #print('H2 storage empty')

            self.fuelcell.power = 0
            self.fuelcell.power_to_load = 0
            self.fuelcell.power_to_battery = 0
            self.fuelcell.get_power()
            self.fuelcell.storage_link.state_of_charge = self.fuelcell.storage_link.state_of_charge_old         
            
        # Calculate fuel cell state of destruction
        self.fuelcell.get_state_of_destruction()             
