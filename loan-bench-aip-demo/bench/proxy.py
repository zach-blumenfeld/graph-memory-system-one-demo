"""The only way out of a benchmark container: an HTTPS CONNECT proxy that allows the hosts
named on its command line and refuses everything else. Every request is logged, allowed or
denied, and the runner saves the log beside the results."""
import asyncio
import sys

ALLOW = set(sys.argv[1:])


async def pipe(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def handle(reader, writer):
    peer = writer.get_extra_info("peername")[0]
    try:
        parts = (await reader.readline()).decode("latin1").split()
        while (await reader.readline()) not in (b"\r\n", b"\n", b""):
            pass
        target = parts[1] if len(parts) > 1 else "?"
        host, _, port = target.rpartition(":")
        if len(parts) < 2 or parts[0] != "CONNECT" or host not in ALLOW or port != "443":
            print(f"DENY {peer} {parts[0] if parts else '?'} {target}", flush=True)
            writer.write(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            await writer.drain()
            writer.close()
            return
        print(f"ALLOW {peer} {target}", flush=True)
        up_reader, up_writer = await asyncio.open_connection(host, 443)
        writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        await writer.drain()
        await asyncio.gather(pipe(reader, up_writer), pipe(up_reader, writer))
    except Exception as e:
        print(f"ERROR {peer} {e!r}", flush=True)
        writer.close()


async def main():
    server = await asyncio.start_server(handle, "0.0.0.0", 8080)
    async with server:
        await server.serve_forever()


asyncio.run(main())
