from mapa import Map
from strips import Box, Wall, Keeper, Floor, searchKeeper, STRIPSKeeper
from consts import Tiles


class EnhancedMap(Map):
    @property
    def PredicatesToStrips(self):
        """Analizar o mapa para verificar a posição inicial das paredes, boxes e keeper. Retorna qual é o goal state."""
        goalStatus = set()
        walls = set()
        box = set()
        keeper = None
        y = -1
        x = -1
        for row in self._map:
            y += 1
            x = -1
            for column in row:
                x += 1
                tile = column
                # Caso a posição corresponda a um goal, adicionar ao goalStatus uma box nessa posição para futura verificação de se já nos encontramos num estado que conclua o nivel
                if Tiles.GOAL == tile:
                    goalStatus.add(Box(x, y))
                    continue
                # Caso a posição esteja inicialmente ocupada por uma caixa já em cima de um goal, adicionar ao set das boxes e ao goalStatus
                elif Tiles.BOX_ON_GOAL == tile:
                    goalStatus.add(Box(x, y))
                    box.add(Box(x, y))
                    continue
                # Caso a posição corresponda a uma parede, adicionar ao set das paredes
                elif Tiles.WALL == tile:
                    walls.add(Wall(x, y))
                    continue
                # Identificar a posição do keeper
                elif Tiles.MAN == tile:
                    keeper = Keeper(x, y)
                    continue
                # Caso o keeper esteja em cima de um goal, adicionar a posição ao goalStatus e identificar a posição do keeper
                elif Tiles.MAN_ON_GOAL == tile:
                    goalStatus.add(Box(x, y))
                    keeper = Keeper(x, y)
                    continue
                # Caso a posição esteja ocupada por uma box, adicionar ao set das boxes
                elif Tiles.BOX == tile:
                    box.add(Box(x, y))
                    continue

        return goalStatus, walls, box, keeper

    def isDeadlocked(self, pos):
        """Deadlocks simples. Verifica-se se uma posição do mapa, caso uma box seja empurrada para lá, impede que a box possa ser empurrada novamente."""

        # Ignoram-se as posições onde há goals, porque uma caixa poderá ser empurrada para lá e ficar BOX_ON_GOAL, não podendo é voltar a ser empurrada novamente
        if pos in self.goals:
            return False

        blockedLeft = self.is_blocked((pos[0]-1, pos[1]))
        blockedRight = self.is_blocked((pos[0]+1, pos[1]))
        blockedTop = self.is_blocked((pos[0], pos[1]-1))
        blockedBottom = self.is_blocked((pos[0], pos[1]+1))

        # Caso uma posição esteja bloqueada por uma parede por cima ou por baixo e, ao mesmo tempo, esteja bloqueada quer pela direita ou pela esquerda (um canto),
        # é impossível alguma vez mais retirar uma caixa dessa posição.
        if (blockedTop or blockedBottom) and (blockedLeft or blockedRight):
            return True
        return False

    def deadSquaresDeadlockHorizontal(self, box_pos):
        """Zonas do mapa onde, apesar de não ser um simple deadlock (canto), se uma caixa for empurrada para estas posições, não pode ser retirada desta zona. Verificação feita em uma linha (horizontalmente)."""
        x, y = box_pos

        # Não se consideram para este deadSquares as posições nas extremidades do mapa
        if self.is_out_of_bounds((x, y-1)) or self.is_out_of_bounds((x, y+1)):
            return False

        isBlockedLeft = False
        isBlockedRight = False
        goalInRow = False
        rowMovable = []

        # Verifica-se se a posição em questão está bloqueada horizontalmente, isto é, que à sua direita e à sua esquerda ir-se-á encontrar, mais cedo ou mais tarde, uma parede.
        for y_map, row in enumerate(self._map):

            # Começando no y_map=0, percorre-se até ao y correspondente à posição em questão
            if y_map == y:
                addLeft = False
                addRight = True
                # Percorrem-se então as colunas do mapa para aquele y em concreto
                for x_map, column in enumerate(row):
                    # Novamente descartando as situações onde nos encontramos nas extremidades do mapa
                    if not self.is_out_of_bounds((x_map, y_map-1)) or not self.is_out_of_bounds((x_map, y_map+1)):

                        # Á esquerda da posição em questão,
                        if x_map < x:
                            # Caso já se tenha previamente encontrado uma parede nesta linha(y), dá-se append da nova posição onde se encontrou uma parede
                            if addLeft:
                                rowMovable.append((x_map, y_map))
                            # Caso se encontre uma parede, o addLeft fica a true para futura pesquisa nesta linha(y) e inicializa-se a lista rowMovable. 
                            # Além disso coloca-se a caixa como bloquada à esquerda
                            if column == Tiles.WALL:
                                addLeft = True
                                rowMovable = []
                                isBlockedLeft = True

                        # Á direita da posição em questão, com a mesma lógica descrita anteriormente
                        if x_map >= x:
                            if column == Tiles.WALL:
                                addRight = False
                                isBlockedRight = True
                            if addRight:
                                rowMovable.append((x_map, y_map))

        # Verificar se existem goals nesta linha
        goalInRow = any([(x, y) in self.goals for (x, y) in rowMovable])

        #Verificar se as posições desta linha candidatas a deadsquare deadlock estão bloqueadas por cima
        isBlockedTop = all(
            [self.get_tile((x, y-1)) == Tiles.WALL for (x, y) in rowMovable if y-1 >= 0])

        #Verificar se as posições desta linha candidatas a deadsquare deadlock estão bloqueadas por baixo
        isBlockedBottom = all([self.get_tile(
            (x, y+1)) == Tiles.WALL for (x, y) in rowMovable if y+1 < self.size[1]])

        return isBlockedLeft and isBlockedRight and not goalInRow and (isBlockedTop or isBlockedBottom)

    def deadSquaresDeadlockVertical(self, box_pos):
        """Zonas do mapa onde, apesar de não ser um simple deadlock (canto), se uma caixa for empurrada para estas posições, não pode ser retirada desta zona. Verificação feita em uma coluna (verticalmente)."""
        
        # Segue a mesma lógica que a descrita anteriormente
        
        x, y = box_pos

        if self.is_out_of_bounds((x-1, y)) or self.is_out_of_bounds((x+1, y)):
            return False

        isBlockedTop = False
        isBlockedBottom = False
        goalInColumn = False
        columnMovable = []
        posValid = []

        for y_map, row in enumerate(self._map):
            for x_map, column in enumerate(row):
                if x_map == x:
                    posValid.append(((y_map, row), (x_map, column)))

        addTop = False
        addBottom = True
        for (y_map, row), (x_map, column) in posValid:
            if not self.is_out_of_bounds((x_map-1, y_map)) or not self.is_out_of_bounds((x_map+1, y_map)):
                if y_map < y:
                    if addTop:
                        columnMovable.append((x_map, y_map))
                    if column == Tiles.WALL:
                        addTop = True
                        columnMovable = []

                    if self.is_blocked((x, y_map)):
                        isBlockedTop = True
                if y_map >= y:
                    if column == Tiles.WALL:
                        addBottom = False
                    if addBottom:
                        columnMovable.append((x_map, y_map))

                    if self.is_blocked((x, y_map)):
                        isBlockedBottom = True

        goalInColumn = any([(x, y) in self.goals for (x, y) in columnMovable])
        isBlockedLeft = all(
            [self.get_tile((x-1, y)) == Tiles.WALL for (x, y) in columnMovable if x-1 >= 0])

        isBlockedRight = all([self.get_tile(
            (x+1, y)) == Tiles.WALL for (x, y) in columnMovable if x+1 < self.size[0]])

        return isBlockedTop and isBlockedBottom and not goalInColumn and (isBlockedLeft or isBlockedRight)

    def goalsReach(self, possibleMovesSokoban):
        """Calcular o tamanho do caminho, se este existir, e sem considerar a existência de caixas, de qualquer posição do mapa até cada goal do mesmo."""
        goals = self.goals
        goals_reach = {}

        # Para cada x,y
        for y, row in enumerate(self._map):
            for x, column in enumerate(row):
                # Caso a posição não seja uma parede, esteja fora do mapa ou seja inacessível
                if not self.is_blocked((x, y)) and not self.outerMap((x, y)):

                    # Para cada goal realiza-se a pesquisa através do searchKeeper
                    for g in goals:
                        path = searchKeeper(STRIPSKeeper(), Keeper(
                            g[0], g[1]), Keeper(x, y), set(), possibleMovesSokoban)
                        # Se este retornar um path é porque é possível chegar a esse mesmo a partir da posição atual
                        if path:
                            # Guardar o length do path encontrado
                            if (x, y) not in goals_reach:
                                goals_reach[(x, y)] = 0
                            goals_reach[(x, y)] += len(path)
        return goals_reach

    def outerMap(self, pos):
        """Verifica quais as posições nas extermidades do mapa que são inacessíveis pelo keeper."""
        temp_x, temp_y = pos

        # Cada um destes ciclos vai percorrer, com base na posição inicial e na direção que está a ser pesquisada,
        # se encontra parede ou se sai fora do mapa. Se isto não se verificar, vai pesquisar no bloco seguinte até que uma das condições
        # se verifique. Aí, caso esteja fora do mapa, considera-se que essa posição é inacessível pelo keeper porque está entre os
        # limites do mapa e paredes que ladeiam o mesmo. Isto serve para reduzir o número pesquisas desnecessárias que o searchKeeper realizaria.

        # Verificação para baixo
        while not self.is_blocked((temp_x, temp_y)):
            temp_y += 1
        if self.is_out_of_bounds((temp_x, temp_y)):
            return True

        temp_x, temp_y = pos
        # Verificação para cima
        while not self.is_blocked((temp_x, temp_y)):
            temp_y -= 1
        if self.is_out_of_bounds((temp_x, temp_y)):
            return True

        temp_x, temp_y = pos
        # Verificação para a direita
        while not self.is_blocked((temp_x, temp_y)):
            temp_x += 1
        if self.is_out_of_bounds((temp_x, temp_y)):
            return True

        temp_x, temp_y = pos
        # Verificação para a esquerda
        while not self.is_blocked((temp_x, temp_y)):
            temp_x -= 1
        if self.is_out_of_bounds((temp_x, temp_y)):
            return True

        return False

    @property
    def initMoves(self):
        """Verificação inicial sobre quais os movimentos possíveis em cada posição no mapa e situações de deadlock."""
        avail_moves = {}
        dead_square_box_deadlocks = set()
        simple_box_deadlocks = set()

        for y, row in enumerate(self._map):
            for x, column in enumerate(row):
                # Caso a posição em questão não seja uma parede nem esteja nas posições inacessíveis pelo keeper (outerMap)
                if column != Tiles.WALL and not self.outerMap((x, y)):
                    # Verificar se a posição causa deadlock, se sim adiciona à lista para retornar
                    if self.isDeadlocked((x, y)):
                        simple_box_deadlocks.add((x, y))

                    if self.deadSquaresDeadlockHorizontal((x, y)) or self.deadSquaresDeadlockVertical((x, y)):
                        dead_square_box_deadlocks.add((x, y))

                    # Em termos dos movimentos possíveis, verificar se o keeper poderia ir para as 4 diferentes direções, i.e,
                    # se essa posição não é uma parede nem está fora do mapa.

                    # Verificar se o keeper pode ir para a direita
                    if not self.is_blocked((x+1, y)):
                        if (x, y) in avail_moves:
                            avail_moves[(x, y)].append('d')
                        else:
                            avail_moves[(x, y)] = ['d']

                    # Verificar se o keeper pode ir para a esquerda
                    if not self.is_blocked((x-1, y)):
                        if (x, y) in avail_moves:
                            avail_moves[(x, y)].append('a')
                        else:
                            avail_moves[(x, y)] = ['a']

                    # Verificar se o keeper pode ir para cima
                    if not self.is_blocked((x, y-1)):
                        if (x, y) in avail_moves:
                            avail_moves[(x, y)].append('w')
                        else:
                            avail_moves[(x, y)] = ['w']

                    # Verificar se o keeper pode ir para baixo
                    if not self.is_blocked((x, y+1)):
                        if (x, y) in avail_moves:
                            avail_moves[(x, y)].append('s')
                        else:
                            avail_moves[(x, y)] = ['s']

        return avail_moves, simple_box_deadlocks, dead_square_box_deadlocks

    def is_out_of_bounds(self, pos):
        """Determinar se a entidade está fora do mapa."""
        x, y = pos
        if x not in range(self.hor_tiles) or y not in range(self.ver_tiles):
            return True

        return False

    @property
    def goals(self):
        """Lista das coordenadas da localização de todos os goals no mapa."""
        return self.filter_tiles([Tiles.GOAL, Tiles.MAN_ON_GOAL, Tiles.BOX_ON_GOAL])
