# NearNodeFlash Pages

## Retrieve the submodules

There are references to files in other repos, so update the submodules for them.

```bash
git submodule update external/nnf-dm
```

## Create mkdocs Environment

```bash
$ git clone git@github.com:NearNodeFlash/NearNodeFlash.github.io.git
$ cd NearNodeFlash.github.io.git
$ python3 -m venv venv
$ . venv/bin/activate
(venv) $ pip install -r mkdocs_requirements.txt
```

### Run mkdocs or mike Server

To run mkdocs server locally, execute `mkdocs serve`. The output will appear similar to below, with the localhost URL listed at the end.

```bash
(venv) $ venv/bin/mkdocs serve
INFO     -  Building documentation...
[...]
INFO     -  Documentation built in 0.22 seconds
INFO     -  [10:59:28] Watching paths for changes: 'docs', 'mkdocs.yml'
INFO     -  [10:59:28] Serving on http://127.0.0.1:8000/
```

Or run `mike serve`.

```bash
(venv) $ venv/bin/mike serve  
Starting server at http://localhost:8000/
Press Ctrl+C to quit.
CStopping server...
```

