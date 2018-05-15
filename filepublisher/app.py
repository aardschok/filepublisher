import os
import logging

from avalon import io, api, style
from avalon.tools import lib as toolslib
from avalon.vendor import qtawesome as qta
from avalon.vendor.Qt import QtCore, QtWidgets

import pyblish.util
import pyblish.api

from .widgets import (
    SearchComboBox,
    CollectionItem,
    UpdateSequenceRange,
    SimpleContextSwitcher,
    display_error_message
)


error_format = "Failed {plugin.__name__}: {error} -- {error.traceback}\n"


class Window(QtWidgets.QWidget):

    on_context_found = QtCore.Signal()
    update_view = QtCore.Signal(list)

    def __init__(self, session=None, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        # Attributes
        self._context = None
        self._session = session or api.Session
        self.log = logging.getLogger("File Sequence Publisher")

        # Build UI
        window_icon = qta.icon("fa.filter", color=style.colors.default)
        self.setWindowIcon(window_icon)
        self.setWindowTitle("File Sequence Publisher")

        layout = QtWidgets.QVBoxLayout()

        breadcrumps = SimpleContextSwitcher()

        set_context_btn = QtWidgets.QPushButton("Set Context")

        browse_hlayout = QtWidgets.QHBoxLayout()
        file_path = QtWidgets.QLineEdit()
        browse_button = QtWidgets.QPushButton("Browse")
        browse_hlayout.addWidget(file_path)
        browse_hlayout.addWidget(browse_button)

        family_layout = QtWidgets.QHBoxLayout()
        family_label = QtWidgets.QLabel("Family")
        family_label.setFixedWidth(50)
        family_box = SearchComboBox()
        family_layout.addWidget(family_label)
        family_layout.addWidget(family_box)

        collect_layout = QtWidgets.QVBoxLayout()
        collect_buttons_hlayout = QtWidgets.QHBoxLayout()

        refresh_icon = qta.icon("fa.refresh", color=style.colors.default)
        refresh_button = QtWidgets.QPushButton()
        refresh_button.setIcon(refresh_icon)
        refresh_button.setFixedWidth(28)
        collect_button = QtWidgets.QPushButton("Collect")
        collect_buttons_hlayout.addWidget(collect_button)
        collect_buttons_hlayout.addWidget(refresh_button)

        collect_view = QtWidgets.QListWidget()
        collect_view.setAlternatingRowColors(True)
        collect_view.setSelectionMode(3)
        collect_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        collect_view.customContextMenuRequested.connect(
            self.show_right_mouse_menu)

        collect_layout.addLayout(collect_buttons_hlayout)
        collect_layout.addWidget(collect_view)

        publish_button = QtWidgets.QPushButton("Publish")
        publish_button.setEnabled(False)

        layout.addWidget(breadcrumps)
        layout.addLayout(browse_hlayout)
        layout.addLayout(family_layout)
        layout.addLayout(collect_layout)
        layout.addWidget(publish_button)

        self.setLayout(layout)

        self.set_context_btn = set_context_btn

        self.browse = browse_button
        self.file_path = file_path
        self.family = family_box
        self.collect_button = collect_button
        self.collection_view = collect_view
        self.publish_button = publish_button
        self.refresh_button = refresh_button

        self.make_connections()

        self.install()

        self.get_families()

        self.resize(self.sizeHint())

    def make_connections(self):
        self.on_context_found.connect(self._on_context_found)
        self.update_view.connect(self.on_update_view)

        self.browse.clicked.connect(self.on_browse)
        self.collect_button.clicked.connect(self.on_collect)
        self.publish_button.clicked.connect(self.on_publish)
        self.refresh_button.clicked.connect(self.on_refresh)

        self.collection_view.itemChanged.connect(self.on_item_toggled)

    def on_browse(self):

        start_directory = self.file_path.text()
        if not start_directory:
            project_root = os.path.join(api.Session["AVALON_PROJECTS"],
                                        api.Session["AVALON_PROJECT"])
            start_directory = os.path.abspath(project_root)

        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            start_directory,
            QtWidgets.QFileDialog.ShowDirsOnly
        )

        if os.path.isdir(directory):
            self.file_path.setText(directory)

    def on_collect(self):

        # Ensure the context is always empty before collecting
        if self._context is not None:
            self._context = None

        target = None
        if self.family.currentText() == "colorbleed.imagesequence":
            target = "filesequence"

        context = self._collect(target)
        if not context:
            print("Could not find a valid context for publishing!")
            return

        self.populate(list(context))

        self._context = context
        self.on_context_found.emit()

    def _collect(self, targets=None):

        self.collection_view.clear()

        api.Session["AVALON_WORKDIR"] = self.file_path.text()
        os.chdir(self.file_path.text())
        if targets:
            pyblish.api.register_target(targets)
        try:
            print("Collecting .. ")
            context = pyblish.util.collect()
            print("Finished Collecting")
        except Exception as exc:
            print(exc)
            return []

        return context

    def _on_context_found(self):
        self.publish_button.setEnabled(True)

    def on_update_view(self, instances):

        # Ensure all instances are still visible.
        # This counters the issue that, after updating the frame range of
        # an instance the non-selected items are not included

        lookup = {}
        self.collection_view.blockSignals(True)

        # Get the original instances
        for row in range(self.collection_view.count()):
            item = self.collection_view.item(row)
            instance = item.get_data()
            lookup[instance.name] = instance

        # Update
        for instance in instances:
            lookup[instance.name] = instance

        updated = lookup.values()
        self.collection_view.clear()
        self.populate(updated)
        self.collection_view.blockSignals(False)

    def on_item_toggled(self):

        for row in range(self.collection_view.count()):
            item = self.collection_view.item(row)
            instance = item.get_data()
            # Value returned by checkState is 0 or 2 due to triState
            # This is the case even if triState is not set as a flag
            instance.data["publish"] = item.checkState() > 1

    def on_publish_debug(self):
        if self._context is not None:
            print(list(self._context))

    def on_publish(self):

        try:
            # Make a copy of the context list
            result = pyblish.util.publish(self._context)
        except Exception as exc:
            self.log.error(exc)
            return []

        # Validate result
        error_results = [r for r in result.data["results"] if r["error"]]
        error_messages = ""
        if error_results:
            self.log.error("Errors occurred ...")
            for result in error_results:
                error_messages + error_format.format(**result)
            # Display error messages which occurred during publish
            display_error_message(error_messages)

        # Reset context, force user to re-collect everything
        self._context = None
        self.publish_button.setEnabled(False)

    def on_refresh(self):
        self.collection_view.clear()
        self.on_collect()

    def show_right_mouse_menu(self, pos):

        globalpos = self.collection_view.viewport().mapToGlobal(pos)

        # Get selected items
        model = self.collection_view.selectionModel()
        selected_items = model.selectedIndexes()

        instances = [i.data(CollectionItem.InstanceRole)
                     for i in selected_items]

        menu = self._build_menu(instances)
        menu.exec_(globalpos)

    def _build_menu(self, instances):

        _parent = self.collection_view
        menu = QtWidgets.QMenu(_parent)

        set_range_icon = qta.icon("fa.scissors", color=style.colors.default)
        set_range_action = QtWidgets.QAction(set_range_icon,
                                             "Update frame range",
                                             menu)
        set_range_action.triggered.connect(
            lambda: self._show_update_frame_range(instances))

        menu.addAction(set_range_action)

        return menu

    # Wrapped functionality to call frame range update widget
    def _show_update_frame_range(self, instances):

        # Check if any items can be altered
        sequence_families = ["colorbleed.imagesequence",
                             "colorbleed.yeticache"]

        valid = [instance for instance in instances if instance.data["family"]
                 in sequence_families]

        if not valid:
            print("No valid instances found for action ..")
            return

        dialog = UpdateSequenceRange(instances=valid,
                                     parent=self.collection_view)
        dialog.data_changed.connect(self.update_view.emit)
        dialog.show()

    def get_families(self):

        families = io.distinct("data.families") + io.distinct("data.family")
        unique_families = set(families)

        # Sort and convert to list
        collected = sorted(list(unique_families))

        completer = QtWidgets.QCompleter(collected)
        completer.setCaseSensitivity(False)

        self.family.setCompleter(completer)
        self.family.addItems(collected)

    def populate(self, instances):

        for instance in instances:
            item = CollectionItem(data=instance)
            item.setText(instance.data["name"])
            self.collection_view.addItem(item)

    def install(self):
        """Ensure the plugins have been registered together with a host name"""

        import avalon.shell
        api.install(avalon.shell)
        pyblish.api.register_host("shell")


def show(session=None):

    io.install()

    with toolslib.application():
        window = Window(session)
        window.setStyleSheet(style.load_stylesheet())
        window.show()


def cli():
    show()
