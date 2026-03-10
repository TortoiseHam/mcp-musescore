"""WebSocket client for communicating with MuseScore."""

import asyncio
import json
import logging
from typing import Any

import websockets
import websockets.asyncio.client
import websockets.exceptions

logger = logging.getLogger("MuseScoreMCP.Client")

RECV_TIMEOUT_SECONDS = 30


class MuseScoreClient:
    """Client to communicate with MuseScore WebSocket API."""

    uri: str
    websocket: websockets.asyncio.client.ClientConnection | None

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.uri = f"ws://{host}:{port}"
        self.websocket = None

    async def connect(self) -> bool:
        """Connect to the MuseScore WebSocket API."""
        try:
            self.websocket = await websockets.connect(self.uri)
            logger.info(f"Connected to MuseScore API at {self.uri}")
            return True
        except Exception as e:
            self.websocket = None
            logger.error(f"Failed to connect to MuseScore API: {str(e)}")
            return False

    async def send_command(self, action: str, params: dict[str, Any] | None = None, _retry: bool = True) -> dict[str, Any]:
        """Send a command to MuseScore and wait for response."""
        if not self.websocket:
            connected = await self.connect()
            if not connected:
                return {"error": "Not connected to MuseScore"}

        if params is None:
            params = {}

        command = {"action": action, "params": params}

        try:
            logger.info(f"Sending command: {json.dumps(command)}")
            assert self.websocket is not None
            await self.websocket.send(json.dumps(command))
            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=RECV_TIMEOUT_SECONDS,
            )
            logger.info(f"Received response: {response}")
            return json.loads(response)
        except asyncio.TimeoutError:
            logger.error(f"Timed out waiting for response after {RECV_TIMEOUT_SECONDS}s")
            self.websocket = None
            return {"error": f"Timed out waiting for MuseScore response after {RECV_TIMEOUT_SECONDS}s"}
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"Connection closed: {str(e)}. Attempting reconnect...")
            self.websocket = None
            if not _retry:
                return {"error": f"Connection lost: {str(e)}"}
            connected = await self.connect()
            if not connected:
                return {"error": f"Connection lost and reconnect failed: {str(e)}"}
            return await self.send_command(action, params, _retry=False)
        except Exception as e:
            logger.error(f"Error sending command: {str(e)}")
            self.websocket = None
            return {"error": str(e)}

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Disconnected from MuseScore API")
