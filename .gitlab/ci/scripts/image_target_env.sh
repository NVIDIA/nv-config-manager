#!/usr/bin/env bash
set -euo pipefail

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
  return 0
}

shell_export() {
  local name="$1"
  local value="$2"
  printf 'export %s=%q\n' "$name" "$value"
  return 0
}

parse_options() {
  local options="$1"
  local -n registry_ref="$2"
  local -n username_ref="$3"

  if [[ -z "$options" ]]; then
    return 0
  fi

  local raw_option option key value
  IFS=',' read -r -a option_items <<< "$options"
  for raw_option in "${option_items[@]}"; do
    option="$(trim "$raw_option")"
    [[ -z "$option" ]] && continue
    key="$(trim "${option%%=*}")"
    value="$(trim "${option#*=}")"
    case "$key" in
      registry) registry_ref="$value" ;;
      username) username_ref="$value" ;;
      *)
        echo "Unsupported image target option '${key}'." >&2
        exit 1
        ;;
    esac
  done
  return 0
}

select_target() {
  local requested_name="$1"
  local records="${NVCM_IMAGE_TARGETS:-}"

  NVCM_SELECTED_IMAGE_TARGET_NAME=""
  NVCM_SELECTED_IMAGE_REPOSITORY=""
  NVCM_SELECTED_IMAGE_TOKEN_VAR=""
  NVCM_SELECTED_IMAGE_REGISTRY=""
  NVCM_SELECTED_IMAGE_USERNAME=""

  if [[ -z "$records" ]]; then
    if [[ -z "${NVCM_IMAGE_REPOSITORY:-}" ]]; then
      echo "Set NVCM_IMAGE_TARGETS, or set legacy NVCM_IMAGE_REPOSITORY." >&2
      exit 1
    fi
    NVCM_SELECTED_IMAGE_TARGET_NAME="${requested_name:-default}"
    NVCM_SELECTED_IMAGE_REPOSITORY="${NVCM_IMAGE_REPOSITORY%/}"
    NVCM_SELECTED_IMAGE_TOKEN_VAR="${NVCM_IMAGE_TOKEN_VAR:-NGC_REGISTRY_TOKEN}"
    NVCM_SELECTED_IMAGE_REGISTRY="${NVCM_IMAGE_REGISTRY:-${NVCM_SELECTED_IMAGE_REPOSITORY%%/*}}"
    NVCM_SELECTED_IMAGE_USERNAME="${NVCM_IMAGE_USERNAME:-\$oauthtoken}"
    return 0
  fi

  local raw_line line name repository token_var options registry username
  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    line="$(trim "$raw_line")"
    [[ -z "$line" || "${line:0:1}" == "#" ]] && continue

    IFS='|' read -r name repository token_var options <<< "$line"
    name="$(trim "${name:-}")"
    repository="$(trim "${repository:-}")"
    token_var="$(trim "${token_var:-}")"
    options="$(trim "${options:-}")"

    if [[ -z "$name" || -z "$repository" || -z "$token_var" ]]; then
      echo "Invalid NVCM_IMAGE_TARGETS record '${line}'. Expected name|repository|token_var|options." >&2
      exit 1
    fi

    if [[ -n "$requested_name" && "$name" != "$requested_name" ]]; then
      continue
    fi

    registry=""
    username=""
    parse_options "$options" registry username

    NVCM_SELECTED_IMAGE_TARGET_NAME="$name"
    NVCM_SELECTED_IMAGE_REPOSITORY="${repository%/}"
    NVCM_SELECTED_IMAGE_TOKEN_VAR="$token_var"
    NVCM_SELECTED_IMAGE_REGISTRY="${registry:-${NVCM_SELECTED_IMAGE_REPOSITORY%%/*}}"
    NVCM_SELECTED_IMAGE_USERNAME="${username:-\$oauthtoken}"
    return 0
  done <<< "$records"

  if [[ -n "$requested_name" ]]; then
    echo "Image target '${requested_name}' was not found in NVCM_IMAGE_TARGETS." >&2
  else
    echo "NVCM_IMAGE_TARGETS does not contain any usable records." >&2
  fi
  return 1
}

target_name="${1:-${NVCM_IMAGE_TARGET:-}}"
select_target "$target_name"

shell_export NVCM_IMAGE_TARGET_NAME "$NVCM_SELECTED_IMAGE_TARGET_NAME"
shell_export NVCM_IMAGE_REPOSITORY "$NVCM_SELECTED_IMAGE_REPOSITORY"
shell_export NVCM_IMAGE_REGISTRY "$NVCM_SELECTED_IMAGE_REGISTRY"
shell_export NVCM_IMAGE_TOKEN_VAR "$NVCM_SELECTED_IMAGE_TOKEN_VAR"
shell_export NVCM_IMAGE_USERNAME "$NVCM_SELECTED_IMAGE_USERNAME"
