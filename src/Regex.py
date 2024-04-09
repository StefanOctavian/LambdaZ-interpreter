from .NFA import NFA
# from NFA import NFA
from dataclasses import dataclass
from string import ascii_uppercase, ascii_lowercase, digits

class Regex:
    def thompson(self, q0: int = 0) -> NFA[int]:
        raise NotImplementedError('the thompson method of the Regex class should never be called')

@dataclass
class EpsilonRegex(Regex):
    def thompson(self, q0: int = 0) -> NFA[int]:
        return NFA(set(), {q0}, q0, {}, {q0})

@dataclass
class CharacterRegex(Regex):
    c: str

    def thompson(self, q0: int = 0) -> NFA[int]:
        q1 = q0 + 1
        return NFA({'', self.c}, {q0, q1}, q0, {(q0, self.c): {q1}}, {q1})

@dataclass
class ConcatRegex(Regex):
    r1: Regex
    r2: Regex

    def thompson(self, q0: int = 0) -> NFA[int]:
        nfa1 = self.r1.thompson(q0)
        qf1 = q0 + len(nfa1.K) - 1
        nfa2 = self.r2.thompson(qf1 + 1)
        return NFA(nfa1.S | nfa2.S, nfa1.K | nfa2.K, q0, 
                   {**nfa1.d, **nfa2.d, (qf1, ''): {nfa2.q0}},
                   nfa2.F)
    
@dataclass
class UnionRegex(Regex):
    r1: Regex
    r2: Regex

    def thompson(self, q0: int = 0) -> NFA[int]:
        nfa1 = self.r1.thompson(q0 + 1)
        qf1 = q0 + len(nfa1.K)
        nfa2 = self.r2.thompson(qf1 + 1)
        qf2 = qf1 + len(nfa2.K)
        return NFA(nfa1.S | nfa2.S, nfa1.K | nfa2.K | {q0, qf2 + 1}, q0, 
                   {**nfa1.d, **nfa2.d, (q0, ''): {nfa1.q0, nfa2.q0}, 
                    (qf1, ''): {qf2 + 1}, (qf2, ''): {qf2 + 1}},
                   {qf2 + 1})

@dataclass   
class KleeneStarRegex(Regex):
    r: Regex

    def thompson(self, q0: int = 0) -> NFA[int]:
        nfa = self.r.thompson(q0 + 1)
        qf = q0 + len(nfa.K)
        qf_next = nfa.d.get((qf, ''), set()) | {nfa.q0, qf + 1}
        return NFA(nfa.S, nfa.K | {q0, qf + 1}, q0, 
                   {**nfa.d, (q0, ''): {nfa.q0, qf + 1}, (qf, ''): qf_next},
                   {qf + 1})
   
class PlusRegex(ConcatRegex):
    r: Regex
    def __init__(self, r: Regex):
        self.r = r
        ConcatRegex.__init__(self, r, KleeneStarRegex(r))

    def __repr__(self):
        return f'PlusRegex({self.r})'

class QuestionRegex(UnionRegex):
    r: Regex
    def __init__(self, r: Regex):
        self.r = r
        UnionRegex.__init__(self, r, EpsilonRegex())

    def __repr__(self):
        return f'QuestionRegex({self.r})'

@dataclass
class CharacterSetRegex(Regex):
    charset: set[str]

    def thompson(self, q0: int = 0) -> NFA[int]:
        q1 = q0 + 1
        return NFA(self.charset, {q0, q1}, q0, {(q0, s): {q1} for s in self.charset}, {q1})

class UpercaseRegex(CharacterSetRegex):
    def __init__(self):
        CharacterSetRegex.__init__(self, set(ascii_uppercase))

    def __repr__(self):
        return 'UpercaseRegex()'

class LowercaseRegex(CharacterSetRegex):
    def __init__(self):
        CharacterSetRegex.__init__(self, set(ascii_lowercase))

    def __repr__(self):
        return 'LowercaseRegex()'

class DigitRegex(CharacterSetRegex):
    def __init__(self):
        CharacterSetRegex.__init__(self, set(digits))

    def __repr__(self):
        return 'DigitRegex()'

class RegexParserError(ValueError):
    def __init__(self, unexpected: str, expected: str, pos: int):
        super().__init__(RegexParserError, self, f'unexpected {unexpected} '
                         f'at position {pos}, expected {expected}')

class RegexParser:
    input: str
    index: int
    def __init__(self):
        self.input = ''
        self.index = 0

    def __consume(self, c: str) -> bool:
        cond = self.index + len(c) <= len(self.input) and self.input.startswith(c, self.index)
        self.index += cond * len(c)
        return cond
    
    def __strip_whitespace(self):
        while self.__consume(' '):
            pass
    
    def __next_char(self):
        self.index += 1
        return self.input[self.index - 1]
    
    def __peek(self) -> str:
        return self.input[self.index] if self.index < len(self.input) else ''

    def __union_term(self) -> Regex:
        concat_factor = self.__concat_factor()
        self.__strip_whitespace()
        return concat_factor if self.__peek() in '|)' \
                             else ConcatRegex(concat_factor, self.__union_term())

    def __concat_factor(self) -> Regex:
        unit_item = self.__unit_item()
        self.__strip_whitespace()
        if self.__consume('*'):
            return KleeneStarRegex(unit_item)
        elif self.__consume('+'):
            return PlusRegex(unit_item)
        elif self.__consume('?'):
            return QuestionRegex(unit_item)
        else:
            return unit_item

    def __unit_item(self) -> Regex:
        self.__strip_whitespace()
        if self.__consume('('):
            inner_regex = self.__parse_regex()
            if not self.__consume(')'):
                raise RegexParserError(
                    self.input[self.index] if self.index < len(self.input) else "end of input",
                    ')', self.index)
            return inner_regex
        elif self.__consume("[a-z]"):
            return LowercaseRegex()
        elif self.__consume("[A-Z]"):
            return UpercaseRegex()
        elif self.__consume("[0-9]"):
            return DigitRegex()
        elif self.__consume("eps"):
            return EpsilonRegex()
        elif self.__consume('\\') and self.__peek() in " |*+?(e[":
            return CharacterRegex(self.__next_char())
        else:
            self.__consume('\\')  # optional backslash
            return CharacterRegex(self.__next_char())

    def __parse_regex(self) -> Regex:
        union_term = self.__union_term()
        self.__strip_whitespace()
        return UnionRegex(union_term, self.__parse_regex()) if self.__consume('|') \
                                                            else union_term

    def parse(self, regex: str) -> Regex:
        self.input = regex
        self.index = 0
        return self.__parse_regex()

def parse_regex(regex: str) -> Regex:
    return RegexParser().parse(regex)
    
