"""Lamport logical clock utilities for distributed event ordering."""

from __future__ import annotations


class LamportClock:
    def __init__(self) -> None:
        self.time = 0

    def increment(self) -> int:
        self.time += 1
        return self.time

    def send_event(self) -> int:
        self.time += 1
        return self.time

    def receive_event(self, received_time: int) -> int:
        self.time = max(self.time, received_time) + 1
        return self.time