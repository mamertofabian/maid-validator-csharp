"""Hand-written implementation-collection tests grounded in real C# shapes.

Samples mirror constructs found in the Deckhand .NET monorepo: block and
file-scoped namespaces, interfaces with Task<T> methods, classes with base
lists, generics, nullable types, default parameters, properties, fields,
enums, structs, records, and delegates.
"""

from __future__ import annotations

from typing import Optional

import pytest

from maid_runner.core.types import ArtifactKind
from maid_runner.validators.base import FoundArtifact

from maid_validator_csharp import CSharpValidator


@pytest.fixture
def validator() -> CSharpValidator:
    return CSharpValidator()


def _impl(validator: CSharpValidator, source: str) -> list[FoundArtifact]:
    result = validator.collect_implementation_artifacts(source, "sample.cs")
    assert result.errors == [], result.errors
    return list(result.artifacts)


def _find(
    artifacts: list[FoundArtifact],
    name: str,
    kind: Optional[ArtifactKind] = None,
    of: Optional[str] = None,
) -> Optional[FoundArtifact]:
    for artifact in artifacts:
        if artifact.name != name:
            continue
        if kind is not None and artifact.kind != kind:
            continue
        if of is not None and artifact.of != of:
            continue
        return artifact
    return None


def test_block_namespace_is_collected_as_namespace(validator):
    artifacts = _impl(validator, "namespace Regionbuild.Attendant { }\n")
    ns = _find(artifacts, "Regionbuild.Attendant", ArtifactKind.NAMESPACE)
    assert ns is not None


def test_file_scoped_namespace_is_collected(validator):
    source = "namespace Modern;\n\npublic class Thing { }\n"
    artifacts = _impl(validator, source)
    assert _find(artifacts, "Modern", ArtifactKind.NAMESPACE) is not None
    assert _find(artifacts, "Thing", ArtifactKind.CLASS) is not None


def test_interface_and_its_methods_are_collected(validator):
    source = (
        "namespace Svc\n"
        "{\n"
        "    public interface IAttendantService\n"
        "    {\n"
        "        Task<List<AttendantVm>> GetAttendantPool(int congregationId);\n"
        "    }\n"
        "}\n"
    )
    artifacts = _impl(validator, source)
    iface = _find(artifacts, "IAttendantService", ArtifactKind.INTERFACE)
    assert iface is not None
    method = _find(
        artifacts, "GetAttendantPool", ArtifactKind.METHOD, of="IAttendantService"
    )
    assert method is not None
    assert method.returns == "Task<List<AttendantVm>>"
    assert [a.name for a in method.args] == ["congregationId"]
    assert method.args[0].type == "int"


def test_default_and_nullable_parameters_are_captured(validator):
    source = (
        "public interface I\n"
        "{\n"
        '    Task<Group?> Save(int id, bool overwrite = false, string note = "");\n'
        "}\n"
    )
    artifacts = _impl(validator, source)
    method = _find(artifacts, "Save", ArtifactKind.METHOD, of="I")
    assert method is not None
    assert method.returns == "Task<Group?>"
    names = [a.name for a in method.args]
    assert names == ["id", "overwrite", "note"]
    overwrite = method.args[1]
    assert overwrite.type == "bool"
    assert overwrite.default == "false"
    assert method.args[2].default == '""'


def test_class_base_list_becomes_bases(validator):
    source = (
        "public class AttendantService : BaseDapperRepository, IAttendantService\n"
        "{\n"
        "    public void Run() { }\n"
        "}\n"
    )
    artifacts = _impl(validator, source)
    cls = _find(artifacts, "AttendantService", ArtifactKind.CLASS)
    assert cls is not None
    assert set(cls.bases) == {"BaseDapperRepository", "IAttendantService"}


def test_private_and_internal_members_are_dropped(validator):
    source = (
        "public class Service\n"
        "{\n"
        "    private readonly Ctx _context;\n"
        "    private void Helper() { }\n"
        "    internal int Secret() { return 1; }\n"
        "    public void Api() { }\n"
        "}\n"
    )
    artifacts = _impl(validator, source)
    assert _find(artifacts, "Api", ArtifactKind.METHOD, of="Service") is not None
    assert _find(artifacts, "Helper") is None
    assert _find(artifacts, "Secret") is None
    assert _find(artifacts, "_context") is None


def test_public_property_and_field_become_attributes(validator):
    source = (
        "public class Model\n"
        "{\n"
        "    public string Name { get; set; }\n"
        "    public int Count;\n"
        "}\n"
    )
    artifacts = _impl(validator, source)
    name = _find(artifacts, "Name", ArtifactKind.ATTRIBUTE, of="Model")
    assert name is not None
    assert name.type_annotation == "string"
    assert _find(artifacts, "Count", ArtifactKind.ATTRIBUTE, of="Model") is not None


def test_enum_struct_record_delegate_kinds(validator):
    source = (
        "public enum Privilege { None, Reader }\n"
        "public struct Point { public int X; }\n"
        "public record PersonDto(string First, string Last);\n"
        "public delegate int Transformer(int input);\n"
    )
    artifacts = _impl(validator, source)
    assert _find(artifacts, "Privilege", ArtifactKind.ENUM) is not None
    assert _find(artifacts, "Point", ArtifactKind.CLASS) is not None
    assert _find(artifacts, "PersonDto", ArtifactKind.CLASS) is not None
    assert _find(artifacts, "Transformer", ArtifactKind.TYPE) is not None


def test_generic_method_records_type_parameters(validator):
    source = (
        "public class Repo\n"
        "{\n"
        "    public T? GetById<TKey>(TKey id) { return default; }\n"
        "}\n"
    )
    artifacts = _impl(validator, source)
    method = _find(artifacts, "GetById", ArtifactKind.METHOD, of="Repo")
    assert method is not None
    assert method.type_parameters == ("TKey",)
    assert method.returns == "T?"


def test_async_method_is_flagged_async(validator):
    source = (
        "public class Service\n"
        "{\n"
        "    public async Task<int> Load() { return 1; }\n"
        "}\n"
    )
    artifacts = _impl(validator, source)
    method = _find(artifacts, "Load", ArtifactKind.METHOD, of="Service")
    assert method is not None
    assert method.is_async is True


def test_top_level_local_function_is_function(validator):
    artifacts = _impl(validator, "int Add(int a, int b) { return a + b; }\n")
    fn = _find(artifacts, "Add", ArtifactKind.FUNCTION)
    assert fn is not None
    assert fn.of is None
    assert [a.name for a in fn.args] == ["a", "b"]


def test_parse_error_returns_errors_without_artifacts(validator):
    result = validator.collect_implementation_artifacts("public class {\n", "bad.cs")
    assert result.artifacts == []
    assert result.errors


def test_empty_source_returns_nothing(validator):
    result = validator.collect_implementation_artifacts("", "empty.cs")
    assert result.artifacts == []
    assert result.errors == []


def test_supported_extension_is_cs():
    assert CSharpValidator.supported_extensions() == (".cs",)
