from __future__ import annotations

import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
from typing import Optional

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")

from gi.repository import AyatanaAppIndicator3, Gio, GLib, Gtk

from .headset import HeadsetControl, HeadsetState, find_program
from .monitor import LOW_BATTERY_PERCENT, decide
from .reminder import ReminderState, step
from .settings import AUTO_OFF_PRESETS, REMINDER_HOURS, Settings, SettingsStore

APP_ID = "io.github.abdelali.HeadsetTray"
APP_NAME = "Headset Tray"
ICON_NAME = "audio-headset-symbolic"
POLL_SECONDS = 60
# The widest label the indicator will show, so the top bar keeps its width
# as the number changes.
LABEL_GUIDE = "⚡100%"


def battery_label(state: Optional[HeadsetState]) -> str:
    if state is None or not state.connected or state.battery is None:
        return "—"
    return f"{'⚡' if state.charging else ''}{state.battery}%"


def status_line(state: Optional[HeadsetState]) -> str:
    if state is None:
        return "Looking for the headset…"
    if not state.connected:
        return state.error or "Headset not connected"
    level = "unknown" if state.battery is None else f"{state.battery}%"
    return f"Battery: {level}{' (charging)' if state.charging else ''}"


def preset_label(minutes: int) -> str:
    if minutes == 0:
        return "Never"
    hours, rest = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if rest:
        parts.append(f"{rest} minutes")
    return " ".join(parts)


class HeadsetTray(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.store = SettingsStore()
        self.settings = self.store.load()
        self.headset = HeadsetControl(find_program())
        # One worker, so that a read and a write never talk to the dongle at
        # the same time.
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.state: Optional[HeadsetState] = None
        self.alert_armed = True
        # The auto-off time still has to reach the headset. Set at start,
        # on every change of the setting and on every reconnection; cleared
        # once the headset has accepted it.
        self.auto_off_pending = True
        self.auto_off_failed = False
        self.preset_items: dict[int, Gtk.RadioMenuItem] = {}
        self.reminder = ReminderState()
        # Plays a sound from the desktop's sound theme; ships with Ubuntu.
        self.sound_player = shutil.which("canberra-gtk-play")

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        # No window: the indicator is the whole interface, so keep the
        # application alive without one.
        self.hold()
        self._build_indicator()
        self._refresh()
        GLib.timeout_add_seconds(POLL_SECONDS, self._on_poll_timer)
        self._poll()

    def do_activate(self) -> None:
        pass

    def do_shutdown(self) -> None:
        self.worker.shutdown(wait=False, cancel_futures=True)
        Gtk.Application.do_shutdown(self)

    # -- interface ---------------------------------------------------------

    def _build_indicator(self) -> None:
        self.indicator = AyatanaAppIndicator3.Indicator.new(
            APP_ID,
            ICON_NAME,
            AyatanaAppIndicator3.IndicatorCategory.HARDWARE,
        )
        self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title(APP_NAME)

        menu = Gtk.Menu()
        self.status_item = Gtk.MenuItem(label=status_line(None))
        self.status_item.set_sensitive(False)
        menu.append(self.status_item)

        self.auto_off_status_item = Gtk.MenuItem(label="")
        self.auto_off_status_item.set_sensitive(False)
        menu.append(self.auto_off_status_item)
        menu.append(Gtk.SeparatorMenuItem())

        auto_off_item = Gtk.MenuItem(label="Turn off after")
        presets = Gtk.Menu()
        group: Optional[Gtk.RadioMenuItem] = None
        for minutes in AUTO_OFF_PRESETS:
            item = Gtk.RadioMenuItem.new_with_label_from_widget(group, preset_label(minutes))
            group = group or item
            item.set_active(minutes == self.settings.auto_off_minutes)
            item.connect("toggled", self._on_preset_toggled, minutes)
            presets.append(item)
            self.preset_items[minutes] = item
        auto_off_item.set_submenu(presets)
        menu.append(auto_off_item)

        self.alert_item = Gtk.CheckMenuItem(
            label=f"Low-battery alert (at {LOW_BATTERY_PERCENT}%)"
        )
        self.alert_item.set_active(self.settings.low_battery_alert)
        self.alert_item.connect("toggled", self._on_alert_toggled)
        menu.append(self.alert_item)

        self.reminder_item = Gtk.CheckMenuItem(label="Evening charge reminder")
        self.reminder_item.set_active(self.settings.charge_reminder)
        self.reminder_item.connect("toggled", self._on_reminder_toggled)
        menu.append(self.reminder_item)

        self.reminder_hour_item = Gtk.MenuItem(label="Remind from")
        hours = Gtk.Menu()
        group = None
        for hour in REMINDER_HOURS:
            item = Gtk.RadioMenuItem.new_with_label_from_widget(group, f"{hour}:00")
            group = group or item
            item.set_active(hour == self.settings.charge_reminder_hour)
            item.connect("toggled", self._on_reminder_hour_toggled, hour)
            hours.append(item)
        self.reminder_hour_item.set_submenu(hours)
        self.reminder_hour_item.set_sensitive(self.settings.charge_reminder)
        menu.append(self.reminder_hour_item)
        menu.append(Gtk.SeparatorMenuItem())

        refresh_item = Gtk.MenuItem(label="Refresh now")
        refresh_item.connect("activate", lambda _item: self._poll())
        menu.append(refresh_item)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _item: self.quit())
        menu.append(quit_item)

        menu.show_all()
        self.indicator.set_menu(menu)

    def _refresh(self) -> None:
        self.indicator.set_label(battery_label(self.state), LABEL_GUIDE)
        self.status_item.set_label(status_line(self.state))
        connected = self.state is not None and self.state.connected
        if self.auto_off_failed and connected:
            self.auto_off_status_item.set_label("Could not set auto-off — will retry")
            self.auto_off_status_item.show()
        else:
            self.auto_off_status_item.hide()

    # -- settings ----------------------------------------------------------

    def _on_preset_toggled(self, item: Gtk.RadioMenuItem, minutes: int) -> None:
        # Toggled fires for the item losing the selection as well.
        if not item.get_active() or minutes == self.settings.auto_off_minutes:
            return
        self._save(replace(self.settings, auto_off_minutes=minutes))
        self.auto_off_pending = True
        self._apply_auto_off()

    def _on_alert_toggled(self, item: Gtk.CheckMenuItem) -> None:
        self._save(replace(self.settings, low_battery_alert=item.get_active()))

    def _on_reminder_toggled(self, item: Gtk.CheckMenuItem) -> None:
        self._save(replace(self.settings, charge_reminder=item.get_active()))
        self.reminder_hour_item.set_sensitive(item.get_active())
        if not item.get_active():
            self.withdraw_notification("charge-reminder")

    def _on_reminder_hour_toggled(self, item: Gtk.RadioMenuItem, hour: int) -> None:
        if not item.get_active() or hour == self.settings.charge_reminder_hour:
            return
        self._save(replace(self.settings, charge_reminder_hour=hour))

    def _save(self, settings: Settings) -> None:
        self.settings = settings
        try:
            self.store.save(settings)
        except OSError as error:
            print(f"headset-tray: could not save settings: {error}", file=sys.stderr)

    # -- headset -----------------------------------------------------------

    def _on_poll_timer(self) -> bool:
        self._poll()
        return GLib.SOURCE_CONTINUE

    def _poll(self) -> None:
        # Looked for again on every poll until found, so that installing
        # HeadsetControl while the tray runs needs no restart.
        if self.headset.program is None:
            self.headset.program = find_program()
        future = self.worker.submit(self.headset.read)
        future.add_done_callback(
            lambda done: GLib.idle_add(self._on_state, done.result())
        )

    def _on_state(self, state: HeadsetState) -> bool:
        decision = decide(self.state, state, self.alert_armed)
        self.state = state
        self.alert_armed = decision.alert_armed
        if decision.apply_auto_off:
            self.auto_off_pending = True
        if decision.alert_low_battery and self.settings.low_battery_alert:
            self._notify_low_battery(state)
        self._check_charge_reminder(state)
        self._apply_auto_off()
        self._refresh()
        return GLib.SOURCE_REMOVE

    def _apply_auto_off(self) -> None:
        if not self.auto_off_pending or self.state is None or not self.state.connected:
            return
        minutes = self.settings.auto_off_minutes
        future = self.worker.submit(self.headset.set_auto_off, minutes)
        future.add_done_callback(
            lambda done: GLib.idle_add(self._on_auto_off_applied, minutes, done.result())
        )

    def _on_auto_off_applied(self, minutes: int, accepted: bool) -> bool:
        # A newer choice made while this one was on its way stays pending.
        if minutes == self.settings.auto_off_minutes:
            self.auto_off_pending = not accepted
            self.auto_off_failed = not accepted
        self._refresh()
        return GLib.SOURCE_REMOVE

    def _check_charge_reminder(self, state: HeadsetState) -> None:
        if not self.settings.charge_reminder:
            return
        self.reminder, remind = step(
            self.reminder, state, datetime.now(), self.settings.charge_reminder_hour
        )
        if remind:
            self._notify_charge_reminder(state)
        elif state.charging:
            self.withdraw_notification("charge-reminder")

    def _notify_charge_reminder(self, state: HeadsetState) -> None:
        notification = Gio.Notification.new("Headset not charging")
        left = "" if state.battery is None else f"{state.battery}% left — "
        notification.set_body(f"{left}put it on charge before you sleep.")
        notification.set_icon(Gio.ThemedIcon.new(ICON_NAME))
        notification.set_priority(Gio.NotificationPriority.HIGH)
        self.send_notification("charge-reminder", notification)
        self._play_sound()

    def _play_sound(self) -> None:
        if self.sound_player is None:
            return
        try:
            # Started and left to finish on its own: the sound is a cue, and
            # nothing waits on it.
            Gio.Subprocess.new(
                [self.sound_player, "--id", "message-new-instant"],
                Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE,
            ).wait_async(None, None, None)
        except GLib.Error as error:  # pragma: no cover - depends on host audio
            print(f"headset-tray: could not play sound: {error}", file=sys.stderr)

    def _notify_low_battery(self, state: HeadsetState) -> None:
        notification = Gio.Notification.new("Headset battery low")
        notification.set_body(f"{state.battery}% left — time to charge it.")
        notification.set_icon(Gio.ThemedIcon.new(ICON_NAME))
        self.send_notification("low-battery", notification)


def main() -> int:
    return HeadsetTray().run(sys.argv)
