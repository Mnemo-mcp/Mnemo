import pytest
from pathlib import Path
from mnemo.repo_map.parsers import _extract_file

FIXTURE_DIR = Path(__file__).parent / 'fixtures' / 'sample_project' / 'src'


class TestPythonParser:
    def test_extracts_classes(self):
        source = (FIXTURE_DIR / 'services' / 'payment_service.py').read_bytes()
        result = _extract_file(source, 'python')
        assert result is not None
        class_names = [c['name'] for c in result['classes']]
        assert 'PaymentService' in class_names

    def test_extracts_methods(self):
        source = (FIXTURE_DIR / 'services' / 'event_bus.py').read_bytes()
        result = _extract_file(source, 'python')
        assert result is not None
        # event_bus.py has EventBus class with methods, no top-level functions
        methods = result['classes'][0].get('methods', [])
        assert len(methods) > 0

    def test_extracts_imports(self):
        source = (FIXTURE_DIR / 'controllers' / 'payment_controller.py').read_bytes()
        result = _extract_file(source, 'python')
        assert result is not None
        assert len(result.get('imports', [])) > 0


class TestJavaScriptParser:
    def test_extracts_classes(self):
        source = (FIXTURE_DIR / 'app.js').read_bytes()
        result = _extract_file(source, 'javascript')
        assert result is not None
        class_names = [c['name'] for c in result['classes']]
        assert 'Router' in class_names

    def test_extracts_functions(self):
        source = (FIXTURE_DIR / 'app.js').read_bytes()
        result = _extract_file(source, 'javascript')
        assert result is not None
        fn_names = result.get('functions', [])
        assert any('createApp' in f for f in fn_names)


class TestTypeScriptParser:
    def test_extracts_classes(self):
        source = (FIXTURE_DIR / 'types.ts').read_bytes()
        result = _extract_file(source, 'typescript')
        assert result is not None
        class_names = [c['name'] for c in result['classes']]
        assert 'PaymentProcessor' in class_names

    def test_extracts_functions(self):
        source = (FIXTURE_DIR / 'types.ts').read_bytes()
        result = _extract_file(source, 'typescript')
        assert result is not None
        fn_names = ' '.join(result.get('functions', []))
        assert 'validateAmount' in fn_names


class TestGoParser:
    def test_extracts_structs_as_classes(self):
        source = (FIXTURE_DIR / 'server.go').read_bytes()
        result = _extract_file(source, 'go')
        assert result is not None
        class_names = [c['name'] for c in result['classes']]
        assert 'Server' in class_names

    def test_extracts_functions(self):
        source = (FIXTURE_DIR / 'server.go').read_bytes()
        result = _extract_file(source, 'go')
        assert result is not None
        fn_text = ' '.join(result.get('functions', []))
        assert 'NewServer' in fn_text or 'main' in fn_text


class TestParserEdgeCases:
    def test_empty_file(self):
        result = _extract_file(b'', 'python')
        assert result is None or (len(result.get('classes', [])) == 0 and len(result.get('functions', [])) == 0)

    def test_invalid_syntax(self):
        result = _extract_file(b'def incomplete(', 'python')
        # tree-sitter handles partial parses gracefully — just no crash
        assert result is not None or result is None

    def test_unsupported_language(self):
        result = _extract_file(b'some content', 'brainfuck')
        assert result is None

    def test_binary_content(self):
        result = _extract_file(b'\x00\x01\x02\x03', 'python')
        assert result is None or (len(result.get('classes', [])) == 0 and len(result.get('functions', [])) == 0)
