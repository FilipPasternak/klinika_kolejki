from PyQt6.QtCore import QTimer, QPointF
from PyQt6.QtGui import QBrush, QColor, QPen
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
ANIMATION_SPEED = 0.25


class QueueView(QWidget):
    """Visual representation of patients waiting and being served."""

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(self.view.renderHints())
        self.view.setMinimumSize(360, 240)
        self.view.setSceneRect(-40, -40, 600, 320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self.patient_items = {}
        self.server_slots = []
        self.server_labels = []

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(80)
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
            active_patients.add(pid)
            max_x = max(max_x, pos.x())

        # Server positions
        for srv_idx, srv_info in snapshot.in_service.items():
            pid = srv_info.get("patient_id")
            if pid is None:
                continue
            pos = QPointF(srv_idx * SERVER_SPACING, SERVER_Y)
            self._set_patient_target(pid, pos, immediate)
            active_patients.add(pid)
            max_x = max(max_x, pos.x())

        # Remove patients no longer present
        for pid in list(self.patient_items.keys()):
            if pid not in active_patients:
                self._remove_patient(pid)

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

            label = QGraphicsSimpleTextItem(f"S{idx + 1}")
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
        if pid not in self.patient_items:
            item = QGraphicsEllipseItem(-PATIENT_RADIUS, -PATIENT_RADIUS, PATIENT_RADIUS * 2, PATIENT_RADIUS * 2)
            item.setBrush(QBrush(QColor("#ef476f")))
            item.setPen(QPen(QColor("#9b1d2a"), 1.5))
            self.scene.addItem(item)

            label = QGraphicsSimpleTextItem(str(pid))
            label.setBrush(QBrush(QColor("white")))
            self.scene.addItem(label)

            self.patient_items[pid] = {"item": item, "label": label, "target": QPointF(pos)}
            item.setPos(pos.x() - PATIENT_RADIUS, pos.y() - PATIENT_RADIUS)
            label.setPos(pos.x() - label.boundingRect().width() / 2, pos.y() - 10)
            return

        self.patient_items[pid]["target"] = QPointF(pos)
        if immediate:
            self._move_patient_immediately(pid)

    def _move_patient_immediately(self, pid: int):
        data = self.patient_items[pid]
        item = data["item"]
        label = data["label"]
        target = data["target"]
        item.setPos(target.x() - PATIENT_RADIUS, target.y() - PATIENT_RADIUS)
        label.setPos(target.x() - label.boundingRect().width() / 2, target.y() - 10)

    def _animate_patients(self):
        for pid, data in self.patient_items.items():
            item = data["item"]
            label = data["label"]
            target = data["target"]

            current = QPointF(item.pos().x() + PATIENT_RADIUS, item.pos().y() + PATIENT_RADIUS)
            delta = target - current
            if abs(delta.x()) < 0.5 and abs(delta.y()) < 0.5:
                self._move_patient_immediately(pid)
                continue

            new_pos = current + delta * ANIMATION_SPEED
            item.setPos(new_pos.x() - PATIENT_RADIUS, new_pos.y() - PATIENT_RADIUS)
            label.setPos(new_pos.x() - label.boundingRect().width() / 2, new_pos.y() - 10)

    def _remove_patient(self, pid: int):
        data = self.patient_items.pop(pid, None)
        if not data:
            return
        self.scene.removeItem(data["item"])
        self.scene.removeItem(data["label"])

