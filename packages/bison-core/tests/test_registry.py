import pytest


def test_registry():
    from bison_core.utils.registry import RegisteredClassCheckError, Registries, Registry

    class Base:
        pass

    platform: Registry[Base] = Registries.as_registry("platform")

    @platform.as_checker
    def check_platform(cls: type[object]) -> bool:
        return hasattr(cls, "test") and callable(getattr(cls, "test"))

    @platform.register
    class APlatform(Base):
        def test(self) -> None:
            pass

    with pytest.raises(RegisteredClassCheckError):

        @platform.register
        class BPlatform(Base):
            pass

    @platform.register(raise_on_failure=False)
    class CPlatform(Base):
        pass

    p: dict[str, type[Base]] = platform.members()

    assert p is not None
    assert p["APlatform"] is APlatform
    assert "BPlatform" not in p
    assert "CPlatform" not in p
