"""

Initial working model taken from : https://github.com/eliben/code-for-blog/blob/master/2008/wx_mpl_dynamic_graph.py
Author: Karthik Duddu

"""

"""
This demo demonstrates how to draw a dynamic mpl (matplotlib) 
plot in a wxPython application.
It allows "live" plotting as well as manual zooming to specific
regions.
Both X and Y axes allow "auto" or "manual" settings. For Y, auto
mode sets the scaling of the graph to see all the data points.
For X, auto mode makes the graph "follow" the data. Set it X min
to manual 0 to always see the whole data from the beginning.
Note: press Enter in the 'manual' text box to make a new value 
affect the plot.
"""
import os
import pprint
import random
import sys
import wx

# The recommended way to use wx with mpl is with the WXAgg
# backend. 
#
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar
import numpy as np
import pylab


class DataGen(object):
    """ A silly class that generates pseudo-random data for
        display in the plot.
    """
    def __init__(self, init=50):
        self.data = self.init = init
        
    def next(self):
        self._recalc_data()
        return self.data
    
    def _recalc_data(self):
        delta = random.uniform(-0.5, 0.5)
        r = random.random()

        if r > 0.9:
            self.data += delta * 15
        elif r > 0.8: 
            # attraction to the initial value
            delta += (0.5 if self.init > self.data else -0.5)
            self.data += delta
        else:
            self.data += delta


class BoundControlBox(wx.Panel):
    """ A static box with a couple of radio buttons and a text
        box. Allows to switch between an automatic mode and a 
        manual mode with an associated value.
    """
    def __init__(self, parent, ID, label, initval):
        wx.Panel.__init__(self, parent, ID)
        
        self.value = initval
        
        box = wx.StaticBox(self, -1, label)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        self.radio_auto = wx.RadioButton(self, -1, 
            label="Auto", style=wx.RB_GROUP)
        self.radio_manual = wx.RadioButton(self, -1,
            label="Manual")
        self.manual_text = wx.TextCtrl(self, -1, 
            size=(35,-1),
            value=str(initval),
            style=wx.TE_PROCESS_ENTER)
        
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_manual_text, self.manual_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter, self.manual_text)
        
        manual_box = wx.BoxSizer(wx.HORIZONTAL)
        manual_box.Add(self.radio_manual, flag=wx.ALIGN_CENTER_VERTICAL)
        manual_box.Add(self.manual_text, flag=wx.ALIGN_CENTER_VERTICAL)
        
        sizer.Add(self.radio_auto, 0, wx.ALL, 10)
        sizer.Add(manual_box, 0, wx.ALL, 10)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
    
    def on_update_manual_text(self, event):
        self.manual_text.Enable(self.radio_manual.GetValue())
    
    def on_text_enter(self, event):
        self.value = self.manual_text.GetValue()
    
    def is_auto(self):
        return self.radio_auto.GetValue()
        
    def manual_value(self):
        return self.value

class ControlPanel(wx.Panel):

    def __init__(self, top_panel):        
        super(ControlPanel, self).__init__(top_panel)        
        self.create_main_panel()

    def on_pause_button(self, event):
        self.paused = not self.paused
    
    def on_update_pause_button(self, event):
        label = "Resume" if self.paused else "Pause"
        self.pause_button.SetLabel(label)
    
    def on_cb_grid(self, event):
        self.draw_plot()
    
    def on_cb_xlab(self, event):
        self.draw_plot()

    def create_main_panel(self):
        self.xmin_control = BoundControlBox(self, -1, "X min", 0)
        self.xmax_control = BoundControlBox(self, -1, "X max", 50)
        self.ymin_control = BoundControlBox(self, -1, "Y min", 0)
        self.ymax_control = BoundControlBox(self, -1, "Y max", 100)
        
        self.pause_button = wx.Button(self, -1, "Pause")
        self.Bind(wx.EVT_BUTTON, self.on_pause_button, self.pause_button)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_pause_button, self.pause_button)
        
        self.cb_grid = wx.CheckBox(self, -1, 
            "Show Grid",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_grid, self.cb_grid)
        self.cb_grid.SetValue(True)
        
        self.cb_xlab = wx.CheckBox(self, -1, 
            "Show X labels",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_xlab, self.cb_xlab)        
        self.cb_xlab.SetValue(True)
        
        self.hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox1.Add(self.pause_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox1.AddSpacer(20)
        self.hbox1.Add(self.cb_grid, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox1.AddSpacer(10)
        self.hbox1.Add(self.cb_xlab, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        
        self.hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox2.Add(self.xmin_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.xmax_control, border=5, flag=wx.ALL)
        self.hbox2.AddSpacer(24)
        self.hbox2.Add(self.ymin_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.ymax_control, border=5, flag=wx.ALL)
        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.hbox1, 0, flag=wx.ALIGN_LEFT | wx.TOP)
        self.vbox.Add(self.hbox2, 0, flag=wx.ALIGN_LEFT | wx.TOP)
        
        self.SetSizer(self.vbox)
        self.vbox.Fit(self)

class PatientFrame(wx.Panel):
    def __init__(self, top_panel):
        super(PatientFrame, self).__init__(top_panel)         
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        fgs = wx.FlexGridSizer(3, 2, 9, 25)
        title = wx.StaticText(self, label="Title")
        author = wx.StaticText(self, label="Author")
        review = wx.StaticText(self, label="Review")

        tc1 = wx.TextCtrl(self)
        tc2 = wx.TextCtrl(self)
        tc3 = wx.TextCtrl(self, style=wx.TE_MULTILINE)

        fgs.AddMany([(title), (tc1, 1, wx.EXPAND), (author), 
            (tc2, 1, wx.EXPAND), (review, 1, wx.EXPAND), (tc3, 1, wx.EXPAND)])

        fgs.AddGrowableRow(2, 1)
        fgs.AddGrowableCol(1, 1)

        hbox.Add(fgs, proportion=1, flag=wx.ALL|wx.EXPAND, border=15)
        self.SetSizer(hbox)


class GraphFrame(wx.Panel):
    """ The main frame of the application
    """
    title = 'Demo: dynamic matplotlib graph'
    
    def __init__(self, top_panel, data_stream):
        # wx.Frame.__init__(self, None, -1, self.title)
        super(GraphFrame, self).__init__(top_panel)
        
        self.datagen = data_stream
        self.data = [self.datagen.next()]
        self.paused = False
        
        self.create_main_panel()
        
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)        
        self.redraw_timer.Start(1000)
    
    def create_main_panel(self):
        # self.panel = wx.Panel(self)
        self.init_plot()
        self.canvas = FigCanvas(self, -1, self.fig)

        # self.pause_button = wx.Button(self, -1, "Pause")
        # self.Bind(wx.EVT_BUTTON, self.on_pause_button, self.pause_button)
        # self.Bind(wx.EVT_UPDATE_UI, self.on_update_pause_button, self.pause_button)
        
        # self.hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        # self.hbox1.Add(self.pause_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        # self.hbox1.AddSpacer(20)
        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)        
        # self.vbox.Add(self.hbox1, 0, flag=wx.ALIGN_LEFT | wx.TOP)        
        
        self.SetSizer(self.vbox)
        self.vbox.Fit(self)
        

    def init_plot(self):
        self.dpi = 100
        self.fig = Figure((3.0, 3.0), dpi=self.dpi)

        self.axes = self.fig.add_subplot(111)
        self.axes.set_axis_bgcolor('black')
        self.axes.set_title('Very important random data', size=12)
        
        pylab.setp(self.axes.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        #
        self.plot_data = self.axes.plot(
            self.data, 
            linewidth=1,
            color=(1, 1, 0),
            )[0]

    def draw_plot(self):
        """ Redraws the plot
        """
        # when xmin is on auto, it "follows" xmax to produce a 
        # sliding window effect. therefore, xmin is assigned after
        # xmax.
        
        # if self.xmax_control.is_auto():
        xmax = len(self.data) if len(self.data) > 50 else 50
        # else:
        #     xmax = int(self.xmax_control.manual_value())
            
        # if self.xmin_control.is_auto():            
        xmin = xmax - 50
        # else:
        #     xmin = int(self.xmin_control.manual_value())

        # for ymin and ymax, find the minimal and maximal values
        # in the data set and add a mininal margin.
        # 
        # note that it's easy to change this scheme to the 
        # minimal/maximal value in the current display, and not
        # the whole data set.

        # if self.ymin_control.is_auto():
        ymin = round(min(self.data), 0) - 1
        # else:
        #     ymin = int(self.ymin_control.manual_value())
        
        # if self.ymax_control.is_auto():
        ymax = round(max(self.data), 0) + 1
        # else:
        #     ymax = int(self.ymax_control.manual_value())

        self.axes.set_xbound(lower=xmin, upper=xmax)
        self.axes.set_ybound(lower=ymin, upper=ymax)
        
        # anecdote: axes.grid assumes b=True if any other flag is
        # given even if b is set to False.
        # so just passing the flag into the first statement won't
        # work.
        #
        # if self.cb_grid.IsChecked():
        self.axes.grid(True, color='gray')
        # else:
        #     self.axes.grid(False)

        # Using setp here is convenient, because get_xticklabels
        # returns a list over which one needs to explicitly 
        # iterate, and setp already handles this.
        #  
        pylab.setp(self.axes.get_xticklabels(), 
            visible=True) #self.cb_xlab.IsChecked()
        
        self.plot_data.set_xdata(np.arange(len(self.data)))
        self.plot_data.set_ydata(np.array(self.data))        
        self.canvas.draw()
    
    def on_redraw_timer(self, event):
        # if paused do not add data, but still redraw the plot
        # (to respond to scale modifications, grid change, etc.)
        #
        if not self.paused:
            self.data.append(self.datagen.next())
        
        self.draw_plot()
    
    def on_exit(self, event):
        self.Destroy()

class GraphTab(wx.Panel):
    def __init__(self, top_panel):
        # wx.Frame.__init__(self, None, -1, self.title)
        super(GraphTab, self).__init__(top_panel)
        ds = DataGen()
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        # control_panel = ControlPanel(self) 
        gs = wx.GridSizer(3, 3, 10, 10)
        graphs_list = []
        for i in range(6):
            graphs_list.append(GraphFrame(self, ds))
            gs.Add(graphs_list[i], 0, wx.EXPAND)
        # gs.Add(control_panel, 0, wx.EXPAND)

        # fgs = wx.FlexGridSizer(2, 1, 9, 25)
        # fgs.Add(p1,0,wx.EXPAND|wx.ALL,border=10)
        # fgs.Add(p2,0,wx.EXPAND|wx.ALL,border=10)
        # fgs.AddGrowableRow(2, 1)
        # fgs.AddGrowableCol(1, 1)
        # gs.AddMany( [
        #         (wx.Button(self, label='*'), 0, wx.EXPAND),
        #         (wx.Button(self, label='1'), 0, wx.EXPAND),
        #         (wx.Button(self, label='2'), 0, wx.EXPAND),
        #         (wx.Button(self, label='3'), 0, wx.EXPAND),
        #         (wx.Button(self, label='-'), 0, wx.EXPAND),
        #         (wx.Button(self, label='0'), 0, wx.EXPAND),
        #         (wx.Button(self, label='.'), 0, wx.EXPAND),
        #         (wx.Button(self, label='='), 0, wx.EXPAND),
        #         (wx.Button(self, label='+'), 0, wx.EXPAND) 
        #     ])       

        hbox.Add(gs, proportion=1, flag=wx.ALL|wx.EXPAND, border=15)
        self.SetSizer(hbox)


class Example(wx.Frame):

    def __init__(self, parent, title):
        super(Example, self).__init__(parent, title=title, 
            size=(300, 250))
        self.create_menu()
        self.create_status_bar()
                
        self.InitUI()
        self.Centre()
        self.Show()    

    def InitUI(self):
    
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        # sub_panel = wx.Panel(panel, style=wx.SUNKEN_BORDER)
        # fgs = wx.FlexGridSizer(3, 2, 9, 25)
        # title = wx.StaticText(sub_panel, label="Title")
        # author = wx.StaticText(sub_panel, label="Author")
        # review = wx.StaticText(sub_panel, label="Review")

        # tc1 = wx.TextCtrl(sub_panel)
        # tc2 = wx.TextCtrl(sub_panel)
        # tc3 = wx.TextCtrl(sub_panel, style=wx.TE_MULTILINE)

        # fgs.AddMany([(title), (tc1, 1, wx.EXPAND), (author), (tc2, 1, wx.EXPAND), (review, 1, wx.EXPAND), (tc3, 1, wx.EXPAND)])

        # fgs.AddGrowableRow(2, 1)
        # fgs.AddGrowableCol(1, 1)

        # sizer.Add(sub_panel, proportion=1, flag=wx.EXPAND, border=15)
        
        notebook = wx.Notebook(panel)
        tabOne = PatientFrame(notebook)
        tabTwo = GraphTab(notebook)        
        notebook.AddPage(tabOne, "Patients")
        notebook.AddPage(tabTwo, "Vitals Graphs")

        # sizer.Add(sub_panel, 1, wx.EXPAND)
        sizer.Add(notebook, 1, wx.EXPAND)
        panel.SetSizer(sizer)

    def on_exit(self, event):
        self.Destroy()

    def create_menu(self):
        self.menubar = wx.MenuBar()
        
        menu_file = wx.Menu()
        m_expt = menu_file.Append(-1, "&Save plot\tCtrl-S", "Save plot to file")
        self.Bind(wx.EVT_MENU, self.on_save_plot, m_expt)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tCtrl-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
                
        self.menubar.Append(menu_file, "&File")
        self.SetMenuBar(self.menubar)

    def create_status_bar(self):
        self.statusbar = self.CreateStatusBar()

    def on_save_plot(self, event):
        file_choices = "PNG (*.png)|*.png"
        
        dlg = wx.FileDialog(
            self, 
            message="Save plot as...",
            defaultDir=os.getcwd(),
            defaultFile="plot.png",
            wildcard=file_choices,
            style=wx.SAVE)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.canvas.print_figure(path, dpi=self.dpi)
            self.flash_status_message("Saved to %s" % path)

    def flash_status_message(self, msg, flash_len_ms=1500):
        self.statusbar.SetStatusText(msg)
        self.timeroff = wx.Timer(self)
        self.Bind(
            wx.EVT_TIMER, 
            self.on_flash_status_off, 
            self.timeroff)
        self.timeroff.Start(flash_len_ms, oneShot=True)
    
    def on_flash_status_off(self, event):
        self.statusbar.SetStatusText('')

if __name__ == '__main__':
    app = wx.App(redirect=True, filename="log.txt")
    Example(None, title="ICU Alarm System")
    # app.frame = GraphFrame()
    # app.frame.Show()
    app.MainLoop()
