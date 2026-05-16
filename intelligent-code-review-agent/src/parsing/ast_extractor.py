"""AST context extraction using Tree-sitter."""

import tree_sitter

from pydantic import BaseModel

from .language_support import LanguageSupport


class CodeContext(BaseModel):
    """Context extracted via Tree-sitter for a changed region."""
    file_path: str
    language: str
    changed_lines: tuple[int, int]
    enclosing_function: str | None = None
    enclosing_class: str | None = None
    function_name: str | None = None
    class_name: str | None = None
    imports: list[str] = []
    related_symbols: list[str] = []
    full_source: str | None = None
    diff_text: str | None = None


class ASTExtractor:
    """Extract code context around changed lines using Tree-sitter."""

    # Node types that represent function/method definitions
    FUNCTION_TYPES = {
        "python": ["function_definition"],
        "javascript": ["function_declaration", "method_definition", "arrow_function"],
        "typescript": ["function_declaration", "method_definition", "arrow_function"],
        "c_sharp": ["method_declaration", "constructor_declaration", "local_function_statement"],
        "java": ["method_declaration", "constructor_declaration"],
        "go": ["function_declaration", "method_declaration"],
        "rust": ["function_item"],
        "c": ["function_definition"],
        "cpp": ["function_definition"],
        "php": ["function_definition", "method_declaration"],
        "ruby": ["method", "singleton_method"],
        "swift": ["function_declaration"],
        "kotlin": ["function_declaration"],
        "scala": ["function_definition", "val_definition"],
        "lua": ["function_declaration", "function_definition"],
        "sql": ["create_function"],
        "julia": ["function_definition", "short_function_definition"],
        "matlab": ["function_definition"],
        "solidity": ["function_definition", "modifier_definition"],
        "shell": ["function_definition"],
        "verilog": ["function_declaration", "task_declaration", "checker_declaration"],
        "zig": ["function_declaration"],
        "objective_c": ["function_definition", "method_definition"],
    }

    # Node types that represent class definitions
    CLASS_TYPES = {
        "python": ["class_definition"],
        "javascript": ["class_declaration"],
        "typescript": ["class_declaration"],
        "c_sharp": ["class_declaration", "struct_declaration", "interface_declaration", "record_declaration"],
        "java": ["class_declaration", "interface_declaration", "enum_declaration"],
        "go": ["type_declaration"],
        "rust": ["impl_item", "struct_item", "trait_item"],
        "c": ["struct_specifier"],
        "cpp": ["class_specifier", "struct_specifier"],
        "php": ["class_declaration", "interface_declaration", "trait_declaration"],
        "ruby": ["class", "module"],
        "swift": ["class_declaration", "struct_declaration", "protocol_declaration"],
        "kotlin": ["class_declaration", "object_declaration"],
        "scala": ["class_definition", "object_definition", "trait_definition"],
        "lua": [],
        "sql": [],
        "julia": ["abstract_definition", "struct_definition"],
        "matlab": [],
        "solidity": ["contract_declaration", "interface_declaration", "library_declaration"],
        "shell": [],
        "verilog": ["module_declaration", "class_declaration", "interface_declaration", "package_declaration"],
        "zig": [],
        "objective_c": ["class_interface", "class_implementation"],
    }

    # Node types that represent import statements
    IMPORT_TYPES = {
        "python": ["import_statement", "import_from_statement"],
        "javascript": ["import_statement"],
        "typescript": ["import_statement"],
        "c_sharp": ["using_directive"],
        "java": ["import_declaration"],
        "go": ["import_declaration"],
        "rust": ["use_declaration"],
        "c": ["preproc_include"],
        "cpp": ["preproc_include"],
        "php": ["namespace_use_declaration"],
        "ruby": ["call"],  # require/require_relative are method calls
        "swift": ["import_declaration"],
        "kotlin": ["import_header"],
        "scala": ["import_declaration"],
        "lua": [],
        "sql": [],
        "julia": ["import_statement"],
        "matlab": [],
        "solidity": ["import_directive"],
        "shell": [],
        "verilog": [],
        "zig": [],
        "objective_c": ["preproc_import", "import"],
    }

    def __init__(self):
        self.language_support = LanguageSupport()

    def extract_context(
        self,
        source_code: str,
        language: str,
        changed_lines: tuple[int, int],
        file_path: str = "",
    ) -> CodeContext:
        """Extract AST context for a changed region in the source code.

        changed_lines are 1-indexed (user-facing line numbers).
        Tree-sitter uses 0-indexed, so we convert internally.
        """
        parser = self.language_support.get_parser(language)
        if parser is None:
            return CodeContext(
                file_path=file_path,
                language=language,
                changed_lines=changed_lines,
            )

        tree = parser.parse(source_code.encode("utf-8"))
        root = tree.root_node

        # Convert 1-indexed to 0-indexed for tree-sitter
        start_line = changed_lines[0] - 1
        end_line = changed_lines[1] - 1

        # Find enclosing function
        enclosing_function, function_name = self._find_enclosing(
            root, start_line, self.FUNCTION_TYPES.get(language, []), source_code
        )

        # Find enclosing class
        enclosing_class, class_name = self._find_enclosing(
            root, start_line, self.CLASS_TYPES.get(language, []), source_code
        )

        # Extract imports
        imports = self._extract_imports(root, source_code, language)

        # Extract related symbols from the changed region
        related_symbols = self._extract_symbols(root, start_line, end_line, source_code)

        return CodeContext(
            file_path=file_path,
            language=language,
            changed_lines=changed_lines,
            enclosing_function=enclosing_function,
            enclosing_class=enclosing_class,
            function_name=function_name,
            class_name=class_name,
            imports=imports,
            related_symbols=related_symbols,
        )

    def _find_enclosing(
        self,
        root: tree_sitter.Node,
        line_number: int,
        node_types: list[str],
        source_code: str,
    ) -> tuple[str | None, str | None]:
        """Find the enclosing node of given types around a line number."""
        if not node_types:
            return None, None

        node = self._find_node_at_line(root, line_number, node_types)
        if node is None:
            return None, None

        source_bytes = source_code.encode("utf-8")
        node_text = source_bytes[node.start_byte:node.end_byte].decode("utf-8")

        # Try to extract the name
        name = self._extract_node_name(node)

        return node_text, name

    def _find_node_at_line(
        self,
        node: tree_sitter.Node,
        line_number: int,
        target_types: list[str],
    ) -> tree_sitter.Node | None:
        """Walk up the tree from a line to find the enclosing target node."""
        # First find a leaf node at the target line
        candidate = self._find_leaf_at_line(node, line_number)
        if candidate is None:
            return None

        # Walk up to find enclosing target type
        current = candidate
        while current is not None:
            if current.type in target_types:
                return current
            current = current.parent
        return None

    def _find_leaf_at_line(
        self, node: tree_sitter.Node, line_number: int
    ) -> tree_sitter.Node | None:
        """Find a leaf node at the given line number (0-indexed)."""
        if node.child_count == 0:
            if node.start_point[0] <= line_number <= node.end_point[0]:
                return node
            return None

        for child in node.children:
            if child.start_point[0] <= line_number <= child.end_point[0]:
                result = self._find_leaf_at_line(child, line_number)
                if result is not None:
                    return result
        return None

    def _extract_node_name(self, node: tree_sitter.Node) -> str | None:
        """Extract the name from a function or class definition node."""
        # Direct name/identifier child
        name_types = {"name", "identifier", "type_identifier", "simple_identifier"}
        for child in node.children:
            if child.type in name_types:
                return child.text.decode("utf-8")
        # Swift/Kotlin: name is simple_identifier after 'func'/'fun' keyword
        for child in node.children:
            if child.type in ("func", "fun", "function"):
                # Next sibling is the name
                idx = list(node.children).index(child)
                if idx + 1 < len(node.children):
                    next_child = node.children[idx + 1]
                    if next_child.type in name_types:
                        return next_child.text.decode("utf-8")
        # C/C++: name is inside function_declarator
        for child in node.children:
            if child.type == "function_declarator":
                for sub in child.children:
                    if sub.type in ("identifier", "field_identifier", "destructor_name", "qualified_identifier"):
                        return sub.text.decode("utf-8")
        # C# / Java: name is inside declarator
        for child in node.children:
            if child.type == "declarator":
                for sub in child.children:
                    if sub.type in ("identifier", "name"):
                        return sub.text.decode("utf-8")
        # Julia: name is inside signature > typed_expression > call_expression
        for child in node.children:
            if child.type == "signature":
                for sub in child.children:
                    if sub.type == "typed_expression":
                        for sub2 in sub.children:
                            if sub2.type == "call_expression":
                                # First child of call_expression is the name
                                if sub2.children:
                                    return sub2.children[0].text.decode("utf-8")
                            elif sub2.type in name_types:
                                return sub2.text.decode("utf-8")
                    elif sub.type in name_types:
                        return sub.text.decode("utf-8")
        return None

    def _extract_imports(
        self,
        root: tree_sitter.Node,
        source_code: str,
        language: str,
    ) -> list[str]:
        """Extract all import statements from the file."""
        import_types = self.IMPORT_TYPES.get(language, [])
        if not import_types:
            return []

        source_bytes = source_code.encode("utf-8")
        imports = []

        def walk(node: tree_sitter.Node):
            if node.type in import_types:
                imports.append(source_bytes[node.start_byte:node.end_byte].decode("utf-8"))
            for child in node.children:
                walk(child)

        walk(root)
        return imports

    def _extract_symbols(
        self,
        root: tree_sitter.Node,
        start_line: int,
        end_line: int,
        source_code: str,
    ) -> list[str]:
        """Extract identifier symbols referenced in the changed lines."""
        source_bytes = source_code.encode("utf-8")
        symbols = set()

        def walk(node: tree_sitter.Node):
            if node.type == "identifier" or node.type == "name":
                if start_line <= node.start_point[0] <= end_line:
                    text = source_bytes[node.start_byte:node.end_byte].decode("utf-8")
                    if len(text) > 1:  # Skip single-char identifiers
                        symbols.add(text)
            for child in node.children:
                walk(child)

        walk(root)
        return list(symbols)
