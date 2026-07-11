# Corresponding source information

The complete build recipe for every published image is the repository revision recorded by its provenance attestation and `sha-*` tag. Source-authored files in this repository are available under Apache-2.0.

TFLint is distributed in executable form under Mozilla Public License 2.0 and includes Terraform-derived code governed by Business Source License 1.1. The corresponding upstream Source Code Form for the pinned version is available without charge from `https://github.com/terraform-linters/tflint`, while the exact build recipe is the Dockerfile at the image revision.

Terragrunt and terraform-docs are compiled from the exact commits recorded in `.devcontainer/Dockerfile`. Their source is available from `https://github.com/gruntwork-io/terragrunt` and `https://github.com/terraform-docs/terraform-docs`; dependency license reports are generated during the image build.

Sources for Debian packages are available from the Debian source archives for the exact binary versions recorded in the image SBOM. Source for Python and npm packages remains available from their distributions and the upstream URLs recorded in their installed package metadata.

For assistance obtaining the exact corresponding source for an image digest, open a GitHub issue and include the digest. Source will be provided without charge. This offer remains valid while the corresponding image is distributed and for at least three years after its last distribution.
