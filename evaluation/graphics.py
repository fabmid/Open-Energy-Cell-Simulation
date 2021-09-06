import matplotlib.pyplot as plt

class Figure_format():

    def __init__(self):
        
        MEDIUM_SIZE = 10
        BIGGER_SIZE = 12
        plt.rc('font', size=MEDIUM_SIZE)            # controls default text sizes
        plt.rc('axes', titlesize=BIGGER_SIZE)       # fontsize of the axes title
        plt.rc('axes', labelsize=BIGGER_SIZE)       # fontsize of the x and y labels
        plt.rc('xtick', labelsize=MEDIUM_SIZE)      # fontsize of the tick labels
        plt.rc('ytick', labelsize=MEDIUM_SIZE)      # fontsize of the tick labels
        plt.rc('legend', fontsize=MEDIUM_SIZE)      # legend fontsize
        plt.rc('figure', titlesize=BIGGER_SIZE)     # fontsize of the figure title
        self.figsize = (5,3)


class Plot_simple(Figure_format):

    def __init__(self,
                 xdata,ydata,
                 xlabel,ylabel,
                 title):
        
        self.xdata = xdata
        self.ydata = ydata
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title=title
        
        # Initialization of super class
        super().__init__()
        
    def generate(self):
        plt.figure(figsize=self.figsize)
        plt.title(self.title)
        plt.plot(self.xdata, self.ydata, '-b')
        plt.xlabel(self.xlabel)
        plt.ylabel(self.ylabel)
        #plt.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()


class Plot_twinx(Figure_format):
 
    def __init__(self,
                 xdata,ydata1,ydata2,
                 xlabel,ylabel1,ylabel2,
                 title):
            
        self.xdata = xdata
        self.ydata1 = ydata1
        self.ydata2 = ydata2
        self.xlabel = xlabel
        self.ylabel1 = ylabel1
        self.ylabel2 = ylabel2
        self.title=title
        
        # Initialization of super class
        super().__init__()
            
    def generate(self):
        fig, ax1 = plt.subplots(figsize=self.figsize)        
        ax1.plot(self.xdata, self.ydata1, 'ob')
        ax1.set_title(self.title)
        ax1.set_ylabel(self.ylabel1)
        ax1.legend(bbox_to_anchor=(0., 1.1), loc=2, borderaxespad=0., ncol=4)
        ax2 = ax1.twinx()   
        ax2.plot(self.xdata, self.ydata2, 'xg')
        ax2.set_xlabel(self.xlabel)
        ax2.set_ylabel(self.ylabel2)
        #ax2.legend(bbox_to_anchor=(0.9, 1.1), loc=2, borderaxespad=0., ncol=4)
        plt.grid()
        

class Plot_imshow(Figure_format):
 
    def __init__(self,
                 data,xlabel,ylabel,
                 title):
            
        self.data = data
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title=title
        
        # Initialization of super class
        super().__init__()
        
    def generate(self):
        plt.figure(figsize=self.figsize)
        plt.title(self.title)
        plt.imshow(self.data, aspect='auto')
        plt.colorbar()
        plt.xlabel(self.xlabel)
        plt.ylabel(self.ylabel)
        plt.grid()
        plt.show()