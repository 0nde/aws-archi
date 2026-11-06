#!/usr/bin/env bash
set -euo pipefail

repository=$1
digest=$2
immutable_tag=$3
shift 3
[[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]
test "$#" -gt 0

normalized_repository=$repository
if [[ "${repository%%/*}" != *.* ]]; then
  normalized_repository="docker.io/$repository"
fi

tag_args=()
for tag in "$@"; do
  [[ "$tag" == "$repository:"* ]]
  if [[ "$tag" == "$repository:$immutable_tag" ]]; then
    if existing=$(docker buildx imagetools inspect "$tag" --format '{{.Manifest.Digest}}' 2>&1); then
      if [[ "$existing" != "$digest" ]]; then
        printf 'Refusing to change immutable tag %s from %s to %s\n' "$tag" "$existing" "$digest" >&2
        exit 1
      fi
    elif [[ "$existing" != "ERROR: $normalized_repository:$immutable_tag: not found" ]]; then
      printf '%s\n' "$existing" >&2
      exit 1
    fi
  fi
  tag_args+=(--tag "$tag")
done

docker buildx imagetools create "${tag_args[@]}" "$repository@$digest"
for tag in "$@"; do
  actual=$(docker buildx imagetools inspect "$tag" --format '{{.Manifest.Digest}}')
  if [[ "$actual" != "$digest" ]]; then
    printf 'Tag %s resolved to %s, expected %s\n' "$tag" "$actual" "$digest" >&2
    exit 1
  fi
done
