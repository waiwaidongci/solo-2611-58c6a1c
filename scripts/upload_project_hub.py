#!/usr/bin/env python3
"""Upload generated projects to a Project Hub instance through its admin API."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from batch_config import PROJECTS, project_id  # noqa: E402

API = os.environ.get("PROJECT_HUB_URL", "http://localhost:8088").rstrip("/")
TOKEN = os.environ.get("PROJECT_HUB_TOKEN", "")
GITHUB_URL = os.environ.get(
    "PROJECT_HUB_SOURCE_URL",
    "https://github.com/waiwaidongci/solo-2611-58c6a1c",
)
GITHUB_REF = os.environ.get(
    "PROJECT_HUB_SOURCE_REF",
    "58c6a1cbc7b392b8fcd696c81fc56c0ff53d286c",
)
TARGET_DOMAIN = "数据工程"
TARGET_SUBDOMAIN = "数据分析与数据应用"


def headers() -> dict[str, str]:
    if not TOKEN:
        raise RuntimeError("PROJECT_HUB_TOKEN 未设置")
    return {"Authorization": f"Bearer {TOKEN}"}


def get_target_tag() -> str:
    response = requests.get(f"{API}/api/v1/tags", headers=headers(), timeout=30)
    response.raise_for_status()
    payload = response.json()
    for domain in payload.get("items", []):
        if domain.get("name") != TARGET_DOMAIN:
            continue
        for child in domain.get("children", []):
            if child.get("name") == TARGET_SUBDOMAIN:
                return child["id"]
    raise RuntimeError(f"未找到标签：{TARGET_DOMAIN} / {TARGET_SUBDOMAIN}")


def git_archive(project: dict, workdir: Path) -> Path:
    pid = project_id(project)
    target = workdir / f"{pid}.zip"
    subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "archive",
            "--format=zip",
            f"--output={target}",
            f"HEAD:projects/{pid}",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    if target.stat().st_size == 0:
        raise RuntimeError(f"{pid} ZIP 为空")
    return target


def metadata(project: dict, tag_id: str) -> dict[str, str]:
    db = "PostgreSQL 16" if project["db"] == "postgres" else "MySQL 8.0"
    frontend = "React 18" if project["frontend"] == "react" else "Vue 3"
    tech_stack = [
        "Python",
        "FastAPI",
        frontend,
        "TypeScript",
        "SQLAlchemy",
        db,
        "Redis",
        "Celery",
        "Docker Compose",
    ]
    description = (
        f"{project['client']}。{project['context']}\n\n"
        f"现有流程：{project['workflow']}\n"
        f"核心痛点：{'；'.join(project['pains'])}。\n"
        f"核心算法：{'；'.join(project['algorithms'])}。\n"
        f"业务实体：{'、'.join(project['entities'])}。"
    )
    return {
        "name": project["name"],
        "description": description,
        "tech_stack": json.dumps(tech_stack, ensure_ascii=False),
        "tag_ids": json.dumps([tag_id]),
        "github_url": GITHUB_URL,
        "github_ref": GITHUB_REF,
    }


def poll_job(job_id: str, timeout_seconds: int = 240) -> dict:
    started = time.monotonic()
    while time.monotonic() - started < timeout_seconds:
        response = requests.get(
            f"{API}/api/v1/admin/analysis-jobs/{job_id}",
            headers=headers(),
            timeout=30,
        )
        response.raise_for_status()
        job = response.json()
        if job.get("status") == "ready":
            return job
        if job.get("status") == "failed":
            raise RuntimeError(f"分析失败：{job.get('error')}")
        time.sleep(1)
    raise RuntimeError(f"分析任务超时：{job_id}")


def verify_engineering(engineering_id: str, version_id: str, tag_id: str) -> dict:
    response = requests.get(
        f"{API}/api/v1/admin/engineering/{engineering_id}",
        headers=headers(),
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    version = next(
        (item for item in payload.get("versions", []) if item.get("id") == version_id),
        None,
    )
    if not version:
        raise RuntimeError(f"工程详情缺少版本 {version_id}")
    if version.get("status") != "ready":
        raise RuntimeError(f"版本状态不是 ready：{version.get('status')}")
    if version.get("source_file_count", 0) <= 0:
        raise RuntimeError("源码文件分析结果为 0")
    if len(version.get("assets", [])) != 6:
        raise RuntimeError(f"截图资产数量不是 6：{len(version.get('assets', []))}")
    tags = payload.get("engineering", {}).get("tags", [])
    if tag_id not in {item.get("id") for item in tags}:
        raise RuntimeError("工程标签校验失败")
    return {
        "engineering_id": engineering_id,
        "version_id": version_id,
        "version_number": version.get("version_number"),
        "source_file_count": version.get("source_file_count"),
        "total_file_count": version.get("total_file_count"),
        "assets": len(version.get("assets", [])),
        "tags": [item.get("name") for item in tags],
    }


def upload_one(project: dict, tag_id: str, workdir: Path) -> dict:
    pid = project_id(project)
    zip_path = git_archive(project, workdir)
    screenshot_dir = ROOT / "test-artifacts" / pid / "screenshots"
    files = [("zip", (zip_path.name, zip_path.read_bytes(), "application/zip"))]
    files.append(
        (
            "startup_screenshot",
            ("01-login.png", (screenshot_dir / "01-login.png").read_bytes(), "image/png"),
        )
    )
    for name in (
        "02-overview.png",
        "03-datasets.png",
        "04-analyses.png",
        "05-result.png",
        "06-result-viewport.png",
    ):
        files.append(
            ("feature_screenshots", (name, (screenshot_dir / name).read_bytes(), "image/png"))
        )
    response = requests.post(
        f"{API}/api/v1/admin/engineering-versions",
        headers=headers(),
        data=metadata(project, tag_id),
        files=files,
        timeout=180,
    )
    if response.status_code != 201:
        raise RuntimeError(f"{pid} 上传失败 {response.status_code}：{response.text[:1000]}")
    result = response.json()
    poll_job(result["job_id"])
    verified = verify_engineering(result["engineering_id"], result["version_id"], tag_id)
    return {
        "id": pid,
        "name": project["name"],
        "status": "pass",
        "job_id": result["job_id"],
        "backup_status": result.get("backup_status"),
        **verified,
    }


def load_existing() -> dict[str, dict]:
    response = requests.get(
        f"{API}/api/v1/admin/engineering",
        headers=headers(),
        params={"page": 1, "page_size": 100},
        timeout=30,
    )
    response.raise_for_status()
    return {item["name"]: item for item in response.json().get("items", [])}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="*", help="仅上传指定 gb-xxxx")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument(
        "--results",
        default=str(ROOT / "test-artifacts" / "project-hub-upload.json"),
    )
    args = parser.parse_args()

    selected = [
        item
        for item in PROJECTS
        if not args.ids or project_id(item) in set(args.ids)
    ]
    if not selected:
        raise RuntimeError("没有匹配的项目")

    tag_id = get_target_tag()
    existing = load_existing()
    already = [project_id(item) for item in selected if item["name"] in existing]
    if already:
        raise RuntimeError(f"工程已存在，拒绝重复创建：{', '.join(already)}")

    results = []
    with tempfile.TemporaryDirectory(prefix="project-hub-upload-") as temp:
        workdir = Path(temp)
        with ThreadPoolExecutor(max_workers=max(1, min(args.concurrency, 3))) as pool:
            futures = {
                pool.submit(upload_one, project, tag_id, workdir): project
                for project in selected
            }
            for future in as_completed(futures):
                project = futures[future]
                pid = project_id(project)
                try:
                    result = future.result()
                    results.append(result)
                    print(
                        f"PASS {pid} {project['name']} "
                        f"files={result['source_file_count']} assets={result['assets']}",
                        flush=True,
                    )
                except Exception as exc:
                    result = {
                        "id": pid,
                        "name": project["name"],
                        "status": "failed",
                        "error": str(exc),
                    }
                    results.append(result)
                    print(f"FAIL {pid} {exc}", flush=True)

    results.sort(key=lambda item: item["id"])
    payload = {
        "project_hub": API,
        "github_url": GITHUB_URL,
        "github_ref": GITHUB_REF,
        "tag_id": tag_id,
        "uploaded": sum(item["status"] == "pass" for item in results),
        "failed": sum(item["status"] == "failed" for item in results),
        "items": results,
    }
    Path(args.results).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"RESULT uploaded={payload['uploaded']} failed={payload['failed']} "
        f"manifest={args.results}",
        flush=True,
    )
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
