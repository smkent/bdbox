from __future__ import annotations

INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>bdbox</title>
  <link rel="icon" type="image/png" href="/static/favicon.png">
  <link rel="stylesheet" href="/static/app.css">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ overflow: hidden; background: #111; }}
  </style>
  <script>window.__BDBOX__ = {{"viewerPort": {ocp_cad_viewer_port}}};</script>
  <script src="/static/app.js" defer></script>
</head>
<body>
  <div id="layout" style="width: 100%; height: 100vh;"></div>
</body>
</html>
"""
