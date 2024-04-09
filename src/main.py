from enum import Enum
from typing import cast, Self
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from sys import argv
from .Lexer import GenericLexer

class LTerminal(Enum):
	LAMBDA = "LAMBDA"
	ID = "ID"
	NUM = "NUM"
	PLUS = "PLUS"
	CONCAT = "CONCAT"
	COLON = "COLON"
	LPAREN = "LPAREN"
	RPAREN = "RPAREN"
	WS = "WS"

	def __repr__(self) -> str:
		return self.value

spec: list[tuple[LTerminal, str]] = [
	(LTerminal.LAMBDA, "lambda"),
	(LTerminal.ID, "([a-z]|[A-Z])+)"),
	(LTerminal.NUM, "([0-9])+"),
	(LTerminal.PLUS, r"\+"),
	(LTerminal.CONCAT, r"\+\+"),
	(LTerminal.COLON, ":"),
	(LTerminal.LPAREN, r"\("),
	(LTerminal.RPAREN, r"\)"),
	(LTerminal.WS, "(\\ |\t|\n)+")
]
lexer = GenericLexer[LTerminal](spec)

@dataclass
class LAtom(ABC):
	@abstractmethod
	def evaluate(self, scope: dict[str, Self]) -> Self:
		pass

@dataclass
class LId(LAtom):
	id: str
	def evaluate(self, scope: dict[str, LAtom]) -> LAtom:
		if self.id in ["+", "++"]:
			return self
		return scope[self.id]

@dataclass
class LList(LAtom):
	lst: list[LAtom]
	def evaluate(self, scope: dict[str, LAtom]) -> LAtom:
		evList = list(map(lambda x: x.evaluate(scope), self.lst))
		if len(evList) != 2:
			return LList(evList)
		# function call
		f = evList[0]
		if not (isinstance(f, LLambdaExpr) or (isinstance(f, LId) and f.id in ["+", "++"])):
			return LList(evList)
		arg = evList[1]
		if isinstance(f, LLambdaExpr):
			return f.expr.evaluate(scope | f.context | {f.arg.id: arg})
		if f.id == "+":
			if not isinstance(arg, LList):
				raise Exception("cannot add non list")
			summer = lambda l: sum(map(toNumber, l))
			def toNumber(x: LList | LNum) -> int:
				return cast(LNum, x).num if isinstance(x, LNum) else summer(cast(LList, x).lst)
			
			return LNum(summer(arg.lst))
		if f.id == "++":
			if not isinstance(arg, LList):
				raise Exception("cannot concat non list")
			
			toList = lambda x: x.lst if isinstance(x, LList) else [x]
			return LList(sum(map(toList, arg.lst), []))
		return LList(evList)  # unreachable but vscode complains
	
	def __repr__(self) -> str:
		if len(self.lst) == 0:
			return "()"
		return f"( {" ".join(map(str, self.lst))} )"

@dataclass
class LNum(LAtom):
	num: int
	def evaluate(self, scope: dict[str, LAtom]) -> LAtom:
		return self
	
	def __repr__(self) -> str:
		return str(self.num)

@dataclass
class LLambdaExpr(LAtom):
	arg: LId
	expr: LAtom
	context: dict[str, LAtom] = field(default_factory=dict)
	def evaluate(self, scope: dict[str, LAtom]) -> LAtom:
		return LLambdaExpr(self.arg, self.expr, self.context | scope)

# this class is only used to mark the end of a list reduction
@dataclass
class LListReduceMarker(LAtom):
	def evaluate(self, scope: dict[str, LAtom]) -> LAtom:
		raise Exception("Unreachable")

class LNonTerminal(Enum):
	LIST = "LIST"
	ATOM = "ATOM"
	LAMBDA_EXPR = "LAMBDA_EXPR"
	# marker for triggering a reduction of a lambda expression
	LAMBDA_REDUCE_MARKER = "LAMBDA_REDUCE_MARKER"

	def __repr__(self) -> str:
		return self.value

def debug_print(*args, **kwargs):
	#print(*args, **kwargs)
	pass

class LParser:
	parseStack: list[LNonTerminal | LTerminal]
	valueStack: list[LAtom]
	input: list[tuple[LTerminal, str]]
	index: int

	def peek(self) -> LTerminal:
		while self.input[self.index][0] == LTerminal.WS:
			self.index += 1
		return self.input[self.index][0]

	def reduceList(self) -> None:
		lst = []
		atom = self.valueStack.pop()
		while not isinstance(atom, LListReduceMarker):
			lst.append(atom)
			atom = self.valueStack.pop()
		llist = LList(lst[::-1])
		self.valueStack.append(llist)

	def reduceLambda(self) -> None:
		expr = self.valueStack.pop()
		arg = cast(LId, self.valueStack.pop())
		self.valueStack.append(LLambdaExpr(arg, expr))

	def terminal(self, terminal: LTerminal) -> None:
		if self.peek() != terminal:
			raise Exception(f"Unexpected token {self.input[self.index][0]}")
		match terminal:
			case LTerminal.ID:
				self.valueStack.append(LId(self.input[self.index][1]))
			case LTerminal.NUM:
				self.valueStack.append(LNum(int(self.input[self.index][1])))
			case LTerminal.PLUS:
				self.valueStack.append(LId("+"))
			case LTerminal.CONCAT:
				self.valueStack.append(LId("++"))
			case LTerminal.RPAREN:
				self.reduceList()

		self.index += 1

	def nonterminal(self, nonterminal: LNonTerminal) -> None:
		match nonterminal:
			case LNonTerminal.LIST:
				if self.peek() != LTerminal.RPAREN:
					self.parseStack.append(LNonTerminal.LIST)
					self.parseStack.append(LNonTerminal.ATOM)
			case LNonTerminal.ATOM:
				match self.peek():
					case LTerminal.LPAREN:
						self.valueStack.append(LListReduceMarker())
						self.parseStack.append(LTerminal.RPAREN)
						self.parseStack.append(LNonTerminal.LIST)
						self.parseStack.append(LTerminal.LPAREN)
					case LTerminal.ID | LTerminal.NUM | LTerminal.PLUS | LTerminal.CONCAT:
						# we can skip going through the main loop for these cases
						self.terminal(self.peek())
					case LTerminal.LAMBDA:
						self.parseStack.append(LNonTerminal.LAMBDA_EXPR)
			case LNonTerminal.LAMBDA_EXPR:
				self.parseStack.append(LNonTerminal.LAMBDA_REDUCE_MARKER)
				self.parseStack.append(LNonTerminal.ATOM)
				self.parseStack.append(LTerminal.COLON)
				self.parseStack.append(LTerminal.ID)
				self.parseStack.append(LTerminal.LAMBDA)
			case LNonTerminal.LAMBDA_REDUCE_MARKER:
				self.reduceLambda()

	
	def parse(self, tokens: list[tuple[LTerminal, str]]) -> LList:
		self.parseStack = []
		self.valueStack = []
		self.input = tokens
		self.index = 0

		self.parseStack.append(LTerminal.RPAREN)
		self.parseStack.append(LNonTerminal.LIST)
		self.parseStack.append(LTerminal.LPAREN)
		self.valueStack.append(LListReduceMarker())
		while len(self.parseStack) != 0:
			debug_print("INPUT: ")
			debug_print(self.input[self.index:])
			debug_print("PARSE STACK: ")
			debug_print(self.parseStack)
			debug_print("VALUE STACK: ")
			debug_print(self.valueStack)

			top = self.parseStack.pop()
			if top == LTerminal.WS:
				continue

			if isinstance(top, LNonTerminal):
				self.nonterminal(top)
			elif isinstance(top, LTerminal):
				self.terminal(top)
			else:
				raise Exception("Invalid symbol on stack")
		assert len(self.valueStack) == 1
		return cast(LList, self.valueStack.pop())


parser = LParser()

def main():
	if len(argv) != 2:
		return
	
	filename = argv[1]
	with open(filename, "r") as f:
		code = f.read()
		tokens = lexer.lex(code)
		# lexical error
		if tokens[0][0] == "":
			print(tokens[0][1])
			return
		debug_print(tokens)
		# type narrowing - no-op at runtime
		tokens = cast(list[tuple[LTerminal, str]], tokens)
		prog_list = parser.parse(tokens)
		debug_print(prog_list)
		#evaluate(prog_list)
		print(prog_list.evaluate({}))

class StackDict[K, V]:
	__dict: dict[K, list[V]]
	def __init__(self) -> None:
		self.__dict = {}
	
	def push(self, key: K, value: V) -> None:
		if key not in self.__dict:
			self.__dict[key] = []
		self.__dict[key].append(value)

	def pop(self, key: K) -> V:
		return self.__dict[key].pop()
	
	def read(self, key: K) -> V:
		return self.__dict[key][-1]

if __name__ == '__main__':
    main()
