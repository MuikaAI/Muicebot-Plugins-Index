"""
Muicebot 插件测试实现

修改自 https://github.com/zhenxun-org/zhenxunflow/releases/latest/download/plugin_test.py

感谢 zhenxun 项目实现！以下是源文件头部说明

---

插件加载测试

测试代码修改自 <https://github.com/nonebot/noneflow>，谢谢 [NoneBot](https://github.com/nonebot)。

在 GitHub Actions 中运行，通过 GitHub Event 文件获取所需信息。并将测试结果保存至 GitHub Action 的输出文件中。

当前会输出 RESULT, OUTPUT, METADATA 三个数据，分别对应测试结果、测试输出、插件元数据。

经测试可以直接在 Python 3.10+ 环境下运行，无需额外依赖。
"""

import json
import os
import sys
import re
import nonebot

from render_template_md import render_plugins_markdown
from typing import NoReturn
from dataclasses import dataclass
from nonebot.adapters.onebot.v11 import Adapter
from asyncio import create_subprocess_shell, run, subprocess
from pathlib import Path

ISSUE_PATTERN = r"### {}\s+([^\s#].*?)(?=(?:\s+###|$))"
PLUGIN_NAME_PATTERN = re.compile(ISSUE_PATTERN.format("名称"))
PLUGIN_PROJECT_PATTERN = re.compile(ISSUE_PATTERN.format("插件项目名"))
PLUGIN_MODULE_NAME_PATTERN = re.compile(ISSUE_PATTERN.format("插件模块名"))
PLUGIN_DESCRIPTION_PATH_PATTERN = re.compile(ISSUE_PATTERN.format("插件描述"))
PLUGIN_GITHUB_URL_PATTERN = re.compile(ISSUE_PATTERN.format("项目链接"))

@dataclass
class NewPluginRequest:
    name: str
    project: str
    module: str
    description: str
    repo: str

    @staticmethod
    def extract_from_issue(body:str) -> "NewPluginRequest":
        name=PLUGIN_NAME_PATTERN.search(body)
        project=PLUGIN_PROJECT_PATTERN.search(body)
        module=PLUGIN_MODULE_NAME_PATTERN.search(body)
        description=PLUGIN_DESCRIPTION_PATH_PATTERN.search(body)
        repo=PLUGIN_GITHUB_URL_PATTERN.search(body)

        if not all([name, project, module, description, repo]):
            skip(f"issue 体内容不完整: {body}")
            sys.exit(1)

        return NewPluginRequest(
            name=name.group(1).strip(),  # type:ignore
            project=project.group(1).strip(),  # type:ignore
            module=module.group(1).strip(),  # type:ignore
            description=description.group(1).strip(),  # type:ignore
            repo=repo.group(1).strip()  # type:ignore
        )


def skip(msg: str) -> NoReturn:
    """
    因不满足特定条件而跳过工作流
    """
    print(f"🤔{msg}")
    sys.exit(1)

def error(msg: str) -> NoReturn:
    """
    因测试流程中失败而中止工作流
    """
    print(f"❌{msg}")
    sys.exit(1)

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
    proc = await create_subprocess_shell(
        f"""git clone {repo} {project}""",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="plugins",
    )
    stdout, stderr = await proc.communicate()
    code = proc.returncode
    if code:
        error(f"拉取 {repo} 时发生错误: {stderr}")

    # python -m pip install
    plugin_path = Path("plugins") / project

    if (plugin_path / "requirements.txt").exists():
        proc = await create_subprocess_shell(
            f"""python -m pip install requirements.txt""",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=plugin_path,
        )
        stdout, stderr = await proc.communicate()
        code = proc.returncode
        if code:
            error(f"安装插件依赖时发生错误: {stderr}")

    elif (plugin_path / "pyproject.toml").exists():
        proc = await create_subprocess_shell(
            f"""python -m pip install .""",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=plugin_path,
        )
        stdout, stderr = await proc.communicate()
        code = proc.returncode
        if code:
            error(f"安装插件依赖时发生错误: {stderr}")


async def plugin_test(plugin_info: NewPluginRequest):
    nonebot.init()
    driver = nonebot.get_driver()
    driver.register_adapter(Adapter)
    nonebot.load_plugin("muicebot")

    from muicebot.plugin import load_plugin, PluginMetadata
    plugin_path = Path("plugins") / plugin_info.project
    plugin = load_plugin(plugin_path)

    if not plugin:
        error("无法加载插件！")

    # Muicebot 1.0 还没发布，先忽略着
    # metadata: PluginMetadata = plugin.metadata  # type:ignore
    # if not metadata:
    #     # error("未检测到插件元数据，请先补充")
    #     return
    
    # metadata = {{
    #     "name": plugin_info.name,
    #     "module": plugin_info.module,
    #     "description": plugin.metadata.description,
    #     "usage": plugin.metadata.usage,
    #     "plugin_type": plugin.metadata.extra["plugin_type"],
    #     "repo": plugin_info.repo,
    # }}
    # with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf8") as f:
    #     f.write(f"METADATA<<EOF\\n{{json.dumps(metadata, cls=SetEncoder)}}\\nEOF\\n")

    # if plugin.metadata.config and not issubclass(plugin.metadata.config, BaseModel):
    #     logger.error("插件配置项不是 Pydantic BaseModel 的子类")
    #     exit(1)



def update_plugins_json(plugin_project:str,
                        plugin_module:str,
                        plugin_name:str,
                        plugin_desc:str,
                        plugin_repo:str,
                        filepath:str="plugins.json"):
    """
    更新插件索引
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print("❌无法解析 JSON")
        sys.exit(1)
    except FileNotFoundError:
        print("⚠️插件索引文件不存在！正在新建...")
    except Exception as e:
        print(f"❌发生了未知错误 {e}")
        sys.exit(1)

    data[plugin_project] = {
        "module": plugin_module,
        "name": plugin_name,
        "description": plugin_desc,
        "repo": plugin_repo
    }

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("✅成功更新 Plugin.json!")
    except Exception as e:
        print(f"❌发生了未知错误 {e}")
        sys.exit(1)

if __name__ == "__main__":
    print(f"🛠️开始 Python 工作流...")
    print(f"🛠️提取插件信息 ...")
    plugin_info = extract_issue_body()

    print(f"🛠️运行插件测试 ...")
    run(plugin_test(plugin_info))
    
    print("🛠️更新索引JSON ...")
    update_plugins_json(plugin_info.project, plugin_info.module, plugin_info.name, plugin_info.description, plugin_info.repo)  # type:ignore

    print(f"🛠️更新 Readme.md ...")
    render_plugins_markdown()