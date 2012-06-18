import sys

import QtGui
from QtGui import QWidget, QPushButton, QComboBox
from QtCore import QTimer

import dynamic_reconfigure.client
import rosservice
import rospy

from .editors import *
from .updater import Updater

class ReconfigureWidget(QWidget):
    def __init__(self):
        super(ReconfigureWidget, self).__init__()

        self.selector = ReconfigureSelector(self)

        self.client = None

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.selector)

        self.vbox = QtGui.QVBoxLayout()
        self.vbox.addLayout(hbox)
        self.vbox.addStretch(1)

        self.setLayout(self.vbox)

    def show(self, node):
        self.close()

        reconf = None
        
        try:
            reconf = dynamic_reconfigure.client.Client(node, timeout=5.0)
        except rospy.exceptions.ROSException:
            print("Could not connect to %s"%node) 
            return
        finally:
            self.close()

        self.client = ClientWidget(self, reconf)
        self.vbox.insertWidget(1, self.client)

    def close(self):
        if self.client is not None:
            # Clear out the old widget
            self.client.close()
            self.client = None

    def shutdown_plugin(self):
        self.close()

class ReconfigureSelector(QWidget):
    def __init__(self, parent):
        super(ReconfigureSelector, self).__init__()

        self.parent = parent
        self.last_nodes = None

        self.combo = QComboBox(self)
        self.update_combo()
        self.combo.activated[str].connect(self.selected)

        self.hbox = QtGui.QHBoxLayout()
        self.hbox.addWidget(self.combo)
        
        self.setLayout(self.hbox)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_combo)
        self.timer.start(100)

    def update_combo(self):
        try:
            nodes = dynamic_reconfigure.find_reconfigure_services()
        except rosservice.ROSServiceIOException:
            print("Reconfigure GUI cannot connect to master.")
        else:
            if not self.last_nodes:
                for n in nodes:
                    self.combo.addItem(n)
            elif len(nodes) == 0:
                self.combo.clear()
                self.parent.close()
            else:
                for i, n in enumerate(self.last_nodes):
                    if not n in nodes:
                        self.combo.removeItem(i)

                for n in nodes:
                    if not n in self.last_nodes:
                        self.combo.addItem(n)

            self.last_nodes = nodes

    def selected(self, node):
        self.parent.show(node)

class ClientWidget(QWidget):
    def __init__(self, parent, reconf):
        super(ClientWidget, self).__init__()

        self.parent = parent
        self.reconf = reconf

        self.grid = QtGui.QGridLayout()
    
        descr = self.reconf.get_group_descriptions()

        self.updater = Updater(self.reconf) 

        self.widgets = []
        self.add_widgets(descr)

        self.setLayout(self.grid)

        self.updater.start()

    def add_widgets(self, descr):
        for param in descr['parameters']:
            if param['edit_method']:
                ed = EnumEditor(self.updater, param)
            elif param['type'] in editor_types:
                ed = eval(editor_types[param['type']])(self.updater, param)

            self.widgets.append(ed)

        for i, ed in enumerate(self.widgets):
            ed.display(self.grid, i)

    def close(self):
        self.reconf.close()
        self.updater.stop()
        self.deleteLater()

