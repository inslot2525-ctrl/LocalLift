"""Build step for the Render Workflow service (native Python runtime, no Dockerfile).

Pillow's RAQM layout needs libfribidi.so.0 to shape Hindi/Marathi. The Dockerfile installs it with apt;
the Workflows Python runtime has no apt step, so this downloads the Debian package, checks its hash and
unpacks the .so into .vendor/lib. The run command sets LD_LIBRARY_PATH to that folder.

Build command: pip install -r requirements.txt && python -m pipeline.vendor_fribidi
"""
import ctypes.util
import hashlib
import io
import pathlib
import sys
import tarfile
import urllib.request

URL = "http://deb.debian.org/debian/pool/main/f/fribidi/libfribidi0_1.0.8-2.1_amd64.deb"
SHA256 = "87fce56627aab7b2968501d370aa3ed6d1c792119efa765e71a690bdfe570e62"  # Debian bookworm Packages index
OUT = pathlib.Path(__file__).resolve().parent.parent / ".vendor" / "lib"


def ar_members(data: bytes):
    i = 8  # after "!<arch>\n"
    while i < len(data):
        name = data[i:i + 16].decode().strip().rstrip("/")
        size = int(data[i + 48:i + 58])
        yield name, data[i + 60:i + 60 + size]
        i += 60 + size + (size % 2)


def main() -> None:
    if ctypes.util.find_library("fribidi"):
        print("vendor_fribidi: system libfribidi found, nothing to do")
        return
    deb = urllib.request.urlopen(URL, timeout=60).read()
    if hashlib.sha256(deb).hexdigest() != SHA256:
        sys.exit("vendor_fribidi: hash mismatch, refusing to use the download")
    data = next(body for name, body in ar_members(deb) if name.startswith("data.tar"))
    OUT.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for m in tar.getmembers():
            if pathlib.PurePosixPath(m.name).name.startswith("libfribidi.so"):
                if m.issym():
                    link = OUT / pathlib.PurePosixPath(m.name).name
                    link.unlink(missing_ok=True)
                    link.symlink_to(m.linkname)
                elif m.isfile():
                    (OUT / pathlib.PurePosixPath(m.name).name).write_bytes(tar.extractfile(m).read())
    print("vendor_fribidi: unpacked", sorted(p.name for p in OUT.iterdir()), "into", OUT)


if __name__ == "__main__":
    main()
