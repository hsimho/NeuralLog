#  Copyright 2021 Victor Guimarães
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""
Define the classes to represent the knowledge of the system.
"""

import re
from abc import ABC, abstractmethod
from collections.abc import Collection

TRAINABLE_KEY = "$"

WEIGHT_SEPARATOR = "::"
NEGATION_KEY = "not"
IMPLICATION_SIGN = ":-"
END_SIGN = "."
PLACE_HOLDER = re.compile("({[a-zA-Z0-9_-]+})")


def get_term_from_string(string):
    """
    Transforms the string into a term. A variable if it starts with an upper
    case letter, or a constant, otherwise.

    :param string: the string
    :type string: str
    :raise TermMalformedException: case the term is malformed
    :return: the term
    :rtype: Term
    """
    if string[0].isupper():
        return Variable(string)
    elif string[0].islower() or string[0] == "_":
        return Constant(string)
    elif string[0] == string[-1] and (string[0] == "'" or string[0] == '"'):
        return Quote(string)
    else:
        raise TermMalformedException()


def get_constant_from_string(string):
    """
    Transforms the string into a constant term.

    :param string: the string
    :type string: str
    :raise TermMalformedException: case the term is malformed
    :return: the term
    :rtype: Term
    """
    if string[0] == string[-1] and (string[0] == "'" or string[0] == '"'):
        return Quote(string)

    return Constant(string)


def build_terms(arguments):
    """
    Builds a list of terms from the arguments.

    :param arguments: the arguments
    :type arguments: list[Term or str]
    :raise TermMalformedException: if the argument is neither a term nor a str
    :return: a list of terms
    :rtype: list[Term]
    """
    terms = []
    for argument in arguments:
        if isinstance(argument, Term):
            terms.append(argument)
        elif isinstance(argument, str):
            terms.append(get_term_from_string(argument))
        elif isinstance(argument, float) or isinstance(argument, int):
            terms.append(Number(argument))
        else:
            raise TermMalformedException()

    return terms


def get_variable_atom(value):
    """
    Gets an atom or literal by replacing their constant for unique variables.

    :param value: the literal, atom or predicate
    :type value: Literal or Atom or Predicate
    :return: the renamed literal, atom
    :rtype: Literal or Atom
    """
    if isinstance(value, Atom):
        predicate = value.predicate
    else:
        predicate = value
    terms = [Variable("X{}".format(i)) for i in range(predicate.arity)]
    variable_atom = Atom(predicate, *terms)
    if isinstance(value, Literal):
        return Literal(variable_atom, negated=value.negated)
    return variable_atom


def get_renamed_atom(atom):
    """
    Gets a renamed atom, replacing their variables for a positional name.
    In this way, atoms with different variable names will have the same key,
    as long as the number of variables and their positions matches.

    :param atom: the atom
    :type atom: Atom
    :return: the renamed atom
    :rtype: Atom
    """
    terms = []
    index = 0
    term_map = dict()
    for term in atom.terms:
        if term.is_constant():
            if isinstance(term, Quote):
                terms.append(Constant(term.value))
            else:
                terms.append(term)
        else:
            if term not in term_map:
                term_map[term] = "X{}".format(index)
                index += 1
            terms.append(term_map[term])
    return Atom(atom.predicate, *terms)


def get_renamed_literal(literal):
    """
    Gets a renamed literal from `literal`.

    :param literal: the literal
    :type literal: Atom or Literal
    :return: the renamed literal
    :rtype: Literal
    """
    renamed_atom = get_renamed_atom(literal)
    negated = False
    if isinstance(literal, Literal):
        negated = literal.negated
    return Literal(renamed_atom, negated=negated)


def get_substitution(generic_atom, specific_atom):
    """
    If `generic_atom` can be unified with the `specific_atom`, returns the
    substitution of the terms of `generic_atom` that unifies it with
    `specific_atom`; otherwise, returns `None`.

    :param generic_atom: the generic atom
    :type generic_atom: Atom
    :param specific_atom: the specific atom
    :type specific_atom: Atom
    :return: the substitution of the `generic_atom` terms
    :rtype: Dict[Term, Term]
    """
    if generic_atom.predicate != specific_atom.predicate:
        return None

    substitutions = dict()
    for i in range(generic_atom.arity()):
        generic_term = generic_atom.terms[i]
        specific_term = specific_atom.terms[i]

        if generic_term.is_constant() and generic_term != specific_term:
            return None
        else:
            substitution = substitutions.get(generic_term, None)
            if substitution is None:
                substitutions[generic_term] = specific_term
            elif substitution != specific_term:
                return None

    return substitutions


def get_variable_indices(atom):
    """
    Gets the indexes of the variables in the atom.

    :param atom: the atom
    :type atom: Atom
    :return: the indices of the variables
    :rtype: list[int]
    """
    indexes = []
    for i in range(atom.arity()):
        if not atom.terms[i].is_constant():
            indexes.append(i)

    return indexes


class KnowledgeException(Exception):
    """
    Represents a exception in the logic knowledge.
    """


class TooManyArgumentsFunction(KnowledgeException):
    """
    Represents an exception raised by function literal with too many arguments.
    """

    MAX_NUMBER_OF_ARGUMENTS = 1

    def __init__(self, predicate):
        """
        Creates a too many arguments exception.

        :param predicate: the predicate
        :type predicate: Predicate
        """
        super().__init__("Too many arguments for function predicate {} at "
                         "The maximum number of arguments allowed is {}."
                         .format(predicate,
                                 self.MAX_NUMBER_OF_ARGUMENTS))


class AtomMalformedException(KnowledgeException):
    """
    Represents an atom malformed exception.
    """

    def __init__(self, expected, found):
        """
        Creates an atom malformed exception.

        :param expected: the number of arguments expected
        :type expected: int
        :param found: the number of arguments found
        :type found: int
        """
        super().__init__("Atom malformed, the predicate expects "
                         "{} argument(s) but {} found.".format(expected, found))


class TermMalformedException(KnowledgeException):
    """
    Represents an term malformed exception.
    """

    def __init__(self):
        """
        Creates an term malformed exception.
        """
        super().__init__("Term malformed, the argument must be either a term "
                         "or a string.")


class ClauseMalformedException(KnowledgeException):
    """
    Represents an term malformed exception.
    """

    def __init__(self, clause=None):
        """
        Creates an term malformed exception.
        """
        super().__init__("Clause malformed, the clause must be an atom, "
                         "a weighted atom or a Horn clause: "
                         "`{}`".format(clause))


class BadArgumentException(KnowledgeException):
    """
    Represents an bad argument exception.
    """

    def __init__(self, value):
        """
        Creates an term malformed exception.
        """
        super().__init__("Expected a number or a term, got {}.".format(value))


class ClauseProvenance(ABC):
    """
    Represents the provenance of the clause in the input file.
    """

    @abstractmethod
    def __repr__(self):
        pass


class FileDefinedClause(ClauseProvenance):
    """
    Represents the provenance of a clause defined in a file.
    """

    def __init__(self, start_line, filename):
        """
        Creates a `ClauseProvenance`.

        :param start_line: the start line
        :type start_line: int
        :param filename: the file name
        :type filename: str
        """
        self.start_line = start_line
        self.filename = filename

    def __repr__(self):
        return "defined at line {} in file {}".format(
            self.start_line, self.filename)


class UnsupportedMatrixRepresentation(Exception):
    """
    Represents an unsupported matrix representation exception.
    """

    def __init__(self, predicate):
        """
        Creates an unsupported matrix representation exception.
        """
        super().__init__("Unsupported matrix representation for: "
                         " {}.".format(predicate))


class Term:
    """
    Represents a logic term.
    """

    def __init__(self, value):
        """
        Creates a logic term.

        :param value: the value of the term
        :type value: Any
        """
        self.value = value

    def get_name(self):
        """
        Returns the name of the term.
        :return: the name of the term
        :rtype: str
        """
        return self.value

    def is_constant(self):
        """
        Returns true if the term is a constant.

        :return: true if it is a constant, false otherwise
        :rtype: bool
        """
        return False

    def is_template(self):
        """
        Returns true if the term is a template to be instantiated based on
        the knowledge base.
        :return: True if the term is a template, false otherwise
        :rtype: bool
        """
        return False

    def key(self):
        """
        Specifies the keys to be used in the equals and hash functions.
        :return: the keys
        :rtype: Any
        """
        return self.value,

    def __hash__(self):
        return hash(self.key())

    def __eq__(self, other):
        if isinstance(other, Term):
            return self.key() == other.key()
        return False

    def __gt__(self, other):
        return self.key() > other.key()

    def __ge__(self, other):
        return self.key() >= other.key()

    def __lt__(self, other):
        self_key = self.key()
        other_key = other.key()
        return (len(self_key),) + self_key < (len(other_key),) + other_key

    def __le__(self, other):
        return self.key() <= other.key()

    def __repr__(self):
        return self.value


class Constant(Term):
    """
    Represents a logic constant.
    """

    def __init__(self, value):
        """
        Creates a logic constant.

        :param value: the name of the constant
        :type value: str
        """
        super().__init__(value)

    # noinspection PyMissingOrEmptyDocstring
    def is_constant(self):
        return True

    def __repr__(self):
        return self.value


class Variable(Term):
    """
    Represents a logic variable.
    """

    def __init__(self, value):
        """
        Creates a logic variable.

        :param value: the name of the variable
        :type value: str
        """
        super().__init__(value)

    # noinspection PyMissingOrEmptyDocstring
    def key(self):
        return Variable.__class__.__name__, self.value

    # noinspection PyMissingOrEmptyDocstring
    def is_constant(self):
        return False


class Quote(Term):
    """
    Represents a quoted term, that might contain a template.
    """

    def __init__(self, value):
        """
        Creates a quoted term.

        :param value: the value of the term.
        :type value: str
        """
        super().__init__(value[1:-1])
        self._is_template = PLACE_HOLDER.search(value) is not None
        self.quote = value[0]

    # noinspection PyMissingOrEmptyDocstring
    def is_constant(self):
        return not self._is_template

    # noinspection PyMissingOrEmptyDocstring
    def is_template(self):
        return self._is_template

    def __str__(self):
        return self.quote + super().__str__() + self.quote


class Number(Term):
    """
    Represents a number term.
    """

    def __init__(self, value):
        super().__init__(value)

    # noinspection PyMissingOrEmptyDocstring
    def get_name(self):
        return str(self.value)

    # noinspection PyMissingOrEmptyDocstring
    def is_constant(self):
        return True

    # noinspection PyMissingOrEmptyDocstring
    def is_template(self):
        return False

    def __str__(self):
        return str(self.value)


class TemplateTerm(Term):
    """
    Defines a template term, a term with variable parts to be instantiated
    based on the knowledge base.
    """

    def __init__(self, parts):
        """
        Creates a template term.

        :param parts: the parts of the term.
        :type parts: list[str]
        """
        super().__init__("".join(parts))
        self.parts = parts

    # noinspection PyMissingOrEmptyDocstring
    def is_constant(self):
        return False

    # noinspection PyMissingOrEmptyDocstring
    def is_template(self):
        return True


class ListTerms(Term):
    """
    Defines a term that is a list of terms.
    """

    def __init__(self, terms):
        """
        Creates a list of terms.

        :param terms: the terms
        :type terms: collections.Iterable[Term]
        """
        self.items = tuple(terms)
        super().__init__(f"[{', '.join(map(lambda x: str(x), self.items))}]")

    # noinspection PyMissingOrEmptyDocstring
    def is_constant(self):
        return True

    # noinspection PyMissingOrEmptyDocstring
    def is_template(self):
        for term in self.items:
            if term.is_template():
                return True

        return False


class Predicate:
    """
    Represents a logic predicate.
    """

    def __init__(self, name, arity=0):
        """
        Creates a logic predicate.

        :param name: the name of the predicate
        :type name: str
        :param arity: the arity of the predicate
        :type arity: int
        """
        self.name = name
        self.arity = arity

    def __lt__(self, other):
        return self.key() < other.key()

    def is_template(self):
        """
        Returns true if the predicate is a template to be instantiated based on
        the knowledge base.
        :return: True if the predicate is a template, false otherwise
        :rtype: bool
        """
        return False

    def __repr__(self):
        return "{}/{}".format(self.name, self.arity)

    def key(self):
        """
        Specifies the keys to be used in the equals and hash functions.
        :return: the keys
        :rtype: Any
        """
        return self.name, self.arity

    def get_name(self):
        """
        Returns the name of the predicate.

        :return: the name of the predicate
        :rtype: str
        """
        return self.name

    def __hash__(self):
        return hash(self.key())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.key() == other.key()
        return False

    def equivalent(self, other):
        """
        Two predicates are equivalent if they have the same name and one of: (1)
        they have the same arity; or (2) at least one of then has a negative
        arity.

        :param other: the other predicate
        :type other: Predicate
        :return: True if this predicate is equivalent to `other`,
            False otherwise.
        :rtype: bool
        """
        if self.arity < 0 or other.arity < 0:
            return self.name == other.name
        else:
            return self == other


class TemplatePredicate(Predicate):
    """
    Defines a template predicate, a predicate with variable parts to be
    instantiated based on the knowledge base.
    """

    def __init__(self, parts, arity=0):
        """
        Creates a template predicate.

        :param parts: the parts of the predicate.
        :type parts: list[str]
        """
        super().__init__("".join(parts), arity=arity)
        self.parts = parts

    # noinspection PyMissingOrEmptyDocstring
    def is_template(self):
        return True


class Clause:
    """
    Represents a logic clause.
    """

    provenance: ClauseProvenance = None

    def __init__(self, provenance=None):
        """
        Creates a clause.

        :param provenance: the provenance of the clause
        :type provenance: ClauseProvenance or None
        """
        self.provenance = provenance

    def set_provenance(self, context):
        """
        Sets the provenance of an clause based on the context.

        :param context: the clause provenance
        :type context: ClauseProvenance or None
        """
        self.provenance = context

    def is_template(self):
        """
        Returns true if the clause is a template to be instantiated based on
        the knowledge base.
        :return: True if the clause is a template, false otherwise
        :rtype: bool
        """
        return False

    def is_grounded(self):
        """
        Returns true if the clause is grounded. A clause is grounded if all
        its terms are constants.
        :return: true if the clause is grounded, false otherwise
        :rtype: bool
        """
        pass

    def key(self):
        """
        Specifies the keys to be used in the equals and hash functions.
        :return: the keys
        :rtype: Any
        """
        pass

    def __hash__(self):
        return hash(self.key())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.key() == other.key()
        return False


class Atom(Clause):
    """
    Represents a logic atom.
    """

    def __init__(self, predicate, *args, weight=1.0, provenance=None):
        """
        Creates a logic atom.

        :param predicate: the predicate
        :type predicate: str or Predicate
        :param args: the list of terms, if any
        :type args: Term ocr str, int, float
        :param weight: the weight of the atom
        :type weight: float
        :param provenance: the provenance of the atom
        :type provenance: ClauseProvenance
        :raise AtomMalformedException: in case the number of terms differs
        from the arity of the predicate
        """
        super(Atom, self).__init__(provenance)
        if isinstance(predicate, Predicate):
            self.predicate = predicate
            if predicate.arity != len(args):
                raise AtomMalformedException(predicate.arity,
                                             len(args))
        else:
            self.predicate = Predicate(predicate, len(args))

        self.weight = weight
        # noinspection PyTypeChecker
        self.terms = build_terms(args)

    def __getitem__(self, item):
        return self.terms[item]

    def simple_key(self):
        """
        Returns a simplified key of an atom. This key does not include neither
        the weight of the atom nor the value of the numeric terms.

        It is useful to check if an atom was defined multiple times with
        different weights and attribute values.

        :return: the simple key of the atom
        :rtype: tuple[Predicate, tuple[Term]]
        """
        return self.predicate, tuple(
            [None if isinstance(x, Number) or not x.is_constant() else
             x for x in self.terms])

    # noinspection PyMissingOrEmptyDocstring
    def is_grounded(self):
        for term in self.terms:
            if isinstance(term, Term) and not term.is_constant():
                return False
        return True

    def arity(self):
        """
        Returns the arity of the atom.

        :return: the arity of the atom
        :rtype: int
        """
        return self.predicate.arity

    def get_number_of_variables(self):
        """
        Returns the number of variables in the atom.

        :return: the number of variables in the atom
        :rtype: int
        """
        return sum(1 for i in self.terms if not i.is_constant())

    # noinspection PyMissingOrEmptyDocstring
    def key(self):
        return self.weight, self.predicate, tuple(self.terms)

    def __repr__(self):
        if self.terms is None or len(self.terms) == 0:
            if self.weight == 1.0:
                return self.predicate.name
            else:
                return "{}::{}".format(self.weight, self.predicate.name)

        atom = "{}({})".format(self.predicate.name,
                               ", ".join(map(lambda x: str(x), self.terms)))
        if self.weight != 1.0:
            return "{}{}{}".format(self.weight, WEIGHT_SEPARATOR, atom)
        return atom

    # noinspection PyMissingOrEmptyDocstring
    def is_template(self):
        if self.predicate.is_template():
            return True
        if self.terms is None or len(self.terms) == 0:
            return False
        for term in self.terms:
            if term.is_template():
                return True

        return False


class Literal(Atom):
    """
    Represents a logic literal.
    """

    def __init__(self, atom, negated=False):
        """
        Creates a logic literal from an atom.

        :param atom: the atom
        :type atom: Atom
        :param negated: if the literal is negated
        :type negated: bool
        :raise AtomMalformedException: in case the number of terms differs
        from the arity of the predicate
        """
        super().__init__(atom.predicate, *atom.terms, weight=1.0,
                         provenance=atom.provenance)
        self.negated = negated

    # noinspection PyMissingOrEmptyDocstring
    def key(self):
        # noinspection PyTypeChecker
        return (self.negated,) + super().key()

    def __repr__(self):
        atom = super().__repr__()
        if self.negated:
            return "{} {}".format(NEGATION_KEY, atom)
        return atom


class AtomClause(Clause):
    """
    Represents an atom clause, an atom that is also a clause. As such,
    it is written with a `END_SIGN` at the end.
    """

    def __init__(self, atom):
        """
        Creates an atom clause
        :param atom: the atom
        :type atom: Atom
        """
        self.atom = Atom(atom.predicate, *atom.terms, weight=atom.weight)
        super(AtomClause, self).__init__(atom.provenance)

    # noinspection PyMissingOrEmptyDocstring
    def is_template(self):
        return self.atom.is_template()

    # noinspection PyMissingOrEmptyDocstring
    def is_grounded(self):
        return self.atom.is_grounded()

    # noinspection PyMissingOrEmptyDocstring
    def key(self):
        return self.atom.key()

    def __repr__(self):
        return self.atom.__str__() + END_SIGN

    def simple_key(self):
        """
        Returns a simplified key of an atom. This key does not include neither
        the weight of the atom nor the value of the numeric terms.

        It is useful to check if an atom was defined multiple times with
        different weights and attribute values.

        :return: the simple key of the atom
        :rtype: tuple[Predicate, tuple[Term]]
        """
        return self.atom.simple_key()


def format_horn_clause(head, body):
    """
    Formats the Horn clause to print.

    :param head: the head of the clause
    :type head: Atom
    :param body: the body of the clause
    :type body: Collection[Literal]
    :return: the formatted Horn clause
    :rtype: str
    """
    body = Literal(Atom("true")) if not body else body
    return "{} {} {}{}".format(
        head, IMPLICATION_SIGN,
        ", ".join(map(lambda x: str(x), body)), END_SIGN)


class HornClause(Clause):
    """
    Represents a logic Horn clause.
    """

    def __init__(self, head, *body, provenance=None):
        """
        Creates a Horn clause.

        :param head: the head
        :type head: Atom
        :param body: the list of literal, if any
        :type body: Literal
        :param provenance: the provenance of the clause
        :type provenance: ClauseProvenance
        """
        super(HornClause, self).__init__(provenance)
        self.head = head
        self.body = list(body)

    def __getitem__(self, item):
        if item == 0:
            return self.head
        return self.body[item - 1]

    # noinspection PyMissingOrEmptyDocstring
    def key(self):
        key_tuple = self.head.key()
        if self.body is not None and len(self.body) > 0:
            for literal in self.body:
                key_tuple += literal.key()
        return tuple(key_tuple)

    def __repr__(self):
        return format_horn_clause(self.head, self.body)

    # noinspection PyMissingOrEmptyDocstring
    def is_template(self):
        if self.head.is_template():
            return True
        if self.body is None or len(self.body) == 0:
            return False
        for literal in self.body:
            if literal.is_template():
                return True

        return False


class TermType:
    """
    Defines the types of a term.
    """

    def __init__(self, variable, number):
        """
        Creates a term type.

        :param variable: true, if the term is variable
        :type variable: bool
        :param number: true, if the term is number
        :type number: bool or None
        """
        self.variable = variable
        self.number = number

    def key(self):
        """
        Specifies the keys to be used in the equals and hash functions.
        :return: the keys
        :rtype: Any
        """
        return self.variable, self.number

    def __hash__(self):
        return hash(self.key())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.key() == other.key()
        return False

    def is_compatible(self, other):
        """
        Checks if two types are compatible against each other.
        Two types are compatibles if their number attribute match or one of
        them is none.

        :param other: the other term
        :type other: TermType
        :return: true if they are compatible, false otherwise.
        :rtype: bool
        """
        if self.number is None:
            return True

        if other.number is None:
            return True

        return self.number == other.number

    def update_type(self, other):
        """
        If `other` is compatible with this type, returns a new type with the
        attributes as an OR of this type and the `other`.

        :param other: the other type
        :type other: TermType
        :return: the update type
        :rtype: TermType
        """
        if not self.is_compatible(other):
            return None
        return TermType(self.variable or other.variable,
                        self.number or other.number)


class PredicateTypeError(KnowledgeException):
    """
    Represents a predicate type exception.
    """

    def __init__(self, current_atom, previous_atom):
        super().__init__("Found atom whose terms types are incompatible with "
                         "previous types: {} and {}".format(previous_atom,
                                                            current_atom))
