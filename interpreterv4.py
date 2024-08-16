import copy
from brewparse import parse_program
from intbase import ErrorType, InterpreterBase
from type_valuev1 import Type, Value, create_value, get_printable

class Interpreter(InterpreterBase):
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    LAMBDA_NODE = 0
    CAPTURED_VARS = 1

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp) # call InterpreterBase's constructor
        self.trace_output = trace_output

    def run(self, program):
        ast = parse_program(program)
        self.ast = ast
        print(self.ast)
        self.get_debug_info(ast)
        main_node = self.get_main_node(ast) 
        self.variable_scope_list = [{}]
        self.variable_alias_list = [{}]
        self.run_func(main_node)
        
    def get_main_node(self, ast):
        functions_list = ast.dict['functions']
        if functions_list:
            for elem in functions_list:
                if elem.dict['name'] == 'main':
                    return elem
        super().error(
            ErrorType.NAME_ERROR,
            "No main() function was found",
        )

    # basically same as run_func but return_value default is NONE    
    def run_if_statements(self, func_node):
        statements = func_node.dict.get('statements') # list of Statement nodes         
        return_value = None

        for statement_node in statements:
            temp_return_val = self.run_statement(statement_node)
            if temp_return_val is not None:
                return_value = temp_return_val
                break

        # delete outermost scope once function is done executing
        self.variable_scope_list.pop()
        return return_value

    def run_func(self, func_node, lambda_node = None):
        statements = func_node.dict.get('statements') # list of Statement nodes         
        return_value = Interpreter.NIL_VALUE

        # if it cant find a varirable, then iterate through the
        # captured variables and if it is a lambda, then look through ITST captured
        # variables

        for statement_node in statements:
            print("statement node")
            print(statement_node)
            temp_return_val = self.run_statement(statement_node, lambda_node)            
            if temp_return_val is not None:
                return_value = temp_return_val
                break

        # delete outermost scope once function is done executing
        self.variable_scope_list.pop()
        self.variable_alias_list.pop()
        return return_value

    def run_statement(self, statement_node, lambda_node = None):
        if statement_node.elem_type == "=":
            self.do_assignment(statement_node, lambda_node)
        elif statement_node.elem_type == "fcall" or statement_node.elem_type == "mcall":
            self.do_func_call(statement_node, lambda_node) 
        elif statement_node.elem_type == 'return':       
            source_node = statement_node.dict['expression']
            if source_node is None:
                return Interpreter.NIL_VALUE
            else:
                return copy.deepcopy(self.evaluate_expression(source_node, lambda_node))

        elif statement_node.elem_type == "if":
            condition = self.evaluate_expression(statement_node.dict['condition'])

            if condition.type() == Type.INT:
                condition = Value(Type.BOOL, self.get_bool_from_int(condition.v))

            elif condition.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "If condition does not evaluate to a boolean",
                )

            # call run_func with statements or else_statements
            if condition.v: # true
                # new scope for block
                self.variable_scope_list.append({})
                self.variable_alias_list.append({})
                return self.run_if_statements(statement_node) # this should pop outermost scope...
            elif statement_node.dict['else_statements'] is not None:
                # duplicate this statement node,
                # but make its 'statements' field what 'else_statements' contains
                # this is for easy compatibility with the run_func function (although, it is kinda hacky)
                
                # new scope for block
                self.variable_scope_list.append({})
                self.variable_alias_list.append({})
                updated_statement_node = copy.deepcopy(statement_node)
                updated_statement_node.dict['statements'] = statement_node.dict['else_statements']
                return self.run_if_statements(updated_statement_node)
        elif statement_node.elem_type == "while":
             # while the condition is true
                # run the statements (Call run_func)
                # if statement has a return value,
                # then return was called within the loop
                # that means we want to break out of our loop
                # and return whatever that value was
            condition = self.evaluate_expression(statement_node.dict['condition'])
            if condition.type() == Type.INT:
                condition = Value(Type.BOOL, self.get_bool_from_int(condition.v))

            elif condition.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "If condition does not evaluate to a boolean",
                )
         
            return_value = None

            while (condition.v):
                # new scope for block
                self.variable_scope_list.append({})
                self.variable_alias_list.append({})


                for statement in statement_node.get('statements'):
                    temp_return_val = self.run_statement(statement)
                    if temp_return_val is not None:
                        return_value = temp_return_val
                        break # from for loop
                
                if return_value is not None:
                    self.variable_scope_list.pop()
                    return return_value
                
                # delete outermost scope once loop iteration is done
                self.variable_scope_list.pop()

                # update condition and verify still evaluates to bool
                # (it could not evaluate to bool if, for instance, it uses a var whose type gets changed)
                condition = self.evaluate_expression(statement_node.dict['condition'])

                if condition.type() == Type.INT:
                    condition = Value(Type.BOOL, self.get_bool_from_int(condition.v))
                elif condition.type() != Type.BOOL:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "While condition does not evaluate to a boolean",
                    )


        return None

    def do_assignment(self, statement_node, lambda_node = None):
        target_var_name = statement_node.dict['name']
        print("target var name")
        print(target_var_name)


        source_node = statement_node.dict['expression']
        print("source node")
        print(source_node)

    
        resulting_value = self.evaluate_expression(source_node, lambda_node)
        print("resulting val")
        print(resulting_value)

        # if lambda value
        # then update value in the actual lambda
        if lambda_node is not None:
            captured_vars_dict = lambda_node[Interpreter.CAPTURED_VARS]
            if target_var_name in captured_vars_dict:
                captured_vars_dict[target_var_name] = resulting_value

                # if this is an object or lambda type
                # then i want to update the actual value too
                # this should have worked...?

                return
                
        # if the target var name has a . then we know it's an object
        # so instead of assigning this value to a name in the scope dict
        # we are going to find that object name (e.g. person)
        # and add the value to that object's dictionary

        # get obj name (before .)
        # get obj field/method (after .)
        if '.' in target_var_name:
            split_names = target_var_name.split('.')
            obj_name = split_names[0]
            field_name = split_names[1]

            # if assigning proto, make sure it's an object type
            if field_name == 'proto' and (resulting_value.type() != Type.OBJ and resulting_value.type() != Type.NIL):
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Can't set proto to non-object or non-nil type",
                )
                    
            closest_scope_index = self.validate_var_name(obj_name)
            if closest_scope_index is None:
                # attempting to assign value to obj that hasn't been created!
                super().error(
                    ErrorType.NAME_ERROR,
                    "Object not found",
                )
            else:
                if (self.variable_scope_list[closest_scope_index][obj_name].type() != Type.OBJ):
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Attempting to get field/method from non-object type",
                    )
                
                self.variable_scope_list[closest_scope_index][obj_name].v[field_name] = resulting_value
                
                # if this is obj references another obj, then we want to update that obj too...
                
                return

        # check all scopes to see if variable exists
        # if it already does, update that value
        # otherwise, insert into outermost scope
        closest_scope_index = None
        # iterate through scopes to see if variable name exists
        for i in range(len(self.variable_scope_list)-1, -1, -1):
            curr_scope_dict = self.variable_scope_list[i]
            if target_var_name in curr_scope_dict:
                closest_scope_index = i
                break

        # insert into outermost scope
        if closest_scope_index is None:
            self.variable_scope_list[len(self.variable_scope_list)-1][target_var_name] = resulting_value
        # insert into relevant scope
        else:
            self.variable_scope_list[closest_scope_index][target_var_name] = resulting_value
            # if pass by reference, update referenced value(s) too
            # (cascading up in event of nested references)
            while target_var_name in self.variable_alias_list[closest_scope_index]:
                ref_var_name = self.variable_alias_list[closest_scope_index][target_var_name]
                self.variable_scope_list[closest_scope_index-1][ref_var_name] = resulting_value

                closest_scope_index -= 1
                target_var_name = ref_var_name

    def is_binary_op(self, node_elem_type):
        if node_elem_type == '+' or node_elem_type == '-' or node_elem_type == '*' or node_elem_type == '/' or node_elem_type == '<' or node_elem_type == '<=' or node_elem_type == '>' or node_elem_type == '>=':
            return True
        return False
    
    def get_bool_value(self, bool):
        if bool:
            return create_value("true")
        return create_value("false")
    
    def get_bool_from_int(self, int_val):
        if int_val != 0:
            return True
        return False

    def get_int_from_bool(self, bool_val):
        if bool_val:
            return 1
        return 0

    def evaluate_expression(self, source_node, lambda_node = None):
        # object node
        if source_node.elem_type == '@':
            obj_fields = {}
            return Value(Type.OBJ, obj_fields)

        # VALUE NODES
        if source_node.elem_type == 'int' or source_node.elem_type == 'string':
            # weird edge case
            # if it's a string and val == true or false
            # create_value will assign it to bool
            # so this handles that
            if source_node.elem_type == 'string' and (source_node.dict['val'] == 'true' or source_node.dict['val'] == 'false'):
                return Value(Type.STRING, source_node.dict['val'])
            # also with nil
            if source_node.elem_type == 'string' and source_node.dict['val'] == 'nil':
                 return Value(Type.STRING, source_node.dict['val'])
            
            return create_value(source_node.dict['val'])
        elif source_node.elem_type == 'bool':
            return self.get_bool_value(source_node.dict['val'])
        elif source_node.elem_type == 'nil':
            return create_value('nil')

        # VARIABLE NODE
        elif source_node.elem_type == 'var':
            var_name = source_node.dict['name']

            # see if lambda node
            # this is supposed to be recognized as lambda!
            if lambda_node is not None:
                print("LAMBDA RECOGNIZED IN EVAL EXPRESS")
                # this should return the value from the lambda node dict
                captured_vars_dict = lambda_node[Interpreter.CAPTURED_VARS]
                for key, value in captured_vars_dict.items(): # name : value
                    if var_name == key:
                        return value
                    if value.type() == Type.LAMBDA:
                        lambda_dict = value.v[Interpreter.CAPTURED_VARS]
                        for key2, value2 in lambda_dict.items():
                            if var_name == key2:
                                return value2


                # if var_name in captured_vars_dict:
                #     return captured_vars_dict[var_name]
                   
            # see if it is a function name
            functions_list = self.ast.dict['functions']
            if functions_list:
                func_match_count = 0 # ONLY IF IT EQUALS ONE, set equal to func name
                matched_elem = None
                for elem in functions_list:
                    if elem.dict['name'] == var_name:
                        func_match_count += 1
                        matched_elem = elem

                if func_match_count == 1 and matched_elem is not None:
                    return Value(Type.FUNC, matched_elem) # matched_elem = statement node
                elif func_match_count > 1:
                    super().error(
                        ErrorType.NAME_ERROR,
                        f"Function {var_name} has been overloaded, so it can't be assigned to a variable",
                    )

            # check if object variable
            # instead of getting the value in the variable scope list
            # get it from the object dict
            if '.' in var_name:
                split_names = var_name.split('.')
                obj_name = split_names[0]
                field_name = split_names[1]
        
                closest_scope_index = self.validate_var_name(obj_name)
                if closest_scope_index is None:
                    # attempting to get value from obj that hasn't been created!
                    super().error(
                        ErrorType.NAME_ERROR,
                        "Object not found",
                    )
                else:
                    if (self.variable_scope_list[closest_scope_index][obj_name].type() != Type.OBJ):
                            super().error(
                                ErrorType.TYPE_ERROR,
                                "Attempting to get field/method from non-object type",
                            )

                    obj_fields_dict = self.variable_scope_list[closest_scope_index][obj_name].v
                    if field_name in obj_fields_dict:
                        return obj_fields_dict[field_name]
                    else:
                        # iterate through proto fields to see if the field ever exists
                        while (True):
                            if 'proto' in obj_fields_dict:
                                obj = obj_fields_dict['proto']

                                if (obj.type() != Type.OBJ):
                                    break

                                obj_fields_dict = obj.v
                                if field_name in obj_fields_dict:
                                    return obj_fields_dict[field_name]
                            else:
                                break

                        # attempting to get value that does not exist on this object
                        super().error(
                            ErrorType.NAME_ERROR,
                            "Field does not exist on this object",
                        )

            # otherwise, check if variable
            scope_index = self.validate_var_name(var_name)
            if scope_index is not None:
                # if this is a reference var, make sure it's up to date, then return it
                if var_name in self.variable_alias_list[scope_index]:
                    # bottom-up approach doesnt work because at the lower level 
                    # we cant tell if two variables reference the same upper var
                    # ex: if a and b reference d and e, but d and e both references f,
                    # we can't know
                    # so we have to take a top-down approach, seeing which ultimate variable
                    # is updated, and then cascading the changes downwards

                    ref_var_name = self.variable_alias_list[scope_index][var_name]

                    # get top_most_var
                    top_most_var_name = var_name
                    search_scope_index = scope_index
                    while top_most_var_name in self.variable_alias_list[search_scope_index]:
                        top_most_var_name = self.variable_alias_list[search_scope_index][top_most_var_name]
                        search_scope_index -= 1

                    # now cascade the changes down
                    scope_index_update_ref = search_scope_index + 1 # starts low, goes high
                    try:
                        new_value = self.variable_scope_list[search_scope_index][top_most_var_name]
                    except:
                        return self.variable_scope_list[scope_index][var_name]
                        
                    referenced_var_names = [top_most_var_name]
                    while scope_index_update_ref < len(self.variable_scope_list):
                        new_referenced_var_names = []
                        for key, val in self.variable_alias_list[scope_index_update_ref].items():
                            if val in referenced_var_names:
                                self.variable_scope_list[scope_index_update_ref][key] = new_value # deep copy or no?
                                new_referenced_var_names.append(key)
                        referenced_var_names = new_referenced_var_names
                        scope_index_update_ref += 1
                            
                        # if there are any vars that reference referenced_var_names
                        # then update their values
                        # and update referenced_var_names to be the vars we just updated
                        # and then increment scope_index
                        
                    self.variable_scope_list[scope_index][var_name] = self.variable_scope_list[scope_index-1][ref_var_name]
                    return self.variable_scope_list[scope_index][var_name]
                
                return self.variable_scope_list[scope_index][var_name]
        
        # EXPRESSION NODE - BINARY/COMPARISON OP FOR INTS (or string)
        elif self.is_binary_op(source_node.elem_type):
            op1_val = self.evaluate_expression(source_node.dict['op1'], lambda_node)
            op2_val = self.evaluate_expression(source_node.dict['op2'], lambda_node)
   
            # string concat
            if (source_node.elem_type == '+' and op1_val.type() == Type.STRING and op2_val.type() == Type.STRING):
                return create_value(op1_val.v + op2_val.v)

            if (op1_val.type() == Type.BOOL):
                op1_val = Value(Type.INT, self.get_int_from_bool(op1_val.v))
            if (op2_val.type() == Type.BOOL):
                op2_val = Value(Type.INT, self.get_int_from_bool(op2_val.v))

            if (op1_val.type() != Type.INT or op2_val.type() != Type.INT):
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible types for arithmetic operation",
                )
            
            if source_node.elem_type == '+':
                return create_value(op1_val.v + op2_val.v)
            elif source_node.elem_type == '-':
                return create_value(op1_val.v - op2_val.v)
            elif source_node.elem_type == '*':
                return create_value(op1_val.v * op2_val.v)
            elif source_node.elem_type == '/':
                return create_value(op1_val.v // op2_val.v)
            elif source_node.elem_type == '<':
                return self.get_bool_value(op1_val.v < op2_val.v)
            elif source_node.elem_type == '<=':
                return self.get_bool_value(op1_val.v <= op2_val.v)
            elif source_node.elem_type == '>':
                return self.get_bool_value(op1_val.v > op2_val.v)
            elif source_node.elem_type == '>=':
                return self.get_bool_value(op1_val.v >= op2_val.v)

        # ARITHMETIC NEGATION
        elif source_node.elem_type == 'neg':
            op1_val = self.evaluate_expression(source_node.dict['op1'], lambda_node)

            if (op1_val.type() != Type.INT):
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for arithmetic negation",
                )

            return create_value(op1_val.v * (-1))
        
        # BOOL BINARY OPS
        elif source_node.elem_type == '&&' or source_node.elem_type == '||':
            op1_val = self.evaluate_expression(source_node.dict['op1'], lambda_node)
            op2_val = self.evaluate_expression(source_node.dict['op2'], lambda_node)

            if (op1_val.type() == Type.INT):
                op1_val = Value(Type.BOOL, self.get_bool_from_int(op1_val.v))
            if (op2_val.type() == Type.INT):
                op2_val = Value(Type.BOOL, self.get_bool_from_int(op2_val.v))

            if (op1_val.type() != Type.BOOL or op2_val.type() != Type.BOOL):
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible types for boolean operation",
                )

            if source_node.elem_type == '&&':
                return self.get_bool_value(op1_val.v and op2_val.v)            
            elif source_node.elem_type == '||':
                return self.get_bool_value(op1_val.v or op2_val.v)

        # BOOL NEGATION
        elif source_node.elem_type == '!':
            op1_val = self.evaluate_expression(source_node.dict['op1'], lambda_node)

            if (op1_val.type() == Type.INT):
                op1_val = Value(Type.BOOL, self.get_bool_from_int(op1_val.v))
                
            if (op1_val.type() != Type.BOOL):
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for boolean negation",
                )

            return self.get_bool_value(not op1_val.v)

        # COMP OPERATORS
        elif source_node.elem_type == '==' or source_node.elem_type == '!=':
            op1_val = self.evaluate_expression(source_node.dict['op1'], lambda_node)
            op2_val = self.evaluate_expression(source_node.dict['op2'], lambda_node)

            if op1_val.type() == Type.LAMBDA and op2_val.type() == Type.LAMBDA:
                if source_node.elem_type == '==':
                    return self.get_bool_value(op1_val is op2_val)
                elif source_node.elem_type == '!=':
                    return self.get_bool_value(op1_val is not op2_val)
                
            if op1_val.type() == Type.OBJ and op2_val.type() == Type.OBJ:
                if source_node.elem_type == '==':
                    return self.get_bool_value(op1_val is op2_val)
                elif source_node.elem_type == '!=':
                    return self.get_bool_value(op1_val is not op2_val)
            
            if ((op1_val.type() == Type.STRING and op2_val.type() == Type.STRING) or (op1_val.type() == Type.INT and op2_val.type() == Type.INT) or (op1_val.type() == Type.BOOL and op2_val.type() == Type.BOOL)):
                if source_node.elem_type == '==':
                    return self.get_bool_value(op1_val.v == op2_val.v)
                elif source_node.elem_type == '!=':
                    return self.get_bool_value(op1_val.v != op2_val.v)
                
            elif (op1_val.type() == Type.BOOL and op2_val.type() == Type.INT) or (op1_val.type() == Type.INT and op2_val.type() == Type.BOOL):
                if op1_val.type() == Type.INT:
                    op1_bool = self.get_bool_from_int(op1_val.v)
                    if source_node.elem_type == '==':
                        return self.get_bool_value(op1_bool == op2_val.v)
                    elif source_node.elem_type == '!=':
                        return self.get_bool_value(op1_bool != op2_val.v)
                    
                if op2_val.type() == Type.INT:
                    op2_bool = self.get_bool_from_int(op2_val.v)
                    if source_node.elem_type == '==':
                        return self.get_bool_value(op1_val.v == op2_bool)
                    elif source_node.elem_type == '!=':
                        return self.get_bool_value(op1_val.v != op2_bool)

            elif op1_val.type() == Type.NIL and op2_val.type() == Type.NIL:
                if source_node.elem_type == '==':
                    return self.get_bool_value(True)
                elif source_node.elem_type == '!=':
                    return self.get_bool_value(False)
                
            elif op1_val.type() == Type.FUNC and op2_val.type() == Type.FUNC:
                if source_node.elem_type == '==':
                    return self.get_bool_value(op1_val.v is op2_val.v)
                elif source_node.elem_type == '!=':
                    return self.get_bool_value(op1_val.v is not op2_val.v)
            else: 
                if source_node.elem_type == '==':
                    return self.get_bool_value(False)
                elif source_node.elem_type == '!=':
                    return self.get_bool_value(True)
    
        # EXPRESSION NODE - inputi
        elif ('name' in source_node.dict and source_node.dict['name'] == 'inputi'):
            args = source_node.dict['args']
            if args:
                # can't have more than one param to inputi
                if len(args) > 1:
                    super().error(
                    ErrorType.NAME_ERROR,
                    f"inputi() function found that takes > 1 parameter",
                    )
                arg_value = self.evaluate_expression(source_node.dict['args'][0], lambda_node)
                print("REAL OUTPUT v v v")
                super().output(get_printable(arg_value)) 
        
            user_input = super().get_input()
            if not user_input.isdigit():
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Input was not integer",
                )
            return create_value(int(user_input))

        # EXPRESSION NODE - inputs
        elif ('name' in source_node.dict and source_node.dict['name'] == 'inputs'):
            args = source_node.dict['args']
            if args:
                # can't have more than one param to inputi
                if len(args) > 1:
                    super().error(
                    ErrorType.NAME_ERROR,
                    f"inputs() function found that takes > 1 parameter",
                    )
                arg_value = self.evaluate_expression(source_node.dict['args'][0], lambda_node)
                print("REAL OUTPUT v v v")
                super().output(get_printable(arg_value))
        
            user_input = super().get_input()
            return create_value(user_input)
        
        # USER-DEFINED FUNCTION
        elif source_node.elem_type == 'fcall':
            return_value = self.do_func_call(source_node)
            return return_value
        
        # FUNCTION FROM OBJ
        elif source_node.elem_type == 'mcall':
            return_value = self.do_func_call(source_node)
            return return_value

        elif source_node.elem_type == 'lambda':
            # get list of formal param var names
            formal_param_name_list = []
            for arg in source_node.dict['args']:
                formal_param_name_list.append(arg.get('name'))

            # get list of all var names
            
            # source_node_string = str(source_node)

            # print("SOURCE NODE STRING HERE v v v ")
            # print(source_node_string)

            # * copy all vars in scope that aren't formal param
            captured_vars = {}
            # all variables in scope need to be captured
            for i in range(len(self.variable_scope_list)-1, -1, -1):
                curr_scope_dict = self.variable_scope_list[i]
                for key, value in curr_scope_dict.items():
                    if key not in formal_param_name_list:
                        # if object or lambda
                        # then do not capture
                        # (which effectively captures by reference)
                        if value.type() != Type.OBJ and value.type() != Type.LAMBDA:
                            captured_vars[key] = copy.deepcopy(value)
                        # else:
                        #     captured_vars[key] = copy.deepcopy(value)
                    

           

            # index_list = list(self.find_var_indices(source_node_string, '[var: name: '))
            # variable_name_list = []
            
            # for index in index_list:
            #     name = ""
            #     inner_index = index + 12
            #     while source_node_string[inner_index] != ']':
            #         name += source_node_string[inner_index]
            #         inner_index += 1

            #     # IF IT IS VISIBLE in the program then it needs to be captured...
            #     # e.g. in this scope or any of the others

                # scope_index = self.validate_var_name(name, True)
            #     if scope_index is not None:
            #         variable_name_list.append(name)

            # also need to add the names of function calls that are NOT
            # in the functions list (and not formal param). these are lambdas which need to be captured
            # index_list = list(self.find_var_indices(source_node_string, '[fcall: name: '))
            # for index in index_list:
            #     name = ""
            #     inner_index = index + 14
            #     while source_node_string[inner_index] != ',':
            #         name += source_node_string[inner_index]
            #         inner_index += 1

            #     if name not in formal_param_name_list and name not in self.ast.dict['functions'] and name != 'print':
            #         variable_name_list.append(name)

            # print("variable name list")
            # print(variable_name_list)
            # print("formal param name list")
            # print(formal_param_name_list)

            # if there's a var that does not match formal parameters 
            # then it must be captured
            # -> go through scopes and get its value
            # DEEP COPY its value and insert into the dict
            # captured_vars = {} # var name : curr var value
            # for var_name in variable_name_list:
            #     if var_name not in formal_param_name_list:
            #         scope_index = self.validate_var_name(var_name, True)
            #         if scope_index is not None:
            #             captured_value = self.variable_scope_list[scope_index][var_name]
            #             captured_vars[var_name] = copy.deepcopy(captured_value)

            print(captured_vars)
            final_lambda_struct = [source_node, captured_vars]
            return Value(Type.LAMBDA, final_lambda_struct)
            # Value(Type.LAMBDA, [lambda_node, {var_names : curr_var_values}])

           

            # the only values that can be captured are ones that are not in the formal params
            # the captured val must be a deep-copy



        super().error(
                ErrorType.NAME_ERROR,
                f"Expression is invalid",
            )
         
    # inspired by https://stackoverflow.com/questions/4664850/how-to-find-all-occurrences-of-a-substring
    def find_var_indices(self, statement_node_str, substr):
        start = 0
        while True:
            start = statement_node_str.find(substr, start)
            if start == -1: return
            yield start
            start += len(substr) # use start += 1 to find overlapping matches

    # calls error if variable name does not exist, returns index scope if does exist
    # when called with gentle = True, it does not throw error when var not defined
    def validate_var_name(self, var_name, gentle=False):
        # iterate through scopes to see if variable name exists
        for i in range(len(self.variable_scope_list)-1, -1, -1):
            curr_scope_dict = self.variable_scope_list[i]
            if var_name in curr_scope_dict:
                return i
            
        if not gentle:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {var_name} has not been defined",
            )
        return None
        
  
    def do_func_call(self, statement_node, outer_lambda_node = None):
        if statement_node.dict['name'] == 'print':
            final_output = ""
            for arg in statement_node.dict['args']:
                arg_value = self.evaluate_expression(arg, outer_lambda_node)
                # trying to print a lambda node!
                # after --- 2
                final_output += get_printable(arg_value)
            print("REAL OUTPUT v v v")
            super().output(final_output)
            return Interpreter.NIL_VALUE
        
        # if the statement node name matches a function name in the ast, then it is defined
        function_elem = None
        functions_list = self.ast.dict['functions']
        if functions_list:
            for elem in functions_list:
                # if function name is same AND num of args is same
                if elem.dict['name'] == statement_node.dict['name'] and len(elem.dict['args']) == len(statement_node.dict['args']):
                    function_elem = elem

        lambda_node = None # INNER lambda node
       

        object =  None

        # if it's mcall
        if statement_node.elem_type == "mcall":
            # get the function/lambda that it references and set it equal to function_elem
            # then, when processing function_elem later, make sure it has the objref in the "this" variable
            # and the proper values passed into the args
            print("statement node 123")
            print(statement_node)
            print(statement_node.dict['objref'])
            print(statement_node.dict['name'])
            obj_name = statement_node.dict['objref']
            method_name = statement_node.dict['name']
            scope_index = self.validate_var_name(obj_name)

            if scope_index is not None:
                var_value = None
                object = self.variable_scope_list[scope_index][obj_name]
                if object.type() != Type.OBJ:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Trying to call method on non-object",
                    )

                # INSPO for altering below

                # obj_fields_dict = self.variable_scope_list[closest_scope_index][obj_name].v
                #     if field_name in obj_fields_dict:
                #         return obj_fields_dict[field_name]
                #     else:
                #         # iterate through proto fields to see if the field ever exists
                #         while (True):
                #             if 'proto' in obj_fields_dict:
                #                 obj = obj_fields_dict['proto']
                #                 obj_fields_dict = obj.v
                #                 if field_name in obj_fields_dict:
                #                     return obj_fields_dict[field_name]
                #             else:
                #                 break

                #         # attempting to get value that does not exist on this object
                #         super().error(
                #             ErrorType.NAME_ERROR,
                #             "Field does not exist on this object",
                #         )

                obj_fields_dict = self.variable_scope_list[scope_index][obj_name].v
                if method_name in obj_fields_dict:
                    var_value = obj_fields_dict[method_name]
                else:
                    # iterate through proto fields to see if the field ever exists
                    failed_to_find_method = False
                    while (True):
                        if 'proto' in obj_fields_dict:
                            obj = obj_fields_dict['proto']
                            if (obj.type() != Type.OBJ):
                                failed_to_find_method = True
                                break
                            obj_fields_dict = obj.v
                            if method_name in obj_fields_dict:
                                var_value = obj_fields_dict[method_name]
                                break
                        else:
                            failed_to_find_method = True
                            break

                    if failed_to_find_method:
                        # attempting to get value that does not exist on this object
                        super().error(
                            ErrorType.NAME_ERROR,
                            "Method does not exist on this object",
                        )

                # try:
                #     var_value = self.variable_scope_list[scope_index][obj_name].v[method_name]
                # except:
                #     # attempting to get value that does not exist on this object
                #     super().error(
                #         ErrorType.NAME_ERROR,
                #         "Method does not exist on this object",
                #     )

                if var_value.t == Type.FUNC:
                    updated_statement_node = var_value.v
                    # get new function elem
                    if functions_list:
                        for elem in functions_list:
                            if elem.dict['name'] == updated_statement_node.dict['name']:
                                if len(elem.dict['args']) != len(statement_node.dict['args']):
                                    super().error(
                                        ErrorType.TYPE_ERROR,
                                        "Invalid number of args passed into function",
                                    )
                                else:
                                    function_elem = elem


                # variable referring to an object is passed by reference
                # e.g. obj.name 
                # need to do special implementation for when lambdas originally capture variables
                # and then update here ******
                
                # elif outer_lambda_node is not None and var_value.t == Type.LAMBDA and statement_node.dict['name'] in outer_lambda_node[Interpreter.CAPTURED_VARS]:
                #     captured_vars_dict = outer_lambda_node[Interpreter.CAPTURED_VARS]
                #     lambda_var_name = statement_node.dict['name']
               
                #     lambda_node = captured_vars_dict[lambda_var_name]
                #     function_elem = lambda_node.v[Interpreter.LAMBDA_NODE]
                elif var_value.t == Type.LAMBDA:
                    
                    function_elem = var_value.v[Interpreter.LAMBDA_NODE]
                    lambda_node = var_value.v
                    print("HERE123")
                    print("statement node")
                    print(statement_node)

                    if object is not None and len(function_elem.dict['args']) != len(statement_node.dict['args']):
                        super().error(
                            ErrorType.NAME_ERROR,
                            "Invalid number of args passed into obj lambda method",
                        )

                    if len(function_elem.dict['args']) != len(statement_node.dict['args']):
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Invalid number of args passed into lambda",
                        )
                else:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Attempting to call function on non-function variable type",
                    )

        # check if statement node is a variable that references another function
        # (either a named function OR a lambda)
        if function_elem is None:
            scope_index = self.validate_var_name(statement_node.dict['name'])
            if scope_index is not None:
                var_value = self.variable_scope_list[scope_index][statement_node.dict['name']]
                if var_value.t == Type.FUNC:
                    updated_statement_node = var_value.v
                    # get new function elem
                    if functions_list:
                        for elem in functions_list:
                            if elem.dict['name'] == updated_statement_node.dict['name']:
                                if len(elem.dict['args']) != len(statement_node.dict['args']):
                                    super().error(
                                        ErrorType.TYPE_ERROR,
                                        "Invalid number of args passed into function",
                                    )
                                else:
                                    function_elem = elem
                # CAPTURED VARIABLES TAKE PRECEDENCE OVER PASS BY REFERENCE
                # INSIDE OF A LAMBDA?
                # that is, if we update x which references y, if y is a captured variable,
                # then we update the y variable outside of the lambda still
                # BUT we reference the original y captured variable when inside the lambda
                elif outer_lambda_node is not None and var_value.t == Type.LAMBDA and statement_node.dict['name'] in outer_lambda_node[Interpreter.CAPTURED_VARS]:
                    # fix needed = the way i capture variables is only the ones that are assignedd
                    # within the lambda
                    # but i need to be capturing all (?) variables in the outer scope
                    # possibly... lets investigate... ***



                     # if this is a lambda node within a lambda node
                    # e.g. var_value.t == Type.LAMBDA *AND* lambda_node is not none
                    # then we need to see if this var value is in the lambda node's captured values
                    # if so we need to reference the CAPTURED VALUE instead of the actual value in this moment
                    captured_vars_dict = outer_lambda_node[Interpreter.CAPTURED_VARS]
                    lambda_var_name = statement_node.dict['name']
                    # if lambda_var_name in captured_vars_dict:


                    lambda_node = captured_vars_dict[lambda_var_name]
                    function_elem = lambda_node.v[Interpreter.LAMBDA_NODE]
                        # passing in a list as my funct elem instead of a funct elem
                elif var_value.t == Type.LAMBDA:
                    # the issue -> calling the lambda is always *the* lambda
                    # i need to call a copy of the lambda if it is not pass by reference
                    function_elem = var_value.v[Interpreter.LAMBDA_NODE]
                    lambda_node = var_value.v
                    print("HERE123")
                    print("statement node")
                    print(statement_node)

                    if len(function_elem.dict['args']) != len(statement_node.dict['args']):
                        super().error(
                            ErrorType.TYPE_ERROR,
                            "Invalid number of args passed into lambda",
                        )
                else:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        "Attempting to call function on non-function variable type",
                    )

        # check that function elem is not still none...
        if function_elem is not None:
            # set up scope for this function
            # run the function
            self.variable_scope_list.append({}) # scope for new function
            self.variable_alias_list.append({})
            scope_index = len(self.variable_scope_list) - 1

            args_val_list = statement_node.dict['args']
            print("statement node 55555")
            print(statement_node)
            args_name_list = function_elem.dict['args']
            print("function elem 555555")
            print(function_elem)
            for i in range(len(args_val_list)):
                arg_val = self.evaluate_expression(args_val_list[i])
                arg_name = args_name_list[i].get('name')
               
                if arg_val.t == Type.LAMBDA and args_name_list[i].elem_type != 'refarg':
                    self.variable_scope_list[scope_index][arg_name] = copy.deepcopy(arg_val)
                elif arg_val.t == Type.OBJ and args_name_list[i].elem_type != 'refarg':
                    self.variable_scope_list[scope_index][arg_name] = copy.deepcopy(arg_val)
                else:
                    self.variable_scope_list[scope_index][arg_name] = arg_val
                    
                if args_name_list[i].elem_type == 'refarg':
                    ref_name = args_val_list[i].get('name')
                    self.variable_alias_list[scope_index][arg_name] = ref_name

            # if this is an object, then add the this variable to be the objref
            if object is not None:
                self.variable_scope_list[scope_index]["this"] = object
                self.variable_alias_list[scope_index]["this"] = statement_node.dict['objref'] # obj name

            return self.run_func(function_elem, lambda_node)
        else:
            super().error(
                    ErrorType.NAME_ERROR,
                    f"Function {statement_node.dict['name']} has not been defined",
                )
        
    def get_debug_info(self, ast):
        pass

def main():
    interpreter = Interpreter(trace_output=True)
    

    # should print 0 but its giving lambda
    program = """
func foo(ref x) {
if (x.a > 9) {
x.a = x.a - 1;
print(x.a);
foo(x);
} else {
print("reached the end!!!");
}
}

func main() {
 x = @;
 x.a = 12;
 foo(x);
 print(x.a);
}
"""
# output 10, 20

# now its 1 2 3 3 3
# should be 1 2 3 4 4


# 1

# 2

# func main() {
#   b = true + 123;
#   print(b);
  
#   b = 123 + true;
#   print(b);
  
#   b = 123 + false;
#   print(b);

#   c = true + true;
#   print(c);
  
#   d = false + true;
#   print(d);
# }







    

#    func cat(a) {
#   print(a);
# }

# func foo() {

#     print("I'm foo");
# }

# func main() {
# 	x = cat;
# 	x("what's upppp");
#     foo();
# }


    #   func foo() { print("hi");}

    #     func main() {
    #     x = foo;                                  /* assigns x to function foo */
    #     y = lambda() { print("I'm a lambda"); };  /* assigns y to a lambda */
    #     }
    
        # func foo(ref a) {
        # a = "abc";
        # }

        # func main() {
        # b = 5;
        # foo(b);
        # print(b);  /* prints abc */
        # }

        #         func a(ref x) {
        #     b(x);
        # }

        # func b(ref y) {
        #     y = 10;
        # }

        # func main() {
        #         z = 100;
        #         a(z);
        #         print(z);
        #     } 
        # prints 10!!!

    interpreter.run(program)

if __name__ == "__main__":
    main()   