"""gRPC server for the distributed expense workflow demo."""

from __future__ import annotations

import logging
import threading
from concurrent import futures
from typing import Dict

import grpc

import service_pb2
import service_pb2_grpc


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("grpc_server")


class TransactionService(service_pb2_grpc.TransactionServiceServicer):
    """Implements a small transactional workflow using in-memory state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._resources: Dict[str, Dict[str, int | str]] = {
            "expense_1001": {"available": 25, "reserved": 0, "status": "open"},
            "expense_1002": {"available": 50, "reserved": 0, "status": "open"},
        }
        self._records: Dict[str, Dict[str, int | str]] = {
            "record_a": {"value": 100, "status": "created", "reservation_id": ""},
            "record_b": {"value": 250, "status": "created", "reservation_id": ""},
        }

    def GetStatus(self, request, context):
        LOGGER.info("Status requested for service_name=%s", request.service_name)
        with self._lock:
            active_records = len(self._records)

        return service_pb2.StatusResponse(
            healthy=True,
            message=f"{request.service_name or 'TransactionService'} is running",
            active_records=active_records,
        )

    def ReserveResource(self, request, context):
        LOGGER.info(
            "Reserve requested for resource_id=%s quantity=%s requester=%s",
            request.resource_id,
            request.quantity,
            request.requester,
        )

        if request.quantity <= 0:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("quantity must be greater than zero")
            return service_pb2.ReserveResponse(success=False, message="Invalid quantity")

        with self._lock:
            resource = self._resources.get(request.resource_id)
            if resource is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("resource not found")
                return service_pb2.ReserveResponse(success=False, message="Resource not found")

            available = int(resource["available"])
            if available < request.quantity:
                return service_pb2.ReserveResponse(
                    success=False,
                    reservation_id="",
                    message=f"Insufficient availability. Requested {request.quantity}, available {available}",
                    reserved_quantity=int(resource["reserved"]),
                )

            resource["available"] = available - request.quantity
            resource["reserved"] = int(resource["reserved"]) + request.quantity
            resource["status"] = "reserved"

        reservation_id = f"res-{request.resource_id}-{request.quantity}"
        return service_pb2.ReserveResponse(
            success=True,
            reservation_id=reservation_id,
            message="Reservation completed successfully",
            reserved_quantity=request.quantity,
        )

    def UpdateRecord(self, request, context):
        LOGGER.info(
            "Update requested for record_id=%s reservation_id=%s new_status=%s adjustment=%s",
            request.record_id,
            request.reservation_id,
            request.new_status,
            request.adjustment,
        )

        with self._lock:
            record = self._records.get(request.record_id)
            if record is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("record not found")
                return service_pb2.UpdateResponse(success=False, message="Record not found")

            if request.reservation_id and request.reservation_id != record["reservation_id"]:
                record["reservation_id"] = request.reservation_id

            current_value = int(record["value"]) + request.adjustment
            record["value"] = current_value
            record["status"] = request.new_status or record["status"]

        return service_pb2.UpdateResponse(
            success=True,
            message="Record updated successfully",
            updated_record_id=request.record_id,
            current_value=current_value,
        )


def serve() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service_pb2_grpc.add_TransactionServiceServicer_to_server(TransactionService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    LOGGER.info("gRPC server started on port 50051")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down gRPC server")
        server.stop(grace=5)


if __name__ == "__main__":
    serve()