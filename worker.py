import sys
import time

import grpc

import artwork_pb2
import artwork_pb2_grpc


def acquire(stub, resource: str, holder: int, ts: int) -> bool:
    reply = stub.AcquireLock(
        artwork_pb2.LockRequest(resource_id=resource, holder_id=holder, timestamp=ts)
    )
    print(f"Node-{holder}: '{resource}' -> granted={reply.granted} ({reply.message})")
    return reply.granted


def release(stub, resource: str, holder: int) -> None:
    stub.ReleaseLock(
        artwork_pb2.LockRequest(resource_id=resource, holder_id=holder, timestamp=holder)
    )


def run(node_id: int, first: str, second: str):
    ts = node_id

    with grpc.insecure_channel("localhost:60100") as channel:
        stub = artwork_pb2_grpc.LockServiceStub(channel)
        held = []

        if acquire(stub, first, node_id, ts):
            held.append(first)
            # Widen race window so both workers likely hold one lock each.
            time.sleep(1.5)

            if acquire(stub, second, node_id, ts):
                held.append(second)
            else:
                print(f"Node-{node_id}: ABORTED -- releasing held locks and retrying")
                for resource in held:
                    release(stub, resource, node_id)
                held = []

                time.sleep(1)
                if acquire(stub, second, node_id, ts):
                    held.append(second)
                if acquire(stub, first, node_id, ts):
                    held.append(first)

        time.sleep(0.5)
        for resource in held:
            release(stub, resource, node_id)

        print(f"Node-{node_id}: DONE")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python worker.py <node_id> <autosave|submission>")
        raise SystemExit(1)

    node_id = int(sys.argv[1])
    role = sys.argv[2].strip().lower()

    if role == "autosave":
        run(node_id, "draft", "submission")
    elif role in {"submission", "finalsubmit", "final_submission"}:
        run(node_id, "submission", "draft")
    else:
        print("Role must be one of: autosave, submission")
        raise SystemExit(1)
