import sys
import threading
import time
from concurrent import futures

import grpc

import artwork_pb2
import artwork_pb2_grpc


DETECT = len(sys.argv) > 1 and sys.argv[1] == "detect"


class LockManager(artwork_pb2_grpc.LockServiceServicer):
    def __init__(self):
        self.mutex = threading.Lock()
        self.locks = {"draft": None, "submission": None}
        # holder_id -> resource_id the holder is currently waiting on
        self.wait_for = {}
        self.conditions = {
            "draft": threading.Condition(),
            "submission": threading.Condition(),
        }

    def _would_cycle(self, holder: int, resource: str) -> bool:
        """Return True if making `holder` wait on `resource` would form a cycle."""
        visited = set()
        current_resource = resource

        while True:
            owner = self.locks.get(current_resource)
            if owner is None:
                return False
            if owner == holder:
                return True
            if owner in visited:
                return False

            visited.add(owner)
            current_resource = self.wait_for.get(owner)
            if current_resource is None:
                return False

    def AcquireLock(self, request, context):
        resource = request.resource_id
        holder = request.holder_id

        if resource not in self.locks:
            return artwork_pb2.LockReply(granted=False, message=f"unknown-resource:{resource}")

        cond = self.conditions[resource]

        with cond:
            with self.mutex:
                owner = self.locks.get(resource)
                if owner is None:
                    self.locks[resource] = holder
                    self.wait_for.pop(holder, None)
                    return artwork_pb2.LockReply(granted=True, message="granted")

                if DETECT and self._would_cycle(holder, resource):
                    print(
                        f"[LockManager] DEADLOCK DETECTED: Node-{holder} -> '{resource}' "
                        f"(held by Node-{owner}) would close a cycle. Aborting Node-{holder}."
                    )
                    return artwork_pb2.LockReply(granted=False, message="deadlock-abort")

                self.wait_for[holder] = resource
                print(
                    f"[LockManager] Node-{holder} WAITING for '{resource}' "
                    f"(held by Node-{owner})"
                )

            while True:
                with self.mutex:
                    owner = self.locks.get(resource)
                    if owner is None:
                        self.locks[resource] = holder
                        self.wait_for.pop(holder, None)
                        return artwork_pb2.LockReply(granted=True, message="granted-after-wait")

                cond.wait(timeout=1)

    def ReleaseLock(self, request, context):
        resource = request.resource_id
        holder = request.holder_id

        if resource not in self.locks:
            return artwork_pb2.LockReply(granted=False, message=f"unknown-resource:{resource}")

        cond = self.conditions[resource]
        with cond:
            with self.mutex:
                if self.locks.get(resource) == holder:
                    self.locks[resource] = None
                    cond.notify_all()
                    return artwork_pb2.LockReply(granted=True, message="released")

        return artwork_pb2.LockReply(granted=False, message="not-holder")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    artwork_pb2_grpc.add_LockServiceServicer_to_server(LockManager(), server)
    server.add_insecure_port("localhost:60100")
    server.start()
    print(f"LockManager started on localhost:60100 (deadlock detection = {DETECT})")

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    serve()
