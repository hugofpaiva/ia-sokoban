import asyncio
import getpass
import json
import os

import websockets
from enhancedMap import EnhancedMap
from strips import *
from search import *


async def agent_loop(server_address="localhost:8000", agent_name="student"):
    skDomain = STRIPSBox()  # Domínio da pesquisa geral das caixas
    keeperDomain = STRIPSKeeper()  # Domínio da pesquisa do keeper

    state = None
    t = None
    actionsIndex = 0  # Para saber em qual movimento do resultado da pesquisa está
    async with websockets.connect(f"ws://{server_address}/player") as websocket:

        # Recebei informações estáticas do jogo
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))

        while True:
            try:
                update = json.loads(
                    await websocket.recv()
                )  # Receber update do jogo

                if "map" in update:
                    # Novo nível
                    game_properties = update
                    mapa = EnhancedMap(update["map"])

                    actionsIndex = 0
                    # Transformação do mapa em predicados
                    goalState, walls, boxes, sokoban = mapa.PredicatesToStrips

                    # Frozenset necessário para a implementação do backtrack
                    initialState = frozenset(boxes)

                    # Determinação de condições de Deadlock e movimentos possiveis do Keeper
                    possibleMovesSokoban, simple_box_deadlocks, dead_square_box_deadlocks = mapa.initMoves
                    early_deadlocks = simple_box_deadlocks.union(
                        dead_square_box_deadlocks)

                    # Determinação de todas as posições que são possíveis de chegar a partir de um goal
                    goals_reach = mapa.goalsReach(possibleMovesSokoban)

                    p = SearchProblem(skDomain, keeperDomain, initialState, goalState,
                                      walls, sokoban, possibleMovesSokoban, early_deadlocks, goals_reach)

                    t = SearchTree(p)

                    # Início da thread da pesquisa
                    t.path_hunt()

                else:
                    # Novo estado do mapa
                    if state != update:
                        state = update

                        # Verifica se já existem ações novas e se já acabou de as enviar
                        if actionsIndex < len(t.actions):
                            await websocket.send(
                                json.dumps(
                                    {"cmd": "key", "key": t.actions[actionsIndex]})
                            )
                            actionsIndex += 1

            except websockets.exceptions.ConnectionClosedOK:
                print("Server has cleanly disconnected us")
                return

# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 student.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))
