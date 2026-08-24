"""Least-connections load balancer for the worker gRPC backends."""

from __future__ import annotations

import threading
import time

import grpc

import worker_pb2
import worker_pb2_grpc


BACKENDS = ["localhost:60201", "localhost:60202", "localhost:60203"]
NUM_REQUESTS = 9
active = [0] * len(BACKENDS)
lock = threading.Lock()


def pick_least_connections() -> int:
    """Reserve the least-loaded backend before dispatching its request."""
    with lock:
        index = active.index(min(active))
        active[index] += 1
        print(
            f"[LB] Routing -> {BACKENDS[index]} "
            f"(active connections now: {active})",
            flush=True,
        )
        return index


def release(index: int) -> None:
    with lock:
        active[index] -= 1
        print(
            f"[LB] Released {BACKENDS[index]} "
            f"(active connections now: {active})",
            flush=True,
        )


def handle_request(request_id: int) -> None:
    index = pick_least_connections()
    try:
        with grpc.insecure_channel(BACKENDS[index]) as channel:
            stub = worker_pb2_grpc.WorkerServiceStub(channel)
            reply = stub.HandleRequest(
                worker_pb2.WorkRequest(request_id=request_id)
            )
            print(
                f"[LB] Request {request_id} -> handled by {reply.handled_by}",
                flush=True,
            )
    finally:
        release(index)


def main() -> None:
    print(f"[LB] Load Balancer starting. Backends: {BACKENDS}")
    threads = []
    for request_id in range(1, NUM_REQUESTS + 1):
        thread = threading.Thread(target=handle_request, args=(request_id,))
        threads.append(thread)
        thread.start()
        time.sleep(0.15)

    for thread in threads:
        thread.join()

    print("\n[LB] All requests processed.")
    print(f"[LB] Final active connection counts (should all be 0): {active}")


if __name__ == "__main__":
    main()