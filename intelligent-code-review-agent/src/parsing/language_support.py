"""Tree-sitter language grammar loading and management."""

import tree_sitter


class LanguageSupport:
    """Manages Tree-sitter language parsers."""

    def __init__(self):
        self._parsers: dict[str, tree_sitter.Parser] = {}
        self._languages: dict[str, tree_sitter.Language] = {}
        self._load_available_languages()

    def _load_available_languages(self):
        """Try to load all supported language grammars."""
        loaders = {
            "python": self._load_python,
            "javascript": self._load_javascript,
            "typescript": self._load_typescript,
            "c_sharp": self._load_c_sharp,
            "java": self._load_java,
            "go": self._load_go,
            "rust": self._load_rust,
            "c": self._load_c,
            "cpp": self._load_cpp,
            "php": self._load_php,
            "ruby": self._load_ruby,
            "swift": self._load_swift,
            "kotlin": self._load_kotlin,
            "scala": self._load_scala,
            "lua": self._load_lua,
            "sql": self._load_sql,
            "julia": self._load_julia,
            "matlab": self._load_matlab,
            "solidity": self._load_solidity,
            "shell": self._load_shell,
            "verilog": self._load_verilog,
            "zig": self._load_zig,
            "objective_c": self._load_objective_c,
        }

        for lang_name, loader in loaders.items():
            try:
                lang = loader()
                if lang is not None:
                    self._languages[lang_name] = lang
                    parser = tree_sitter.Parser(lang)
                    self._parsers[lang_name] = parser
            except Exception:
                pass  # Language not available, skip

    def _load_python(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_python
            return tree_sitter.Language(tree_sitter_python.language())
        except Exception:
            return None

    def _load_javascript(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_javascript
            return tree_sitter.Language(tree_sitter_javascript.language())
        except Exception:
            return None

    def _load_typescript(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_typescript
            return tree_sitter.Language(tree_sitter_typescript.language_typescript())
        except Exception:
            return None

    def _load_c_sharp(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_c_sharp
            return tree_sitter.Language(tree_sitter_c_sharp.language())
        except Exception:
            return None

    def _load_java(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_java
            return tree_sitter.Language(tree_sitter_java.language())
        except Exception:
            return None

    def _load_go(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_go
            return tree_sitter.Language(tree_sitter_go.language())
        except Exception:
            return None

    def _load_rust(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_rust
            return tree_sitter.Language(tree_sitter_rust.language())
        except Exception:
            return None

    def _load_c(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_c
            return tree_sitter.Language(tree_sitter_c.language())
        except Exception:
            return None

    def _load_cpp(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_cpp
            return tree_sitter.Language(tree_sitter_cpp.language())
        except Exception:
            return None

    def _load_php(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_php
            return tree_sitter.Language(tree_sitter_php.language_php())
        except Exception:
            return None

    def _load_ruby(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_ruby
            return tree_sitter.Language(tree_sitter_ruby.language())
        except Exception:
            return None

    def _load_swift(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_swift
            return tree_sitter.Language(tree_sitter_swift.language())
        except Exception:
            return None

    def _load_kotlin(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_kotlin
            return tree_sitter.Language(tree_sitter_kotlin.language())
        except Exception:
            return None

    def _load_scala(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_scala
            return tree_sitter.Language(tree_sitter_scala.language())
        except Exception:
            return None

    def _load_lua(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_lua
            return tree_sitter.Language(tree_sitter_lua.language())
        except Exception:
            return None

    def _load_sql(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_sql
            return tree_sitter.Language(tree_sitter_sql.language())
        except Exception:
            return None

    def _load_julia(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_julia
            return tree_sitter.Language(tree_sitter_julia.language())
        except Exception:
            return None

    def _load_matlab(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_matlab
            return tree_sitter.Language(tree_sitter_matlab.language())
        except Exception:
            return None

    def _load_solidity(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_solidity
            return tree_sitter.Language(tree_sitter_solidity.language())
        except Exception:
            return None

    def _load_shell(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_bash
            return tree_sitter.Language(tree_sitter_bash.language())
        except Exception:
            return None

    def _load_verilog(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_verilog
            return tree_sitter.Language(tree_sitter_verilog.language())
        except Exception:
            return None

    def _load_zig(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_zig
            return tree_sitter.Language(tree_sitter_zig.language())
        except Exception:
            return None

    def _load_objective_c(self) -> tree_sitter.Language | None:
        try:
            import tree_sitter_objc
            return tree_sitter.Language(tree_sitter_objc.language())
        except Exception:
            return None

    def get_parser(self, language: str) -> tree_sitter.Parser | None:
        """Get a Tree-sitter parser for the given language."""
        return self._parsers.get(language)

    def get_language(self, language: str) -> tree_sitter.Language | None:
        """Get a Tree-sitter Language object for the given language."""
        return self._languages.get(language)

    def is_supported(self, language: str) -> bool:
        """Check if a language has Tree-sitter support."""
        return language in self._parsers

    @property
    def supported_languages(self) -> list[str]:
        """List all supported languages."""
        return list(self._parsers.keys())
