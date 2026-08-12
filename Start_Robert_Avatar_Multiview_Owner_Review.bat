@echo off
setlocal
cd /d "%~dp0"
py tools\avatar_multiview_owner_review_server.py serve ^
  --manifest Avatar\avatar_builder\multiview_authoring\manifests\private\robert_user_avatar_20260716.draft.json ^
  --reviewer-id robert_owner ^
  --open-browser
endlocal
