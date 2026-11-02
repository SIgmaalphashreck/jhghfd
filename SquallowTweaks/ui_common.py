"""SquallowTweaks - Farben, Stylesheet und Widgets (mit animierten Hover-Effekten)."""
from __future__ import annotations

import math
import os
import time
from collections import deque
from typing import Optional

from PySide6.QtCore import (Property, QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer, QVariantAnimation, Signal)
from PySide6.QtGui import (QBrush, QColor, QCursor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QPolygonF, QRadialGradient)
from PySide6.QtWidgets import (QAbstractButton, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QSizePolicy, QVBoxLayout, QWidget)

BG = "#0A0A10"
SIDEBAR = "#0D0D15"
CARD = "#13131D"
CARD2 = "#1B1B2B"
BORDER = "#23233A"
TEXT = "#EDEDF7"
MUTED = "#8C8CA8"
DIM = "#5E5E7A"
ACCENT = "#8B7CF6"
ACCENT2 = "#B89CFF"
GREEN = "#4ADE80"
YELLOW = "#FBBF24"
RED = "#F87171"
CYAN = "#5EEAD4"
PINK = "#F472B6"

TAG_COLORS = {"FPS": ACCENT2, "LATENZ": CYAN, "PING": GREEN, "FRAMETIME": PINK}
EVIDENCE_COLORS = {"belegt": GREEN, "klein": YELLOW, "schwach": DIM}
EVIDENCE_TEXT = {"belegt": "Wirkung laut Tests belegt", "klein": "Kleine/systemabhängige Wirkung", "schwach": "Wirkung kaum belegt (optional)"}

QSS = f"""
* {{ font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans", "DejaVu Sans", sans-serif; font-size: 13px; color: {TEXT}; }}
QMainWindow, #root {{ background: {BG}; }}
QWidget {{ background: transparent; }}
#sidebar {{ background: {SIDEBAR}; border-right: 1px solid {BORDER}; }}
QLabel#h1 {{ font-size: 26px; font-weight: 700; }}
QLabel#h2 {{ font-size: 15px; font-weight: 600; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#dim {{ color: {DIM}; font-size: 11px; }}
QLabel#section {{ color: {DIM}; font-size: 10px; font-weight: 700; letter-spacing: 2px; }}
QLabel#big {{ font-size: 26px; font-weight: 700; }}
QLabel#pill {{ border-radius: 8px; padding: 2px 8px; font-size: 10px; font-weight: 700; letter-spacing: 1px; }}
QLineEdit {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; padding: 9px 12px; selection-background-color: {ACCENT}; }}
QLineEdit:focus {{ border-color: {ACCENT}; background: #171726; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2B2B45; border-radius: 4px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: #4A4A78; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ height: 0; }}
QProgressBar {{ background: #1B1B2B; border: none; border-radius: 3px; max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ border-radius: 3px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {CYAN}); }}
QToolTip {{ background: #1B1B2B; color: {TEXT}; border: 1px solid #34345A; padding: 8px; border-radius: 6px; }}
QTableView {{ background: transparent; border: none; gridline-color: transparent; outline: 0; }}
QHeaderView::section {{ background: transparent; color: {DIM}; border: none; padding: 6px 10px; font-size: 10px; font-weight: 700; letter-spacing: 2px; }}
QMessageBox {{ background: {CARD}; }}
"""


def lerp(a, b, t: float) -> QColor:
    a, b = QColor(a), QColor(b)
    t = max(0.0, min(1.0, t))
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t), int(a.alpha() + (b.alpha() - a.alpha()) * t))


def alpha(color, a: int) -> QColor:
    c = QColor(color)
    c.setAlpha(a)
    return c


class HoverValue:
    """Animierter Wert 0..1 fuer Hover-Effekte (sanfter Uebergang statt Sprung)."""

    def __init__(self, widget: QWidget, duration: int = 160):
        self.v = 0.0
        self.widget = widget
        self.anim = QVariantAnimation(widget)
        self.anim.setDuration(duration)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._tick)

    def _tick(self, x):
        self.v = float(x)
        self.widget.update()

    def to(self, end: float):
        self.anim.stop()
        self.anim.setStartValue(self.v)
        self.anim.setEndValue(float(end))
        self.anim.start()


def pointer_inside(w: QWidget) -> bool:
    return w.rect().contains(w.mapFromGlobal(QCursor.pos()))


# ---------------------------------------------------------------------------
# Icons (gezeichnet)
# ---------------------------------------------------------------------------
def draw_icon(p: QPainter, name: str, rect: QRectF, color) -> None:
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(rect.topLeft())
    s = rect.width()
    c = QColor(color)
    p.setPen(QPen(c, max(1.6, s * 0.085), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    if name == "dashboard":
        g = s * 0.14
        w = (s - 3 * g) / 2
        for r in range(2):
            for q in range(2):
                p.drawRoundedRect(QRectF(g + q * (w + g), g + r * (w + g), w, w), 3, 3)
    elif name == "bolt":
        poly = QPolygonF([QPointF(s * .58, s * .08), QPointF(s * .22, s * .56), QPointF(s * .47, s * .56),
                          QPointF(s * .40, s * .92), QPointF(s * .78, s * .42), QPointF(s * .52, s * .42)])
        p.setBrush(c)
        p.drawPolygon(poly)
    elif name == "target":
        p.drawEllipse(QRectF(s * .14, s * .14, s * .72, s * .72))
        p.drawEllipse(QRectF(s * .36, s * .36, s * .28, s * .28))
        for a, b, c2, d in ((.5, .02, .5, .2), (.5, .8, .5, .98), (.02, .5, .2, .5), (.8, .5, .98, .5)):
            p.drawLine(QPointF(s * a, s * b), QPointF(s * c2, s * d))
    elif name == "bench":
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        for i, h in enumerate((0.34, 0.62, 0.9)):
            p.drawRoundedRect(QRectF(s * (0.12 + i * 0.3), s * .94 - s * h, s * .2, s * h), 2, 2)
    elif name == "wifi":
        for r in (0.20, 0.36, 0.52):
            p.drawArc(QRectF(s * .5 - s * r, s * .78 - s * r, 2 * s * r, 2 * s * r), 45 * 16, 90 * 16)
        p.setBrush(c)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(s * .5, s * .78), s * .06, s * .06)
    elif name == "list":
        for i in range(3):
            y = s * (0.22 + i * 0.28)
            p.drawLine(QPointF(s * .30, y), QPointF(s * .92, y))
            p.setBrush(c)
            p.drawEllipse(QPointF(s * .12, y), 1.4, 1.4)
            p.setBrush(Qt.NoBrush)
    elif name == "trash":
        p.drawLine(QPointF(s * .18, s * .26), QPointF(s * .82, s * .26))
        p.drawLine(QPointF(s * .40, s * .26), QPointF(s * .40, s * .14))
        p.drawLine(QPointF(s * .40, s * .14), QPointF(s * .60, s * .14))
        p.drawLine(QPointF(s * .60, s * .14), QPointF(s * .60, s * .26))
        path = QPainterPath()
        path.moveTo(s * .26, s * .26)
        path.lineTo(s * .30, s * .88)
        path.lineTo(s * .70, s * .88)
        path.lineTo(s * .74, s * .26)
        p.drawPath(path)
        p.drawLine(QPointF(s * .44, s * .42), QPointF(s * .44, s * .72))
        p.drawLine(QPointF(s * .56, s * .42), QPointF(s * .56, s * .72))
    elif name == "gear":
        p.drawEllipse(QRectF(s * .30, s * .30, s * .40, s * .40))
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(QPointF(s * .5 + math.cos(a) * s * .30, s * .5 + math.sin(a) * s * .30),
                       QPointF(s * .5 + math.cos(a) * s * .44, s * .5 + math.sin(a) * s * .44))
    p.restore()


def tinted_pixmap(path: str, size: int) -> QPixmap:
    return QPixmap(path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


# ---------------------------------------------------------------------------
# Bausteine
# ---------------------------------------------------------------------------
def label(text: str = "", name: str = "", wrap: bool = False) -> QLabel:
    lab = QLabel(text)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(wrap)
    return lab


def pill(text: str, color: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("pill")
    c = QColor(color)
    lab.setStyleSheet(f"QLabel#pill {{ color: {color}; background: rgba({c.red()},{c.green()},{c.blue()},38); }}")
    lab.setAlignment(Qt.AlignCenter)
    lab.setFixedHeight(20)
    lab.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    return lab


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", name: str = ""):
        super().__init__(text)
        if name:
            self.setObjectName(name)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(40)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _e):
        p = QPainter(self)
        fm = QFontMetrics(self.font())
        p.setPen(self.palette().color(self.foregroundRole()))
        p.setFont(self.font())
        p.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, fm.elidedText(self.text(), Qt.ElideRight, self.width()))


class HoverFrame(QFrame):
    """Karte mit animiertem Hover: Farbwechsel, leuchtender Rand und Akzent-Linie oben."""

    def __init__(self, radius: int = 14, base: str = CARD, hover: str = CARD2, border: str = BORDER, hborder: str = ACCENT,
                 hover_on: bool = True):
        super().__init__()
        self.radius, self.base, self.hover, self.border, self.hborder, self.hover_on = radius, base, hover, border, hborder, hover_on
        self.hv = HoverValue(self)

    def enterEvent(self, e):
        if self.hover_on:
            self.hv.to(1)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self.hover_on and not pointer_inside(self):
            self.hv.to(0)
        super().leaveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        h = self.hv.v
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(lerp(self.border, self.hborder, h * 0.9), 1 + h * 0.6))
        p.setBrush(lerp(self.base, self.hover, h))
        p.drawRoundedRect(r, self.radius, self.radius)
        if h > 0.02:
            g = QLinearGradient(r.left(), 0, r.right(), 0)
            g.setColorAt(0, alpha(self.hborder, 0))
            g.setColorAt(0.5, alpha(self.hborder, int(200 * h)))
            g.setColorAt(1, alpha(CYAN, 0))
            p.setPen(QPen(QBrush(g), 1.6))
            p.drawLine(QPointF(r.left() + self.radius, r.top() + 0.8), QPointF(r.right() - self.radius, r.top() + 0.8))


class Card(HoverFrame):
    def __init__(self, name: str = "card"):
        if name == "hero":
            super().__init__(16, "#19153A", "#201B48", "#2E2A55", ACCENT2)
        else:
            super().__init__(14)


class AnimButton(QPushButton):
    """Button mit animiertem Hover. variant: accent | ghost | danger | chip."""

    def __init__(self, text: str, variant: str = "ghost"):
        super().__init__(text)
        self.variant = variant
        self.hv = HoverValue(self)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(variant == "chip")
        self.setFocusPolicy(Qt.NoFocus)
        self._fx: Optional[QGraphicsDropShadowEffect] = None
        self.setMinimumWidth(self.sizeHint().width())
        if variant == "accent":
            self._fx = QGraphicsDropShadowEffect(self)
            self._fx.setOffset(0, 4)
            self._fx.setBlurRadius(24)
            self._fx.setColor(alpha(ACCENT, 100))
            self.setGraphicsEffect(self._fx)
            self.hv.anim.valueChanged.connect(self._glow)

    def _glow(self, v):
        if self._fx:
            self._fx.setBlurRadius(24 + 18 * float(v))
            self._fx.setColor(alpha(ACCENT, int(100 + 110 * float(v))))

    def sizeHint(self) -> QSize:
        f = QFont(self.font())
        f.setBold(True)
        f.setPixelSize(15 if self.variant == "accent" else 13)
        w = QFontMetrics(f).horizontalAdvance(self.text())
        return QSize(w + {"accent": 56, "chip": 30}.get(self.variant, 34), {"accent": 48, "chip": 32}.get(self.variant, 38))

    def enterEvent(self, e):
        self.hv.to(1)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.hv.to(0)
        super().leaveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        h = self.hv.v
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        v = self.variant
        rad = 12 if v == "accent" else (r.height() / 2 if v == "chip" else 10)
        txt = QColor("#ffffff")
        if not self.isEnabled():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#2A2848"))
            p.drawRoundedRect(r, rad, rad)
            txt = QColor(DIM)
        elif v == "accent":
            g = QLinearGradient(r.left(), 0, r.right(), 0)
            g.setColorAt(0, lerp("#7C6CF0", "#9183FF", h))
            g.setColorAt(1, lerp("#A98BFF", "#C4A9FF", h))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(r, rad, rad)
        elif v == "danger":
            p.setPen(QPen(lerp("#4A2630", RED, h), 1))
            p.setBrush(lerp("#2A1A22", "#3C2029", h))
            p.drawRoundedRect(r, rad, rad)
            txt = QColor(RED)
        elif v == "chip":
            on = self.isChecked()
            p.setPen(QPen(QColor(ACCENT) if on else lerp(BORDER, "#4A4A78", h), 1))
            p.setBrush(QColor("#261F4D") if on else lerp(CARD, CARD2, h))
            p.drawRoundedRect(r, rad, rad)
            txt = QColor("#ffffff") if on else lerp(MUTED, TEXT, h)
        else:
            p.setPen(QPen(lerp(BORDER, ACCENT, h), 1))
            p.setBrush(lerp(CARD2, "#262244", h))
            p.drawRoundedRect(r, rad, rad)
        p.setPen(txt)
        f = QFont(self.font())
        f.setBold(True)
        f.setPixelSize(15 if v == "accent" else 13)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, self.text())


class NavButton(QPushButton):
    def __init__(self, text: str, icon: str):
        super().__init__(text)
        self.icon_name = icon
        self.hv = HoverValue(self, 140)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(42)
        self.setFocusPolicy(Qt.NoFocus)

    def enterEvent(self, e):
        self.hv.to(1)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.hv.to(0)
        super().leaveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        h = self.hv.v
        on = self.isChecked()
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if on:
            g = QLinearGradient(r.left(), 0, r.right(), 0)
            g.setColorAt(0, QColor("#2B2266"))
            g.setColorAt(1, QColor("#1B1838"))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(r, 10, 10)
            p.setBrush(QColor(ACCENT2))
            p.drawRoundedRect(QRectF(0, r.height() * 0.22, 3.5, r.height() * 0.56 + 2), 2, 2)
        elif h > 0.01:
            p.setPen(Qt.NoPen)
            p.setBrush(alpha("#26264A", int(255 * h)))
            p.drawRoundedRect(r, 10, 10)
        col = QColor(ACCENT2) if on else lerp(MUTED, TEXT, h)
        draw_icon(p, self.icon_name, QRectF(16 + 2 * h, (self.height() - 20) / 2, 20, 20), col)
        p.setPen(QColor(TEXT) if on else lerp(MUTED, TEXT, h))
        f = QFont(self.font())
        f.setPixelSize(14)
        f.setWeight(QFont.DemiBold if on else QFont.Medium)
        p.setFont(f)
        p.drawText(QRectF(48 + 2 * h, 0, self.width() - 56, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class GradientLine(QWidget):
    """Duenne Akzentlinie mit wanderndem Lichtreflex."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(3)
        self.pos = -0.3
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(5200)
        self.anim.setStartValue(-0.3)
        self.anim.setEndValue(1.3)
        self.anim.setLoopCount(-1)
        self.anim.valueChanged.connect(self._t)
        self.anim.start()

    def _t(self, v):
        self.pos = float(v)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0, QColor(ACCENT))
        g.setColorAt(1, QColor(CYAN))
        p.fillRect(self.rect(), QBrush(g))
        s = QLinearGradient(self.width() * (self.pos - 0.15), 0, self.width() * (self.pos + 0.15), 0)
        s.setColorAt(0, QColor(255, 255, 255, 0))
        s.setColorAt(0.5, QColor(255, 255, 255, 150))
        s.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(self.rect(), QBrush(s))


class Toggle(QAbstractButton):
    def __init__(self):
        super().__init__()
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(46, 26)
        self._pos = 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)
        self.hv = HoverValue(self, 120)

    def _get(self) -> float:
        return self._pos

    def _set(self, v: float) -> None:
        self._pos = v
        self.update()

    offset = Property(float, _get, _set)

    def enterEvent(self, e):
        self.hv.to(1)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.hv.to(0)
        super().leaveEvent(e)

    def _animate(self, on: bool):
        self._anim.stop()
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def set_checked_silent(self, on: bool):
        self.blockSignals(True)
        self.setChecked(on)
        self.blockSignals(False)
        self._anim.stop()
        self._pos = 1.0 if on else 0.0
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        t = self._pos
        col = lerp(lerp("#2A2A42", "#3A3A5C", self.hv.v), ACCENT, t)
        if not self.isEnabled():
            col.setAlpha(110)
        if self.hv.v > 0.02 and self.isEnabled() and t > 0.5:
            p.setPen(QPen(alpha(ACCENT2, int(90 * self.hv.v)), 3))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(-0.5, -0.5, 0.5, 0.5), r.height() / 2, r.height() / 2)
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = r.left() + 3 + (r.width() - d - 6) * t
        p.setBrush(QColor("#ffffff" if self.isEnabled() else "#9A9AB0"))
        p.drawEllipse(QRectF(x, r.top() + 3, d, d))


class Chips(QWidget):
    changed = Signal(str)

    def __init__(self, names: list[str], current: Optional[str] = None):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.buttons: dict[str, AnimButton] = {}
        for n in names:
            b = AnimButton(n, "chip")
            b.clicked.connect(lambda _c=False, name=n: self.select(name))
            lay.addWidget(b)
            self.buttons[n] = b
        lay.addStretch(1)
        self.current = names[0]
        self.select(current or names[0], emit=False)

    def select(self, name: str, emit: bool = True):
        for n, b in self.buttons.items():
            b.setChecked(n == name)
            b.update()
        self.current = name
        if emit:
            self.changed.emit(name)


class RingGauge(QWidget):
    def __init__(self, c1: str = ACCENT, c2: str = CYAN, minimum: int = 140):
        super().__init__()
        self.c1, self.c2 = QColor(c1), QColor(c2)
        self._target = 0.0
        self._shown = 0.0
        self.text = "–"
        self.sub = ""
        self.setMinimumSize(minimum, minimum)
        self._anim = QPropertyAnimation(self, b"shown", self)
        self._anim.setDuration(450)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def _g(self) -> float:
        return self._shown

    def _s(self, v: float) -> None:
        self._shown = v
        self.update()

    shown = Property(float, _g, _s)

    def set_value(self, frac: Optional[float], text: str, sub: str = ""):
        self.text, self.sub = text, sub
        frac = max(0.0, min(1.0, frac or 0.0))
        if abs(frac - self._target) > 0.004:
            self._target = frac
            self._anim.stop()
            self._anim.setStartValue(self._shown)
            self._anim.setEndValue(frac)
            self._anim.start()
        else:
            self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height())
        th = max(10, side * 0.085)
        r = QRectF((self.width() - side) / 2 + th, (self.height() - side) / 2 + th, side - 2 * th, side - 2 * th)
        p.setPen(QPen(QColor("#1D1D2E"), th, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(r, 0, 360 * 16)
        t = self._shown
        col = lerp(self.c1, self.c2, t)
        if t > 0.8:
            col = lerp(col, RED, (t - 0.8) / 0.2)
        if t > 0.004:
            p.setPen(QPen(alpha(col, 50), th * 1.9, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(r, 90 * 16, int(-360 * 16 * t))
            p.setPen(QPen(col, th, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(r, 90 * 16, int(-360 * 16 * t))
        p.setPen(QColor(TEXT))
        f = QFont(self.font())
        f.setPixelSize(int(side * 0.22))
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(r.left(), r.top() + r.height() * 0.22, r.width(), r.height() * 0.36), Qt.AlignCenter, self.text)
        f.setPixelSize(max(10, int(side * 0.085)))
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor(MUTED))
        p.drawText(QRectF(r.left(), r.top() + r.height() * 0.56, r.width(), r.height() * 0.2), Qt.AlignCenter, self.sub)


class LineChart(QWidget):
    def __init__(self, vmax: Optional[float] = 100.0, unit: str = "%", maxlen: int = 90, show_legend: bool = True):
        super().__init__()
        self.vmax, self.unit, self.maxlen, self.show_legend = vmax, unit, maxlen, show_legend
        self.series: dict[str, tuple[QColor, deque]] = {}
        self.setMinimumHeight(120)

    def add_series(self, name: str, color: str):
        self.series[name] = (QColor(color), deque(maxlen=self.maxlen))

    def push(self, name: str, value: Optional[float]):
        self.series[name][1].append(value)

    def set_data(self, name: str, values: list):
        self.series[name][1].clear()
        self.series[name][1].extend(values)
        self.update()

    def clear(self):
        for _c, d in self.series.values():
            d.clear()
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        top_pad, bot_pad = (30 if self.show_legend else 8), 8
        plot_h = max(10, h - top_pad - bot_pad)
        vals = [v for _c, d in self.series.values() for v in d if v is not None]
        vmax = self.vmax or max(max(vals, default=1.0) * 1.25, 1.0)
        p.setPen(QPen(QColor("#1F1F33"), 1))
        for i in range(5):
            y = top_pad + plot_h * i / 4
            p.drawLine(QPointF(0, y), QPointF(w, y))
        p.setPen(QColor(DIM))
        f = QFont(self.font())
        f.setPixelSize(10)
        p.setFont(f)
        p.drawText(QRectF(w - 70, top_pad - 14, 66, 12), Qt.AlignRight, f"{vmax:.0f}{self.unit}")
        x = 4
        for name, (col, data) in self.series.items():
            if self.show_legend:
                p.setBrush(col)
                p.setPen(Qt.NoPen)
                p.drawEllipse(QPointF(x + 4, 14), 4, 4)
                p.setPen(QColor(MUTED))
                f2 = QFont(self.font())
                f2.setPixelSize(12)
                p.setFont(f2)
                p.drawText(QPointF(x + 14, 18), name)
                x += 24 + QFontMetrics(f2).horizontalAdvance(name)
            pts = list(data)
            if len(pts) < 2:
                continue
            step = w / max(1, self.maxlen - 1)
            x0 = w - step * (len(pts) - 1)
            path = QPainterPath()
            started = False
            for i, v in enumerate(pts):
                px = x0 + i * step
                if v is None:
                    p.setPen(QPen(QColor(RED), 2))
                    p.drawLine(QPointF(px, h - bot_pad), QPointF(px, h - bot_pad - 14))
                    started = False
                    continue
                py = top_pad + plot_h * (1 - min(1.0, v / vmax))
                if not started:
                    path.moveTo(px, py)
                    started = True
                else:
                    path.lineTo(px, py)
            if started and len(self.series) == 1:
                fill = QPainterPath(path)
                fill.lineTo(QPointF(w, h - bot_pad))
                fill.lineTo(QPointF(x0, h - bot_pad))
                g = QLinearGradient(0, top_pad, 0, h)
                g.setColorAt(0, alpha(col, 70))
                g.setColorAt(1, alpha(col, 0))
                p.setPen(Qt.NoPen)
                p.setBrush(g)
                p.drawPath(fill)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(alpha(col, 60), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(path)
            p.setPen(QPen(col, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(path)


class Sparkline(QWidget):
    """Kleine Verlaufslinie fuer Metrik-Karten."""

    def __init__(self, color: str = ACCENT, maxlen: int = 60, vmax: Optional[float] = 100.0):
        super().__init__()
        self.color, self.maxlen, self.vmax = QColor(color), maxlen, vmax
        self.data: deque = deque(maxlen=maxlen)
        self.setFixedHeight(46)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def push(self, v: float):
        self.data.append(v)
        self.update()

    def paintEvent(self, _e):
        if len(self.data) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        vmax = self.vmax or max(max(self.data), 1.0) * 1.2
        step = w / (self.maxlen - 1)
        x0 = w - step * (len(self.data) - 1)
        path = QPainterPath()
        for i, v in enumerate(self.data):
            x, y = x0 + i * step, h - 3 - (h - 8) * min(1.0, v / vmax)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        fill = QPainterPath(path)
        fill.lineTo(w, h)
        fill.lineTo(x0, h)
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, alpha(self.color, 80))
        g.setColorAt(1, alpha(self.color, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawPath(fill)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(self.color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)


class OrbBanner(Card):
    """Hero-Banner mit langsam wandernden Farb-Orbs (animiert nur, solange sichtbar)."""

    def __init__(self):
        super().__init__("hero")
        self.t0 = time.time()
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update)

    def showEvent(self, e):
        self.timer.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self.timer.stop()
        super().hideEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), self.radius, self.radius)
        p.setClipPath(path)
        t = time.time() - self.t0
        w, h = self.width(), self.height()
        for col, sp, ph in ((ACCENT, 0.35, 0.0), (CYAN, 0.27, 2.1), (PINK, 0.21, 4.2)):
            cx = w * (0.25 + 0.5 * (0.5 + 0.5 * math.sin(t * sp + ph)))
            cy = h * (0.35 + 0.3 * math.sin(t * sp * 1.3 + ph))
            g = QRadialGradient(cx, cy, h * 1.1)
            g.setColorAt(0, alpha(col, 46))
            g.setColorAt(1, alpha(col, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawEllipse(QPointF(cx, cy), h * 1.1, h * 1.1)


class StatTile(Card):
    def __init__(self, title: str, color: str = TEXT):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)
        self.title = label(title.upper(), "dim")
        self.value = label("–", "big")
        self.value.setStyleSheet(f"color:{color};")
        self.sub = label("", "muted")
        for w in (self.title, self.value, self.sub):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            lay.addWidget(w)

    def set(self, value: str, sub: str = ""):
        self.value.setText(value)
        self.sub.setText(sub)


class TweakRow(HoverFrame):
    """Eine Zeile: Wirkungs-Punkt, Name, EIN Satz, Tags, Schalter. Details im Tooltip."""
    toggled = Signal(str, bool)

    def __init__(self, tweak, admin_ok: bool):
        super().__init__(12)
        self.tweak = tweak
        self.locked = tweak.admin and not admin_ok
        self.unavailable = False
        self.setFixedHeight(68)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(12)
        col = QVBoxLayout()
        col.setSpacing(2)
        head = QHBoxLayout()
        head.setSpacing(8)
        if tweak.evidence:
            dot = QLabel()
            dot.setFixedSize(9, 9)
            dot.setStyleSheet(f"background:{EVIDENCE_COLORS.get(tweak.evidence, DIM)};border-radius:4px;")
            dot.setToolTip(EVIDENCE_TEXT.get(tweak.evidence, ""))
            head.addWidget(dot)
        name = QLabel(tweak.name)
        name.setStyleSheet("font-size:14px;font-weight:600;")
        name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        head.addWidget(name)
        if tweak.recommended:
            star = QLabel("★")
            star.setStyleSheet(f"color:{ACCENT2};")
            star.setToolTip("Wird von Auto Optimize gesetzt")
            head.addWidget(star)
        head.addStretch(1)
        col.addLayout(head)
        col.addWidget(ElidedLabel(tweak.description, "muted"))
        lay.addLayout(col, 1)
        tags = QHBoxLayout()
        tags.setSpacing(6)
        for t in tweak.tags:
            tags.addWidget(pill(t, TAG_COLORS.get(t, MUTED)))
        if tweak.risk != "niedrig":
            tags.addWidget(pill("RISIKO", YELLOW))
        if tweak.admin:
            tags.addWidget(pill("ADMIN", RED if self.locked else DIM))
        lay.addLayout(tags)
        self.toggle = Toggle()
        lay.addWidget(self.toggle)
        self.toggle.clicked.connect(lambda c: self.toggled.emit(self.tweak.id, bool(c)))
        tip = f"{tweak.description}\n\n{tweak.impact}"
        if tweak.evidence:
            tip += f"\n\n{EVIDENCE_TEXT.get(tweak.evidence, '')}"
        if tweak.restart and tweak.restart != "Nein":
            tip += f"\nWirksam: {tweak.restart}"
        if tweak.risk != "niedrig":
            tip += f"\nRisiko: {tweak.risk}"
        if self.locked:
            tip += "\n\nBraucht Administratorrechte."
            self.toggle.setEnabled(False)
        self.setToolTip(tip)

    def set_state(self, state: str, msg: str = ""):
        from engine import STATUS_ACTIVE, STATUS_UNKNOWN
        self.toggle.set_checked_silent(state == STATUS_ACTIVE)
        self.toggle.setEnabled(state != STATUS_UNKNOWN and not self.locked)
        self.unavailable = state == STATUS_UNKNOWN
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.unavailable:
            p = QPainter(self)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(10, 10, 16, 120))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 12, 12)


def make_scroll(widget: QWidget) -> QScrollArea:
    """Ganze Seite scrollt als Einheit; ein Mausrad-Schritt = etwa eine Zeile (normales Windows-Gefuehl)."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    area.setWidget(widget)
    area.verticalScrollBar().setSingleStep(34)
    return area


def apply_dark_titlebar(win: QWidget) -> None:
    """Dunkle Windows-Titelleiste (statt weiss), passend zum Design."""
    if os.name != "nt":
        return
    try:
        import ctypes
        hwnd = int(win.winId())
        dwm = ctypes.windll.dwmapi

        def put(attr: int, val: int):
            v = ctypes.c_int(val)
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))
        put(20, 1)            # DWMWA_USE_IMMERSIVE_DARK_MODE
        put(19, 1)            # aeltere Windows-10-Builds
        put(35, 0x00150D0D)   # Titelleistenfarbe #0D0D15 (Windows 11)
        put(36, 0x00F7EDED)   # Titeltext #EDEDF7
        put(34, 0x00150D0D)   # Rahmenfarbe
    except Exception:  # noqa: BLE001
        pass
