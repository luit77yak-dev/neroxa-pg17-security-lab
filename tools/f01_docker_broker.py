#!/usr/bin/env python3
"""F01 disposable-only Docker broker.

The native test process has no Docker group membership or access to the raw
Docker socket. A runner-owned broker accepts a limited Docker CLI protocol for
just one disposable Supabase project. No create, start, run, cp, mounts, or
arbitrary container exec is accepted. No production credentials are used.
"""
import argparse
import base64
import json
import os
import re
import socket
import socketserver
import struct
import subprocess
import sys

LIMIT = 16 * 1024 * 1024
PS_ARGS = ("ps", "--format", "{{json .}}")
SQL_ARGS = ("psql", "-X", "-q", "-A", "-t", "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1")
IMAGE_FORMAT = "{{.Image}}"
DOCKER = "/usr/bin/docker"


def command_for(argv, project):
    """Reject every Docker command except read-only scoped queries and psql on DB."""
    if not re.fullmatch(r"neroxa-02a3-[0-9]+-buyer", project):
        raise ValueError("Invalid disposable project identity")
    db = "supabase_db_" + project
    if tuple(argv) == PS_ARGS:
        return list(argv), "ps"
    if tuple(argv) == ("inspect", db):
        return list(argv), "inspect"
    if len(argv) == 4 and argv[0] == "inspect" and argv[2:] == ["--format", IMAGE_FORMAT] and argv[1].startswith("supabase_") and argv[1].endswith("_" + project):
        return list(argv), "inspect-format"
    if tuple(argv) == ("exec", "-i", db, *SQL_ARGS):
        return list(argv), "psql"
    raise ValueError("Docker command not allowed")


def run_command(argv, project, body):
    cmd, kind = command_for(argv, project)
    if kind != "psql" and body:
        raise ValueError("Unexpected input to read-only Docker query")
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/home/runner", "DOCKER_HOST": "unix:///var/run/docker.sock"}
    p = subprocess.run([DOCKER] + cmd, input=body, capture_output=True, env=env, timeout=120, check=False)
    output = p.stdout
    if kind == "ps" and p.returncode == 0:
        good = []
        for line in output.splitlines():
            row = json.loads(line)
            if row.get("Names", "").endswith("_" + project):
                good.append(line)
        output = b"\n".join(good) + (b"\n" if good else b"")
    elif kind == "inspect" and p.returncode == 0:
        data = json.loads(output)
        if len(data) != 1 or data[0].get("Name", "").lstrip("/") != "supabase_db_" + project:
            raise ValueError("Docker inspected unexpected container")
        labels = data[0].get("Config", {}).get("Labels") or {}
        if labels.get("com.supabase.cli.project") != project:
            raise ValueError("Docker project label mismatch")
    return {"rc":p.returncode, "stdout":base64.b64encode(output).decode("ascii"),"stderr":base64.b64encode(p.stderr).decode("ascii")}


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        pid, uid, gid = struct.unpack("3i", self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid != self.server.test_uid:
            return
        try:
            raw = self.rfile.readline(LIMIT + 1)
            if len(raw) > LIMIT or not raw.endswith(b"\n"):
                raise ValueError("Invalid request length")
            req = json.loads(raw)
            if sorted(req) != ["argv", "stdin_b64"] or not isinstance(req["argv"], list) or not isinstance(req["stdin_b64"], str):
                raise ValueError("Invalid request structure")
            if any(not isinstance(s, str) for s in req["argv"]):
                raise ValueError("Invalid argv type")
            body = base64.b64decode(req["stdin_b64"], validate=True)
            if len(body) > LIMIT // 2:
                raise ValueError("Request body limit")
            response = run_command(req["argv"], self.server.project, body)
        except (ValueError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            response = {"rc":126, "stdout":"", "stderr":base64.b64encode(f"F01_BROKER_DENIED:{type(exc).__name__}\n".encode()).decode()}
        self.wfile.write((json.dumps(response, separators=(",", ":")) + "\n").encode())


class UnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    request_queue_size = 16


def client(socket_path, argv):
    data = sys.stdin.buffer.read(LIMIT // 2 + 1)
    if len(data) > LIMIT // 2:
        raise SystemExit("F01_BROKER_DENIED:input too large")
    req = {"argv":argv, "stdin_b64":base64.b64encode(data).decode()}
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(150)
        sock.connect(socket_path)
        sock.sendall((json.dumps(req,separators=(",", ":"))+"\n").encode())
        payload=b""
        while b"\n" not in payload:
            chunk=sock.recv(65536)
            if not chunk: raise RuntimeError("Broker response truncated")
            payload+=chunk
            if len(payload)>LIMIT*2: raise RuntimeError("Broker response limit")
    out=json.loads(payload.split(b"\n",1)[0])
    sys.stdout.buffer.write(base64.b64decode(out["stdout"], validate=True))
    sys.stderr.buffer.write(base64.b64decode(out["stderr"], validate=True))
    raise SystemExit(int(out["rc"]))


def main():
    p=argparse.ArgumentParser()
    subs=p.add_subparsers(dest="mode",required=True)
    server=subs.add_parser("serve")
    server.add_argument("--socket",required=True)
    server.add_argument("--project",required=True)
    server.add_argument("--test-uid",required=True,type=int)
    call=subs.add_parser("client")
    call.add_argument("--socket",required=True)
    call.add_argument("docker_args",nargs=argparse.REMAINDER)
    a=p.parse_args()
    if a.mode=="client":
        client(a.socket,a.docker_args)
        return
    command_for(list(PS_ARGS),a.project)
    if os.path.exists(a.socket): raise SystemExit("Broker socket already exists")
    with UnixServer(a.socket,Handler) as s:
        s.project=a.project
        s.test_uid=a.test_uid
        os.chmod(a.socket,0o600)
        print("F01_BROKER_READY=restricted; no arbitrary Docker APIs",flush=True)
        s.serve_forever()


if __name__ == "__main__":main()
