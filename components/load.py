import pandas
import data_loader
from simulatable import Simulatable

class Load(Simulatable):
    """Relevant methods to define the simulation load profile power.

    Parameters
    ----------
    None : `None`

    Note
    ----
    - Class data_loader is integrated and its method LoadDemand() to integrate csv load.
    - This method is called externally before the central method simulate() of the class simulation is called.
    
    """


    def __init__(self):

        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # Integrate load demand data_loader for csv load profile integration
        self.load_demand = data_loader.LoadDemand()
        #Initialize power of load profile
        self.power = 0
        self.load_data = None


    def calculate(self):
        """Extracts power flow of load profile for each timestep in order to make class simulatable..

        Parameters
        ----------
        None : `None`

        Returns
        -------
        power : `float`
            [W] Load power flow of timestep in watts.
        """
        if not isinstance(self.load_data, pandas.core.series.Series):
            self.load_data = self.load_demand.get_day_profile()

        self.power = self.load_data[self.time % len(self.load_data)]