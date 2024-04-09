from .DFA import DFA
# from DFA import DFA

from dataclasses import dataclass
from collections.abc import Callable
from queue import Queue
from functools import reduce

EPSILON = ''  # this is how epsilon is represented by the checker in the transition function of NFAs


@dataclass
class NFA[STATE]:
    S: set[str]
    K: set[STATE]
    q0: STATE
    d: dict[tuple[STATE, str], set[STATE]]
    F: set[STATE]

    def epsilon_closure(self, state: STATE) -> set[STATE]:
        # compute the epsilon closure of a state (you will need this for subset construction)
        # see the EPSILON definition at the top of this file
        def helper(openSet: set[STATE], closedSet: set[STATE]) -> set[STATE]:
            if openSet == set():
                return closedSet
            else:
                nextState = next(iter(openSet))
                return helper(
                    (openSet | self.d.get((nextState, EPSILON), set())) - closedSet - {nextState},
                    closedSet | {nextState})

        return helper({state}, set())

    def subset_construction(self) -> DFA[frozenset[STATE]]:
        # convert this nfa to a dfa using the subset construction algorithm
        epsilon_closures = {state: self.epsilon_closure(state) for state in self.K}
        dfaDict = dict()
        closedStates = set()
        finalStates = set()
        dfaInitState = frozenset(epsilon_closures.get(self.q0, set()))

        openStates = Queue(1 << len(self.K))
        openStates.put(dfaInitState)
        closedStates.add(dfaInitState)

        characters = self.S - {''}
        while not openStates.empty():
            group: frozenset[STATE] = openStates.get(False)
            if group & self.F != set():
                finalStates.add(group)

            for c in characters:
                nextStates = reduce(lambda acc, s: acc | self.d.get((s, c), set()), 
                                    group, set[STATE]())
                nextGroup = reduce(lambda acc, s: acc | epsilon_closures.get(s, set()), 
                                   nextStates, set[STATE]())
                nextGroup = frozenset(nextGroup)

                if nextGroup not in closedStates:
                    openStates.put(nextGroup)
                    closedStates.add(nextGroup)

                dfaDict[(group, c)] = nextGroup

        return DFA(characters, closedStates, dfaInitState, dfaDict, finalStates)

    def remap_states[OTHER_STATE](self, f: 'Callable[[STATE], OTHER_STATE]') -> 'NFA[OTHER_STATE]':
        # optional, but may be useful for the second stage of the project. Works similarly to 'remap_states'
        # from the DFA class. See the comments there for more details.
        map_set = lambda s: {f(q) for q in s}
        return NFA(self.S, map_set(self.K), self.q0, 
                   {(f(q), c): map_set(v) for (q, c), v in self.d.items()}, 
                   map_set(self.F))
