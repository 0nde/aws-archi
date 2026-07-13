# Corresponding source information

The complete build recipe for every published image is the repository revision recorded by its provenance attestation. A `sha-*` tag provides a mutable source-traceability alias for source-triggered builds, but scheduled refreshes do not create or retarget that alias; use the attested revision together with the immutable image digest for exact identification. Source-authored files in this repository are available under Apache-2.0.

Terraform and TFLint are compiled from the exact release commits recorded in `.devcontainer/Dockerfile`. Terraform is governed by Business Source License 1.1. TFLint is distributed under Mozilla Public License 2.0 and includes Terraform-derived code governed by Business Source License 1.1. Their upstream source is available without charge from `https://github.com/hashicorp/terraform` and `https://github.com/terraform-linters/tflint`; the exact build recipe is the Dockerfile at the image revision.

Terragrunt and terraform-docs are also compiled from the exact commits recorded in `.devcontainer/Dockerfile`. Their source is available from `https://github.com/gruntwork-io/terragrunt` and `https://github.com/terraform-docs/terraform-docs`; dependency license reports are generated during the image build for every locally compiled Go tool.

Sources for Debian packages are available from the Debian source archives for the exact binary versions recorded in the image SBOM. Source for Python and npm packages remains available from their distributions and the upstream URLs recorded in their installed package metadata.

For assistance obtaining the exact corresponding source for an image digest, open a GitHub issue and include the digest. Source will be provided without charge. This offer remains valid while the corresponding image is distributed and for at least three years after its last distribution.
