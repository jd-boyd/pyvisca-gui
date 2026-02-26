#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
pyvisca-gui: Graphical User Interface for VISCA PTZ cameras

A Dear PyGui-based GUI for controlling VISCA PTZ cameras using the pyvisca library.
Supports both keyboard and mouse input for full camera control.
"""

import os
import json
import time
import threading

import dearpygui.dearpygui as dpg
from pyvisca import PTZ


def get_config_path():
    """Get the path to the config file."""
    config_dir = os.path.expanduser("~/.config/pyvisca-gui")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.json")


class ViscaGUI:
    """GUI application for VISCA PTZ camera control using Dear PyGui."""

    def __init__(self, connection_string="192.168.1.32:8234"):
        """Initialize GUI and connect to camera.

        Args:
            connection_string: Serial port or RFC-2217 server address
        """
        self.connection_string = connection_string
        self.camera = None
        self.pan_speed = 5
        self.tilt_speed = 5
        self.zoom_speed = 5
        self.focus_speed = 5
        self.running = True
        self.status_message = "Initializing..."
        self.current_movement = None
        self.last_movement_time = 0
        self.movement_timeout = 0.15
        self.current_zoom = None
        self.current_focus = None
        self.last_status_check = time.time()
        self.status_check_interval = 0.5
        self._cached_status = None
        self.incoming_messages = []
        self.max_messages = 10
        self.log_messages = []

        # Keyboard key handler state
        self.keys_pressed = set()

        # Load config and auto-connect if enabled
        auto_connect = self.load_config()
        if auto_connect:
            self.connect_camera()

    def connect_camera(self):
        """Connect to the VISCA camera."""
        try:
            self.status_message = f"Connecting to {self.connection_string}..."
            self.camera = PTZ(self.connection_string)
            self.status_message = f"Connected to {self.connection_string}"
            self.add_log(f"Connected to {self.connection_string}")
            self.save_config()
            return True
        except Exception as e:
            self.status_message = f"Connection failed: {e}"
            self.add_log(f"Connection failed: {e}")
            return False

    def is_connected(self):
        """Check if the camera connection is still valid."""
        if self.camera is None:
            return False

        try:
            return self.camera._output is not None and self.camera._output.isOpen()
        except Exception:
            return False

    def ensure_connected(self):
        """Ensure that the camera is connected, reconnect if needed."""
        if not self.is_connected():
            self.status_message = "Reconnecting..."
            if self.connect_camera():
                self.status_message = f"Reconnected to {self.connection_string}"
                return True
            else:
                return False
        return True

    def get_camera_status(self):
        """Get current camera status."""
        if self.camera is None:
            return {"connected": False, "error": "No camera connection"}

        if not self.is_connected():
            return {
                "connected": False,
                "error": "Connection lost - will reconnect on next action",
            }

        try:
            power = self.camera.get_power()
            power_str = "ON" if power == 1 else "OFF" if power == 0 else "UNKNOWN"

            pan = 0
            tilt = 0
            zoom = 0
            video_format = "Unknown"
            ae_mode = "Unknown"
            white_balance = "Unknown"

            try:
                pan = self.camera.get_pan()
            except (IndexError, ValueError, AttributeError):
                pass

            try:
                tilt = self.camera.get_tilt()
            except (IndexError, ValueError, AttributeError):
                pass

            try:
                zoom = self.camera.get_zoom()
            except (IndexError, ValueError, AttributeError):
                pass

            try:
                video_format = self.camera.get_video_format_string()
            except (IndexError, ValueError, AttributeError):
                pass

            try:
                ae_mode = self.camera.get_ae_mode_string()
            except (IndexError, ValueError, AttributeError):
                pass

            try:
                white_balance = self.camera.get_white_balance_string()
            except (IndexError, ValueError, AttributeError):
                pass

            return {
                "connected": True,
                "power": power_str,
                "pan": pan,
                "tilt": tilt,
                "zoom": zoom,
                "video_format": video_format,
                "ae_mode": ae_mode,
                "white_balance": white_balance,
                "pan_speed": self.pan_speed,
                "tilt_speed": self.tilt_speed,
                "zoom_speed": self.zoom_speed,
                "focus_speed": self.focus_speed,
            }
        except Exception as e:
            error_str = str(e)
            if len(error_str) > 100:
                error_str = error_str[:97] + "..."
            return {"connected": False, "error": error_str}

    def add_log(self, message):
        """Add message to the log."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_messages.append(f"[{timestamp}] {message}")
        if len(self.log_messages) > 100:
            self.log_messages = self.log_messages[-100:]

    def check_incoming_messages(self):
        """Check for incoming camera messages."""
        if self.camera is None:
            return False

        if not self.is_connected():
            return False

        try:
            raw = self.camera.read()
            if raw and len(raw) > 0:
                self.incoming_messages.append(raw)
                if len(self.incoming_messages) > self.max_messages:
                    self.incoming_messages = self.incoming_messages[
                        -self.max_messages :
                    ]
                self.add_log(f"Msg: {raw}")
                return True
            return False
        except Exception:
            return False

    def check_movement_timeout(self):
        """Check if movement should stop due to timeout."""
        now = time.time()

        if (
            self.current_movement
            and (now - self.last_movement_time) > self.movement_timeout
        ):
            try:
                self.camera.stop()
                self.current_movement = None
                self.status_message = "Movement stopped"
                self.add_log("Movement stopped (timeout)")
            except Exception:
                pass

        if (
            self.current_zoom
            and (now - self.last_movement_time) > self.movement_timeout
        ):
            try:
                self.camera.zoom_stop()
                self.current_zoom = None
            except Exception:
                pass

        if (
            self.current_focus
            and (now - self.last_movement_time) > self.movement_timeout
        ):
            try:
                self.camera.focus_stop()
                self.current_focus = None
            except Exception:
                pass

    # ===== Movement Control Methods =====

    def move_up(self, sender=None, app_data=None, user_data=None):
        """Move camera up (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.up(self.tilt_speed)
            self.current_movement = "up"
            self.last_movement_time = time.time()
            self.status_message = "Moving UP"
            self.add_log("Moving UP")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def move_down(self, sender=None, app_data=None, user_data=None):
        """Move camera down (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.down(self.tilt_speed)
            self.current_movement = "down"
            self.last_movement_time = time.time()
            self.status_message = "Moving DOWN"
            self.add_log("Moving DOWN")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def move_left(self, sender=None, app_data=None, user_data=None):
        """Move camera left (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.left(self.pan_speed)
            self.current_movement = "left"
            self.last_movement_time = time.time()
            self.status_message = "Moving LEFT"
            self.add_log("Moving LEFT")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def move_right(self, sender=None, app_data=None, user_data=None):
        """Move camera right (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.right(self.pan_speed)
            self.current_movement = "right"
            self.last_movement_time = time.time()
            self.status_message = "Moving RIGHT"
            self.add_log("Moving RIGHT")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def stop(self, sender=None, app_data=None, user_data=None):
        """Stop all movement (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.stop()
            self.current_movement = None
            self.current_zoom = None
            self.current_focus = None
            self.incoming_messages.clear()
            self.status_message = "Stopped (cleared messages)"
            self.add_log("Stopped (cleared messages)")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    # ===== Zoom Control Methods =====

    def zoom_in(self, sender=None, app_data=None, user_data=None):
        """Zoom in (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.zoom_in(self.zoom_speed)
            self.current_zoom = "in"
            self.last_movement_time = time.time()
            self.status_message = "Zooming IN"
            self.add_log("Zooming IN")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def zoom_out(self, sender=None, app_data=None, user_data=None):
        """Zoom out (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.zoom_out(self.zoom_speed)
            self.current_zoom = "out"
            self.last_movement_time = time.time()
            self.status_message = "Zooming OUT"
            self.add_log("Zooming OUT")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def zoom_stop(self, sender=None, app_data=None, user_data=None):
        """Stop zoom (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.zoom_stop()
            self.current_zoom = None
            self.status_message = "Zoom STOP"
            self.add_log("Zoom STOP")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    # ===== Focus Control Methods =====

    def focus_near(self, sender=None, app_data=None, user_data=None):
        """Focus near (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.focus_near(self.focus_speed)
            self.current_focus = "near"
            self.last_movement_time = time.time()
            self.status_message = "Focus NEAR"
            self.add_log("Focus NEAR")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def focus_far(self, sender=None, app_data=None, user_data=None):
        """Focus far (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.focus_far(self.focus_speed)
            self.current_focus = "far"
            self.last_movement_time = time.time()
            self.status_message = "Focus FAR"
            self.add_log("Focus FAR")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def focus_stop(self, sender=None, app_data=None, user_data=None):
        """Stop focus (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.focus_stop()
            self.current_focus = None
            self.status_message = "Focus STOP"
            self.add_log("Focus STOP")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    # ===== Additional Control Methods =====

    def home(self, sender=None, app_data=None, user_data=None):
        """Move to home position (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.home()
            self.status_message = "Going HOME"
            self.add_log("Going HOME")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def toggle_power(self, sender=None, app_data=None, user_data=None):
        """Toggle power (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            current_power = self.camera.get_power()
            if current_power == 1:
                self.camera.power(0)
                self.status_message = "Power OFF"
                self.add_log("Power OFF")
            elif current_power == 0:
                self.camera.power(1)
                self.status_message = "Power ON"
                self.add_log("Power ON")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def reset(self, sender=None, app_data=None, user_data=None):
        """Reset camera (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.reset()
            self.status_message = "Camera RESET"
            self.add_log("Camera RESET")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def clear(self, sender=None, app_data=None, user_data=None):
        """Clear buffer and messages (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.reset_input_buffer()
            self.incoming_messages.clear()
            self.status_message = "Buffer & messages CLEARED"
            self.add_log("Buffer & messages CLEARED")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def autofocus(self, sender=None, app_data=None, user_data=None):
        """Enable autofocus (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.autofocus()
            self.status_message = "Autofocus enabled"
            self.add_log("Autofocus enabled")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    # ===== White Balance Methods =====

    def white_balance_auto(self, sender=None, app_data=None, user_data=None):
        """Set white balance to auto (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.white_balance_auto()
            self.status_message = "White balance: Auto"
            self.add_log("White balance: Auto")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def white_balance_indoor(self, sender=None, app_data=None, user_data=None):
        """Set white balance to indoor (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.white_balance_indoor()
            self.status_message = "White balance: Indoor"
            self.add_log("White balance: Indoor")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def white_balance_outdoor(self, sender=None, app_data=None, user_data=None):
        """Set white balance to outdoor (mouse callback)."""
        if not self.ensure_connected():
            return
        try:
            self.camera.white_balance_outdoor()
            self.status_message = "White balance: Outdoor"
            self.add_log("White balance: Outdoor")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    # ===== Preset Methods =====

    def recall_preset(self, preset):
        """Recall a preset."""

        def callback(sender=None, app_data=None, user_data=None):
            if not self.ensure_connected():
                return
            try:
                self.camera.preset_recall(preset)
                self.status_message = f"Recalling preset {preset}"
                self.add_log(f"Recalling preset {preset}")
            except Exception as e:
                self.status_message = f"Error: {e}"
                self.add_log(f"Error: {e}")

        return callback

    # ===== Connection Methods =====

    def disconnect(self, sender=None, app_data=None, user_data=None):
        """Disconnect from camera."""
        try:
            if self.camera:
                self.camera.close()
                self.camera = None
                self.status_message = "Disconnected"
                self.add_log("Disconnected")
        except Exception as e:
            self.status_message = f"Error: {e}"
            self.add_log(f"Error: {e}")

    def reconnect(self, sender=None, app_data=None, user_data=None):
        """Reconnect to camera."""
        self.status_message = f"Reconnecting to {self.connection_string}..."
        self.add_log(f"Reconnecting to {self.connection_string}")
        if self.connect_camera():
            self.status_message = f"Reconnected to {self.connection_string}"

    def update_connection_string(self, sender, app_data):
        """Update connection string from input."""
        self.connection_string = app_data
        self.status_message = f"Connection string updated: {self.connection_string}"
        self.add_log(f"Connection string updated: {self.connection_string}")

    def show_window(self, label):
        """Show a window by its label if it exists."""
        try:
            dpg.show_item(label)
        except Exception:
            pass

    def load_config(self):
        """Load configuration from file."""
        config_path = get_config_path()
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                    self.connection_string = config.get("connection_string", "192.168.1.32:8234")
                    self.pan_speed = config.get("pan_speed", 5)
                    self.tilt_speed = config.get("tilt_speed", 5)
                    self.zoom_speed = config.get("zoom_speed", 5)
                    self.focus_speed = config.get("focus_speed", 5)
                    return config.get("auto_connect", False)
        except Exception as e:
            self.add_log(f"Failed to load config: {e}")
        return False

    def save_config(self):
        """Save configuration to file."""
        config_path = get_config_path()
        try:
            config = {
                "connection_string": self.connection_string,
                "pan_speed": self.pan_speed,
                "tilt_speed": self.tilt_speed,
                "zoom_speed": self.zoom_speed,
                "focus_speed": self.focus_speed,
                "auto_connect": True
            }
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.add_log(f"Failed to save config: {e}")

    # ===== Speed Adjustment Methods =====

    def increase_pan_speed(self, sender=None, app_data=None, user_data=None):
        """Increase pan speed."""
        self.pan_speed = min(24, self.pan_speed + 1)
        self.status_message = f"Pan speed: {self.pan_speed}"
        self.add_log(f"Pan speed: {self.pan_speed}")

    def decrease_pan_speed(self, sender=None, app_data=None, user_data=None):
        """Decrease pan speed."""
        self.pan_speed = max(0, self.pan_speed - 1)
        self.status_message = f"Pan speed: {self.pan_speed}"
        self.add_log(f"Pan speed: {self.pan_speed}")

    def increase_tilt_speed(self, sender=None, app_data=None, user_data=None):
        """Increase tilt speed."""
        self.tilt_speed = min(24, self.tilt_speed + 1)
        self.status_message = f"Tilt speed: {self.tilt_speed}"
        self.add_log(f"Tilt speed: {self.tilt_speed}")

    def decrease_tilt_speed(self, sender=None, app_data=None, user_data=None):
        """Decrease tilt speed."""
        self.tilt_speed = max(0, self.tilt_speed - 1)
        self.status_message = f"Tilt speed: {self.tilt_speed}"
        self.add_log(f"Tilt speed: {self.tilt_speed}")

    def increase_zoom_speed(self, sender=None, app_data=None, user_data=None):
        """Increase zoom speed."""
        self.zoom_speed = min(7, self.zoom_speed + 1)
        self.status_message = f"Zoom speed: {self.zoom_speed}"
        self.add_log(f"Zoom speed: {self.zoom_speed}")

    def decrease_zoom_speed(self, sender=None, app_data=None, user_data=None):
        """Decrease zoom speed."""
        self.zoom_speed = max(0, self.zoom_speed - 1)
        self.status_message = f"Zoom speed: {self.zoom_speed}"
        self.add_log(f"Zoom speed: {self.zoom_speed}")

    def increase_focus_speed(self, sender=None, app_data=None, user_data=None):
        """Increase focus speed."""
        self.focus_speed = min(7, self.focus_speed + 1)
        self.status_message = f"Focus speed: {self.focus_speed}"
        self.add_log(f"Focus speed: {self.focus_speed}")

    def decrease_focus_speed(self, sender=None, app_data=None, user_data=None):
        """Decrease focus speed."""
        self.focus_speed = max(0, self.focus_speed - 1)
        self.status_message = f"Focus speed: {self.focus_speed}"
        self.add_log(f"Focus speed: {self.focus_speed}")

    # ===== UI Creation =====

    def create_ui(self):
        """Create the Dear PyGui interface."""
        dpg.create_context()
        dpg.create_viewport(
            title="pyvisca-gui - VISCA PTZ Camera Control", width=1200, height=800
        )

        # === Menu Bar ===
        with dpg.viewport_menu_bar():
            # File menu
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())

            # View menu to restore windows
            with dpg.menu(label="View"):
                dpg.add_menu_item(
                    label="Show Pan/Tilt/Zoom/Focus Window",
                    callback=lambda: self.show_window("Pan/Tilt/Zoom/Focus"),
                )
                dpg.add_menu_item(
                    label="Show Status Window", callback=lambda: self.show_window("Status")
                )
                dpg.add_menu_item(
                    label="Show Com Log Window", callback=lambda: self.show_window("Com Log")
                )
                dpg.add_menu_item(
                    label="Show Connection Window",
                    callback=lambda: self.show_window("Connection"),
                )
                dpg.add_menu_item(
                    label="Show Settings Window",
                    callback=lambda: self.show_window("Settings"),
                )

        # === Pan/Tilt/Zoom Control Window ===
        with dpg.window(
            label="Pan/Tilt/Zoom/Focus", width=400, height=700, pos=(10, 10)
        ):
            dpg.add_text("Camera Movement Control", color=(255, 255, 0), bullet=True)

            dpg.add_spacer(height=10)

            # Directional buttons
            dpg.add_text("Pan/Tilt:", color=(200, 200, 200))

            # Directional pad
            with dpg.group(horizontal=True):
                dpg.add_button(label="▲", width=50, callback=self.move_up)
                dpg.add_spacer(width=20)
                dpg.add_button(label="▼", width=50, callback=self.move_down)
            with dpg.group(horizontal=True):
                dpg.add_button(label="◀", width=50, callback=self.move_left)
                dpg.add_spacer(width=20)
                dpg.add_button(label="▶", width=50, callback=self.move_right)

            dpg.add_spacer(height=10)
            dpg.add_button(label="■ STOP", width=350, callback=self.stop)

            dpg.add_spacer(height=20)

            # Zoom controls
            dpg.add_text("Zoom:", color=(200, 200, 200))
            with dpg.group(horizontal=True):
                dpg.add_button(label="ZOOM IN (+)", width=100, callback=self.zoom_in)
                dpg.add_spacer(width=20)
                dpg.add_button(label="ZOOM OUT (-)", width=100, callback=self.zoom_out)
                dpg.add_spacer(width=20)
                dpg.add_button(label="ZOOM STOP", width=100, callback=self.zoom_stop)

            dpg.add_spacer(height=20)

            # Focus controls
            dpg.add_text("Focus:", color=(200, 200, 200))
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="FOCUS NEAR ([)", width=110, callback=self.focus_near
                )
                dpg.add_spacer(width=20)
                dpg.add_button(
                    label="FOCUS FAR (])", width=110, callback=self.focus_far
                )
                dpg.add_spacer(width=20)
                dpg.add_button(
                    label="FOCUS STOP (x)", width=110, callback=self.focus_stop
                )

            dpg.add_spacer(height=20)

            # Quick actions
            dpg.add_text("Quick Actions:", color=(200, 200, 200))
            with dpg.group(horizontal=True):
                dpg.add_button(label="HOME", width=80, callback=self.home)
                dpg.add_spacer(width=10)
                dpg.add_button(label="POWER", width=80, callback=self.toggle_power)
                dpg.add_spacer(width=10)
                dpg.add_button(label="RESET", width=80, callback=self.reset)
                dpg.add_spacer(width=10)
                dpg.add_button(label="CLEAR", width=80, callback=self.clear)

        # === Status Window ===
        with dpg.window(label="Status", width=300, height=400, pos=(420, 10)):
            dpg.add_text("Camera Status", color=(255, 255, 0), bullet=True)
            dpg.add_spacer(height=10)

            # Status items (will be updated by main loop)
            self.status_connected_label = dpg.add_text("Connected: Checking...")
            self.status_power_label = dpg.add_text("Power: ...")
            self.status_pan_label = dpg.add_text("Pan: ...")
            self.status_tilt_label = dpg.add_text("Tilt: ...")
            self.status_zoom_label = dpg.add_text("Zoom: ...")
            self.status_video_label = dpg.add_text("Video: ...")
            self.status_ae_label = dpg.add_text("AE: ...")
            self.status_wb_label = dpg.add_text("WB: ...")
            self.status_message_label = dpg.add_text("Status: Initializing...")

            dpg.add_spacer(height=20)

            # Speed display
            dpg.add_separator(label="Speed Settings")
            self.speed_pan_label = dpg.add_text(f"Pan: {self.pan_speed}")
            self.speed_tilt_label = dpg.add_text(f"Tilt: {self.tilt_speed}")
            self.speed_zoom_label = dpg.add_text(f"Zoom: {self.zoom_speed}")
            self.speed_focus_label = dpg.add_text(f"Focus: {self.focus_speed}")

        # === Com Log Window ===
        with dpg.window(label="Com Log", width=400, height=400, pos=(730, 10)):
            dpg.add_text("Activity Log", color=(255, 255, 0), bullet=True)
            dpg.add_spacer(height=10)

            self.log_output = dpg.add_text("", wrap=400)

        # === Connection Window ===
        with dpg.window(label="Connection", width=300, height=200, pos=(420, 420)):
            dpg.add_text("Connection Settings", color=(255, 255, 0), bullet=True)
            dpg.add_spacer(height=10)

            dpg.add_text("Connection String:")
            dpg.add_input_text(
                hint="192.168.1.32:8234",
                default_value=self.connection_string,
                width=200,
                callback=self.update_connection_string,
                on_enter=True,
            )

            dpg.add_spacer(height=20)

            with dpg.group(horizontal=True):
                dpg.add_button(label="Connect", width=130, callback=self.reconnect)
                dpg.add_spacer(width=10)
                dpg.add_button(label="Disconnect", width=130, callback=self.disconnect)

            dpg.add_spacer(height=20)

            # Presets
            dpg.add_separator(label="Presets")
            with dpg.group(horizontal=True):
                for i in range(5):
                    dpg.add_button(
                        label=str(i), width=50, callback=self.recall_preset(i)
                    )
            with dpg.group(horizontal=True):
                for i in range(5, 10):
                    dpg.add_button(
                        label=str(i), width=50, callback=self.recall_preset(i)
                    )

        # === Settings Window ===
        with dpg.window(label="Settings", width=350, height=450, pos=(730, 420)):
            dpg.add_text("Settings", color=(255, 255, 0), bullet=True)
            dpg.add_spacer(height=10)

            # Speed controls
            dpg.add_separator(label="Speed Settings")
            dpg.add_spacer(height=10)

            self.speed_display_label = dpg.add_text(
                f"Pan: {self.pan_speed}  Tilt: {self.tilt_speed}  Zoom: {self.zoom_speed}  Focus: {self.focus_speed}"
            )
            dpg.add_spacer(height=10)

            dpg.add_text("Pan Speed:")
            with dpg.group(horizontal=True):
                dpg.add_button(label="<", width=40, callback=self.decrease_pan_speed)
                dpg.add_button(label=">", width=40, callback=self.increase_pan_speed)

            dpg.add_spacer(height=10)
            dpg.add_text("Tilt Speed:")
            with dpg.group(horizontal=True):
                dpg.add_button(label="<", width=40, callback=self.decrease_tilt_speed)
                dpg.add_button(label=">", width=40, callback=self.increase_tilt_speed)

            dpg.add_spacer(height=10)
            dpg.add_text("Zoom Speed:")
            with dpg.group(horizontal=True):
                dpg.add_button(label="<", width=40, callback=self.decrease_zoom_speed)
                dpg.add_button(label=">", width=40, callback=self.increase_zoom_speed)

            dpg.add_spacer(height=10)
            dpg.add_text("Focus Speed:")
            with dpg.group(horizontal=True):
                dpg.add_button(label="<", width=40, callback=self.decrease_focus_speed)
                dpg.add_button(label=">", width=40, callback=self.increase_focus_speed)

            dpg.add_spacer(height=20)

            # White balance
            dpg.add_separator(label="White Balance")
            dpg.add_spacer(height=10)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Auto", width=100, callback=self.white_balance_auto)
                dpg.add_spacer(width=10)
                dpg.add_button(
                    label="Indoor", width=100, callback=self.white_balance_indoor
                )
                dpg.add_spacer(width=10)
                dpg.add_button(
                    label="Outdoor", width=100, callback=self.white_balance_outdoor
                )

            dpg.add_spacer(height=20)

            # Autofocus
            dpg.add_button(label="Autofocus", width=320, callback=self.autofocus)

        # === Keyboard Handler ===

        def key_handler(sender, app_data, user_data=None):
            """Handle keyboard input."""
            try:
                if not self.ensure_connected():
                    return

                key = app_data

                # Movement: Arrow keys
                if key == dpg.mvKey_Up:
                    self.move_up()
                elif key == dpg.mvKey_Down:
                    self.move_down()
                elif key == dpg.mvKey_Left:
                    self.move_left()
                elif key == dpg.mvKey_Right:
                    self.move_right()

                # Stop
                elif key == dpg.mvKey_Space:
                    self.stop()

                # Speed: </>. for pan/tilt
                elif key == ord(","):
                    self.decrease_pan_speed()
                elif key == ord("."):
                    self.increase_pan_speed()
                elif key == ord("<"):
                    self.decrease_tilt_speed()
                elif key == ord(">"):
                    self.increase_tilt_speed()

                # Zoom speed: a/d
                elif key == ord("a"):
                    self.decrease_zoom_speed()
                elif key == ord("d"):
                    self.increase_zoom_speed()

                # Focus speed: s/f
                elif key == ord("s"):
                    self.decrease_focus_speed()
                elif key == ord("f"):
                    self.increase_focus_speed()

                # Zoom: +/-
                elif key == ord("+") or key == ord("="):
                    self.zoom_in()
                elif key == ord("-") or key == ord("_"):
                    self.zoom_out()
                elif key == ord("z"):
                    self.zoom_stop()

                # Focus: [/]
                elif key == ord("["):
                    self.focus_near()
                elif key == ord("]"):
                    self.focus_far()
                elif key == ord("x"):
                    self.focus_stop()

                # Quick actions
                elif key == ord("h"):
                    self.home()
                elif key == ord("p"):
                    self.toggle_power()
                elif key == ord("r"):
                    self.reset()
                elif key == ord("c"):
                    self.clear()
                elif key == ord("f"):
                    self.autofocus()

                # White balance: b
                elif key == ord("b"):
                    current_wb = self.camera.get_white_balance_mode()
                    if current_wb == 0:
                        self.white_balance_indoor()
                    elif current_wb == 1:
                        self.white_balance_outdoor()
                    else:
                        self.white_balance_auto()

                # Presets: 0-9
                elif ord("0") <= key <= ord("9"):
                    preset = key - ord("0")
                    self.recall_preset(preset)()

                # Quit
                elif key == dpg.mvKey_Escape:
                    self.running = False

            except Exception as e:
                self.status_message = f"Error: {e}"
                self.add_log(f"Error: {e}")


        with dpg.handler_registry():
            dpg.add_key_down_handler(callback=key_handler)

        # === Status Update Thread ===

        def status_update_loop():
            """Update UI with camera status."""
            while self.running:
                try:
                    now = time.time()
                    if now - self.last_status_check > self.status_check_interval:
                        status = self.get_camera_status()
                        self.last_status_check = now
                        self._cached_status = status

                        # Update status labels
                        if status.get("connected"):
                            conn_text = f"Connected: {self.connection_string}"
                            conn_color = (0, 200, 0)
                        else:
                            conn_text = (
                                f"Disconnected: {status.get('error', 'Unknown')}"
                            )
                            conn_color = (200, 0, 0)

                        dpg.set_value(self.status_connected_label, conn_text)
                        dpg.set_item_color(
                            self.status_connected_label, dpg.mvThemeCol_Text, conn_color
                        )

                        if status.get("connected"):
                            dpg.set_value(
                                self.status_power_label,
                                f"Power: {status.get('power', 'Unknown')}",
                            )
                            dpg.set_value(
                                self.status_pan_label, f"Pan: {status.get('pan', 0)}"
                            )
                            dpg.set_value(
                                self.status_tilt_label, f"Tilt: {status.get('tilt', 0)}"
                            )
                            dpg.set_value(
                                self.status_zoom_label, f"Zoom: {status.get('zoom', 0)}"
                            )
                            dpg.set_value(
                                self.status_video_label,
                                f"Video: {status.get('video_format', 'Unknown')}",
                            )
                            dpg.set_value(
                                self.status_ae_label,
                                f"AE: {status.get('ae_mode', 'Unknown')}",
                            )
                            dpg.set_value(
                                self.status_wb_label,
                                f"WB: {status.get('white_balance', 'Unknown')}",
                            )

                            # Update speed display
                            dpg.set_value(
                                self.speed_pan_label, f"Pan: {status.get('pan_speed', 0)}"
                            )
                            dpg.set_value(
                                self.speed_tilt_label,
                                f"Tilt: {status.get('tilt_speed', 0)}",
                            )
                            dpg.set_value(
                                self.speed_zoom_label, f"Zoom: {status.get('zoom_speed', 0)}"
                            )
                            dpg.set_value(
                                self.speed_focus_label,
                                f"Focus: {status.get('focus_speed', 0)}",
                            )

                        dpg.set_value(
                            self.status_message_label, f"Status: {self.status_message}"
                        )

                        # Update log
                        log_text = "\n".join(self.log_messages[-30:])
                        dpg.set_value(self.log_output, log_text)

                    self.check_incoming_messages()
                    self.check_movement_timeout()

                    # Update speeds in PTZ window
                    dpg.set_value(
                        self.speed_display_label,
                        f"Pan: {self.pan_speed}  Tilt: {self.tilt_speed}  Zoom: {self.zoom_speed}  Focus: {self.focus_speed}",
                    )

                except Exception:
                    pass

                time.sleep(0.1)

        # Start status update thread
        self.status_thread = threading.Thread(target=status_update_loop, daemon=True)
        self.status_thread.start()

    def run(self):
        """Run the GUI main loop."""
        self.create_ui()
        dpg.setup_dearpygui()
        dpg.show_viewport()

        while self.running and dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

        dpg.destroy_context()


def main():
    """Main entry point."""
    import sys

    connection_string = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.32:8234"
    gui = ViscaGUI(connection_string)
    gui.run()


if __name__ == "__main__":
    main()
