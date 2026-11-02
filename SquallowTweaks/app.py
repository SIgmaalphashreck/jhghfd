"""SquallowTweaks - Hauptfenster."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

import pages_a
import pages_b
import service as svc
from ui_common import (ACCENT2, GREEN, RED, GradientLine, NavButton, apply_dark_titlebar, label, make_scroll, pill, tinted_pixmap)

APP_NAME = "SquallowTweaks"
VERSION = "1.1.0"


def asset(name: str) -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / "assets" / name)


class MainWindow(QMainWindow):
    # (Bereich, [(Name, Icon)])
    NAV = (("ÜBERSICHT", (("Dashboard", "dashboard"),)),
           ("OPTIMIERUNG", (("Tweaks", "bolt"), ("Fortnite", "target"), ("Benchmark", "bench"))),
           ("SYSTEM", (("Prozesse", "list"), ("Netzwerk", "wifi"), ("Bereinigung", "trash"), ("Einstellungen", "gear"))))
    SCROLLING = ("Tweaks", "Fortnite", "Benchmark", "Netzwerk", "Bereinigung", "Einstellungen")

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(asset("bird.png")))
        self.resize(1320, 840)
        self.setMinimumSize(1120, 720)
        self.service = svc.Service()
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(GradientLine())
        body = QHBoxLayout()
        body.setSpacing(0)
        outer.addLayout(body, 1)
        body.addWidget(self._sidebar())
        self.stack = QStackedWidget()
        s = self.service
        self.pages = {
            "Dashboard": pages_a.DashboardPage(s), "Tweaks": pages_a.TweaksPage(s), "Fortnite": pages_a.FortnitePage(s),
            "Benchmark": pages_a.BenchmarkPage(s), "Prozesse": pages_b.ProcessesPage(s), "Netzwerk": pages_b.NetworkPage(s),
            "Bereinigung": pages_b.CleanPage(s), "Einstellungen": pages_b.SettingsPage(s),
        }
        self.holders = {}
        for name, page in self.pages.items():
            page.navigate.connect(self.go)
            holder = make_scroll(page) if name in self.SCROLLING else page
            self.holders[name] = holder
            self.stack.addWidget(holder)
        body.addWidget(self.stack, 1)
        self.sampler = svc.Sampler()
        self.sampler.sample.connect(self.on_sample)
        self.sampler.procs.connect(self.pages["Prozesse"].on_procs)
        self.sampler.start()
        self.service.refresh_states()
        self.go("Dashboard")

    def _sidebar(self) -> QWidget:
        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(232)
        v = QVBoxLayout(side)
        v.setContentsMargins(14, 20, 14, 16)
        v.setSpacing(2)
        logo = QHBoxLayout()
        logo.setContentsMargins(6, 0, 0, 10)
        icon = QLabel()
        icon.setPixmap(tinted_pixmap(asset("bird.png"), 44))
        logo.addWidget(icon)
        name = QVBoxLayout()
        name.setSpacing(0)
        t1 = QLabel(f"Squallow<span style='color:{ACCENT2};'>Tweaks</span>")
        t1.setTextFormat(Qt.RichText)
        t1.setStyleSheet("font-size:15px;font-weight:700;")
        name.addWidget(t1)
        name.addWidget(label(f"v{VERSION}", "dim"))
        logo.addLayout(name)
        logo.addStretch(1)
        v.addLayout(logo)
        self.nav_buttons: dict[str, NavButton] = {}
        for section, items in self.NAV:
            sec = label(section, "section")
            sec.setContentsMargins(10, 14, 0, 6)
            v.addWidget(sec)
            for text, ico in items:
                b = NavButton(text, ico)
                b.clicked.connect(lambda _c=False, n=text: self.go(n))
                v.addWidget(b)
                self.nav_buttons[text] = b
        v.addStretch(1)
        row = QHBoxLayout()
        row.setContentsMargins(6, 0, 0, 0)
        row.addWidget(pill("ADMIN" if self.service.admin else "KEIN ADMIN", GREEN if self.service.admin else RED))
        row.addStretch(1)
        v.addLayout(row)
        return side

    def go(self, name: str):
        for n, b in self.nav_buttons.items():
            b.setChecked(n == name)
        self.stack.setCurrentWidget(self.holders[name])
        self.sampler.want_procs = name == "Prozesse"
        if name == "Fortnite":
            self.pages["Fortnite"].refresh()
        if name == "Netzwerk":
            if not self.pages["Netzwerk"].monitor:
                self.pages["Netzwerk"].start()
        else:
            self.pages["Netzwerk"].stop()

    def on_sample(self, d: dict):
        self.service.fortnite_running = bool(d.get("fn"))
        self.pages["Dashboard"].on_sample(d)
        self.pages["Prozesse"].on_sample(d)
        self.sampler.auto_high = self.pages["Fortnite"].prio_on
        if self.stack.currentWidget() is self.holders["Fortnite"]:
            self.pages["Fortnite"].refresh()

    def showEvent(self, e):
        super().showEvent(e)
        apply_dark_titlebar(self)

    def closeEvent(self, e):
        self.sampler.stop()
        self.pages["Netzwerk"].shutdown()
        self.sampler.wait(2500)
        super().closeEvent(e)
