from simulatable import Simulatable

class Power_Junction(Simulatable):
    """Relevant methods of the power junction to compute all power input and
    output flows and the resulting battery power flow.

    Parameters
    ----------
    input_link_1 : `class`
        [-] Component 1 that provides input power to junction
    input_link_2 : `class`
        [-] Component 2 that provides input power to junction
    load : `class`
        [-] Load class to integrate load power flow

    Note
    ----
    - Power junction can be enlarged with further input and output power flows.
    """

    def __init__(self,
                 input_link_1,
                 input_link_2,
                 load):

        # Integrate simulatable class and connected component classes
        Simulatable.__init__(self)
        self.load = load
        self.input_link_1 = input_link_1
        self.input_link_2 = input_link_2

        # Initialize power flow of junction
        self.power = 0


    def calculate(self):
        """Calculates needed battery power to balance input and output power flows of junction.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        power : `float`
            [W] Power junction power flow to battery.
        """

        # Calculate power flow of junction
        if self.input_link_2 is not None:
            self.power = self.input_link_1.power + self.input_link_2.power - self.load.power
        else:
            self.power = self.input_link_1.power - self.load.power
