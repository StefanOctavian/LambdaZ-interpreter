from .DFA import DFA
from .NFA import NFA
from .Regex import parse_regex
# from DFA import DFA
# from NFA import NFA
# from Regex import parse_regex
from functools import reduce
from typing import Literal, TypeVar, Optional
from math import inf

def debug_print(*args, **kwargs):
    # print(*args, **kwargs)
    pass

error_format = (lambda line, col: f"No viable alternative at character {col}, line {line}")

class GenericLexer[Token]:
    tokenNames: list[Token]
    tokenStates: dict[int, int]  # map final state to token index in the specification
    dfa: DFA[frozenset[int]]

    def __init__(self, spec: list[tuple[Token, str]]) -> None:
        """initialisation converts the specification to a dfa which will be used in 
        the lex method; the specification is a list of pairs (TOKEN_NAME:REGEX)"""

        self.tokenStates = dict()
        self.tokenNames = [name for name, _ in spec]
        def combiner(acc: tuple[NFA[int], int], spec_index: int) -> tuple[NFA[int], int]:
            _, regex_str = spec[spec_index]
            nfa_acc, last_state = acc
            nfa = parse_regex(regex_str).thompson(last_state + 1)
            self.tokenStates[nfa.q0 + len(nfa.K) - 1] = spec_index
            transitions = nfa_acc.d | nfa.d
            transitions[(0, '')] |= {nfa.q0}
            return NFA(nfa_acc.S | nfa.S, nfa_acc.K | nfa.K, 0,
                       transitions, nfa_acc.F | nfa.F), last_state + len(nfa.K)

        initial_acc = (NFA(set(), {0}, 0, {(0, ''): set()}, set()), 0)
        nfa, _ = reduce(combiner, range(0, len(spec)), initial_acc)
        
        self.dfa = nfa.subset_construction()

    def longest_prefix_match(self, word: str) -> tuple[frozenset[int] | None, int]:
        """returns a pair (last_state, length) where last_state is the final state the dfa
        reaches when accepting a prefix of the word and length is the length of the 
        longest such prefix. If no prefix is accepted, last_state is None and length is the 
        length of the scanned prefix until reaching a sink state (if any) or the end of the word."""
        state = self.dfa.q0
        accepted = state in self.dfa.F
        accept_state = state if accepted else None
        accept_index = 0 if accepted else -1

        for i, c in enumerate(word):
            state = self.dfa.d.get((state, c))
            # state may be None if the word contains a character not in the alphabet
            if state in self.dfa.F:
                accepted = True
                accept_state = state
                accept_index = i + 1
            # subset ∘ thompson produces the unique sink state represented by frozenset()
            if state == frozenset() or state is None:
                return accept_state if accepted else None, accept_index if accepted else i
        
        if state in self.dfa.F:
            return state, len(word)

        return accept_state if accepted else None, accept_index if accepted else len(word)

    def lex(self, word: str) -> list[tuple[Token, str]] | list[tuple[Literal[""], str]]:
        # this method splits the lexer into tokens based on the specification and the rules described in the lecture
        # the result is a list of tokens in the form (TOKEN_NAME:MATCHED_STRING)
        tokens: list[tuple[Token, str]] = []

        line_lengths = (len(line) for line in word.split('\n'))
        index: int = 0

        suffix = word
        while suffix != '':
            debug_print(f"{suffix=}")
            accept_state, length = self.longest_prefix_match(suffix)
            index += length
            debug_print(f"{accept_state=}, {length=}")
            if accept_state is None:
                col = index
                line: int = 0
                for line, linelen in enumerate(line_lengths):
                    col -= (line > 0)
                    if col < linelen: break
                    col -= linelen
                if length == len(suffix):
                    return [("", error_format(line, "EOF"))]
                else: 
                    return [("", error_format(line, col))]
            
            prefix = suffix[:length]
            tokenIndex = int(min(self.tokenStates.get(state, inf) for state in accept_state))
            tokens.append((self.tokenNames[tokenIndex], prefix))
            suffix = suffix[length:]

        return tokens
    
Lexer = GenericLexer[str]
# if __name__ == "__main__":
#     lexer = Lexer([
#                 ("SPACE", "\\ "),
#                 ("NEWLINE", "\n"),
#                 ("ABC", "a(b+)c"),
#                 ("AS", "a+"),
#                 ("BCS", "(bc)+"),
#                 ("DORC", "(d|c)+")
#             ])
#     print(lexer.lex("d a\nbdbc ccddabbbc"))
    