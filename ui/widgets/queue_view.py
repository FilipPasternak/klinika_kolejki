import math

from PyQt6.QtCore import QTimer, QPointF
from PyQt6.QtGui import QBrush, QColor, QPen, QPainter
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)

PATIENT_RADIUS = 16
QUEUE_SPACING = 42
SERVER_SPACING = 90
QUEUE_Y = 120
SERVER_Y = 20
SMOOTH_MIN_STEP = 0.12
SMOOTH_MAX_STEP = 0.45
SMOOTH_DISTANCE_SCALE = 60.0
EXIT_TARGET_Y = -220
EXIT_REMOVE_THRESHOLD_Y = -210
TIMER_VERTICAL_OFFSET = PATIENT_RADIUS + 6


class QueueView(QWidget):
    """Visual representation of patients waiting and being served."""

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(self.view.renderHints() | QPainter.RenderHint.Antialiasing)
        self.view.setMinimumSize(360, 240)
        self.view.setSceneRect(-40, -40, 600, 320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self.patient_items = {}
        self.server_slots = []
        self.server_labels = []

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(40)
        self._refresh_timer.timeout.connect(self._on_tick)

        self._ensure_server_slots(self.engine.params.servers_c)
        self.sync_once()

    def start(self):
        if not self._refresh_timer.isActive():
            self._refresh_timer.start()

    def stop(self):
        if self._refresh_timer.isActive():
            self._refresh_timer.stop()
        self.sync_once()

    def reset_view(self):
        for pid in list(self.patient_items):
            self._remove_patient(pid)
        self.sync_once()

    def sync_once(self):
        snapshot = self.engine.get_snapshot()
        self._update_scene(snapshot, immediate=True)

    def _on_tick(self):
        snapshot = self.engine.get_snapshot()
        self._update_scene(snapshot)

    def _update_scene(self, snapshot, immediate: bool = False):
        self._ensure_server_slots(len(snapshot.in_service))
        active_patients = set()

        max_x = 0

        # Queue positions
        for idx, pid in enumerate(snapshot.queue):
            pos = QPointF(idx * QUEUE_SPACING, QUEUE_Y)
            self._set_patient_target(pid, pos, immediate)
            self._set_patient_timer(pid, None)
            active_patients.add(pid)
            max_x = max(max_x, pos.x())

        # Server positions
        for srv_idx, srv_info in snapshot.in_service.items():
            pid = srv_info.get("patient_id")
            if pid is None:
                continue
            pos = QPointF(srv_idx * SERVER_SPACING, SERVER_Y)
            self._set_patient_target(pid, pos, immediate)
            self._set_patient_timer(pid, srv_info)
            active_patients.add(pid)
            max_x = max(max_x, pos.x())

        # Remove patients no longer present
        for pid in list(self.patient_items.keys()):
            if pid not in active_patients:
                if immediate:
                    self._remove_patient(pid)
                else:
                    self._mark_patient_exiting(pid)

        if not immediate:
            self._animate_patients()

        width = max(420, max_x + 120)
        self.scene.setSceneRect(-80, -80, width, 340)

    def _ensure_server_slots(self, count: int):
        while len(self.server_slots) < count:
            idx = len(self.server_slots)
            rect = QGraphicsRectItem(-25, -15, 50, 30)
            rect.setPen(QPen(QColor("#2d7dd2"), 2))
            rect.setBrush(QBrush(QColor(220, 235, 255)))
            self.scene.addItem(rect)

            label = QGraphicsSimpleTextItem(f"Stan. {idx + 1}")
            label.setBrush(QBrush(QColor("#1b4f72")))
            self.scene.addItem(label)

            self.server_slots.append(rect)
            self.server_labels.append(label)

        while len(self.server_slots) > count:
            rect = self.server_slots.pop()
            label = self.server_labels.pop()
            self.scene.removeItem(rect)
            self.scene.removeItem(label)

        for idx, rect in enumerate(self.server_slots):
            x = idx * SERVER_SPACING
            rect.setPos(x - rect.rect().width() / 2, SERVER_Y - rect.rect().height() / 2)
            label = self.server_labels[idx]
            label.setPos(x - label.boundingRect().width() / 2, SERVER_Y - 30)

    def _set_patient_target(self, pid: int, pos: QPointF, immediate: bool):
        created = False
        if pid not in self.patient_items:
            item = QGraphicsEllipseItem(-PATIENT_RADIUS, -PATIENT_RADIUS, PATIENT_RADIUS * 2, PATIENT_RADIUS * 2)
            item.setBrush(QBrush(QColor("#ef476f")))
            item.setPen(QPen(QColor("#9b1d2a"), 1.5))
            item.setZValue(1)
            self.scene.addItem(item)

            label = QGraphicsSimpleTextItem(str(pid))
            label.setBrush(QBrush(QColor("white")))
            label.setZValue(2)
            self.scene.addItem(label)

            timer_label = QGraphicsSimpleTextItem("")
            timer_label.setBrush(QBrush(QColor("#1b4f72")))
            timer_label.setVisible(False)
            timer_label.setZValue(2)
            self.scene.addItem(timer_label)

            self.patient_items[pid] = {
                "item": item,
                "label": label,
                "timer": timer_label,
                "target": QPointF(pos),
                "current": QPointF(pos),
                "exiting": False,
            }
            created = True

        data = self.patient_items[pid]
        data["target"] = QPointF(pos)
        data["exiting"] = False
        if immediate or created:
            self._move_patient_immediately(pid)

    def _move_patient_immediately(self, pid: int):
        data = self.patient_items[pid]
        target = data["target"]
        self._apply_patient_position(pid, target)

    def _animate_patients(self):
        for pid, data in self.patient_items.items():
            item = data["item"]
            target = data["target"]

            current = QPointF(item.pos().x() + PATIENT_RADIUS, item.pos().y() + PATIENT_RADIUS)
            delta = target - current
            if abs(delta.x()) < 0.5 and abs(delta.y()) < 0.5:
                self._move_patient_immediately(pid)
                continue

            distance = math.hypot(delta.x(), delta.y())
            step = 1.0 - math.exp(-distance / SMOOTH_DISTANCE_SCALE)
            step = max(SMOOTH_MIN_STEP, min(step, SMOOTH_MAX_STEP))
            new_pos = current + delta * step
            self._apply_patient_position(pid, new_pos)

            if data.get("exiting") and data["current"].y() <= EXIT_REMOVE_THRESHOLD_Y:
                self._remove_patient(pid)

    def _remove_patient(self, pid: int):
        data = self.patient_items.pop(pid, None)
        if not data:
            return
        self.scene.removeItem(data["item"])
        self.scene.removeItem(data["label"])
        timer_label = data.get("timer")
        if timer_label:
            self.scene.removeItem(timer_label)

    def _apply_patient_position(self, pid: int, center: QPointF):
        data = self.patient_items.get(pid)
        if not data:
            return

        data["current"] = QPointF(center)
        item = data["item"]
        label = data["label"]
        timer_label = data.get("timer")

        item.setPos(center.x() - PATIENT_RADIUS, center.y() - PATIENT_RADIUS)
        label.setPos(center.x() - label.boundingRect().width() / 2, center.y() - label.boundingRect().height() / 2)

        if timer_label:
            timer_label.setPos(
                center.x() - timer_label.boundingRect().width() / 2,
                center.y() + TIMER_VERTICAL_OFFSET,
            )

    def _set_patient_timer(self, pid: int, srv_info: dict | None):
        data = self.patient_items.get(pid)
        if not data:
            return

        timer_label = data.get("timer")
        if not timer_label:
            return

        if not srv_info or srv_info.get("patient_id") is None:
            timer_label.setText("")
            timer_label.setVisible(False)
        else:
            elapsed = srv_info.get("elapsed", 0.0)
            total = srv_info.get("total", 0.0)
            elapsed_txt = self._format_duration(elapsed)
            text = elapsed_txt
            if total > 0.0:
                total_txt = self._format_duration(total)
                text = f"{elapsed_txt} / {total_txt}"
            timer_label.setText(text)
            timer_label.setVisible(True)

        # Refresh placement after text update
        current = data.get("current", data.get("target", QPointF()))
        self._apply_patient_position(pid, current)

    @staticmethod
    def _format_duration(hours_value: float) -> str:
        total_seconds = max(hours_value, 0.0) * 3600.0
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _mark_patient_exiting(self, pid: int):
        data = self.patient_items.get(pid)
        if not data or data.get("exiting"):
            return

        current = data.get("current")
        if current is None:
            item = data["item"]
            current = QPointF(item.pos().x() + PATIENT_RADIUS, item.pos().y() + PATIENT_RADIUS)

        data["target"] = QPointF(current.x(), EXIT_TARGET_Y)
        data["exiting"] = True

