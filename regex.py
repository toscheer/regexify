from enum import Enum
import copy


class NodeType(Enum):
  STRING = 0
  ALTERNATION = 1
  CONCATENATION = 2
  KLEENE_STAR = 3
  KLEENE_PLUS = 4
  MAYBE = 5
  
  
class Regex:

  JOINED_BY = ['', '|', '', '', '', '']
  IN_PARENTHESES = [False, True, True, False, False, False]
  SUFFIX = ['', '', '', '*', '+', '?']
  
  def __init__(self, type, values): 
    self.type = type
    self.values = values
    
  def __eq__(self, other):
    # base case
    if self.type == NodeType.STRING and other.type == NodeType.STRING:
      return self.values[0] == other.values[0]
    # check for the most simple to recognize unequality, a different type or amount of child elements
    if len(self.values) != len(other.values) or self.type != other.type:
      return False
    # check each child element for equality (recursively, but the construction should guarantee no cycles)
    for i in range(len(self.values)):
      if self.values[i] != other.values[i]:
        return False
    return True
    
  def __str__(self):
    str_values = [str(i) for i in self.values]
    # check if parentheses are needed
    if len(self.values) > 1 and Regex.IN_PARENTHESES[self.type.value]:
      match self.type:
        case NodeType.ALTERNATION:
          return '(' + Regex.JOINED_BY[self.type.value].join(str_values) + Regex.SUFFIX[self.type.value] + ')'
        case NodeType.CONCATENATION:
          # concatenations that only have strings as child elements don't need parentheses
          if all(map(lambda x: x.type == NodeType.STRING, self.values)):
            return Regex.JOINED_BY[self.type.value].join(str_values) + Regex.SUFFIX[self.type.value]
          else:
            return '(' + Regex.JOINED_BY[self.type.value].join(str_values) + Regex.SUFFIX[self.type.value] + ')' 
    return Regex.JOINED_BY[self.type.value].join(str_values) + Regex.SUFFIX[self.type.value]
    
  def __hash__(self):
    if self.type == NodeType.STRING:
      return hash(self.values[0])
    return hash(repr(self))


def simplify_regex(r):
  # execute simplification steps until no further simplification is possible (returned regex is equal to initial regex)
  before = copy.deepcopy(r)
  r = simplify_step(r)
  while before != r:
    before = copy.deepcopy(r)
    r = simplify_step(r)
  return r
  
  
def simplify_step(r):

  # return simple string values (no further simplification possible)
  if r.type == NodeType.STRING:
    return r
  # simplify all children recursively (recursion base case is a child with type STRING)
  r.values = list(map(simplify_step, r.values))
      
  # apply some simplification rules according to the type of this node
  match r.type:
    
    case NodeType.ALTERNATION:
      # Rule: Alternation with a single option is no alternation at all
      if len(r.values) == 1:
        return r.values[0]
      # RULE: x|x = x, we achieve this by converting the list to a dict (no duplicates) and back again (lower time complexity than manually iterating in 0(n^2))
      r.values = list(dict.fromkeys(r.values))
      # RULE: x|x* = x*, x|x+ = x+, x|x? = x?
      # generate list of all elements that aren't Kleene Star, Plus or a Maybe
      non_wrapping = [x for x in r.values if x.type in [NodeType.STRING, NodeType.ALTERNATION, NodeType.CONCATENATION]]         
      # generate list of the content of all elements that are the above things
      wrapping = [x.values[0] for x in r.values if x.type in [NodeType.KLEENE_PLUS, NodeType.KLEENE_STAR, NodeType.MAYBE]]     
      # check if any of the elements in the first list are contained in any element in the second list, if so remove them
      for e in non_wrapping:
        if e in wrapping:
          r.values.remove(e)
      # RULE: ε|x = x?, achieved by checking if any child element is a string element containing 'ε'
      try:
        ep_index = list(map(lambda x: x.type == NodeType.STRING and x.values[0] == 'ε', r.values)).index(True)
      except ValueError:
        ep_index = -1
      if ep_index >= 0 and len(r.values) > 1:
        # remove the ε element, this expression becomes a Maybe with an alternation expression containing the other elements as a child       
        r.values.pop(ep_index)
        r.type = NodeType.MAYBE
        new_alt = Regex(NodeType.ALTERNATION, r.values)
        r.values = [new_alt]
      # RULE: x?|y = (x|y)?, same procedure as above
      try:
        maybe_index = list(map(lambda x: x.type == NodeType.MAYBE, r.values)).index(True)
      except ValueError:
        maybe_index = -1
      if maybe_index >= 0 and len(r.values) > 1:
        # merge whatever the maybe element contains up one layer 
        maybe_element = r.values[maybe_index]
        maybe_element.type = maybe_element.values[0].type
        maybe_element.values = maybe_element.values[0].values
        # this expression becomes a Maybe with an alternation expression containing the other elements as a child       
        r.type = NodeType.MAYBE
        new_alt = Regex(NodeType.ALTERNATION, r.values)
        r.values = [new_alt]
      # Important: Check if any of these manipulations reduced everything to a single element (in that case: merge)
      if len(r.values) == 1 and r.values[0].type == NodeType.STRING:
        r.type = NodeType.STRING        
        r.values = [r.values[0].values[0]]
      # check type again because the ε|x = x? rule could have changed it
      elif len(r.values) == 1 and r.type == NodeType.ALTERNATION:
        r.type = r.values[0].type
        r.values = r.values[0].values
        
    case NodeType.CONCATENATION:
      # RULE: Concatenation with a single option is no concatenation at all
      if len(r.values) == 1:
        return r.values[0]
      # RULE: xx* = x+ = x*x, we achieve this via pairwise iteration and comparison (via __eq__ implementation to catch deeper equalities)
      # iterate from right to left, so something like xx*x becomes xx+ instead of x+x (leaves more room for other rules to simplify further)
      i = len(r.values)-1
      while i > 0:
        left = r.values[i-1]
        right = r.values[i]
        # case xx*
        if right.type == NodeType.KLEENE_STAR and left == right.values[0]:
          r.values.pop(i-1)
          right.type = NodeType.KLEENE_PLUS
          i -= 1
          continue
        # case x*x
        if left.type == NodeType.KLEENE_STAR and right == left.values[0]:
          r.values.pop(i)
          left.type = NodeType.KLEENE_PLUS
          i -= 1
          continue
        i -= 1
      # RULE: x?x* = x* = x*x?, again achieved via pairwise iteration
      i = 0
      max_index = len(r.values)-1
      while i < max_index:
        left = r.values[i]
        right = r.values[i+1]
        # case x?x*
        if left.type == NodeType.MAYBE and right.type == NodeType.KLEENE_STAR and left.values[0] == right.values[0]:
          r.values.pop(i)
          max_index -= 1
          continue
        # case x*x?
        if left.type == NodeType.KLEENE_STAR and right.type == NodeType.MAYBE and left.values[0] == right.values[0]:
          r.values.pop(i+1)
          max_index -= 1
          continue
        i+= 1
      # RULE: Multiple ε are equal to a single ε (e.g. εεε = ε), we iterate and upon finding an ε we stop to 'eat' all immediately following ones to achieve this
      # RULE: x*x* = x*, achieved via the same means as the rule above
      i = 0
      max_index = len(r.values)-1
      while i < max_index:
        left = r.values[i]
        right = r.values[i+1]
        epsilon_case = (left.type == NodeType.STRING and right.type == NodeType.STRING and left.values[0] == 'ε' and right.values[0] == 'ε')
        kleene_case = (left.type == NodeType.KLEENE_STAR and right.type == NodeType.KLEENE_STAR and left.values[0] == right.values[0])
        if epsilon_case or kleene_case:
          r.values.pop(i+1)
          max_index -= 1
          continue
        i += 1
      # RULE: xε = x = εx, again achieved via pairwise iteration and checking if one of the two elements is an empty word
      i = 0
      max_index = len(r.values)-1
      while i < max_index:
        left = r.values[i]
        right = r.values[i+1]
        # case εx
        if left.type == NodeType.STRING and left.values[0] == 'ε':
          r.values.pop(i)
          max_index -= 1
          continue
        # case xε
        if right.type == NodeType.STRING and right.values[0] == 'ε':
          r.values.pop(i+1)
          max_index -= 1
          continue
        i += 1 
      # Rule: x(y|z) = xy|xz and (x|y)z = xz|yz, again achieved via pairwise iteration, checking and concatenation of fitting elements
      i = 0
      max_index = len(r.values)-1
      while i < max_index:
        left = r.values[i]
        right = r.values[i+1]
        # case x(y|z) (simplification is not sensible if the single element is a Kleene Star, Plus or a Maybe)
        if right.type == NodeType.ALTERNATION and left.type != NodeType.KLEENE_PLUS and left.type != NodeType.KLEENE_STAR and left.type != NodeType.MAYBE:
          # replace old left element with new alternation, filled with pairwise concatenations of left element and right's values
          new_alt = Regex(NodeType.ALTERNATION, [])
          for e in right.values:
            new_alt.values.append(Regex(NodeType.CONCATENATION, [left, e]))
          # insert new alternation at old position of left element, delete right element
          r.values = r.values[:i] + [new_alt] + r.values[i+2:]
          max_index -= 1
          continue
        # case (x|y)z, same principle
        if left.type == NodeType.ALTERNATION and right.type != NodeType.KLEENE_PLUS and right.type != NodeType.KLEENE_STAR and right.type != NodeType.MAYBE:
          new_alt = Regex(NodeType.ALTERNATION, [])
          for e in left.values:
            new_alt.values.append(Regex(NodeType.CONCATENATION, [e, right]))
          r.values = r.values[:i] + [new_alt] + r.values[i+2:]
          max_index -= 1
          continue
        i += 1
      # Important: Check if any of these manipulations reduced everything to a single element (in that case: merge)
      if len(r.values) == 1 and r.values[0].type == NodeType.STRING:
        r.type = NodeType.STRING        
        r.values = [r.values[0].values[0]]
      elif len(r.values) == 1:
        r.type = r.values[0].type
        r.values = r.values[0].values
        
    case NodeType.KLEENE_STAR:
      # RULE: ε* = ε, we can just check if the child is a single node of type String with value 'ε' for this
      if len(r.values) == 1 and r.values[0].type == NodeType.STRING and r.values[0].values[0] == 'ε':
        # change type to string and make the value a list with one string (instead of another regex object)
        r.type = NodeType.STRING
        r.values = [r.values[0].values[0]]
      # RULE: (ε|x|y)* = (x|y)*, we need to check two layers deep for this
      if len(r.values) == 1 and not isinstance(r.values[0], str) and r.values[0].type == NodeType.ALTERNATION:
        # check if any of the elements of that alternation is an ε
        try:
          ep_index = list(map(lambda x: x.type == NodeType.STRING and x.values[0] == 'ε', r.values[0].values)).index(True)
        except ValueError:
          ep_index = -1
        if ep_index >= 0 and len(r.values[0].values) > 1:
          r.values[0].values.pop(ep_index)
      # RULE: (x*)* = (x+)* = (x?)* = x*, we need to check two layers deep for this
      if len(r.values) == 1 and not isinstance(r.values[0], str) and r.values[0].type in [NodeType.KLEENE_STAR, NodeType.KLEENE_PLUS, NodeType.MAYBE]:
        r.values = r.values[0].values
        
    case NodeType.KLEENE_PLUS:
      # RULE: ε+ = ε, we can just check if the child is a single node of type String with value 'ε' for this
      if len(r.values) == 1 and r.values[0].type == NodeType.STRING and r.values[0].values[0] == 'ε':
        # change type to string and make the value a list with one string (instead of another regex object)
        r.type = NodeType.STRING
        r.values = [r.values[0].values[0]]
      # RULE: (x*)+ = (x?)+ = x*, we need to check two layers deep for this
      if len(r.values) == 1 and not isinstance(r.values[0], str) and r.values[0].type in [NodeType.KLEENE_STAR, NodeType.MAYBE]:
        r.type = NodeType.KLEENE_STAR
        r.values = r.values[0].values
      # RULE: (x+)+ = x+, we need to check two layers deep for this
      if len(r.values) == 1 and not isinstance(r.values[0], str) and r.values[0].type == NodeType.KLEENE_PLUS:
        r.values = r.values[0].values
        
    case NodeType.MAYBE:
      # RULE: ε? = ε, we can just check if the child is a single node of type String with value 'ε' for this
      if len(r.values) == 1 and r.values[0].type == NodeType.STRING and r.values[0].values[0] == 'ε':
        # change type to string and make the value a list with one string (instead of another regex object)
        r.type = NodeType.STRING
        r.values = [r.values[0].values[0]]
      # RULE: (x*)? = x*, we need to check two layers deep for this
      if len(r.values) == 1 and not isinstance(r.values[0], str) and r.values[0].type == NodeType.KLEENE_STAR:
        r.type = NodeType.KLEENE_STAR
        r.values = r.values[0].values
      # RULE: (x?)? = x?, we need to check two layers deep for this
      if len(r.values) == 1 and not isinstance(r.values[0], str) and r.values[0].type == NodeType.MAYBE:
        r.values = r.values[0].values
        
  # merge children of the same type into the parent (only for alternations and concatenations!)      
  if r.type != NodeType.STRING:
    for i in range(len(r.values)):
      if r.values[i].type == r.type and not Regex.SUFFIX[r.type.value]:
        r.values = r.values[:i] + r.values[i].values + r.values[i+1:]
      
  return r
  
def print_tree(regex, indent=0):
  if regex.type == NodeType.STRING:
    print(' ' * indent, regex.values[0])
  else:
    print(' ' * indent, regex.type.name)
    for e in regex.values:
      print_tree(e, indent+2)
