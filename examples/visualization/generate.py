import json
import os

TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "template.html")
MARKER = '["graph { goes -> here }"]'


def generate_html(dot_source_list, outfile):
    graphs = json.dumps(dot_source_list, indent=2)

    with open(TEMPLATE_FILE) as template:
        for line in template:
            if MARKER in line:
                line = line.replace(MARKER, graphs)
            outfile.write(line)
