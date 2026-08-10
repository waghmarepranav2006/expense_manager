import argparse
import concurrent.futures
import logging
import threading
import time
from typing import Dict, List

import grpc

import artwork_pb2
import artwork_pb2_grpc


PEERS: Dict[int, str] = {1: "localhost:60051", 2: "localhost:60052", 3: "localhost:60053"}


class NodeServicer(artwork_pb2_grpc.MutexServiceServicer):
    def __init__(self, node: "Node"):
        self.node = node

    def RequestAccess(self, request, context):
        # Update local Lamport clock with incoming timestamp
        with self.node.lock:
            self.node.clock = max(self.node.clock, request.timestamp) + 1
            logging.info("[%d] Received RequestAccess from %d (ts=%d); local clock=%d",
                         self.node.id, request.node_id, request.timestamp, self.node.clock)

            # Decide whether to defer the reply
            # Defer if this node is HELD, or if this node WANTS and has higher priority
            defer = False
            if self.node.state == "HELD":
                defer = True
            elif self.node.state == "WANTED":
                # If our (request_ts, id) < (incoming_ts, incoming_id) then our request has priority
                if (self.node.request_timestamp, self.node.id) < (request.timestamp, request.node_id):
                    defer = True

            if defer:
                logging.info("[%d] DEFERRING reply to %d", self.node.id, request.node_id)
                event = threading.Event()
                self.node.deferred.append(event)
                # wait outside the lock so release_cs can set the event
        if defer:
            event.wait()
            with self.node.lock:
                self.node.clock += 1
                send_ts = self.node.clock
                logging.info("[%d] Unblocked and GRANTING to %d (send_ts=%d)", self.node.id, request.node_id, send_ts)
                return artwork_pb2.AccessReply(node_id=self.node.id, timestamp=send_ts)

        # Not deferred: grant immediately
        with self.node.lock:
            self.node.clock += 1
            send_ts = self.node.clock
            logging.info("[%d] GRANTING to %d immediately (send_ts=%d)", self.node.id, request.node_id, send_ts)
            return artwork_pb2.AccessReply(node_id=self.node.id, timestamp=send_ts)


class Node:
    def __init__(self, node_id: int):
        self.id = node_id
        self.peers = {k: v for k, v in PEERS.items() if k != self.id}

        self.state = "RELEASED"  # RELEASED, WANTED, HELD
        self.clock = 0
        self.request_timestamp = 0
        self.deferred: List[threading.Event] = []
        self.lock = threading.Lock()

        self.server = None

    def start_server(self):
        server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
        artwork_pb2_grpc.add_MutexServiceServicer_to_server(NodeServicer(self), server)
        bind_addr = PEERS[self.id]
        server.add_insecure_port(bind_addr)
        server.start()
        self.server = server
        logging.info("[%d] Server started at %s", self.id, bind_addr)

    def stop_server(self):
        if self.server:
            logging.info("[%d] Stopping server", self.id)
            self.server.stop(0)

    def call_with_retry(self, peer_addr: str, request: artwork_pb2.AccessRequest, timeout=3):
        # Retry until success; useful for peers starting up slightly later
        last_exc = None
        while True:
            try:
                with grpc.insecure_channel(peer_addr) as channel:
                    stub = artwork_pb2_grpc.MutexServiceStub(channel)
                    # short timeout to avoid long blocking
                    reply = stub.RequestAccess(request, timeout=timeout)
                    return reply
            except Exception as e:
                last_exc = e
                logging.debug("[%d] Retry contacting %s: %s", self.id, peer_addr, e)
                time.sleep(1)

    def request_cs(self):
        # Begin requesting critical section
        with self.lock:
            self.clock += 1
            self.state = "WANTED"
            self.request_timestamp = self.clock
            logging.info("[%d] WANTS CS (ts=%d)", self.id, self.request_timestamp)

        # Build request object
        req = artwork_pb2.AccessRequest(node_id=self.id, timestamp=self.request_timestamp)

        # Send RequestAccess to all peers concurrently
        replies = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.peers) or 1) as ex:
            futures = {ex.submit(self.call_with_retry, addr, req): pid for pid, addr in self.peers.items()}
            for fut in concurrent.futures.as_completed(futures):
                peer_id = futures[fut]
                try:
                    reply = fut.result()
                    replies.append(reply)
                    with self.lock:
                        self.clock = max(self.clock, reply.timestamp) + 1
                    logging.info("[%d] Received reply from %d (ts=%d); clock=%d", self.id, reply.node_id, reply.timestamp, self.clock)
                except Exception as e:
                    logging.warning("[%d] Failed to get reply from %d: %s", self.id, peer_id, e)

        # Once all replies received, enter critical section
        with self.lock:
            self.state = "HELD"
            self.clock += 1
            logging.info("[%d] ENTERED critical section (clock=%d)", self.id, self.clock)

        # Simulate critical section
        time.sleep(0.5)

        # Release
        self.release_cs()

    def release_cs(self):
        with self.lock:
            self.state = "RELEASED"
            logging.info("[%d] RELEASING critical section; waking %d deferred peers", self.id, len(self.deferred))
            deferred_events = list(self.deferred)
            self.deferred.clear()

        for ev in deferred_events:
            try:
                ev.set()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Ricart-Agrawala node")
    parser.add_argument("node_id", type=int, choices=[1, 2, 3], help="Node ID (1/2/3)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    node = Node(args.node_id)
    node.start_server()

    try:
        # Give time for all nodes to start
        logging.info("[%d] Waiting 6s for peers to start...", node.id)
        time.sleep(6)

        # Request critical section once
        node.request_cs()

        # Keep server alive briefly to ensure replies are flushed
        time.sleep(1)
    finally:
        node.stop_server()


if __name__ == "__main__":
    main()
