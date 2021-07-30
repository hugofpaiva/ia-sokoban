from abc import ABC, abstractmethod
import threading
import heapq


class SearchDomain(ABC):

    # construtor
    @abstractmethod
    def __init__(self):
        pass

    # lista de accoes possiveis num estado
    @abstractmethod
    def actions(self, state):
        pass

    # resultado de uma accao num estado, ou seja, o estado seguinte
    @abstractmethod
    def result(self, state, action):
        pass

    # custo de uma accao num estado
    @abstractmethod
    def cost(self, state, action):
        pass

    # custo estimado de chegar de um estado a outro
    @abstractmethod
    def heuristic(self, state, goal):
        pass

    # test if the given "goal" is satisfied in "state"
    @abstractmethod
    def satisfies(self, state, goal):
        pass


# Problemas concretos a resolver dentro de um determinado dominio
class SearchProblem:
    def __init__(self, domain, keeper_domain, initial, goal, walls, initialSokoban, possibleMovesSokoban, early_deadlocks, goals_reach):
        self.domain = domain
        self.keeper_domain = keeper_domain
        self.initial = initial
        self.goal = goal
        self.walls = walls
        self.initialSokoban = initialSokoban
        self.possibleMovesSokoban = possibleMovesSokoban
        self.early_deadlocks = early_deadlocks
        self.all_states_and_keeper = set()
        self.goals_reach = goals_reach

    def goal_test(self, state):
        return self.domain.satisfies(state, self.goal)

    def backtracking(self, state, keeper):
        """Permite evitar a duplicação de estados, comparando com todos os que já existiram anteriormente."""
        temp_set = set()
        temp_set.update(state)
        temp_set.add(keeper)
        temp_set = frozenset(temp_set)
        if temp_set in self.all_states_and_keeper:
            return True
        return False


class SearchNode:
    def __init__(self, state, parent, cost, heuristic, action, keeper=None, path=[]):
        self.state = state
        self.parent = parent
        self.cost = cost
        self.heuristic = heuristic
        self.action = action

        # Para a pesquisa das caixas. Contém a posição do keeper em cada estado.
        self.keeper = keeper

        self.path = path

        # Evita o cálculo desnecessário de cada vez que é feita a ordenação de nós abertos
        self.sort_cost = self.cost + self.heuristic

    def in_parent(self, newstate):
        """Verifica se um determinado estado já existiu nos nós pais"""
        if self.parent == None:
            return False

        if self.parent.state == newstate:
            return True

        return self.parent.in_parent(newstate)

    def __lt__(self, node2):
        """Permite ditar como é feita a ordenação da heap e de qualquer outra estrutura de dados que use < para ordenar."""
        return self.sort_cost < node2.sort_cost

    def __str__(self):
        return "no(" + str(self.state) + "," + str(self.parent) + ")"

    def __repr__(self):
        return str(self)

# Arvores de pesquisa
class SearchTree:

    # construtor
    def __init__(self, problem):
        self.problem = problem
        root = SearchNode(problem.initial, None, 0, problem.domain.heuristic(
            problem.initial, problem.goal), None, problem.initialSokoban)
        self.open_nodes = heapq.heapify([root])
        self.actions = []

    @property
    def cost(self):
        return self.solution.cost

    def get_path(self, node):
        """Obter o caminho (sequencia de movimentos/ações) da raiz até um nó."""
        if node.parent == None:
            return []

        path = self.get_path(node.parent)
        path += node.action.path
        return path

    def path_hunt(self):
        threading.Thread(target=self.search, args=()).start()

    def search(self):
        """Pesquisa de uma solução com recurso a duas pesquisas e múltiplas verificações e otimizações. 
        Primeira gera um movimento para uma caixa e posteriormente pesquisa o caminho da posição atual 
        do keeper até ao lado da caixa necessário para executar o movimento."""
        root = SearchNode(self.problem.initial, None, 0, self.problem.domain.heuristic(
            self.problem.initial, self.problem.goal), None, self.problem.initialSokoban)

        temp_set = set()
        temp_set.add(self.problem.initial)
        temp_set.add(self.problem.initialSokoban)
        temp_set = frozenset(temp_set)

        self.problem.all_states_and_keeper.add(temp_set)
        self.open_nodes = [root]

        # Criação da heap que guardará e ordenará os nós que passarão pela pesquisa
        heapq.heapify(self.open_nodes)

        while self.open_nodes:
            node = heapq.heappop(self.open_nodes)

            # Verificação se um dado estado é o estado goal da pesquisa
            if self.problem.goal_test(node.state):
                self.solution = node
                self.actions = self.get_path(node)
                return self.actions

            lnewnodes = []

            # Geração de novas ações dado um estado
            for a in self.problem.domain.actions(node.state, self.problem.walls):
                newstate = self.problem.domain.result(node.state, a)

                # Verificação da existência deste estado anteriormente
                if not self.problem.backtracking(newstate, a.keeperAfterMove):
                    box = a.pc

                    # Verificação se a ação gerada é um movimento possível e se não levaria a deadlocks simples ou do tipo deadsquare
                    if a.move in self.problem.possibleMovesSokoban[(box.args[0], box.args[1])] and ((a.pos.args[0], a.pos.args[1]) not in self.problem.early_deadlocks) and a.pos not in node.state and self.problem.goals_reach[(box.args[0], box.args[1])]:
                        temp_state = set(node.state)
                        temp_state.remove(a.pc)

                        # Verificação se este estado está em Freeze Deadlock
                        if not self.problem.domain.checkFreezeDeadlock(temp_state, a.pos, self.problem.walls, self.problem.goal):
                            initialState = node.keeper
                            goalState = a.keeper

                            # Pesquisa de um caminho desde a posição atual do keeper até ao lado necessário para mover a caixa
                            path = self.problem.domain.keeperSearch(
                                self.problem.keeper_domain, initialState, goalState, node.state, self.problem.possibleMovesSokoban)

                            if path is not None:
                                a.path = path + [a.move]

                                # Criação de um novo nó
                                newnode = SearchNode(newstate, node, node.cost+1, self.problem.domain.heuristic(
                                    newstate, self.problem.goal), a, a.keeperAfterMove)

                                lnewnodes.append(newnode)

                                # Atualização do backtrack com o novo estado gerado
                                temp_set = set()
                                temp_set.update(newstate)
                                temp_set.add(a.keeperAfterMove)
                                temp_set = frozenset(temp_set)
                                self.problem.all_states_and_keeper.add(
                                    temp_set)

            # Adição dos novos nós gerados à heap e ordenação automática pela mesma
            for newnode in lnewnodes:
                heapq.heappush(self.open_nodes, newnode)

        return None
