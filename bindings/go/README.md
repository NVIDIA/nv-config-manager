# NVIDIA Config Manager Go Bindings

This module contains generated clients for every NVIDIA Config Manager OpenAPI service. The
packages are generated with OpenAPI Generator and committed so API changes are reviewable.

Install a specific platform release:

```bash
go get github.com/nvidia/nv-config-manager/bindings/go@v1.3.0
```

Import the service package you need. Generated packages use the name `openapi`, so an explicit
alias can make call sites clearer:

```go
import temporal "github.com/nvidia/nv-config-manager/bindings/go/temporal"
```

Regenerate every OpenAPI specification and Go client from the repository root:

```bash
make api-generate
```

Generation requires Docker; the command uses a version-and-digest-pinned OpenAPI Generator image.

Do not edit generated service directories by hand.
