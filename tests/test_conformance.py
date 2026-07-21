"""C# validator conformance against the public MAID Runner kit.

Passing this suite is the acceptance bar for the plugin: it proves the
collector cannot manufacture false-green validation for C#.
"""

from __future__ import annotations

from maid_runner.core.types import ArtifactKind
from maid_runner.testing.validator_conformance import (
    ConformanceArtifactSample,
    ConformanceFixtures,
    make_conformance_suite,
)

from maid_validator_csharp import CSharpValidator


def _fixtures() -> ConformanceFixtures:
    return ConformanceFixtures(
        extension=".cs",
        artifact_samples={
            ArtifactKind.CLASS.value: ConformanceArtifactSample(
                source="namespace N { public class Widget {} }\n",
                expected_name="Widget",
            ),
            ArtifactKind.FUNCTION.value: ConformanceArtifactSample(
                source="int Render() { return 1; }\n",
                expected_name="Render",
            ),
            ArtifactKind.METHOD.value: ConformanceArtifactSample(
                source="public class Widget { public void Draw() {} }\n",
                expected_name="Draw",
                expected_of="Widget",
            ),
            ArtifactKind.ATTRIBUTE.value: ConformanceArtifactSample(
                source=("public class Widget { public string Id { get; set; } }\n"),
                expected_name="Id",
                expected_of="Widget",
            ),
        },
        private_artifact_source="int _helper() { return 1; }\n",
        behavioral_target_kind=ArtifactKind.CLASS.value,
        behavioral_target_name="Widget",
        behavioral_target_of=None,
        behavioral_correct_source=(
            "using Xunit;\n\n"
            "public class UsageTests\n"
            "{\n"
            "    [Fact]\n"
            "    public void Creates() { var w = new Widget(); }\n"
            "}\n"
        ),
        behavioral_wrong_identity_source=(
            "using Xunit;\n\n"
            "public class OtherTests\n"
            "{\n"
            "    [Fact]\n"
            "    public void Creates() { var g = new Gadget(); }\n"
            "}\n"
        ),
        unparseable_source="public class {\n",
        empty_source="",
    )


TestCSharpValidatorConformance = make_conformance_suite(CSharpValidator, _fixtures())
