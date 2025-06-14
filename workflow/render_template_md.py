import json
from jinja2 import Environment, FileSystemLoader

PLUGINS_FILE = "./plugins.json"
TEMPLATE_FILE = "./README.md.jinja2"
OUTPUT_FILE = "./README.md"

def render_plugins_markdown():
    with open(PLUGINS_FILE, "r", encoding="utf-8") as f:
        plugins = json.load(f)

    env = Environment(loader=FileSystemLoader('.'), autoescape=False, trim_blocks=True, lstrip_blocks=True)
    template = env.get_template(TEMPLATE_FILE)

    rendered = template.render(plugins=plugins)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"✅ 已成功生成: {OUTPUT_FILE}")

if __name__ == "__main__":
    render_plugins_markdown()
