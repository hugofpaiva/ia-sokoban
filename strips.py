from search import *
import heapq

# Predicados usados para descrever estado, pre-condições e efeitos
class Predicate:
    def __str__(self):
        return type(self).__name__ + "(" + str(self.args[0]) + "," + str(self.args[1]) + ")"

    def __repr__(self):
        return str(self)

    def __eq__(self, predicate):
        """Permite comparações com "==", etc."""
        return str(self) == str(predicate)

    def __hash__(self):
        """Permite a criação de uma hash costumizada para aumentar a performance dos sets e afins."""
        return hash(str(self))

    def substitute(self, assign):
        """Substitui os argumentos em um predicado the arguments in a predicate."""
        la = self.args
        return type(self)(assign[la[0]]+la[2], assign[la[1]]+la[3])


# Operadores
# -- Os operadores do domínio vão ser subclasses
# -- Ações concretas são instancias dos operadores
class Operator:

    def __init__(self, args, pc, neg, pos, move, keeper=None):
        self.args = args
        self.pc = pc
        self.neg = neg
        self.pos = pos
        self.move = move
        self.keeper = keeper

    def __str__(self):
        return type(self).__name__ + '(' + str(self.args[0]) + "," + str(self.args[1]) + ")"

    def __repr__(self):
        return str(self)

    def __eq__(self, operator):
        return str(self) == str(operator)

    def __hash__(self):
        return hash(str(self))

    @classmethod
    def instanciate(cls, args):
        """Produz uma ação. Retorna None se a ação não for aplicável."""
        if len(args) != len(cls.args):
            return None
        assign = dict(zip(cls.args, args))
        pc = cls.pc.substitute(assign)
        neg = cls.neg.substitute(assign)
        pos = cls.pos.substitute(assign)
        move = cls.move
        keeper = cls.keeper.substitute(assign)
        return cls(args, pc, neg, pos, move, keeper)


class Keeper(Predicate):
    def __init__(self, x, y, addx=0, addy=0):
        self.args = [x, y, addx, addy]


class Box(Predicate):
    def __init__(self, x, y, addx=0, addy=0):
        self.args = [x, y, addx, addy]


class Wall(Predicate):
    def __init__(self, x, y, addx=0, addy=0):
        self.args = [x, y, addx, addy]


class Floor(Predicate):
    def __init__(self, x, y, addx=0, addy=0):
        self.args = [x, y, addx, addy]


X = 'X'
Y = 'Y'


class Up(Operator):
    args = [X, Y]
    pc = Keeper(X, Y)
    neg = Keeper(X, Y)
    pos = Keeper(X, Y, 0, -1)
    keeper = Keeper(X, Y, 0, -1)
    move = 'w'


class Down(Operator):
    args = [X, Y]
    pc = Keeper(X, Y)
    neg = Keeper(X, Y)
    pos = Keeper(X, Y, 0, +1)
    keeper = Keeper(X, Y, 0, +1)
    move = 's'


class Left(Operator):
    args = [X, Y]
    pc = Keeper(X, Y)
    neg = Keeper(X, Y)
    pos = Keeper(X, Y, -1, 0)
    keeper = Keeper(X, Y, -1, 0)
    move = 'a'


class Right(Operator):
    args = [X, Y]
    pc = Keeper(X, Y)
    neg = Keeper(X, Y)
    pos = Keeper(X, Y, +1, 0)
    keeper = Keeper(X, Y, +1, 0)
    move = 'd'


class UpBox(Operator):
    args = [X, Y]
    pc = Box(X, Y, 0, 0)
    neg = Box(X, Y, 0, 0)
    pos = Box(X, Y, 0, -1)
    keeper = Keeper(X, Y, 0, +1)
    move = 'w'


class DownBox(Operator):
    args = [X, Y]
    pc = Box(X, Y, 0, 0)
    neg = Box(X, Y, 0, 0)
    pos = Box(X, Y, 0, +1)
    keeper = Keeper(X, Y, 0, -1)
    move = 's'


class LeftBox(Operator):
    args = [X, Y]
    pc = Box(X, Y, 0, 0)
    neg = Box(X, Y, 0, 0)
    pos = Box(X, Y, -1, 0)
    keeper = Keeper(X, Y, +1, 0)
    move = 'a'


class RightBox(Operator):
    args = [X, Y]
    pc = Box(X, Y, 0, 0)
    neg = Box(X, Y, 0, 0)
    pos = Box(X, Y, +1, 0)
    keeper = Keeper(X, Y, -1, 0)
    move = 'd'


# Domínio de pesquisa baseado em STRIPS
class STRIPSBox(SearchDomain):

    def __init__(self):
        pass

    def checkFreezeDeadlock(self, state, boxAfter, walls, goal):
        """FreezeDeadLock ocorre quando uma ou mais caixas estão bloqueadas numa posição, não podendo ser empurradas novamente."""
        
        # axis: True - verifica apenas na vertical
        # axis: False - verifica apenas na horizontal

        # Embedded function para evitar loops na recursão (corre depois do código indicado abaixo)
        def childsFreezeDeadLock(state, boxAfter, walls, goal, axis, initial):
            boxesToCheck = set()

            x, y = boxAfter.args[0], boxAfter.args[1]
            
            # Se axis = True, significa que a caixa que estava junto a esta estava bloqueada horizontalmente, como tal, esta também está.
            # Portanto, tem apenas de se verificar se a caixa está ou não bloqueada verticalmente
            if axis:
                nextToBoxY = set()
                blockedVertical = False
                
                # Seguir a mesma lógica e verificar se há paredes/caixas a bloquear esta verticalmente
                if Box(x, y+1, 0, 0) in state:
                    nextToBoxY.add(Box(x, y+1, 0, 0))

                if Box(x, y-1, 0, 0) in state:
                    nextToBoxY.add(Box(x, y-1, 0, 0))

                if Wall(x, y+1, 0, 0) in walls:
                    nextToBoxY.add(Wall(x, y+1, 0, 0))

                if Wall(x, y-1, 0, 0) in walls:
                    nextToBoxY.add(Wall(x, y-1, 0, 0))

                # Para cada posição acima adicionada ao nextToBoxY
                for y in nextToBoxY:   
                    # Se for uma parede considera-se bloqueado verticalmente
                    if isinstance(y, Wall):
                        blockedVertical = True
                    # Se for uma box terá de se chamar recursivamente a função embedded para verificar também para essa caixa se ela está bloqueada 
                    # Sendo que esta box atual foi verificada verticalmente, a próxima só precisa de ser verificada horizontalmente, daí axis ser passado a False
                    else:
                        # Para evitar loops, quando uma caixa já foi pesquisada, considera-se que está bloqueada 
                        if boxAfter in initial:
                            blockedVertical = True
                            
                        # Adicionar a caixa ao initial para manter um set com as caixas que já foram pesquisadas (a atual)
                        # Adicionar ao boxesToCheck a caixa que foi encontrada como estando a bloquear na vertical da atual
                        else:
                            boxesToCheck.add(y)
                            initial.add(boxAfter)
                            blockedVertical, boxesCheck = childsFreezeDeadLock(
                                state, y, walls, goal, False, initial)
                            # Juntar o resultado da chamada recursiva ao que já tinhamos previamente
                            boxesToCheck.union(boxesCheck)
                return blockedVertical, boxesToCheck


            # Verificar apenas horizontalmente, segue a mesma lógica
            else:
                nextToBoxX = set()
                blockedHorizontal = False

                if Box(x+1, y, 0, 0) in state:
                    nextToBoxX.add(Box(x+1, y, 0, 0))

                if Box(x-1, y, 0, 0) in state:
                    nextToBoxX.add(Box(x-1, y, 0, 0))

                if Wall(x+1, y, 0, 0) in walls:
                    nextToBoxX.add(Wall(x+1, y, 0, 0))

                if Wall(x-1, y, 0, 0) in walls:
                    nextToBoxX.add(Wall(x-1, y, 0, 0))

                for x in nextToBoxX:
                    if isinstance(x, Wall):
                        blockedHorizontal = True
                    else:
                        if boxAfter in initial:
                            blockedHorizontal = True
                        else:
                            boxesToCheck.add(x)
                            initial.add(boxAfter)
                            blockedHorizontal, boxesCheck = childsFreezeDeadLock(
                                state, x, walls, goal, True, initial)
                            boxesToCheck.union(boxesCheck)
                return blockedHorizontal, boxesToCheck



        # O QUE CORRE INICIALMENTE:
        nextToBoxY = set()
        nextToBoxX = set()
        boxesToCheck = set()

        x, y = boxAfter.args[0], boxAfter.args[1]
        # Caso haja uma box diretamente abaixo da caixa em questão
        if Box(x, y+1, 0, 0) in state:
            nextToBoxY.add(Box(x, y+1, 0, 0))

        # Caso haja uma box diretamente acima da caixa em questão
        if Box(x, y-1, 0, 0) in state:
            nextToBoxY.add(Box(x, y-1, 0, 0))

        # Caso haja uma box diretamente à direita da caixa em questão
        if Box(x+1, y, 0, 0) in state:
            nextToBoxX.add(Box(x+1, y, 0, 0))

        # Caso haja uma box diretamente à esquerda da caixa em questão
        if Box(x-1, y, 0, 0) in state:
            nextToBoxX.add(Box(x-1, y, 0, 0))

        # Caso haja uma parede diretamente à direita da caixa em questão
        if Wall(x+1, y, 0, 0) in walls:
            nextToBoxX.add(Wall(x+1, y, 0, 0))

        # Caso haja uma parede diretamente à esquerda da caixa em questão
        if Wall(x-1, y, 0, 0) in walls:
            nextToBoxX.add(Wall(x-1, y, 0, 0))

        # Caso haja uma parede diretamente abaixo da caixa em questão
        if Wall(x, y+1, 0, 0) in walls:
            nextToBoxY.add(Wall(x, y+1, 0, 0))

        # Caso haja uma parede diretamente acima da caixa em questão
        if Wall(x, y-1, 0, 0) in walls:
            nextToBoxY.add(Wall(x, y-1, 0, 0))

        # Adicionar ao estado atual a caixa depois de ser realizado o movimento que está a ser estudado
        state.add(boxAfter)

        blockedVertical = False
        blockedHorizontal = False
        # Caso haja paredes/caixas ao lado ou para cima e para baixo da caixa em questão
        if nextToBoxX and nextToBoxY:
            # Para as caixas que estão ao lado 
            for x in nextToBoxX:
                if not blockedHorizontal:
                    # Se se tratar de uma parede, está bloqueado horizontalmente 
                    if isinstance(x, Wall):
                        blockedHorizontal = True
                    # Caso contrário, adicionar a caixa a uma lista de caixas que futuramente serão analizadas para verificar se elas próprias estão, também, bloqueadas
                    else:
                        boxesToCheck.add(x)
                        # Chamada da função embedded, passa-se o axis = True porque só vai ser preciso verificar verticalmente na próxima box e passa-se o initial com a box
                        # depois de ser deslocada para fazer verificação de loops
                        blockedHorizontal, boxesCheck = childsFreezeDeadLock(
                            state, x, walls, goal, True, {boxAfter})
                        boxesToCheck.union(boxesCheck)

            # Apenas vale a pena verificar se está bloqueado verticalmente se estiver bloqueado horizontalmente 
            if blockedHorizontal:
                for y in nextToBoxY:
                    if not blockedVertical:
                        if isinstance(y, Wall):
                            blockedVertical = True
                        else:
                            boxesToCheck.add(y)
                            # Chamada da função embedded, axis = False porque como a caixa atual está bloqueada horizontalmente, a próxima só precisa de ser verificada verticalmente
                            blockedVertical, boxesCheck = childsFreezeDeadLock(
                                state, y, walls, goal, False, {boxAfter})
                            boxesToCheck.union(boxesCheck)

        # É considerado um estado de deadlock se nenhuma das caixas estiver em cima de um goal e se estiverem bloqueadas vertical e horizontalmente
        for box in boxesToCheck:
            if box not in goal and blockedHorizontal and blockedVertical:
                return True
        return False


    def actions(self, state, walls):
        operators = [UpBox, DownBox, LeftBox, RightBox]
        actions = set()
        for op in operators:
            for box in state:
                action = op.instanciate([box.args[0], box.args[1]])
                # Verifica se a posição onde o keeper tem de estar para realizar o movimento sobre a caixa é outra caixa ou uma parede, 
                # evitando uma pesquisa extensa sem resultado possível
                if Wall(action.keeper.args[0], action.keeper.args[1]) not in walls and Box(action.keeper.args[0], action.keeper.args[1]) not in state:
                    action.keeperAfterMove = Keeper(
                        action.args[0], action.args[1])
                    actions.add(action)
        return actions

    def keeperSearch(self, keeper_domain, initialState, goalState, state, possibleMovesSokoban):
        return searchKeeper(keeper_domain, initialState, goalState, state, possibleMovesSokoban)

    def result(self, state, action):
        # remover os efeitos negativos
        newstate = set(state)
        newstate.remove(action.neg)

        # adicionar os efeitos positivos
        newstate.add(action.pos)
        return frozenset(newstate)

    def cost(self, cost):
        return cost+1

    def heuristic(self, state, goal):
        """Heurística da pesquisa de ações das caixas."""
        # Tem em consideração as caixas já em goals, se existem caixas na coluna ou linha de outros goals e
        # a distância das caixas que não estão já em goals à posição dos goals não ocupados
        heuristic = 0
        for box in state:
            for g in goal:
                if box == g:
                    heuristic -= 1
                elif g not in state:
                    heuristic += abs(box.args[0] - g.args[0]) + \
                        abs(box.args[0] - g.args[1])
                if box.args[0] == g.args[0] or box.args[1] == g.args[1]:
                    heuristic -= 1
        return heuristic

    def satisfies(self, state, goal):
        return state == goal


class STRIPSKeeper(SearchDomain):

    def __init__(self):
        pass

    def actions(self, keeper):
        operators = [Up, Down, Left, Right]
        actions = []
        for op in operators:
            action = op.instanciate([keeper.args[0], keeper.args[1]])
            actions.append(action)
        return actions

    def result(self, state, action):
        return action.pos

    def cost(self, cost):
        return cost+1

    def heuristic(self, state, goal):
        """Heurística para a pesquisa do Keeper"""
        # Distância de Manhattan
        return abs(state.args[0] - goal.args[0]) + abs(state.args[1] - goal.args[1])

    def satisfies(self, state, goal):
        return state == goal


def searchKeeper(domain, initial, goal, boxes, possibleMoves):
    """Pesquisa do caminho da posição atual do keeper até ao lado da caixa necessário para executar o movimento."""
    # Segue a lógica da pesquisa principal

    backtrack = set()

    root = SearchNode(initial, None, 0,
                      domain.heuristic(initial, goal), None)
    open_nodes = [root]
    heapq.heapify(open_nodes)

    while open_nodes:
        node = heapq.heappop(open_nodes)

        if domain.satisfies(node.state, goal):
            return node.path
        lnewnodes = []

        for a in domain.actions(node.state):
            newstate = domain.result(node.state, a)

            if newstate not in backtrack:
                
                # Verificação se a ação gerada é um movimento possível e se não leva o keeper a ocupar uma posição de uma caixa existente neste estado
                if a.move in possibleMoves[(node.state.args[0], node.state.args[1])] and not any(b.args == a.pos.args for b in boxes):
                    newnode = SearchNode(
                        newstate, node, node.cost+1, domain.heuristic(newstate, goal), a, path=node.path + [a.move])
                    backtrack.add(newstate)
                    lnewnodes.append(newnode)

        for newnode in lnewnodes:
            heapq.heappush(open_nodes, newnode)

    return None
