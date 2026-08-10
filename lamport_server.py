"""Lamport-aware gRPC server for the distributed expense workflow demo."""

from __future__ import annotations

import logging
import threading
from concurrent import futures
from typing import Dict, Tuple

import grpc

from lamport_clock import LamportClock
import service_pb2
import service_pb2_grpc


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("lamport_server")


class LamportTransactionService(service_pb2_grpc.TransactionServiceServicer):
    """Implements the transactional workflow while maintaining Lamport order."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._clock = LamportClock()
        self._resources: Dict[str, Dict[str, int | str]] = {
            "expense_1001": {"available": 25, "reserved": 0, "status": "open"},
            "expense_1002": {"available": 50, "reserved": 0, "status": "open"},
        }
        self._records: Dict[str, Dict[str, int | str]] = {
            "record_a": {"value": 100, "status": "created", "reservation_id": ""},
            "record_b": {"value": 250, "status": "created", "reservation_id": ""},
        }

    def _apply_lamport_receive(self, incoming_timestamp: int, event_name: str) -> int:
        with self._lock:
            local_time = self._clock.receive_event(incoming_timestamp)
            LOGGER.info(
                "%s received | incoming=%s | local_clock=%s",
                event_name,
                incoming_timestamp,
                local_time,
            )
            return local_time

    def _build_timestamped_response(self, response, local_time: int):
        response.lamport_timestamp = self._clock.increment()
        LOGGER.info("Response ready | local_clock=%s | response_timestamp=%s", local_time, response.lamport_timestamp)
        return response

    def GetStatus(self, request, context):
        local_time = self._apply_lamport_receive(request.lamport_timestamp, "GetStatus")
        with self._lock:
            active_records = len(self._records)

        response = service_pb2.StatusResponse(
            healthy=True,
            message=f"{request.service_name or 'TransactionService'} is running",
            active_records=active_records,
        )
        return self._build_timestamped_response(response, local_time)

    def ReserveResource(self, request, context):
        local_time = self._apply_lamport_receive(request.lamport_timestamp, "ReserveResource")

        if request.quantity <= 0:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("quantity must be greater than zero")
            response = service_pb2.ReserveResponse(success=False, message="Invalid quantity")
            return self._build_timestamped_response(response, local_time)

        with self._lock:
            resource = self._resources.get(request.resource_id)
            if resource is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("resource not found")
                response = service_pb2.ReserveResponse(success=False, message="Resource not found")
                return self._build_timestamped_response(response, local_time)

            available = int(resource["available"])
            if available < request.quantity:
                response = service_pb2.ReserveResponse(
                    success=False,
                    reservation_id="",
                    message=f"Insufficient availability. Requested {request.quantity}, available {available}",
                    reserved_quantity=int(resource["reserved"]),
                )
                return self._build_timestamped_response(response, local_time)

            resource["available"] = available - request.quantity
            resource["reserved"] = int(resource["reserved"]) + request.quantity
            resource["status"] = "reserved"

        reservation_id = f"res-{request.resource_id}-{request.quantity}"
        response = service_pb2.ReserveResponse(
            success=True,
            reservation_id=reservation_id,
            message="Reservation completed successfully",
            reserved_quantity=request.quantity,
        )
        return self._build_timestamped_response(response, local_time)

    def UpdateRecord(self, request, context):
        local_time = self._apply_lamport_receive(request.lamport_timestamp, "UpdateRecord")

        with self._lock:
            record = self._records.get(request.record_id)
            if record is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("record not found")
                response = service_pb2.UpdateResponse(success=False, message="Record not found")
                return self._build_timestamped_response(response, local_time)

            if request.reservation_id and request.reservation_id != record["reservation_id"]:
                record["reservation_id"] = request.reservation_id

            current_value = int(record["value"]) + request.adjustment
            record["value"] = current_value
            record["status"] = request.new_status or record["status"]

        response = service_pb2.UpdateResponse(
            success=True,
            message="Record updated successfully",
            updated_record_id=request.record_id,
            current_value=current_value,
        )
        return self._build_timestamped_response(response, local_time)


def serve() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service_pb2_grpc.add_TransactionServiceServicer_to_server(LamportTransactionService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    LOGGER.info("Lamport-aware gRPC server started on port 50051")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down Lamport-aware gRPC server")
        server.stop(grace=5)


if __name__ == "__main__":
    serve()