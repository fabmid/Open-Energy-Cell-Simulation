class Simulatable:
    """Most central methods to make simulation "simulatable", which means that
    timestep proceeds after the calculation of all component performance of the current timestep.
    Simulatable class - Parent class for system class and all component classes.

    Parameters
    ----------
    **childs : `dict`
        Dict with all classes which shall be simulated, seperated in dispatchables and non_dispatchables

    Returns
    -------
    None : `None`

    Note
    ----
    - Class needs to be initialized in system class
    - Komplexität der Klasse: Jede komponente erbt auch von simulatable(),
      das heißt jede Komponente ruft ggf wieder die Methoden hier auf.
    """

    def __init__(self,
                 **childs):

        # Set initial time to -1 (no simulation mode)
        self.time = -1

        # Create empty list for all components (as simulatable class of them is not initialized with **childs)
        if not childs:
            self.childs = []

        # Get child lists seperated in non_dispatchable and dispatchable
        for key, value in childs.items():
            if key=='non_dispatchables':
                self.childs_non_dispatchables = value
            elif key=='dispatchables':
                self.childs_dispatchables = value


    def simulation_test(self):
         """
         Test method removes all components from childs list and from simulation calculation with capacity of 0!
         This enables also to set component capacity of 0 for a system of this component initialized

         Parameters
         ----------
         None : `None`

        Returns
        -------
        None : `None`

         Note
         ----
         - Removeable components:
             - Photovoltaic
             - Battery
             - Heat Pump
             - Thermal storage
             - Electrolyzer
             - Fuel cell
             - H2 storage
             - Wind turbine
         - Wäre auch noch erweiterbar auf: Heat Grid
         - If component is removed or not is checked with parameter size_nominal, used for economic calculation
         - Component is not removed from milp
         """

         # Calls simulation_test() method of all simulatable childs
         # empty list with components to be removed
         remove = list()

         # Iterate over all childs
         for child in self.childs:
             if isinstance(child, Simulatable):
                 # remove component from childs list in case it has capacity of 0!
                 try:
                     if child.size_nominal == 0:
                         remove.append(child)
                     else:
                         pass
                 # do nothin in case component is not sizeable or has capacity > 0!
                 except:
                     pass

         # Remove all components, which are in remove list
         self.childs =  [elem for elem in self.childs if elem not in remove]


    def simulation_start(self):
        """
        Start Method, which calls smiulation_start method for all childs and
        sets time index to zero (for all child classes).

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - System-classes must not have own simulation_start class! This would result in wrong defined time index.
        """

        # Set time index to zero
        self.time = 0

        # Calls simulation_start method for all simulatable childs
        for child in self.childs:

            if isinstance(child, Simulatable):
                child.simulation_start()


    def simulation_update(self):
        """
        Update method, which calls simulation_updates method for all childs and
        increases time index by 1 to go to next simulation step (for all child classes).

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - System-classes must not have own simulation_start class! This would result in wrong defined time index.
        """

        # Update time parameters with +1
        self.time += 1

        # Calls simulatable_update method for all simulatable childs
        for child in self.childs:

            if isinstance(child, Simulatable):
                child.simulation_update()


    def simulation_end(self):
        """
        End Method, which calls simulation_end method for all childs and
        sets time index back to zero (for all child classes).

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - System-classes must not have own simulation_start class! This would result in wrong defined time index.
        """

        # Set time index back to 0
        self.time = 0

        # Calls simulation_end method for all simulatable childs
        for child in self.childs:

            if isinstance(child, Simulatable):
                child.simulation_end()


    def simulation_init(self):
         """
         Init Method, which calls simulation_init method of all childs and
         loads/calculates data using external libaries pvlib/windpowerlib,
         where all timesteps are computed initially as a batch.

         Parameters
         ----------
         None : `None`

         Returns
         -------
         None : `None`

         Note
         ----
         - System-classes need to have own simulation_init class!
         - Usually lists for component results of simulation (dispatchable and non_dispatchables are initiliazed here).
         """

         # Calls simulation_init() method of all simulatable childs
         for child in self.childs:

             if isinstance(child, Simulatable):
                 child.simulation_init()


    def simulation_calculate(self):
        """
        Calculate methods, which calls simulation_calculate method of all childs
        where usually central component simulation takes place.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - In the case of usage of pvlib or windpowerlib central computation takes palce in simulation_init method.
        """

        # Calls simulation_calculate method of all simulatable childs
        for child in self.childs:

            if isinstance(child, Simulatable):
                child.simulation_calculate()