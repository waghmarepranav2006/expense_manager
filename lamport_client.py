"""Lamport-aware gRPC client for the distributed expense workflow demo."""

from __future__ import annotations

import logging

import grpc

from lamport_clock import LamportClock
import service_pb2
import service_pb2_grpc


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("lamport_client")


def call_rpc(method_name, request_factory, rpc_call, clock: LamportClock):
    try:
        local_timestamp = clock.send_event()
        request = request_factory(local_timestamp)
        LOGGER.info("Sending Request (Lamport Clock : %s) -> %s", local_timestamp, method_name)
        response = rpc_call(request)
        clock.receive_event(response.lamport_timestamp)
        LOGGER.info("Received Response (Lamport Clock : %s) -> %s", response.lamport_timestamp, response)
        return response
    except grpc.RpcError as exc:
        LOGGER.error(
            "%s failed with code=%s details=%s",
            method_name,
            exc.code(),
            exc.details(),
        )
        return None


def main() -> None:
    clock = LamportClock()

    with grpc.insecure_channel("localhost:50051") as channel:
        grpc.channel_ready_future(channel).result(timeout=10)
        stub = service_pb2_grpc.TransactionServiceStub(channel)

        status_response = call_rpc(
            "GetStatus",
            lambda ts: service_pb2.StatusRequest(service_name="ExpenseManagerClient", lamport_timestamp=ts),
            stub.GetStatus,
            clock,
        )

        reserve_response = call_rpc(
            "ReserveResource",
            lambda ts: service_pb2.ReserveRequest(
                resource_id="expense_1001",
                quantity=5,
                requester="client-service",
                lamport_timestamp=ts,
            ),
            stub.ReserveResource,
            clock,
        )

        reservation_id = reserve_response.reservation_id if reserve_response else ""
        update_response = call_rpc(
            "UpdateRecord",
            lambda ts: service_pb2.UpdateRequest(
                record_id="record_a",
                reservation_id=reservation_id,
                new_status="processed",
                adjustment=15,
                lamport_timestamp=ts,
            ),
            stub.UpdateRecord,
            clock,
        )

        LOGGER.info(
            "Workflow summary -> status=%s reserve=%s update=%s final_client_clock=%s",
            status_response,
            reserve_response,
            update_response,
            clock.time,
        )


if __name__ == "__main__":
    main()