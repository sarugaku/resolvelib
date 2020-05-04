import json
import os

import jinja2


environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    autoescape=True,
)


def generate_html(dot_source_list, outfile):
    template = environment.get_template("template.html")
    iterable = template.generate(dot_source_list=dot_source_list)

    for item in iterable:
        outfile.write(item)
