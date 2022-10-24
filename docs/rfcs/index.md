# Request for Comment

{% for child in page.children %}
1. [{{ child.title }}]({{child.url|trim('/rfcs')}}) {{ child.read_source(config)|default(boolean=true) }} - {{ child.meta.state|title }}
{% endfor %}

