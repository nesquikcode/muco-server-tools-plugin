from .sdk import Message, ServerPlugin, ClientData, Packet, ServerConfig, History

from logging import Logger
from fastapi.websockets import WebSocket

import os, asyncio, random, time, json
from string import ascii_letters
os.chdir(os.path.dirname(__file__))

adminpsw = ''.join(random.choices(ascii_letters, k=14))
admins: set[ClientData] = set()
plugin = ServerPlugin()
cfg = json.load(open("index.json"))

@plugin.event("on_startup", None)
def startup(config: ServerConfig, logger: Logger):
    logger.info(f"Enabled ServerTools v{cfg['version']}.")
    logger.info(f"Admin password is {adminpsw}.")

@plugin.event("on_shutdown", None)
def shutdown(config: ServerConfig, logger: Logger):
    logger.info(f"Disabled ServerTools v{cfg['version']}.")

@plugin.event("on_packet", "privateMessage")
def onMessage(config: ServerConfig, logger: Logger, clients: set[ClientData], messages: list, packet: Packet, ws: WebSocket):
    if packet["touser"] == config.server_nickname:
        fromuser = packet.uuid
        data = packet["text"]
        cmd = data.split()[0]
        args = data.split()[1:] if len(data.split()) > 1 else []
        
        client = None
        for x in clients:
            if x.client_uuid == fromuser and x.ws == ws:
                client = x
                break
        else:
            logger.warning(f"Client {fromuser} not found in clients. Is websocket disconnected?"); return True
        
        if cmd == "login" and client not in admins:
            if len(args) < 1:
                asyncio.run(
                    ws.send_text(
                        Message(
                            client.server_uuid,
                            "Неверное использование команды: login [пароль]",
                            config.server_nickname,
                            int(time.time())
                        ).wsPacket
                    )
                ); return True

            if args[0] == adminpsw:
                admins.add(client)
                asyncio.run(
                    ws.send_text(
                        Message(
                            client.server_uuid,
                            "Вход успешен.",
                            config.server_nickname,
                            int(time.time())
                        ).wsPacket
                    )
                ); return True
        if client not in admins: return True

        if cmd == "clearHistory":
            messages.clear()

            for x in clients:
                asyncio.run(
                    ws.send_text(
                        History(
                            x.server_uuid,
                            messages
                        ).wsPacket
                    )
                )
            asyncio.run(
                ws.send_text(
                    Message(
                        client.server_uuid,
                        "История сервера очищена.",
                        config.server_nickname,
                        int(time.time())
                    ).wsPacket
                )
            )
        elif cmd == "onlineUsers":
            text = f" \\- Всего {len(clients)} пользователей на сервере:\n"
            for c, x in enumerate(clients, 1):
                text += f"#{c} - '{x.nickname}' ({x.client_uuid}{', '+ws.client.host+':'+str(ws.client.port) if ws.client is not None else ''})"
            asyncio.run(
                ws.send_text(
                    Message(
                        client.server_uuid,
                        text,
                        config.server_nickname,
                        int(time.time())
                    ).wsPacket
                )
            )
    
    return True

@plugin.event("on_packet", "disconnect")
def onDisconnect(config: ServerConfig, logger: Logger, clients: set[ClientData], messages: list, packet: Packet, ws: WebSocket):
    client = None
    for x in clients:
        if x.client_uuid == packet.uuid and x.ws == ws:
            client = x
            break
    else:
        logger.warning(f"Client {packet.uuid} not found in clients. Is websocket disconnected?"); return True
    
    if client in admins:
        admins.discard(client); return True