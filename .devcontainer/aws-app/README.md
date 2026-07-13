# AWS application tooling

AWS SAM CLI and the AWS Session Manager plugin are intentionally excluded from the core image. They add a sizeable dependency surface and their independent release and signing lifecycles should not be hidden behind an unpinned `postCreateCommand`.

For a project that needs them:

1. start from `ghcr.io/0nde/aws-archi` pinned by digest in a project-specific Dockerfile;
2. select the official installer for the build architecture;
3. pin the desired release rather than downloading `latest`;
4. verify the installer signature and reviewed signer fingerprint using the current AWS procedure;
5. add the tool and its signer pin to that project's dependency-maintenance process;
6. use the repository's Docker profile when SAM container builds or local Lambda emulation are required.

AWS publishes installers for both `x86_64` and `arm64`. The official procedures and signer material are deliberately linked instead of copied here so a rotated or expired key is not presented as permanently current:

- [Install AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [Verify the AWS SAM CLI installer](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/reference-sam-cli-install-verify.html)
- [Install Session Manager on Debian or Ubuntu](https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-debian-and-ubuntu.html)
- [Verify the Session Manager installer](https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-linux-verify-signature.html)

This guidance keeps optional tooling auditable without enlarging or weakening the supported core image.
