"""
Muicebot 插件测试实现

修改自 https://github.com/zhenxun-org/zhenxunflow/releases/latest/download/plugin_test.py

感谢 zhenxun 项目实现！
"""

import json
import os
import re
import sys
from asyncio import create_subprocess_shell, run, subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

import nonebot
from jinja2 import Environment, FileSystemLoader
from nonebot.adapters.onebot.v11 import Adapter

ISSUE_PATTERN = r"### {}\s+([^\s#].*?)(?=(?:\s+###|$))"
PLUGIN_NAME_PATTERN = re.compile(ISSUE_PATTERN.format("名称"))
PLUGIN_PROJECT_PATTERN = re.compile(ISSUE_PATTERN.format("插件项目名"))
PLUGIN_MODULE_NAME_PATTERN = re.compile(ISSUE_PATTERN.format("插件模块名"))
PLUGIN_DESCRIPTION_PATH_PATTERN = re.compile(ISSUE_PATTERN.format("插件描述"))
PLUGIN_GITHUB_URL_PATTERN = re.compile(ISSUE_PATTERN.format("项目链接"))

PLUGINS_FILE = "./plugins.json"
TEMPLATE_FILE = "./README.md.jinja2"
OUTPUT_FILE = "./README.md"

MUICEBOT_PATH = Path("./Muicebot")
MUICEBOT_PLUGINS_PATH = MUICEBOT_PATH / "plugins"


@dataclass
class NewPluginRequest:
    name: str
    project: str
    module: str
    description: str
    repo: str

    @staticmethod
    def extract_from_issue(body: str) -> "NewPluginRequest":
        name = PLUGIN_NAME_PATTERN.search(body)
        project = PLUGIN_PROJECT_PATTERN.search(body)
        module = PLUGIN_MODULE_NAME_PATTERN.search(body)
        description = PLUGIN_DESCRIPTION_PATH_PATTERN.search(body)
        repo = PLUGIN_GITHUB_URL_PATTERN.search(body)

        if not all([name, project, module, description, repo]):
            skip(f"issue 体内容不完整: {body}")

        return NewPluginRequest(
            name=name.group(1).strip(),  # type:ignore
            project=project.group(1).strip(),  # type:ignore
            module=module.group(1).strip(),  # type:ignore
            description=description.group(1).strip(),  # type:ignore
            repo=repo.group(1).strip(),  # type:ignore
        )


def skip(msg: str) -> NoReturn:
    """
    因不满足特定条件而跳过工作流
    """
    print(f"🤔{msg}")
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write("should_skip=true\n")
    sys.exit(0)


def error(msg: str) -> NoReturn:
    """
    因测试流程中失败而中止工作流
    """
    print(f"❌{msg}")
    sys.exit(1)


async def run_command(command: str, cwd: Path, error_message: str):
    """Helper to run a shell command and handle errors."""
    proc = await create_subprocess_shell(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
    )
    _stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        stderr_decoded = stderr.decode(errors="ignore").strip()
        error(f"{error_message}: {stderr_decoded}")


def extract_issue_body() -> NewPluginRequest:
    """
    解析 Issue 负载
    """
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event_name = os.environ.get("GITHUB_EVENT_NAME")

    if event_path is None:
        skip("未找到 GITHUB_EVENT_PATH，已跳过")

    elif event_name not in ["issues", "issue_comment"]:
        skip(f"不支持的事件: {event_name}，已跳过")

    with open(event_path, encoding="utf8") as f:
        event = json.load(f)

    issue = event["issue"]
    issue_body = issue.get("body")
    pull_request = issue.get("pull_request")
    state = issue.get("state")
    labels = issue.get("labels", [])

    if pull_request:
        skip("评论在拉取请求下，已跳过")

    elif state != "open":
        skip("议题未开启，已跳过")

    elif not any(label["name"] == "Plugin" for label in labels):
        skip("议题与插件发布无关，已跳过")

    return NewPluginRequest.extract_from_issue(issue_body)


async def install_plugin(plugin_info: NewPluginRequest):
    """
    安装插件依赖
    """
    repo = plugin_info.repo
    project = plugin_info.project

    # git clone
    await run_command(
        f"git clone {repo} {project}",
        cwd=MUICEBOT_PLUGINS_PATH,
        error_message=f"拉取 {repo} 时发生错误",
    )

    # python -m pip install
    plugin_path = Path(MUICEBOT_PLUGINS_PATH) / project

    if (plugin_path / "requirements.txt").exists():
        await run_command(
            "python -m pip install -r requirements.txt",
            cwd=plugin_path,
            error_message="安装插件依赖 (requirements.txt) 时发生错误",
        )
    elif (plugin_path / "pyproject.toml").exists():
        await run_command(
            "python -m pip install .",
            cwd=plugin_path,
            error_message="安装插件依赖 (pyproject.toml) 时发生错误",
        )


async def plugin_test(plugin_info: NewPluginRequest):
    os.chdir(MUICEBOT_PATH)

    nonebot.init()
    driver = nonebot.get_driver()
    driver.register_adapter(Adapter)
    nonebot.load_plugin("muicebot")

    from muicebot.plugin import load_plugin

    plugin_path = Path("plugins") / plugin_info.project / plugin_info.module
    plugin = load_plugin(plugin_path)

    if not plugin:
        error("无法加载插件！")

    metadata = plugin.meta
    if not metadata:
        error("未检测到插件元数据，请先补充")

    # metadata = {
    #     "name": plugin_info.name,
    #     "module": plugin_info.module,
    #     "description": metadata.description,
    #     "usage": metadata.usage,
    #     "repo": plugin_info.repo,
    # }
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf8") as f:
        f.write(f"plugin_name={plugin_info.name}\n")

    os.chdir("..")


def update_plugins_json(
    plugin_project: str,
    plugin_module: str,
    plugin_name: str,
    plugin_desc: str,
    plugin_repo: str,
    filepath: str = "plugins.json",
):
    """
    更新插件索引
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        error("❌无法解析 JSON")
    except FileNotFoundError:
        print("⚠️插件索引文件不存在！正在新建...")
        data = {}
    except Exception as e:
        error(f"❌发生了未知错误 {e}")

    data[plugin_project] = {
        "module": plugin_module,
        "name": plugin_name,
        "description": plugin_desc,
        "repo": plugin_repo,
    }

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("✅成功更新 Plugin.json!")
    except Exception as e:
        error(f"❌发生了未知错误 {e}")


def render_plugins_markdown():
    with open(PLUGINS_FILE, "r", encoding="utf-8") as f:
        plugins = json.load(f)

    env = Environment(
        loader=FileSystemLoader("."),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(TEMPLATE_FILE)

    rendered = template.render(plugins=plugins)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"✅ 已成功生成: {OUTPUT_FILE}")


if __name__ == "__main__":
    print("🛠️开始 Python 工作流...")
    print("🛠️提取插件信息 ...")
    plugin_info = extract_issue_body()

    print("🛠️安装插件依赖 ...")
    run(install_plugin(plugin_info))

    print("🛠️运行插件测试 ...")
    run(plugin_test(plugin_info))

    print("🛠️更新索引JSON ...")
    update_plugins_json(
        plugin_info.project,
        plugin_info.module,
        plugin_info.name,
        plugin_info.description,
        plugin_info.repo,
    )

    print("🛠️更新 Readme.md ...")
    render_plugins_markdown()
