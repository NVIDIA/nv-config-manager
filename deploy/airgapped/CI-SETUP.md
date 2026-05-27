# GitLab CI/CD Setup Guide

This guide explains how to set up airgapped bundle creation using GitLab CI/CD.

## Overview

The GitLab CI/CD pipeline provides **manual** airgapped bundle builds:
- ✅ **Manual trigger** - Click play button to build (avoids confusion with Nautobot bootstrap)
- ✅ Creates tarballs for both amd64 and arm64
- ✅ Creates releases with artifacts for tags
- ✅ Validates package integrity
- ✅ Includes an OCI registry upload helper for images and the packaged chart
- ✅ Uploads to S3 for distribution

## Prerequisites

1. GitLab repository with CI/CD enabled
2. GitLab Runner with Docker executor
3. NGC API Key from NVIDIA (for pulling NVCR images)
4. AWS credentials (for S3 uploads)

## Setup Steps

### 1. Get Your NGC API Key

1. Go to https://ngc.nvidia.com/setup/api-key
2. Sign in with your NVIDIA account
3. Click "Generate API Key"
4. Copy the key (you won't be able to see it again!)

### 2. Configure CI/CD Variables

Go to your GitLab project: **Settings > CI/CD > Variables**

#### Required Variables

| Key | Value | Type | Protected | Masked |
|-----|-------|------|-----------|--------|
| `NGC_REGISTRY_TOKEN` | Your NGC API key | Variable | ✓ | ✓ |
| `AWS_ACCESS_KEY_ID` | AWS access key | Variable | ✓ | ✓ |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Variable | ✓ | ✓ |

**Important:**
- ✅ **Check "Masked"** - Prevents the key from appearing in logs
- ✅ **Check "Protected"** - Only available on protected branches/tags
- ❌ **Uncheck "Expand variable reference"** - Use literal value

#### Optional Variables

| Key | Value | Description |
|-----|-------|-------------|
| `S3_BUCKET` | `nv-config-manager-tarballs` | Override S3 bucket name |
| `S3_REGION` | `us-west-2` | Override AWS region |
| `VERSION` | Custom version | Override automatic version detection |

### 3. Runner Configuration

Ensure your GitLab Runner has:

#### Docker Executor
```toml
[[runners]]
  executor = "docker"
  [runners.docker]
    privileged = true  # Required for containerd
    volumes = ["/certs/client", "/cache"]
```

#### Sufficient Resources
- **CPU**: 2+ cores
- **Memory**: 8GB+ RAM
- **Disk**: 50GB+ free space (Docker images are large)

### 4. Test the Pipeline

1. Commit and push to trigger the pipeline:
   ```bash
   git add .
   git commit -m "Add CI/CD pipeline"
   git push
   ```

2. Go to **CI/CD > Pipelines** to watch the build

3. Check the job logs for any errors

## Pipeline Stages

### Stage 1: Prepare
- `check:prerequisites` - Verifies NGC_REGISTRY_TOKEN is set, chart exists

### Stage 2: Build (MANUAL)
- `build:airgapped` - **Manual** - Creates the airgapped tarballs (amd64 + arm64)
- `publish:s3` - Uploads to S3 after build completes

### Stage 3: Test
- `test:extract` - Validates package structure
- `test:checksum` - Verifies SHA256 checksums
- `test:helm-lint` - Lints Helm chart
- `test:load-images` - Validates image tarballs

### Stage 4: Publish
- `prepare:release-info` - Extracts chart info for release notes
- `publish:release` - Creates GitLab Release with S3 links

## Triggering Builds

### Manual Trigger (Primary Method)

Airgapped bundle builds are **manual** to avoid confusion with Nautobot's "Load Bootstrap Data" job.

1. Go to **CI/CD > Pipelines**
2. Find the pipeline for your branch/tag
3. Click the **▶** (play) button next to `build:airgapped`
4. Wait for build to complete

#### On Tag (Release)
```bash
git tag v1.0.0
git push --tags
```
→ Creates pipeline, then click play on `build:airgapped-release` to create release tarballs

## Downloading Artifacts

### From S3 (Primary)

Artifacts are uploaded to S3 after the manual build completes:

```bash
# Latest (main branch or tags)
https://nv-config-manager-tarballs.s3.us-west-2.amazonaws.com/latest/nv-config-manager-airgapped-latest-amd64.tar.gz
https://nv-config-manager-tarballs.s3.us-west-2.amazonaws.com/latest/nv-config-manager-airgapped-latest-arm64.tar.gz

# Specific version
https://nv-config-manager-tarballs.s3.us-west-2.amazonaws.com/v1.0.0/nv-config-manager-airgapped-v1.0.0-amd64.tar.gz
https://nv-config-manager-tarballs.s3.us-west-2.amazonaws.com/v1.0.0/nv-config-manager-airgapped-v1.0.0-arm64.tar.gz

# Commit SHA version
https://nv-config-manager-tarballs.s3.us-west-2.amazonaws.com/a1b2c3d4/nv-config-manager-airgapped-a1b2c3d4-amd64.tar.gz
```

### From Releases Page (Tags)

1. Go to **Deployments > Releases**
2. Find your version
3. Click the download link

### Using AWS CLI

```bash
# Download specific version
aws s3 cp s3://nv-config-manager-tarballs/v1.0.0/nv-config-manager-airgapped-v1.0.0-amd64.tar.gz .

# Download latest
aws s3 cp s3://nv-config-manager-tarballs/latest/nv-config-manager-airgapped-latest-amd64.tar.gz .
```

## Customizing the Pipeline

### Change S3 Bucket

Edit `.gitlab-ci.yml` or set CI/CD variable:

```yaml
variables:
  S3_BUCKET: "my-custom-bucket"
  S3_REGION: "eu-west-1"
```

### Change Artifact Retention

```yaml
build:airgapped:
  artifacts:
    expire_in: 7 days  # Change from 1 hour
```

### Build Only One Architecture

For faster builds during development:

```yaml
build:airgapped:
  script:
    - ./airgapped/create-airgapped.sh --arch amd64 ...
```

### Add Slack Notifications

```yaml
notify:slack:
  stage: .post
  script:
    - |
      curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"Airgapped bundle build completed: ${CI_PIPELINE_URL}"}' \
        ${SLACK_WEBHOOK_URL}
  when: on_success
  only:
    - tags
```

## Troubleshooting

### Error: "NGC_REGISTRY_TOKEN not set"

**Solution:** Add NGC_REGISTRY_TOKEN to CI/CD variables (see Setup Steps above)

### Error: "Failed to pull image from nvcr.io"

**Possible causes:**
1. NGC_REGISTRY_TOKEN is incorrect or expired
2. NGC_REGISTRY_TOKEN is not masked properly
3. Network/firewall issues

**Solution:**
```bash
# Test your key locally
echo "YOUR_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin
docker pull nvcr.io/nvidian/cfa/nv-config-manager-dcim-deployment:latest
```

### Error: "Chart.yaml not found"

**Solution:** Ensure you're running the pipeline from the repository root where Chart.yaml exists

### Pipeline Stuck on "pending"

**Possible causes:**
1. No available runners
2. Runner doesn't have Docker executor
3. Runner resources exhausted

**Solution:** Check **Settings > CI/CD > Runners** and verify runner status

### S3 Upload Fails

**Possible causes:**
1. AWS credentials not set or incorrect
2. S3 bucket doesn't exist
3. IAM permissions insufficient

**Solution:**
```bash
# Test AWS credentials locally
aws sts get-caller-identity
aws s3 ls s3://nv-config-manager-tarballs/
```

### Large Tarball Size

The tarball can be several GB. To reduce size:
1. Build only for the architecture you need
2. Review `airgapped/extraimages.config` and remove unnecessary images

## Security Best Practices

### 1. Protect Your API Keys
- ✅ Always mask variables
- ✅ Use protected branches for releases
- ✅ Rotate keys periodically
- ❌ Never commit keys to git

### 2. Use Protected Tags for Releases
```bash
# Settings > Repository > Protected tags
# Protect tags matching: v*
```

### 3. Limit Runner Access
- Use specific runners for sensitive builds
- Tag runners and configure jobs to use them:
  ```yaml
  build:airgapped:
    tags:
      - secure-runner
  ```

### 4. Scan Images
Add a security scanning stage to your pipeline:

```yaml
test:security:
  stage: test
  image: aquasec/trivy:latest
  needs:
    - build:airgapped
  script:
    - cd ${OUTPUT_DIR}
    - TARBALL=$(ls nv-config-manager-airgapped-*.tar.gz | head -1)
    - mkdir -p extract && cd extract
    - tar -xzf "../${TARBALL}"
    - ROOT_FOLDER=$(basename "${TARBALL}" .tar.gz)
    - cd "${ROOT_FOLDER}/images"
    - |
      for img in *.tar; do
        echo "Scanning $img..."
        # Load and scan
        docker load -i "$img" 2>/dev/null || true
      done
    - trivy image --severity HIGH,CRITICAL --no-progress nvcr.io/nvidian/cfa/nv-config-manager-dcim-deployment
  allow_failure: true
  only:
    - tags
```

### 5. S3 Bucket Security
- Enable versioning
- Configure lifecycle policies
- Restrict public access (use signed URLs if needed)
- Enable server-side encryption

## Support

For issues:
1. Check job logs: **CI/CD > Jobs > [job name] > logs**
2. Verify runner status: **Settings > CI/CD > Runners**
3. Test locally: `./airgapped/create-airgapped.sh --help`
4. Review GitLab Runner logs on the runner host

