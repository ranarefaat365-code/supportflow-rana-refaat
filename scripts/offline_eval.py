"""Strictly offline structural evaluation: socket-level deny before third-party imports."""

import os
import socket
import sys

os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ.pop("CONFIDENT_API_KEY", None)
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""


def deny(*args, **kwargs):
    raise OSError("Outbound networking is disabled for this offline evaluation process")


socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
socket.getaddrinfo = deny

if __name__ == "__main__":
    from evals.run import run_suite

    r = run_suite(sys.argv[1] if len(sys.argv) > 1 else "artifacts")
    print({k: r[k] for k in ["total", "passed", "failed", "semantic_judge_run"]})
    raise SystemExit(0 if r["failed"] == 0 else 1)
