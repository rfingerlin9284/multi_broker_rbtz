#!/usr/bin/env python3
"""
RICK Battlestation WebSocket API
Real-time streaming server for dashboard integration

Streams:
- Position updates (entry/exit, P&L, trailing stops)
- Phase progression (graduation events, statistics)
- Entry gate results (approvals/rejections)
- Guardian gate status (margin, positions, correlation)
- Hive mind consensus (multi-AI analysis)
- Adaptive AI learning (parameter updates)

WebSocket Protocol:
- Client connects to ws://localhost:8888
- Server broadcasts JSON messages:
  * status_update: Full system status every 60s
  * trade_opened: New position opened
  * trade_closed: Position closed with P&L
  * phase_graduation: Autonomous advancement
  * gate_rejection: Signal rejected by gates
  * price_update: Real-time price changes
  * voice_trigger: Text for voice narrator
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Set, Dict, Any
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RickWebSocketAPI:
    """WebSocket server for real-time dashboard streaming"""
    
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        
    async def register_client(self, websocket: WebSocketServerProtocol):
        """Register new dashboard client"""
        self.clients.add(websocket)
        logger.info(f"📡 Dashboard client connected ({len(self.clients)} total)")
        
        # Send welcome message
        await websocket.send(json.dumps({
            'type': 'connection_established',
            'message': 'Connected to RICK Battlestation',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }))
    
    async def unregister_client(self, websocket: WebSocketServerProtocol):
        """Unregister disconnected client"""
        self.clients.discard(websocket)
        logger.info(f"📡 Dashboard client disconnected ({len(self.clients)} remaining)")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return
        
        message_json = json.dumps(message)
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        # Clean up disconnected clients
        self.clients -= disconnected
    
    async def broadcast_status(self, status: Dict):
        """Broadcast full system status"""
        await self.broadcast({
            'type': 'status_update',
            'data': status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_trade_opened(self, trade: Dict):
        """Broadcast new trade opening"""
        await self.broadcast({
            'type': 'trade_opened',
            'data': trade,
            'voice_text': trade.get('voice_text', f"Entering {trade['symbol']}"),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_trade_closed(self, trade: Dict):
        """Broadcast trade closure"""
        await self.broadcast({
            'type': 'trade_closed',
            'data': trade,
            'voice_text': trade.get('voice_text', f"{trade['symbol']} closed"),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_phase_graduation(self, phase_data: Dict):
        """Broadcast phase graduation event"""
        await self.broadcast({
            'type': 'phase_graduation',
            'data': phase_data,
            'voice_text': f"Phase graduation achieved. Welcome to phase {phase_data['new_phase']}.",
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_gate_rejection(self, rejection: Dict):
        """Broadcast signal rejection by gates"""
        await self.broadcast({
            'type': 'gate_rejection',
            'data': rejection,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    async def broadcast_price_update(self, prices: Dict):
        """Broadcast real-time price updates"""
        await self.broadcast({
            'type': 'price_update',
            'data': prices,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle individual client connection"""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                # Handle client commands (if needed)
                try:
                    data = json.loads(message)
                    command = data.get('command')
                    
                    if command == 'ping':
                        await websocket.send(json.dumps({'type': 'pong'}))
                    elif command == 'request_status':
                        # Client requested status update
                        # Will be handled by battlestation
                        pass
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
    
    async def start(self):
        """Start WebSocket server"""
        logger.info(f"🚀 Starting RICK WebSocket API on ws://{self.host}:{self.port}")
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10
        )
        logger.info(f"✅ WebSocket server running on ws://{self.host}:{self.port}")
        
        # Keep server running
        await asyncio.Future()  # Run forever
    
    async def stop(self):
        """Stop WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")


async def main():
    """Standalone server for testing"""
    api = RickWebSocketAPI()
    
    # Start server
    server_task = asyncio.create_task(api.start())
    
    # Simulate some events for testing
    await asyncio.sleep(2)
    
    logger.info("📡 Broadcasting test messages...")
    
    await api.broadcast_trade_opened({
        'symbol': 'BTC-USD',
        'side': 'BUY',
        'size': 10.0,
        'price': 87500.0,
        'position_id': 'test_001'
    })
    
    await asyncio.sleep(5)
    
    await api.broadcast_trade_closed({
        'symbol': 'BTC-USD',
        'pnl': 2.50,
        'reason': 'Trailing stop'
    })
    
    # Run forever
    await server_task


if __name__ == "__main__":
    asyncio.run(main())
