import graphviz as gv
import regex as re
import copy

class DFA:
  
  def __init__(self, states, alphabet, initial, accept, transitions): 
  
    # for step visualization, colors for start state, end state and transitions
    self.visualize_colors = ['gray', 'yellow', 'blue']
  
    # check input for given number of states
    if not isinstance(states, int):
      raise TypeError('Number of states must be an integer!')
    elif states <= 0:
      raise ValueError('Number of states must be a positive integer!')     
    self.states = states
      
    # check input for given alphabet
    if not isinstance(alphabet, list):
      raise TypeError('Alphabet must be a list of valid inputs!')
    if len(alphabet) != len(set(alphabet)):
      raise TypeError('Alphabet cannot contain duplicates!')
    for i in alphabet: 
      if not isinstance(i, str):
        raise TypeError('Each entry in alphabet must be a string!')
      elif len(i) != 1:
        err_msg = 'Each entry in alphabet must be a single character, but found \'' + i + '\'!'
        raise ValueError(err_msg)
    self.alphabet = alphabet
    
    # check input for given initial state
    if not isinstance(initial, int):
      raise TypeError('Initial state must be an integer!')
    elif initial < 1 or initial > states:
      err_msg = 'Initial state must be an integer between 1 and the number of states (' + str(states) + '), but is ' + str(initial) + '!'
      raise ValueError(err_msg)
    self.initial = initial
    
    # check input for given accepting states
    if not isinstance(accept, list): 
      raise TypeError('Accepted states must be a list of acceptable end states!')
    if len(accept) != len(set(accept)):
      raise TypeError('List of accepted states cannot contain duplicates!')
    for i in accept:
      if not isinstance(i, int):
        raise TypeError('Each entry in accepted states must be an integer!')
      elif i < 1 or i > states:
        err_msg = 'Each entry in accepted states must be an integer between 1 and the number of states (' + str(states) + '), but one is ' + str(i) + '!'
        raise ValueError(err_msg)
    self.accept = accept 
    
    # create a nested dictionary for the transition function
    self.transitions = {}
    for i in range(1, states+1):
      self.transitions[i] = {}
    # check input for given transition function
    if not isinstance(transitions, list):
      raise TypeError('Transitions table must be a dictionary in the format {"start": value, "input": value, "end": value!')
    for i in transitions:
      if not isinstance(i['start'], int) or not isinstance(i['end'], int):
        raise TypeError('Start and end point of each transition must be an integer!')
      elif i['start'] < 1 or i['start'] > states:
        err_msg = 'Start point of each transition must be a valid state (an integer between 1 and the number of states ' + str(states) + '), but the one at index ' + str(transitions.index(i)) + ' is ' + str(i['start']) + '!'
        raise ValueError(err_msg)
      elif i['end'] < 1 or i['end'] > states:
        err_msg = 'End point of each transition must be a valid state (an integer between 1 and the number of states ' + str(states) + '), but the one at index ' + str(transitions.index(i)) + ' is ' + str(i['end']) + '!'
        raise ValueError(err_msg)
      elif not isinstance(i['input'], str): 
        raise TypeError('Input for each transition must be a string!')
      elif len(i['input']) != 1:
        err_msg = 'Input for each transition must be a single character, but found \'' + i['input'] + '\' at index ' + str(transitions.index(i)) + '!'
        raise ValueError(err_msg)
      elif i['input'] not in alphabet:
        err_msg = 'Input for each transition must be element of the given alphabet, but found \'' + i['input'] + '\' at index ' + str(transitions.index(i)) + '!'
        raise ValueError(err_msg)
      self.transitions[i['start']][i['input']] = i['end']
    
    # check if given transition function is defined for each possible transition
    for i in range(1, states+1):
     if not self.transitions[i]:
       err_msg = 'Given transition function is not defined for each possible start point, ' + str(i) + ' is missing!'
       raise ValueError(err_msg)
     for j in self.alphabet:
       if not j in self.transitions[i]:
         err_msg = 'Given transition function is not defined for each possible input, δ(' + str(i) + ', \'' + str(j) + '\') is missing!'
         raise ValueError(err_msg)
         
    # create a dictionary that associates each tuple (s1, s2) of two states with all inputs that lead to a transitions from s1 to s2
    self.edge_map = {(i, j): [] for i in range(1, self.states+1) for j in range(1, self.states+1)}
    for i in self.transitions:
      for j in self.transitions[i]:
        self.edge_map[(i, self.transitions[i][j])].append(j)      
         
  def __str__(self):
    string_rep =  'DFA has ' + str(self.states) + ' states, with an alphabet of ' + str(self.alphabet) + '.'
    string_rep += '\nThe initial state is ' + str(self.initial) + ', while the accepting states are ' + str(self.accept) + '.'
    string_rep += '\nTransition function: \n\n'
    for i in self.transitions:
      for j in self.transitions[i]:
        string_rep += str(i) + ' --- ' + j + ' --> ' + str(self.transitions[i][j]) + '\n'
    return string_rep
    
  def is_accepted(self, input):
    # an automaton with no accepting states will only ever accept the empty language
    if len(self.accept) == 0:
      return input == ''
    # an automaton with all accepting states and an alphabet E will accept (x)*, where x is an alternation of all elements in E
    if len(self.accept) == self.states:
      return True
    current_state = self.initial 
    for c in input:
      try:
        current_state = self.transitions[current_state][c]
      except KeyError:
        err_msg = 'Given input contains character \'' + c + '\' that is not part of this automaton\'s alphabet!'
        raise ValueError(err_msg)
    return current_state in self.accept

  def visualize(self, file_name, colored_edges=None, step_start=-1, step_end=-1):
    # default colors and colors for start state, end state and involved transitions (if a step is visualized)
    bg_color = ['white' for i in range(0, self.states+1)]
    transition_color = {(x, y): 'black' for x in range(1, self.states+1) for y in range(1, self.states+1)}
    transition_width = {(x, y): '1.0' for x in range(1, self.states+1) for y in range(1, self.states+1)}
    transition_style = {(x, y): 'solid' for x in range(1, self.states+1) for y in range(1, self.states+1)}
    if colored_edges:
      for e in colored_edges[0]:
        transition_color[e] = 'blue'   
        transition_width[e] = '3.0'
        transition_style[e] = 'dashed'
      for f in colored_edges[1]:
        # used on both sides
        if f in colored_edges[0]:
          transition_color[f] = 'green'
          transition_style[f] = 'solid'
        else: 
          transition_color[f] = 'red'
          transition_style[f] = 'dashed'
        transition_width[f] = '3.0'
    if step_start >= 1 and step_end >= 1:
      # use a gradient if start and end state are equivalent, otherwise gray for start and yellow for end state
      (bg_color[step_start], bg_color[step_end]) = ('gray', 'yellow') if step_start != step_end else ('gray:yellow', 'gray:yellow')
    # create new graph representation with graphviz
    dot = gv.Digraph(name=file_name, format='png')
    # set layout direction (left to right)
    dot.graph_attr['rankdir'] = 'LR'
    dot.graph_attr['size'] = '16,8'
    dot.graph_attr['dpi'] = '100'
    # add phantom node for arrow into initial state
    dot.node('', '', shape='plaintext')
    # add states (mark accepting states with double circle)
    for i in range(1, self.states+1):
      if i not in self.accept:
        dot.node('z' + str(i), 'z' + str(i), shape='circle', style='filled', fillcolor=bg_color[i])
      else:
        dot.node('z' + str(i), 'z' + str(i), shape='doublecircle', style='filled', fillcolor=bg_color[i])
    # connect phantom node and initial node
    dot.edge('', 'z' + str(self.initial), label='')
    # iterate over edge map to create and label existing edges (i.e. no empty value for this tuple)
    for i in self.edge_map:
      if self.edge_map[i]: 
        # create a pretty label from the value list
        dot.edge('z' + str(i[0]), 'z' + str(i[1]), label=', '.join(self.edge_map[i]), color=transition_color[i], fontcolor=transition_color[i], penwidth = transition_width[i], style=transition_style[i])
    # render visualization
    return dot
    
  def to_regex(self):
    # create a 3d matrix to store our results in, format is r_table[k][i][j], initialized to 0 (representing the empty set)
    n = self.states+1
    r_table = [[[0 for k in range(n)] for j in range(n)] for i in range(n)]
    # create another matrix to store which transitions are relevant for each step (will be color-coded when the user chooses to look at this step)
    # t_table[k][i][j][0] contains transitions relevant for expression on the left side of alternation for this step
    # t_table[k][i][j][1] contains transitions relevant for expression on the right side of alternation for this step
    t_table = [[[[set() for x in range(2)] for k in range(n)] for j in range(n)] for i in range(n)]
    # initialize values for k=0
    for i in range(1, n):
      for j in range (1, n):
        if i == j:
          r_table[0][i][j] = re.Regex(re.NodeType.STRING, ['ε'])
        for a in self.alphabet:
          if a in self.edge_map[(i, j)]:
            # different construction for table entries with something in them and un-initialized ones
            if isinstance(r_table[0][i][j], int):
              r_table[0][i][j] = re.Regex(re.NodeType.STRING, [a])
            else:
              r_table[0][i][j] = re.Regex(re.NodeType.ALTERNATION, [r_table[0][i][j], re.Regex(re.NodeType.STRING, [a])])
            t_table[0][i][j][0].update([(i, j)])
    # fill table for values of k = 1, ..., n
    for k in range (1, n):
      for i in range (1, n):
        for j in range (1, n):
          left = copy.deepcopy(r_table[k-1][i][j])
          right_elements = []
          right_elements.append(copy.deepcopy(r_table[k-1][i][k]))
          right_elements.append(re.Regex(re.NodeType.KLEENE_STAR, [copy.deepcopy(r_table[k-1][k][k])]))
          right_elements.append(copy.deepcopy(r_table[k-1][k][j]))
          # again, some table entries may be still be un-initialized
          right_is_empty = any(map(lambda x: isinstance(x, int), right_elements))
          '''
          We can already do a bit of simplification during the construction of our term here, therefore saving on more time-intensive 
          operations later down the line. Depending on the current values of k, i and j, two or more of the subterms that constitute 
          this term can potentially be equal. As an example a(2,2,2) = a(1,2,2)|a(1,2,2)a(1,2,2)*a(1,2,2). 
          For the alternation w|xy*z between the left and right side, the following rules can be applied:
          - If w = x, w|xy*z is equal to w(y*z)?        (I)
          For the concatention xy*z on the right side, the following rules can be applied:
          - If x = y = z, xy*z is equal to xx+          (II)
          - If x = y, xy*z is equal to x+z              (III)
          - If y = z, xy*z is eqal to xy+               (IV)
          '''
          if isinstance(left, int) and right_is_empty:
            # both sides of the alternation un-initialized
            r_table[k][i][j] = 0
          elif isinstance(left, int):
            # left side un-initialized, alternation disappears, while concatenation on right side remains
            r_table[k][i][j] = re.Regex(re.NodeType.CONCATENATION, right_elements)
            t_table[k][i][j][0].update(t_table[k-1][i][j][0])
            t_table[k][i][j][0].update(t_table[k-1][i][j][1])
            t_table[k][i][j][1].update(t_table[k-1][i][k][0])
            t_table[k][i][j][1].update(t_table[k-1][i][k][1])
            t_table[k][i][j][1].update(t_table[k-1][k][k][0])
            t_table[k][i][j][1].update(t_table[k-1][k][k][1])
            t_table[k][i][j][1].update(t_table[k-1][k][j][0])
            t_table[k][i][j][1].update(t_table[k-1][k][j][1])
          elif right_is_empty:
            # same principle as above, but only the single term on the left side remains
            r_table[k][i][j] = left
            t_table[k][i][j][0].update(t_table[k-1][i][j][0])
            t_table[k][i][j][0].update(t_table[k-1][i][j][1])
          else:
            # everything initialized, we can proceed and check for equalities
            if (k-1, i, j) == (k-1, i, k):
              # indices equivalent to left == right_elements[0] (but without having to compare objects), apply rule I
              r_table[k][i][j] = re.Regex(re.NodeType.CONCATENATION, [right_elements[0], re.Regex(re.NodeType.MAYBE, [re.Regex(re.NodeType.CONCATENATION, right_elements[1:])])])
            elif (k-1, i, k) == (k-1, k, k) and (k-1, k, k) == (k-1, k, j):
              # indices equivalent to "all values on the right side equal", apply rule II
              right = re.Regex(re.NodeType.CONCATENATION, [right_elements[0], re.Regex(re.NodeType.KLEENE_PLUS, [right_elements[0]])])
              r_table[k][i][j] = re.Regex(re.NodeType.ALTERNATION, [left, right])
            elif (k-1, i, k) == (k-1, k, k):
              # indices equivalent to right_elements[0] == right_elements[1], apply rule III
              right = re.Regex(re.NodeType.CONCATENATION, [re.Regex(re.NodeType.KLEENE_PLUS, [right_elements[0]]), right_elements[2]])
              r_table[k][i][j] = re.Regex(re.NodeType.ALTERNATION, [left, right])
            elif (k-1, k, k) == (k-1, k, j):
              # indiced equivalent to right_elements[1] == right_elements[2], apply rule IV
              right = re.Regex(re.NodeType.CONCATENATION, [right_elements[0], re.Regex(re.NodeType.KLEENE_PLUS, [right_elements[1]])])
              r_table[k][i][j] = re.Regex(re.NodeType.ALTERNATION, [left, right])
            else:
              # no equalities, build table entry as normal
              right = re.Regex(re.NodeType.CONCATENATION, right_elements)
              r_table[k][i][j] = re.Regex(re.NodeType.ALTERNATION, [left, right])
            t_table[k][i][j][0].update(t_table[k-1][i][j][0])
            t_table[k][i][j][0].update(t_table[k-1][i][j][1])
            t_table[k][i][j][1].update(t_table[k-1][i][k][0])
            t_table[k][i][j][1].update(t_table[k-1][i][k][1])
            t_table[k][i][j][1].update(t_table[k-1][k][k][0])
            t_table[k][i][j][1].update(t_table[k-1][k][k][1])
            t_table[k][i][j][1].update(t_table[k-1][k][j][0])
            t_table[k][i][j][1].update(t_table[k-1][k][j][1])
          # simplify the resulting regex further
          if not isinstance(r_table[k][i][j], int):
            r_table[k][i][j] = re.simplify_regex(r_table[k][i][j])
            
    # return an alternation of all a(n, i, j) where n is the number of states, i is the initial state and j are all accepting states    
    candidates = [r_table[self.states][self.initial][j] for j in self.accept if not isinstance(r_table[self.states][self.initial][j], int)]
    if len(candidates) == 0:
      # no a(n, i, j) that isn't the empty language, so we return that
      return ('', r_table, t_table)
    elif len(candidates) == 1:
      # only one a(n, i, j) that isn't the empty language, no need for an alternation
      return (candidates[0], r_table, t_table)
    else:
      # construct alternation and return that
      return (re.Regex(re.NodeType.ALTERNATION, candidates), r_table, t_table)