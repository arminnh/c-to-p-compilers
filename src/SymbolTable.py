from AbstractSyntaxTree import *

offset = "    "

class SymbolInfo:
    def __init__(self, astnode):
        astnode.symbolInfo = self
        self.address = None
        self.astnode = astnode
        self.typeInfo = astnode.getType()

class VariableSymbolInfo(SymbolInfo):
    def __init__(self, astnode):
        # astnode is ASTDeclaratorInitializerNode
        self.seen = 0 # 0: unseen, 1: begind declared right now, 2: seen and declaration finished
        super(VariableSymbolInfo, self).__init__(astnode)

    @property
    def defined(self):
        for child in self.astnode.children:
            if isinstance(child, ASTExpressionNode):
                return True
        return False


class FunctionSymbolInfo(SymbolInfo):
    def __init__(self, astnode, depth):
        super(FunctionSymbolInfo, self).__init__(astnode)
        self.depth = depth

    @property
    def defined(self):
        return isinstance(self.astnode, ASTFunctionDefinitionNode)


class Scope:
    def __init__(self, parent=None, isFunctionScope=False, name=None):
        self.isFunctionScope = isFunctionScope
        self.addressCounter = 0
        self.addressedVariables = []
        self.name = name
        self.parent = parent
        self.currentChild = 0
        self.children = []
        self.symbols = {}

    def getAddressCounter(self):
        if self.parent is None or self.isFunctionScope:
            return self.addressCounter
        return self.parent.getAddressCounter()

    def assignAddress(self, variable, insertIntoAddressedVariables=True):
        if self.parent is None or self.isFunctionScope:
            if insertIntoAddressedVariables:
                self.addressedVariables.append(variable) # put variable into function scope variable address list
            variable.address = self.addressCounter # set variable's address
            self.addressCounter += variable.typeInfo.size() # increment counter
            return variable.address
        return self.parent.assignAddress(variable)

    def addChild(self, scope):
        scope.parent = self
        self.children.append(scope)
        return scope

    def insertSymbol(self, info):
        #print("inserted id " + str(info.astnode.identifier) + " into symbol table")
        if (info.typeInfo.baseType != "void" or info.typeInfo.indirections != 0) and isinstance(info, VariableSymbolInfo):
            self.assignAddress(info)
        self.symbols[info.astnode.identifier] = info

    def retrieveSymbol(self, name, requireSeen):
        if name is None:
            return None

        symbolInfo = self.symbols.get(name)

        if symbolInfo is not None and requireSeen:
            if isinstance(symbolInfo, VariableSymbolInfo) and symbolInfo.seen < requireSeen:
                return None
        return symbolInfo


    def isInsertionOk(self, new):
        old = self.retrieveSymbol(new.astnode.identifier, requireSeen=0)

        if old is not None:
            if isinstance(old.astnode, ASTDeclaratorInitializerNode):
                return ("identifier '{0}' already taken by variable".format(old.astnode.identifier), new.astnode)

            if type(new) is FunctionSymbolInfo:
                if isinstance(new.astnode, ASTFunctionDefinitionNode):
                    if type(old.astnode) is ASTFunctionDeclarationNode:
                        if old.astnode.getParameters() == new.astnode.getParameters():
                            return True # definition can overwrite declaration
                        else:
                            return ("function definition parameters don't match with previous declaration", new.astnode)

                    elif isinstance(old.astnode, ASTFunctionDefinitionNode):
                        return ("redefinition of function '{0}'".format(new.astnode.identifier), new.astnode)

                elif isinstance(new.astnode, ASTFunctionDeclarationNode):
                    if type(old.astnode) is ASTFunctionDefinitionNode:
                        if not old.astnode.getType().isCompatible(new.astnode.getType()):
                            return ("conflicting types for function declaration " + str(new.astnode.identifier), new.astnode)

                        if old.astnode.getParameters() == new.astnode.getParameters():
                            return False # declaration cannot overwrite definition
                        else:
                            return ("function declaration parameters don't match previous definition", new.astnode)

                    elif type(old.astnode) is ASTFunctionDeclarationNode:
                        if old.astnode.getParameters() == new.astnode.getParameters():
                            return False # declaration cannot overwrite definition
                        else:
                            return ("function declaration parameters don't match previous declaration", new.astnode)

            elif type(new) is VariableSymbolInfo:
                return ("identifier '{0}' already taken by function".format(old.astnode.identifier), old.astnode)

        else:
            return True


    def out(self, level):
        out = offset * level + "Scope" + (" " + self.name if self.name is not None else "") + ":\n"
        if self.isFunctionScope:
            out += offset * (level + 1) + str([info.typeInfo.baseType for info in self.addressedVariables]) + "\n"
        for key, value in self.symbols.items():
            out += offset * (level + 1) + str(key) + ": " + str(value.astnode.getType())
            if value.address is not None:
                out += " | " + str(value.address)
            out += "\n"

        for child in self.children:
            out += child.out(level + 1)

        return out

class SymbolTable(object):
    def __init__(self):
        self.traverse = False
        self.root = Scope()
        self.currentScope = self.root
        self.currentDepth = 0
        self.functionDepth = 1
        self.stringLiterals = {}

    def openScope(self, isFunctionScope=False, name=None):
        self.currentDepth += 1
        if isFunctionScope:
            self.functionDepth += 1

        if self.traverse:
            if self.currentScope.currentChild >= len(self.currentScope.children):
                raise Exception("Trying to open nonexisting scope; current scope:\n" + self.currentScope.out(0) + "am at child " + str(self.currentScope.currentChild))
            self.currentScope.currentChild += 1
            self.currentScope = self.currentScope.children[self.currentScope.currentChild - 1]
            if name != self.currentScope.name:
                print("Warning: Symbol table open scope traverse: expected {0}, got {1}".format(self.currentScope.name, name))
            self.currentScope.currentChild = 0
            for identifier, symbol in self.currentScope.symbols.items():
                if isinstance(symbol, VariableSymbolInfo):
                    symbol.seen = 0
        else:
            scope = self.currentScope
            self.currentScope = self.currentScope.addChild(Scope(isFunctionScope=isFunctionScope, name=name))

    def closeScope(self):
        self.currentDepth -= 1
        if self.currentScope.isFunctionScope:
            self.functionDepth -= 1
        self.currentScope = self.currentScope.parent

    def insertStringLiteral(self, astnode):
        if self.stringLiterals.get(astnode.value) is not None:
            return
        symbol = VariableSymbolInfo(astnode)
        self.root.assignAddress(symbol, insertIntoAddressedVariables=False)
        self.stringLiterals[astnode.decodedValue] = symbol

    def insertVariableSymbol(self, astnode):
        self.currentScope.insertSymbol(VariableSymbolInfo(astnode))

    def insertFunctionSymbol(self, astnode):
        self.currentScope.insertSymbol(FunctionSymbolInfo(astnode, self.functionDepth))

    def isInsertionOk(self, astnode, isFunction):
        if isFunction:
            return self.currentScope.isInsertionOk(FunctionSymbolInfo(astnode, self.functionDepth))
        else:
            return self.currentScope.isInsertionOk(VariableSymbolInfo(astnode))

    def retrieveSymbol(self, name, requireSeen=1):
        scope = self.currentScope

        while scope is not None:
            nametype = scope.retrieveSymbol(name, requireSeen)
            if nametype is not None:
                return nametype

            scope = scope.parent

        return None

    def functionDefinitionDepthDifference(self, symbolInfo):
        scope = self.currentScope
        depthDifference = 0

        while scope is not None:
            if symbolInfo in scope.symbols.values():
                return depthDifference
            if scope.isFunctionScope:
                depthDifference += 1
            scope = scope.parent

    def __str__(self):
        return self.root.out(0)

    def traverseOn(self):
        self.traverse = True
        self.resetToRoot()

    def traverseOff(self):
        self.traverse = False

    def resetToRoot(self):
        self.currentScope = self.root
        self.root.currentChild = 0
