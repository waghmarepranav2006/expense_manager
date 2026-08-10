"""gRPC client for the distributed expense workflow demo."""

from __future__ import annotations

import logging

import grpc

import service_pb2
import service_pb2_grpc


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("grpc_client")


def call_rpc(method_name, rpc_call):
    try:
        LOGGER.info("Sending %s request", method_name)
        response = rpc_call()
        LOGGER.info("Received %s response: %s", method_name, response)
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
    with grpc.insecure_channel("localhost:50051") as channel:
        grpc.channel_ready_future(channel).result(timeout=10)
        stub = service_pb2_grpc.TransactionServiceStub(channel)

        status_response = call_rpc(
            "GetStatus",
            lambda: stub.GetStatus(service_pb2.StatusRequest(service_name="ExpenseManagerClient")),
        )

        reserve_response = call_rpc(
            "ReserveResource",
            lambda: stub.ReserveResource(
                service_pb2.ReserveRequest(
                    resource_id="expense_1001",
                    quantity=5,
                    requester="client-service",
                )
            ),
        )

        reservation_id = reserve_response.reservation_id if reserve_response else ""
        update_response = call_rpc(
            "UpdateRecord",
            lambda: stub.UpdateRecord(
                service_pb2.UpdateRequest(
                    record_id="record_a",
                    reservation_id=reservation_id,
                    new_status="processed",
                    adjustment=15,
                )
            ),
        )

        LOGGER.info("Workflow summary -> status=%s reserve=%s update=%s", status_response, reserve_response, update_response)


if __name__ == "__main__":
    main()