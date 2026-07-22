"""Behavioral identity regressions derived from a real C# MAID contract."""

from maid_runner.core.types import ArtifactKind

from maid_validator_csharp import CSharpValidator


def _identities(source: str) -> set[tuple[ArtifactKind, str, str | None]]:
    result = CSharpValidator().collect_behavioral_artifacts(source, "WorkflowTests.cs")
    assert result.errors == []
    return {
        (artifact.kind, artifact.name, artifact.of) for artifact in result.artifacts
    }


def test_type_annotations_cover_interface_identity_and_resolve_method_owner():
    identities = _identities("""
        public class WorkflowTests {
            [TestMethod]
            public async Task Calls() {
                IWorkflowService service = new WorkflowService();
                await service.BroadcastAsync();
            }
        }
        """)

    assert (ArtifactKind.INTERFACE, "IWorkflowService", None) in identities
    assert (ArtifactKind.CLASS, "WorkflowService", None) in identities
    assert (ArtifactKind.METHOD, "BroadcastAsync", "IWorkflowService") in identities
    assert (ArtifactKind.METHOD, "BroadcastAsync", "WorkflowService") in identities


def test_var_object_creation_resolves_instance_method_owner():
    identities = _identities("""
        public class WorkflowTests {
            [TestMethod]
            public async Task Calls() {
                var service = new WorkflowService();
                await service.CompleteAsync();
            }
        }
        """)

    assert (ArtifactKind.METHOD, "CompleteAsync", "WorkflowService") in identities


def test_object_initializer_members_cover_class_attributes():
    identities = _identities("""
        public class WorkflowTests {
            [TestMethod]
            public void Builds() {
                var details = new InductionDetailsVm {
                    Location = "Hall",
                    VolunteerId = 200
                };
            }
        }
        """)

    assert (ArtifactKind.ATTRIBUTE, "Location", "InductionDetailsVm") in identities
    assert (ArtifactKind.ATTRIBUTE, "VolunteerId", "InductionDetailsVm") in identities


def test_typeof_and_nameof_cover_interface_method_identity():
    identities = _identities("""
        public class WorkflowTests {
            [TestMethod]
            public void Inspects() {
                var senderType = typeof(IInductionEmailSender);
                var method = nameof(IInductionEmailSender.SendRequestAsync);
            }
        }
        """)

    assert (ArtifactKind.INTERFACE, "IInductionEmailSender", None) in identities
    assert (
        ArtifactKind.METHOD,
        "SendRequestAsync",
        "IInductionEmailSender",
    ) in identities


def test_receiver_bindings_do_not_leak_between_test_methods():
    identities = _identities("""
        public class WorkflowTests {
            [TestMethod]
            public void First() {
                IFoo service = new Foo();
                service.Run();
            }
            [TestMethod]
            public void Second() {
                IBar service = new Bar();
                service.Stop();
            }
        }
        """)

    assert (ArtifactKind.METHOD, "Run", "IFoo") in identities
    assert (ArtifactKind.METHOD, "Run", "Foo") in identities
    assert (ArtifactKind.METHOD, "Run", "IBar") not in identities
    assert (ArtifactKind.METHOD, "Run", "Bar") not in identities
    assert (ArtifactKind.METHOD, "Stop", "IBar") in identities
    assert (ArtifactKind.METHOD, "Stop", "Bar") in identities
    assert (ArtifactKind.METHOD, "Stop", "IFoo") not in identities
    assert (ArtifactKind.METHOD, "Stop", "Foo") not in identities


def test_receiver_bindings_do_not_leak_between_lexical_blocks():
    identities = _identities("""
        public class WorkflowTests {
            [TestMethod]
            public void Calls() {
                { IFoo service = new Foo(); service.Run(); }
                { IBar service = new Bar(); service.Stop(); }
            }
        }
        """)

    assert (ArtifactKind.METHOD, "Run", "IFoo") in identities
    assert (ArtifactKind.METHOD, "Run", "Foo") in identities
    assert (ArtifactKind.METHOD, "Run", "IBar") not in identities
    assert (ArtifactKind.METHOD, "Run", "Bar") not in identities
    assert (ArtifactKind.METHOD, "Stop", "IBar") in identities
    assert (ArtifactKind.METHOD, "Stop", "Bar") in identities
    assert (ArtifactKind.METHOD, "Stop", "IFoo") not in identities
    assert (ArtifactKind.METHOD, "Stop", "Foo") not in identities


def test_nullable_and_qualified_generic_types_use_base_identity():
    identities = _identities("""
        public class WorkflowTests {
            [TestMethod]
            public void Calls() {
                IFoo? nullable = new Foo();
                Demo.IService<string> generic = new Service();
                nullable.Run();
                generic.Send();
            }
        }
        """)

    assert (ArtifactKind.INTERFACE, "IFoo", None) in identities
    assert (ArtifactKind.METHOD, "Run", "IFoo") in identities
    assert (ArtifactKind.INTERFACE, "IService", None) in identities
    assert (ArtifactKind.METHOD, "Send", "IService") in identities
    assert all(artifact[1] != "IService<string>" for artifact in identities)


def test_qualified_nameof_uses_terminal_method_and_type_owner():
    identities = _identities("""
        public class WorkflowTests {
            [TestMethod]
            public void Inspects() {
                var method = nameof(Demo.IEmailSender.SendAsync);
            }
        }
        """)

    assert (ArtifactKind.METHOD, "SendAsync", "IEmailSender") in identities
    assert (ArtifactKind.METHOD, "IEmailSender", "Demo") not in identities


def test_target_typed_object_initializer_covers_attributes():
    identities = _identities("""
        public class WorkflowTests {
            [TestMethod]
            public void Builds() {
                InductionDetailsVm details = new() { Location = "Hall" };
            }
        }
        """)

    assert (ArtifactKind.CLASS, "InductionDetailsVm", None) in identities
    assert (ArtifactKind.ATTRIBUTE, "Location", "InductionDetailsVm") in identities
