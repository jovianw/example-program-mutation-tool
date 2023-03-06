import sys
import ast
import astor
import random
import copy
from pprint import pprint

# We out here coding in a manic episode while hella ill and hardcoding stuff
def main(ifile, n):
    # Get original AST
    try:
        with open(ifile, "r") as source:
            originalTree = ast.parse(source.read())
    except:
        print("Error opening file")
        sys.exit(1)
    
    random.seed(123)

    # Analyze possible mutation points
    analyzer = Analyzer()
    analyzer.visit(originalTree)
    numPossibleMutations = analyzer.count()

    for i in range(n): # For every mutant
        # Select number of mutations to make
        # Use scuffed custom distribution
        randomNumMutation = random.randint(0, 4) # 0.5 1, 0.25 2, 0.25 everything else
        if numPossibleMutations < 2:
            numMutations = 1
        elif 0 <= randomNumMutation <= 2:
            numMutations = 1
        elif randomNumMutation == 3:
            numMutations = 2
        elif randomNumMutation == 4:
            numMutations = random.randint(3, numPossibleMutations)

        # Select which mutations to make
        mutations = random.sample(range(numPossibleMutations), numMutations)
        mutationInds = [set() for j in range(len(analyzer.stats))]
        for mutation in mutations:
            statInd = 0
            while mutation >= 0:
                if mutation < analyzer.stats[statInd]:
                    mutationInds[statInd].add(mutation)
                    mutation = -1
                else:
                    mutation -= analyzer.stats[statInd]
                statInd += 1
        if mutationInds[16]: # Special handling for function calls since there's so many of them
            mutationInds[16] = {random.randint(0, analyzer.numCalls - 1)}

        # Make mutations
        currentTree = copy.deepcopy(originalTree)
        mutator = Mutator(mutationInds)
        mutator.visit(currentTree)

        # Write into output file
        try:
            with open(str(i) + ".py", "w") as source:
                source.write(astor.to_source(currentTree))
        except Exception as e:
            print(e)


class Analyzer(ast.NodeVisitor):
    '''Analyzes AST for possible mutation points'''
    def __init__(self):
        self.stats = [0] * 19 # Counts of each mutation type
        self.visitedIds = set() # Visited variables, to avoid removing inits
        self.numCalls = 0 # Number of function calls

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Add) and not ( # +
            isinstance(node.left, ast.Str) or 
            isinstance(node.right, ast.Str)
        ):
            self.stats[0] += 1
        elif isinstance(node.op, ast.Sub): # -
            self.stats[1] += 1
        elif isinstance(node.op, ast.Mult): # *
            self.stats[2] += 1
        elif isinstance(node.op, ast.FloorDiv): # //
            self.stats[3] += 1
        elif isinstance(node.op, ast.Div): # /
            self.stats[4] += 1
        self.generic_visit(node)

    def visit_Compare(self, node):
        for op in node.ops:
            if isinstance(op, ast.Eq): # ==
                self.stats[5] += 1
            elif isinstance(op, ast.NotEq): # !=
                self.stats[6] += 1
            elif isinstance(op, ast.Lt): # <
                self.stats[7] += 1
            elif isinstance(op, ast.LtE): # <=
                self.stats[8] += 1
            elif isinstance(op, ast.Gt): # >
                self.stats[9] += 1
            elif isinstance(op, ast.GtE): # >=
                self.stats[10] += 1
            elif isinstance(op, ast.Is): # is
                self.stats[11] += 1
            elif isinstance(op, ast.IsNot): # is not
                self.stats[12] += 1
            elif isinstance(op, ast.In): # in
                self.stats[13] += 1
            elif isinstance(op, ast.NotIn): # not in
                self.stats[14] += 1
        self.generic_visit(node)

    def visit_Assign(self, node): # assignments
        # Get names in assignment
        targetIds = set()
        for target in node.targets:
            if isinstance(target, ast.Name): # name targets
                targetIds.add(target.id)
            elif isinstance(target, ast.Tuple): # tupled targets
                for elem in target.elts:
                    if isinstance(elem, ast.Name):
                        targetIds.add(elem.id)
        # If names have been mentioned already
        if targetIds.issubset(self.visitedIds):
            self.stats[15] += 1
        self.generic_visit(node)

    def visit_Call(self, node): # function calls
        self.stats[16] = 1 # placeholder
        self.numCalls += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.And): # and
            self.stats[17] += 1
        if isinstance(node.op, ast.Or): # or
            self.stats[18] += 1
        self.generic_visit(node)

    def report(self):
        # Report counts of each possible mutation
        pprint(self.stats)

    def count(self):
        # Returns number of possible mutations
        return sum(self.stats)
    

class Mutator(ast.NodeTransformer):
    '''Makes mutations according to targetMutations (a list of sets of operation occurences to mutate)'''
    def __init__(self, targetMutations):
        self.targets = targetMutations # List of sets of operation occurences to mutate
        self.current = [0] * len(targetMutations) # Current number of operation occurences
        self.visitedIds = set() # Visited variables, to avoid removing inits

    def visit_BinOp(self, node):
        result = node
        if isinstance(node.op, ast.Add) and not ( # +
            isinstance(node.left, ast.Str) or 
            isinstance(node.right, ast.Str)
        ):
            if self.current[0] in self.targets[0]:
                result = ast.BinOp(left=node.left, op=ast.Sub(), right=node.right)
            self.current[0] += 1
        elif isinstance(node.op, ast.Sub): # -
            if self.current[1] in self.targets[1]:
                result = ast.BinOp(left=node.left, op=ast.Add(), right=node.right)
            self.current[1] += 1
        elif isinstance(node.op, ast.Mult): # *
            if self.current[2] in self.targets[2]:
                result = ast.BinOp(left=node.left, op=ast.FloorDiv(), right=node.right)
            self.current[2] += 1
        elif isinstance(node.op, ast.FloorDiv): # //
            if self.current[3] in self.targets[3]:
                result = ast.BinOp(left=node.left, op=ast.Mult(), right=node.right)
            self.current[3] += 1
        elif isinstance(node.op, ast.Div): # /
            if self.current[4] in self.targets[4]:
                result = ast.BinOp(left=node.left, op=ast.Mult(), right=node.right)
            self.current[4] += 1
        self.generic_visit(node)
        return result

    def visit_Compare(self, node):
        mutated = False # whether or not to return newResult
        newResult = copy.copy(node)
        for opInd in range(len(node.ops)):
            if isinstance(node.ops[opInd], ast.Eq): # ==
                if self.current[5] in self.targets[5]:
                    newResult.ops[opInd] = ast.NotEq()
                    mutated = True
                self.current[5] += 1
            elif isinstance(node.ops[opInd], ast.NotEq): # !=
                if self.current[6] in self.targets[6]:
                    newResult.ops[opInd] = ast.Eq()
                    mutated = True
                self.current[6] += 1
            elif isinstance(node.ops[opInd], ast.Lt): # <
                if self.current[7] in self.targets[7]:
                    newResult.ops[opInd] = ast.GtE()
                    mutated = True
                self.current[7] += 1
            elif isinstance(node.ops[opInd], ast.LtE): # <=
                if self.current[8] in self.targets[8]:
                    newResult.ops[opInd] = ast.Gt()
                    mutated = True
                self.current[8] += 1
            elif isinstance(node.ops[opInd], ast.Gt): # >
                if self.current[9] in self.targets[9]:
                    newResult.ops[opInd] = ast.LtE()
                    mutated = True
                self.current[9] += 1
            elif isinstance(node.ops[opInd], ast.GtE): # >=
                if self.current[10] in self.targets[10]:
                    newResult.ops[opInd] = ast.Lt()
                    mutated = True
                self.current[10] += 1
            elif isinstance(node.ops[opInd], ast.Is): # is
                if self.current[11] in self.targets[11]:
                    newResult.ops[opInd] = ast.IsNot()
                    mutated = True
                self.current[11] += 1
            elif isinstance(node.ops[opInd], ast.IsNot): # is not
                if self.current[12] in self.targets[12]:
                    newResult.ops[opInd] = ast.Is()
                    mutated = True
                self.current[12] += 1
            elif isinstance(node.ops[opInd], ast.In): # in
                if self.current[13] in self.targets[13]:
                    newResult.ops[opInd] = ast.NotIn()
                    mutated = True
                self.current[13] += 1
            elif isinstance(node.ops[opInd], ast.NotIn): # not in
                if self.current[14] in self.targets[14]:
                    newResult.ops[opInd] = ast.In()
                    mutated = True
                self.current[14] += 1
        self.generic_visit(node)
        return newResult if mutated else node
    
    def visit_Assign(self, node): # = assignments
        result = node
        targetIds = set()
        # Get names of assignment
        for target in node.targets:
            if isinstance(target, ast.Name): # Name targets
                targetIds.add(target.id)
            elif isinstance(target, ast.Tuple): # Tupled targets
                for elem in target.elts:
                    if isinstance(elem, ast.Name):
                        targetIds.add(elem.id)
        # If names already mentioned before
        if targetIds.issubset(self.visitedIds):
            if self.current[15] in self.targets[15]:
                result = ast.Expr(ast.Num(1))
            self.current[15] += 1
        self.generic_visit(node)
        return result
    
    def visit_Call(self, node): # function calls
        result = node
        if self.current[16] in self.targets[16]:
            result = ast.NameConstant(None)
        self.current[16] += 1
        self.generic_visit(node)
        return result
        
    def visit_BoolOp(self, node):
        result = node
        if isinstance(node.op, ast.And): # and
            if self.current[17] in self.targets[17]:
                result = ast.BoolOp(op=ast.Or(), values=node.values)
            self.current[17] += 1
        if isinstance(node.op, ast.Or): # or
            if self.current[18] in self.targets[18]:
                result = ast.BoolOp(op=ast.And(), values=node.values)
            self.current[18] += 1
        self.generic_visit(node)
        return result


if __name__ == "__main__":
    try:
        ifile = sys.argv[1]
        n = int(sys.argv[2])
    except:
        print("Incorrect parameters:")
        print("mutate.py <source file> <number of mutants>")
        sys.exit(1)
    main(ifile, n)