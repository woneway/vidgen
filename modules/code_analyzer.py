"""代码项目分析模块 — 扫描项目目录，提取结构化分析结果"""
from __future__ import annotations

import configparser
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import httpx


@dataclass
class ProjectAnalysis:
    name: str
    description: str
    tech_stack: list[str]
    languages: dict[str, int]      # {"Python": 3287, ...} LOC per language
    total_files: int
    total_loc: int
    structure: str                  # 树形目录结构
    entry_points: list[str]
    dependencies: list[str]
    test_info: str
    readme_summary: str
    github_url: str | None
    github_stats: dict | None      # {stars, forks, contributors}
    key_features: list[str]
    code_examples: list[dict] = field(default_factory=list)  # [{filename, code, language}]


# 文件扩展名 → 语言名
_EXT_MAP = {
    ".py": "Python", ".pyx": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".cs": "C#",
    ".php": "PHP",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".yml": "YAML", ".yaml": "YAML",
    ".json": "JSON",
    ".md": "Markdown",
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".less": "Less",
    ".sql": "SQL",
    ".r": "R", ".R": "R",
    ".lua": "Lua",
    ".dart": "Dart",
    ".ex": "Elixir", ".exs": "Elixir",
}

# 跳过的目录
_SKIP_DIRS = {
    "node_modules", "venv", ".venv", "env", ".env",
    ".git", ".svn", ".hg",
    "dist", "build", "target", "out", "__pycache__",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "vendor", "Pods", ".gradle", ".idea", ".vscode",
    "coverage", "htmlcov", ".next", ".nuxt",
    "egg-info", ".eggs",
}


async def analyze_project(project_path: str) -> ProjectAnalysis:
    """扫描项目目录，返回结构化分析结果"""
    root = Path(project_path).resolve()
    if not root.is_dir():
        raise ValueError(f"路径不存在或不是目录: {project_path}")

    # 快速分析（用于后续并发依赖）
    readme_summary = _read_readme(root)
    tech_stack = _detect_tech_stack(root)
    name = _detect_name(root, readme_summary, tech_stack)
    description = _extract_description(readme_summary, name)
    entry_points = _find_entry_points(root, tech_stack)
    dependencies = _extract_dependencies(root, tech_stack)
    test_info = _detect_tests(root, tech_stack)
    key_features = _extract_key_features(readme_summary)
    github_url = _extract_git_remote(root)

    # 深度分析
    languages, total_files, total_loc = _count_loc(root)
    structure = _extract_structure(root)
    code_examples = _extract_code_examples(root, entry_points, tech_stack)
    github_stats = await _fetch_github_stats(github_url) if github_url else None

    return ProjectAnalysis(
        name=name,
        description=description,
        tech_stack=tech_stack,
        languages=languages,
        total_files=total_files,
        total_loc=total_loc,
        structure=structure,
        entry_points=entry_points,
        dependencies=dependencies,
        test_info=test_info,
        readme_summary=readme_summary,
        github_url=github_url,
        github_stats=github_stats,
        key_features=key_features,
        code_examples=code_examples,
    )


def _read_readme(root: Path) -> str:
    """读取 README 前 2000 字符"""
    for name in ("README.md", "README.rst", "README.txt", "README", "readme.md"):
        p = root / name
        if p.exists():
            try:
                return p.read_text(encoding="utf-8", errors="replace")[:2000]
            except Exception:
                continue
    return ""


def _detect_name(root: Path, readme: str, tech_stack: list[str]) -> str:
    """从多个来源推断项目名"""
    # 1. pyproject.toml name
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(encoding="utf-8")
            m = re.search(r'name\s*=\s*"([^"]+)"', text)
            if m:
                return m.group(1)
        except Exception:
            pass

    # 2. package.json name
    pkg = root / "package.json"
    if pkg.exists():
        try:
            import json
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if "name" in data:
                return data["name"]
        except Exception:
            pass

    # 3. README 第一行标题
    if readme:
        first_line = readme.strip().split("\n")[0]
        m = re.match(r"^#\s+(.+)", first_line)
        if m:
            title = m.group(1).strip()
            if len(title) < 50:
                return title

    # 4. 目录名
    return root.name


def _extract_description(readme: str, name: str) -> str:
    """从 README 提取一句话描述"""
    if not readme:
        return f"{name} project"

    lines = readme.strip().split("\n")
    for line in lines[1:10]:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("["):
            if len(stripped) > 10:
                return stripped[:200]

    return f"{name} project"


def _detect_tech_stack(root: Path) -> list[str]:
    """检测技术栈"""
    stack = []
    indicators = {
        "requirements.txt": "Python",
        "setup.py": "Python",
        "pyproject.toml": "Python",
        "Pipfile": "Python",
        "package.json": "Node.js",
        "tsconfig.json": "TypeScript",
        "go.mod": "Go",
        "Cargo.toml": "Rust",
        "build.gradle": "Java/Gradle",
        "build.gradle.kts": "Kotlin/Gradle",
        "pom.xml": "Java/Maven",
        "Gemfile": "Ruby",
        "mix.exs": "Elixir",
        "pubspec.yaml": "Dart/Flutter",
        "Package.swift": "Swift",
        "CMakeLists.txt": "C/C++",
        "Makefile": "Make",
        "Dockerfile": "Docker",
        "docker-compose.yml": "Docker Compose",
        "docker-compose.yaml": "Docker Compose",
        ".github/workflows": "GitHub Actions",
        "Procfile": "Heroku",
        "serverless.yml": "Serverless",
        "terraform": "Terraform",
    }

    for indicator, tech in indicators.items():
        if (root / indicator).exists():
            if tech not in stack:
                stack.append(tech)

    # Python 框架检测
    if "Python" in stack:
        req_files = ["requirements.txt", "setup.py", "pyproject.toml"]
        combined = ""
        for f in req_files:
            p = root / f
            if p.exists():
                try:
                    combined += p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass
        if "django" in combined.lower():
            stack.append("Django")
        if "flask" in combined.lower():
            stack.append("Flask")
        if "fastapi" in combined.lower():
            stack.append("FastAPI")
        if "asyncio" in combined.lower() or "aiohttp" in combined.lower():
            stack.append("asyncio")

    # Node.js 框架检测
    if "Node.js" in stack:
        pkg = root / "package.json"
        if pkg.exists():
            try:
                import json
                data = json.loads(pkg.read_text(encoding="utf-8"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "react" in deps:
                    stack.append("React")
                if "vue" in deps:
                    stack.append("Vue")
                if "next" in deps:
                    stack.append("Next.js")
                if "express" in deps:
                    stack.append("Express")
            except Exception:
                pass

    return stack


def _count_loc(root: Path) -> tuple[dict[str, int], int, int]:
    """按语言统计 LOC，返回 (languages, total_files, total_loc)"""
    languages: dict[str, int] = {}
    total_files = 0

    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过排除目录
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]

        for fname in filenames:
            ext = Path(fname).suffix.lower()
            lang = _EXT_MAP.get(ext)
            if not lang:
                continue

            fpath = Path(dirpath) / fname
            try:
                lines = fpath.read_text(encoding="utf-8", errors="replace").count("\n")
                languages[lang] = languages.get(lang, 0) + lines
                total_files += 1
            except Exception:
                continue

    total_loc = sum(languages.values())

    # 按 LOC 降序排序
    languages = dict(sorted(languages.items(), key=lambda x: x[1], reverse=True))
    return languages, total_files, total_loc


def _extract_structure(root: Path, max_depth: int = 2) -> str:
    """生成关键目录树（纯文本）"""
    lines = [root.name + "/"]

    def _walk(current: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda e: (not e.is_dir(), e.name))
        except PermissionError:
            return

        # 过滤
        entries = [
            e for e in entries
            if e.name not in _SKIP_DIRS
            and not e.name.startswith(".")
            and e.name != "__pycache__"
        ]

        for i, entry in enumerate(entries[:15]):  # 限制每层最多 15 项
            is_last = i == len(entries[:15]) - 1
            connector = "└── " if is_last else "├── "
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{connector}{entry.name}{suffix}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                _walk(entry, prefix + extension, depth + 1)

    _walk(root, "", 1)
    return "\n".join(lines[:60])  # 最多 60 行


def _find_entry_points(root: Path, tech_stack: list[str]) -> list[str]:
    """查找主入口文件"""
    candidates = [
        "main.py", "app.py", "run.py", "cli.py", "manage.py", "server.py",
        "index.js", "index.ts", "app.js", "app.ts", "server.js", "server.ts",
        "main.go", "cmd/main.go",
        "src/main.rs", "src/lib.rs",
        "src/main.java",
    ]
    found = []
    for c in candidates:
        if (root / c).exists():
            found.append(c)
    # Python 包入口：src/<pkg>/__init__.py 或 <pkg>/__init__.py
    skip_pkg = {"tests", "test", "docs", "scripts", "tools", "utils"}
    if not found:
        for child in sorted(root.iterdir()):
            if (child.is_dir()
                    and child.name not in skip_pkg
                    and child.name not in _SKIP_DIRS
                    and not child.name.startswith(".")
                    and (child / "__init__.py").exists()):
                init = f"{child.name}/__init__.py"
                found.append(init)
                break
    return found if found else [root.name]


def _extract_dependencies(root: Path, tech_stack: list[str]) -> list[str]:
    """提取主要依赖列表"""
    deps = []

    # Python: requirements.txt
    req = root / "requirements.txt"
    if req.exists():
        try:
            for line in req.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    pkg = re.split(r"[>=<!\[\];]", line)[0].strip()
                    if pkg:
                        deps.append(pkg)
        except Exception:
            pass

    # Python: pyproject.toml dependencies
    pyproject = root / "pyproject.toml"
    if pyproject.exists() and not deps:
        try:
            text = pyproject.read_text(encoding="utf-8")
            # 找 dependencies = [ 开始，逐行解析到匹配的 ]
            m = re.search(r'^dependencies\s*=\s*\[', text, re.MULTILINE)
            if m:
                rest = text[m.end():]
                bracket_depth = 1
                buf = []
                for ch in rest:
                    if ch == '[':
                        bracket_depth += 1
                    elif ch == ']':
                        bracket_depth -= 1
                        if bracket_depth == 0:
                            break
                    buf.append(ch)
                block = "".join(buf)
                for item in re.findall(r'["\']([^"\']+)["\']', block):
                    pkg = re.split(r"[>=<!\[\];]", item)[0].strip()
                    if pkg:
                        deps.append(pkg)
        except Exception:
            pass

    # Node.js
    pkg = root / "package.json"
    if pkg.exists():
        try:
            import json
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps.extend(data.get("dependencies", {}).keys())
        except Exception:
            pass

    # Go
    gomod = root / "go.mod"
    if gomod.exists():
        try:
            for line in gomod.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("module") and not line.startswith("go "):
                    if not line.startswith("require") and not line.startswith(")"):
                        pkg = line.split()[0] if line.split() else ""
                        if pkg and "/" in pkg:
                            deps.append(pkg)
        except Exception:
            pass

    return deps[:30]  # 最多 30 个


def _detect_tests(root: Path, tech_stack: list[str]) -> str:
    """检测测试框架和测试数量"""
    test_files = 0
    framework = "unknown"

    # 检查 pytest/unittest
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for f in filenames:
            if f.startswith("test_") or f.endswith("_test.py") or f.endswith(".test.js") or f.endswith(".test.ts") or f.endswith("_test.go"):
                test_files += 1

    # 检测框架
    if (root / "pytest.ini").exists() or (root / "conftest.py").exists():
        framework = "pytest"
    elif (root / "jest.config.js").exists() or (root / "jest.config.ts").exists():
        framework = "Jest"
    elif any((root / f).exists() for f in ("vitest.config.ts", "vitest.config.js")):
        framework = "Vitest"

    if test_files == 0:
        return "暂无测试"
    return f"{framework} — {test_files} 个测试文件"


def _extract_git_remote(root: Path) -> str | None:
    """从 .git/config 解析 remote origin URL"""
    config_path = root / ".git" / "config"
    if not config_path.exists():
        return None

    try:
        config = configparser.ConfigParser()
        config.read(str(config_path))
        url = config.get('remote "origin"', "url", fallback=None)
        if url:
            # 转换 git@github.com:user/repo.git → https://github.com/user/repo
            if url.startswith("git@github.com:"):
                url = url.replace("git@github.com:", "https://github.com/")
            url = url.removesuffix(".git")
            return url
    except Exception:
        pass
    return None


async def _fetch_github_stats(url: str) -> dict | None:
    """获取 GitHub 仓库统计信息"""
    if not url or "github.com" not in url:
        return None

    # 提取 owner/repo
    m = re.search(r"github\.com[/:]([^/]+)/([^/\s]+)", url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            if r.status_code != 200:
                return None
            data = r.json()
            return {
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "language": data.get("language"),
            }
    except Exception:
        return None


def _extract_key_features(readme: str) -> list[str]:
    """从 README 提取关键特性列表"""
    if not readme:
        return []

    features = []
    in_features = False
    for line in readme.split("\n"):
        stripped = line.strip()
        # 检测 Features/特性 标题
        if re.match(r"^#{1,3}\s.*(feature|特性|功能|highlight)", stripped, re.IGNORECASE):
            in_features = True
            continue
        if in_features:
            if stripped.startswith("#"):
                break
            if stripped.startswith("- ") or stripped.startswith("* "):
                features.append(stripped[2:].strip()[:100])
                if len(features) >= 8:
                    break

    return features


def _extract_code_examples(
    root: Path, entry_points: list[str], tech_stack: list[str],
) -> list[dict]:
    """从入口文件提取关键代码片段"""
    examples = []
    # 主要语言扩展名
    lang_ext = {".py": "python", ".js": "javascript", ".ts": "typescript", ".go": "go", ".rs": "rust"}

    for ep in entry_points[:3]:
        fpath = root / ep
        if not fpath.exists():
            continue
        ext = fpath.suffix.lower()
        lang = lang_ext.get(ext, ext.lstrip("."))

        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
            # 取前 15 行非空非注释行
            code_lines = []
            for l in lines:
                stripped = l.strip()
                if not stripped:
                    continue
                code_lines.append(l)
                if len(code_lines) >= 15:
                    break

            if code_lines:
                examples.append({
                    "filename": ep,
                    "code": "\n".join(code_lines),
                    "language": lang,
                })
        except Exception:
            continue

    # 如果入口文件不够，尝试 examples/ 目录（含子目录）
    if len(examples) < 2:
        for edir in ("examples", "example", "demo"):
            epath = root / edir
            if not epath.is_dir():
                continue
            for dirpath, _, filenames in os.walk(epath):
                for fname in sorted(filenames):
                    f = Path(dirpath) / fname
                    if f.suffix.lower() in lang_ext:
                        try:
                            content = f.read_text(encoding="utf-8", errors="replace")
                            lines = [l for l in content.split("\n") if l.strip()][:15]
                            if lines:
                                rel = f.relative_to(root)
                                examples.append({
                                    "filename": str(rel),
                                    "code": "\n".join(lines),
                                    "language": lang_ext[f.suffix.lower()],
                                })
                        except Exception:
                            continue
                    if len(examples) >= 3:
                        break
                if len(examples) >= 3:
                    break

    return examples[:3]
