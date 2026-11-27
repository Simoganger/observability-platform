#!/usr/bin/env python3
"""Render the whole platform for one environment exactly like Argo CD would.

  python3 scripts/render.py kind            # → build/kind/<app>.yaml
  python3 scripts/render.py eks --strict    # non-zero exit on any render error

1. `helm template gitops/root` with values-<env>.yaml → list of Applications
2. for every Application: `helm template <chart>` with its value files,
   or `kustomize build <path>`
Used by CI (gitops-validate.yaml) and by `make render`. Requires helm, kubectl, PyYAML.
"""
import argparse
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> str:
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{res.stderr.strip()}")
    return res.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("env", choices=["kind", "eks", "gke", "existing"])
    ap.add_argument("--out", default="build")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    out = ROOT / args.out / args.env
    out.mkdir(parents=True, exist_ok=True)

    root = run(["helm", "template", "root", "gitops/root",
                "-f", "gitops/root/values.yaml", "-f", f"gitops/root/values-{args.env}.yaml",
                "--set", f"global.env={args.env}"])
    (out / "_root.yaml").write_text(root)
    apps = [d for d in yaml.safe_load_all(root) if d and d.get("kind") == "Application"]

    failures = 0
    for app in apps:
        name, spec = app["metadata"]["name"], app["spec"]
        ns = spec["destination"]["namespace"]
        try:
            if "sources" in spec:
                chart_src = next(s for s in spec["sources"] if "chart" in s)
                helm = chart_src.get("helm", {})
                repo, chart = chart_src["repoURL"], chart_src["chart"]
                # Argo CD writes OCI registries without a scheme (docker.io/org); helm needs oci://
                chart_ref = ([chart, "--repo", repo] if "://" in repo
                             else [f"oci://{repo.rstrip('/')}/{chart}"])
                cmd = ["helm", "template", helm.get("releaseName", name), *chart_ref,
                       "--version", str(chart_src["targetRevision"]),
                       "--namespace", ns, "--kube-version", "1.34.0", "--include-crds"]
                for vf in helm.get("valueFiles", []):
                    path = ROOT / vf.replace("$values/", "")
                    if path.exists():
                        cmd += ["-f", str(path)]
                rendered = run(cmd)
            elif "helm" in spec["source"]:
                # Local chart: value files are relative to the chart directory.
                src = spec["source"]
                cmd = ["helm", "template", src["helm"].get("releaseName", name), src["path"],
                       "--namespace", ns, "--kube-version", "1.34.0"]
                for vf in src["helm"].get("valueFiles", []):
                    path = ROOT / src["path"] / vf
                    if path.exists():
                        cmd += ["-f", str(path)]
                for param in src["helm"].get("parameters", []):
                    cmd += ["--set", f"{param['name']}={param['value']}"]
                rendered = run(cmd)
            else:
                rendered = run(["kubectl", "kustomize", spec["source"]["path"]])
            (out / f"{name}.yaml").write_text(rendered)
            kinds = sum(1 for line in rendered.splitlines() if line.startswith("kind:"))
            print(f"  ✔ {name:<24} {kinds:>4} objects  → {ns}")
        except RuntimeError as exc:
            failures += 1
            print(f"  ✘ {name}: {exc}", file=sys.stderr)

    print(f"{args.env}: {len(apps)} applications, {failures} failed → {out.relative_to(ROOT)}")
    return 1 if (failures and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
