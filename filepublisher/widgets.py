from avalon import style

from avalon.vendor.Qt import QtWidgets, QtCore
from avalon.vendor import qtawesome as qta
from avalon.tools.contextmanager import app

from . import lib


class CollectionItem(QtWidgets.QListWidgetItem):

    InstanceRole = QtCore.Qt.UserRole + 2
    item_clicked = QtCore.Signal()

    def __init__(self, data=None, parent=None):
        QtWidgets.QListWidgetItem.__init__(self, parent)

        self.setFlags(self.flags() | QtCore.Qt.ItemIsUserCheckable)
        self.setCheckState(QtCore.Qt.Checked)

        self._data = None
        if data:
            self.set_data(data)

    def set_data(self, data):
        self._data = data
        self.setData(self.InstanceRole, data)

    def get_data(self):
        return self._data


class SearchComboBox(QtWidgets.QComboBox):
    """Searchable ComboBox with empty placeholder value as first value"""

    def __init__(self, parent=None, placeholder=""):
        QtWidgets.QComboBox.__init__(self, parent)

        self.setEditable(True)
        self.setInsertPolicy(self.NoInsert)
        self.lineEdit().setPlaceholderText(placeholder)

        # Apply completer settings
        completer = self.completer()
        completer.setCompletionMode(completer.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)

    def populate(self, items):
        self.clear()
        self.addItems([""])     # ensure first item is placeholder
        self.addItems(items)

    def get_valid_value(self):
        """Return the current text if it's a valid value else None

        Note: The empty placeholder value is valid and returns as ""

        """

        text = self.currentText()
        lookup = set(self.itemText(i) for i in range(self.count()))
        if text not in lookup:
            return None

        return text


class UpdateSequenceRange(QtWidgets.QDialog):

    data_changed = QtCore.Signal(list)

    def __init__(self, instances=None, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.setWindowTitle("Update Sequence Range")
        self.setModal(True)
        self.setFixedWidth(150)
        self.setFixedHeight(100)

        self._instances = instances

        layout = QtWidgets.QVBoxLayout()

        start_hlayout = QtWidgets.QHBoxLayout()
        start_label = QtWidgets.QLabel("Start")
        start_label.setFixedWidth(30)

        start_stylesheet = "QAbstractQSpinBox:up-button {subcontrol-origin: border}"
        start_value = QtWidgets.QSpinBox()
        start_value.setAlignment(QtCore.Qt.AlignRight)
        start_value.setStyleSheet(start_stylesheet)

        start_hlayout.addWidget(start_label)
        start_hlayout.addWidget(start_value)

        end_hlayout = QtWidgets.QHBoxLayout()
        end_label = QtWidgets.QLabel("End")
        end_label.setFixedWidth(30)

        end_stylesheet = "QAbstractSpinBox:down-button {subcontrol-origin: bottom}"
        end_value = QtWidgets.QSpinBox()
        end_value.setAlignment(QtCore.Qt.AlignRight)
        end_value.setStyleSheet(end_stylesheet)

        end_hlayout.addWidget(end_label)
        end_hlayout.addWidget(end_value)

        accept_btn = QtWidgets.QPushButton("Accept")

        layout.addLayout(start_hlayout)
        layout.addLayout(end_hlayout)
        layout.addWidget(accept_btn)

        self.start_value = start_value
        self.end_value = end_value
        self.accept = accept_btn

        self.setLayout(layout)

        self.make_connections()

        self._on_init()

    def _on_init(self):

        if self._instances is None:
            return

        first = self._instances[0]

        self.start_value.setValue(first.data["startFrame"])
        self.end_value.setValue(first.data["endFrame"])

    def make_connections(self):
        self.accept.clicked.connect(self.on_accept)

    def on_accept(self):

        updated_instances = []
        start, end = self.get_frames()
        for instance in self._instances:
            updated = lib.update_filesequence_instance(instance, start, end)
            updated_instances.append(updated)

        self.data_changed.emit(updated_instances)

        self.deleteLater()

    def get_frames(self):
        return self.start_value.value(), self.end_value.value()


class SimpleContextSwitcher(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        layout = QtWidgets.QHBoxLayout()

        context = QtWidgets.QLabel()
        context.setMinimumWidth(50)
        context.setStyleSheet("QLabel {font-weight: bold}")

        set_context_icon = qta.icon("fa.arrow-right",
                                    color=style.colors.default)
        set_context_button = QtWidgets.QPushButton()
        set_context_button.setIcon(set_context_icon)
        set_context_button.setFixedWidth(28)

        layout.addWidget(context)
        layout.addWidget(set_context_button)

        self.setLayout(layout)

        self.set_context_btn = set_context_button
        self.context_label = context

        self.connections()

        self._set_context_label()

    def connections(self):
        self.set_context_btn.clicked.connect(self.on_set_context)

    def on_set_context(self):

        # Launch context manager
        cm = app.App(self)
        # Override close event
        cm.closeEvent = self.custom_close_event
        cm.setModal(True)

        cm.show()

    def _set_context_label(self):
        context = self._get_current_context()
        print("context:", context)
        context_label = self._create_context_label(*context)
        self.context_label.setText(context_label)

    def _get_current_context(self):

        project = lib.get_project()
        silo = lib.get_silo()
        asset = lib.get_asset()
        task = lib.get_task()

        return project, silo, asset, task

    def _create_context_label(self, project=None, silo=None, asset=None,
                              task=None):

        breadcrumbs = [i for i in (project, silo, asset, task) if i not in
                       ["placeholder", None]]
        return " > ".join(breadcrumbs)

    def custom_close_event(self, event):
        """Custom close event to ensure the data is being set correctly"""
        self._set_context_label()


def display_error_message(message):
    """Show a message box with given message

    Args:
        message(str): the message to display

    Return:
        None
    """

    QtWidgets.QMessageBox.critical(
        None,
        "An error has occurred!",
        message
    )
