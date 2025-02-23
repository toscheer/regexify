from flask import Flask, session, render_template, request, redirect, url_for
import json
import os
import secrets
import string
import shutil
import base64
import dfa
import re as reg

app = Flask(__name__)
  
# Set secret key
app.secret_key = 'MY_SECRET_KEY'

# Configure upload folder
UPLOAD_FOLDER = 'static/sessions'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# max upload size
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
  os.makedirs(UPLOAD_FOLDER)

# Allowed file extension
ALLOWED_EXTENSIONS = {'json'}

def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
  
def build_tree(no_of_states, initial_state, accepting_states):
  # build the tree structure that is later used to populate the tree view in the web app
  n = no_of_states+1
  # title at the very top (also used to go back to a non-colored graph)
  tree_struct = [{'text': 'DFA Graph'}]
  for i in range(1, n):
    for j in range(1, n):
      # populate top layer of the tree view 
      label = ints_to_tree_label(n-1, i, j)
      if i == initial_state and j in accepting_states:
        # if this is a step which makes up the resulting regex (k = states, i initial state, j in accepting states), make the text red
        node = {
                 'text': label,
                 'backColor': '#bbbbbb',
                 'nodes': []
               }
      else:
        node = {
                 'text': label,
                 'nodes': []
               }
      tree_struct.append(node)
  # recursively go through all of the nodes in the top layer and edit the 'nodes' field with the next deeper layer (as long as k >= 0)
  for e in tree_struct:
    if e['text'] != 'DFA Graph':
      append_tree_rec(e)
  return tree_struct

def append_tree_rec(node):
  # extract indices from parent's label
  (k, i, j) = tree_label_to_ints(node['text'])
  if k == 0:
    # base case, parent was already at the last step, nothing more to append
    return
  elif k == 1:
    # special case, the labels for k = 0 are leaves of the tree, so they don't need the nodes list for children
    node['nodes'].append({'text': ints_to_tree_label(k-1, i, j)})
    node['nodes'].append({'text': 'OR'})
    node['nodes'].append({'text': ints_to_tree_label(k-1, i, k)})
    node['nodes'].append({'text': ints_to_tree_label(k-1, k, k) + '*'})
    node['nodes'].append({'text': ints_to_tree_label(k-1, k, j)})
  else:
    # recursive case, add children and recursively call function on each of them
    node['nodes'].append({'text': ints_to_tree_label(k-1, i, j), 'nodes': []})
    node['nodes'].append({'text': 'OR'})
    node['nodes'].append({'text': ints_to_tree_label(k-1, i, k), 'nodes': []})
    node['nodes'].append({'text': ints_to_tree_label(k-1, k, k) + '*', 'nodes': []})
    node['nodes'].append({'text': ints_to_tree_label(k-1, k, j), 'nodes': []})
    for e in node['nodes']:
      if e['text'] != 'OR':
        append_tree_rec(e)
      
def ints_to_tree_label(k, i, j):
  # build a tree label in the form 'a(k, i, j)' from three indices k, i, j
  return 'a(' + ', '.join([str(k), str(i), str(j)]) + ')'
  
def tree_label_to_ints(label):
  # extract the three indices k, i, j from a tree label in the form 'a(k, i, j)'
  trunc = label[2:-1]
  # for labels ending in *, truncate one more char
  if trunc[-1] == ')':
    trunc = trunc[:-1]
  trunc = trunc.replace(',', '')
  trunc = trunc.split(' ')
  return (int(trunc[0]), int(trunc[1]), int(trunc[2]))
           
@app.route('/')
def index():
  # session management to differentiate new and returning users
  session.permanent = True
  # check if there already is an existing session cookie
  if not 'user_id' in session:
    # new user, give ID and create directory for their workspace (with an example DFA encoding)
    new_id = ''.join(secrets.choice(string.ascii_letters + string.digits) for x in range(8))
    session['user_id'] = new_id
    new_dir = './' + UPLOAD_FOLDER + '/' + new_id
    example_dir = './' + UPLOAD_FOLDER + '/example'
    files = os.listdir(example_dir)
    shutil.copytree(example_dir, new_dir)
    return redirect(url_for('user', id=new_id))
  else:
    # old user, redirect to appropriate url
    return redirect(url_for('user', id=session['user_id']))
    
@app.route('/user/<id>', methods=['GET', 'POST'])  
def user(id):
  dir = './' + UPLOAD_FOLDER + '/' + id + '/'
  # backup of previously loaded to render in case new input has an error (this is always either already verified or the example automaton)
  with open(dir + 'dfa_encoding.json', 'r') as fd:
    json_backup = json.load(fd)
  # build DFA from encoding, convert to regex and generate a visualization of the entire DFA
  backup_dfa = dfa.DFA(json_backup['states'], json_backup['alphabet'], json_backup['initial'], json_backup['accept'], json_backup['transitions'])
  (backup_total_regex, backup_regex_table, backup_step_table) = backup_dfa.to_regex()
  backup_visualized = backup_dfa.visualize('backup_visualization')
  backup_visualized_output = backup_visualized.pipe(format='png')
  backup_visualized_output = base64.b64encode(backup_visualized_output).decode('utf-8')
  backup_tree_data = build_tree(backup_dfa.states, backup_dfa.initial, backup_dfa.accept)
  # backup the file itself too (could otherwise be overwritten if the error only occurs after saving)
  shutil.copyfile(dir + 'dfa_encoding.json', dir + 'backup_dfa_encoding.json')
  if request.method == 'POST':
    # if the request method was POST, a new file was uploaded and must be verified
    if 'file' not in request.files:
      return render_template('application.html', error='No file uploaded!', id=id, regex=backup_total_regex, visualized_output=backup_visualized_output, tree_data=backup_tree_data)
    file = request.files['file']
    if file.filename == '':
      return render_template('application.html', error='No file selected!', id=id, regex=backup_total_regex, visualized_output=backup_visualized_output, tree_data=backup_tree_data)
    if file and allowed_file(file.filename):
      file.save(dir + 'dfa_encoding.json')
    else:
      return render_template('application.html', error='That type of file is not allowed!', id=id, regex=backup_total_regex, visualized_output=backup_visualized_output, tree_data=backup_tree_data)
  try:
    with open(dir + 'dfa_encoding.json', 'r') as f:
      json_data = json.load(f)
    # build DFA from encoding, convert to regex and generate a visualization of the entire DFA
    current_dfa = dfa.DFA(json_data['states'], json_data['alphabet'], json_data['initial'], json_data['accept'], json_data['transitions'])
    (total_regex, regex_table, step_table) = current_dfa.to_regex()
    visualized = current_dfa.visualize('current_visualization')
    visualized_output = visualized.pipe(format='png')
    visualized_output = base64.b64encode(visualized_output).decode('utf-8')
    os.remove(dir + 'backup_dfa_encoding.json')
    tree_data = build_tree(current_dfa.states, current_dfa.initial, current_dfa.accept)
    # everything okay, delete backup file and render site with visualization of the entire DFA and regex
    return render_template('application.html', id=id, regex=total_regex, visualized_output=visualized_output, tree_data=tree_data)
  except json.JSONDecodeError:
    # error while decoding, restore previously loaded from backup and render site with error
    shutil.copyfile(dir + 'backup_dfa_encoding.json', dir + 'dfa_encoding.json')
    return render_template('application.html', error='Invalid JSON file!', id=id, regex=backup_total_regex, visualized_output=backup_visualized_output, tree_data=backup_tree_data)
  except Exception as e:
    # json file does not comply with the necessary format, restore previously loaded from backup and render site with error
    shutil.copyfile(dir + 'backup_dfa_encoding.json', dir + 'dfa_encoding.json')
    return render_template('application.html', error=f'DFA not correctly encoded: {str(e)}', id=id, regex=backup_total_regex, visualized_output=backup_visualized_output, tree_data=backup_tree_data)
    
@app.route('/swap', methods=['POST'])
def swap():
  # route for async requests if something in the tree view was clicked
  data = request.get_json()
  dir = './' + UPLOAD_FOLDER + '/' + data['id'] + '/'
  label = data['label']
  with open(dir + 'dfa_encoding.json', 'r') as f:
    json_data = json.load(f)
  current_dfa = dfa.DFA(json_data['states'], json_data['alphabet'], json_data['initial'], json_data['accept'], json_data['transitions'])
  (total_regex, regex_table, step_table) = current_dfa.to_regex()
  if label == 'DFA Graph':
    # base label was clicked - go back to graph for the entire DFA with no steps colored in
    visualized = current_dfa.visualize('current_visualization')
    visualized_output = visualized.pipe(format='png')
    visualized_output = base64.b64encode(visualized_output).decode('utf-8')
    # case differentiation in case of empty set
    regex_output = 'Ø' if isinstance(total_regex, int) else str(total_regex)
    return {'regex': regex_output, 'img': visualized_output}
  else: 
    # a certain step was clicked, extract indices from label and generate image and regex corresponding to that step
    (k, i, j) = tree_label_to_ints(label)
    visualized = current_dfa.visualize('current_visualization', step_table[k][i][j], i, j)
    visualized_output = visualized.pipe(format='png')
    visualized_output = base64.b64encode(visualized_output).decode('utf-8')
    # case differentiation in case of empty set
    regex_output = 'Ø' if isinstance(regex_table[k][i][j], int) else str(regex_table[k][i][j])
    return {'regex': regex_output, 'img': visualized_output}
    
@app.route('/sanity', methods=['POST'])
def sanity():
  # route for async requests to sanity check an input against both automaton and regex
  data = request.get_json()
  dir = './' + UPLOAD_FOLDER + '/' + data['id'] + '/'
  to_check = data['input']
  with open(dir + 'dfa_encoding.json', 'r') as f:
    json_data = json.load(f)
  current_dfa = dfa.DFA(json_data['states'], json_data['alphabet'], json_data['initial'], json_data['accept'], json_data['transitions'])
  (total_regex, regex_table, step_table) = current_dfa.to_regex()
  # check against automaton, throw error message if input does not match the automaton's alphabet
  try:
    automaton_match = current_dfa.is_accepted(to_check)
  except ValueError as e:
    return {'message': str(e)}
  regex_match = reg.fullmatch(str(total_regex), to_check)
  automaton_result = '\'' + to_check + '\' ' + ('not ' if not automaton_match else '') + 'accepted by current DFA!'
  regex_result = '\'' + to_check + '\' ' + ('not ' if not automaton_match else '') + 'accepted by current RegEx!'
  return {'message': automaton_result + '\n' + regex_result}

if __name__ == '__main__':
    app.run(debug=True)