class Simulatable:
    """Most central methods to make simulation "simulatable", which means that
    timestep proceeds after the calculation of all component performance of the current timestep.
    Simulatable class - Parent class for simulation class and all component classes.

    Parameters
    ----------
    *childs : `class`
        All classes which shall be simulated

    Note
    ----
    - Class needs to be initialized in simulation class with system component as follows:
        - e.g. Simulatable.__init__(self,self.env,self.load,self.pv,self.charger,
                               self.power_junction, self.battery_management, self.battery)
    """

    def __init__(self,
                 *childs):

        self.time = -1
        self.childs = list(childs)


    def calculate(self):
        """Null methods - stands for for calculation methods of component classes.

        Parameters
        ----------
        None : `None`
        """

        pass

        
    def start(self):
        """Start Method, which initialize start method for all childs and
        sets time index to zero.

        Parameters
        ----------
        None : `None`
        """

        # Set time index to zero
        self.time = 0
        # Calls start method for all simulatable childs
        for child in self.childs:
            if isinstance(child, Simulatable):
                child.start()


    def end(self):
        """End Method, which terminates Simulatable with end method for all childs
        and sets time index back to zero.

        Parameters
        ----------
        None : `None`
        """

        # Set time index back to 0
        self.time = 0
        # Calls end method for all simulatable childs
        for child in self.childs:
            if isinstance(child, Simulatable):
                child.end()


    def update(self):
        """Method, which updates time index and goes to next simulation step for all childs.

        Parameters
        ----------
        None : `None`
        """
                
        # Call null method
        self.calculate()

        # Update time parameters with +1
        self.time += 1
        # Calls update method for all simulatable childs
        for child in self.childs:
            if isinstance(child, Simulatable):
                child.update()
      

    def balance(self):
        """Method, which updates carrier and checks its energy balance.

        Parameters
        ----------
        None : `None`
        """

        # Calls update method for all simulatable childs
        for child in self.childs:
            if isinstance(child, Simulatable):
                child.balance()