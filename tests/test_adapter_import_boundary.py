"""Fresh-interpreter checks for the adapter package's optional import boundary."""

import importlib
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from robots import adapters

ROOT = Path(__file__).resolve().parents[1]


def run_isolated(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            f"import sys; sys.path.insert(0, {str(ROOT / 'src')!r})\n" + textwrap.dedent(script),
        ],
        cwd=ROOT.parent,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


@pytest.mark.parametrize("module", ["native_actor_presentation", "native_progression"])
def test_pure_decoder_import_does_not_load_optional_providers(module: str) -> None:
    result = run_isolated(f"""
        import importlib
        import importlib.abc
        import sys

        blocked = ('httpx', 'yaml', 'robots.adapters.chat', 'robots.adapters.decision',
                   'robots.adapters.mechanics_yaml')

        class DenyOptional(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if any(fullname == name or fullname.startswith(name + '.') for name in blocked):
                    raise ModuleNotFoundError('optional import denied: ' + fullname, name=fullname)
                return None

        sys.meta_path.insert(0, DenyOptional())
        importlib.import_module('robots.adapters.{module}')
        assert not any(name in sys.modules for name in blocked)
        """)
    assert result.returncode == 0, result.stderr


def test_dir_lists_lazy_exports_without_loading_them() -> None:
    result = run_isolated("""
        import sys
        import robots.adapters as adapters
        assert set(adapters.__all__).issubset(dir(adapters))
        assert 'robots.adapters.chat' not in sys.modules
        assert 'robots.adapters.decision' not in sys.modules
        assert 'robots.adapters.mechanics_stub' not in sys.modules
        """)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("reverse", [False, True])
def test_public_exports_keep_class_identity_and_cache(reverse: bool) -> None:
    result = run_isolated(f"""
        import importlib
        import robots.adapters as adapters
        expected = {{
            'ChatRemote': 'robots.adapters.chat',
            'ClefLocal': 'robots.adapters.decision',
            'ClefRemote': 'robots.adapters.decision',
            'LocalChatServer': 'robots.adapters.chat',
            'ScriptedDecisionModel': 'robots.adapters.decision',
            'StaticChatGenerator': 'robots.adapters.chat',
            'StubMechanics': 'robots.adapters.mechanics_stub',
            'YamlMechanics': 'robots.adapters.mechanics_stub',
        }}
        assert adapters.__all__ == list(expected)
        names = list(expected)
        if {reverse!r}:
            names.reverse()
        for name in names:
            value = getattr(adapters, name)
            assert isinstance(value, type)
            assert value is getattr(importlib.import_module(expected[name]), name)
            assert value is vars(adapters)[name]
            assert value is getattr(adapters, name)
        from robots.adapters import StubMechanics
        from robots.adapters import *
        assert StubMechanics is adapters.StubMechanics
        for name in expected:
            assert globals()[name] is getattr(adapters, name)
        StubMechanics()
        """)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("name", ["missing", "httpx", "robots.adapters.chat", "__not_metadata__"])
def test_unknown_names_raise_normal_attribute_error(name: str) -> None:
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(adapters, name)


def test_package_directory_advertises_exports() -> None:
    assert set(adapters.__all__).issubset(dir(adapters))


def test_explicit_optional_import_preserves_failure_identity() -> None:
    result = run_isolated("""
        import importlib.abc
        import sys
        import robots.adapters as adapters

        failure = ModuleNotFoundError('optional HTTP dependency unavailable', name='httpx')
        class DenyHttp(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == 'httpx':
                    raise failure
                return None
        sys.meta_path.insert(0, DenyHttp())
        try:
            adapters.ChatRemote
        except ModuleNotFoundError as error:
            assert error is failure
        else:
            raise AssertionError('explicit provider access must require its dependency')
        assert 'ChatRemote' not in vars(adapters)
        assert hasattr(adapters, '__path__')
        assert not hasattr(adapters, '__not_metadata__')
        """)
    assert result.returncode == 0, result.stderr


def test_local_exports_match_defining_classes() -> None:
    for name in adapters.__all__:
        value = getattr(adapters, name)
        assert value is getattr(importlib.import_module(value.__module__), name)
        assert value is vars(adapters)[name]
