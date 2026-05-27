#!/usr/bin/env bash
# Upload NVIDIA Config Manager bundle images and Helm chart to an OCI-compliant registry.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'EOF'
Usage: ./upload-to-registry.sh --registry <registry-host/project> [options]

Uploads images from images/image-list.txt and the packaged Helm chart from helm/.
By default image source paths are preserved below the target project, e.g.:
  nvcr.io/nvidian/cfa/nv-config-manager:v1
    -> registry.example.com/nv-config-manager/nvidian/cfa/nv-config-manager:v1

Options:
  --registry REGISTRY/PROJECT        Target image registry namespace
  --chart-registry REGISTRY/PROJECT  Target OCI chart registry namespace (default: <registry>/charts)
  --images-dir DIR                   Image tarball directory (default: ./images)
  --chart-dir DIR                    Helm chart directory (default: ./helm)
  --charts-dir DIR                   Dependency chart directory (default: ./charts)
  --include-dependency-charts        Also push charts/*.tgz in addition to the main chart
  --username USER                    Registry username or robot/service account
  --password PASS                    Registry password/token
  --password-stdin                   Read registry password/token from stdin
  --skip-login                       Do not run docker/helm registry login
  --mode auto|skopeo|docker          Image upload backend (default: auto; prefers bundled/system skopeo)
  --platform OS/ARCH                Docker push platform for architecture-specific bundles, for example linux/amd64
  --flatten                          Push images directly under REGISTRY/PROJECT by basename
  --insecure                         Disable TLS verification for skopeo image uploads
  --plain-http                       Use plain HTTP for Helm chart uploads to local registries
  --skip-images                      Upload chart only
  --skip-chart                       Upload images only
  --dry-run                          Print upload plan without pushing
  --map-file FILE                    Write image source-to-target map (default: image-map.tsv)
  -h, --help                         Show this help

Environment equivalents:
  OCI_REGISTRY, OCI_CHART_REGISTRY, REGISTRY_USERNAME, REGISTRY_PASSWORD,
  IMAGES_DIR, CHART_DIR, CHARTS_DIR, UPLOAD_MODE, UPLOAD_PLATFORM, SKOPEO_BIN
EOF
}

REGISTRY_NAMESPACE="${OCI_REGISTRY:-}"
CHART_REGISTRY="${OCI_CHART_REGISTRY:-}"
IMAGES_DIR="${IMAGES_DIR:-images}"
CHART_DIR="${CHART_DIR:-helm}"
CHARTS_DIR="${CHARTS_DIR:-charts}"
REGISTRY_USERNAME="${REGISTRY_USERNAME:-}"
REGISTRY_PASSWORD="${REGISTRY_PASSWORD:-}"
SKOPEO_BIN="${SKOPEO_BIN:-}"
PASSWORD_STDIN=false
SKIP_LOGIN=false
MODE="${UPLOAD_MODE:-auto}"
UPLOAD_PLATFORM="${UPLOAD_PLATFORM:-}"
FLATTEN=false
INSECURE=false
PLAIN_HTTP=false
DRY_RUN=false
SKIP_IMAGES=false
SKIP_CHART=false
INCLUDE_DEPENDENCY_CHARTS=false
MAP_FILE="image-map.tsv"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --registry) REGISTRY_NAMESPACE="$2"; shift 2 ;;
        --chart-registry) CHART_REGISTRY="$2"; shift 2 ;;
        --images-dir) IMAGES_DIR="$2"; shift 2 ;;
        --chart-dir) CHART_DIR="$2"; shift 2 ;;
        --charts-dir) CHARTS_DIR="$2"; shift 2 ;;
        --include-dependency-charts) INCLUDE_DEPENDENCY_CHARTS=true; shift ;;
        --username) REGISTRY_USERNAME="$2"; shift 2 ;;
        --password) REGISTRY_PASSWORD="$2"; shift 2 ;;
        --password-stdin) PASSWORD_STDIN=true; shift ;;
        --skip-login) SKIP_LOGIN=true; shift ;;
        --mode) MODE="$2"; shift 2 ;;
        --platform) UPLOAD_PLATFORM="$2"; shift 2 ;;
        --flatten) FLATTEN=true; shift ;;
        --insecure) INSECURE=true; shift ;;
        --plain-http) PLAIN_HTTP=true; shift ;;
        --skip-images) SKIP_IMAGES=true; shift ;;
        --skip-chart) SKIP_CHART=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --map-file) MAP_FILE="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
    esac
done

strip_registry_scheme() {
    local value="$1"
    value="${value#http://}"
    value="${value#https://}"
    value="${value#oci://}"
    value="${value%/}"
    printf '%s\n' "$value"
}

find_skopeo() {
    if [[ -n "$SKOPEO_BIN" ]]; then
        if [[ ! -x "$SKOPEO_BIN" ]]; then
            echo "ERROR: SKOPEO_BIN is not executable: $SKOPEO_BIN" >&2
            return 1
        fi
        return 0
    fi

    local bundled="$SCRIPT_DIR/tools/skopeo/skopeo"
    if [[ -x "$bundled" ]]; then
        SKOPEO_BIN="$bundled"
        return 0
    fi

    if command -v skopeo >/dev/null 2>&1; then
        SKOPEO_BIN="$(command -v skopeo)"
        return 0
    fi

    return 1
}

if [[ -z "$REGISTRY_NAMESPACE" && "$SKIP_IMAGES" != true ]]; then
    echo "ERROR: --registry is required unless --skip-images is set" >&2
    exit 1
fi
if [[ -z "$REGISTRY_NAMESPACE" && -z "$CHART_REGISTRY" && "$SKIP_CHART" != true ]]; then
    echo "ERROR: --registry or --chart-registry is required unless --skip-chart is set" >&2
    exit 1
fi

REGISTRY_NAMESPACE="$(strip_registry_scheme "$REGISTRY_NAMESPACE")"
if [[ -z "$CHART_REGISTRY" && -n "$REGISTRY_NAMESPACE" ]]; then
    CHART_REGISTRY="${REGISTRY_NAMESPACE}/charts"
fi
CHART_REGISTRY="$(strip_registry_scheme "$CHART_REGISTRY")"
REGISTRY_HOST="${REGISTRY_NAMESPACE%%/*}"
CHART_REGISTRY_HOST="${CHART_REGISTRY%%/*}"
IMAGE_LIST="${IMAGES_DIR%/}/image-list.txt"

case "$MODE" in
    auto|skopeo|docker) ;;
    *) echo "ERROR: --mode must be auto, skopeo, or docker" >&2; exit 1 ;;
esac

if [[ "$PASSWORD_STDIN" == true ]]; then
    IFS= read -r REGISTRY_PASSWORD
fi

if [[ "$SKIP_IMAGES" != true ]]; then
    if [[ ! -f "$IMAGE_LIST" ]]; then
        echo "ERROR: image list not found: $IMAGE_LIST" >&2
        exit 1
    fi
    if [[ "$DRY_RUN" != true ]]; then
        if [[ "$MODE" == "auto" ]]; then
            if [[ -n "$SKOPEO_BIN" || -x "$SCRIPT_DIR/tools/skopeo/skopeo" ]] || command -v skopeo >/dev/null 2>&1; then
                find_skopeo || exit 1
                MODE="skopeo"
            elif command -v docker >/dev/null 2>&1; then
                MODE="docker"
            else
                echo "ERROR: install skopeo or docker to upload images, or pass --skip-images" >&2
                exit 1
            fi
        elif [[ "$MODE" == "skopeo" ]]; then
            find_skopeo || {
                echo "ERROR: skopeo mode requested but no Skopeo binary was found" >&2
                exit 1
            }
        elif [[ "$MODE" == "docker" ]] && ! command -v docker >/dev/null 2>&1; then
            echo "ERROR: docker mode requested but docker was not found" >&2
            exit 1
        fi
    fi
fi

if [[ "$SKIP_CHART" != true && "$DRY_RUN" != true ]] && ! command -v helm >/dev/null 2>&1; then
    echo "ERROR: helm is required to upload the chart, or pass --skip-chart" >&2
    exit 1
fi

image_to_filename() {
    local image="$1"
    echo "${image}" | sed 's|[/:@]|-|g; s|$|.tar|'
}

target_ref() {
    local image="$1"
    local ref_no_digest="$image"
    local digest_tag=""

    if [[ "$image" == *@* ]]; then
        ref_no_digest="${image%@*}"
        digest_tag="${image#*@}"
        digest_tag="${digest_tag//:/-}"
    fi

    local repo="$ref_no_digest"
    local tag="latest"
    local last_component="${repo##*/}"
    if [[ "$last_component" == *:* ]]; then
        tag="${last_component##*:}"
        repo="${repo%:*}"
    fi
    if [[ -n "$digest_tag" ]]; then
        tag="$digest_tag"
    fi

    local path="$repo"
    local first_segment="${repo%%/*}"
    if [[ "$repo" == */* ]] && { [[ "$first_segment" == *.* ]] || [[ "$first_segment" == *:* ]] || [[ "$first_segment" == "localhost" ]]; }; then
        path="${repo#*/}"
    fi
    if [[ "$FLATTEN" == true ]]; then
        path="${path##*/}"
    fi

    printf '%s/%s:%s\n' "$REGISTRY_NAMESPACE" "$path" "$tag"
}

copy_with_skopeo() {
    local archive="$1"
    local source="$2"
    local target="$3"
    local args=(copy)
    if [[ "$INSECURE" == true ]]; then
        args+=(--dest-tls-verify=false)
    fi
    if [[ -n "$REGISTRY_USERNAME" ]]; then
        args+=(--dest-creds "${REGISTRY_USERNAME}:${REGISTRY_PASSWORD}")
    fi
    if "$SKOPEO_BIN" "${args[@]}" "docker-archive:${archive}:${source}" "docker://${target}"; then
        return 0
    fi
    "$SKOPEO_BIN" "${args[@]}" "oci-archive:${archive}:${source}" "docker://${target}"
}

copy_with_docker() {
    local archive="$1"
    local source="$2"
    local target="$3"
    local load_output
    load_output=$(docker load -i "$archive")

    local loaded_ref="$source"
    if ! docker image inspect "$loaded_ref" >/dev/null 2>&1; then
        loaded_ref=$(echo "$load_output" | awk -F': ' '/Loaded image:/ {print $2; exit} /Loaded image ID:/ {print $2; exit}')
    fi
    if [[ -z "$loaded_ref" ]]; then
        echo "ERROR: could not identify loaded image for $archive" >&2
        echo "$load_output" >&2
        return 1
    fi

    docker tag "$loaded_ref" "$target"
    local push_args=(push)
    if [[ -n "$UPLOAD_PLATFORM" ]]; then
        push_args+=(--platform "$UPLOAD_PLATFORM")
    fi
    docker "${push_args[@]}" "$target"
}

login_for_images() {
    if [[ "$SKIP_LOGIN" == true || -z "$REGISTRY_USERNAME" || "$DRY_RUN" == true ]]; then
        return
    fi
    if [[ "$MODE" == "docker" ]]; then
        if [[ -z "$REGISTRY_PASSWORD" ]]; then
            echo "ERROR: docker login requested but no password was provided" >&2
            exit 1
        fi
        echo "$REGISTRY_PASSWORD" | docker login "$REGISTRY_HOST" --username "$REGISTRY_USERNAME" --password-stdin
    fi
}

login_for_chart() {
    if [[ "$SKIP_LOGIN" == true || -z "$REGISTRY_USERNAME" || "$DRY_RUN" == true ]]; then
        return
    fi
    if [[ -z "$REGISTRY_PASSWORD" ]]; then
        echo "ERROR: helm registry login requested but no password was provided" >&2
        exit 1
    fi
    echo "$REGISTRY_PASSWORD" | helm registry login "$CHART_REGISTRY_HOST" --username "$REGISTRY_USERNAME" --password-stdin
}

upload_images() {
    if [[ "$SKIP_IMAGES" == true ]]; then
        echo "Skipping image upload"
        return
    fi
    login_for_images
    if [[ "$MODE" == "docker" && "$INSECURE" == true ]]; then
        echo "WARNING: --insecure cannot reconfigure Docker daemon TLS behavior; configure insecure registries in Docker if needed." >&2
    fi

    : > "$MAP_FILE"
    local count=0
    while IFS= read -r source || [[ -n "$source" ]]; do
        [[ -z "$source" || "$source" =~ ^[[:space:]]*# ]] && continue
        local archive="${IMAGES_DIR%/}/$(image_to_filename "$source")"
        local target
        target="$(target_ref "$source")"
        printf '%s\t%s\n' "$source" "$target" >> "$MAP_FILE"

        if [[ ! -f "$archive" ]]; then
            echo "ERROR: archive missing for $source: $archive" >&2
            exit 1
        fi

        echo "Uploading image $source -> $target"
        if [[ "$DRY_RUN" == true ]]; then
            count=$((count + 1))
            continue
        fi

        if [[ "$MODE" == "skopeo" ]]; then
            copy_with_skopeo "$archive" "$source" "$target"
        else
            copy_with_docker "$archive" "$source" "$target"
        fi
        count=$((count + 1))
    done < "$IMAGE_LIST"
    echo "Uploaded ${count} image(s). Source-to-target map: $MAP_FILE"
}

collect_charts() {
    local charts=()
    while IFS= read -r chart; do
        [[ -n "$chart" ]] && charts+=("$chart")
    done < <(find "$CHART_DIR" -maxdepth 1 -name 'nv-config-manager-*.tgz' -type f 2>/dev/null | sort)

    if [[ ${#charts[@]} -eq 0 && -f "$CHART_DIR/Chart.yaml" ]]; then
        local packaged_dir
        packaged_dir=$(mktemp -d)
        helm package "$CHART_DIR" --destination "$packaged_dir" >/dev/null
        while IFS= read -r chart; do
            [[ -n "$chart" ]] && charts+=("$chart")
        done < <(find "$packaged_dir" -maxdepth 1 -name 'nv-config-manager-*.tgz' -type f | sort)
    fi

    if [[ "$INCLUDE_DEPENDENCY_CHARTS" == true && -d "$CHARTS_DIR" ]]; then
        while IFS= read -r chart; do
            [[ -n "$chart" ]] && charts+=("$chart")
        done < <(find "$CHARTS_DIR" -maxdepth 1 -name '*.tgz' -type f | sort)
    fi

    printf '%s\n' "${charts[@]}"
}

upload_charts() {
    if [[ "$SKIP_CHART" == true ]]; then
        echo "Skipping chart upload"
        return
    fi
    login_for_chart

    local count=0
    while IFS= read -r chart; do
        [[ -n "$chart" ]] || continue
        echo "Uploading chart $chart -> oci://${CHART_REGISTRY}"
        if [[ "$DRY_RUN" != true ]]; then
            local helm_args=(push "$chart" "oci://${CHART_REGISTRY}")
            if [[ "$PLAIN_HTTP" == true ]]; then
                helm_args+=(--plain-http)
            fi
            helm "${helm_args[@]}"
        fi
        count=$((count + 1))
    done < <(collect_charts)

    if [[ "$count" -eq 0 ]]; then
        echo "ERROR: no chart archives found in $CHART_DIR" >&2
        exit 1
    fi
    echo "Uploaded ${count} chart(s) to oci://${CHART_REGISTRY}"
}

upload_images
upload_charts
