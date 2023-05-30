#
# Copyright (c) 2013 Shotgun Software, Inc
# ----------------------------------------------------
#Tcs
"""
A Katana engine for Shotgun Toolkit.
"""
from distutils.version import StrictVersion
from functools import partial, wraps
import logging
import os
import traceback
import sgtk

from Katana import Callbacks
from Katana import Configuration
import UI4.App.MainWindow


__all__ = ('delay_until_ui_visible', 'KatanaEngine')


def delay_until_ui_visible(show_func):
    """Wrapper to delay showing dialogs until Katana Main UI is visible.

    If it is not possible to show right now, ``None`` will be returned.

    Args:
        show_func (callable): Show dialog method to wrap.

    Returns:
        callable: Wrapped function

    """
    @wraps(show_func)
    def wrapper(self, *args, **kwargs):
        result = None
        ui_state = self.has_ui
        window_title = '"{args[0]}" ({args[2].__name__})'.format(args=args)

        if ui_state == self.UI_MAINWINDOW_VISIBLE:
            # Remove added kwarg from Katana's Callbacks.addCallback
            kwargs.pop('objectHash', None)
            result = show_func(self, *args, **kwargs)

        elif ui_state:
            self.logger.info(
                'Delaying %s for %s until Katana main window is showing.',
                show_func.__name__, window_title,
            )
            func = partial(wrapper, self, *args, **kwargs)
            Callbacks.addCallback(Callbacks.Type.onStartupComplete, func)
        else:
            self.logger.error(
                "Sorry, this environment doesn't support UI display! Can't"
                ' show the requested window %s.', window_title,
            )

        # lastly, return the instantiated widget
        return result

    return wrapper


class KatanaEngine(sgtk.platform.Engine):
    """
    An engine that supports Katana.
    """
    UI_MAINWINDOW_NONE = 1
    UI_MAINWINDOW_INVISIBLE = 2
    UI_MAINWINDOW_VISIBLE = 3

    def __init__(self, *args, **kwargs):
        self._ui_enabled = bool(Configuration.get('KATANA_UI_MODE'))
        self._dialogParent = None
        super(KatanaEngine, self).__init__(*args, **kwargs)

        # Add Katana's handlers to engine's Shotgun logger
        for katana_handler in logging.getLogger().handlers:
            # self.logger.addHandler(logging.NullHandler())
            self.logger.addHandler(katana_handler)

    @property
    def has_ui(self):
        """Whether Katana is running as a GUI/interactive session.

        If it is, return the corresponding UI state enum.

        Returns:
            False or int: Main Window state, else False if not in GUI mode.
        """
        if self._ui_enabled:
            window = UI4.App.MainWindow.GetMainWindow()
            if window is None:
                return self.UI_MAINWINDOW_NONE
            elif window.isVisible():
                return self.UI_MAINWINDOW_VISIBLE
            else:
                return self.UI_MAINWINDOW_INVISIBLE
        return self._ui_enabled

    @classmethod
    def main_window_ready(cls):
        """
        Whether Katana is fully started and the main window/menu is available.

        Returns:
            bool: Whether the main window is available.
        """
        return bool(UI4.App.MainWindow.GetMainWindow())

    def init_engine(self):
        self.logger.debug("%s: Initializing...", self)
        os.environ["SGTK_KATANA_ENGINE_INIT_NAME"] = self.instance_name

    def add_katana_menu(self, **kwargs):
        self.logger.info("Start creating Shotgun menu.")

        menu_name = "Shotgrid"
        if self.get_setting("use_sgtk_as_menu_name", False):
            menu_name = "Sgtk"

        tk_katana = self.import_module("tk_katana")
        self._menu_generator = tk_katana.MenuGenerator(self, menu_name)

    def pre_app_init(self):
        """
        Called at startup.
        """
        tk_katana = self.import_module("tk_katana")

        # Make sure callbacks tracking the context switching are active.
        tk_katana.tank_ensure_callbacks_registered()

    def post_app_init(self):
        if self.has_ui:
            try:
                if self.main_window_ready():
                    self.add_katana_menu()
                else:
                    self.logger.debug(
                        'Adding onStartupComplete callback for '
                        '"KatanaEngine.add_katana_menu" as '
                        'main Katana window is not ready yet.'
                    )
                    Callbacks.addCallback(
                        Callbacks.Type.onStartupComplete,
                        self.add_katana_menu,
                    )
            except Exception:
                self.logger.error(
                    'Failed to add Katana menu\n%s',
                    traceback.format_exc(),
                )

    def destroy_engine(self):
        if self.has_ui and self.main_window_ready():
            self.logger.debug("%s: Destroying...", self)
            try:
                self._menu_generator.destroy_menu()
            except Exception:
                self.logger.error(
                    'Failed to destoy menu\n%s',
                    traceback.format_exc()
                )

    def launch_command(self, cmd_id):
        callback = self._callback_map.get(cmd_id)
        if callback is None:
            self.logger.error("No callback found for id: %s", cmd_id)
            return
        callback()

    @delay_until_ui_visible
    def show_dialog(self, title, bundle, widget_class, *args, **kwargs):
        """Overridden to delay showing until UI is fully initialised.

        If it is not possible to show right now, ``None`` will be returned.

        Args:
            title (str):
                Title of the window. This will appear in the Toolkit title bar.
            bundle (sgtk.platform.bundle.TankBundle):
                The app, engine or framework associated with this window.
            widget_class (QtWidgets.QWidget):
                Class of the UI to be constructed, must subclass from QWidget.
            args (list):
                Arguments for the ``widget_class`` constructor.
            kwargs (list):
                Keyword arguments for the ``widget_class`` constructor.

        Returns:
            QtWidgets.QWidget or None: Widget of dialog shown, if any.
        """
        if self._dialogParent:
            widget = widget_class(parent=self._dialogParent)
            self._dialogParent.layout().addWidget(widget)
            return widget
        else:
            return super(KatanaEngine, self).show_dialog(
                title, bundle, widget_class, *args, **kwargs)
        # return super(KatanaEngine, self).show_dialog(
        #     title, bundle, widget_class, *args, **kwargs)
        

    @delay_until_ui_visible
    def show_modal(self, title, bundle, widget_class, *args, **kwargs):
        """Overridden to delay showing until UI is fully initialised.

        If it is not possible to show right now, ``None`` will be returned.

        Args:
            title (str):
                Title of the window. This will appear in the Toolkit title bar.
            bundle (sgtk.platform.bundle.TankBundle):
                The app, engine or framework associated with this window.
            widget_class (QtWidgets.QWidget):
                Class of the UI to be constructed, must subclass from QWidget.
            args (list):
                Arguments for the ``widget_class`` constructor.
            kwargs (list):
                Keyword arguments for the ``widget_class`` constructor.

        Returns:
            (int, QtWidgets.QWidget) or None: Widget of dialog shown, if any.
        """
        return super(KatanaEngine, self).show_modal(
            title, bundle, widget_class, *args, **kwargs
        )

    def __define_qt5_base(self):
        return self._define_qt_base()

    def _define_qt_base(self):
        """Override to setup PyQt5 bindings for PySide 1 and 2 using Qt.py.

        This is one of the paths-of-least-resistance hack to get
        PyQt5 compatibility quickly.

        Since our patcher and Qt.py is local to tk_katana, we can only
        fetch them here using the engine's ``import_module()``.

        In the future, after some heavy refactoring and big-brain thinking,
        we should up-stream a solid PyQt5 compatibility into `sgtk.util`.

        Returns:
            dict[str]: Mapping of Qt module, class and bindings names.
                - "qt_core", QtCore module to use
                - "qt_gui", QtGui module to use
                - "wrapper", Qt wrapper root module, e.g. PySide
                - "dialog_base", base class for Tank's dialog factory.
        """
        katana_version = os.environ['KATANA_RELEASE'].replace('v', '.')
        if StrictVersion(katana_version) < StrictVersion('3.1'):
            # Hint to Qt.Py older Katana uses SIP v1 (PyQt4).
            os.environ['QT_SIP_API_HINT'] = '1'

        vendor = self.import_module("vendor")
        utils = self.import_module("utils")
        return utils.QtPyImporter(vendor.Qt).base

