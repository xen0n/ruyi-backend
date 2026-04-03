from pydantic import BaseModel, Field


class DistfileChecksums(BaseModel):
    sha256: str
    sha512: str


class DistfileMetadata(BaseModel):
    name: str
    size: int
    checksums: DistfileChecksums
    strip_components: int = 1
    """Number of leading path components to strip when unpacking."""


class BinaryHostDecl(BaseModel):
    host: str
    distfiles: list[str]


class BlobHostDecl(BaseModel):
    host: str
    distfiles: list[str]


class PackageVendorDecl(BaseModel):
    name: str
    eula: str = ""


class PackageMetadataDecl(BaseModel):
    desc: str
    vendor: PackageVendorDecl


class PackagePublishMetadata(BaseModel):
    """Metadata sent alongside a distfile upload."""

    category: str
    """Package category, e.g. 'toolchain', 'emulator', 'board-image'."""

    name: str
    """Package name, e.g. 'gnu-plct', 'box64-upstream'."""

    version: str
    """Package version, e.g. '0.20250401.0', '0.3.1-pre.ruyi.20240901'."""

    distfiles: list[DistfileMetadata]
    """Distfile declarations with names, sizes, and checksums."""

    binary: list[BinaryHostDecl] = Field(default_factory=list)
    """Binary host mappings (at least one of binary or blob required)."""

    blob: list[BlobHostDecl] = Field(default_factory=list)
    """Blob host mappings (at least one of binary or blob required)."""

    metadata: PackageMetadataDecl
    """Package metadata (description, vendor)."""
