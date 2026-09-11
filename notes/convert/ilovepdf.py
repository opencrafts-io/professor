import requests

from .base import ConversionError

API = "https://api.ilovepdf.com/v1"


class ILovePDFConverter:
    """Office documents -> PDF via iLoveAPI's officepdf tool (10 credits/file)."""

    def __init__(self, public_key, timeout=120):
        self._public_key = public_key
        self._timeout = timeout

    def _check(self, step, response):
        if response.status_code != 200:
            raise ConversionError(f"{step} returned {response.status_code}: {response.text[:300]}")
        return response

    def to_pdf(self, file_bytes, filename):
        auth = self._check(
            "auth",
            requests.post(f"{API}/auth", json={"public_key": self._public_key}, timeout=30),
        )
        headers = {"Authorization": f"Bearer {auth.json()['token']}"}

        start = self._check(
            "start", requests.get(f"{API}/start/officepdf", headers=headers, timeout=30)
        )
        server, task = start.json()["server"], start.json()["task"]

        upload = self._check(
            "upload",
            requests.post(
                f"https://{server}/v1/upload",
                headers=headers,
                data={"task": task},
                files={"file": (filename, file_bytes)},
                timeout=self._timeout,
            ),
        )
        self._check(
            "process",
            requests.post(
                f"https://{server}/v1/process",
                headers=headers,
                json={
                    "task": task,
                    "tool": "officepdf",
                    "files": [
                        {
                            "server_filename": upload.json()["server_filename"],
                            "filename": filename,
                        }
                    ],
                },
                timeout=self._timeout,
            ),
        )
        download = self._check(
            "download",
            requests.get(
                f"https://{server}/v1/download/{task}", headers=headers, timeout=self._timeout
            ),
        )
        if not download.content.startswith(b"%PDF-"):
            raise ConversionError("converted result is not a PDF")
        return download.content
